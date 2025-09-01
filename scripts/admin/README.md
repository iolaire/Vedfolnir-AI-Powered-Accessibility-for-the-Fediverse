# Admin Scripts

This directory contains administrative scripts for managing user accounts and system operations.

## ✅ Status: All Scripts Working and Tested

All scripts have been tested and are working correctly with the current database schema.

## User Account Management Scripts

### 1. Quick Unlock User (`quick_unlock_user.py`)

Simple script to quickly unlock a user account by username.

```bash
# Unlock a specific user
python scripts/admin/quick_unlock_user.py admin
python scripts/admin/quick_unlock_user.py username
```

**Features:**
- Fast and simple unlocking
- Minimal output
- Automatic audit logging

### 2. Comprehensive Unlock Script (`unlock_user_account.py`)

Full-featured script for unlocking user accounts with detailed options.

```bash
# List all locked accounts
python scripts/admin/unlock_user_account.py --list-locked

# Unlock specific user by username
python scripts/admin/unlock_user_account.py --username admin

# Unlock specific user by email
python scripts/admin/unlock_user_account.py --email admin@example.com

# Unlock specific user by ID
python scripts/admin/unlock_user_account.py --user-id 1

# Unlock all locked accounts
python scripts/admin/unlock_user_account.py --unlock-all

# Unlock with custom reason for audit log
python scripts/admin/unlock_user_account.py --username admin --reason "Password reset completed"

# Force unlock without confirmation
python scripts/admin/unlock_user_account.py --username admin --force

# Verbose output
python scripts/admin/unlock_user_account.py --username admin --verbose
```

**Features:**
- Multiple user identification methods (username, email, ID)
- List locked accounts
- Bulk unlock operations
- Custom audit reasons
- Confirmation prompts
- Verbose output mode

### 3. User Account Manager (`user_account_manager.py`)

Comprehensive user account management script with multiple operations.

```bash
# Unlock operations
python scripts/admin/user_account_manager.py unlock admin
python scripts/admin/user_account_manager.py unlock-all
python scripts/admin/user_account_manager.py list-locked

# User listing and information
python scripts/admin/user_account_manager.py list-users
python scripts/admin/user_account_manager.py user-info admin

# Account activation/deactivation
python scripts/admin/user_account_manager.py activate username
python scripts/admin/user_account_manager.py deactivate username

# Password management
python scripts/admin/user_account_manager.py reset-password admin

# Email verification
python scripts/admin/user_account_manager.py verify-email username

# Force operations without confirmation
python scripts/admin/user_account_manager.py unlock-all --force
```

**Features:**
- Account unlocking (single and bulk)
- Account activation/deactivation
- Password reset with secure generation
- Email verification management
- Detailed user information display
- Complete user listing with status
- Comprehensive audit logging

## User Account Locking System

### How Account Locking Works

The system automatically locks user accounts after failed login attempts:

1. **Failed Login Tracking**: Each failed login attempt is recorded
2. **Lockout Threshold**: After 5 failed attempts, the account is locked
3. **Lockout Duration**: Accounts remain locked until manually unlocked
4. **Automatic Reset**: Failed attempts reset after successful login

### Account Lock Fields

- `account_locked`: Boolean flag indicating if account is locked
- `failed_login_attempts`: Counter of consecutive failed login attempts
- `last_failed_login`: Timestamp of the last failed login attempt

### Unlock Methods Available

The `User` model provides an `unlock_account()` method that:
- Sets `account_locked = False`
- Resets `failed_login_attempts = 0`
- Clears `last_failed_login = None`

## Security and Audit Logging

All admin operations are automatically logged to the `user_audit_log` table with:

- **Action Type**: Specific action performed (e.g., "account_unlocked", "admin_password_reset")
- **User ID**: Target user affected by the action
- **Admin User ID**: ID of admin performing the action (if applicable)
- **Details**: Descriptive text about the action
- **IP Address**: Source IP address (127.0.0.1 for script operations)
- **User Agent**: Identifies the script used
- **Timestamp**: When the action occurred

## Common Use Cases

### Emergency Account Access

```bash
# Quick unlock for emergency access
python scripts/admin/quick_unlock_user.py admin

# Or with more details
python scripts/admin/user_account_manager.py unlock admin
```

### Bulk Account Management

```bash
# See all locked accounts
python scripts/admin/user_account_manager.py list-locked

# Unlock all at once
python scripts/admin/user_account_manager.py unlock-all
```

### User Support

```bash
# Check user status
python scripts/admin/user_account_manager.py user-info username

# Reset password for user
python scripts/admin/user_account_manager.py reset-password username

# Verify email if verification is stuck
python scripts/admin/user_account_manager.py verify-email username
```

### System Administration

```bash
# List all users and their status
python scripts/admin/user_account_manager.py list-users

# Deactivate problematic account
python scripts/admin/user_account_manager.py deactivate username

# Reactivate account later
python scripts/admin/user_account_manager.py activate username
```

## Prerequisites

### Environment Setup

All scripts require:
1. **Environment Variables**: Proper `.env` file configuration
2. **Database Access**: MySQL database connection
3. **Python Dependencies**: All requirements installed

### Required Permissions

Scripts should be run by system administrators with:
- File system access to the project directory
- Database connection permissions
- Ability to modify user records

### Database Requirements

The scripts work with the MySQL database schema including:
- `users` table with account locking fields
- `user_audit_log` table for audit trails
- Proper foreign key relationships

## Error Handling

All scripts include comprehensive error handling for:

- **User Not Found**: Clear messages when users don't exist
- **Database Errors**: Connection and query error handling
- **Permission Errors**: File and database permission issues
- **Invalid Input**: Validation of command-line arguments
- **Interrupted Operations**: Graceful handling of Ctrl+C

## Best Practices

### Security

1. **Audit Everything**: All operations are logged automatically
2. **Confirm Destructive Actions**: Scripts prompt before bulk operations
3. **Use Secure Passwords**: Generated passwords are cryptographically secure
4. **Limit Access**: Only run scripts with appropriate administrative privileges

### Operations

1. **Check Before Acting**: Use `list-locked` or `user-info` to verify status
2. **Use Appropriate Tool**: Quick script for simple unlocks, comprehensive script for complex operations
3. **Document Reasons**: Use `--reason` flag for audit trail context
4. **Test First**: Verify operations on non-critical accounts when possible

### Monitoring

1. **Review Audit Logs**: Regularly check `user_audit_log` table
2. **Monitor Failed Attempts**: Watch for patterns in failed login attempts
3. **Track Bulk Operations**: Pay attention to bulk unlock operations
4. **Verify Results**: Confirm operations completed successfully

## Troubleshooting

### Common Issues

**"User not found"**
- Verify username spelling
- Check if user exists with `list-users`
- Try searching by email instead

**"Account is not locked"**
- User may already be unlocked
- Check current status with `user-info`
- Verify failed login attempts count

**Database connection errors**
- Check `.env` file configuration
- Verify MySQL service is running
- Confirm database credentials

**Permission denied**
- Ensure scripts are executable (`chmod +x`)
- Check file system permissions
- Verify database user permissions

### Getting Help

For additional help:
1. Use `--help` flag on any script for usage information
2. Use `--verbose` flag for detailed output
3. Check the audit logs for operation history
4. Review the main application logs for context

## Integration with Web Interface

These scripts complement the web-based admin interface:

- **Web Interface**: For regular administrative tasks and user management
- **Scripts**: For emergency access, bulk operations, and automation
- **Audit Trail**: Both interfaces log to the same audit system
- **Consistency**: Same underlying user management service and database

The scripts use the same `UserManagementService` and database models as the web application, ensuring consistency and reliability.