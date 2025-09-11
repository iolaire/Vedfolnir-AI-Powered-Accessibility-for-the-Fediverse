#!/usr/bin/env python3
"""
Test email template rendering without mail system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string

def test_template_rendering():
    """Test if email template renders correctly"""
    
    app = Flask(__name__, template_folder='templates')
    
    with app.app_context():
        try:
            # Read the template file directly
            template_path = os.path.join('templates', 'emails', 'email_verification.html')
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            # Render the template using Flask
            html_content = render_template_string(
                template_content,
                username='testuser',
                verification_url='http://127.0.0.1:5000/user-management/verify-email/test-token',
                base_url='http://127.0.0.1:5000'
            )
            
            print("✅ Template rendered successfully!")
            print(f"Template length: {len(html_content)} characters")
            print("\nFirst 500 characters:")
            print(html_content[:500])
            
            # Check if it contains expected content
            checks = [
                ('Verify Your Email', 'title'),
                ('testuser', 'username'),
                ('test-token', 'verification token'),
                ('Vedfolnir', 'app name'),
                ('<html', 'HTML structure'),
                ('</html>', 'HTML closing')
            ]
            
            print("\nContent checks:")
            all_passed = True
            for check, description in checks:
                if check in html_content:
                    print(f"✅ Contains {description}")
                else:
                    print(f"❌ Missing {description}")
                    all_passed = False
            
            return all_passed
            
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
        print("The template should render correctly in the application")
    else:
        print("❌ Template rendering test failed")
        print("There may be an issue with the template file")