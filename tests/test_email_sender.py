"""
Unit tests for the email sender module.
"""

import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock, mock_open
import smtplib
import datetime

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.email_sender import EmailSender


class TestEmailSender(unittest.TestCase):
    """Tests for the EmailSender class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Test configuration
        self.smtp_server = "test-smtp.example.com"
        self.smtp_port = 587
        self.username = "test@example.com"
        self.password = "testpassword"
        self.sender = "noreply@example.com"
        self.bcc = ["admin@example.com"]
        
        # Create email sender with test config
        self.email_sender = EmailSender(
            smtp_server=self.smtp_server,
            smtp_port=self.smtp_port,
            username=self.username,
            password=self.password,
            sender=self.sender,
            bcc=self.bcc
        )
    
    @patch('os.makedirs')
    @patch('utils.email_sender.open', new_callable=mock_open)
    def test_create_default_templates(self, mock_file, mock_makedirs):
        """Test creation of default email templates."""
        # Call the method
        self.email_sender._create_default_templates()
        
        # Verify directories are created
        mock_makedirs.assert_called_once_with("templates/email", exist_ok=True)
        
        # Verify template file is written
        mock_file.assert_called_with("templates/email/new_opportunities.html", "w")
        
        # Verify template content is written
        handle = mock_file()
        self.assertTrue(handle.write.called)
        # Check that the template content contains expected elements
        write_args = handle.write.call_args[0][0]
        self.assertIn("New Construction Opportunities", write_args)
        self.assertIn("<html>", write_args)
        self.assertIn("{{ opportunities|length }}", write_args)
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending."""
        # Configure mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Test data
        recipients = ["recipient@example.com"]
        subject = "Test Subject"
        body_html = "<html><body><p>Test Body</p></body></html>"
        
        # Send email
        result = self.email_sender.send_email(recipients, subject, body_html)
        
        # Verify SMTP connection setup
        mock_smtp.assert_called_once_with(self.smtp_server, self.smtp_port)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(self.username, self.password)
        
        # Verify email sending
        self.assertTrue(mock_server.sendmail.called)
        sendmail_args = mock_server.sendmail.call_args[0]
        self.assertEqual(sendmail_args[0], self.sender)  # From
        self.assertEqual(sendmail_args[1], recipients + self.bcc)  # To + BCC
        self.assertIn(subject, sendmail_args[2])  # Email content contains subject
        self.assertIn(body_html, sendmail_args[2])  # Email content contains HTML body
        
        # Verify result
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    def test_send_email_with_attachments(self, mock_smtp):
        """Test sending email with attachments."""
        # Configure mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Test data
        recipients = ["recipient@example.com"]
        subject = "Test Subject"
        body_html = "<html><body><p>Test Body</p></body></html>"
        attachments = [
            {"filename": "test.pdf", "content": b"test pdf content"},
            {"filename": "test.docx", "content": b"test docx content"}
        ]
        
        # Send email
        result = self.email_sender.send_email(
            recipients, subject, body_html, attachments=attachments
        )
        
        # Verify email sending
        self.assertTrue(mock_server.sendmail.called)
        sendmail_args = mock_server.sendmail.call_args[0]
        
        # Verify attachments are included
        email_content = sendmail_args[2]
        for attachment in attachments:
            self.assertIn(attachment["filename"], email_content)
        
        # Verify result
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    def test_send_email_with_cc(self, mock_smtp):
        """Test sending email with CC recipients."""
        # Configure mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Test data
        recipients = ["recipient@example.com"]
        cc = ["cc@example.com"]
        subject = "Test Subject"
        body_html = "<html><body><p>Test Body</p></body></html>"
        
        # Send email
        result = self.email_sender.send_email(
            recipients, subject, body_html, cc=cc
        )
        
        # Verify email sending
        self.assertTrue(mock_server.sendmail.called)
        sendmail_args = mock_server.sendmail.call_args[0]
        
        # Verify CC is included in recipients
        self.assertEqual(sendmail_args[1], recipients + cc + self.bcc)
        
        # Verify CC header is present
        self.assertIn("Cc: cc@example.com", sendmail_args[2])
        
        # Verify result
        self.assertTrue(result)
    
    def test_send_email_no_recipients(self):
        """Test sending email with no recipients."""
        result = self.email_sender.send_email([], "Subject", "Body")
        self.assertFalse(result)
    
    def test_send_email_no_smtp_config(self):
        """Test sending email with missing SMTP configuration."""
        # Create email sender with missing config
        email_sender = EmailSender(
            smtp_server="",
            smtp_port=587,
            username="",
            password="",
            sender="test@example.com"
        )
        
        result = email_sender.send_email(
            ["test@example.com"], "Subject", "Body"
        )
        
        self.assertFalse(result)
    
    @patch('smtplib.SMTP')
    def test_send_email_smtp_error(self, mock_smtp):
        """Test handling of SMTP errors."""
        # Configure mock to raise an exception
        mock_smtp.return_value.__enter__.side_effect = smtplib.SMTPException("SMTP Error")
        
        # Test data
        recipients = ["recipient@example.com"]
        subject = "Test Subject"
        body_html = "<html><body><p>Test Body</p></body></html>"
        
        # Send email and verify it handles the error
        result = self.email_sender.send_email(recipients, subject, body_html)
        self.assertFalse(result)
    
    @patch('utils.email_sender.EmailSender.send_email')
    @patch('utils.email_sender.template_env.get_template')
    def test_send_new_opportunities_notification(self, mock_get_template, mock_send_email):
        """Test sending new opportunities notification."""
        # Configure mocks
        mock_template = MagicMock()
        mock_get_template.return_value = mock_template
        mock_template.render.return_value = "<html>Rendered Template</html>"
        mock_send_email.return_value = True
        
        # Test data
        opportunities = [
            {
                "id": "opp1",
                "title": "Bridge Construction",
                "source": "Austender",
                "reference_id": "ATM-2023-001",
                "publish_date": datetime.datetime(2023, 10, 1),
                "closing_date": datetime.datetime(2023, 11, 15),
                "capital_value": 2000000,
                "capital_value_currency": "AUD",
                "location": "Sydney"
            },
            {
                "id": "opp2",
                "title": "Hospital Renovation",
                "source": "ANI",
                "reference_id": "ANI-2023-002",
                "publish_date": "2023-10-15",  # Test string date
                "closing_date": "2023-12-01",  # Test string date
                "capital_value": 5000000,
                "capital_value_currency": "AUD",
                "location": "Melbourne"
            }
        ]
        recipients = ["test@example.com"]
        base_url = "https://example.com"
        
        # Send notification
        result = self.email_sender.send_new_opportunities_notification(
            opportunities, recipients, base_url
        )
        
        # Verify template rendering
        mock_get_template.assert_called_once_with("new_opportunities.html")
        self.assertTrue(mock_template.render.called)
        
        # Verify template context
        render_args = mock_template.render.call_args[1]
        self.assertEqual(render_args["opportunities"], opportunities)
        self.assertEqual(render_args["base_url"], base_url)
        self.assertTrue("date" in render_args)
        
        # Verify email sending
        mock_send_email.assert_called_once()
        send_args = mock_send_email.call_args[0]
        self.assertEqual(send_args[0], recipients)
        self.assertIn("New Construction Opportunities", send_args[1])
        self.assertEqual(send_args[2], "<html>Rendered Template</html>")
        
        # Verify result
        self.assertTrue(result)
    
    @patch('utils.email_sender.EmailSender.send_email')
    def test_send_new_opportunities_notification_no_opps(self, mock_send_email):
        """Test sending notification with no opportunities."""
        result = self.email_sender.send_new_opportunities_notification(
            [], ["test@example.com"]
        )
        
        # Verify no email is sent
        mock_send_email.assert_not_called()
        
        # Verify result
        self.assertFalse(result)
    
    @patch('utils.email_sender.EmailSender.send_email')
    @patch('utils.email_sender.template_env.get_template')
    def test_send_new_opportunities_notification_error(self, mock_get_template, mock_send_email):
        """Test handling of errors in send_new_opportunities_notification."""
        # Configure mock to raise an exception
        mock_get_template.side_effect = Exception("Template error")
        
        # Test data
        opportunities = [{"id": "opp1", "title": "Test"}]
        recipients = ["test@example.com"]
        
        # Send notification and verify it handles the error
        result = self.email_sender.send_new_opportunities_notification(
            opportunities, recipients
        )
        
        # Verify no email is sent
        mock_send_email.assert_not_called()
        
        # Verify result
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
