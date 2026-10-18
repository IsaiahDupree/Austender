"""
Asynchronous Task Queue Module

This module provides a simple task queue for handling asynchronous operations
such as web scraping, document analysis, and email notifications.
"""

import asyncio
import concurrent.futures
import threading
import queue
import time
import uuid
import traceback
from typing import Dict, Any, Callable, Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import functools

# Import logging configuration
from utils.logging_config import setup_logging

# Set up logger
logger = setup_logging(__name__)


class TaskStatus(Enum):
    """Task status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Class for storing task results."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate the task duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class TaskQueue:
    """Asynchronous task queue for handling long-running operations."""
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the task queue.
        
        Args:
            max_workers (int): Maximum number of worker threads
        """
        self.max_workers = max_workers
        self.tasks: Dict[str, TaskResult] = {}
        self.task_queue = queue.Queue()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.RLock()
        
        # Start worker thread
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        logger.info(f"Task queue initialized with {max_workers} workers")
    
    def _worker_loop(self) -> None:
        """Worker loop that processes tasks from the queue."""
        while self.running:
            try:
                # Try to get a task from the queue
                task_id, task_func, args, kwargs = self.task_queue.get(timeout=1)
                
                with self.lock:
                    # Update task status to running
                    if task_id in self.tasks:
                        self.tasks[task_id].status = TaskStatus.RUNNING
                        self.tasks[task_id].start_time = time.time()
                
                try:
                    # Execute the task
                    logger.info(f"Executing task {task_id}")
                    result = task_func(*args, **kwargs)
                    
                    # Update task result
                    with self.lock:
                        if task_id in self.tasks:
                            self.tasks[task_id].status = TaskStatus.COMPLETED
                            self.tasks[task_id].result = result
                            self.tasks[task_id].end_time = time.time()
                    
                    logger.info(f"Task {task_id} completed successfully")
                
                except Exception as e:
                    # Handle task failure
                    error_message = f"{str(e)}\n{traceback.format_exc()}"
                    logger.error(f"Task {task_id} failed: {error_message}")
                    
                    with self.lock:
                        if task_id in self.tasks:
                            self.tasks[task_id].status = TaskStatus.FAILED
                            self.tasks[task_id].error = error_message
                            self.tasks[task_id].end_time = time.time()
                
                finally:
                    # Mark task as done in the queue
                    self.task_queue.task_done()
            
            except queue.Empty:
                # No tasks in the queue, just continue
                pass
            except Exception as e:
                # Unexpected error in the worker loop
                logger.error(f"Error in worker loop: {str(e)}\n{traceback.format_exc()}")
    
    def enqueue(self, func: Callable, *args, **kwargs) -> str:
        """
        Enqueue a task for asynchronous execution.
        
        Args:
            func (Callable): Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            str: Task ID
        """
        task_id = str(uuid.uuid4())
        
        # Create task result
        task_result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        
        with self.lock:
            self.tasks[task_id] = task_result
        
        # Add task to queue
        self.task_queue.put((task_id, func, args, kwargs))
        logger.info(f"Task {task_id} enqueued")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """
        Get the status of a task.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            Optional[TaskResult]: Task result or None if not found
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            bool: True if task was cancelled, False otherwise
        """
        with self.lock:
            if task_id in self.tasks and self.tasks[task_id].status == TaskStatus.PENDING:
                self.tasks[task_id].status = TaskStatus.CANCELLED
                logger.info(f"Task {task_id} cancelled")
                return True
            
            logger.warning(f"Cannot cancel task {task_id}: not found or not pending")
            return False
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """
        Wait for a task to complete.
        
        Args:
            task_id (str): Task ID
            timeout (Optional[float]): Maximum time to wait in seconds, or None to wait indefinitely
            
        Returns:
            Optional[TaskResult]: Task result or None if timeout reached
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                if task_id in self.tasks:
                    status = self.tasks[task_id].status
                    if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        return self.tasks[task_id]
            
            # Check timeout
            if timeout is not None and time.time() - start_time > timeout:
                logger.warning(f"Timeout reached waiting for task {task_id}")
                return None
            
            # Sleep a bit to avoid busy waiting
            time.sleep(0.1)
    
    def cleanup_old_tasks(self, max_age: float = 3600) -> int:
        """
        Remove completed tasks older than the specified age.
        
        Args:
            max_age (float): Maximum age in seconds (default: 1 hour)
            
        Returns:
            int: Number of tasks removed
        """
        current_time = time.time()
        tasks_to_remove = []
        
        with self.lock:
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.end_time and current_time - task.end_time > max_age):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
        
        return len(tasks_to_remove)
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the task queue.
        
        Args:
            wait (bool): Wait for all tasks to complete
        """
        logger.info("Shutting down task queue")
        
        # Stop accepting new tasks
        self.running = False
        
        if wait:
            # Wait for all tasks to complete
            self.task_queue.join()
        
        # Stop the worker thread
        self.worker_thread.join(timeout=1)
        
        # Shutdown the executor
        self.executor.shutdown(wait=wait)
        
        logger.info("Task queue shut down")


# Global task queue instance
task_queue = TaskQueue()


def async_task(func):
    """
    Decorator to execute a function as an asynchronous task.
    
    Args:
        func (Callable): Function to decorate
        
    Returns:
        Callable: Decorated function that returns a task ID
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return task_queue.enqueue(func, *args, **kwargs)
    return wrapper
