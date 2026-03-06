"""Email service for sending emails via Console, SMTP, or SES."""

import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ..config import get_settings

logger = logging.getLogger(__name__)

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
        subject = "Verify your email - PushUp Pro"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #1e293b; background: #f0f4ff; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6, #a855f7); color: #ffffff; padding: 24px; text-align: center; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{ background: #ffffff; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid rgba(0,0,0,0.08); border-top: none; }}
                .otp-code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #7c3aed; text-align: center; padding: 20px; background: #f0f4ff; border-radius: 8px; margin: 20px 0; border: 2px dashed #a855f7; }}
                .footer {{ text-align: center; margin-top: 20px; color: #94a3b8; font-size: 12px; }}
                p {{ color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PushUp Pro</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    <p>Welcome to PushUp Pro! Please use the following code to verify your email address:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p>This code will expire in {settings.otp_expire_minutes} minutes.</p>
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; PushUp Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Hi {username},

Welcome to PushUp Pro! Please use the following code to verify your email address:

{otp_code}

This code will expire in {settings.otp_expire_minutes} minutes.

If you didn't create an account, you can safely ignore this email.

- PushUp Pro Team
        """

        return self.provider.send_email(to_email, subject, body_html, body_text)

    def send_password_reset_email(self, to_email: str, otp_code: str, username: str) -> bool:
        """Send password reset OTP email."""
        subject = "Reset your password - PushUp Pro"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #1e293b; background: #f0f4ff; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6, #a855f7); color: #ffffff; padding: 24px; text-align: center; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{ background: #ffffff; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid rgba(0,0,0,0.08); border-top: none; }}
                .otp-code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #7c3aed; text-align: center; padding: 20px; background: #f0f4ff; border-radius: 8px; margin: 20px 0; border: 2px dashed #a855f7; }}
                .footer {{ text-align: center; margin-top: 20px; color: #94a3b8; font-size: 12px; }}
                p {{ color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PushUp Pro</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    <p>We received a request to reset your password. Use the following code to set a new password:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p>This code will expire in {settings.otp_expire_minutes} minutes.</p>
                    <p>If you didn't request a password reset, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; PushUp Pro. All rights reserved.</p>
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

- PushUp Pro Team
        """

        return self.provider.send_email(to_email, subject, body_html, body_text)

    def send_feature_granted_email(self, to_email: str, username: str, feature_display_name: str) -> bool:
        """Send email notifying user that a feature request has been approved."""
        subject = f"Access granted: {feature_display_name} - PushUp Pro"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #1e293b; background: #f0f4ff; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6, #a855f7); color: #ffffff; padding: 24px; text-align: center; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{ background: #ffffff; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid rgba(0,0,0,0.08); border-top: none; }}
                .feature-name {{ font-size: 24px; font-weight: bold; color: #7c3aed; text-align: center; padding: 20px; background: #f0f4ff; border-radius: 8px; margin: 20px 0; border: 2px dashed #a855f7; }}
                .footer {{ text-align: center; margin-top: 20px; color: #94a3b8; font-size: 12px; }}
                p {{ color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PushUp Pro</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    <p>Great news! Your request for access to the following feature has been approved:</p>
                    <div class="feature-name">{feature_display_name}</div>
                    <p>You can start using it right away. Head over to the app and explore!</p>
                    <p>If you have any questions, feel free to reach out to us.</p>
                </div>
                <div class="footer">
                    <p>&copy; PushUp Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Hi {username},

Great news! Your request for access to the following feature has been approved:

{feature_display_name}

You can start using it right away. Head over to the app and explore!

If you have any questions, feel free to reach out to us.

- PushUp Pro Team
        """

        return self.provider.send_email(to_email, subject, body_html, body_text)

    def send_feature_review_email(
        self, to_email: str, username: str,
        feature_display_name: str, admin_message: str,
    ) -> bool:
        """Send email notifying user that their feature request is being reviewed."""
        subject = f"Update on your request: {feature_display_name} - PushUp Pro"

        # Convert newlines in admin message to <p> tags for HTML
        message_paragraphs = "".join(
            f"<p style=\"color: #1e293b; margin: 8px 0;\">{line}</p>"
            for line in admin_message.split("\n") if line.strip()
        )

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #1e293b; background: #f0f4ff; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6, #a855f7); color: #ffffff; padding: 24px; text-align: center; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{ background: #ffffff; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid rgba(0,0,0,0.08); border-top: none; }}
                .feature-name {{ font-size: 18px; font-weight: bold; color: #7c3aed; text-align: center; padding: 16px; background: #f0f4ff; border-radius: 8px; margin: 16px 0; border: 2px dashed #a855f7; }}
                .admin-message {{ background: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 0 8px 8px 0; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #94a3b8; font-size: 12px; }}
                p {{ color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PushUp Pro</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    <p>We're reviewing your request for:</p>
                    <div class="feature-name">{feature_display_name}</div>
                    <p><strong>Message from our team:</strong></p>
                    <div class="admin-message">
                        {message_paragraphs}
                    </div>
                    <p>Please reply to this email if you have any questions.</p>
                </div>
                <div class="footer">
                    <p>&copy; PushUp Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""Hi {username},

We're reviewing your request for: {feature_display_name}

Message from our team:

{admin_message}

Please reply to this email if you have any questions.

- PushUp Pro Team
        """

        return self.provider.send_email(to_email, subject, body_html, body_text)

    def notify_admins_waitlist_join(self, db, email: str, name: Optional[str] = None) -> None:
        """Notify all admins that someone joined the waitlist."""
        from ..db_models.user import User

        admins = db.query(User).filter(User.is_admin == True).all()
        if not admins:
            return

        display_name = name or "N/A"
        subject = "New waitlist signup \u2014 PushUp Pro"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #1e293b; background: #f0f4ff; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6, #a855f7); color: #ffffff; padding: 24px; text-align: center; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{ background: #ffffff; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid rgba(0,0,0,0.08); border-top: none; }}
                .detail {{ font-size: 16px; color: #7c3aed; padding: 12px; background: #f0f4ff; border-radius: 8px; margin: 16px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #94a3b8; font-size: 12px; }}
                p {{ color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PushUp Pro \u2014 Admin Alert</h1>
                </div>
                <div class="content">
                    <p>A new user has joined the waitlist:</p>
                    <div class="detail">
                        <strong>Email:</strong> {email}<br>
                        <strong>Name:</strong> {display_name}
                    </div>
                    <p>Review and approve from the <strong>Admin Panel \u2192 Waitlist</strong> tab.</p>
                </div>
                <div class="footer">
                    <p>&copy; PushUp Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""New waitlist signup \u2014 PushUp Pro

Email: {email}
Name: {display_name}

Review and approve from the Admin Panel \u2192 Waitlist tab.
"""

        for admin in admins:
            try:
                self.provider.send_email(admin.email, subject, body_html, body_text)
            except Exception as e:
                logger.warning(f"Failed to send waitlist notification to {admin.email}: {e}")

    def notify_admins_feature_request(self, db, username: str, email: str, feature_name: str) -> None:
        """Notify all admins that a user submitted a feature request."""
        from ..db_models.user import User

        admins = db.query(User).filter(User.is_admin == True).all()
        if not admins:
            return

        subject = f"Feature request: {feature_name} \u2014 PushUp Pro"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #1e293b; background: #f0f4ff; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6, #a855f7); color: #ffffff; padding: 24px; text-align: center; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .content {{ background: #ffffff; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid rgba(0,0,0,0.08); border-top: none; }}
                .detail {{ font-size: 16px; color: #7c3aed; padding: 12px; background: #f0f4ff; border-radius: 8px; margin: 16px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #94a3b8; font-size: 12px; }}
                p {{ color: #64748b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PushUp Pro \u2014 Admin Alert</h1>
                </div>
                <div class="content">
                    <p>A user has requested access to a feature:</p>
                    <div class="detail">
                        <strong>Feature:</strong> {feature_name}<br>
                        <strong>User:</strong> {username}<br>
                        <strong>Email:</strong> {email}
                    </div>
                    <p>Review and approve from the <strong>Admin Panel \u2192 Feature Requests</strong> tab.</p>
                </div>
                <div class="footer">
                    <p>&copy; PushUp Pro. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""Feature request: {feature_name} \u2014 PushUp Pro

User: {username}
Email: {email}
Feature: {feature_name}

Review and approve from the Admin Panel \u2192 Feature Requests tab.
"""

        for admin in admins:
            try:
                self.provider.send_email(admin.email, subject, body_html, body_text)
            except Exception as e:
                logger.warning(f"Failed to send feature request notification to {admin.email}: {e}")


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get singleton email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
