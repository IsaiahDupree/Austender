"""
Subscription Management Module

This module handles user subscriptions for receiving notifications about new opportunities
based on custom filters and preferences.
"""

import os
import json
import uuid
import datetime
from typing import Dict, List, Any, Optional, Set, Union
from pathlib import Path
import logging

# Import configuration and logging
from config.config import DATA_DIR
from utils.logging_config import setup_logging

# Set up logger
logger = setup_logging(__name__)


class SubscriptionManager:
    """
    Manages user subscriptions for opportunity notifications.
    
    This class handles creating, updating, and deleting user subscriptions
    for receiving email notifications about new opportunities that match
    their specified criteria.
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the subscription manager.
        
        Args:
            data_path (Optional[str]): Path to store subscription data
                If not provided, uses DATA_DIR/subscriptions.json
        """
        # Set up data storage
        self.data_path = data_path or os.path.join(DATA_DIR, "subscriptions.json")
        self.subscriptions = {}
        self.load_subscriptions()
        
        logger.info(f"Subscription manager initialized with data path: {self.data_path}")
    
    def load_subscriptions(self) -> None:
        """Load subscriptions from file."""
        data_file = Path(self.data_path)
        
        # Create directory if it doesn't exist
        data_file.parent.mkdir(parents=True, exist_ok=True)
        
        if data_file.exists():
            try:
                with open(data_file, "r") as f:
                    self.subscriptions = json.load(f)
                logger.info(f"Loaded {len(self.subscriptions)} subscriptions")
            except Exception as e:
                logger.error(f"Error loading subscriptions: {str(e)}")
                self.subscriptions = {}
        else:
            logger.info("No subscriptions file found, starting with empty subscriptions")
            self.subscriptions = {}
    
    def save_subscriptions(self) -> None:
        """Save subscriptions to file."""
        try:
            with open(self.data_path, "w") as f:
                json.dump(self.subscriptions, f, indent=2)
            logger.info(f"Saved {len(self.subscriptions)} subscriptions")
        except Exception as e:
            logger.error(f"Error saving subscriptions: {str(e)}")
    
    def add_subscription(
        self,
        email: str,
        name: str,
        filters: Dict[str, Any],
        notification_frequency: str = "daily"
    ) -> Dict[str, Any]:
        """
        Add a new subscription.
        
        Args:
            email (str): Email address for notifications
            name (str): User's name
            filters (Dict[str, Any]): Criteria for matching opportunities
            notification_frequency (str): How often to send notifications (daily, weekly)
            
        Returns:
            Dict[str, Any]: The created subscription
        """
        # Validate parameters
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        
        if not name:
            raise ValueError("Name is required")
        
        if not isinstance(filters, dict):
            raise ValueError("Filters must be a dictionary")
        
        if notification_frequency not in ["daily", "weekly", "immediate"]:
            raise ValueError("Invalid notification frequency")
        
        # Create unique ID for the subscription
        subscription_id = str(uuid.uuid4())
        
        # Create the subscription
        subscription = {
            "id": subscription_id,
            "email": email,
            "name": name,
            "filters": filters,
            "notification_frequency": notification_frequency,
            "active": True,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "last_notification": None
        }
        
        # Store the subscription
        self.subscriptions[subscription_id] = subscription
        self.save_subscriptions()
        
        logger.info(f"Added subscription {subscription_id} for {email}")
        return subscription
    
    def update_subscription(
        self,
        subscription_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing subscription.
        
        Args:
            subscription_id (str): ID of the subscription to update
            **kwargs: Fields to update
            
        Returns:
            Optional[Dict[str, Any]]: The updated subscription, or None if not found
        """
        if subscription_id not in self.subscriptions:
            logger.warning(f"Subscription {subscription_id} not found")
            return None
        
        # Get the subscription
        subscription = self.subscriptions[subscription_id]
        
        # Update allowed fields
        allowed_fields = [
            "name", "filters", "notification_frequency", "active"
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                subscription[field] = value
        
        # Update timestamp
        subscription["updated_at"] = datetime.datetime.now().isoformat()
        
        # Save changes
        self.save_subscriptions()
        
        logger.info(f"Updated subscription {subscription_id}")
        return subscription
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """
        Delete a subscription.
        
        Args:
            subscription_id (str): ID of the subscription to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        if subscription_id not in self.subscriptions:
            logger.warning(f"Subscription {subscription_id} not found")
            return False
        
        # Remove the subscription
        del self.subscriptions[subscription_id]
        self.save_subscriptions()
        
        logger.info(f"Deleted subscription {subscription_id}")
        return True
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a subscription by ID.
        
        Args:
            subscription_id (str): ID of the subscription
            
        Returns:
            Optional[Dict[str, Any]]: The subscription, or None if not found
        """
        return self.subscriptions.get(subscription_id)
    
    def get_subscriptions_by_email(self, email: str) -> List[Dict[str, Any]]:
        """
        Get all subscriptions for an email address.
        
        Args:
            email (str): Email address
            
        Returns:
            List[Dict[str, Any]]: List of subscriptions
        """
        return [
            subscription for subscription in self.subscriptions.values()
            if subscription["email"].lower() == email.lower()
        ]
    
    def get_all_subscriptions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all subscriptions.
        
        Args:
            active_only (bool): Only return active subscriptions
            
        Returns:
            List[Dict[str, Any]]: List of subscriptions
        """
        if active_only:
            return [
                subscription for subscription in self.subscriptions.values()
                if subscription.get("active", True)
            ]
        return list(self.subscriptions.values())
    
    def get_subscribers_for_frequency(self, frequency: str) -> List[Dict[str, Any]]:
        """
        Get all subscribers for a specific notification frequency.
        
        Args:
            frequency (str): Notification frequency (daily, weekly, immediate)
            
        Returns:
            List[Dict[str, Any]]: List of subscriptions
        """
        return [
            subscription for subscription in self.subscriptions.values()
            if subscription.get("notification_frequency") == frequency
            and subscription.get("active", True)
        ]
    
    def filter_opportunities_for_subscription(
        self,
        subscription: Dict[str, Any],
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter opportunities based on subscription criteria.
        
        Args:
            subscription (Dict[str, Any]): Subscription with filters
            opportunities (List[Dict[str, Any]]): List of opportunities
            
        Returns:
            List[Dict[str, Any]]: Filtered opportunities
        """
        if not opportunities:
            return []
        
        filters = subscription.get("filters", {})
        if not filters:
            return opportunities  # No filters means all opportunities match
        
        filtered_opportunities = []
        
        for opportunity in opportunities:
            matches = True
            
            # Check each filter condition
            for field, value in filters.items():
                if field not in opportunity:
                    continue  # Skip filters for fields that don't exist
                
                # Handle different filter types based on field
                if field == "capital_value":
                    # Range filter for capital value
                    min_value = value.get("min")
                    max_value = value.get("max")
                    
                    if min_value is not None and opportunity[field] < min_value:
                        matches = False
                        break
                    
                    if max_value is not None and opportunity[field] > max_value:
                        matches = False
                        break
                
                elif field in ["location", "source"]:
                    # List filter for categorical fields
                    if isinstance(value, list) and opportunity[field] not in value:
                        matches = False
                        break
                    # String filter for exact match
                    elif isinstance(value, str) and opportunity[field] != value:
                        matches = False
                        break
                
                elif field == "keywords":
                    # Keyword search in title and description
                    if not any(
                        keyword.lower() in opportunity.get("title", "").lower() or
                        keyword.lower() in opportunity.get("description", "").lower()
                        for keyword in value
                    ):
                        matches = False
                        break
            
            if matches:
                filtered_opportunities.append(opportunity)
        
        return filtered_opportunities
    
    def mark_notification_sent(self, subscription_id: str) -> None:
        """
        Update the last notification timestamp for a subscription.
        
        Args:
            subscription_id (str): ID of the subscription
        """
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id]["last_notification"] = datetime.datetime.now().isoformat()
            self.save_subscriptions()
            logger.info(f"Updated last notification timestamp for subscription {subscription_id}")
    
    def get_emails_by_filter(self, opportunities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group opportunities by subscriber email based on subscription filters.
        
        Args:
            opportunities (List[Dict[str, Any]]): List of opportunities
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary mapping email to list of matching opportunities
        """
        result = {}
        
        # Get active subscriptions
        active_subscriptions = self.get_all_subscriptions(active_only=True)
        
        for subscription in active_subscriptions:
            email = subscription["email"]
            
            # Filter opportunities for this subscription
            matching_opportunities = self.filter_opportunities_for_subscription(
                subscription, opportunities
            )
            
            if matching_opportunities:
                # Add to result, merging with existing opportunities if needed
                if email in result:
                    # Add only new opportunities not already in the list
                    existing_ids = {opp["id"] for opp in result[email]}
                    for opp in matching_opportunities:
                        if opp["id"] not in existing_ids:
                            result[email].append(opp)
                else:
                    result[email] = matching_opportunities
                
                # Update last notification timestamp
                self.mark_notification_sent(subscription["id"])
        
        return result


# Create a singleton instance
_subscription_manager_instance = None

def get_subscription_manager() -> SubscriptionManager:
    """Get the global subscription manager instance."""
    global _subscription_manager_instance
    if _subscription_manager_instance is None:
        _subscription_manager_instance = SubscriptionManager()
    return _subscription_manager_instance

# Initialize the subscription manager
subscription_manager = get_subscription_manager()
