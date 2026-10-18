"""
Subscription API Endpoints

This module defines the API endpoints for managing opportunity subscriptions.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, validator
import datetime

# Import utility modules
from utils.subscription_manager import subscription_manager
from utils.security import validate_api_key
from utils.logging_config import setup_logging

# Set up logger
logger = setup_logging(__name__)

# Create router
router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
    dependencies=[Depends(validate_api_key)]
)


# Pydantic models for request and response validation
class SubscriptionFilter(BaseModel):
    """Filter criteria for subscriptions."""
    keywords: Optional[List[str]] = None
    location: Optional[Union[str, List[str]]] = None
    capital_value_min: Optional[float] = None
    capital_value_max: Optional[float] = None
    source: Optional[Union[str, List[str]]] = None
    
    @validator('keywords', 'location', 'source', pre=True)
    def ensure_list(cls, v):
        """Ensure value is a list if needed."""
        if isinstance(v, str):
            return [v]
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format used by subscription manager."""
        result = {}
        if self.keywords:
            result["keywords"] = self.keywords
        
        if self.location:
            result["location"] = self.location
        
        if self.capital_value_min is not None or self.capital_value_max is not None:
            result["capital_value"] = {}
            if self.capital_value_min is not None:
                result["capital_value"]["min"] = self.capital_value_min
            if self.capital_value_max is not None:
                result["capital_value"]["max"] = self.capital_value_max
        
        if self.source:
            result["source"] = self.source
        
        return result


class SubscriptionCreate(BaseModel):
    """Data model for creating a subscription."""
    email: EmailStr
    name: str
    filters: SubscriptionFilter
    notification_frequency: str = "daily"
    
    @validator('notification_frequency')
    def validate_frequency(cls, v):
        """Validate notification frequency."""
        if v not in ["daily", "weekly", "immediate"]:
            raise ValueError("Invalid notification frequency")
        return v


class SubscriptionUpdate(BaseModel):
    """Data model for updating a subscription."""
    name: Optional[str] = None
    filters: Optional[SubscriptionFilter] = None
    notification_frequency: Optional[str] = None
    active: Optional[bool] = None
    
    @validator('notification_frequency')
    def validate_frequency(cls, v):
        """Validate notification frequency if provided."""
        if v is not None and v not in ["daily", "weekly", "immediate"]:
            raise ValueError("Invalid notification frequency")
        return v


class SubscriptionResponse(BaseModel):
    """Data model for subscription responses."""
    id: str
    email: EmailStr
    name: str
    filters: Dict[str, Any]
    notification_frequency: str
    active: bool
    created_at: str
    updated_at: str
    last_notification: Optional[str] = None


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(subscription: SubscriptionCreate):
    """
    Create a new subscription for opportunity notifications.
    
    Args:
        subscription: Subscription data
        
    Returns:
        The created subscription
    """
    try:
        result = subscription_manager.add_subscription(
            email=subscription.email,
            name=subscription.name,
            filters=subscription.filters.to_dict(),
            notification_frequency=subscription.notification_frequency
        )
        logger.info(f"Created subscription for {subscription.email}")
        return result
    except ValueError as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[SubscriptionResponse])
async def get_all_subscriptions(
    email: Optional[str] = Query(None, description="Filter by email address"),
    active_only: bool = Query(False, description="Only return active subscriptions")
):
    """
    Get all subscriptions, optionally filtered by email.
    
    Args:
        email: Optional email address to filter by
        active_only: Only return active subscriptions
        
    Returns:
        List of subscriptions
    """
    try:
        if email:
            result = subscription_manager.get_subscriptions_by_email(email)
            if active_only:
                result = [s for s in result if s.get("active", True)]
        else:
            result = subscription_manager.get_all_subscriptions(active_only=active_only)
        
        logger.info(f"Retrieved {len(result)} subscriptions")
        return result
    except Exception as e:
        logger.error(f"Error retrieving subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str = Path(..., description="ID of the subscription to retrieve")
):
    """
    Get a specific subscription by ID.
    
    Args:
        subscription_id: ID of the subscription
        
    Returns:
        The subscription
    """
    subscription = subscription_manager.get_subscription(subscription_id)
    if not subscription:
        logger.warning(f"Subscription {subscription_id} not found")
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    logger.info(f"Retrieved subscription {subscription_id}")
    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_update: SubscriptionUpdate,
    subscription_id: str = Path(..., description="ID of the subscription to update")
):
    """
    Update a subscription.
    
    Args:
        subscription_update: Updated subscription data
        subscription_id: ID of the subscription to update
        
    Returns:
        The updated subscription
    """
    # First check if subscription exists
    existing = subscription_manager.get_subscription(subscription_id)
    if not existing:
        logger.warning(f"Subscription {subscription_id} not found")
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Prepare update data
    update_data = {}
    
    if subscription_update.name is not None:
        update_data["name"] = subscription_update.name
    
    if subscription_update.notification_frequency is not None:
        update_data["notification_frequency"] = subscription_update.notification_frequency
    
    if subscription_update.active is not None:
        update_data["active"] = subscription_update.active
    
    if subscription_update.filters is not None:
        update_data["filters"] = subscription_update.filters.to_dict()
    
    # Update the subscription
    try:
        result = subscription_manager.update_subscription(
            subscription_id=subscription_id,
            **update_data
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        logger.info(f"Updated subscription {subscription_id}")
        return result
    
    except Exception as e:
        logger.error(f"Error updating subscription {subscription_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: str = Path(..., description="ID of the subscription to delete")
):
    """
    Delete a subscription.
    
    Args:
        subscription_id: ID of the subscription to delete
        
    Returns:
        Confirmation message
    """
    success = subscription_manager.delete_subscription(subscription_id)
    if not success:
        logger.warning(f"Subscription {subscription_id} not found")
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    logger.info(f"Deleted subscription {subscription_id}")
    return {"message": "Subscription deleted"}


# Add missing imports
from typing import Union  # Add at the top of the file with other imports
