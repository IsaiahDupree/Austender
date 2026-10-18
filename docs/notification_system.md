# Notification System Documentation

## Overview

The notification system allows users to subscribe to alerts about new construction opportunities matching their specific criteria. The system automatically scrapes opportunities from various sources, filters them based on user preferences, and sends email notifications at the frequency chosen by each user.

## System Components

### 1. Subscription Management

The subscription system allows users to:

- Create subscriptions specifying their email, name, notification frequency, and filtering criteria
- Update existing subscriptions to change filters or notification frequency
- Deactivate/reactivate subscriptions
- Delete subscriptions

Subscription filters can include:

- Keywords in title or description
- Location of the project
- Source of the opportunity (Austender, ANI, ICN, SAM)
- Value range of the opportunity

### 2. Email Notifications

The email notification system:

- Sends HTML-formatted emails with opportunity details
- Supports three notification frequencies:
  - Immediate: Sent as soon as a matching opportunity is found
  - Daily: Daily digest of new opportunities
  - Weekly: Weekly summary of new opportunities
- Includes direct links to view opportunities on the platform
- Provides unsubscribe functionality

### 3. Scheduling System

The scheduler:
- Runs scraping jobs at regular intervals to find new opportunities
- Processes notifications based on user-selected frequencies
- Ensures timely delivery of notifications
- Runs as background tasks to avoid blocking the main application

## Technical Architecture

```ascii
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│  User Interface   │     │       API         │     │  External Sources │
│  (React Frontend) │────►│  (FastAPI Backend)│────►│  (Austender, etc) │
└───────────────────┘     └─────────┬─────────┘     └───────────────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │   Notification    │
                          │   Coordinator     │
                          └─────────┬─────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
        ┌────────▼─────────┐┌───────▼────────┐┌────────▼─────────┐
        │   Subscription   ││  Email Sender  ││     Scheduler    │
        │     Manager      ││                ││                  │
        └────────┬─────────┘└───────┬────────┘└────────┬─────────┘
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │     Database      │
                          │                   │
                          └───────────────────┘
```


## Using the System

### Setting Up Email Provider

To enable email notifications, configure the following environment variables:

- `SMTP_SERVER`: SMTP server address (e.g., smtp.gmail.com)
- `SMTP_PORT`: SMTP server port (typically 587 for TLS)
- `SMTP_USERNAME`: Email account username
- `SMTP_PASSWORD`: Email account password
- `EMAIL_FROM`: From address for notifications
- `EMAIL_BCC`: Optional BCC recipients

### Managing Subscriptions through API

The system provides REST API endpoints for managing subscriptions:

#### Create Subscription

```json
POST /subscriptions
{
  "email": "user@example.com",
  "name": "User Name",
  "filters": {
    "keywords": ["bridge", "construction"],
    "location": ["Sydney", "Melbourne"],
    "source": ["Austender"],
    "capital_value_min": 1000000,
    "capital_value_max": 5000000
  },
  "notification_frequency": "daily"
}
```

#### Get Subscriptions

```http
GET /subscriptions
GET /subscriptions?email=user@example.com
GET /subscriptions/{subscription_id}
```

#### Update Subscription

```json
PUT /subscriptions/{subscription_id}
{
  "name": "Updated Name",
  "filters": {...},
  "notification_frequency": "weekly",
  "active": true
}
```

#### Delete Subscription

```http
DELETE /subscriptions/{subscription_id}
```

### Frontend Integration

The frontend provides:

1. **Subscription Form** - For users to create new subscriptions with:
   - Contact information
   - Notification preferences
   - Filter criteria

2. **Subscription Management Page** - For viewing and managing existing subscriptions:
   - Toggle active/inactive status
   - Edit subscription details
   - Delete subscriptions

## Testing

The notification system includes comprehensive tests:

1. **Unit Tests** - Test individual components:
   - `test_subscription_manager.py` - Tests subscription storage and filtering
   - `test_email_sender.py` - Tests email composition and delivery
   - `test_scheduler.py` - Tests task scheduling functionality

2. **Integration Tests** - Test component interactions:
   - `test_notification_integration.py` - Tests the full notification flow

Run tests with:

```bash
python run_notification_tests.py
```

## Deployment Considerations

1. **Environment Variables**
   - Use `.env.development`, `.env.testing`, and `.env.production` for different environments
   - Set `ENV` variable to control which configuration is loaded

2. **Email Provider**
   - Consider rate limits of your email provider
   - For high-volume deployments, consider using a dedicated email service like SendGrid or Mailgun

3. **Scaling**
   - The notification system is designed to work with distributed task queues
   - For high loads, consider using Redis or RabbitMQ as a task broker

4. **Security**
   - API endpoints are protected with API key validation
   - Sensitive data like SMTP passwords should be stored securely
   - Email templates include unsubscribe links for compliance

## Troubleshooting

### Common Issues

1. **Emails not being sent**
   - Check SMTP configuration
   - Verify email provider allows application access
   - Check logs for SMTP errors

2. **Scheduled tasks not running**
   - Ensure `SCHEDULER_ENABLED` is set to `true`
   - Check logs for scheduler errors
   - Verify that the application started correctly

3. **Notifications not matching expected criteria**
   - Check subscription filters
   - Verify opportunity data is formatted correctly
   - Check logs for filtering errors

### Logging

The notification system logs events to:
- Console
- File: `logs/app.log`

Set log level with `LOG_LEVEL` environment variable.

## Future Enhancements

Potential improvements to consider:

1. **Analytics Dashboard** - Track notification effectiveness and user engagement
2. **AI-Enhanced Matching** - Use ML to improve opportunity matching
3. **Mobile Notifications** - Add push notifications for mobile users
4. **Personalized Templates** - Allow users to customize email templates
5. **SMS Notifications** - Add SMS notifications for urgent opportunities
