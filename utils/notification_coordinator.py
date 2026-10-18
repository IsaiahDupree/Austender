"""
Notification Coordinator Module

This module coordinates the process of scraping for new opportunities,
filtering them based on user subscriptions, and sending notifications.
"""

import datetime
import logging
from typing import Dict, List, Any, Optional, Set, Union
import json

# Import utility modules
from utils.logging_config import setup_logging
from utils.task_queue import async_task
from utils.subscription_manager import subscription_manager
from utils.email_sender import email_sender, send_opportunity_notification
from utils.scheduler import scheduler

# Import configuration
from config.config import BASE_URL

# Set up logger
logger = setup_logging(__name__)


class NotificationCoordinator:
    """
    Coordinates opportunity scraping and notification delivery.
    
    This class handles scheduling scraping tasks, processing new opportunities,
    matching them with user subscriptions, and triggering email notifications.
    """
    
    def __init__(self):
        """Initialize the notification coordinator."""
        self._last_processed_opportunities = {}
        logger.info("Notification coordinator initialized")
    
    def schedule_notification_tasks(self) -> None:
        """
        Schedule recurring notification tasks.
        
        This sets up daily and weekly notification jobs based on user preferences.
        """
        scheduler_instance = scheduler
        
        # Schedule daily notifications
        scheduler_instance.add_job(
            job_id="daily_notifications",
            func=self.process_frequency_notifications,
            run_at_specific_time="08:00",  # 8 AM
            args=["daily"]
        )
        
        # Schedule weekly notifications (every Monday at 8 AM)
        scheduler_instance.add_job(
            job_id="weekly_notifications",
            func=self.process_frequency_notifications,
            run_at_specific_time="08:00",  # 8 AM
            args=["weekly"]
        )
        
        # Schedule check for new opportunities (every 12 hours)
        scheduler_instance.add_job(
            job_id="check_new_opportunities",
            func=self.check_for_new_opportunities,
            interval_hours=12
        )
        
        logger.info("Notification tasks scheduled")
    
    @async_task
    def check_for_new_opportunities(self) -> None:
        """
        Check for new opportunities and send immediate notifications.
        
        This function is scheduled to run periodically to check for new
        opportunities and send notifications to users who have selected
        the 'immediate' notification frequency.
        """
        try:
            # This would typically call the scraper to get new opportunities
            # For now, we'll assume new_opportunities comes from elsewhere
            # new_opportunities = scraper.get_new_opportunities()
            
            # Placeholder for testing - would be replaced with actual scraped data
            logger.info("Checking for new opportunities")
            
            # Here you would call your scraper APIs to get new opportunities
            # For now we're just logging - in the real implementation you'd connect this
            # to your scrapers (austender_scraper, etc.)
            logger.info("Scraper would run here to find new opportunities")
            
            # For demonstration, let's assume we found some opportunities
            # In a real implementation, this would be replaced with actual scraper results
            
            # Process immediate notifications
            self.process_frequency_notifications("immediate")
            
        except Exception as e:
            logger.error(f"Error checking for new opportunities: {str(e)}", exc_info=True)
    
    @async_task
    def process_frequency_notifications(self, frequency: str) -> None:
        """
        Process notifications for a specific frequency.
        
        Args:
            frequency (str): Notification frequency (daily, weekly, immediate)
        """
        try:
            logger.info(f"Processing {frequency} notifications")
            
            # Get subscribers for this frequency
            subscribers = subscription_manager.get_subscribers_for_frequency(frequency)
            
            if not subscribers:
                logger.info(f"No subscribers found for {frequency} notifications")
                return
            
            # Get opportunities since last notification
            # In a real implementation, you would retrieve opportunities from your database
            # that have been created since the last notification for each subscription
            opportunities = self._get_new_opportunities_since_last_notification(frequency)
            
            if not opportunities:
                logger.info(f"No new opportunities found for {frequency} notifications")
                return
            
            # Group opportunities by subscriber based on their filters
            email_opportunities = subscription_manager.get_emails_by_filter(opportunities)
            
            # Send notifications
            self._send_notifications(email_opportunities)
            
        except Exception as e:
            logger.error(f"Error processing {frequency} notifications: {str(e)}", exc_info=True)
    
    def _get_new_opportunities_since_last_notification(self, frequency: str) -> List[Dict[str, Any]]:
        """
        Get opportunities created since the last notification for a frequency.
        
        Args:
            frequency (str): Notification frequency (daily, weekly, immediate)
            
        Returns:
            List[Dict[str, Any]]: List of new opportunities
        """
        # In a real implementation, you would query your database for opportunities
        # created since the last notification for the given frequency
        
        # Get last processed time for this frequency
        last_processed = self._last_processed_opportunities.get(frequency)
        
        # Update last processed time
        self._last_processed_opportunities[frequency] = datetime.datetime.now().isoformat()
        
        # Placeholder for testing - would be replaced with database query
        # In a real implementation, you'd query new opportunities from your database
        # based on the timestamp
        
        # Just for demonstration purposes - in real code you'd query your database
        # Something like: db.query(Opportunity).filter(Opportunity.created_at > last_processed)
        
        # Placeholder data for testing
        return [
            {
                "id": "opp-1",
                "title": "Construction of New Bridge",
                "description": "Construction of a new bridge in Sydney",
                "reference_id": "2023-12345",
                "source": "Austender",
                "publish_date": "2023-12-01",
                "closing_date": "2024-02-01",
                "capital_value": 2500000,
                "capital_value_currency": "AUD",
                "location": "Sydney",
                "url": "https://www.tenders.gov.au/tender/12345"
            },
            {
                "id": "opp-2", 
                "title": "Hospital Renovation Project",
                "description": "Major renovation of General Hospital",
                "reference_id": "2023-67890",
                "source": "Austender",
                "publish_date": "2023-12-05",
                "closing_date": "2024-03-01",
                "capital_value": 5000000,
                "capital_value_currency": "AUD",
                "location": "Melbourne",
                "url": "https://www.tenders.gov.au/tender/67890"
            }
        ]
    
    def _send_notifications(self, email_opportunities: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Send notifications to subscribers.
        
        Args:
            email_opportunities (Dict[str, List[Dict[str, Any]]]): 
                Dictionary mapping email to list of matching opportunities
        """
        for email, opportunities in email_opportunities.items():
            if not opportunities:
                continue
            
            logger.info(f"Sending notification to {email} with {len(opportunities)} opportunities")
            
            # Get subscriber name from first subscription
            subscriptions = subscription_manager.get_subscriptions_by_email(email)
            name = subscriptions[0]["name"] if subscriptions else "Subscriber"
            
            # Send email notification
            try:
                send_opportunity_notification(
                    opportunities=opportunities,
                    recipients=[email],
                    base_url=BASE_URL
                )
                logger.info(f"Notification sent to {email}")
            except Exception as e:
                logger.error(f"Error sending notification to {email}: {str(e)}")
    
    def process_new_opportunity_immediate(self, opportunity: Dict[str, Any]) -> None:
        """
        Process a single new opportunity for immediate notifications.
        
        Args:
            opportunity (Dict[str, Any]): Opportunity data
        """
        try:
            # Get subscribers for immediate notifications
            subscribers = subscription_manager.get_subscribers_for_frequency("immediate")
            
            if not subscribers:
                logger.info("No subscribers found for immediate notifications")
                return
            
            # Create a list with just this opportunity
            opportunities = [opportunity]
            
            # Group by subscriber based on filters
            email_opportunities = subscription_manager.get_emails_by_filter(opportunities)
            
            # Send notifications
            self._send_notifications(email_opportunities)
            
        except Exception as e:
            logger.error(f"Error processing immediate notification: {str(e)}")
    
    def start_coordinator(self) -> None:
        """Start the notification coordinator and its scheduled tasks."""
        # Schedule notification tasks
        self.schedule_notification_tasks()
        
        # Start the scheduler
        scheduler.start()
        
        logger.info("Notification coordinator started")
    
    def stop_coordinator(self) -> None:
        """Stop the notification coordinator and its scheduled tasks."""
        # Stop the scheduler
        scheduler.stop()
        logger.info("Notification coordinator stopped")


# Create a singleton instance
_notification_coordinator_instance = None

def get_notification_coordinator() -> NotificationCoordinator:
    """Get the global notification coordinator instance."""
    global _notification_coordinator_instance
    if _notification_coordinator_instance is None:
        _notification_coordinator_instance = NotificationCoordinator()
    return _notification_coordinator_instance

# Initialize the notification coordinator
notification_coordinator = get_notification_coordinator()


def start_notification_system() -> None:
    """Start the notification system."""
    coordinator = get_notification_coordinator()
    coordinator.start_coordinator()


def stop_notification_system() -> None:
    """Stop the notification system."""
    coordinator = get_notification_coordinator()
    coordinator.stop_coordinator()
