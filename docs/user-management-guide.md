# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# User Management Guide

This comprehensive guide covers all aspects of user account management in Vedfolnir, including registration, authentication, profile management, and GDPR rights.

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Registration](#user-registration)
3. [Email Verification](#email-verification)
4. [User Authentication](#user-authentication)
5. [Profile Management](#profile-management)
6. [Password Management](#password-management)
7. [User Roles and Permissions](#user-roles-and-permissions)
8. [GDPR Rights and Data Protection](#gdpr-rights-and-data-protection)
9. [Troubleshooting](#troubleshooting)
10. [Security Best Practices](#security-best-practices)

## Getting Started

### System Overview

Vedfolnir uses a comprehensive user management system with role-based access control, email verification, and GDPR compliance. The system supports two user roles:

- **Admin Users**: Full system access including administrative functions
- **Viewer Users**: Limited access to their own platforms and content

### Prerequisites

- Valid email address for account verification
- Modern web browser with JavaScript enabled
- Internet connection for email verification

## User Registration

### Self-Registration Process

1. **Access Registration Page**
   - Navigate to `/register` or click "Sign Up" from the login page
   - The registration form will be displayed

2. **Complete Registration Form**
   ```
   Username: [Enter unique username]
   Email: [Enter valid email address]
   First Name: [Enter first name]
   Last Name: [Enter last name]
   Password: [Enter secure password]
   Confirm Password: [Re-enter password]
   ```

3. **Password Requirements**
   - Minimum 8 characters
   - Must contain uppercase and lowercase letters
   - Must contain at least one number
   - Must contain at least one special character

4. **Submit Registration**
   - Click "Register" to submit the form
   - System validates all input data
   - Account is created with "unverified" status

5. **Email Verification Required**
   - Check your email for verification message
   - Click the verification link to activate your account
   - Account remains inactive until email is verified

### Registration Validation

The system performs comprehensive validation:

- **Email Format**: Must be valid email format using email_validator
- **Username Uniqueness**: Username must be unique across all users
- **Password Strength**: Must meet security requirements
- **CSRF Protection**: All forms include CSRF tokens
- **Rate Limiting**: Registration limited to prevent abuse

### Common Registration Issues

**Email Already Exists**
- Error: "An account with this email already exists"
- Solution: Use a different email or recover existing account

**Username Taken**
- Error: "Username is already taken"
- Solution: Choose a different username

**Weak Password**
- Error: "Password does not meet requirements"
- Solution: Create stronger password meeting all criteria

## Email Verification

### Verification Process

1. **Receive Verification Email**
   - Email sent immediately after registration
   - Contains secure verification link
   - Link expires after 24 hours

2. **Click Verification Link**
   - Opens verification page in browser
   - System validates the token
   - Account is activated automatically

3. **Verification Confirmation**
   - Success message displayed
   - Redirect to login page
   - Account is now active and ready to use

### Managing Email Verification

**Resend Verification Email**
- Available on login page for unverified accounts
- Click "Resend verification email"
- New email sent with fresh verification link

**Verification Email Not Received**
1. Check spam/junk folder
2. Verify email address was entered correctly
3. Contact administrator if email still not received

**Expired Verification Link**
- Links expire after 24 hours
- Request new verification email
- Use the new link to verify account

### Email Verification Security

- **Secure Tokens**: Cryptographically secure verification tokens
- **Time Limits**: Links expire to prevent misuse
- **Single Use**: Each token can only be used once
- **Account Protection**: Unverified accounts cannot log in

## User Authentication

### Login Process

1. **Access Login Page**
   - Navigate to `/login` or click "Sign In"
   - Enter your credentials

2. **Login Form**
   ```
   Username or Email: [Enter username or email]
   Password: [Enter password]
   Remember Me: [Optional checkbox]
   ```

3. **Authentication Validation**
   - System verifies credentials
   - Checks email verification status
   - Validates account is not locked

4. **Successful Login**
   - Secure session created
   - Redirected to dashboard
   - Session synchronized across browser tabs

### Account Security Features

**Account Lockout Protection**
- Account locked after 5 failed login attempts
- Lockout duration: 30 minutes
- Automatic unlock after timeout period

**Session Management**
- Database-stored sessions (not cookies)
- Secure session tokens
- Cross-tab synchronization
- Automatic session cleanup

**Rate Limiting**
- Login attempts limited per IP address
- Protection against brute force attacks
- Temporary blocks for suspicious activity

### Login Troubleshooting

**Invalid Credentials**
- Verify username/email and password
- Check caps lock status
- Try password reset if forgotten

**Account Locked**
- Wait 30 minutes for automatic unlock
- Contact administrator for immediate unlock
- Review recent login attempts

**Email Not Verified**
- Complete email verification process
- Request new verification email if needed
- Cannot log in until email is verified

## Profile Management

### Accessing Profile Settings

1. **Navigate to Profile**
   - Click username in navigation bar
   - Select "Profile" from dropdown menu
   - Profile management page opens

2. **Profile Information Display**
   - Current profile information shown
   - Edit options available for each field
   - Account status and role displayed

### Editing Profile Information

**Personal Information**
```
First Name: [Editable field]
Last Name: [Editable field]
Username: [Read-only - cannot be changed]
Current Role: [Read-only - set by administrator]
```

**Email Address Management**
1. **Change Email Process**
   - Enter new email address
   - Click "Update Email"
   - Verification email sent to new address
   - Click verification link to confirm change
   - Old email address replaced after verification

2. **Email Change Security**
   - Verification required for new email
   - Old email notified of change attempt
   - Change can be cancelled before verification
   - Account access maintained during process

### Profile Update Process

1. **Make Changes**
   - Edit desired fields in profile form
   - Review changes before saving

2. **Save Changes**
   - Click "Save Changes" button
   - System validates all input
   - Changes applied immediately (except email)

3. **Change Confirmation**
   - Success message displayed
   - Updated information shown
   - Audit log entry created

### Profile Data Validation

- **Name Fields**: Alphanumeric characters and common punctuation
- **Email Format**: Valid email format required
- **Input Sanitization**: XSS protection applied
- **Length Limits**: Reasonable limits on field lengths

## Password Management

### Changing Password (Authenticated Users)

1. **Access Password Change**
   - Go to Profile Settings
   - Click "Change Password" tab
   - Password change form displayed

2. **Password Change Form**
   ```
   Current Password: [Enter current password]
   New Password: [Enter new password]
   Confirm New Password: [Re-enter new password]
   ```

3. **Password Change Process**
   - System verifies current password
   - Validates new password meets requirements
   - Updates password hash in database
   - Invalidates all existing sessions
   - Forces re-login on all devices

### Password Reset (Forgotten Password)

1. **Initiate Password Reset**
   - Click "Forgot Password" on login page
   - Enter email address
   - Click "Send Reset Link"

2. **Reset Email Process**
   - Reset email sent to registered address
   - Contains secure reset link
   - Link expires after 1 hour

3. **Complete Password Reset**
   - Click reset link in email
   - Enter new password (twice)
   - Click "Reset Password"
   - All existing sessions invalidated
   - Redirect to login page

### Password Security Requirements

**Strength Requirements**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*)

**Security Features**
- Passwords hashed using bcrypt
- Reset tokens cryptographically secure
- Time-limited reset links
- Session invalidation after password change

### Password Reset Troubleshooting

**Reset Email Not Received**
1. Check spam/junk folder
2. Verify email address is correct
3. Wait a few minutes for delivery
4. Contact administrator if still not received

**Reset Link Expired**
- Links expire after 1 hour
- Request new reset email
- Use new link immediately

**Reset Link Already Used**
- Each link can only be used once
- Request new reset if needed
- Contact administrator for assistance

## User Roles and Permissions

### Role Overview

**Admin Users**
- Full system access
- User management capabilities
- Administrative functions
- All platform access
- System configuration

**Viewer Users**
- Limited to own platforms
- Caption generation and review
- Profile management
- No administrative access
- Platform-scoped content access

### Admin User Capabilities

**User Management**
- Create new user accounts
- Edit existing user profiles
- Reset user passwords
- Delete user accounts
- Assign user roles

**System Administration**
- Access admin dashboard
- View system health metrics
- Perform data cleanup
- Monitor system performance
- Configure system settings

**Platform Management**
- Access all platform connections
- Manage global platform settings
- Monitor platform health
- Troubleshoot platform issues

### Viewer User Capabilities

**Platform Management**
- Add personal platform connections
- Edit own platform settings
- Test platform connections
- Switch between own platforms

**Content Management**
- Generate captions for own platforms
- Review and approve captions
- Manage own content
- Access own processing history

**Profile Management**
- Edit personal profile
- Change password
- Manage email preferences
- Exercise GDPR rights

### Permission Enforcement

**Access Control**
- Role-based route protection
- Platform-scoped data access
- Session-based authorization
- CSRF protection on all forms

**Security Measures**
- Input validation and sanitization
- Rate limiting on sensitive operations
- Audit logging for all actions
- Secure session management

## GDPR Rights and Data Protection

### Overview of GDPR Rights

Under GDPR, you have the following rights regarding your personal data:

1. **Right to Access**: Request copy of your personal data
2. **Right to Rectification**: Correct inaccurate personal data
3. **Right to Erasure**: Request deletion of your personal data
4. **Right to Data Portability**: Receive your data in machine-readable format
5. **Right to Object**: Object to processing of your personal data

### Exercising Your GDPR Rights

**Data Access Request**
1. Go to Profile Settings
2. Click "GDPR Rights" tab
3. Click "Request My Data"
4. System generates comprehensive data export
5. Download link provided via email

**Data Rectification**
- Use profile editing features to correct information
- Contact administrator for data you cannot edit
- Changes logged in audit trail

**Data Erasure (Right to be Forgotten)**
1. Go to Profile Settings
2. Click "Delete My Account"
3. Review deletion consequences
4. Confirm deletion request
5. Account and all data permanently deleted

**Data Portability**
- Data export includes all personal information
- Machine-readable JSON format
- Includes profile data, platform connections, and activity history
- Secure download link with expiration

### Data Processing Information

**What Data We Collect**
- Account information (username, email, name)
- Platform connection details (encrypted)
- Caption generation and review activity
- System usage logs and statistics

**How We Use Your Data**
- Provide user account functionality
- Enable platform connections and content processing
- Improve system performance and user experience
- Comply with legal obligations

**Data Retention**
- Account data retained while account is active
- Activity logs retained for 2 years
- Deleted data permanently removed within 30 days
- Backup data removed within 90 days

### Privacy and Consent

**Consent Management**
- Clear consent obtained during registration
- Granular consent options available
- Consent can be withdrawn at any time
- Processing stops when consent withdrawn

**Data Protection Measures**
- Encryption of sensitive data
- Secure data transmission (HTTPS)
- Access controls and authentication
- Regular security audits and updates

### GDPR Compliance Features

**Audit Trail**
- All data operations logged
- User actions tracked and recorded
- Administrative actions audited
- Compliance reporting available

**Data Minimization**
- Only necessary data collected
- Regular data cleanup processes
- Automatic deletion of expired data
- Purpose limitation enforced

## Troubleshooting

### Common User Issues

**Cannot Log In**
1. Verify email is verified
2. Check account is not locked
3. Confirm correct credentials
4. Try password reset if needed

**Email Verification Issues**
1. Check spam/junk folder
2. Verify email address correct
3. Request new verification email
4. Contact administrator if persistent

**Profile Update Problems**
1. Check all required fields completed
2. Verify email format if changing email
3. Ensure password meets requirements
4. Clear browser cache and retry

**Platform Access Issues**
1. Verify correct user role
2. Check platform is properly configured
3. Test platform connection
4. Contact administrator for role issues

### Error Messages and Solutions

**"Email address already in use"**
- Another account uses this email
- Use different email or recover existing account
- Contact administrator if you believe this is an error

**"Account is locked"**
- Too many failed login attempts
- Wait 30 minutes for automatic unlock
- Contact administrator for immediate assistance

**"Invalid verification token"**
- Verification link may be expired
- Request new verification email
- Ensure you're using the complete link

**"Session expired"**
- Your session has timed out
- Log in again to continue
- Enable "Remember Me" for longer sessions

### Getting Help

**Self-Service Options**
- Review this user guide
- Check troubleshooting section
- Use password reset functionality
- Try clearing browser cache

**Contacting Support**
1. Gather relevant information:
   - Error messages
   - Steps to reproduce issue
   - Browser and operating system
   - Screenshots if helpful

2. Contact administrator with:
   - Clear description of problem
   - What you were trying to do
   - What happened instead
   - Any error messages received

## Security Best Practices

### Account Security

**Strong Passwords**
- Use unique password for Vedfolnir
- Include mix of characters, numbers, symbols
- Avoid personal information
- Change password regularly

**Email Security**
- Use secure email provider
- Keep email account secure
- Monitor for suspicious emails
- Report phishing attempts

**Session Management**
- Log out when finished
- Don't share login credentials
- Use "Remember Me" only on trusted devices
- Report suspicious account activity

### Privacy Protection

**Personal Information**
- Only provide necessary information
- Keep profile information current
- Review privacy settings regularly
- Exercise GDPR rights as needed

**Platform Connections**
- Use secure platform credentials
- Regularly review connected platforms
- Remove unused platform connections
- Monitor platform access logs

### Safe Usage Practices

**Browser Security**
- Keep browser updated
- Use reputable browser
- Enable security features
- Clear cache regularly

**Network Security**
- Use secure internet connections
- Avoid public Wi-Fi for sensitive operations
- Use VPN if necessary
- Report security concerns

**Data Protection**
- Regularly backup important data
- Review data export periodically
- Understand data retention policies
- Exercise data rights appropriately

This user guide provides comprehensive information for managing your Vedfolnir user account. For additional assistance, consult the troubleshooting section or contact your system administrator.