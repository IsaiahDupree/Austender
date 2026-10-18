"""
Unit tests for the scheduler module.
"""

import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock, call
import time
import threading
import schedule

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.scheduler import Scheduler


class TestScheduler(unittest.TestCase):
    """Tests for the Scheduler class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Patch schedule to avoid actual scheduling during tests
        self.patcher = patch('utils.scheduler.schedule')
        self.mock_schedule = self.patcher.start()
        
        # Initialize scheduler with testing enabled
        self.scheduler = Scheduler()
        self.scheduler._enabled = True
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop scheduler if running
        if self.scheduler._running:
            self.scheduler.stop()
        
        # Stop the patcher
        self.patcher.stop()
        
        # Clear schedule
        schedule.clear()
    
    def test_start_scheduler(self):
        """Test starting the scheduler."""
        # Start the scheduler
        self.scheduler.start()
        
        # Verify scheduler is running
        self.assertTrue(self.scheduler._running)
        self.assertIsNotNone(self.scheduler._thread)
        
        # Stop scheduler
        self.scheduler.stop()
    
    def test_start_scheduler_already_running(self):
        """Test attempting to start scheduler when already running."""
        # Start the scheduler
        self.scheduler.start()
        
        # Capture original thread
        original_thread = self.scheduler._thread
        
        # Try to start again
        self.scheduler.start()
        
        # Verify same thread is still running
        self.assertEqual(self.scheduler._thread, original_thread)
        
        # Stop scheduler
        self.scheduler.stop()
    
    def test_start_scheduler_disabled(self):
        """Test starting scheduler when disabled."""
        # Disable scheduler
        self.scheduler._enabled = False
        
        # Try to start
        self.scheduler.start()
        
        # Verify scheduler didn't start
        self.assertFalse(self.scheduler._running)
        self.assertIsNone(self.scheduler._thread)
    
    def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        # Start the scheduler
        self.scheduler.start()
        
        # Stop the scheduler
        self.scheduler.stop()
        
        # Verify scheduler is stopped
        self.assertFalse(self.scheduler._running)
        self.assertIsNone(self.scheduler._thread)
    
    def test_stop_scheduler_not_running(self):
        """Test stopping scheduler when not running."""
        # Verify scheduler isn't running
        self.assertFalse(self.scheduler._running)
        
        # Try to stop
        self.scheduler.stop()
        
        # Verify still not running
        self.assertFalse(self.scheduler._running)
    
    @patch('utils.scheduler.time.sleep')
    def test_run_scheduler_loop(self, mock_sleep):
        """Test the scheduler loop."""
        # Mock schedule.run_pending to do nothing
        self.mock_schedule.run_pending = MagicMock()
        
        # Set up to exit after a few loops
        mock_sleep.side_effect = [None, None, Exception("Stop loop")]
        
        # Run loop
        with self.assertRaises(Exception):
            self.scheduler._running = True
            self.scheduler._run_scheduler()
        
        # Verify schedule was run
        self.assertEqual(self.mock_schedule.run_pending.call_count, 3)
    
    def test_add_job_daily(self):
        """Test adding a daily job."""
        # Mock function
        mock_func = MagicMock()
        
        # Mock schedule.every().days
        mock_every = MagicMock()
        self.mock_schedule.every.return_value = mock_every
        mock_days = MagicMock()
        mock_every.days = mock_days
        mock_job = MagicMock()
        mock_days.do.return_value = mock_job
        
        # Add job
        result = self.scheduler.add_job(
            job_id="test_daily",
            func=mock_func,
            interval_days=2
        )
        
        # Verify job was added
        self.assertTrue(result)
        self.assertIn("test_daily", self.scheduler._scheduled_jobs)
        self.assertEqual(self.scheduler._scheduled_jobs["test_daily"], mock_job)
        
        # Verify schedule was called correctly
        self.mock_schedule.every.assert_called_once_with(2)
        mock_days.do.assert_called_once()
    
    def test_add_job_hourly(self):
        """Test adding an hourly job."""
        # Mock function
        mock_func = MagicMock()
        
        # Mock schedule.every().hours
        mock_every = MagicMock()
        self.mock_schedule.every.return_value = mock_every
        mock_hours = MagicMock()
        mock_every.hours = mock_hours
        mock_job = MagicMock()
        mock_hours.do.return_value = mock_job
        
        # Add job
        result = self.scheduler.add_job(
            job_id="test_hourly",
            func=mock_func,
            interval_hours=3
        )
        
        # Verify job was added
        self.assertTrue(result)
        self.assertIn("test_hourly", self.scheduler._scheduled_jobs)
        self.assertEqual(self.scheduler._scheduled_jobs["test_hourly"], mock_job)
        
        # Verify schedule was called correctly
        self.mock_schedule.every.assert_called_once_with(3)
        mock_hours.do.assert_called_once()
    
    def test_add_job_minutes(self):
        """Test adding a minutely job."""
        # Mock function
        mock_func = MagicMock()
        
        # Mock schedule.every().minutes
        mock_every = MagicMock()
        self.mock_schedule.every.return_value = mock_every
        mock_minutes = MagicMock()
        mock_every.minutes = mock_minutes
        mock_job = MagicMock()
        mock_minutes.do.return_value = mock_job
        
        # Add job
        result = self.scheduler.add_job(
            job_id="test_minutely",
            func=mock_func,
            interval_minutes=5
        )
        
        # Verify job was added
        self.assertTrue(result)
        self.assertIn("test_minutely", self.scheduler._scheduled_jobs)
        self.assertEqual(self.scheduler._scheduled_jobs["test_minutely"], mock_job)
        
        # Verify schedule was called correctly
        self.mock_schedule.every.assert_called_once_with(5)
        mock_minutes.do.assert_called_once()
    
    def test_add_job_specific_time(self):
        """Test adding a job to run at a specific time."""
        # Mock function
        mock_func = MagicMock()
        
        # Mock schedule.every().day.at()
        mock_every = MagicMock()
        self.mock_schedule.every.return_value = mock_every
        mock_day = MagicMock()
        mock_every.day = mock_day
        mock_at = MagicMock()
        mock_day.at = mock_at
        mock_job = MagicMock()
        mock_at.do.return_value = mock_job
        
        # Add job
        result = self.scheduler.add_job(
            job_id="test_daily_time",
            func=mock_func,
            run_at_specific_time="14:30"
        )
        
        # Verify job was added
        self.assertTrue(result)
        self.assertIn("test_daily_time", self.scheduler._scheduled_jobs)
        self.assertEqual(self.scheduler._scheduled_jobs["test_daily_time"], mock_job)
        
        # Verify schedule was called correctly
        mock_day.at.assert_called_once_with("14:30")
        mock_at.do.assert_called_once()
    
    def test_add_job_with_args(self):
        """Test adding a job with arguments."""
        # Mock function
        mock_func = MagicMock()
        
        # Mock schedule
        mock_every = MagicMock()
        self.mock_schedule.every.return_value = mock_every
        mock_days = MagicMock()
        mock_every.days = mock_days
        mock_job = MagicMock()
        mock_days.do.return_value = mock_job
        
        # Add job with args and kwargs
        args = ["arg1", "arg2"]
        kwargs = {"kwarg1": "value1", "kwarg2": "value2"}
        
        result = self.scheduler.add_job(
            job_id="test_args",
            func=mock_func,
            interval_days=1,
            args=args,
            kwargs=kwargs
        )
        
        # Verify job was added
        self.assertTrue(result)
        
        # Verify args and kwargs were passed
        do_call = mock_days.do.call_args
        # First arg should be the wrapper function
        wrapper_func = do_call[0][0]
        # Check that other args match what we passed
        self.assertEqual(do_call[0][1:], tuple(args))
        self.assertEqual(do_call[1], kwargs)
    
    def test_add_job_already_exists(self):
        """Test adding a job with an ID that already exists."""
        # Set up existing job
        self.scheduler._scheduled_jobs["test_job"] = MagicMock()
        
        # Try to add again
        result = self.scheduler.add_job(
            job_id="test_job",
            func=MagicMock(),
            interval_days=1
        )
        
        # Verify job was not added
        self.assertFalse(result)
    
    def test_add_job_invalid_params(self):
        """Test adding a job with invalid parameters."""
        # Try to add with no interval or time
        result = self.scheduler.add_job(
            job_id="test_invalid",
            func=MagicMock(),
            interval_days=None,
            interval_hours=None,
            interval_minutes=None,
            run_at_specific_time=None
        )
        
        # Verify job was not added
        self.assertFalse(result)
    
    def test_remove_job(self):
        """Test removing a job."""
        # Set up existing job
        mock_job = MagicMock()
        self.scheduler._scheduled_jobs["test_job"] = mock_job
        
        # Remove job
        result = self.scheduler.remove_job("test_job")
        
        # Verify job was removed
        self.assertTrue(result)
        self.assertNotIn("test_job", self.scheduler._scheduled_jobs)
        
        # Verify schedule was called correctly
        self.mock_schedule.cancel_job.assert_called_once_with(mock_job)
    
    def test_remove_job_not_found(self):
        """Test removing a job that doesn't exist."""
        # Try to remove non-existent job
        result = self.scheduler.remove_job("nonexistent")
        
        # Verify job was not removed
        self.assertFalse(result)
        self.mock_schedule.cancel_job.assert_not_called()
    
    def test_get_all_jobs(self):
        """Test getting all scheduled jobs."""
        # Set up existing jobs
        job1 = MagicMock()
        job1.next_run = time.time() + 3600  # 1 hour from now
        job1.last_run = None
        job1.interval = 1
        job1.unit = "days"
        job1.at_time = None
        
        job2 = MagicMock()
        job2.next_run = time.time() + 7200  # 2 hours from now
        job2.last_run = time.time() - 3600  # 1 hour ago
        job2.interval = 2
        job2.unit = "hours"
        job2.at_time = None
        
        self.scheduler._scheduled_jobs = {
            "job1": job1,
            "job2": job2
        }
        
        # Get all jobs
        jobs_info = self.scheduler.get_all_jobs()
        
        # Verify result
        self.assertEqual(len(jobs_info), 2)
        self.assertIn("job1", jobs_info)
        self.assertIn("job2", jobs_info)
        
        # Check job1 details
        self.assertIn("next_run", jobs_info["job1"])
        self.assertEqual(jobs_info["job1"]["last_run"], None)
        self.assertEqual(jobs_info["job1"]["interval"], "1")
        self.assertEqual(jobs_info["job1"]["unit"], "days")
        self.assertEqual(jobs_info["job1"]["at_time"], "None")
        
        # Check job2 details
        self.assertIn("next_run", jobs_info["job2"])
        self.assertIsNotNone(jobs_info["job2"]["last_run"])
        self.assertEqual(jobs_info["job2"]["interval"], "2")
        self.assertEqual(jobs_info["job2"]["unit"], "hours")
        self.assertEqual(jobs_info["job2"]["at_time"], "None")
    
    def test_run_job_now(self):
        """Test running a job immediately."""
        # Set up existing job
        mock_job = MagicMock()
        self.scheduler._scheduled_jobs["test_job"] = mock_job
        
        # Run job now
        result = self.scheduler.run_job_now("test_job")
        
        # Verify job was run
        self.assertTrue(result)
        mock_job.run.assert_called_once()
    
    def test_run_job_now_not_found(self):
        """Test running a job that doesn't exist."""
        # Try to run non-existent job
        result = self.scheduler.run_job_now("nonexistent")
        
        # Verify job was not run
        self.assertFalse(result)
    
    def test_run_job_now_error(self):
        """Test running a job that raises an error."""
        # Set up existing job that raises an error
        mock_job = MagicMock()
        mock_job.run.side_effect = Exception("Job error")
        self.scheduler._scheduled_jobs["test_job"] = mock_job
        
        # Run job now
        result = self.scheduler.run_job_now("test_job")
        
        # Verify job was attempted but failed
        self.assertFalse(result)
        mock_job.run.assert_called_once()
    
    def test_scheduler_properties(self):
        """Test scheduler properties."""
        # Set up scheduler state
        self.scheduler._running = True
        self.scheduler._enabled = True
        
        # Check properties
        self.assertTrue(self.scheduler.is_running)
        self.assertTrue(self.scheduler.is_enabled)
        
        # Change state
        self.scheduler._running = False
        self.scheduler._enabled = False
        
        # Check properties again
        self.assertFalse(self.scheduler.is_running)
        self.assertFalse(self.scheduler.is_enabled)
    
    def test_set_enabled(self):
        """Test setting enabled state."""
        # Start with scheduler enabled and running
        self.scheduler._enabled = True
        self.scheduler._running = True
        
        # Disable scheduler
        self.scheduler.set_enabled(False)
        
        # Verify state
        self.assertFalse(self.scheduler._enabled)
        self.assertFalse(self.scheduler._running)
        
        # Enable scheduler again
        self.scheduler.set_enabled(True)
        
        # Verify state
        self.assertTrue(self.scheduler._enabled)
        self.assertTrue(self.scheduler._running)


if __name__ == "__main__":
    unittest.main()
