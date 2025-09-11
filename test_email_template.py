#!/usr/bin/env python3
"""
Test email template rendering
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app.services.email.components.email_service import EmailService

def test_template_rendering():
    """Test if email template renders correctly"""
    
    app = Flask(__name__, template_folder='templates')
    app.config['MAIL_SERVER'] = 'localhost'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = ''
    app.config['MAIL_PASSWORD'] = ''
    app.config['MAIL_DEFAULT_SENDER'] = 'test@example.com'
    
    email_service = EmailService(app)
    
    # Test rendering the email verification template
    try:
        html_content = email_service.render_template(
            'email_verification.html',
            username='testuser',
            verification_url='http://127.0.0.1:5000/user-management/verify-email/test-token',
            base_url='http://127.0.0.1:5000'
        )
        
        print("✅ Template rendered successfully!")
        print(f"Template length: {len(html_content)} characters")
        print("\nFirst 500 characters:")
        print(html_content[:500])
        
        # Check if it contains expected content
        if 'Verify Your Email' in html_content:
            print("\n✅ Contains expected title")
        else:
            print("\n❌ Missing expected title")
            
        if 'testuser' in html_content:
            print("✅ Contains username")
        else:
            print("❌ Missing username")
            
        if 'test-token' in html_content:
            print("✅ Contains verification token")
        else:
            print("❌ Missing verification token")
            
        return True
        
    except Exception as e:
        print(f"❌ Error rendering template: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing email template rendering...")
    print("=" * 50)
    
    success = test_template_rendering()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Template rendering test passed")
    else:
        print("❌ Template rendering test failed")
        print("This suggests templates are falling back to the basic template")