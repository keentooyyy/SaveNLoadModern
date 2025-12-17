"""
Email service for sending emails via Gmail SMTP
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_otp_email(email: str, otp_code: str, username: str = None) -> bool:
    """
    Send OTP code via email with beautiful HTML template
    
    Args:
        email: Recipient email address
        otp_code: 6-digit OTP code
        username: Optional username for personalization
    
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        subject = 'Password Reset OTP - Save N Load'
        
        from_email = settings.DEFAULT_FROM_EMAIL
        
        # Check if email is configured
        if not from_email or not settings.EMAIL_HOST_USER:
            logger.error("Email configuration is missing. Please set GMAIL_USER and GMAIL_APP_PASSWORD in environment variables.")
            return False
        
        # Create plain text version
        if username:
            greeting = f"Hello {username},"
        else:
            greeting = "Hello,"
        
        plain_message = f"""{greeting}

You have requested to reset your password for your Save N Load account.

Your OTP code is: {otp_code}

This code will expire in 10 minutes.

If you did not request this password reset, please ignore this email.

Best regards,
Save N Load Team"""
        
        # Get icon URL from external hosting (imgbb, imgur, etc.)
        # Set EMAIL_ICON_URL in environment variables with the full URL to your hosted icon
        # Example: https://i.ibb.co/xxxxx/icon.png
        import os
        icon_url = os.getenv('EMAIL_ICON_URL', '')
        
        # Fallback to local static file if no external URL is set
        if not icon_url:
            from django.templatetags.static import static
            static_path = static('images/icon.png')
            site_url = os.getenv('SITE_URL', 'http://localhost:8000')
            if not site_url.endswith('/'):
                site_url += '/'
            icon_url = f"{site_url.rstrip('/')}{static_path}"
        
        # Render HTML template
        html_message = render_to_string(
            'SaveNLoad/emails/otp_email.html',
            {
                'username': username,
                'otp_code': otp_code,
                'icon_url': icon_url,
            }
        )
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=[email]
        )
        
        # Attach HTML version
        msg.attach_alternative(html_message, "text/html")
        
        # Send email
        msg.send()
        
        logger.info(f"OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False

