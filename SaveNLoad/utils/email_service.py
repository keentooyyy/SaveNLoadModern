"""
Email service for sending emails via Gmail SMTP
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


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
            print("ERROR: Email configuration is missing. Please set GMAIL_USER and GMAIL_APP_PASSWORD in environment variables.")
            return False
        
        # Check if password is configured
        if not settings.EMAIL_HOST_PASSWORD:
            print("ERROR: GMAIL_APP_PASSWORD is not set in environment variables. You need a Gmail App Password (not your regular password).")
            return False
        
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
        
        # Create email message with HTML content
        msg = EmailMultiAlternatives(
            subject=subject,
            body=html_message,  # Use HTML as body
            from_email=from_email,
            to=[email]
        )
        
        # Set content type to HTML
        msg.content_subtype = "html"
        
        # Send email
        msg.send()
        
        print(f"OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: Failed to send OTP email to {email}: {error_msg}")
        
        # Provide helpful error messages for common Gmail issues
        if "535" in error_msg or "BadCredentials" in error_msg or "Username and Password not accepted" in error_msg:
            print(
                "GMAIL AUTHENTICATION ERROR: Gmail rejected the credentials.\n"
                "SOLUTION:\n"
                "1. Make sure you're using a Gmail App Password (NOT your regular Gmail password)\n"
                "2. Enable 2-Step Verification on your Google account\n"
                "3. Generate an App Password: https://myaccount.google.com/apppasswords\n"
                "4. Use the 16-character App Password (no spaces) in GMAIL_APP_PASSWORD\n"
                "5. Make sure GMAIL_USER is your full Gmail address (e.g., yourname@gmail.com)"
            )
        elif "534" in error_msg or "Application-specific password required" in error_msg:
            print(
                "GMAIL ERROR: Application-specific password required.\n"
                "Generate an App Password at: https://myaccount.google.com/apppasswords"
            )
        
        return False

