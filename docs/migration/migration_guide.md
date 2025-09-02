# Migration Guide: Platform-Aware Database

This guide provides step-by-step instructions for migrating from the environment variable-based configuration to the new platform-aware database system.

## Overview

The Vedfolnir has been upgraded to support multiple platform connections through a database-driven system. This migration:

- Converts environment-based configuration to database platform connections
- Preserves all existing data (posts, images, processing runs)
- Adds platform identification to all data
- Enables multi-platform support through the web interface
- Maintains backward compatibility during the transition

## Pre-Migration Checklist

### 1. Backup Your Data

**Critical: Always backup your data before migration**

```bash
# Backup the entire storage directory
cp -r stigrate_to_platbackup_$(date +%Y%m%d_%H%M%S)

# Backup the database specifically
cp storage/database/vedfolnir.db storage/database/vedfolnir_backup_$(date +%Y%m%d_%H%M%S).db

# Backup your configuration
cp .env .env.backup
```

### 2. Verify Current Configuration

```bash
# Test your current configuration
python validate_config.py

# Check database contents
python check_db.py
```

### 3. Note Your Current Settings

Document your current environment variables:

```bash
# Display current configuration (sensitive data will be masked)
grep -E '^(ACTIVITYPUB_|MASTODON_)' .env
```

Common variables to note:
- `ACTIVITYPUB_API_TYPE`
- `ACTIVITYPUB_INSTANCE_URL`
- `ACTIVITYPUB_USERNAME`
- `ACTIVITYPUB_ACCESS_TOKEN`
- `MASTODON_CLIENT_KEY` (if using Mastodon)
- `MASTODON_CLIENT_SECRET` (if using Mastodon)

## Migration Process

### Step 1: Update Dependencies

```bash
# Install new dependencies for encryption and platform management
pip install -r requirements.txt
```

### Step 2: Run the Migration Script

```bash
# Run the platform-aware migration
python migrate_to_platform_aware.py
```

The migration script will:

1. **Create new database tables:**
   - `platform_connections` - Store encrypted platform credentials
   - `user_sessions` - Track user platform context

2. **Add platform columns to existing tables:**
   - Add `platform_connection_id` to posts, images, processing_runs
   - Add `platform_type` and `instance_url` for backward compatibility

3. **Create default platform connection:**
   - Convert your current `.env` configuration to a database platform connection
   - Encrypt and store your credentials securely

4. **Migrate existing data:**
   - Associate all existing posts, images, and processing runs with the default platform
   - Preserve all data integrity and relationships

5. **Create performance indexes:**
   - Add database indexes for efficient platform-based queries

### Step 3: Verify Migration Results

```bash
# Check migration status
python check_db.py

# Verify platform connections
python -c "
from database import DatabaseManager
from config import Config
db = DatabaseManager(Config())
platforms = db.get_user_platforms(1)  # Assuming user ID 1
for p in platforms:
    print(f'Platform: {p.name} ({p.platform_type}) - {p.instance_url}')
"
```

### Step 4: Test the Web Interface

```bash
# Start the web application
python web_app.py
```

1. **Log in to the web interface** at `http://localhost:5000`
2. **Navigate to Platform Management**
3. **Verify your migrated platform appears**
4. **Test the platform connection**

### Step 5: Test Processing

```bash
# Test processing with the migrated setup
python main.py --users your_username --log-level DEBUG
```

Verify that:
- Posts are processed correctly
- Images are associated with the right platform
- Processing runs are recorded properly

## Migration Scenarios

### Scenario 1: Single Pixelfed Instance

**Before migration (.env):**
```bash
ACTIVITYPUB_API_TYPE=pixelfed
ACTIVITYPUB_INSTANCE_URL=https://pixelfed.social
ACTIVITYPUB_USERNAME=myusername
ACTIVITYPUB_ACCESS_TOKEN=abc123...
```

**After migration:**
- Platform connection created: "Default Pixelfed" (pixelfed)
- All existing data associated with this platform
- Web interface shows platform context

### Scenario 2: Single Mastodon Instance

**Before migration (.env):**
```bash
ACTIVITYPUB_API_TYPE=mastodon
ACTIVITYPUB_INSTANCE_URL=https://mastodon.social
ACTIVITYPUB_USERNAME=myusername
ACTIVITYPUB_ACCESS_TOKEN=def456...
MASTODON_CLIENT_KEY=ghi789...
MASTODON_CLIENT_SECRET=jkl012...
```

**After migration:**
- Platform connection created: "Default Mastodon" (mastodon)
- All credentials encrypted and stored securely
- All existing data preserved and associated

### Scenario 3: Fresh Installation

**If you don't have existing data:**
- Migration creates the new database schema
- No data migration needed
- Ready to add platform connections through web interface

## Post-Migration Tasks

### 1. Add Additional Platforms

After migration, you can add more platform connections:

1. **Navigate to Platform Management in the web interface**
2. **Click "Add Platform"**
3. **Configure additional Pixelfed or Mastodon instances**
4. **Test each connection**

### 2. Update Environment Variables (Optional)

You can now remove platform-specific environment variables:

```bash
# Create a minimal .env for system settings only
cat > .env << EOF
# System Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b
LOG_LEVEL=INFO

# Web Interface
FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
AUTH_ADMIN_PASSWORD=your_secure_password

# Security
PLATFORM_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
EOF
```

### 3. Update Scripts and Automation

If you have scripts that rely on environment variables:

**Before:**
```bash
# Old way - environment variables
export ACTIVITYPUB_INSTANCE_URL=https://pixelfed.social
python main.py --users username
```

**After:**
```bash
# New way - platform context managed automatically
python main.py --users username
```

### 4. Configure User Access

Set up additional users if needed:

```bash
# Create additional users
python init_admin_user.py
```

Each user can manage their own platform connections independently.

## Rollback Procedure

If you need to rollback the migration:

### Step 1: Stop the Application

```bash
# Stop any running processes
pkill -f "python web_app.py"
pkill -f "python main.py"
```

### Step 2: Restore Database Backup

```bash
# Restore the database backup
cp storage/database/vedfolnir_backup_YYYYMMDD_HHMMSS.db storage/database/vedfolnir.db
```

### Step 3: Restore Configuration

```bash
# Restore environment configuration
cp .env.backup .env
```

### Step 4: Downgrade Code (if needed)

```bash
# If you need to revert to a previous version
git checkout previous_version_tag
pip install -r requirements.txt
```

### Step 5: Verify Rollback

```bash
# Test the rolled-back configuration
python validate_config.py
python main.py --users username --log-level DEBUG
```

## Troubleshooting

### Migration Fails

**Problem:** Migration script fails with database errors

**Solutions:**
1. **Check database permissions:**
   ```bash
   ls -la storage/database/
   ```

2. **Verify database integrity:**
   ```bash
   sqlite3 storage/database/vedfolnir.db "PRAGMA integrity_check;"
   ```

3. **Check disk space:**
   ```bash
   df -h storage/
   ```

4. **Review migration logs:**
   ```bash
   tail -f logs/migration.log
   ```

### Missing Environment Variables

**Problem:** Migration can't find required environment variables

**Solutions:**
1. **Verify .env file exists and is readable:**
   ```bash
   ls -la .env
   cat .env | grep ACTIVITYPUB
   ```

2. **Set missing variables:**
   ```bash
   # Add missing variables to .env
   echo "ACTIVITYPUB_API_TYPE=pixelfed" >> .env
   ```

### Credential Encryption Fails

**Problem:** Error encrypting platform credentials

**Solutions:**
1. **Generate encryption key:**
   ```bash
   python -c "from cryptography.fernet import Fernet; print(f'PLATFORM_ENCRYPTION_KEY={Fernet.generate_key().decode()}')" >> .env
   ```

2. **Check cryptography installation:**
   ```bash
   pip install --upgrade cryptography
   ```

### Web Interface Issues

**Problem:** Can't access platform management after migration

**Solutions:**
1. **Check user authentication:**
   ```bash
   python init_admin_user.py
   ```

2. **Verify Flask secret key:**
   ```bash
   grep FLASK_SECRET_KEY .env || echo "FLASK_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
   ```

3. **Check web app logs:**
   ```bash
   tail -f logs/webapp.log
   ```

### Data Integrity Issues

**Problem:** Data appears to be missing or corrupted after migration

**Solutions:**
1. **Check data counts before and after:**
   ```bash
   # Before migration (from backup)
   sqlite3 storage_backup/database/vedfolnir.db "SELECT COUNT(*) FROM posts;"
   
   # After migration
   sqlite3 storage/database/vedfolnir.db "SELECT COUNT(*) FROM posts;"
   ```

2. **Verify platform associations:**
   ```bash
   sqlite3 storage/database/vedfolnir.db "SELECT COUNT(*) FROM posts WHERE platform_connection_id IS NOT NULL;"
   ```

3. **Check foreign key constraints:**
   ```bash
   sqlite3 storage/database/vedfolnir.db "PRAGMA foreign_key_check;"
   ```

## Performance Considerations

### Database Optimization

After migration, optimize database performance:

```bash
# Analyze database statistics
sqlite3 storage/database/vedfolnir.db "ANALYZE;"

# Vacuum database to reclaim space
sqlite3 storage/database/vedfolnir.db "VACUUM;"
```

### Index Verification

Verify that performance indexes were created:

```bash
sqlite3 storage/database/vedfolnir.db ".indexes"
```

Expected indexes:
- `idx_platform_connections_user`
- `idx_platform_connections_active`
- `idx_posts_platform_connection`
- `idx_posts_platform_type`
- `idx_images_platform_connection`
- `idx_processing_runs_platform_connection`

## Security Considerations

### Credential Security

After migration:

1. **Verify encryption:** Credentials should not be readable in the database
2. **Secure the encryption key:** Store `PLATFORM_ENCRYPTION_KEY` securely
3. **Update access controls:** Ensure only authorized users can access platform management
4. **Monitor access:** Check logs for unauthorized access attempts

### Environment Cleanup

Remove sensitive data from environment files:

```bash
# Create a clean environment file
grep -v -E '^(ACTIVITYPUB_ACCESS_TOKEN|MASTODON_CLIENT)' .env > .env.clean
mv .env.clean .env
```

## Validation and Testing

### Post-Migration Validation

Run comprehensive tests after migration:

```bash
# Test configuration
python validate_config.py

# Test database integrity
python check_db.py

# Test platform connections
python -c "
from database import DatabaseManager
from config import Config
db = DatabaseManager(Config())
platforms = db.get_user_platforms(1)
for p in platforms:
    success, message = p.test_connection()
    print(f'{p.name}: {\"✓\" if success else \"✗\"} {message}')
"

# Test processing
python main.py --users test_username --log-level DEBUG
```

### Performance Testing

Test performance with the new schema:

```bash
# Time a typical query
time python -c "
from database import DatabaseManager
from config import Config
db = DatabaseManager(Config())
db.set_platform_context(1, 1)  # user_id=1, platform_id=1
posts = db.get_posts_for_platform(limit=100)
print(f'Retrieved {len(posts)} posts')
"
```

## Support and Resources

### Getting Help

If you encounter issues during migration:

1. **Check the logs:** Review all log files in the `logs/` directory
2. **Verify backups:** Ensure your backups are complete and accessible
3. **Test rollback:** Verify that rollback procedures work before proceeding
4. **Document issues:** Note specific error messages and steps that led to them
5. **Seek support:** Create detailed issue reports with logs and configuration details

### Additional Resources

- **Platform Setup Guide:** `docs/platform_setup.md`
- **Troubleshooting Guide:** `docs/troubleshooting.md`
- **API Documentation:** `docs/api_documentation.md`
- **Security Documentation:** `security/security_checklist.md`

This migration guide should help you successfully upgrade to the platform-aware database system while preserving all your existing data and functionality.