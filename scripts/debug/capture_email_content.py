#!/usr/bin/env python3
"""
Test to capture rendered email content
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app.services.email.components.email_service import EmailService
from datetime import datetime

def capture_email_content():
    """Capture the rendered email content to a file"""
    
    app = Flask(__name__, template_folder='templates')
    app.config['MAIL_SERVER'] = 'sandbox.smtp.mailtrap.io'
    app.config['MAIL_PORT'] = 2525
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'dummy'
    app.config['MAIL_PASSWORD'] = 'dummy'
    app.config['MAIL_DEFAULT_SENDER'] = 'test@example.com'
    app.config['MAIL_FROM'] = 'test@example.com'
    
    # Monkey patch the send method to capture content
    original_send_method = None
    
    async def capture_send_method(self, message):
        """Capture email content instead of sending"""
        print("📧 Capturing email content...")
        
        # Extract content from the message
        subject = getattr(message, 'subject', 'No Subject')
        sender = getattr(message, 'From', 'Unknown Sender')
        recipients = getattr(message, 'To', 'Unknown Recipients')
        
        # Get HTML content
        html_content = None
        if hasattr(message, 'html') and message.html:
            html_content = message.html
        
        # Get text content
        text_content = None
        if hasattr(message, 'body') and message.body:
            text_content = message.body
        
        # Save to files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save HTML content
        if html_content:
            html_filename = f'/tmp/email_content_{timestamp}.html'
            with open(html_filename, 'w') as f:
                f.write(html_content)
            print(f"✅ HTML content saved to: {html_filename}")
            
            # Print first 500 chars
            print("\n📋 HTML Content Preview:")
            print("=" * 50)
            print(html_content[:500])
            if len(html_content) > 500:
                print("... (truncated)")
        
        # Save text content
        if text_content:
            text_filename = f'/tmp/email_content_{timestamp}.txt'
            with open(text_filename, 'w') as f:
                f.write(text_content)
            print(f"✅ Text content saved to: {text_filename}")
            
            print("\n📋 Text Content Preview:")
            print("=" * 50)
            print(text_content[:500])
            if len(text_content) > 500:
                print("... (truncated)")
        
        print(f"\n📧 Email Details:")
        print(f"   Subject: {subject}")
        print(f"   From: {sender}")
        print(f"   To: {recipients}")
        
        # Return success without actually sending
        return True
    
    try:
        # Create email service
        email_service = EmailService(app)
        
        # Monkey patch the send method
        original_send_method = email_service.send_email_with_retry
        email_service.send_email_with_retry = capture_send_method.__get__(email_service, EmailService)
        
        print("🔧 Testing email rendering...")
        
        # Test rendering verification email
        result = asyncio.run(email_service.send_verification_email(
            user_email="test@example.com",
            username="testuser",
            verification_token="test-token-123",
            base_url="http://127.0.0.1:5000"
        ))
        
        if result:
            print("\n✅ Email content captured successfully!")
            print("Check the files in /tmp/ for the full email content")
        else:
            print("\n❌ Failed to capture email content")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore original method if it existed
        if original_send_method and email_service:
            email_service.send_email_with_retry = original_send_method

if __name__ == "__main__":
    print("Email Content Capture Test")
    print("=" * 50)
    
    capture_email_content()