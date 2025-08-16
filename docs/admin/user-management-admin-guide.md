# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Admin User Management Guide

This comprehensive guide covers all administrative aspects of user management in Vedfolnir, including user creation, management, monitoring, and system administration.

## Table of Contents

1. [Admin Overview](#admin-overview)
2. [User Management Dashboard](#user-management-dashboard)
3. [Creating Users](#creating-users)
4. [Managing Existing Users](#managing-existing-users)
5. [User Roles and Permissions](#user-roles-and-permissions)
6. [Password Management](#password-management)
7. [Email Management](#email-management)
8. [User Monitoring and Analytics](#user-monitoring-and-analytics)
9. [GDPR Compliance Administration](#gdpr-compliance-administration)
10. [Security Administration](#security-administration)
11. [Troubleshooting User Issues](#troubleshooting-user-issues)
12. [System Maintenance](#system-maintenance)

## Admin Overview

### Administrative Responsibilities

As an admin user, you have comprehensive control over the user management system:

- **User Lifecycle Management**: Create, modify, and delete user accounts
- **Role Assignment**: Assign and modify user roles and permissions
- **Security Oversight**: Monitor security events and manage account lockouts
- **GDPR Compliance**: Handle data subject requests and ensure compliance
- **System Health**: Monitor user-related system performance and issues

### Admin Access Requirements

**Prerequisites**
- Admin role assigned to your account
- Active and verified email address
- Secure admin password
- Understanding of user management policies

**Security Considerations**
- Admin actions are fully audited
- Session preservation during user management operations
- CSRF protection on all admin forms
- Rate limiting on sensitive operations

## User Management Dashboard

### Accessing the Dashboard

1. **Navigate to Admin Area**
   - Log in with admin credentials
   - Click "Admin" in navigation menu
   - Select "User Management" from admin dashboard

2. **Dashboard Overview**
   - User statistics and metrics
   - Recent user activity
   - Pending administrative tasks
   - System health indicators

### Dashboard Components

**User Statistics Panel**
```
Total Users: [Number]
Active Users: [Number]
Pending Verification: [Number]
Locked Accounts: [Number]
Admin Users: [Number]
Viewer Users: [Number]
```

**Recent Activity Feed**
- New user registrations
- Email verification completions
- Password reset requests
- Account lockouts and unlocks
- Role changes and updates

**Quick Actions**
- Create New User
- Bulk User Operations
- Export User Data
- System Health Check

### User List Management

**User List View**
- Sortable columns (username, email, role, status, created date)
- Search and filter functionality
- Bulk selection capabilities
- Quick action buttons

**Filter Options**
- User role (Admin, Viewer)
- Account status (Active, Locked, Unverified)
- Registration date range
- Last login date range
- Email verification status

**Search Functionality**
- Search by username
- Search by email address
- Search by first/last name
- Advanced search with multiple criteria

## Creating Users

### Admin User Creation Process

1. **Access User Creation**
   - Click "Create New User" from dashboard
   - User creation form displayed
   - All fields available for admin input

2. **User Creation Form**
   ```
   Username: [Required - unique identifier]
   Email: [Required - valid email address]
   First Name: [Optional - user's first name]
   Last Name: [Optional - user's last name]
   Role: [Required - Admin or Viewer]
   Password: [Required - temporary password]
   Send Welcome Email: [Checkbox - notify user]
   Skip Email Verification: [Checkbox - admin bypass]
   ```

3. **Form Validation**
   - Username uniqueness check
   - Email format validation
   - Password strength requirements
   - Role selection validation

4. **User Creation Options**

   **Standard Creation**
   - User receives welcome email with credentials
   - Email verification required before login
   - User must change password on first login

   **Admin Bypass Creation**
   - Skip email verification requirement
   - User can log in immediately
   - Still receives welcome email with credentials

### Bulk User Creation

**CSV Import Process**
1. **Prepare CSV File**
   ```csv
   username,email,first_name,last_name,role
   john_doe,john@example.com,John,Doe,viewer
   jane_admin,jane@example.com,Jane,Smith,admin
   ```

2. **Import Process**
   - Click "Bulk Import" button
   - Upload CSV file
   - Review import preview
   - Confirm bulk creation

3. **Import Validation**
   - Duplicate username detection
   - Email format validation
   - Role validation
   - Error reporting for invalid entries

**Bulk Creation Results**
- Success/failure summary
- Detailed error report
- Email notification options
- Audit log entries

### User Creation Best Practices

**Security Considerations**
- Generate strong temporary passwords
- Require password change on first login
- Send credentials via secure email
- Document user creation rationale

**Communication**
- Send welcome emails with clear instructions
- Provide user guide links
- Include contact information for support
- Set clear expectations for first login

## Managing Existing Users

### User Profile Management

**Accessing User Profiles**
1. Find user in user list
2. Click "Edit" button
3. User profile editor opens
4. All user information displayed

**Editable User Information**
```
Personal Information:
- First Name
- Last Name
- Email Address (triggers re-verification)

Account Settings:
- Username (read-only after creation)
- Role (Admin/Viewer)
- Account Status (Active/Locked)
- Email Verification Status

Security Settings:
- Force Password Reset
- Unlock Account
- Reset Failed Login Attempts
```

### User Status Management

**Account Status Options**
- **Active**: Normal account operation
- **Locked**: Account locked due to security issues
- **Suspended**: Temporarily disabled by admin
- **Pending**: Awaiting email verification

**Status Change Process**
1. Select user from list
2. Click "Change Status"
3. Select new status
4. Provide reason for change
5. Confirm status change
6. User notified via email (if applicable)

### Role Management

**Role Assignment**
1. **Change User Role**
   - Edit user profile
   - Select new role from dropdown
   - Confirm role change
   - System updates permissions immediately

2. **Role Change Implications**
   - **Admin to Viewer**: Loses admin access, retains own platforms
   - **Viewer to Admin**: Gains full system access
   - Session preservation during role changes
   - Audit log entry created

**Permission Verification**
- Test user permissions after role change
- Verify platform access is appropriate
- Confirm admin functions work correctly
- Monitor for any access issues

### User Deletion

**Deletion Process**
1. **Select User for Deletion**
   - Find user in user list
   - Click "Delete" button
   - Deletion confirmation dialog

2. **Deletion Options**
   ```
   Deletion Type:
   - Soft Delete: Mark as deleted, preserve data
   - Hard Delete: Permanently remove all data
   
   Data Handling:
   - Preserve platform connections
   - Delete platform connections
   - Archive user content
   - Permanently delete content
   ```

3. **Deletion Confirmation**
   - Review deletion consequences
   - Confirm understanding of data loss
   - Enter admin password for verification
   - Execute deletion

**GDPR Compliant Deletion**
- Complete data erasure option
- Cascading deletion of related data
- Audit trail preservation
- Compliance reporting

### Bulk User Operations

**Available Bulk Operations**
- Role changes
- Status updates
- Password resets
- Email notifications
- Account lockouts/unlocks

**Bulk Operation Process**
1. Select users using checkboxes
2. Choose bulk operation from dropdown
3. Configure operation parameters
4. Review affected users
5. Execute bulk operation
6. Monitor operation progress

## User Roles and Permissions

### Role Definitions

**Admin Role Capabilities**
- Full system access
- User management operations
- System configuration
- All platform access
- Administrative reporting
- Security oversight

**Viewer Role Capabilities**
- Personal platform management
- Caption generation and review
- Profile management
- Limited to own content
- No administrative access

### Permission Management

**Role-Based Access Control**
- Route-level permission enforcement
- Platform-scoped data access
- Feature-level restrictions
- API endpoint protection

**Permission Verification Tools**
- User permission checker
- Role capability matrix
- Access audit reports
- Permission testing utilities

### Custom Permission Configuration

**Advanced Permission Settings**
- Platform access restrictions
- Feature-specific permissions
- Time-based access controls
- IP-based restrictions

**Permission Inheritance**
- Default role permissions
- Custom permission overrides
- Permission group management
- Inheritance hierarchy

## Password Management

### Admin Password Operations

**Password Reset for Users**
1. **Initiate Admin Reset**
   - Select user from list
   - Click "Reset Password"
   - Choose reset method

2. **Reset Methods**
   ```
   Email Reset:
   - Send reset link to user's email
   - User completes reset process
   - Admin notified of completion
   
   Admin Reset:
   - Generate temporary password
   - Provide password to user securely
   - Force password change on next login
   ```

3. **Reset Confirmation**
   - User sessions invalidated
   - Reset logged in audit trail
   - User notified via email
   - Admin receives confirmation

### Password Policy Management

**System Password Policies**
- Minimum length requirements
- Character complexity rules
- Password history restrictions
- Expiration policies

**Policy Enforcement**
- Real-time validation
- Policy violation reporting
- Compliance monitoring
- Exception handling

### Bulk Password Operations

**Mass Password Reset**
1. Select multiple users
2. Choose bulk password reset
3. Select reset method (email/admin)
4. Execute bulk operation
5. Monitor reset progress

**Password Audit**
- Weak password detection
- Password age reporting
- Compliance verification
- Security recommendations

## Email Management

### Email System Administration

**Email Configuration**
- SMTP server settings
- Email template management
- Delivery monitoring
- Bounce handling

**Email Template Management**
- Welcome email templates
- Password reset templates
- Verification email templates
- Notification templates

### User Email Operations

**Email Verification Management**
1. **Manual Verification**
   - Bypass email verification for users
   - Mark email as verified
   - Send verification confirmation

2. **Resend Verification**
   - Generate new verification token
   - Send fresh verification email
   - Monitor delivery status

**Email Change Administration**
- Approve email change requests
- Handle email conflicts
- Manage verification process
- Resolve email issues

### Email Monitoring

**Delivery Tracking**
- Email send success/failure rates
- Bounce and rejection monitoring
- Delivery time analytics
- Provider-specific issues

**Email Security**
- SPF/DKIM configuration
- Spam prevention measures
- Email authentication
- Security monitoring

## User Monitoring and Analytics

### User Activity Monitoring

**Activity Dashboard**
- Login frequency and patterns
- Platform usage statistics
- Feature utilization metrics
- Session duration analytics

**Real-Time Monitoring**
- Active user sessions
- Current platform connections
- Processing job status
- System resource usage

### User Analytics

**Usage Statistics**
```
User Engagement Metrics:
- Daily/Weekly/Monthly active users
- Feature adoption rates
- Platform connection trends
- Content processing volumes

Performance Metrics:
- Login success rates
- Session duration averages
- Error rates by user
- Support ticket volumes
```

**Reporting Capabilities**
- Automated report generation
- Custom report creation
- Data export functionality
- Trend analysis tools

### Security Monitoring

**Security Event Tracking**
- Failed login attempts
- Account lockout events
- Suspicious activity detection
- Security policy violations

**Threat Detection**
- Brute force attack monitoring
- Unusual access patterns
- Geographic anomalies
- Device fingerprinting

## GDPR Compliance Administration

### Data Subject Rights Management

**Access Requests**
1. **Process Data Access Requests**
   - Verify user identity
   - Generate comprehensive data export
   - Deliver data securely
   - Log request completion

2. **Data Export Contents**
   - Personal profile information
   - Platform connection data
   - Activity logs and history
   - System interaction records

**Erasure Requests**
1. **Right to be Forgotten**
   - Verify deletion request
   - Assess legal obligations
   - Execute complete data deletion
   - Confirm deletion completion

2. **Deletion Verification**
   - Database record removal
   - File system cleanup
   - Backup data handling
   - Third-party data removal

### Compliance Monitoring

**GDPR Compliance Dashboard**
- Data processing activities
- Consent management status
- Data retention compliance
- Breach notification status

**Audit Trail Management**
- Complete activity logging
- Compliance report generation
- Data processing records
- Legal basis documentation

### Privacy Impact Assessments

**Regular Assessments**
- Data processing impact evaluation
- Privacy risk assessment
- Mitigation strategy development
- Compliance verification

**Documentation Management**
- Privacy policy maintenance
- Data processing agreements
- Consent record keeping
- Compliance documentation

## Security Administration

### Account Security Management

**Security Policy Enforcement**
- Password policy compliance
- Account lockout management
- Session security monitoring
- Access control verification

**Security Incident Response**
1. **Incident Detection**
   - Automated security alerts
   - Manual incident reporting
   - Security event correlation
   - Threat assessment

2. **Incident Response Process**
   - Immediate threat containment
   - User notification procedures
   - Investigation coordination
   - Recovery planning

### Access Control Administration

**Session Management**
- Active session monitoring
- Session timeout configuration
- Cross-device session tracking
- Session invalidation tools

**Authentication Security**
- Multi-factor authentication setup
- Authentication method management
- Login attempt monitoring
- Credential security verification

### Security Auditing

**Regular Security Audits**
- User access reviews
- Permission verification
- Security policy compliance
- Vulnerability assessments

**Security Reporting**
- Security metrics dashboard
- Incident report generation
- Compliance status reports
- Risk assessment summaries

## Troubleshooting User Issues

### Common User Problems

**Login Issues**
1. **Account Lockout**
   - Verify lockout reason
   - Check failed login attempts
   - Unlock account if appropriate
   - Reset failed attempt counter

2. **Email Verification Problems**
   - Check email delivery status
   - Resend verification email
   - Manually verify email if needed
   - Investigate email system issues

**Profile Issues**
1. **Profile Update Failures**
   - Check input validation errors
   - Verify database connectivity
   - Review audit logs
   - Test profile update process

2. **Email Change Issues**
   - Verify new email format
   - Check for email conflicts
   - Monitor verification process
   - Handle verification failures

### Diagnostic Tools

**User Account Diagnostics**
- Account status checker
- Permission verification tool
- Session analysis utility
- Activity log viewer

**System Health Checks**
- Database connectivity test
- Email system verification
- Authentication service check
- Session management test

### Issue Resolution Process

**Standard Resolution Steps**
1. **Issue Identification**
   - Gather user-reported symptoms
   - Review system logs
   - Check user account status
   - Identify root cause

2. **Resolution Implementation**
   - Apply appropriate fix
   - Test resolution effectiveness
   - Verify user can access system
   - Document resolution steps

3. **Follow-up Actions**
   - Monitor for recurring issues
   - Update documentation
   - Implement preventive measures
   - Communicate with user

## System Maintenance

### Regular Maintenance Tasks

**Daily Tasks**
- Monitor user activity logs
- Check email delivery status
- Review security alerts
- Verify system health

**Weekly Tasks**
- User account audit
- Security policy review
- Performance monitoring
- Backup verification

**Monthly Tasks**
- Comprehensive security audit
- User access review
- System performance analysis
- Compliance verification

### Database Maintenance

**User Data Maintenance**
- Clean up expired tokens
- Archive old audit logs
- Optimize database performance
- Verify data integrity

**Backup and Recovery**
- Regular database backups
- Backup verification procedures
- Recovery testing
- Disaster recovery planning

### System Updates

**User Management Updates**
- Security patch application
- Feature updates
- Configuration changes
- Performance optimizations

**Update Process**
1. **Pre-Update Preparation**
   - Backup current system
   - Test updates in staging
   - Plan rollback procedures
   - Schedule maintenance window

2. **Update Execution**
   - Apply updates systematically
   - Monitor system stability
   - Verify functionality
   - Document changes

3. **Post-Update Verification**
   - Test all user functions
   - Verify security measures
   - Check performance metrics
   - Communicate completion

This admin guide provides comprehensive information for managing all aspects of the user management system. Regular review and updates ensure effective administration and security compliance.