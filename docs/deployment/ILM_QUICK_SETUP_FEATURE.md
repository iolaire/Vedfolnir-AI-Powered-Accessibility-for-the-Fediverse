# ILM Quick Setup Feature

## Overview

Added a "Quick Setup" feature to `scripts/setup/generate_env_secrets_ILM.py` that allows you to skip all interactive prompts and use pre-configured ILM development defaults after agreeing to overwrite the .env file.

## How It Works

### 1. **Automatic Prompt After .env Overwrite Agreement**
When you agree to overwrite an existing .env file, the script now asks:
```
🚀 Quick Setup Option:
You can use ILM development defaults for all settings (recommended for development)
Use quick setup with ILM defaults? (Y/n):
```

### 2. **Quick Setup for New .env Files**
Even for new .env files, the script offers the quick setup option immediately:
```
🚀 Quick Setup Option:
You can use ILM development defaults for all settings (recommended for development)
Use quick setup with ILM defaults? (Y/n):
```

### 3. **Complete Automation**
If you choose "Y" (default), the script:
- ✅ Skips ALL interactive prompts
- ✅ Uses pre-configured ILM development defaults
- ✅ Generates secure secrets automatically
- ✅ Creates the complete .env file
- ✅ Creates admin and reviewer users
- ✅ Shows a comprehensive summary

## ILM Development Defaults Applied

### Database Configuration
```bash
DB_TYPE=mysql
DB_NAME=vedfolnir
DB_USER=database_user_1d7b0d0696a20
DB_PASSWORD=EQA&bok7
DB_UNIX_SOCKET=/tmp/mysql.sock
# Plus all MySQL advanced configuration optimized for development
```

### Redis Configuration
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=ZkjBdCsoodbvY6EpXF
SESSION_STORAGE=redis
```

### Ollama Configuration
```bash
OLLAMA_URL=http://Mac-mini-M2.local:11434
OLLAMA_MODEL=llava:7b
```

### Email Configuration (Sandbox)
```bash
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=587
MAIL_USERNAME=24cc1476b47de6
MAIL_PASSWORD=7be97c03d858ab
MAIL_DEFAULT_SENDER=iolaire@vedfolnir.org
```

### Security Configuration (Development Mode)
```bash
SECURITY_CSRF_ENABLED=false
SECURITY_RATE_LIMITING_ENABLED=false
SECURITY_INPUT_VALIDATION_ENABLED=false
```

### WebSocket Configuration (Development Optimized)
```bash
# Relaxed security for easier development
SOCKETIO_REQUIRE_AUTH=false
SOCKETIO_SESSION_VALIDATION=false
SOCKETIO_RATE_LIMITING=false
SOCKETIO_CSRF_PROTECTION=false

# Verbose logging for debugging
SOCKETIO_LOG_LEVEL=DEBUG
SOCKETIO_LOG_CONNECTIONS=true
SOCKETIO_DEBUG=true
SOCKETIO_ENGINEIO_LOGGER=true

# Development-optimized performance
SOCKETIO_RECONNECTION_ATTEMPTS=10
SOCKETIO_RECONNECTION_DELAY=500
SOCKETIO_MAX_CONNECTIONS=100
SOCKETIO_CONNECTION_POOL_SIZE=5
```

### User Accounts Created
- **Admin User**: `admin` (iolaire@iolaire.net) with generated secure password
- **Reviewer User**: `iolaire` (iolaire@usa.net) with preset password

## Usage Examples

### Quick Setup (Recommended)
```bash
python scripts/setup/generate_env_secrets_ILM.py
# When prompted: "Use quick setup with ILM defaults? (Y/n):" 
# Press Enter or type 'y'
```

### Manual Setup (If You Want to Customize)
```bash
python scripts/setup/generate_env_secrets_ILM.py
# When prompted: "Use quick setup with ILM defaults? (Y/n):" 
# Type 'n' to go through all the interactive prompts
```

## Output Example

When using quick setup, you'll see:
```
🚀 ILM Quick Setup - Using Development Defaults
==================================================

✅ All defaults applied for ILM development environment

Generated/Default values:
  Flask Secret Key: abc123def456... (32 chars)
  Encryption Key: xyz789uvw012... (44 chars)
  Admin Username: admin
  Admin Email: iolaire@iolaire.net
  Admin Password: P@ssw0rd... (24 chars)
  Database: MySQL - vedfolnir
  DB User: database_user_1d7b0d0696a20
  Connection: Unix socket (/tmp/mysql.sock)
  Redis: localhost:6379
  Redis Password: ZkjBdCs... (16 chars)
  Session Storage: redis
  Email Server: sandbox.smtp.mailtrap.io:587
  Email Username: 24cc1476b47de6
  Storage Limit: 10 GB
  Warning Threshold: 80%
  Storage Monitoring: Enabled
  WebSocket Profile: ILM Development (optimized)
  WebSocket Transports: websocket,polling
  WebSocket Security: Relaxed for development
  WebSocket Logging: DEBUG (verbose)
  WebSocket Debug: true

✅ .env file created successfully with ILM development defaults!
📁 Location: /path/to/your/project/.env

👤 Creating admin user...
   Creating new admin user: admin

👤 Creating reviewer user...
   Creating new reviewer user: iolaire

🎉 ILM Quick Setup completed successfully!

📋 Summary:
   • .env file created with development defaults
   • Admin user: admin (iolaire@iolaire.net)
   • Reviewer user: iolaire (iolaire@usa.net)
   • Database: MySQL with ILM defaults
   • Redis: Configured with session management
   • WebSocket: Development-optimized settings
   • Security: Relaxed for development
   • Logging: Verbose for debugging

🚀 You can now start the application!
   python web_app.py
```

## Benefits

### 1. **Speed**
- Complete setup in seconds instead of minutes
- No need to answer 20+ configuration questions
- Perfect for rapid development cycles

### 2. **Consistency**
- Same configuration every time
- No risk of typos or configuration errors
- Optimized settings for ILM development environment

### 3. **Convenience**
- One command setup after system reset
- All secrets generated automatically
- Users created automatically

### 4. **Flexibility**
- Can still choose manual setup if needed
- Quick setup is optional, not forced
- Easy to modify defaults if needed

## Technical Implementation

### New Function: `quick_setup_with_defaults()`
- Contains all ILM development defaults
- Generates secure secrets automatically
- Creates complete .env file with proper formatting
- Creates admin and reviewer users
- Provides comprehensive feedback

### Integration Points
- Triggered after .env overwrite agreement
- Also available for new .env files
- Falls back to manual setup if declined
- Maintains all existing functionality

## Future Enhancements

Could be extended to support:
- Multiple quick setup profiles (dev, staging, prod)
- Custom default overrides via config file
- Environment-specific quick setups
- Backup and restore of quick setup configurations

This feature significantly improves the development experience by reducing setup time from several minutes to just a few seconds while maintaining all the flexibility of the original script.