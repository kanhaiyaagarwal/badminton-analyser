"""Email service for sending emails via Console, SMTP, or SES."""

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ..config import get_settings

settings = get_settings()


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    def send_email(self, to_email: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
        """Send an email. Returns True on success, False on failure."""
        pass


class ConsoleEmailProvider(EmailProvider):
    """Console email provider for development - logs emails to stdout."""

    def send_email(self, to_email: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
        print("\n" + "=" * 60)
        print("EMAIL (Console Provider - Development Mode)")
        print("=" * 60)
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print("-" * 60)
        print(body_text or body_html)
        print("=" * 60 + "\n")
        return True


class SMTPEmailProvider(EmailProvider):
    """SMTP email provider for sending real emails."""

    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name

    def send_email(self, to_email: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            if body_text:
                msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            return True
        except Exception as e:
            print(f"SMTP email error: {e}")
            return False


class SESEmailProvider(EmailProvider):
    """AWS SES email provider for production environments."""

    def __init__(self):
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name
        self.region = settings.ses_region or settings.aws_region

    def send_email(self, to_email: str, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
        try:
            import boto3
            from botocore.exceptions import ClientError

            # Use explicit credentials if provided, otherwise use default credential chain (AWS CLI, IAM role, etc.)
            if settings.aws_access_key_id and settings.aws_secret_access_key and not settings.aws_access_key_id.startswith("YOUR_"):
                client = boto3.client(
                    "ses",
                    region_name=self.region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                )
            else:
                client = boto3.client("ses", region_name=self.region)

            body = {"Html": {"Charset": "UTF-8", "Data": body_html}}
            if body_text:
                body["Text"] = {"Charset": "UTF-8", "Data": body_text}

            client.send_email(
                Source=f"{self.from_name} <{self.from_email}>",
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Charset": "UTF-8", "Data": subject},
                    "Body": body,
                },
            )
            return True
        except Exception as e:
            print(f"SES email error: {e}")
            return False


def get_email_provider() -> EmailProvider:
    """Get the configured email provider."""
    provider = settings.email_provider.lower()
    if provider == "smtp":
        return SMTPEmailProvider()
    elif provider == "ses":
        return SESEmailProvider()
    else:
        return ConsoleEmailProvider()


class EmailService:
    """High-level email service for sending application emails."""

    def __init__(self):
        self.provider = get_email_provider()

    def send_otp_email(self, to_email: str, otp_code: str, username: str) -> bool:
        """Send OTP verification email."""
        subject = "Verify your email - Badminton Analyzer"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4ecca3; color: #1a1a2e; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .otp-code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #4ecca3; text-align: center; padding: 20px; background: #1a1a2e; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Badminton Analyzer</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    <p>Welcome to Badminton Analyzer! Please use the following code to verify your email address:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p>This code will expire in {settings.otp_expire_minutes} minutes.</p>
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; Badminton Analyzer. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Hi {username},

Welcome to Badminton Analyzer! Please use the following code to verify your email address:

{otp_code}

This code will expire in {settings.otp_expire_minutes} minutes.

If you didn't create an account, you can safely ignore this email.

- Badminton Analyzer Team
        """

        return self.provider.send_email(to_email, subject, body_html, body_text)

    def send_password_reset_email(self, to_email: str, otp_code: str, username: str) -> bool:
        """Send password reset OTP email."""
        subject = "Reset your password - Badminton Analyzer"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4ecca3; color: #1a1a2e; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .otp-code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #4ecca3; text-align: center; padding: 20px; background: #1a1a2e; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Badminton Analyzer</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    <p>We received a request to reset your password. Use the following code to set a new password:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p>This code will expire in {settings.otp_expire_minutes} minutes.</p>
                    <p>If you didn't request a password reset, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; Badminton Analyzer. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Hi {username},

We received a request to reset your password. Use the following code to set a new password:

{otp_code}

This code will expire in {settings.otp_expire_minutes} minutes.

If you didn't request a password reset, you can safely ignore this email.

- Badminton Analyzer Team
        """

        return self.provider.send_email(to_email, subject, body_html, body_text)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get singleton email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
