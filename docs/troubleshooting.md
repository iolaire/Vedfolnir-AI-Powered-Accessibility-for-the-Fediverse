# Troubleshooting Guide: Platform-Aware Database

This guide provides solutions for common issues encountered with the platform-aware database system and multi-platform support.

## Quick Diagnostics

### System Health Check

Run these commands to quickly assess system health:

```bash
# Check database connectivity
python check_db.py

# Verify platform connections
python -c "
from database import DatabaseManager
from config import Config
db = DatabaseManager(Config())
platforms = db.get_user_platforms(1)
for p in platforms:
    success, msg = p.test_connection()
    print(f'{p.name}: {\"✓\" if success else \"✗\"} {msg}')
"

# Test Ollama connectivity
curl -s http://localhost:11434/api/version || echo "Ollama not accessible"

# Check web application
curl -s http://localhost:5000/health || echo "Web app not running"
```

### Log Analysis

Check recent logs for errors:

```bash
# Main application logs
tail -n 50 logs/vedfolnir.log | grep -i error

# Web application logs
tail -n 50 logs/webapp.log | grep -i error

# Security logs
tail -n 50 logs/security.log | grep -i error
```

## Platform Connection Issues

### Connection Test Failures

#### Problem: "Connection test failed" when adding platform

**Symptoms:**
- Platform connection test fails in web interface
- Error messages about authentication or network issues
- Platform shows as "Inactive" after creation

**Diagnostic Steps:**

1. **Verify credentials:**
   ```bash
   # Test API access manually
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        https://your-instance.com/api/v1/accounts/verify_credentials
   ```

2. **Check network connectivity:**
   ```bash
   # Test basic connectivity
   curl -I https://your-instance.com
   
   # Test API endpoint
   curl https://your-instance.com/api/v1/instance
   ```

3. **Verify SSL/TLS:**
   ```bash
   # Check SSL certificate
   openssl s_client -connect your-instance.com:443 -servername your-instance.com
   ```

**Solutions:**

1. **Credential Issues:**
   - Regenerate access token on the platform
   - Verify token has correct scopes (read, write)
   - Check for typos in credentials
   - Ensure no extra spaces or characters

2. **Network Issues:**
   - Check firewall settings
   - Verify DNS resolution
   - Test from different network if possible

3. **Platform-Specific Issues:**
   
   **For Pixelfed:**
   - Verify instance supports required API endpoints
   - Check if instance has API access restrictions
   - Ensure account is not restricted or suspended
   
   **For Mastodon:**
   - Verify all three credentials (access token, client key, client secret)
   - Check if application needs manual approval
   - Ensure redirect URI is set correctly

### Authentication Errors

#### Problem: 401 Unauthorized errors during processing

**Symptoms:**
- Processing fails with authentication errors
- "Invalid or expired token" messages
- API requests return 401 status codes

**Diagnostic Steps:**

1. **Test token validity:**
   ```bash
   # For Pixelfed
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://your-pixelfed-instance.com/api/v1/accounts/verify_credentials
   
   # For Mastodon
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://your-mastodon-instance.com/api/v1/accounts/verify_credentials
   ```

2. **Check token scopes:**
   ```bash
   # Examine token details (Mastodon)
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://your-mastodon-instance.com/api/v1/apps/verify_credentials
   ```

**Solutions:**

1. **Token Expired:**
   - Regenerate access token on the platform
   - Update platform connection in web interface
   - Test connection after update

2. **Insufficient Scopes:**
   - Recreate application with correct scopes
   - Ensure both 'read' and 'write' scopes are selected
   - Generate new token with proper permissions

3. **Account Issues:**
   - Verify account is not suspended or restricted
   - Check if account has API access permissions
   - Ensure account is verified if required by platform

### Platform Switching Issues

#### Problem: Data doesn't update when switching platforms

**Symptoms:**
- Platform indicator shows new platform but data remains from old platform
- Processing affects wrong platform's data
- Statistics don't match expected platform

**Diagnostic Steps:**

1. **Check session state:**
   ```bash
   # Check current platform context in database
   sqlite3 storage/database/vedfolnir.db "
   SELECT us.session_id, pc.name, pc.platform_type, pc.instance_url 
   FROM user_sessions us 
   JOIN platform_connections pc ON us.active_platform_id = pc.id 
   ORDER BY us.updated_at DESC LIMIT 5;
   "
   ```

2. **Verify platform data isolation:**
   ```bash
   # Check data counts per platform
   sqlite3 storage/database/vedfolnir.db "
   SELECT pc.name, COUNT(p.id) as post_count 
   FROM platform_connections pc 
   LEFT JOIN posts p ON pc.id = p.platform_connection_id 
   GROUP BY pc.id, pc.name;
   "
   ```

**Solutions:**

1. **Clear Browser Cache:**
   - Clear browser cache and cookies
   - Refresh the page
   - Log out and log back in

2. **Session Issues:**
   - Restart web application
   - Clear session data:
     ```bash
     sqlite3 storage/database/vedfolnir.db "DELETE FROM user_sessions;"
     ```

3. **Database Consistency:**
   - Run database integrity check:
     ```bash
     sqlite3 storage/database/vedfolnir.db "PRAGMA integrity_check;"
     ```

## Database Issues

### Migration Problems

#### Problem: Migration script fails

**Symptoms:**
- Migration script exits with errors
- Database schema is incomplete
- Data appears to be missing after migration

**Diagnostic Steps:**

1. **Check database state:**
   ```bash
   # List all tables
   sqlite3 storage/database/vedfolnir.db ".tables"
   
   # Check table schemas
   sqlite3 storage/database/vedfolnir.db ".schema platform_connections"
   ```

2. **Verify data integrity:**
   ```bash
   # Check for foreign key violations
   sqlite3 storage/database/vedfolnir.db "PRAGMA foreign_key_check;"
   
   # Count records in key tables
   sqlite3 storage/database/vedfolnir.db "
   SELECT 'posts' as table_name, COUNT(*) as count FROM posts
   UNION ALL
   SELECT 'images', COUNT(*) FROM images
   UNION ALL
   SELECT 'platform_connections', COUNT(*) FROM platform_connections;
   "
   ```

**Solutions:**

1. **Incomplete Migration:**
   - Restore from backup
   - Re-run migration with debug logging:
     ```bash
     LOG_LEVEL=DEBUG python migrate_to_platform_aware.py
     ```

2. **Permission Issues:**
   - Check database file permissions:
     ```bash
     ls -la storage/database/vedfolnir.db
     ```
   - Ensure write access to database directory

3. **Disk Space Issues:**
   - Check available disk space:
     ```bash
     df -h storage/
     ```
   - Clean up old log files if needed

### Database Corruption

#### Problem: Database corruption errors

**Symptoms:**
- "Database is locked" errors
- "Database disk image is malformed" errors
- Queries fail with database errors

**Diagnostic Steps:**

1. **Check database integrity:**
   ```bash
   sqlite3 storage/database/vedfolnir.db "PRAGMA integrity_check;"
   ```

2. **Identify lock issues:**
   ```bash
   # Check for processes using the database
   lsof storage/database/vedfolnir.db
   ```

**Solutions:**

1. **Database Locked:**
   - Stop all application processes
   - Wait for locks to clear
   - Restart application

2. **Corruption Recovery:**
   ```bash
   # Backup current database
   cp storage/database/vedfolnir.db storage/database/vedfolnir.db.corrupt
   
   # Attempt repair
   sqlite3 storage/database/vedfolnir.db ".recover" | sqlite3 storage/database/vedfolnir_recovered.db
   
   # Replace with recovered database
   mv storage/database/vedfolnir_recovered.db storage/database/vedfolnir.db
   ```

3. **Restore from Backup:**
   ```bash
   # Find latest backup
   ls -la storage/database/vedfolnir_backup_*.db
   
   # Restore from backup
   cp storage/database/vedfolnir_backup_YYYYMMDD_HHMMSS.db storage/database/vedfolnir.db
   ```

## Web Interface Issues

### Login Problems

#### Problem: Cannot log in to web interface

**Symptoms:**
- Login form rejects valid credentials
- "Invalid username or password" errors
- Redirected back to login page

**Diagnostic Steps:**

1. **Check user accounts:**
   ```bash
   sqlite3 storage/database/vedfolnir.db "SELECT id, username, email, is_active FROM users;"
   ```

2. **Verify password hashing:**
   ```bash
   # Test password verification
   python -c "
   from werkzeug.security import check_password_hash
   from database import DatabaseManager
   from config import Config
   db = DatabaseManager(Config())
   user = db.get_user_by_username('admin')
   if user:
       print(f'User found: {user.username}')
       print(f'Password hash: {user.password_hash[:20]}...')
   else:
       print('User not found')
   "
   ```

**Solutions:**

1. **Reset Admin Password:**
   ```bash
   python init_admin_user.py
   ```

2. **Check Flask Configuration:**
   ```bash
   # Verify Flask secret key is set
   grep FLASK_SECRET_KEY .env || echo "FLASK_SECRET_KEY missing"
   ```

3. **Clear Session Data:**
   ```bash
   # Clear user sessions
   sqlite3 storage/database/vedfolnir.db "DELETE FROM user_sessions;"
   ```

### Platform Management Interface Issues

#### Problem: Platform management page doesn't load

**Symptoms:**
- Blank platform management page
- JavaScript errors in browser console
- Platform list doesn't display

**Diagnostic Steps:**

1. **Check browser console:**
   - Open browser developer tools
   - Look for JavaScript errors
   - Check network tab for failed requests

2. **Verify API endpoints:**
   ```bash
   # Test platform API endpoint
   curl -b cookies.txt http://localhost:5000/api/platforms
   ```

**Solutions:**

1. **JavaScript Issues:**
   - Clear browser cache
   - Disable browser extensions
   - Try different browser

2. **API Errors:**
   - Check web application logs:
     ```bash
     tail -f logs/webapp.log
     ```
   - Restart web application

3. **Template Issues:**
   - Verify template files exist:
     ```bash
     ls -la templates/platform_management.html
     ```

## Processing Issues

### No Images Found for Processing

#### Problem: Processing reports no images found

**Symptoms:**
- "No images found for processing" messages
- Processing completes immediately with no results
- User has posts with images but none are processed

**Diagnostic Steps:**

1. **Check user posts:**
   ```bash
   # Verify user exists and has posts
   python -c "
   import asyncio
   from config import Config
   from activitypub_client import ActivityPubClient
   
   async def check_posts():
       config = Config()
       client = ActivityPubClient(config.activitypub)
       posts = await client.get_user_posts('username', limit=10)
       print(f'Found {len(posts)} posts')
       for post in posts[:3]:
           print(f'Post {post.id}: {len(post.media_attachments)} media')
   
   asyncio.run(check_posts())
   "
   ```

2. **Check existing alt text:**
   ```bash
   # Check if images already have alt text
   sqlite3 storage/database/vedfolnir.db "
   SELECT COUNT(*) as images_with_alt_text 
   FROM images 
   WHERE original_alt_text IS NOT NULL AND original_alt_text != '';
   "
   ```

**Solutions:**

1. **User Not Found:**
   - Verify username spelling
   - Check if user account exists on platform
   - Ensure user has public posts

2. **Images Already Have Alt Text:**
   - This is expected behavior
   - Bot only processes images without alt text
   - Check for recent posts without alt text

3. **Platform Configuration:**
   - Verify correct platform is selected
   - Check platform connection is active
   - Test platform connection

### Caption Generation Failures

#### Problem: Caption generation fails or produces poor results

**Symptoms:**
- "Caption generation failed" errors
- Empty or nonsensical captions
- Processing hangs during caption generation

**Diagnostic Steps:**

1. **Test Ollama directly:**
   ```bash
   # Test Ollama service
   curl http://localhost:11434/api/version
   
   # Test model availability
   ollama list | grep llava
   
   # Test caption generation
   echo "Describe this image briefly." | ollama run llava:7b
   ```

2. **Check image processing:**
   ```bash
   # Verify images are being downloaded
   ls -la storage/images/ | head -10
   
   # Check image file sizes
   find storage/images/ -name "*.jpg" -o -name "*.png" | head -5 | xargs ls -la
   ```

**Solutions:**

1. **Ollama Issues:**
   - Restart Ollama service:
     ```bash
     ollama serve
     ```
   - Pull model if missing:
     ```bash
     ollama pull llava:7b
     ```

2. **Image Processing Issues:**
   - Check image download permissions
   - Verify network connectivity to image URLs
   - Check disk space for image storage

3. **Model Performance:**
   - Try different model:
     ```bash
     # In .env file
     OLLAMA_MODEL=llava:13b
     ```
   - Adjust timeout settings:
     ```bash
     OLLAMA_TIMEOUT=120
     ```

## Performance Issues

### Slow Processing

#### Problem: Processing is very slow

**Symptoms:**
- Processing takes much longer than expected
- High CPU or memory usage
- Timeouts during processing

**Diagnostic Steps:**

1. **Monitor system resources:**
   ```bash
   # Check CPU and memory usage
   top -p $(pgrep -f "python main.py")
   
   # Check disk I/O
   iotop -p $(pgrep -f "python main.py")
   ```

2. **Profile database queries:**
   ```bash
   # Enable SQLite query logging
   sqlite3 storage/database/vedfolnir.db "PRAGMA query_only = ON;"
   ```

**Solutions:**

1. **Reduce Batch Size:**
   ```bash
   # Process fewer posts per run
   MAX_POSTS_PER_RUN=10 python main.py --users username
   ```

2. **Optimize Database:**
   ```bash
   # Analyze and vacuum database
   sqlite3 storage/database/vedfolnir.db "ANALYZE; VACUUM;"
   ```

3. **Adjust Rate Limiting:**
   ```bash
   # Increase delays between requests
   USER_PROCESSING_DELAY=10 python main.py --users username
   ```

### Memory Issues

#### Problem: High memory usage or out of memory errors

**Symptoms:**
- Python process uses excessive memory
- "MemoryError" exceptions
- System becomes unresponsive

**Solutions:**

1. **Reduce Image Processing:**
   ```bash
   # Limit concurrent image processing
   MAX_CONCURRENT_IMAGES=2 python main.py --users username
   ```

2. **Clear Image Cache:**
   ```bash
   # Clean up downloaded images
   find storage/images/ -mtime +7 -delete
   ```

3. **Optimize Model Usage:**
   ```bash
   # Use smaller model
   OLLAMA_MODEL=llava:7b python main.py --users username
   ```

## Security Issues

### Credential Security

#### Problem: Concerns about credential storage security

**Diagnostic Steps:**

1. **Verify encryption:**
   ```bash
   # Check that credentials are encrypted in database
   sqlite3 storage/database/vedfolnir.db "SELECT access_token FROM platform_connections LIMIT 1;"
   # Should show encrypted data, not plaintext
   ```

2. **Check encryption key:**
   ```bash
   # Verify encryption key is set
   grep PLATFORM_ENCRYPTION_KEY .env
   ```

**Solutions:**

1. **Regenerate Encryption Key:**
   ```bash
   # Generate new encryption key
   python -c "from cryptography.fernet import Fernet; print(f'PLATFORM_ENCRYPTION_KEY={Fernet.generate_key().decode()}')"
   ```

2. **Rotate Platform Credentials:**
   - Regenerate access tokens on platforms
   - Update platform connections in web interface
   - Test connections after update

### Access Control Issues

#### Problem: Users can access other users' data

**Diagnostic Steps:**

1. **Check user isolation:**
   ```bash
   # Verify platform connections are user-specific
   sqlite3 storage/database/vedfolnir.db "
   SELECT u.username, pc.name, pc.platform_type 
   FROM users u 
   JOIN platform_connections pc ON u.id = pc.user_id 
   ORDER BY u.username;
   "
   ```

**Solutions:**

1. **Review User Permissions:**
   - Check user roles and permissions
   - Verify session management
   - Test with different user accounts

2. **Update Security Configuration:**
   ```bash
   # Enable security features
   echo "SECURITY_HEADERS_ENABLED=true" >> .env
   echo "RATE_LIMIT_ENABLED=true" >> .env
   ```

## Getting Help

### Collecting Diagnostic Information

When seeking help, collect this information:

1. **System Information:**
   ```bash
   # System details
   uname -a
   python --version
   pip list | grep -E "(flask|sqlalchemy|cryptography)"
   ```

2. **Configuration (sanitized):**
   ```bash
   # Show configuration without sensitive data
   grep -v -E "(TOKEN|SECRET|KEY)" .env
   ```

3. **Recent Logs:**
   ```bash
   # Collect recent logs
   tail -n 100 logs/vedfolnir.log > debug_logs.txt
   tail -n 100 logs/webapp.log >> debug_logs.txt
   ```

4. **Database State:**
   ```bash
   # Database statistics
   sqlite3 storage/database/vedfolnir.db "
   SELECT 'users' as table_name, COUNT(*) as count FROM users
   UNION ALL
   SELECT 'platform_connections', COUNT(*) FROM platform_connections
   UNION ALL
   SELECT 'posts', COUNT(*) FROM posts
   UNION ALL
   SELECT 'images', COUNT(*) FROM images;
   " > database_stats.txt
   ```

### Support Channels

1. **Check Documentation:**
   - Platform Setup Guide: `docs/platform_setup.md`
   - Migration Guide: `docs/migration_guide.md`
   - API Documentation: `docs/api_documentation.md`

2. **Search Existing Issues:**
   - Check GitHub issues for similar problems
   - Look for closed issues with solutions

3. **Create New Issue:**
   - Include diagnostic information
   - Provide steps to reproduce
   - Specify platform types and versions
   - Include relevant log excerpts (sanitized)

### Emergency Procedures

#### Complete System Reset

If all else fails, you can reset the system:

```bash
# 1. Backup everything
cp -r storage storage_emergency_backup_$(date +%Y%m%d_%H%M%S)
cp .env .env.emergency_backup

# 2. Stop all processes
pkill -f "python web_app.py"
pkill -f "python main.py"

# 3. Reset database
rm storage/database/vedfolnir.db
python migrate_to_platform_aware.py

# 4. Recreate admin user
python init_admin_user.py

# 5. Re-add platform connections through web interface
python web_app.py
```

#### Data Recovery

If you need to recover data from backups:

```bash
# Find available backups
ls -la storage/database/vedfolnir_backup_*.db

# Restore specific backup
cp storage/database/vedfolnir_backup_YYYYMMDD_HHMMSS.db storage/database/vedfolnir.db

# Verify restored data
python check_db.py
```

This troubleshooting guide should help resolve most common issues with the platform-aware database system. For complex issues, don't hesitate to seek support with detailed diagnostic information.