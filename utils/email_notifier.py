"""
Email Notification System
------------------------
Module that handles sending email notifications about new opportunities.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger("email_notifier")

class EmailNotifier:
    """Handles sending email notifications about new opportunities."""
    
    def __init__(self):
        """Initialize the email notifier with configuration from environment variables."""
        # SMTP configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        
        # Recipient configuration
        self.recipient_emails = os.getenv("RECIPIENT_EMAILS", "").split(",")
        
        # Check if email is configured
        self.is_configured = all([
            self.smtp_server,
            self.smtp_port,
            self.smtp_username,
            self.smtp_password,
            self.sender_email,
            len(self.recipient_emails) > 0
        ])
        
        if not self.is_configured:
            logger.warning("Email notification not fully configured. Set environment variables for SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, and RECIPIENT_EMAILS.")
    
    def send_email(self, subject: str, body_html: str, recipients: List[str] = None) -> bool:
        """
        Send an email with the given subject and HTML body.
        
        Args:
            subject: Email subject
            body_html: Email body in HTML format
            recipients: List of recipient email addresses, uses default if None
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email notification not configured, skipping")
            return False
        
        if not recipients:
            recipients = self.recipient_emails
        
        try:
            # Create the email message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipients)
            
            # Attach the HTML body
            html_part = MIMEText(body_html, "html")
            message.attach(html_part)
            
            # Connect to the SMTP server and send the email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(
                    self.sender_email,
                    recipients,
                    message.as_string()
                )
            
            logger.info(f"Email sent: {subject} to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def send_new_opportunities_notification(self, opportunities: List[Dict]) -> bool:
        """
        Send an email notification about new opportunities.
        
        Args:
            opportunities: List of new opportunity dictionaries
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not opportunities:
            logger.info("No new opportunities to notify about")
            return False
        
        # Create the email subject
        subject = f"New Government Construction Opportunities - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Create the HTML email body
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                h2 {{ color: #3498db; margin-top: 20px; }}
                .opportunity {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
                .opportunity h3 {{ margin-top: 0; color: #2c3e50; }}
                .opportunity p {{ margin: 5px 0; }}
                .meta {{ color: #7f8c8d; font-size: 0.9em; }}
                .value {{ font-weight: bold; color: #27ae60; }}
                .closing {{ font-weight: bold; color: #e74c3c; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .cta {{ display: inline-block; background-color: #3498db; color: white; padding: 10px 15px; 
                       text-decoration: none; border-radius: 5px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>New Government Construction Opportunities</h1>
                
                <div class="summary">
                    <p>We've found <strong>{len(opportunities)}</strong> new opportunities that match your criteria.</p>
                    <p>This email contains the latest opportunities from government websites including Austender, ANI, ICN, and SAM.</p>
                </div>
                
                <h2>New Opportunities</h2>
        """
        
        # Add each opportunity to the email
        for opp in opportunities:
            closing_date = opp.get("closing_date", "Not specified")
            value = f"{opp.get('value_amount', 'Not specified')} {opp.get('value_currency', 'AUD')}" if opp.get('value_amount') else "Not specified"
            
            html += f"""
                <div class="opportunity">
                    <h3>{opp.get('title', 'Untitled Opportunity')}</h3>
                    <p>{opp.get('description', '')[:200]}...</p>
                    <p><strong>Category:</strong> {opp.get('category', 'Not specified')}</p>
                    <p><strong>Source:</strong> {opp.get('source', 'Not specified')}</p>
                    <p><strong>Value:</strong> <span class="value">{value}</span></p>
                    <p><strong>Closing Date:</strong> <span class="closing">{closing_date}</span></p>
                    <p><strong>Agency:</strong> {opp.get('agency', 'Not specified')}</p>
                    <p class="meta">ID: {opp.get('id', 'Unknown')} | Added: {opp.get('last_updated', 'Unknown')}</p>
                    <a href="{opp.get('url', '#')}" class="cta">View Opportunity</a>
                </div>
            """
        
        # Close the email HTML
        html += """
                <p>Visit the website for more detailed information and to search for additional opportunities.</p>
            </div>
        </body>
        </html>
        """
        
        # Send the email
        return self.send_email(subject, html)
    
    def send_error_notification(self, error_message: str, context: Dict = None) -> bool:
        """
        Send an email notification about an error in the scraping process.
        
        Args:
            error_message: Description of the error
            context: Additional context about the error
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # Create the email subject
        subject = f"Error Alert - Government Opportunities Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Create the HTML email body
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #e74c3c; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                h2 {{ color: #3498db; margin-top: 20px; }}
                .error {{ background-color: #fef2f2; border-left: 4px solid #e74c3c; padding: 15px; margin-bottom: 15px; }}
                .context {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Scraper Error Alert</h1>
                
                <div class="error">
                    <h2>Error Message</h2>
                    <p>{error_message}</p>
                </div>
        """
        
        # Add context if provided
        if context:
            html += """
                <div class="context">
                    <h2>Error Context</h2>
                    <ul>
            """
            
            for key, value in context.items():
                html += f"<li><strong>{key}:</strong> {value}</li>"
            
            html += """
                    </ul>
                </div>
            """
        
        # Add timestamp
        html += f"""
                <p>Timestamp: {datetime.now().isoformat()}</p>
                <p>Please check the logs for more details.</p>
            </div>
        </body>
        </html>
        """
        
        # Send the email
        return self.send_email(subject, html)
