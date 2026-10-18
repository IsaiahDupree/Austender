"""
Scheduler Module

This module provides a scheduling system for running recurring tasks 
like scraping websites for new opportunities and sending notifications.
"""

import threading
import schedule
import time
import datetime
from typing import Callable, Dict, List, Any, Optional
import logging
import functools

# Import configuration
from config.config import (
    UPDATE_INTERVAL_DAYS, SCHEDULER_ENABLED
)

# Import logging and database models
from utils.logging_config import setup_logging

# Set up logger
logger = setup_logging(__name__)


class Scheduler:
    """Scheduler for running periodic tasks."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self._running = False
        self._thread = None
        self._scheduled_jobs = {}
        self._enabled = SCHEDULER_ENABLED
        logger.info("Scheduler initialized")
    
    def start(self) -> None:
        """Start the scheduler in a background thread."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        if not self._enabled:
            logger.warning("Scheduler is disabled. Not starting.")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            logger.warning("Scheduler is not running")
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler loop."""
        while self._running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(5)  # Wait a bit before retrying
    
    def add_job(
        self,
        job_id: str,
        func: Callable,
        interval_days: Optional[int] = None,
        interval_hours: Optional[int] = None, 
        interval_minutes: Optional[int] = None,
        run_at_specific_time: Optional[str] = None,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None
    ) -> bool:
        """
        Add a job to the scheduler.
        
        Args:
            job_id (str): Unique identifier for the job
            func (Callable): Function to run
            interval_days (Optional[int]): Run every X days
            interval_hours (Optional[int]): Run every X hours
            interval_minutes (Optional[int]): Run every X minutes
            run_at_specific_time (Optional[str]): Run at specific time (24h format, e.g. "14:30")
            args (Optional[List]): Arguments to pass to the function
            kwargs (Optional[Dict]): Keyword arguments to pass to the function
            
        Returns:
            bool: True if job was added successfully
        """
        if job_id in self._scheduled_jobs:
            logger.warning(f"Job {job_id} is already scheduled")
            return False
        
        # Apply defaults if not specified
        if interval_days is None and interval_hours is None and interval_minutes is None and run_at_specific_time is None:
            interval_days = UPDATE_INTERVAL_DAYS
        
        # Create a wrapper function that logs exceptions
        @functools.wraps(func)
        def job_wrapper(*args, **kwargs):
            try:
                logger.info(f"Running scheduled job: {job_id}")
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Completed job {job_id} in {elapsed:.2f} seconds")
                return result
            except Exception as e:
                logger.error(f"Error in scheduled job {job_id}: {str(e)}", exc_info=True)
        
        # Set up arguments
        job_args = args or []
        job_kwargs = kwargs or {}
        
        # Schedule the job
        if run_at_specific_time:
            job = schedule.every().day.at(run_at_specific_time).do(
                job_wrapper, *job_args, **job_kwargs
            )
        elif interval_days:
            job = schedule.every(interval_days).days.do(
                job_wrapper, *job_args, **job_kwargs
            )
        elif interval_hours:
            job = schedule.every(interval_hours).hours.do(
                job_wrapper, *job_args, **job_kwargs
            )
        elif interval_minutes:
            job = schedule.every(interval_minutes).minutes.do(
                job_wrapper, *job_args, **job_kwargs
            )
        else:
            logger.error(f"Invalid schedule parameters for job {job_id}")
            return False
        
        self._scheduled_jobs[job_id] = job
        logger.info(f"Added job {job_id} to scheduler")
        return True
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the scheduler.
        
        Args:
            job_id (str): Job identifier
            
        Returns:
            bool: True if job was removed, False otherwise
        """
        if job_id not in self._scheduled_jobs:
            logger.warning(f"Job {job_id} is not scheduled")
            return False
        
        schedule.cancel_job(self._scheduled_jobs[job_id])
        del self._scheduled_jobs[job_id]
        logger.info(f"Removed job {job_id} from scheduler")
        return True
    
    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all scheduled jobs.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of job information
        """
        jobs_info = {}
        for job_id, job in self._scheduled_jobs.items():
            next_run = job.next_run
            jobs_info[job_id] = {
                "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None,
                "last_run": getattr(job, "last_run", None),
                "interval": str(job.interval),
                "unit": job.unit,
                "at_time": str(job.at_time) if job.at_time else None,
            }
        return jobs_info
    
    def run_job_now(self, job_id: str) -> bool:
        """
        Run a scheduled job immediately.
        
        Args:
            job_id (str): Job identifier
            
        Returns:
            bool: True if job was run, False otherwise
        """
        if job_id not in self._scheduled_jobs:
            logger.warning(f"Job {job_id} is not scheduled")
            return False
        
        job = self._scheduled_jobs[job_id]
        
        try:
            job.run()
            logger.info(f"Manually ran job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error running job {job_id} manually: {str(e)}")
            return False
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    @property
    def is_enabled(self) -> bool:
        """Check if scheduler is enabled."""
        return self._enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the scheduler.
        
        Args:
            enabled (bool): Whether to enable the scheduler
        """
        self._enabled = enabled
        if not enabled and self._running:
            self.stop()
        elif enabled and not self._running:
            self.start()


# Create a singleton instance
_scheduler_instance = None

def get_scheduler():
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = Scheduler()
    return _scheduler_instance

# Initialize the scheduler
scheduler = get_scheduler()
