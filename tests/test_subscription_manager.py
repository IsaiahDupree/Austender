"""
Unit tests for the subscription manager module.
"""

import os
import unittest
import tempfile
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.subscription_manager import SubscriptionManager


class TestSubscriptionManager(unittest.TestCase):
    """Tests for the SubscriptionManager class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary file for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = os.path.join(self.temp_dir.name, "test_subscriptions.json")
        
        # Initialize with empty test file
        with open(self.data_path, "w") as f:
            json.dump({}, f)
        
        # Create subscription manager with test file
        self.subscription_manager = SubscriptionManager(data_path=self.data_path)
    
    def tearDown(self):
        """Clean up test environment after each test."""
        self.temp_dir.cleanup()
    
    def test_add_subscription(self):
        """Test adding a new subscription."""
        # Test data
        email = "test@example.com"
        name = "Test User"
        filters = {"keywords": ["bridge", "construction"]}
        notification_frequency = "daily"
        
        # Add subscription
        subscription = self.subscription_manager.add_subscription(
            email=email,
            name=name,
            filters=filters,
            notification_frequency=notification_frequency
        )
        
        # Verify subscription was added
        self.assertIn(subscription["id"], self.subscription_manager.subscriptions)
        self.assertEqual(subscription["email"], email)
        self.assertEqual(subscription["name"], name)
        self.assertEqual(subscription["filters"], filters)
        self.assertEqual(subscription["notification_frequency"], notification_frequency)
        self.assertTrue(subscription["active"])
        
        # Verify file was updated
        with open(self.data_path, "r") as f:
            saved_data = json.load(f)
            self.assertEqual(len(saved_data), 1)
            self.assertIn(subscription["id"], saved_data)
    
    def test_add_subscription_with_invalid_data(self):
        """Test adding a subscription with invalid data."""
        # Test with invalid email
        with self.assertRaises(ValueError):
            self.subscription_manager.add_subscription(
                email="",
                name="Test User",
                filters={"keywords": ["bridge"]}
            )
        
        # Test with invalid name
        with self.assertRaises(ValueError):
            self.subscription_manager.add_subscription(
                email="test@example.com",
                name="",
                filters={"keywords": ["bridge"]}
            )
        
        # Test with invalid filters
        with self.assertRaises(ValueError):
            self.subscription_manager.add_subscription(
                email="test@example.com",
                name="Test User",
                filters="not a dict"
            )
        
        # Test with invalid notification frequency
        with self.assertRaises(ValueError):
            self.subscription_manager.add_subscription(
                email="test@example.com",
                name="Test User",
                filters={"keywords": ["bridge"]},
                notification_frequency="invalid"
            )
    
    def test_update_subscription(self):
        """Test updating an existing subscription."""
        # Add a subscription first
        subscription = self.subscription_manager.add_subscription(
            email="test@example.com",
            name="Test User",
            filters={"keywords": ["bridge"]},
            notification_frequency="daily"
        )
        
        # Update the subscription
        updated_name = "Updated User"
        updated_filters = {"keywords": ["bridge", "renovation"]}
        updated_frequency = "weekly"
        
        updated = self.subscription_manager.update_subscription(
            subscription_id=subscription["id"],
            name=updated_name,
            filters=updated_filters,
            notification_frequency=updated_frequency
        )
        
        # Verify update
        self.assertEqual(updated["name"], updated_name)
        self.assertEqual(updated["filters"], updated_filters)
        self.assertEqual(updated["notification_frequency"], updated_frequency)
        
        # Verify subscription in manager was updated
        subscription_in_manager = self.subscription_manager.subscriptions[subscription["id"]]
        self.assertEqual(subscription_in_manager["name"], updated_name)
        self.assertEqual(subscription_in_manager["filters"], updated_filters)
        self.assertEqual(subscription_in_manager["notification_frequency"], updated_frequency)
        
        # Verify file was updated
        with open(self.data_path, "r") as f:
            saved_data = json.load(f)
            self.assertEqual(saved_data[subscription["id"]]["name"], updated_name)
    
    def test_update_nonexistent_subscription(self):
        """Test updating a subscription that doesn't exist."""
        result = self.subscription_manager.update_subscription(
            subscription_id="nonexistent",
            name="New Name"
        )
        
        self.assertIsNone(result)
    
    def test_delete_subscription(self):
        """Test deleting a subscription."""
        # Add a subscription first
        subscription = self.subscription_manager.add_subscription(
            email="test@example.com",
            name="Test User",
            filters={"keywords": ["bridge"]},
            notification_frequency="daily"
        )
        
        # Delete the subscription
        result = self.subscription_manager.delete_subscription(subscription["id"])
        
        # Verify deletion
        self.assertTrue(result)
        self.assertNotIn(subscription["id"], self.subscription_manager.subscriptions)
        
        # Verify file was updated
        with open(self.data_path, "r") as f:
            saved_data = json.load(f)
            self.assertEqual(len(saved_data), 0)
    
    def test_delete_nonexistent_subscription(self):
        """Test deleting a subscription that doesn't exist."""
        result = self.subscription_manager.delete_subscription("nonexistent")
        self.assertFalse(result)
    
    def test_get_subscription(self):
        """Test getting a specific subscription."""
        # Add a subscription first
        subscription = self.subscription_manager.add_subscription(
            email="test@example.com",
            name="Test User",
            filters={"keywords": ["bridge"]},
            notification_frequency="daily"
        )
        
        # Get the subscription
        retrieved = self.subscription_manager.get_subscription(subscription["id"])
        
        # Verify retrieval
        self.assertEqual(retrieved["id"], subscription["id"])
        self.assertEqual(retrieved["email"], subscription["email"])
        self.assertEqual(retrieved["name"], subscription["name"])
    
    def test_get_subscriptions_by_email(self):
        """Test getting subscriptions by email."""
        # Add multiple subscriptions
        email = "test@example.com"
        self.subscription_manager.add_subscription(
            email=email,
            name="Test User 1",
            filters={"keywords": ["bridge"]}
        )
        self.subscription_manager.add_subscription(
            email=email,
            name="Test User 2",
            filters={"keywords": ["renovation"]}
        )
        self.subscription_manager.add_subscription(
            email="other@example.com",
            name="Other User",
            filters={"keywords": ["construction"]}
        )
        
        # Get subscriptions by email
        subscriptions = self.subscription_manager.get_subscriptions_by_email(email)
        
        # Verify retrieval
        self.assertEqual(len(subscriptions), 2)
        self.assertTrue(all(sub["email"] == email for sub in subscriptions))
    
    def test_get_all_subscriptions(self):
        """Test getting all subscriptions."""
        # Add multiple subscriptions
        sub1 = self.subscription_manager.add_subscription(
            email="test1@example.com",
            name="Test User 1",
            filters={"keywords": ["bridge"]}
        )
        sub2 = self.subscription_manager.add_subscription(
            email="test2@example.com",
            name="Test User 2",
            filters={"keywords": ["renovation"]}
        )
        
        # Deactivate one subscription
        self.subscription_manager.update_subscription(
            subscription_id=sub2["id"],
            active=False
        )
        
        # Get all subscriptions
        all_subs = self.subscription_manager.get_all_subscriptions()
        active_subs = self.subscription_manager.get_all_subscriptions(active_only=True)
        
        # Verify retrieval
        self.assertEqual(len(all_subs), 2)
        self.assertEqual(len(active_subs), 1)
        self.assertEqual(active_subs[0]["id"], sub1["id"])
    
    def test_filter_opportunities_for_subscription(self):
        """Test filtering opportunities based on subscription criteria."""
        # Create a subscription with filters
        subscription = {
            "id": "test-sub",
            "filters": {
                "keywords": ["bridge", "construction"],
                "location": ["Sydney", "Melbourne"],
                "capital_value": {"min": 1000000, "max": 5000000}
            }
        }
        
        # Create test opportunities
        opportunities = [
            {
                "id": "opp1",
                "title": "Bridge Construction",
                "description": "Building a new bridge",
                "location": "Sydney",
                "capital_value": 2000000
            },
            {
                "id": "opp2",
                "title": "Hospital Renovation",
                "description": "Renovation of existing hospital",
                "location": "Brisbane",
                "capital_value": 3000000
            },
            {
                "id": "opp3",
                "title": "School Construction",
                "description": "Building a new school",
                "location": "Melbourne",
                "capital_value": 6000000
            },
            {
                "id": "opp4",
                "title": "Road Maintenance",
                "description": "Regular maintenance of roads",
                "location": "Sydney",
                "capital_value": 500000
            }
        ]
        
        # Filter opportunities
        filtered = self.subscription_manager.filter_opportunities_for_subscription(
            subscription, opportunities
        )
        
        # Verify filtering
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "opp1")  # Only opp1 meets all criteria
    
    def test_get_subscribers_for_frequency(self):
        """Test getting subscribers for a specific notification frequency."""
        # Add subscriptions with different frequencies
        self.subscription_manager.add_subscription(
            email="daily@example.com",
            name="Daily User",
            filters={"keywords": ["bridge"]},
            notification_frequency="daily"
        )
        self.subscription_manager.add_subscription(
            email="weekly@example.com",
            name="Weekly User",
            filters={"keywords": ["renovation"]},
            notification_frequency="weekly"
        )
        self.subscription_manager.add_subscription(
            email="immediate@example.com",
            name="Immediate User",
            filters={"keywords": ["construction"]},
            notification_frequency="immediate"
        )
        
        # Get subscribers by frequency
        daily = self.subscription_manager.get_subscribers_for_frequency("daily")
        weekly = self.subscription_manager.get_subscribers_for_frequency("weekly")
        immediate = self.subscription_manager.get_subscribers_for_frequency("immediate")
        
        # Verify retrieval
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily[0]["email"], "daily@example.com")
        
        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly[0]["email"], "weekly@example.com")
        
        self.assertEqual(len(immediate), 1)
        self.assertEqual(immediate[0]["email"], "immediate@example.com")


if __name__ == "__main__":
    unittest.main()
