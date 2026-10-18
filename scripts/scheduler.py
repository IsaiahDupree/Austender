"""
Scheduler Module

This module handles the scheduling of scraping jobs and notification delivery.
"""

import schedule
import time
import logging
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os
import threading

# Add the project root to the system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.austender_scraper import AustenderScraper
from database.models import Opportunity, setup_database
from config.config import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, 
    EMAIL_FROM, UPDATE_INTERVAL_DAYS
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.config import DATABASE_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scheduler")

# Set up database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def scrape_austender():
    """Run the Austender scraper."""
    logger.info("Starting Austender scraping job")
    
    try:
        scraper = AustenderScraper()
        scraper.run_full_scrape()
        logger.info("Austender scraping job completed successfully")
    except Exception as e:
        logger.error(f"Error during Austender scraping: {str(e)}")


def send_email_notifications():
    """Send email notifications for new opportunities."""
    logger.info("Checking for new opportunities to send notifications")
    
    try:
        # Get opportunities added in the last 24 hours
        with SessionLocal() as db:
            # Calculate the date 24 hours ago
            one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
            
            # Query for new opportunities
            new_opportunities = db.query(Opportunity).filter(
                Opportunity.created_at >= one_day_ago
            ).all()
            
            if not new_opportunities:
                logger.info("No new opportunities found for notification")
                return
            
            logger.info(f"Found {len(new_opportunities)} new opportunities for notification")
            
            # Format the email content
            email_content = format_email_content(new_opportunities)
            
            # Send the email
            send_email(
                subject="New Construction Opportunities Available",
                body=email_content,
                recipients=["developers@example.com"]  # Replace with actual recipients
            )
            
            logger.info(f"Sent notification email for {len(new_opportunities)} opportunities")
            
    except Exception as e:
        logger.error(f"Error sending email notifications: {str(e)}")


def format_email_content(opportunities):
    """
    Format a list of opportunities into HTML content for an email.
    
    Args:
        opportunities (list): List of Opportunity objects
        
    Returns:
        str: HTML-formatted email content
    """
    # Create HTML for email
    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            .opportunity { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
            .title { font-weight: bold; font-size: 18px; color: #2a5885; }
            .info { margin: 10px 0; }
            .info span { font-weight: bold; }
            .buttons { margin-top: 15px; }
            .button { display: inline-block; padding: 10px 15px; background-color: #2a5885; color: white; 
                     text-decoration: none; border-radius: 3px; margin-right: 10px; }
        </style>
    </head>
    <body>
        <h1>New Construction Opportunities</h1>
        <p>Here are the latest construction opportunities that may be of interest:</p>
    """
    
    # Add each opportunity to the email
    for opp in opportunities:
        html += f"""
        <div class="opportunity">
            <div class="title">{opp.title}</div>
            <div class="info"><span>Source:</span> {opp.source}</div>
            <div class="info"><span>Reference ID:</span> {opp.reference_id}</div>
            <div class="info"><span>Published:</span> {opp.publish_date.strftime('%d/%m/%Y') if opp.publish_date else 'N/A'}</div>
            <div class="info"><span>Closes:</span> {opp.closing_date.strftime('%d/%m/%Y') if opp.closing_date else 'N/A'}</div>
            <div class="info"><span>Value:</span> ${opp.capital_value:,.2f} {opp.capital_value_currency if opp.capital_value else 'N/A'}</div>
            <div class="info"><span>Location:</span> {opp.location or 'N/A'}</div>
            <div class="buttons">
                <a href="{opp.url}" class="button">View Details</a>
            </div>
        </div>
        """
    
    # Close the HTML
    html += """
        <p>Thank you for using our opportunity tracking service.</p>
    </body>
    </html>
    """
    
    return html


def send_email(subject, body, recipients):
    """
    Send an email to recipients.
    
    Args:
        subject (str): Email subject
        body (str): Email body (HTML)
        recipients (list): List of recipient email addresses
    """
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_FROM
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        
        # Attach the HTML body
        msg.attach(MIMEText(body, "html"))
        
        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
            
        logger.info(f"Email sent to {len(recipients)} recipients")
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")


def run_scheduler():
    """Run the scheduler."""
    # Initialize the database
    setup_database()
    
    # Schedule jobs
    
    # Run scraping job twice a month (on 1st and 15th)
    schedule.every().month.at("00:00").do(scrape_austender)
    schedule.every().month.at("00:00").day_of_month(15).do(scrape_austender)
    
    # Send email notifications every day at 9:00 AM
    schedule.every().day.at("09:00").do(send_email_notifications)
    
    logger.info("Scheduler started")
    
    # Run the scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def run_on_demand():
    """Run scraping and notifications on demand."""
    # Initialize the database
    setup_database()
    
    # Run scraping
    scrape_austender()
    
    # Send notifications
    send_email_notifications()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the opportunity scraper scheduler")
    parser.add_argument("--on-demand", action="store_true", help="Run scraping once instead of scheduling")
    
    args = parser.parse_args()
    
    if args.on_demand:
        run_on_demand()
    else:
        run_scheduler()
