# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# User Management Troubleshooting Guide

This comprehensive troubleshooting guide addresses common issues with the Vedfolnir user management system, providing step-by-step solutions for users and administrators.

## Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Registration Issues](#registration-issues)
3. [Email Verification Problems](#email-verification-problems)
4. [Login and Authentication Issues](#login-and-authentication-issues)
5. [Profile Management Problems](#profile-management-problems)
6. [Password Reset Issues](#password-reset-issues)
7. [Role and Permission Problems](#role-and-permission-problems)
8. [Email System Issues](#email-system-issues)
9. [Session Management Problems](#session-management-problems)
10. [GDPR and Data Issues](#gdpr-and-data-issues)
11. [Admin-Specific Issues](#admin-specific-issues)
12. [System-Level Troubleshooting](#system-level-troubleshooting)
13. [Performance Issues](#performance-issues)
14. [Security Concerns](#security-concerns)
15. [Emergency Procedures](#emergency-procedures)

## Quick Diagnosis

### Common Symptoms and Quick Fixes

**"Cannot log in"**
1. Check if email is verified
2. Verify account is not locked
3. Confirm correct credentials
4. Try password reset

**"Email not received"**
1. Check spam/junk folder
2. Verify email address is correct
3. Check email system status
4. Try resending email

**"Access denied"**
1. Verify user role and permissions
2. Check if logged in correctly
3. Confirm platform selection
4. Contact administrator

**"Profile won't update"**
1. Check all required fields
2. Verify email format
3. Clear browser cache
4. Try different browser

### Diagnostic Tools

**User Account Status Check**
```bash
# Check user account status
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_TO_CHECK'
user = session.query(User).filter_by(username=username).first()

if user:
    print(f'User: {user.username}')
    print(f'Email: {user.email}')
    print(f'Email Verified: {user.email_verified}')
    print(f'Role: {user.role}')
    print(f'Active: {user.is_active}')
    print(f'Locked: {user.account_locked}')
    print(f'Failed Attempts: {user.failed_login_attempts}')
else:
    print('User not found')

session.close()
"
```

**Email System Test**
```bash
# Test email configuration
python -c "
from services.email_service import EmailService
from config import Config

config = Config()
email_service = EmailService(config)

# Test email configuration
try:
    result = email_service.test_connection()
    print(f'Email system status: {result}')
except Exception as e:
    print(f'Email system error: {e}')
"
```

## Registration Issues

### Problem: "Username already exists"

**Symptoms:**
- Error message during registration
- Cannot complete registration form
- Username field shows validation error

**Diagnosis:**
```bash
# Check if username exists
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'DISPUTED_USERNAME'
existing_user = session.query(User).filter_by(username=username).first()

if existing_user:
    print(f'Username {username} is taken by user ID {existing_user.id}')
    print(f'Email: {existing_user.email}')
    print(f'Created: {existing_user.created_at}')
else:
    print(f'Username {username} is available')

session.close()
"
```

**Solutions:**
1. **Choose Different Username**
   - Try variations of desired username
   - Add numbers or underscores
   - Use different naming convention

2. **Recover Existing Account**
   - If you own the existing account, use password reset
   - Contact administrator if account recovery needed

3. **Admin Resolution**
   - Admin can check account ownership
   - Admin can rename or delete unused accounts
   - Admin can assist with account recovery

### Problem: "Email address already in use"

**Symptoms:**
- Cannot register with email address
- Error message about duplicate email
- Registration form rejects email

**Diagnosis:**
```bash
# Check email usage
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

email = 'disputed@example.com'
existing_user = session.query(User).filter_by(email=email).first()

if existing_user:
    print(f'Email {email} is used by:')
    print(f'Username: {existing_user.username}')
    print(f'User ID: {existing_user.id}')
    print(f'Verified: {existing_user.email_verified}')
    print(f'Active: {existing_user.is_active}')
else:
    print(f'Email {email} is available')

session.close()
"
```

**Solutions:**
1. **Use Different Email**
   - Use alternative email address
   - Create new email account if needed

2. **Recover Existing Account**
   - Use "Forgot Password" if you own the account
   - Contact administrator for account recovery

3. **Admin Investigation**
   - Admin can verify account ownership
   - Admin can merge or delete duplicate accounts
   - Admin can assist with email conflicts

### Problem: Registration form validation errors

**Symptoms:**
- Form won't submit
- Multiple validation errors
- Password requirements not met

**Common Validation Issues:**

**Password Too Weak**
```
Requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one number
- At least one special character (!@#$%^&*)

Examples of valid passwords:
- MySecure123!
- Password2024#
- StrongPass$1
```

**Invalid Email Format**
- Must be valid email format (user@domain.com)
- No spaces or special characters except @ and .
- Domain must be valid format

**Username Requirements**
- 3-80 characters
- Letters, numbers, underscores, hyphens only
- Must start with letter or number
- Cannot be reserved system names

**Solutions:**
1. **Review Requirements**
   - Check each field's requirements
   - Ensure all required fields completed
   - Verify format requirements met

2. **Browser Issues**
   - Clear browser cache and cookies
   - Try different browser
   - Disable browser extensions
   - Enable JavaScript

3. **Network Issues**
   - Check internet connection
   - Try from different network
   - Disable VPN if using one

## Email Verification Problems

### Problem: Verification email not received

**Symptoms:**
- No verification email in inbox
- Cannot complete registration
- Account remains unverified

**Diagnosis Steps:**

1. **Check Email Delivery**
```bash
# Check recent email attempts
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

email = 'user@example.com'
user = session.query(User).filter_by(email=email).first()

if user:
    print(f'User: {user.username}')
    print(f'Email verified: {user.email_verified}')
    print(f'Verification sent: {user.email_verification_sent_at}')
    print(f'Token exists: {bool(user.email_verification_token)}')
else:
    print('User not found')

session.close()
"
```

2. **Check Email System Status**
```bash
# Test email system
python -c "
from services.email_service import EmailService
from config import Config

config = Config()
email_service = EmailService(config)

try:
    status = email_service.check_system_status()
    print(f'Email system operational: {status}')
except Exception as e:
    print(f'Email system error: {e}')
"
```

**Solutions:**

1. **Check Spam/Junk Folder**
   - Look in spam, junk, or promotions folder
   - Add sender to safe senders list
   - Check email filters and rules

2. **Verify Email Address**
   - Confirm email address was entered correctly
   - Check for typos in domain name
   - Verify email account is active

3. **Resend Verification Email**
   - Use "Resend verification" link on login page
   - Wait a few minutes between attempts
   - Try from different browser/device

4. **Admin Manual Verification**
```bash
# Admin can manually verify email
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_TO_VERIFY'
user = session.query(User).filter_by(username=username).first()

if user:
    user.email_verified = True
    user.email_verification_token = None
    session.commit()
    print(f'Email verified for user: {username}')
else:
    print('User not found')

session.close()
"
```

### Problem: Verification link expired or invalid

**Symptoms:**
- "Invalid token" error when clicking link
- "Link expired" message
- Cannot complete verification

**Diagnosis:**
```bash
# Check token status
python -c "
from database import DatabaseManager
from config import Config
from models import User, EmailVerificationToken
from datetime import datetime

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

token = 'TOKEN_FROM_EMAIL'
verification = session.query(EmailVerificationToken).filter_by(token=token).first()

if verification:
    print(f'Token found for user ID: {verification.user_id}')
    print(f'Created: {verification.created_at}')
    print(f'Expires: {verification.expires_at}')
    print(f'Used: {verification.used_at}')
    print(f'Expired: {verification.expires_at < datetime.utcnow()}')
else:
    print('Token not found')

session.close()
"
```

**Solutions:**

1. **Request New Verification Email**
   - Go to login page
   - Click "Resend verification email"
   - Use new link immediately

2. **Check Link Integrity**
   - Ensure complete link was copied
   - Try copying link manually
   - Open in different browser

3. **Admin Token Reset**
```bash
# Admin can generate new token
python -c "
from database import DatabaseManager
from config import Config
from models import User
from services.user_management_service import UserRegistrationService
from services.email_service import EmailService

config = Config()
db_manager = DatabaseManager(config)
email_service = EmailService(config)
registration_service = UserRegistrationService(db_manager, email_service)

username = 'USER_NEEDING_NEW_TOKEN'
session = db_manager.get_session()
user = session.query(User).filter_by(username=username).first()

if user:
    result = registration_service.send_verification_email(user.id)
    print(f'New verification email sent: {result}')
else:
    print('User not found')

session.close()
"
```

## Login and Authentication Issues

### Problem: "Invalid credentials" error

**Symptoms:**
- Cannot log in with correct credentials
- "Username or password incorrect" message
- Login form rejects input

**Diagnosis Steps:**

1. **Verify Account Status**
```bash
# Check account details
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'PROBLEM_USERNAME'
user = session.query(User).filter_by(username=username).first()

if user:
    print(f'Username: {user.username}')
    print(f'Email: {user.email}')
    print(f'Email verified: {user.email_verified}')
    print(f'Account active: {user.is_active}')
    print(f'Account locked: {user.account_locked}')
    print(f'Failed attempts: {user.failed_login_attempts}')
    print(f'Last failed: {user.last_failed_login}')
else:
    print('User not found')

session.close()
"
```

2. **Test Password Hash**
```bash
# Verify password hash (admin only)
python -c "
from werkzeug.security import check_password_hash
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'PROBLEM_USERNAME'
test_password = 'USER_PROVIDED_PASSWORD'

user = session.query(User).filter_by(username=username).first()

if user:
    password_valid = check_password_hash(user.password_hash, test_password)
    print(f'Password valid: {password_valid}')
else:
    print('User not found')

session.close()
"
```

**Solutions:**

1. **Basic Troubleshooting**
   - Verify caps lock is off
   - Check for extra spaces
   - Try typing password manually
   - Use different browser

2. **Account Issues**
   - Complete email verification if required
   - Wait for account unlock if locked
   - Contact admin if account disabled

3. **Password Reset**
   - Use "Forgot Password" link
   - Follow password reset process
   - Create new secure password

### Problem: Account locked after failed attempts

**Symptoms:**
- "Account is locked" error message
- Cannot log in even with correct credentials
- Lockout message displayed

**Diagnosis:**
```bash
# Check lockout status
python -c "
from database import DatabaseManager
from config import Config
from models import User
from datetime import datetime, timedelta

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'LOCKED_USERNAME'
user = session.query(User).filter_by(username=username).first()

if user:
    print(f'Account locked: {user.account_locked}')
    print(f'Failed attempts: {user.failed_login_attempts}')
    print(f'Last failed: {user.last_failed_login}')
    
    if user.last_failed_login:
        unlock_time = user.last_failed_login + timedelta(minutes=30)
        print(f'Auto-unlock at: {unlock_time}')
        print(f'Time remaining: {unlock_time - datetime.utcnow()}')
else:
    print('User not found')

session.close()
"
```

**Solutions:**

1. **Wait for Auto-Unlock**
   - Accounts auto-unlock after 30 minutes
   - Wait for unlock time to pass
   - Try logging in after unlock

2. **Admin Manual Unlock**
```bash
# Admin can unlock account immediately
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'LOCKED_USERNAME'
user = session.query(User).filter_by(username=username).first()

if user:
    user.account_locked = False
    user.failed_login_attempts = 0
    user.last_failed_login = None
    session.commit()
    print(f'Account unlocked for user: {username}')
else:
    print('User not found')

session.close()
"
```

3. **Password Reset**
   - Use password reset if you suspect password compromise
   - Reset will unlock account
   - Create new secure password

### Problem: Email not verified, cannot log in

**Symptoms:**
- "Please verify your email" message
- Login blocked until verification
- Verification email issues

**Solutions:**

1. **Complete Email Verification**
   - Check email for verification link
   - Click verification link
   - Try resending verification email

2. **Admin Manual Verification**
   - Contact administrator
   - Admin can manually verify email
   - Provide proof of email ownership

3. **Email Address Issues**
   - Verify email address is correct
   - Update email address if needed
   - Use different email if necessary

## Profile Management Problems

### Problem: Cannot update profile information

**Symptoms:**
- Profile form won't save
- Validation errors on profile update
- Changes don't persist

**Diagnosis:**
```bash
# Check user profile status
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

user_id = 123  # Replace with actual user ID
user = session.query(User).filter_by(id=user_id).first()

if user:
    print(f'User ID: {user.id}')
    print(f'Username: {user.username}')
    print(f'Email: {user.email}')
    print(f'First name: {user.first_name}')
    print(f'Last name: {user.last_name}')
    print(f'Email verified: {user.email_verified}')
    print(f'Account active: {user.is_active}')
else:
    print('User not found')

session.close()
"
```

**Solutions:**

1. **Form Validation Issues**
   - Check all required fields are completed
   - Verify email format if changing email
   - Ensure names don't contain invalid characters
   - Check field length limits

2. **Browser Issues**
   - Clear browser cache and cookies
   - Try different browser
   - Disable browser extensions
   - Check JavaScript is enabled

3. **Session Issues**
   - Log out and log back in
   - Check session hasn't expired
   - Try from different device

4. **Database Issues**
   - Contact administrator
   - Check database connectivity
   - Verify user permissions

### Problem: Email change not working

**Symptoms:**
- New email not updated
- Verification email not sent
- Email change process stuck

**Diagnosis:**
```bash
# Check email change status
python -c "
from database import DatabaseManager
from config import Config
from models import User, EmailVerificationToken

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

user_id = 123  # Replace with actual user ID
user = session.query(User).filter_by(id=user_id).first()

if user:
    print(f'Current email: {user.email}')
    print(f'Email verified: {user.email_verified}')
    
    # Check for pending verification tokens
    tokens = session.query(EmailVerificationToken).filter_by(user_id=user_id).all()
    for token in tokens:
        print(f'Pending verification for: {token.email}')
        print(f'Token created: {token.created_at}')
        print(f'Token expires: {token.expires_at}')
else:
    print('User not found')

session.close()
"
```

**Solutions:**

1. **Complete Verification Process**
   - Check email for verification link
   - Click verification link to confirm change
   - Check spam folder for verification email

2. **Resend Verification Email**
   - Try resending verification email
   - Wait a few minutes between attempts
   - Contact admin if emails not received

3. **Admin Email Update**
```bash
# Admin can update email directly
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

user_id = 123  # Replace with actual user ID
new_email = 'newemail@example.com'

user = session.query(User).filter_by(id=user_id).first()

if user:
    user.email = new_email
    user.email_verified = True  # Admin verification
    session.commit()
    print(f'Email updated to: {new_email}')
else:
    print('User not found')

session.close()
"
```

## Password Reset Issues

### Problem: Password reset email not received

**Symptoms:**
- No reset email in inbox
- Cannot complete password reset
- Reset process stuck

**Diagnosis:**
```bash
# Check password reset status
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

email = 'user@example.com'
user = session.query(User).filter_by(email=email).first()

if user:
    print(f'User: {user.username}')
    print(f'Reset token exists: {bool(user.password_reset_token)}')
    print(f'Reset sent at: {user.password_reset_sent_at}')
    print(f'Reset used: {user.password_reset_used}')
else:
    print('User not found with that email')

session.close()
"
```

**Solutions:**

1. **Check Email Delivery**
   - Look in spam/junk folder
   - Verify email address is correct
   - Check email account is active
   - Add sender to safe senders list

2. **Retry Password Reset**
   - Wait 5 minutes between attempts
   - Try from different browser
   - Clear browser cache

3. **Admin Password Reset**
```bash
# Admin can reset password directly
python -c "
from database import DatabaseManager
from config import Config
from models import User
from werkzeug.security import generate_password_hash

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_NEEDING_RESET'
temp_password = 'TempPass123!'

user = session.query(User).filter_by(username=username).first()

if user:
    user.password_hash = generate_password_hash(temp_password)
    user.password_reset_token = None
    user.password_reset_used = False
    session.commit()
    print(f'Password reset for {username}')
    print(f'Temporary password: {temp_password}')
    print('User should change password on next login')
else:
    print('User not found')

session.close()
"
```

### Problem: Reset link expired or invalid

**Symptoms:**
- "Invalid token" error
- "Link expired" message
- Cannot complete reset

**Solutions:**

1. **Request New Reset Link**
   - Go to forgot password page
   - Enter email address again
   - Use new link immediately

2. **Check Link Integrity**
   - Ensure complete link was copied
   - Try opening in different browser
   - Copy link manually if needed

3. **Admin Token Cleanup**
```bash
# Clean up expired tokens
python -c "
from database import DatabaseManager
from config import Config
from models import User
from datetime import datetime, timedelta

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

# Clear expired reset tokens
expired_time = datetime.utcnow() - timedelta(hours=1)
users_with_expired_tokens = session.query(User).filter(
    User.password_reset_sent_at < expired_time,
    User.password_reset_token.isnot(None)
).all()

for user in users_with_expired_tokens:
    user.password_reset_token = None
    user.password_reset_sent_at = None
    user.password_reset_used = False

session.commit()
print(f'Cleaned up {len(users_with_expired_tokens)} expired tokens')
session.close()
"
```

## Role and Permission Problems

### Problem: Access denied to features

**Symptoms:**
- "Access denied" or 403 error
- Missing menu items or buttons
- Cannot access admin features

**Diagnosis:**
```bash
# Check user role and permissions
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserRole

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_WITH_ACCESS_ISSUES'
user = session.query(User).filter_by(username=username).first()

if user:
    print(f'Username: {user.username}')
    print(f'Role: {user.role}')
    print(f'Is Admin: {user.role == UserRole.ADMIN}')
    print(f'Is Viewer: {user.role == UserRole.VIEWER}')
    print(f'Account active: {user.is_active}')
    print(f'Email verified: {user.email_verified}')
else:
    print('User not found')

session.close()
"
```

**Solutions:**

1. **Verify Expected Role**
   - Confirm what role user should have
   - Check if role assignment is correct
   - Contact admin for role changes

2. **Admin Role Assignment**
```bash
# Admin can change user role
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserRole

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_TO_PROMOTE'
new_role = UserRole.ADMIN  # or UserRole.VIEWER

user = session.query(User).filter_by(username=username).first()

if user:
    old_role = user.role
    user.role = new_role
    session.commit()
    print(f'Changed {username} role from {old_role} to {new_role}')
else:
    print('User not found')

session.close()
"
```

3. **Session Refresh**
   - Log out and log back in
   - Clear browser cache
   - Try different browser

### Problem: Platform access restrictions

**Symptoms:**
- Cannot see own platforms
- Platform data not loading
- Platform switching not working

**Diagnosis:**
```bash
# Check platform connections
python -c "
from database import DatabaseManager
from config import Config
from models import User, PlatformConnection

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_WITH_PLATFORM_ISSUES'
user = session.query(User).filter_by(username=username).first()

if user:
    platforms = session.query(PlatformConnection).filter_by(user_id=user.id).all()
    print(f'User: {user.username} (Role: {user.role})')
    print(f'Platform connections: {len(platforms)}')
    
    for platform in platforms:
        print(f'  - {platform.name} ({platform.platform_type})')
        print(f'    URL: {platform.instance_url}')
        print(f'    Active: {platform.is_active}')
else:
    print('User not found')

session.close()
"
```

**Solutions:**

1. **Check Platform Configuration**
   - Verify platforms are properly configured
   - Test platform connections
   - Update platform credentials if needed

2. **Role-Based Access**
   - Viewer users can only see own platforms
   - Admin users can see all platforms
   - Verify role is appropriate for access needs

3. **Platform Context Issues**
   - Try switching to different platform
   - Clear platform context and reselect
   - Contact admin for platform access issues

## Email System Issues

### Problem: No emails being sent

**Symptoms:**
- No verification emails received
- No password reset emails
- No notification emails

**Diagnosis:**
```bash
# Test email system configuration
python -c "
import os
from config import Config

config = Config()

print('Email Configuration:')
print(f'MAIL_SERVER: {os.getenv(\"MAIL_SERVER\", \"Not set\")}')
print(f'MAIL_PORT: {os.getenv(\"MAIL_PORT\", \"Not set\")}')
print(f'MAIL_USE_TLS: {os.getenv(\"MAIL_USE_TLS\", \"Not set\")}')
print(f'MAIL_USERNAME: {os.getenv(\"MAIL_USERNAME\", \"Not set\")}')
print(f'MAIL_PASSWORD: {\"Set\" if os.getenv(\"MAIL_PASSWORD\") else \"Not set\"}')
print(f'MAIL_DEFAULT_SENDER: {os.getenv(\"MAIL_DEFAULT_SENDER\", \"Not set\")}')
"
```

**Solutions:**

1. **Check Email Configuration**
   - Verify SMTP settings in .env file
   - Test SMTP credentials
   - Check firewall and network settings

2. **Email Service Test**
```bash
# Test email service directly
python -c "
from services.email_service import EmailService
from config import Config

config = Config()
email_service = EmailService(config)

try:
    # Test email sending
    result = email_service.send_test_email('test@example.com')
    print(f'Test email result: {result}')
except Exception as e:
    print(f'Email service error: {e}')
"
```

3. **SMTP Troubleshooting**
   - Check SMTP server is accessible
   - Verify port is not blocked
   - Test with different SMTP provider
   - Check authentication credentials

### Problem: Emails going to spam

**Symptoms:**
- Emails consistently in spam folder
- Low email delivery rates
- Users not receiving emails

**Solutions:**

1. **Email Authentication**
   - Configure SPF records
   - Set up DKIM signing
   - Configure DMARC policy
   - Use reputable SMTP provider

2. **Email Content**
   - Avoid spam trigger words
   - Use proper HTML formatting
   - Include unsubscribe links
   - Maintain good sender reputation

3. **SMTP Provider**
   - Use dedicated email service
   - Configure proper reverse DNS
   - Monitor sender reputation
   - Follow email best practices

## Session Management Problems

### Problem: Session expires too quickly

**Symptoms:**
- Frequent login prompts
- Session timeout messages
- Lost work due to session expiry

**Diagnosis:**
```bash
# Check session configuration
python -c "
import os
from config import Config

config = Config()

print('Session Configuration:')
print(f'SESSION_TIMEOUT: {os.getenv(\"SESSION_TIMEOUT\", \"7200\")} seconds')
print(f'SESSION_CLEANUP_INTERVAL: {os.getenv(\"SESSION_CLEANUP_INTERVAL\", \"3600\")} seconds')
print(f'SESSION_TOKEN_LENGTH: {os.getenv(\"SESSION_TOKEN_LENGTH\", \"32\")}')
"
```

**Solutions:**

1. **Adjust Session Timeout**
   - Increase SESSION_TIMEOUT in .env file
   - Restart application after changes
   - Balance security with usability

2. **Use Remember Me**
   - Check "Remember Me" during login
   - Creates longer-lived session
   - More convenient for trusted devices

3. **Session Configuration**
```bash
# Update session timeout (admin)
echo "SESSION_TIMEOUT=14400" >> .env  # 4 hours
echo "SESSION_CLEANUP_INTERVAL=7200" >> .env  # 2 hours
```

### Problem: Session not syncing across tabs

**Symptoms:**
- Different login status in different tabs
- Session conflicts between tabs
- Inconsistent user state

**Solutions:**

1. **Browser Issues**
   - Clear browser cache and cookies
   - Close all tabs and restart browser
   - Try different browser

2. **Session Synchronization**
   - Log out from all tabs
   - Log in again in one tab
   - Other tabs should sync automatically

3. **Database Session Check**
```bash
# Check active sessions for user
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserSession

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_WITH_SESSION_ISSUES'
user = session.query(User).filter_by(username=username).first()

if user:
    active_sessions = session.query(UserSession).filter_by(
        user_id=user.id,
        is_active=True
    ).all()
    
    print(f'Active sessions for {username}: {len(active_sessions)}')
    for sess in active_sessions:
        print(f'  Session: {sess.session_token[:8]}...')
        print(f'  Created: {sess.created_at}')
        print(f'  Last activity: {sess.last_activity}')
else:
    print('User not found')

session.close()
"
```

## GDPR and Data Issues

### Problem: Data export not working

**Symptoms:**
- Export request fails
- No download link received
- Incomplete data export

**Diagnosis:**
```bash
# Check user data for export
python -c "
from database import DatabaseManager
from config import Config
from models import User
from services.gdpr_service import GDPRService

config = Config()
db_manager = DatabaseManager(config)
gdpr_service = GDPRService(db_manager)

user_id = 123  # Replace with actual user ID

try:
    export_data = gdpr_service.export_user_data(user_id)
    print(f'Export successful: {len(export_data)} data points')
    print('Data categories:')
    for category in export_data.keys():
        print(f'  - {category}')
except Exception as e:
    print(f'Export failed: {e}')
"
```

**Solutions:**

1. **Retry Data Export**
   - Try export request again
   - Wait for processing to complete
   - Check email for download link

2. **Admin Manual Export**
   - Contact administrator
   - Admin can generate export manually
   - Provide secure delivery method

3. **Partial Export**
   - Export specific data categories
   - Use profile export for basic data
   - Contact admin for complete export

### Problem: Account deletion not working

**Symptoms:**
- Deletion request fails
- Account still active after deletion
- Data not removed

**Diagnosis:**
```bash
# Check account deletion status
python -c "
from database import DatabaseManager
from config import Config
from models import User

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_TO_DELETE'
user = session.query(User).filter_by(username=username).first()

if user:
    print(f'User still exists: {user.username}')
    print(f'Account active: {user.is_active}')
    print(f'Email: {user.email}')
    print('Deletion may have failed')
else:
    print('User not found - deletion may have succeeded')

session.close()
"
```

**Solutions:**

1. **Retry Deletion Process**
   - Go through deletion process again
   - Confirm all deletion steps
   - Verify deletion confirmation

2. **Admin Deletion**
```bash
# Admin can delete user account
python -c "
from database import DatabaseManager
from config import Config
from services.user_management_service import UserProfileService
from services.email_service import EmailService

config = Config()
db_manager = DatabaseManager(config)
email_service = EmailService(config)
profile_service = UserProfileService(db_manager, email_service)

user_id = 123  # Replace with actual user ID
admin_user_id = 1  # Replace with admin user ID

try:
    result = profile_service.delete_user_profile(user_id, admin_user_id)
    print(f'Deletion result: {result}')
except Exception as e:
    print(f'Deletion failed: {e}')
"
```

3. **GDPR Compliance Check**
   - Verify all data categories removed
   - Check cascading deletions completed
   - Confirm backup data handling

## Admin-Specific Issues

### Problem: Cannot access admin interface

**Symptoms:**
- Admin menu not visible
- 403 errors on admin pages
- Admin functions not working

**Diagnosis:**
```bash
# Verify admin status
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserRole

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'ADMIN_USERNAME'
user = session.query(User).filter_by(username=username).first()

if user:
    print(f'Username: {user.username}')
    print(f'Role: {user.role}')
    print(f'Is Admin: {user.role == UserRole.ADMIN}')
    print(f'Account active: {user.is_active}')
    print(f'Email verified: {user.email_verified}')
    print(f'Account locked: {user.account_locked}')
else:
    print('User not found')

session.close()
"
```

**Solutions:**

1. **Verify Admin Role**
   - Confirm user has ADMIN role
   - Check role assignment is correct
   - Verify account is active

2. **Grant Admin Role**
```bash
# Grant admin role to user
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserRole

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

username = 'USER_TO_MAKE_ADMIN'
user = session.query(User).filter_by(username=username).first()

if user:
    user.role = UserRole.ADMIN
    session.commit()
    print(f'Granted admin role to {username}')
else:
    print('User not found')

session.close()
"
```

3. **Session Refresh**
   - Log out and log back in
   - Clear browser cache
   - Try different browser

### Problem: Admin operations failing

**Symptoms:**
- User creation fails
- User updates don't save
- Admin functions error out

**Diagnosis:**
```bash
# Check admin service status
python -c "
from database import DatabaseManager
from config import Config
from services.user_management_service import AdminUserService
from services.email_service import EmailService

config = Config()
db_manager = DatabaseManager(config)
email_service = EmailService(config)

try:
    admin_service = AdminUserService(db_manager, email_service)
    print('Admin service initialized successfully')
    
    # Test database connection
    session = db_manager.get_session()
    session.execute('SELECT 1')
    print('Database connection working')
    session.close()
    
except Exception as e:
    print(f'Admin service error: {e}')
"
```

**Solutions:**

1. **Check Database Connection**
   - Verify database is accessible
   - Check database permissions
   - Test database connectivity

2. **Verify Admin Permissions**
   - Confirm admin has necessary permissions
   - Check session is valid
   - Verify CSRF tokens

3. **Service Restart**
   - Restart application
   - Clear application cache
   - Check for service errors

## System-Level Troubleshooting

### Problem: Database connection issues

**Symptoms:**
- Database errors in logs
- Cannot save user data
- Application crashes

**Diagnosis:**
```bash
# Test database connection
python -c "
from database import DatabaseManager
from config import Config

config = Config()

try:
    db_manager = DatabaseManager(config)
    session = db_manager.get_session()
    result = session.execute('SELECT COUNT(*) FROM users').scalar()
    print(f'Database connection successful. User count: {result}')
    session.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

**Solutions:**

1. **Check Database File**
   - Verify database file exists
   - Check file permissions
   - Ensure disk space available

2. **Database Repair**
```bash
# Check database integrity
sqlite3 storage/database/vedfolnir.db "PRAGMA integrity_check;"

# Vacuum database if needed
sqlite3 storage/database/vedfolnir.db "VACUUM;"
```

3. **Backup and Restore**
   - Restore from recent backup
   - Check backup integrity
   - Migrate data if necessary

### Problem: Application performance issues

**Symptoms:**
- Slow page loads
- Timeouts during operations
- High resource usage

**Diagnosis:**
```bash
# Check system resources
python -c "
import psutil
import os

print('System Resources:')
print(f'CPU Usage: {psutil.cpu_percent()}%')
print(f'Memory Usage: {psutil.virtual_memory().percent}%')
print(f'Disk Usage: {psutil.disk_usage(\"/\").percent}%')

# Check database size
db_path = 'storage/database/vedfolnir.db'
if os.path.exists(db_path):
    db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
    print(f'Database Size: {db_size:.2f} MB')
"
```

**Solutions:**

1. **Database Optimization**
```bash
# Optimize database
python -c "
from database import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

# Analyze query performance
session.execute('ANALYZE')
session.commit()
session.close()

print('Database optimized')
"
```

2. **Clean Up Old Data**
```bash
# Clean up expired tokens and sessions
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserSession, EmailVerificationToken
from datetime import datetime, timedelta

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

# Clean expired sessions
expired_time = datetime.utcnow() - timedelta(hours=24)
expired_sessions = session.query(UserSession).filter(
    UserSession.last_activity < expired_time
).delete()

# Clean expired tokens
expired_tokens = session.query(EmailVerificationToken).filter(
    EmailVerificationToken.expires_at < datetime.utcnow()
).delete()

session.commit()
print(f'Cleaned {expired_sessions} sessions and {expired_tokens} tokens')
session.close()
"
```

3. **System Resources**
   - Increase available memory
   - Check disk space
   - Monitor CPU usage
   - Optimize system configuration

## Performance Issues

### Problem: Slow user operations

**Symptoms:**
- Long load times for user pages
- Timeouts during user operations
- Slow database queries

**Solutions:**

1. **Database Indexing**
```bash
# Add missing indexes
python -c "
from database import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

# Add indexes for common queries
session.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
session.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
session.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
session.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)')
session.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)')

session.commit()
print('Database indexes created')
session.close()
"
```

2. **Query Optimization**
   - Review slow queries in logs
   - Optimize database queries
   - Use appropriate indexes
   - Limit result sets

3. **Caching**
   - Implement user data caching
   - Cache session information
   - Use browser caching
   - Optimize static assets

### Problem: High memory usage

**Symptoms:**
- Application using excessive memory
- Out of memory errors
- System slowdown

**Solutions:**

1. **Memory Profiling**
```bash
# Monitor memory usage
python -c "
import psutil
import os

process = psutil.Process(os.getpid())
memory_info = process.memory_info()

print(f'RSS Memory: {memory_info.rss / 1024 / 1024:.2f} MB')
print(f'VMS Memory: {memory_info.vms / 1024 / 1024:.2f} MB')
print(f'Memory Percent: {process.memory_percent():.2f}%')
"
```

2. **Session Cleanup**
   - Implement regular session cleanup
   - Remove expired sessions
   - Optimize session storage

3. **Database Connection Pooling**
   - Use connection pooling
   - Limit concurrent connections
   - Close unused connections

## Security Concerns

### Problem: Suspicious login activity

**Symptoms:**
- Multiple failed login attempts
- Logins from unusual locations
- Account lockouts

**Diagnosis:**
```bash
# Check recent login attempts
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserAuditLog

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

# Check recent failed logins
recent_failures = session.query(UserAuditLog).filter(
    UserAuditLog.action == 'login_failed'
).order_by(UserAuditLog.created_at.desc()).limit(10).all()

print('Recent failed login attempts:')
for failure in recent_failures:
    print(f'  User ID: {failure.user_id}')
    print(f'  Time: {failure.created_at}')
    print(f'  IP: {failure.ip_address}')
    print(f'  Details: {failure.details}')
    print('---')

session.close()
"
```

**Solutions:**

1. **Account Security**
   - Force password reset for affected accounts
   - Enable account monitoring
   - Review access logs

2. **IP Blocking**
   - Block suspicious IP addresses
   - Implement rate limiting
   - Monitor for patterns

3. **Security Hardening**
   - Increase password requirements
   - Implement 2FA if available
   - Monitor security events

### Problem: Potential data breach

**Symptoms:**
- Unauthorized access detected
- Data integrity issues
- Security alerts

**Emergency Response:**

1. **Immediate Actions**
   - Change all admin passwords
   - Lock affected accounts
   - Review access logs
   - Document incident

2. **Investigation**
   - Identify scope of breach
   - Determine data affected
   - Review security logs
   - Assess damage

3. **Recovery**
   - Restore from clean backup
   - Patch security vulnerabilities
   - Notify affected users
   - Implement additional security

## Emergency Procedures

### Emergency Admin Access

If all admin accounts are locked or inaccessible:

```bash
# Create emergency admin account
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserRole
from werkzeug.security import generate_password_hash
import secrets

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

# Create emergency admin
emergency_password = secrets.token_urlsafe(16)
emergency_user = User(
    username='emergency_admin',
    email='admin@localhost',
    password_hash=generate_password_hash(emergency_password),
    role=UserRole.ADMIN,
    email_verified=True,
    is_active=True
)

session.add(emergency_user)
session.commit()

print(f'Emergency admin created:')
print(f'Username: emergency_admin')
print(f'Password: {emergency_password}')
print('Change password immediately after login')

session.close()
"
```

### Database Recovery

If database is corrupted:

```bash
# Backup current database
cp storage/database/vedfolnir.db storage/database/vedfolnir.db.backup

# Check database integrity
sqlite3 storage/database/vedfolnir.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
# cp storage/database/vedfolnir.db.backup.YYYY-MM-DD storage/database/vedfolnir.db

# Or recreate database
python -c "
from database import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
db_manager.create_tables()
print('Database recreated')
"
```

### System Reset

Complete system reset (use with caution):

```bash
# Backup all data
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cp -r storage/ backups/$(date +%Y%m%d_%H%M%S)/
cp .env backups/$(date +%Y%m%d_%H%M%S)/

# Reset database
rm storage/database/vedfolnir.db
python -c "
from database import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
db_manager.create_tables()
print('Database reset complete')
"

# Create initial admin user
python -c "
from database import DatabaseManager
from config import Config
from models import User, UserRole
from werkzeug.security import generate_password_hash

config = Config()
db_manager = DatabaseManager(config)
session = db_manager.get_session()

admin_user = User(
    username='admin',
    email='admin@localhost',
    password_hash=generate_password_hash('admin123'),
    role=UserRole.ADMIN,
    email_verified=True,
    is_active=True
)

session.add(admin_user)
session.commit()

print('Initial admin user created:')
print('Username: admin')
print('Password: admin123')
print('CHANGE PASSWORD IMMEDIATELY')

session.close()
"
```

This troubleshooting guide covers the most common issues with the user management system. For issues not covered here, contact the system administrator or consult the system logs for more detailed error information.