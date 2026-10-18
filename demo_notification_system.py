#!/usr/bin/env python
"""
Demonstration of the Notification System

This script demonstrates the full notification workflow by:
1. Creating sample subscriptions
2. Generating sample opportunities
3. Running the notification process
4. Displaying the results
"""

import os
import sys
import json
import datetime
import time
import logging
from typing import List, Dict, Any
import tempfile
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure basic logging for demo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("demo")

# Import utility modules
from utils.subscription_manager import SubscriptionManager
from utils.notification_coordinator import NotificationCoordinator
from utils.email_sender import EmailSender


def create_sample_subscriptions(subscription_manager: SubscriptionManager) -> List[Dict[str, Any]]:
    """
    Create sample subscriptions for demonstration.
    
    Args:
        subscription_manager: Subscription manager instance
        
    Returns:
        List of created subscriptions
    """
    logger.info("Creating sample subscriptions")
    
    subscriptions = []
    
    # Subscription 1: Daily digest for bridge construction in Sydney
    subscriptions.append(
        subscription_manager.add_subscription(
            email="daily@example.com",
            name="Daily User",
            filters={
                "keywords": ["bridge", "construction"],
                "location": ["Sydney"]
            },
            notification_frequency="daily"
        )
    )
    
    # Subscription 2: Weekly digest for high-value projects in Melbourne
    subscriptions.append(
        subscription_manager.add_subscription(
            email="weekly@example.com",
            name="Weekly User",
            filters={
                "location": ["Melbourne"],
                "capital_value": {"min": 3000000}
            },
            notification_frequency="weekly"
        )
    )
    
    # Subscription 3: Immediate notifications for any Austender opportunity
    subscriptions.append(
        subscription_manager.add_subscription(
            email="immediate@example.com",
            name="Immediate User",
            filters={
                "source": "Austender"
            },
            notification_frequency="immediate"
        )
    )
    
    # Subscription 4: Daily digest for renovations in Brisbane
    subscriptions.append(
        subscription_manager.add_subscription(
            email="brisbane@example.com",
            name="Brisbane User",
            filters={
                "keywords": ["renovation"],
                "location": ["Brisbane"]
            },
            notification_frequency="daily"
        )
    )
    
    logger.info(f"Created {len(subscriptions)} sample subscriptions")
    return subscriptions


def create_sample_opportunities() -> List[Dict[str, Any]]:
    """
    Create sample opportunities for demonstration.
    
    Returns:
        List of sample opportunities
    """
    logger.info("Creating sample opportunities")
    
    # Current date for reference
    now = datetime.datetime.now()
    
    opportunities = [
        {
            "id": "opp-1",
            "title": "Sydney Harbour Bridge Maintenance",
            "description": "Regular maintenance and painting of Sydney Harbour Bridge",
            "reference_id": "ATM-2023-001",
            "source": "Austender",
            "publish_date": now.strftime("%Y-%m-%d"),
            "closing_date": (now + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "capital_value": 1500000,
            "capital_value_currency": "AUD",
            "location": "Sydney",
            "url": "https://www.tenders.gov.au/tender/ATM-2023-001"
        },
        {
            "id": "opp-2",
            "title": "Melbourne Hospital Renovation",
            "description": "Major renovation of Melbourne General Hospital",
            "reference_id": "ATM-2023-002",
            "source": "Austender",
            "publish_date": now.strftime("%Y-%m-%d"),
            "closing_date": (now + datetime.timedelta(days=45)).strftime("%Y-%m-%d"),
            "capital_value": 5000000,
            "capital_value_currency": "AUD",
            "location": "Melbourne",
            "url": "https://www.tenders.gov.au/tender/ATM-2023-002"
        },
        {
            "id": "opp-3",
            "title": "Brisbane Convention Center Renovation",
            "description": "Renovation of the Brisbane Convention Center",
            "reference_id": "ANI-2023-001",
            "source": "ANI",
            "publish_date": now.strftime("%Y-%m-%d"),
            "closing_date": (now + datetime.timedelta(days=60)).strftime("%Y-%m-%d"),
            "capital_value": 3500000,
            "capital_value_currency": "AUD",
            "location": "Brisbane",
            "url": "https://www.ani.gov.au/tender/ANI-2023-001"
        },
        {
            "id": "opp-4",
            "title": "Pedestrian Bridge Construction Perth",
            "description": "Construction of a new pedestrian bridge in Perth CBD",
            "reference_id": "ICN-2023-001",
            "source": "ICN",
            "publish_date": now.strftime("%Y-%m-%d"),
            "closing_date": (now + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "capital_value": 2000000,
            "capital_value_currency": "AUD",
            "location": "Perth",
            "url": "https://gateway.icn.org.au/tender/ICN-2023-001"
        }
    ]
    
    logger.info(f"Created {len(opportunities)} sample opportunities")
    return opportunities


def setup_demo_environment():
    """
    Set up a temporary environment for the demonstration.
    
    Returns:
        Tuple of (temp_dir, subscription_manager, notification_coordinator, email_sender)
    """
    # Create a temp directory for demo files
    temp_dir = tempfile.TemporaryDirectory()
    logger.info(f"Created temporary directory: {temp_dir.name}")
    
    # Create a subscription data file
    subscription_path = os.path.join(temp_dir.name, "subscriptions.json")
    with open(subscription_path, "w") as f:
        json.dump({}, f)
    
    # Initialize components with test configuration
    subscription_manager = SubscriptionManager(data_path=subscription_path)
    
    email_sender = EmailSender(
        smtp_server="demo-smtp.example.com",  # Mock server for demo
        smtp_port=587,
        username="demo@example.com",
        password="demo-password",
        sender="noreply@example.com"
    )
    
    notification_coordinator = NotificationCoordinator()
    
    return temp_dir, subscription_manager, notification_coordinator, email_sender


def run_notification_demo(args):
    """
    Run the notification system demonstration.
    
    Args:
        args: Command line arguments
    """
    # Parse command line arguments
    print_emails = args.print_emails
    
    logger.info("Setting up demo environment")
    temp_dir, subscription_manager, coordinator, email_sender = setup_demo_environment()
    
    try:
        # Create subscriptions
        subscriptions = create_sample_subscriptions(subscription_manager)
        
        # Create opportunities
        opportunities = create_sample_opportunities()
        
        # Get subscribers by frequency
        daily_subscribers = subscription_manager.get_subscribers_for_frequency("daily")
        weekly_subscribers = subscription_manager.get_subscribers_for_frequency("weekly")
        immediate_subscribers = subscription_manager.get_subscribers_for_frequency("immediate")
        
        logger.info(f"Subscribers: Daily={len(daily_subscribers)}, Weekly={len(weekly_subscribers)}, Immediate={len(immediate_subscribers)}")
        
        # For demo purposes, patch the email sender to capture emails instead of sending them
        sent_emails = []
        
        def mock_send_email(recipients, subject, body_html, *args, **kwargs):
            sent_emails.append({
                "recipients": recipients,
                "subject": subject,
                "body_html": body_html[:100] + "..." if body_html else ""  # Truncate for display
            })
            logger.info(f"Mock email sent: {subject} to {recipients}")
            return True
        
        # Override the send_email method
        email_sender.send_email = mock_send_email
        
        # Filter opportunities for each subscription
        logger.info("Filtering opportunities for subscriptions")
        
        email_opportunities = subscription_manager.get_emails_by_filter(opportunities)
        
        # Display matching results
        logger.info("Subscription matching results:")
        
        for email, matched_opps in email_opportunities.items():
            sub_names = [sub["name"] for sub in subscription_manager.get_subscriptions_by_email(email)]
            logger.info(f"  {email} ({', '.join(sub_names)}): {len(matched_opps)} opportunities")
            
            for opp in matched_opps:
                logger.info(f"    - {opp['title']} ({opp['location']}, {opp['source']})")
        
        # Simulate notification processing
        logger.info("Processing notifications")
        
        # Patch coordinator methods to use our variables
        coordinator._get_new_opportunities_since_last_notification = lambda x: opportunities
        
        # Process notifications for each frequency
        coordinator.process_frequency_notifications("immediate")
        coordinator.process_frequency_notifications("daily")
        coordinator.process_frequency_notifications("weekly")
        
        # Display sent emails
        if print_emails and sent_emails:
            logger.info("\nEmails that would be sent:")
            for i, email in enumerate(sent_emails, 1):
                logger.info(f"\nEmail {i}:")
                logger.info(f"  To: {', '.join(email['recipients'])}")
                logger.info(f"  Subject: {email['subject']}")
                logger.info(f"  Body: {email['body_html']}")
        
        logger.info(f"\nDemo completed successfully. {len(sent_emails)} notifications would be sent.")
        
    finally:
        # Clean up
        logger.info("Cleaning up temporary files")
        temp_dir.cleanup()


def main():
    """Main function to parse arguments and run the demo."""
    parser = argparse.ArgumentParser(description="Demonstrate the notification system")
    parser.add_argument(
        "--print-emails", 
        action="store_true",
        help="Print the content of emails that would be sent"
    )
    
    args = parser.parse_args()
    run_notification_demo(args)


if __name__ == "__main__":
    main()
