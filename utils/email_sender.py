"""
Email Notification Module

This module handles sending email notifications about new opportunities
and other important updates to subscribed users.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio
import jinja2
import datetime

# Import configuration
from config.config import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, 
    EMAIL_FROM, EMAIL_BCC
)

# Import logging and task queue
from utils.logging_config import setup_logging
from utils.task_queue import async_task

# Set up logger
logger = setup_logging(__name__)

# Set up Jinja2 template environment
template_loader = jinja2.FileSystemLoader(searchpath="./templates/email")
template_env = jinja2.Environment(loader=template_loader)


class EmailSender:
    """Email sender class for handling notification delivery."""
    
    def __init__(
        self, 
        smtp_server: str = SMTP_SERVER,
        smtp_port: int = SMTP_PORT,
        username: str = SMTP_USERNAME,
        password: str = SMTP_PASSWORD,
        sender: str = EMAIL_FROM,
        bcc: Optional[List[str]] = None
    ):
        """
        Initialize the email sender.
        
        Args:
            smtp_server (str): SMTP server address
            smtp_port (int): SMTP server port
            username (str): SMTP username
            password (str): SMTP password
            sender (str): Sender email address
            bcc (Optional[List[str]]): BCC recipients for all emails
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.bcc = bcc or []
        
        # Ensure templates directory exists
        os.makedirs("templates/email", exist_ok=True)
        
        # Create default templates if they don't exist
        self._create_default_templates()
        
        logger.info("Email sender initialized")
    
    def _create_default_templates(self) -> None:
        """Create default email templates if they don't exist."""
        templates_dir = Path("templates/email")
        
        # New opportunities template
        new_opps_template = templates_dir / "new_opportunities.html"
        if not new_opps_template.exists():
            with open(new_opps_template, "w") as f:
                f.write("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Construction Opportunities</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #2a5885;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            padding: 20px;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 5px 5px;
        }
        .opportunity {
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .title {
            font-weight: bold;
            font-size: 18px;
            color: #2a5885;
            margin-bottom: 10px;
        }
        .info {
            margin: 10px 0;
        }
        .label {
            font-weight: bold;
            display: inline-block;
            width: 120px;
        }
        .buttons {
            margin-top: 15px;
        }
        .button {
            display: inline-block;
            padding: 10px 15px;
            background-color: #2a5885;
            color: white;
            text-decoration: none;
            border-radius: 3px;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #777;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>New Construction Opportunities</h1>
        <p>{{ opportunities|length }} new opportunities found on {{ date }}</p>
    </div>
    
    <div class="content">
        <p>Hello,</p>
        <p>We've found {{ opportunities|length }} new construction opportunities that may be of interest:</p>
        
        {% for opp in opportunities %}
        <div class="opportunity">
            <div class="title">{{ opp.title }}</div>
            <div class="info"><span class="label">Source:</span> {{ opp.source }}</div>
            <div class="info"><span class="label">Reference ID:</span> {{ opp.reference_id }}</div>
            <div class="info"><span class="label">Published:</span> {{ opp.publish_date }}</div>
            <div class="info"><span class="label">Closes:</span> {{ opp.closing_date }}</div>
            <div class="info"><span class="label">Value:</span> {{ opp.capital_value_formatted }}</div>
            <div class="info"><span class="label">Location:</span> {{ opp.location }}</div>
            <div class="buttons">
                <a href="{{ base_url }}/opportunities/{{ opp.id }}" class="button">View Details</a>
            </div>
        </div>
        {% endfor %}
        
        <p>Visit our website to view all opportunities:</p>
        <p><a href="{{ base_url }}/opportunities" class="button">View All Opportunities</a></p>
        
        <div class="footer">
            <p>You're receiving this email because you're subscribed to construction opportunity updates.</p>
            <p>To unsubscribe, <a href="{{ base_url }}/unsubscribe?email={{ recipient }}">click here</a>.</p>
        </div>
    </div>
</body>
</html>
                """.strip())
            logger.info("Created default new opportunities email template")
    
    def send_email(
        self,
        recipients: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            recipients (List[str]): List of recipient email addresses
            subject (str): Email subject
            body_html (str): HTML body content
            body_text (Optional[str]): Plain text body content (auto-generated from HTML if None)
            attachments (Optional[List[Dict[str, Any]]]): List of attachments, each with 'filename' and 'content'
            cc (Optional[List[str]]): CC recipients
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not recipients:
            logger.warning("No recipients specified for email")
            return False
        
        if not self.smtp_server or not self.username or not self.password:
            logger.error("SMTP configuration missing")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender
            msg["To"] = ", ".join(recipients)
            
            if cc:
                msg["Cc"] = ", ".join(cc)
                all_recipients = recipients + cc
            else:
                all_recipients = recipients.copy()
                
            if self.bcc:
                all_recipients += self.bcc
            
            # Add plain text body
            if body_text is None:
                # Very simple HTML to text conversion
                body_text = body_html.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
                body_text = body_text.replace("<p>", "").replace("</p>", "\n\n")
                body_text = body_text.replace("<div>", "").replace("</div>", "\n")
                body_text = body_text.replace("<h1>", "").replace("</h1>", "\n\n")
                body_text = body_text.replace("<h2>", "").replace("</h2>", "\n\n")
                
                # Remove all other HTML tags
                import re
                body_text = re.sub(r"<[^>]*>", "", body_text)
            
            text_part = MIMEText(body_text, "plain")
            html_part = MIMEText(body_html, "html")
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment["filename"]
                    content = attachment["content"]
                    
                    attach_part = MIMEApplication(content)
                    attach_part.add_header(
                        "Content-Disposition", f"attachment; filename={filename}"
                    )
                    msg.attach(attach_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.sendmail(self.sender, all_recipients, msg.as_string())
            
            logger.info(f"Email sent: {subject} to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def send_new_opportunities_notification(
        self,
        opportunities: List[Dict[str, Any]],
        recipients: List[str],
        base_url: str = "http://localhost:3000",
    ) -> bool:
        """
        Send a notification about new opportunities.
        
        Args:
            opportunities (List[Dict[str, Any]]): List of opportunity data
            recipients (List[str]): List of recipient email addresses
            base_url (str): Base URL for links in the email
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not opportunities:
            logger.warning("No opportunities to include in notification")
            return False
        
        try:
            # Format opportunity data for templates
            for opp in opportunities:
                # Format dates
                if "publish_date" in opp and opp["publish_date"]:
                    if isinstance(opp["publish_date"], str):
                        opp["publish_date"] = opp["publish_date"]
                    else:
                        opp["publish_date"] = opp["publish_date"].strftime("%d/%m/%Y")
                
                if "closing_date" in opp and opp["closing_date"]:
                    if isinstance(opp["closing_date"], str):
                        opp["closing_date"] = opp["closing_date"]
                    else:
                        opp["closing_date"] = opp["closing_date"].strftime("%d/%m/%Y")
                
                # Format capital value
                if "capital_value" in opp and opp["capital_value"]:
                    currency = opp.get("capital_value_currency", "AUD")
                    opp["capital_value_formatted"] = f"${opp['capital_value']:,.2f} {currency}"
                else:
                    opp["capital_value_formatted"] = "N/A"
            
            # Get the template
            template = template_env.get_template("new_opportunities.html")
            
            # Render the template
            today = datetime.datetime.now().strftime("%d %B %Y")
            html_content = template.render(
                opportunities=opportunities,
                base_url=base_url,
                date=today,
                recipient=recipients[0] if recipients else ""
            )
            
            # Send the email
            subject = f"New Construction Opportunities - {today}"
            return self.send_email(recipients, subject, html_content)
            
        except Exception as e:
            logger.error(f"Error sending new opportunities notification: {str(e)}")
            return False


# Global email sender instance
email_sender = EmailSender()


@async_task
def send_opportunity_notification(
    opportunities: List[Dict[str, Any]],
    recipients: List[str],
    base_url: str = "http://localhost:3000",
) -> bool:
    """
    Send opportunity notification as an asynchronous task.
    
    Args:
        opportunities (List[Dict[str, Any]]): List of opportunity data
        recipients (List[str]): List of recipient email addresses
        base_url (str): Base URL for links in the email
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    return email_sender.send_new_opportunities_notification(
        opportunities, recipients, base_url
    )
