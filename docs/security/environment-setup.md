# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Security Environment Setup

This document provides instructions for securely configuring sensitive settings in your .env file that are required for Vedfolnir.

## Overview

The following sensitive settings must be configured in your .env file:

- `FLASK_SECRET_KEY`: Flask application secret key for session security
- `PLATFORM_ENCRYPTION_KEY`: Encryption key for platform credentials stored in database

**Note**: Admin user credentials are stored in the database, not in the .env file. The setup script will create the admin user for you.

## Quick Setup

### Option A: Automated Setup (Recommended)

Use the provided script to generate all required values and create your .env file:

```bash
# Run the environment secrets generator
python3 scripts/setup/generate_env_secrets.py

# Start the application
python3 web_app.py
```

This script will:
- Generate cryptographically secure keys and passwords
- Prompt for admin username and email
- Create a properly configured .env file
- Create the admin user in the database
- Set appropriate file permissions
- Provide clear next steps

### Option B: Manual Setup

If you prefer to set up your .env file manually:

#### 1. Copy the Template
```bash
# Copy the example file to create your .env file
cp .env.example .env
```

#### 2. Generate Secure Values

Generate each required value using these commands:

```bash
# Generate Flask secret key (32 characters minimum)
python3 -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate platform encryption key (Fernet key format)
python3 -c "from cryptography.fernet import Fernet; print('PLATFORM_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Generate a secure admin password (24 characters with mixed types)
python3 -c "import secrets, string; chars = string.ascii_letters + string.digits + '!@#$%^&*'; print('AUTH_ADMIN_PASSWORD=' + ''.join(secrets.choice(chars) for _ in range(24)))"
```

#### 3. Edit Your .env File

Open your .env file and replace the placeholder values:

```bash
# Edit the .env file with your preferred editor
nano .env
# or
vim .env
```

Replace these lines with your generated values:
```bash
FLASK_SECRET_KEY=your-generated-secret-key-here
AUTH_ADMIN_USERNAME=your-chosen-username
AUTH_ADMIN_EMAIL=your-email@domain.com
AUTH_ADMIN_PASSWORD=your-generated-password-here
PLATFORM_ENCRYPTION_KEY=your-generated-encryption-key-here
```

#### 4. Secure Your .env File

Set appropriate permissions to protect your .env file:

```bash
# Make the .env file readable only by the owner
chmod 600 .env

# Verify the file is properly protected
ls -la .env
```

## Detailed Instructions

### Flask Secret Key

The Flask secret key is used for:
- Session cookie signing and encryption
- CSRF token generation
- Password reset tokens
- Any Flask cryptographic operations

**Generation:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Requirements:**
- Must be at least 32 characters long
- Should be cryptographically random
- Must be kept secret and never logged
- Should be rotated periodically in production

### Platform Encryption Key

This key encrypts platform credentials (API tokens, client secrets) stored in the database.

**Generation:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Requirements:**
- Must be a valid Fernet key (32 URL-safe base64-encoded bytes)
- Used to encrypt/decrypt platform API tokens in database
- If lost, all stored platform credentials become unrecoverable
- Should be backed up securely

### Admin Credentials

**Username Requirements:**
- Should be unique and not easily guessable
- Avoid common usernames like "admin", "administrator", "root"
- 3-64 characters, alphanumeric and underscores only

**Email Requirements:**
- Must be a valid email address
- Should be an email you have access to
- Used for admin notifications and password resets

**Password Requirements:**
- Minimum 8 characters (recommend 16+ for admin accounts)
- Must contain uppercase, lowercase, numbers, and special characters
- Should be unique and not reused from other accounts
- Consider using a password manager

**Secure Password Generation:**
```bash
# Generate a 24-character password with mixed characters
python3 -c "import secrets, string; chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'; print(''.join(secrets.choice(chars) for _ in range(24)))"
```

## Verification

### Automated Verification (Recommended)
```bash
# Run the comprehensive verification script
python3 scripts/setup/verify_env_setup.py
```

This script will:
- Check that your .env file exists and is readable
- Validate that all required settings are present
- Verify the format and strength of each value
- Test configuration loading
- Provide specific guidance for any issues

### Manual Verification
```bash
# Check that .env file exists and has proper permissions
ls -la .env

# Verify required variables are set (without showing values)
grep -q "FLASK_SECRET_KEY=" .env && echo "FLASK_SECRET_KEY: SET" || echo "FLASK_SECRET_KEY: MISSING"
grep -q "AUTH_ADMIN_USERNAME=" .env && echo "AUTH_ADMIN_USERNAME: SET" || echo "AUTH_ADMIN_USERNAME: MISSING"
grep -q "AUTH_ADMIN_EMAIL=" .env && echo "AUTH_ADMIN_EMAIL: SET" || echo "AUTH_ADMIN_EMAIL: MISSING"
grep -q "AUTH_ADMIN_PASSWORD=" .env && echo "AUTH_ADMIN_PASSWORD: SET" || echo "AUTH_ADMIN_PASSWORD: MISSING"
grep -q "PLATFORM_ENCRYPTION_KEY=" .env && echo "PLATFORM_ENCRYPTION_KEY: SET" || echo "PLATFORM_ENCRYPTION_KEY: MISSING"
```

### Test Application Startup
```bash
# Start the application and check for configuration errors
python3 web_app.py
```

If any required settings are missing from your .env file, the application will show a clear error message with a reference to this documentation.

## Security Best Practices

### Development Environment
1. Use .env file for local development (never commit to version control)
2. Use different values for development and production
3. Regularly rotate keys and passwords
4. Set proper file permissions (600) on .env file

### Production Environment
1. Use your platform's secrets management system when possible:
   - AWS Secrets Manager / Parameter Store
   - Azure Key Vault
   - Google Secret Manager
   - HashiCorp Vault
   - Kubernetes Secrets

2. If using .env files in production:
   - Set restrictive file permissions (600 or 400)
   - Store .env file outside web root
   - Use different encryption keys per environment
   - Implement key rotation procedures
   - Monitor for unauthorized access

### Key Rotation

#### Flask Secret Key Rotation
```bash
# Generate new key
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Update .env file
sed -i "s/FLASK_SECRET_KEY=.*/FLASK_SECRET_KEY=$NEW_SECRET/" .env

# Restart application (all existing sessions will be invalidated)
```

#### Platform Encryption Key Rotation
⚠️ **Warning**: Rotating the platform encryption key requires careful planning as it will make existing encrypted data unreadable.

1. Generate new key
2. Decrypt existing platform credentials with old key
3. Re-encrypt with new key
4. Update .env file
5. Restart application

## Migration from Environment Variables

If you previously had these settings configured as system environment variables, you can migrate them to your .env file:

### Automated Migration
```bash
# Use the migration script to move environment variables to .env file
python3 scripts/setup/migrate_env_to_file.py
```

### Manual Migration
```bash
# Create .env file from template
cp .env.example .env

# Add your existing environment variable values to .env file
echo "FLASK_SECRET_KEY=$FLASK_SECRET_KEY" >> .env
echo "AUTH_ADMIN_USERNAME=$AUTH_ADMIN_USERNAME" >> .env
echo "AUTH_ADMIN_EMAIL=$AUTH_ADMIN_EMAIL" >> .env
echo "AUTH_ADMIN_PASSWORD=$AUTH_ADMIN_PASSWORD" >> .env
echo "PLATFORM_ENCRYPTION_KEY=$PLATFORM_ENCRYPTION_KEY" >> .env

# Set proper permissions
chmod 600 .env

# Unset the environment variables (optional)
unset FLASK_SECRET_KEY AUTH_ADMIN_USERNAME AUTH_ADMIN_EMAIL AUTH_ADMIN_PASSWORD PLATFORM_ENCRYPTION_KEY
```

## Troubleshooting

### Common Issues

**"Configuration Error: FLASK_SECRET_KEY is required in .env file"**
- Ensure your .env file exists in the project root
- Check that FLASK_SECRET_KEY is set in your .env file
- Verify the .env file has proper permissions (readable by the application)

**"Configuration Error: AUTH_ADMIN_PASSWORD is required in .env file"**
- Ensure all admin authentication variables are set in your .env file
- Verify the password meets complexity requirements
- Check that there are no extra spaces or quotes around the values

**"Invalid username or password" after setting up .env file**
This happens when you've configured credentials in .env but the admin user in the database has different credentials.

*Solution:*
```bash
# Update the admin user with .env file credentials
python3 scripts/setup/update_admin_user.py
```

*Alternative:*
```bash
# Use the interactive admin user setup (will offer to update existing user)
python3 scripts/setup/init_admin_user.py
```

**"Platform credentials cannot be decrypted"**
- The `PLATFORM_ENCRYPTION_KEY` may have changed
- Check that the key is exactly as generated (no extra spaces/characters)
- If key is lost, platform connections will need to be re-configured

**".env file not found" or "Permission denied"**
- Ensure .env file exists: `ls -la .env`
- Check file permissions: `chmod 600 .env`
- Verify you're running the application from the correct directory

### Getting Help

If you encounter issues:
1. Check the application logs for specific error messages
2. Verify your .env file exists and has all required settings
3. Ensure Python dependencies are installed (`pip install cryptography python-dotenv`)
4. Check file permissions on .env file
5. Try the automated verification script: `python3 scripts/setup/verify_env_setup.py`

## Security Feature Toggles (Development/Testing)

The application includes security feature toggles for development and testing purposes. These are configured in the `.env` file:

```bash
# Security Feature Toggles (Development/Testing Only)
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_HEADERS_ENABLED=true
SECURITY_SESSION_VALIDATION_ENABLED=true
SECURITY_ADMIN_CHECKS_ENABLED=true
```

### ⚠️ Important Security Notes

1. **Production Requirement**: ALL security toggles MUST be set to `true` in production
2. **Development Use**: Only disable specific features for testing/debugging purposes
3. **Never Commit**: Never commit `.env` files with disabled security features
4. **Documentation**: See [Security Guide](../SECURITY.md) for detailed information

### Common Development Scenarios

```bash
# API testing without CSRF tokens
SECURITY_CSRF_ENABLED=false

# Load testing without rate limits
SECURITY_RATE_LIMITING_ENABLED=false

# Debugging with relaxed security headers
SECURITY_HEADERS_ENABLED=false
```

**Remember to re-enable all security features after testing!**

## Security Checklist

- [ ] Created .env file from .env.example template
- [ ] Generated cryptographically secure keys and passwords
- [ ] Set all required variables in .env file
- [ ] **Verified all security toggles are enabled for production**
- [ ] Verified .env file is not committed to version control (.gitignore)
- [ ] Set proper file permissions (600) on .env file
- [ ] Tested application startup successfully
- [ ] Documented key storage location for team
- [ ] Planned key rotation schedule for production
- [ ] Configured production secrets management (if applicable)
- [ ] Removed any hardcoded credentials from codebase