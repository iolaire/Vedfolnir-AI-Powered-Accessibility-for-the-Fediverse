# Multi-Platform Setup Guide

This guide provides detailed instructions for setting up the Vedfolnir with both Pixelfed and Mastodon platforms.

## Overview

The Vedfolnir supports multiple ActivityPub platforms through a platform adapter architecture. Each platform has specific requirements and setup procedures.

## Supported Platforms

| Platform | Status | API Type | OAuth2 Required |
|----------|--------|----------|-----------------|
| Pixelfed | ✅ Full Support | `pixelfed` | No |
| Mastodon | ✅ Full Support | `mastodon` | Yes |

## Platform Selection

Set the platform type in your `.env` file:

```bash
# For Pixelfed
ACTIVITYPUB_API_TYPE=pixelfed

# For Mastodon
ACTIVITYPUB_API_TYPE=mastodon
```

If not specified, the system defaults to `pixelfed` for backward compatibility.

## Pixelfed Setup

### Prerequisites

- Access to a Pixelfed instance
- Account with posting permissions
- Basic understanding of API tokens

### Step-by-Step Setup

#### 1. Create Pixelfed Application

1. **Log in to your Pixelfed instance**
   - Navigate to `https://your-pixelfed-instance.com`

2. **Access Developer Settings**
   - Go to Settings → Applications
   - URL: `https://your-pixelfed-instance.com/settings/applications`

3. **Create New Application**
   - Click "Create New Application" or similar button
   - Fill in application details:
     - **Name**: `Vedfolnir`
     - **Description**: `Automated alt text generation for accessibility`
     - **Website**: (optional) Your website or repository URL
     - **Scopes**: Select `read` and `write`
       - `read`: Required to fetch user posts and media
       - `write`: Required to update media descriptions

4. **Save and Get Token**
   - Click "Create" or "Save"
   - Copy the generated **Access Token**
   - Store it securely - you won't be able to see it again

#### 2. Configure Environment

Create your configuration file:

```bash
# Copy the Pixelfed example
cp .env.example.pixelfed .env

# Edit with your details
nano .env
```

Required configuration:

```bash
# Platform Configuration
ACTIVITYPUB_API_TYPE=pixelfed
ACTIVITYPUB_INSTANCE_URL=https://your-pixelfed-instance.com
ACTIVITYPUB_USERNAME=your_username
ACTIVITYPUB_ACCESS_TOKEN=your_access_token_here

# Optional: HTTP Signature Keys (for enhanced security)
# PRIVATE_KEY_PATH=path/to/private.key
# PUBLIC_KEY_PATH=path/to/public.key
```

#### 3. Test Configuration

```bash
# Validate configuration
python validate_config.py

# Test API access
python -c "
import asyncio
from config import Config
from activitypub_client import ActivityPubClient

async def test():
    config = Config()
    client = ActivityPubClient(config.activitypub)
    try:
        posts = await client.get_user_posts('$ACTIVITYPUB_USERNAME', limit=1)
        print(f'✅ Success: Found {len(posts)} posts')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"
```

### Pixelfed-Specific Configuration Options

```bash
# Rate limiting (Pixelfed typically has conservative limits)
RATE_LIMIT_PIXELFED_MINUTE=60
RATE_LIMIT_PIXELFED_HOUR=1000
RATE_LIMIT_PIXELFED_DAY=10000

# Endpoint-specific limits
RATE_LIMIT_PIXELFED_ENDPOINT_MEDIA_MINUTE=30
RATE_LIMIT_PIXELFED_ENDPOINT_STATUSES_MINUTE=40

# Processing settings
MAX_POSTS_PER_RUN=50
USER_PROCESSING_DELAY=5
```

## Mastodon Setup

### Prerequisites

- Access to a Mastodon instance
- Account with posting permissions
- Understanding of OAuth2 applications

### Step-by-Step Setup

#### 1. Create Mastodon Application

1. **Log in to your Mastodon instance**
   - Navigate to `https://your-mastodon-instance.com`

2. **Access Developer Settings**
   - Go to Preferences → Development
   - URL: `https://your-mastodon-instance.com/settings/applications`

3. **Create New Application**
   - Click "New Application"
   - Fill in application details:
     - **Application name**: `Vedfolnir`
     - **Application website**: (optional) Your website or repository URL
     - **Redirect URI**: `urn:ietf:wg:oauth:2.0:oob`
       - This is for command-line applications
       - Do not change this value
     - **Scopes**: Check the following boxes:
       - ✅ `read` - Read access to your account
       - ✅ `write` - Write access to your account
       - ❌ `follow` - Not needed
       - ❌ `push` - Not needed

4. **Submit and Get Credentials**
   - Click "Submit"
   - You'll be redirected to your application page
   - Copy the following three values:
     - **Client key** (also called Client ID)
     - **Client secret**
     - **Your access token**

#### 2. Configure Environment

Create your configuration file:

```bash
# Copy the Mastodon example
cp .env.example.mastodon .env

# Edit with your details
nano .env
```

Required configuration:

```bash
# Platform Configuration
ACTIVITYPUB_API_TYPE=mastodon
ACTIVITYPUB_INSTANCE_URL=https://your-mastodon-instance.com
ACTIVITYPUB_USERNAME=your_username
ACTIVITYPUB_ACCESS_TOKEN=your_access_token_here

# Mastodon OAuth2 Credentials
MASTODON_CLIENT_KEY=your_client_key_here
MASTODON_CLIENT_SECRET=your_client_secret_here
```

#### 3. Test Configuration

```bash
# Validate configuration
python validate_config.py

# Test OAuth2 authentication
curl -X POST \
     -F "client_id=$MASTODON_CLIENT_KEY" \
     -F "client_secret=$MASTODON_CLIENT_SECRET" \
     -F "grant_type=client_credentials" \
     https://your-mastodon-instance.com/oauth/token

# Test API access
python -c "
import asyncio
from config import Config
from activitypub_client import ActivityPubClient

async def test():
    config = Config()
    client = ActivityPubClient(config.activitypub)
    try:
        posts = await client.get_user_posts('$ACTIVITYPUB_USERNAME', limit=1)
        print(f'✅ Success: Found {len(posts)} posts')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"
```

### Mastodon-Specific Configuration Options

```bash
# Rate limiting (Mastodon typically allows higher limits)
RATE_LIMIT_MASTODON_MINUTE=300
RATE_LIMIT_MASTODON_HOUR=3000
RATE_LIMIT_MASTODON_DAY=30000

# Endpoint-specific limits
RATE_LIMIT_MASTODON_ENDPOINT_MEDIA_MINUTE=100
RATE_LIMIT_MASTODON_ENDPOINT_STATUSES_MINUTE=200
RATE_LIMIT_MASTODON_ENDPOINT_ACCOUNTS_MINUTE=150

# Processing settings
MAX_POSTS_PER_RUN=50
USER_PROCESSING_DELAY=5
```

## Common Configuration

### Ollama Setup

Both platforms require Ollama for AI caption generation:

```bash
# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b
OLLAMA_TIMEOUT=60.0

# Install and setup Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llava:7b
ollama serve
```

### Caption Configuration

```bash
# Caption settings
CAPTION_MAX_LENGTH=500
CAPTION_OPTIMAL_MIN_LENGTH=80
CAPTION_OPTIMAL_MAX_LENGTH=200

# Enhanced classification
USE_ENHANCED_CLASSIFICATION=true
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
```

### Processing Configuration

```bash
# Processing limits
MAX_POSTS_PER_RUN=50
MAX_USERS_PER_RUN=10
USER_PROCESSING_DELAY=5

# Retry configuration
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=30.0
RETRY_USE_JITTER=true
```

## Migration Between Platforms

### From Pixelfed to Mastodon

1. **Backup existing data:**
   ```bash
   cp .env .env.pixelfed.backup
   cp storage/database/vedfolnir.db storage/database/vedfolnir.db.backup
   ```

2. **Update configuration:**
   ```bash
   # Change platform type
   sed -i 's/ACTIVITYPUB_API_TYPE=pixelfed/ACTIVITYPUB_API_TYPE=mastodon/' .env
   
   # Add Mastodon credentials
   echo "MASTODON_CLIENT_KEY=your_client_key" >> .env
   echo "MASTODON_CLIENT_SECRET=your_client_secret" >> .env
   ```

3. **Test new configuration:**
   ```bash
   python validate_config.py
   ```

### From Mastodon to Pixelfed

1. **Backup existing data:**
   ```bash
   cp .env .env.mastodon.backup
   cp storage/database/vedfolnir.db storage/database/vedfolnir.db.backup
   ```

2. **Update configuration:**
   ```bash
   # Change platform type
   sed -i 's/ACTIVITYPUB_API_TYPE=mastodon/ACTIVITYPUB_API_TYPE=pixelfed/' .env
   
   # Remove Mastodon-specific settings (optional)
   sed -i '/MASTODON_CLIENT_/d' .env
   ```

3. **Test new configuration:**
   ```bash
   python validate_config.py
   ```

## Multi-Instance Setup

You can run the bot for multiple instances by creating separate configuration files:

### Directory Structure

```
vedfolnir/
├── .env.mastodon.social
├── .env.pixelfed.social
├── .env.my.instance
└── scripts/
    ├── run-mastodon-social.sh
    ├── run-pixelfed-social.sh
    └── run-my-instance.sh
```

### Example Scripts

**run-mastodon-social.sh:**
```bash
#!/bin/bash
export $(cat .env.mastodon.social | xargs)
python main.py --users "$@"
```

**run-pixelfed-social.sh:**
```bash
#!/bin/bash
export $(cat .env.pixelfed.social | xargs)
python main.py --users "$@"
```

### Usage

```bash
# Run for different instances
./scripts/run-mastodon-social.sh user1 user2
./scripts/run-pixelfed-social.sh user3 user4
```

## Platform Comparison

### Feature Comparison

| Feature | Pixelfed | Mastodon | Notes |
|---------|----------|----------|-------|
| OAuth2 Required | No | Yes | Mastodon requires client credentials |
| Rate Limits | Conservative | Generous | Mastodon typically allows more requests |
| Media Update API | Direct | Standard | Both support media description updates |
| Post Formats | Image-focused | Mixed content | Pixelfed optimized for images |
| Instance Variety | Moderate | High | More Mastodon instances available |

### API Differences

**Pixelfed:**
- Simpler authentication (access token only)
- Image-focused API endpoints
- Direct media update support
- Conservative rate limiting

**Mastodon:**
- OAuth2 authentication required
- General-purpose API
- Standard ActivityPub implementation
- Higher rate limits typically

### Performance Considerations

**Pixelfed:**
- Faster authentication
- Optimized for image content
- Lower rate limits may slow processing

**Mastodon:**
- More authentication overhead
- Higher rate limits allow faster processing
- Mixed content types may require filtering

## Troubleshooting Platform-Specific Issues

### Pixelfed Issues

**Problem:** Access token not working
```bash
# Test token manually
curl -H "Authorization: Bearer $ACTIVITYPUB_ACCESS_TOKEN" \
     "$ACTIVITYPUB_INSTANCE_URL/api/v1/accounts/verify_credentials"
```

**Problem:** Rate limiting too aggressive
```bash
# Reduce request rate
echo "USER_PROCESSING_DELAY=10" >> .env
echo "RATE_LIMIT_PIXELFED_MINUTE=30" >> .env
```

### Mastodon Issues

**Problem:** OAuth2 authentication failing
```bash
# Test OAuth2 credentials
curl -X POST \
     -F "client_id=$MASTODON_CLIENT_KEY" \
     -F "client_secret=$MASTODON_CLIENT_SECRET" \
     -F "grant_type=client_credentials" \
     "$ACTIVITYPUB_INSTANCE_URL/oauth/token"
```

**Problem:** Application not approved
- Some Mastodon instances require manual approval
- Contact instance administrator
- Check instance policies

### Common Issues

**Problem:** Instance not responding
```bash
# Test instance connectivity
curl -I "$ACTIVITYPUB_INSTANCE_URL"

# Check instance status
curl "$ACTIVITYPUB_INSTANCE_URL/api/v1/instance"
```

**Problem:** User not found
```bash
# Test user lookup
curl -H "Authorization: Bearer $ACTIVITYPUB_ACCESS_TOKEN" \
     "$ACTIVITYPUB_INSTANCE_URL/api/v1/accounts/lookup?acct=$ACTIVITYPUB_USERNAME"
```

## Best Practices

### Security

1. **Store credentials securely:**
   ```bash
   chmod 600 .env
   ```

2. **Use environment-specific configurations:**
   - Development: Use test instances
   - Production: Use secure, long-lived tokens

3. **Rotate credentials regularly:**
   - Regenerate access tokens periodically
   - Update OAuth2 applications as needed

### Performance

1. **Optimize rate limiting:**
   - Use platform-specific rate limits
   - Monitor API usage
   - Adjust delays based on instance performance

2. **Batch processing:**
   - Process multiple users efficiently
   - Use appropriate delays between requests
   - Monitor system resources

### Monitoring

1. **Log analysis:**
   ```bash
   # Monitor platform-specific errors
   tail -f logs/vedfolnir.log | grep -E "(pixelfed|mastodon)"
   
   # Check rate limiting
   tail -f logs/vedfolnir.log | grep "rate limit"
   ```

2. **Health checks:**
   ```bash
   # Test platform connectivity
   python validate_config.py
   
   # Monitor API responses
   curl "$ACTIVITYPUB_INSTANCE_URL/api/v1/instance"
   ```

This multi-platform setup guide should help you successfully configure the Vedfolnir for both Pixelfed and Mastodon instances. Choose the platform that best fits your needs and follow the appropriate setup instructions.