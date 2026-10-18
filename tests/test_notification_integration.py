"""
Integration tests for the notification system.

These tests verify that the notification components work correctly together,
including the subscription manager, email sender, and notification coordinator.
"""

import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock, call
import datetime
import time

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.subscription_manager import SubscriptionManager
from utils.email_sender import EmailSender
from utils.notification_coordinator import NotificationCoordinator
from utils.scheduler import Scheduler


class TestNotificationIntegration(unittest.TestCase):
    """Integration tests for the notification system components."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary files for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.subscription_data_path = os.path.join(self.temp_dir.name, "test_subscriptions.json")
        
        # Initialize with empty test file
        with open(self.subscription_data_path, "w") as f:
            json.dump({}, f)
        
        # Create subscription manager with test file
        self.subscription_manager = SubscriptionManager(data_path=self.subscription_data_path)
        
        # Patch dependencies to avoid actual emails/scheduling during tests
        self.email_patcher = patch('utils.email_sender.EmailSender.send_email')
        self.mock_send_email = self.email_patcher.start()
        self.mock_send_email.return_value = True
        
        self.schedule_patcher = patch('utils.scheduler.schedule')
        self.mock_schedule = self.schedule_patcher.start()
        
        # Setup email sender and notification coordinator
        self.email_sender = EmailSender(
            smtp_server="test-smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password="testpassword",
            sender="noreply@example.com"
        )
        
        self.coordinator = NotificationCoordinator()
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop any running jobs
        if hasattr(self, 'scheduler') and self.scheduler._running:
            self.scheduler.stop()
        
        # Stop patchers
        self.email_patcher.stop()
        self.schedule_patcher.stop()
        
        # Clean up temp directory
        self.temp_dir.cleanup()
    
    def _add_test_subscriptions(self):
        """Helper to add test subscriptions."""
        # Add different subscriptions
        self.subscription_manager.add_subscription(
            email="daily@example.com",
            name="Daily User",
            filters={"keywords": ["bridge", "construction"]},
            notification_frequency="daily"
        )
        
        self.subscription_manager.add_subscription(
            email="weekly@example.com",
            name="Weekly User",
            filters={"location": ["Sydney", "Melbourne"]},
            notification_frequency="weekly"
        )
        
        self.subscription_manager.add_subscription(
            email="immediate@example.com",
            name="Immediate User",
            filters={"source": "Austender"},
            notification_frequency="immediate"
        )
        
        # Add another subscription with multiple criteria
        self.subscription_manager.add_subscription(
            email="multi@example.com",
            name="Multi-Criteria User",
            filters={
                "keywords": ["renovation"],
                "location": ["Brisbane"],
                "capital_value": {"min": 1000000}
            },
            notification_frequency="daily"
        )
    
    def _create_test_opportunities(self):
        """Helper to create test opportunities."""
        return [
            {
                "id": "opp1",
                "title": "Bridge Construction Sydney",
                "description": "Building a new bridge in Sydney",
                "location": "Sydney",
                "source": "Austender",
                "reference_id": "ATM-2023-001",
                "publish_date": datetime.datetime(2023, 10, 1),
                "closing_date": datetime.datetime(2023, 11, 15),
                "capital_value": 2000000,
                "capital_value_currency": "AUD"
            },
            {
                "id": "opp2",
                "title": "Hospital Renovation Brisbane",
                "description": "Renovation of existing hospital",
                "location": "Brisbane",
                "source": "ANI",
                "reference_id": "ANI-2023-002",
                "publish_date": datetime.datetime(2023, 10, 15),
                "closing_date": datetime.datetime(2023, 12, 1),
                "capital_value": 5000000,
                "capital_value_currency": "AUD"
            },
            {
                "id": "opp3",
                "title": "School Construction Melbourne",
                "description": "Building a new school",
                "location": "Melbourne",
                "source": "Austender",
                "reference_id": "ATM-2023-003",
                "publish_date": datetime.datetime(2023, 10, 20),
                "closing_date": datetime.datetime(2023, 12, 15),
                "capital_value": 3000000,
                "capital_value_currency": "AUD"
            }
        ]
    
    @patch('utils.subscription_manager.get_subscription_manager')
    @patch('utils.email_sender.email_sender')
    def test_subscription_filtering_and_notifications(self, mock_email_sender, mock_sub_manager):
        """Test that opportunities are filtered correctly and notifications sent."""
        # Setup mocks
        mock_sub_manager.return_value = self.subscription_manager
        mock_email_sender.send_new_opportunities_notification = MagicMock(return_value=True)
        
        # Add test subscriptions
        self._add_test_subscriptions()
        
        # Create test opportunities
        opportunities = self._create_test_opportunities()
        
        # Create method to process opportunities (simulating coordinator)
        test_email_opps = self.subscription_manager.get_emails_by_filter(opportunities)
        
        # Verify filtering results
        self.assertIn("daily@example.com", test_email_opps)  # Should match "bridge construction"
        self.assertIn("weekly@example.com", test_email_opps)  # Should match Sydney and Melbourne
        self.assertIn("immediate@example.com", test_email_opps)  # Should match Austender source
        self.assertIn("multi@example.com", test_email_opps)  # Should match Brisbane renovation
        
        # Verify each subscription got the correct opportunities
        # Daily User should get the Bridge Construction (keywords match)
        daily_opps = test_email_opps["daily@example.com"]
        self.assertEqual(len(daily_opps), 1)
        self.assertEqual(daily_opps[0]["id"], "opp1")
        
        # Weekly User should get Sydney and Melbourne opportunities
        weekly_opps = test_email_opps["weekly@example.com"]
        self.assertEqual(len(weekly_opps), 2)
        self.assertIn("opp1", [o["id"] for o in weekly_opps])
        self.assertIn("opp3", [o["id"] for o in weekly_opps])
        
        # Immediate User should get Austender opportunities
        immediate_opps = test_email_opps["immediate@example.com"]
        self.assertEqual(len(immediate_opps), 2)
        self.assertIn("opp1", [o["id"] for o in immediate_opps])
        self.assertIn("opp3", [o["id"] for o in immediate_opps])
        
        # Multi-Criteria User should get Brisbane renovation
        multi_opps = test_email_opps["multi@example.com"]
        self.assertEqual(len(multi_opps), 1)
        self.assertEqual(multi_opps[0]["id"], "opp2")
    
    @patch('utils.subscription_manager.get_subscription_manager')
    @patch('utils.email_sender.send_opportunity_notification')
    def test_notification_coordinator_email_dispatch(self, mock_send_notification, mock_sub_manager):
        """Test that notification coordinator correctly dispatches emails."""
        # Setup mocks
        mock_sub_manager.return_value = self.subscription_manager
        mock_send_notification.return_value = True
        
        # Add test subscriptions
        self._add_test_subscriptions()
        
        # Create test opportunities
        opportunities = self._create_test_opportunities()
        
        # Set up coordinator with direct method call
        # (to avoid dealing with async tasks in tests)
        with patch.object(self.coordinator, '_get_new_opportunities_since_last_notification',
                         return_value=opportunities):
            # Process daily notifications
            self.coordinator._send_notifications(
                self.subscription_manager.get_emails_by_filter(opportunities)
            )
        
        # Verify emails were sent to all matching subscribers
        self.assertEqual(mock_send_notification.call_count, 4)  # One for each unique email
        
        # Check the arguments for at least one call to verify the right data is being passed
        call_args = mock_send_notification.call_args_list
        
        # Each call should have recipients and opportunities
        for call_arg in call_args:
            args, kwargs = call_arg
            self.assertTrue('opportunities' in kwargs)
            self.assertTrue('recipients' in kwargs)
            self.assertIsInstance(kwargs['opportunities'], list)
            self.assertIsInstance(kwargs['recipients'], list)
            self.assertTrue(len(kwargs['recipients']) == 1)  # One email per call
    
    @patch('utils.notification_coordinator.subscription_manager')
    @patch('utils.notification_coordinator.send_opportunity_notification')
    def test_process_frequency_notifications(self, mock_send_notification, mock_sub_manager):
        """Test processing notifications for a specific frequency."""
        # Setup mock subscription manager
        mock_sub_manager.get_subscribers_for_frequency.return_value = [
            {"id": "sub1", "email": "test@example.com", "name": "Test User"}
        ]
        mock_sub_manager.get_emails_by_filter.return_value = {
            "test@example.com": [{"id": "opp1", "title": "Test Opportunity"}]
        }
        
        # Create opportunities
        opportunities = self._create_test_opportunities()
        
        # Set up coordinator with direct method call
        with patch.object(self.coordinator, '_get_new_opportunities_since_last_notification',
                         return_value=opportunities):
            # Process daily notifications directly (not as async task)
            self.coordinator.process_frequency_notifications("daily")
        
        # Verify correct methods were called
        mock_sub_manager.get_subscribers_for_frequency.assert_called_once_with("daily")
        mock_sub_manager.get_emails_by_filter.assert_called_once()
        mock_send_notification.assert_called_once()
    
    @patch('utils.scheduler.Scheduler.add_job')
    def test_notification_tasks_scheduled(self, mock_add_job):
        """Test that notification tasks are properly scheduled."""
        # Initialize coordinator and schedule tasks
        self.coordinator.schedule_notification_tasks()
        
        # Verify scheduler added the expected jobs
        self.assertEqual(mock_add_job.call_count, 3)
        
        # Check that the correct jobs were scheduled
        job_ids = [call_args[1]['job_id'] for call_args in mock_add_job.call_args_list]
        self.assertIn("daily_notifications", job_ids)
        self.assertIn("weekly_notifications", job_ids)
        self.assertIn("check_new_opportunities", job_ids)
        
        # Verify specific job configurations
        for call_args in mock_add_job.call_args_list:
            kwargs = call_args[1]
            if kwargs['job_id'] == "daily_notifications":
                self.assertEqual(kwargs['args'], ["daily"])
                self.assertIn("run_at_specific_time", kwargs)
            elif kwargs['job_id'] == "weekly_notifications":
                self.assertEqual(kwargs['args'], ["weekly"])
                self.assertIn("run_at_specific_time", kwargs)
            elif kwargs['job_id'] == "check_new_opportunities":
                self.assertIn("interval_hours", kwargs)
    
    @patch('utils.notification_coordinator.start_notification_system')
    @patch('utils.notification_coordinator.stop_notification_system')
    @patch('fastapi.FastAPI.on_event')
    def test_api_startup_shutdown_events(self, mock_on_event, mock_stop, mock_start):
        """Test that FastAPI events correctly start and stop the notification system."""
        from api.app import app  # Import the FastAPI application
        
        # Find the startup and shutdown event handlers
        event_handlers = {}
        for call_args in mock_on_event.call_args_list:
            event_name = call_args[0][0]
            handler = call_args[0][1]
            event_handlers[event_name] = handler
        
        # Verify both event handlers were registered
        self.assertIn("startup", event_handlers)
        self.assertIn("shutdown", event_handlers)
        
        # Execute the handlers (for coverage)
        if "startup" in event_handlers and callable(event_handlers["startup"]):
            import asyncio
            asyncio.run(event_handlers["startup"]())
            mock_start.assert_called_once()
        
        if "shutdown" in event_handlers and callable(event_handlers["shutdown"]):
            import asyncio
            asyncio.run(event_handlers["shutdown"]())
            mock_stop.assert_called_once()
    
    def test_notification_system_end_to_end(self):
        """Test the notification system end-to-end (integration)."""
        # This test simulates the full flow from new opportunities to notifications
        
        # 1. Set up subscriptions
        self._add_test_subscriptions()
        
        # 2. Create new opportunities
        opportunities = self._create_test_opportunities()
        
        # 3. Set up mocks for components we don't want to actually execute
        with patch('utils.notification_coordinator.send_opportunity_notification') as mock_send:
            mock_send.return_value = True
            
            # 4. Simulate immediate notifications for a new opportunity
            self.coordinator.process_new_opportunity_immediate(opportunities[0])
            
            # 5. Verify notification was sent to immediate subscriber
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            self.assertEqual(len(kwargs['opportunities']), 1)
            self.assertEqual(kwargs['recipients'], ["immediate@example.com"])
            
            # Reset mock for next test
            mock_send.reset_mock()
            
            # 6. Simulate daily notifications
            with patch.object(self.coordinator, '_get_new_opportunities_since_last_notification',
                             return_value=opportunities):
                self.coordinator.process_frequency_notifications("daily")
            
            # 7. Verify daily notifications were sent
            self.assertTrue(mock_send.called)
            call_count = 0
            for call_args in mock_send.call_args_list:
                args, kwargs = call_args
                if "daily@example.com" in kwargs['recipients'] or "multi@example.com" in kwargs['recipients']:
                    call_count += 1
            
            # Both daily subscribers should have received notifications
            self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()
