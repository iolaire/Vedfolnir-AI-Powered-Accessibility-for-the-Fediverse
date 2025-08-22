# Troubleshooting Guide: MySQL-Based Vedfolnir

This guide provides solutions for common issues encountered with the MySQL-based Vedfolnir system, including database connectivity, platform management, and performance optimization.

## Quick Diagnostics

### System Health Check

Run these commands to quickly assess system health:

```bash
# Check MySQL database connectivity
python -c "
from database import get_db_connection
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    result = cursor.fetchone()
    conn.close()
    print('✓ MySQL database connection: OK')
except Exception as e:
    print(f'✗ MySQL database connection: FAILED - {e}')
"

# Check Redis connectivity
python -c "
import redis
try:
    r = redis.Redis.from_url('redis://localhost:6379/0')
    r.ping()
    print('✓ Redis connection: OK')
except Exception as e:
    print(f'✗ Redis connection: FAILED - {e}')
"

# Verify platform connections
python -c "
from database import DatabaseManager
from config import Config
try:
    db = DatabaseManager(Config())
    platforms = db.get_user_platforms(1)
    for p in platforms:
        success, msg = p.test_connection()
        print(f'{p.name}: {\"✓\" if success else \"✗\"} {msg}')
except Exception as e:
    print(f'Platform check failed: {e}')
"

# Test Ollama connectivity
curl -s http://localhost:11434/api/version || echo "✗ Ollama not accessible"

# Check web application
curl -s http://localhost:5000/health || echo "✗ Web app not running"
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

# MySQL error logs (system-dependent)
sudo tail -n 50 /var/log/mysql/error.log | grep -i error

# Redis logs
sudo tail -n 50 /var/log/redis/redis-server.log | grep -i error
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

1. **Check session state in Redis:**
   ```bash
   # Check current session data
   redis-cli keys "vedfolnir:session:*"
   
   # Examine session content (replace with actual session ID)
   redis-cli hgetall "vedfolnir:session:session_id_here"
   ```

2. **Check MySQL session data:**
   ```bash
   # Check user sessions and active platforms
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       us.session_id, 
       us.user_id,
       us.active_platform_id,
       pc.name as platform_name, 
       pc.platform_type, 
       pc.instance_url,
       us.updated_at
   FROM user_sessions us 
   LEFT JOIN platform_connections pc ON us.active_platform_id = pc.id 
   ORDER BY us.updated_at DESC 
   LIMIT 5;
   "
   ```

3. **Verify platform data isolation:**
   ```bash
   # Check data counts per platform
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       pc.name, 
       pc.platform_type,
       COUNT(p.id) as post_count 
   FROM platform_connections pc 
   LEFT JOIN posts p ON pc.id = p.platform_connection_id 
   GROUP BY pc.id, pc.name, pc.platform_type
   ORDER BY pc.name;
   "
   ```

**Solutions:**

1. **Clear Browser Cache:**
   - Clear browser cache and cookies
   - Refresh the page
   - Log out and log back in

2. **Session Issues:**
   ```bash
   # Restart web application
   pkill -f "python web_app.py"
   python web_app.py
   
   # Clear Redis session data
   redis-cli FLUSHDB
   
   # Or clear specific user sessions in MySQL
   mysql -u vedfolnir -p vedfolnir -e "DELETE FROM user_sessions WHERE user_id = 1;"
   ```

3. **Database Consistency:**
   ```bash
   # Check MySQL database integrity
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       table_name,
       CASE 
           WHEN table_name = 'users' THEN (SELECT COUNT(*) FROM users)
           WHEN table_name = 'platform_connections' THEN (SELECT COUNT(*) FROM platform_connections)
           WHEN table_name = 'posts' THEN (SELECT COUNT(*) FROM posts)
           WHEN table_name = 'captions' THEN (SELECT COUNT(*) FROM captions)
       END as record_count
   FROM information_schema.tables 
   WHERE table_schema = 'vedfolnir' 
   AND table_name IN ('users', 'platform_connections', 'posts', 'captions');
   "
   
   # Check for orphaned records
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 'Orphaned posts' as issue, COUNT(*) as count
   FROM posts p 
   LEFT JOIN platform_connections pc ON p.platform_connection_id = pc.id 
   WHERE pc.id IS NULL
   UNION ALL
   SELECT 'Orphaned captions', COUNT(*)
   FROM captions c 
   LEFT JOIN posts p ON c.post_id = p.id 
   WHERE p.id IS NULL;
   "
   ```

4. **Platform Connection Validation:**
   ```bash
   # Test all platform connections
   python -c "
   from database import DatabaseManager
   from config import Config
   
   db = DatabaseManager(Config())
   platforms = db.get_all_platform_connections()
   
   for platform in platforms:
       try:
           success, message = platform.test_connection()
           status = '✓' if success else '✗'
           print(f'{platform.name} ({platform.platform_type}): {status} {message}')
       except Exception as e:
           print(f'{platform.name}: ✗ Error - {e}')
   "
   ```

## Database Issues

### MySQL Connection Problems

#### Problem: "Can't connect to MySQL server" errors

**Symptoms:**
- Application fails to start with MySQL connection errors
- "Connection refused" or "Access denied" messages
- Database operations timeout or fail

**Diagnostic Steps:**

1. **Check MySQL service status:**
   ```bash
   # Check if MySQL is running
   sudo systemctl status mysql
   # or for Docker
   docker-compose ps mysql
   
   # Check MySQL process
   ps aux | grep mysql
   ```

2. **Test MySQL connectivity:**
   ```bash
   # Test connection with credentials
   mysql -h localhost -u vedfolnir -p vedfolnir
   
   # Test from application context
   python -c "
   import pymysql
   try:
       conn = pymysql.connect(
           host='localhost',
           user='vedfolnir',
           password='your_password',
           database='vedfolnir',
           charset='utf8mb4'
       )
       print('✓ MySQL connection successful')
       conn.close()
   except Exception as e:
       print(f'✗ MySQL connection failed: {e}')
   "
   ```

3. **Check MySQL configuration:**
   ```bash
   # Check MySQL configuration
   mysql -u root -p -e "SHOW VARIABLES LIKE 'bind_address';"
   mysql -u root -p -e "SHOW VARIABLES LIKE 'port';"
   
   # Check user privileges
   mysql -u root -p -e "SELECT user, host FROM mysql.user WHERE user='vedfolnir';"
   mysql -u root -p -e "SHOW GRANTS FOR 'vedfolnir'@'localhost';"
   ```

**Solutions:**

1. **MySQL Service Issues:**
   ```bash
   # Start MySQL service
   sudo systemctl start mysql
   sudo systemctl enable mysql
   
   # For Docker
   docker-compose up -d mysql
   ```

2. **Connection Configuration:**
   ```bash
   # Update MySQL bind address (if needed)
   sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
   # Change: bind-address = 0.0.0.0
   
   # Restart MySQL
   sudo systemctl restart mysql
   ```

3. **User and Permissions:**
   ```sql
   -- Connect as root and fix user permissions
   mysql -u root -p
   
   -- Recreate user if needed
   DROP USER IF EXISTS 'vedfolnir'@'localhost';
   CREATE USER 'vedfolnir'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'localhost';
   FLUSH PRIVILEGES;
   ```

4. **Firewall Issues:**
   ```bash
   # Check if firewall is blocking MySQL
   sudo ufw status
   sudo ufw allow 3306/tcp  # If needed for remote connections
   ```

### Database Schema Issues

#### Problem: Table doesn't exist or schema mismatch errors

**Symptoms:**
- "Table 'vedfolnir.tablename' doesn't exist" errors
- Schema version mismatch warnings
- Missing columns or indexes

**Diagnostic Steps:**

1. **Check database schema:**
   ```bash
   # List all tables
   mysql -u vedfolnir -p vedfolnir -e "SHOW TABLES;"
   
   # Check specific table structure
   mysql -u vedfolnir -p vedfolnir -e "DESCRIBE users;"
   mysql -u vedfolnir -p vedfolnir -e "DESCRIBE platform_connections;"
   
   # Check indexes
   mysql -u vedfolnir -p vedfolnir -e "SHOW INDEX FROM users;"
   ```

2. **Verify database initialization:**
   ```bash
   # Check if database was properly initialized
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT table_name, table_rows 
   FROM information_schema.tables 
   WHERE table_schema = 'vedfolnir'
   ORDER BY table_name;
   "
   ```

**Solutions:**

1. **Initialize Database:**
   ```bash
   # Run database initialization
   python -c "
   from database import init_db
   init_db()
   print('Database initialized successfully')
   "
   ```

2. **Run Migrations:**
   ```bash
   # Apply database migrations
   python -c "
   from database import run_migrations
   run_migrations()
   print('Migrations completed')
   "
   ```

3. **Manual Schema Creation:**
   ```sql
   -- Connect to MySQL and create missing tables
   mysql -u vedfolnir -p vedfolnir
   
   -- Example: Create users table if missing
   CREATE TABLE IF NOT EXISTS users (
       id INT AUTO_INCREMENT PRIMARY KEY,
       username VARCHAR(255) NOT NULL UNIQUE,
       email VARCHAR(255) NOT NULL UNIQUE,
       password_hash VARCHAR(255) NOT NULL,
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
   ```

### MySQL Performance Issues

#### Problem: Slow database queries or high CPU usage

**Symptoms:**
- Application responds slowly
- High MySQL CPU usage
- Query timeouts
- Connection pool exhaustion

**Diagnostic Steps:**

1. **Check MySQL performance:**
   ```bash
   # Check current connections
   mysql -u vedfolnir -p -e "SHOW PROCESSLIST;"
   
   # Check slow queries
   mysql -u vedfolnir -p -e "SHOW VARIABLES LIKE 'slow_query_log';"
   mysql -u vedfolnir -p -e "SHOW VARIABLES LIKE 'long_query_time';"
   
   # Check InnoDB status
   mysql -u vedfolnir -p -e "SHOW ENGINE INNODB STATUS\G" | head -50
   ```

2. **Monitor query performance:**
   ```bash
   # Enable slow query log (if not enabled)
   mysql -u root -p -e "
   SET GLOBAL slow_query_log = 'ON';
   SET GLOBAL long_query_time = 2;
   "
   
   # Check slow query log
   sudo tail -f /var/log/mysql/slow.log
   ```

3. **Check system resources:**
   ```bash
   # Monitor MySQL process
   top -p $(pgrep mysqld)
   
   # Check disk I/O
   iostat -x 1 5
   
   # Check memory usage
   free -h
   ```

**Solutions:**

1. **Optimize MySQL Configuration:**
   ```bash
   # Edit MySQL configuration
   sudo nano /etc/mysql/conf.d/vedfolnir.cnf
   ```
   ```ini
   [mysqld]
   # InnoDB settings
   innodb_buffer_pool_size = 1G
   innodb_log_file_size = 256M
   innodb_flush_log_at_trx_commit = 2
   
   # Connection settings
   max_connections = 200
   wait_timeout = 28800
   
   # Query cache (MySQL 5.7 and earlier)
   query_cache_size = 64M
   query_cache_type = 1
   ```

2. **Add Database Indexes:**
   ```sql
   -- Add indexes for common queries
   mysql -u vedfolnir -p vedfolnir
   
   -- Index on frequently queried columns
   CREATE INDEX idx_posts_user_id ON posts(user_id);
   CREATE INDEX idx_posts_created_at ON posts(created_at);
   CREATE INDEX idx_captions_post_id ON captions(post_id);
   CREATE INDEX idx_platform_connections_user_id ON platform_connections(user_id);
   ```

3. **Optimize Queries:**
   ```bash
   # Analyze table statistics
   mysql -u vedfolnir -p vedfolnir -e "ANALYZE TABLE users, posts, captions, platform_connections;"
   
   # Optimize tables
   mysql -u vedfolnir -p vedfolnir -e "OPTIMIZE TABLE users, posts, captions, platform_connections;"
   ```

### Connection Pool Issues

#### Problem: "Too many connections" or connection pool exhaustion

**Symptoms:**
- "Too many connections" MySQL errors
- Application hangs waiting for database connections
- Connection timeout errors

**Diagnostic Steps:**

1. **Check connection usage:**
   ```bash
   # Check current connections
   mysql -u vedfolnir -p -e "SHOW STATUS LIKE 'Threads_connected';"
   mysql -u vedfolnir -p -e "SHOW VARIABLES LIKE 'max_connections';"
   
   # Check connection history
   mysql -u vedfolnir -p -e "SHOW STATUS LIKE 'Connections';"
   mysql -u vedfolnir -p -e "SHOW STATUS LIKE 'Max_used_connections';"
   ```

2. **Monitor connection pool:**
   ```bash
   # Check application connection pool status
   python -c "
   from database import get_db_engine
   engine = get_db_engine()
   pool = engine.pool
   print(f'Pool size: {pool.size()}')
   print(f'Checked out: {pool.checkedout()}')
   print(f'Overflow: {pool.overflow()}')
   "
   ```

**Solutions:**

1. **Increase MySQL Connection Limit:**
   ```sql
   -- Temporarily increase connection limit
   mysql -u root -p -e "SET GLOBAL max_connections = 500;"
   
   -- Permanently increase (add to my.cnf)
   -- max_connections = 500
   ```

2. **Optimize Connection Pool:**
   ```python
   # In config.py - adjust connection pool settings
   SQLALCHEMY_ENGINE_OPTIONS = {
       'pool_size': 20,
       'max_overflow': 30,
       'pool_timeout': 30,
       'pool_recycle': 3600,
       'pool_pre_ping': True
   }
   ```

3. **Fix Connection Leaks:**
   ```bash
   # Check for unclosed connections in code
   grep -r "get_db_connection" . --include="*.py"
   
   # Ensure proper connection handling
   # Always use try/finally or context managers
   ```

## Web Interface Issues

### Login Problems

#### Problem: Cannot log in to web interface

**Symptoms:**
- Login form rejects valid credentials
- "Invalid username or password" errors
- Redirected back to login page

**Diagnostic Steps:**

1. **Check user accounts in MySQL:**
   ```bash
   # Check if users exist
   mysql -u vedfolnir -p vedfolnir -e "SELECT id, username, email, is_active FROM users;"
   
   # Check specific user
   mysql -u vedfolnir -p vedfolnir -e "SELECT * FROM users WHERE username='admin';"
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

3. **Check session management:**
   ```bash
   # Check Redis session storage
   redis-cli keys "vedfolnir:session:*"
   
   # Check MySQL session table (if using database sessions)
   mysql -u vedfolnir -p vedfolnir -e "SELECT COUNT(*) FROM sessions;"
   ```

**Solutions:**

1. **Reset Admin Password:**
   ```bash
   # Use the admin user creation script
   python scripts/setup/init_admin_user.py
   
   # Or manually reset password
   python -c "
   from werkzeug.security import generate_password_hash
   from database import get_db_connection
   import pymysql
   
   new_password = 'new_secure_password'
   password_hash = generate_password_hash(new_password)
   
   conn = get_db_connection()
   cursor = conn.cursor()
   cursor.execute('UPDATE users SET password_hash = %s WHERE username = %s', 
                  (password_hash, 'admin'))
   conn.commit()
   conn.close()
   print('Password updated successfully')
   "
   ```

2. **Check Flask Configuration:**
   ```bash
   # Verify Flask secret key is set
   grep FLASK_SECRET_KEY .env || echo "FLASK_SECRET_KEY missing"
   
   # Check Redis configuration
   grep REDIS_URL .env || echo "REDIS_URL missing"
   ```

3. **Clear Session Data:**
   ```bash
   # Clear Redis sessions
   redis-cli FLUSHDB
   
   # Or clear MySQL sessions (if using database sessions)
   mysql -u vedfolnir -p vedfolnir -e "DELETE FROM sessions;"
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
   
   # Check if platforms exist in database
   mysql -u vedfolnir -p vedfolnir -e "SELECT id, name, platform_type, instance_url FROM platform_connections;"
   ```

3. **Check database connectivity from web app:**
   ```bash
   # Test database connection from web context
   python -c "
   from web_app import app
   from database import get_db_connection
   
   with app.app_context():
       try:
           conn = get_db_connection()
           cursor = conn.cursor()
           cursor.execute('SELECT COUNT(*) FROM platform_connections')
           count = cursor.fetchone()[0]
           conn.close()
           print(f'Found {count} platform connections')
       except Exception as e:
           print(f'Database error: {e}')
   "
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
   - Restart web application:
     ```bash
     pkill -f "python web_app.py"
     python web_app.py
     ```

3. **Database Connection Issues:**
   - Verify MySQL is running and accessible
   - Check connection pool status
   - Restart web application

### Session Management Issues

#### Problem: Users get logged out frequently or sessions don't persist

**Symptoms:**
- Frequent automatic logouts
- Session data not persisting between requests
- "Session expired" messages

**Diagnostic Steps:**

1. **Check Redis session storage:**
   ```bash
   # Check Redis connectivity
   redis-cli ping
   
   # Check session keys
   redis-cli keys "vedfolnir:session:*"
   
   # Check session data
   redis-cli get "vedfolnir:session:session_id_here"
   ```

2. **Check session configuration:**
   ```bash
   # Verify session settings
   grep -E "(SESSION|REDIS)" .env
   
   # Check session timeout settings
   python -c "
   from config import Config
   config = Config()
   print(f'Session timeout: {config.session_timeout}')
   print(f'Redis URL: {config.redis_url}')
   "
   ```

**Solutions:**

1. **Redis Issues:**
   ```bash
   # Restart Redis
   sudo systemctl restart redis-server
   
   # Or for Docker
   docker-compose restart redis
   
   # Check Redis memory usage
   redis-cli info memory
   ```

2. **Session Configuration:**
   ```bash
   # Update session timeout in .env
   echo "REDIS_SESSION_TIMEOUT=7200" >> .env
   
   # Restart web application
   pkill -f "python web_app.py"
   python web_app.py
   ```

3. **Cookie Issues:**
   - Check browser cookie settings
   - Verify domain configuration
   - Clear browser cookies for the site

## Processing Issues

### No Images Found for Processing

#### Problem: Processing reports no images found

**Symptoms:**
- "No images found for processing" messages
- Processing completes immediately with no results
- User has posts with images but none are processed

**Diagnostic Steps:**

1. **Check user posts in MySQL:**
   ```bash
   # Verify user exists and has posts
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       u.username,
       COUNT(p.id) as post_count,
       COUNT(CASE WHEN p.has_media = 1 THEN 1 END) as posts_with_media
   FROM users u
   LEFT JOIN posts p ON u.id = p.user_id
   WHERE u.username = 'target_username'
   GROUP BY u.id, u.username;
   "
   ```

2. **Check existing alt text:**
   ```bash
   # Check if images already have alt text
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       COUNT(*) as total_images,
       COUNT(CASE WHEN original_alt_text IS NOT NULL AND original_alt_text != '' THEN 1 END) as images_with_alt_text,
       COUNT(CASE WHEN original_alt_text IS NULL OR original_alt_text = '' THEN 1 END) as images_without_alt_text
   FROM images;
   "
   ```

3. **Check platform connection:**
   ```bash
   # Verify platform connection is active
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       pc.name,
       pc.platform_type,
       pc.is_active,
       pc.last_sync_at
   FROM platform_connections pc
   JOIN users u ON pc.user_id = u.id
   WHERE u.username = 'target_username';
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

2. **Check image processing in MySQL:**
   ```bash
   # Verify images are being downloaded and stored
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       COUNT(*) as total_images,
       COUNT(CASE WHEN local_path IS NOT NULL THEN 1 END) as downloaded_images,
       COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as processed_images,
       COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_images
   FROM images
   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY);
   "
   
   # Check recent processing errors
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       i.id,
       i.original_url,
       i.processing_status,
       i.error_message,
       i.updated_at
   FROM images i
   WHERE i.processing_status = 'failed'
   ORDER BY i.updated_at DESC
   LIMIT 10;
   "
   ```

3. **Check storage directory:**
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
   
   # Check MySQL performance
   mysql -u vedfolnir -p -e "SHOW PROCESSLIST;"
   
   # Check disk I/O
   iotop -p $(pgrep -f "python main.py")
   ```

2. **Profile MySQL queries:**
   ```bash
   # Enable slow query log
   mysql -u root -p -e "
   SET GLOBAL slow_query_log = 1;
   SET GLOBAL long_query_time = 2;
   "
   
   # Check slow queries
   mysqldumpslow -s t -t 10 /var/log/mysql/slow.log
   ```

3. **Check database performance:**
   ```bash
   # Check table sizes and optimization
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       table_name,
       table_rows,
       ROUND(data_length/1024/1024, 2) as data_mb,
       ROUND(index_length/1024/1024, 2) as index_mb
   FROM information_schema.tables 
   WHERE table_schema = 'vedfolnir'
   ORDER BY (data_length + index_length) DESC;
   "
   ```

**Solutions:**

1. **Reduce Batch Size:**
   ```bash
   # Process fewer posts per run
   MAX_POSTS_PER_RUN=10 python main.py --users username
   ```

2. **Optimize MySQL:**
   ```bash
   # Analyze and optimize tables
   mysql -u vedfolnir -p vedfolnir -e "
   ANALYZE TABLE users, platform_connections, posts, captions, images;
   OPTIMIZE TABLE users, platform_connections, posts, captions, images;
   "
   
   # Add missing indexes
   mysql -u vedfolnir -p vedfolnir -e "
   CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
   CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
   CREATE INDEX IF NOT EXISTS idx_images_post_id ON images(post_id);
   CREATE INDEX IF NOT EXISTS idx_captions_post_id ON captions(post_id);
   "
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
- MySQL connection pool exhaustion

**Diagnostic Steps:**

1. **Monitor memory usage:**
   ```bash
   # Check Python process memory
   ps aux | grep python | grep -E "(main.py|web_app.py)"
   
   # Check MySQL memory usage
   mysql -u vedfolnir -p -e "
   SELECT 
       SUBSTRING_INDEX(event_name,'/',2) AS code_area, 
       FORMAT_BYTES(SUM(current_alloc)) AS current_alloc 
   FROM performance_schema.memory_summary_global_by_event_name 
   WHERE current_alloc > 0 
   GROUP BY SUBSTRING_INDEX(event_name,'/',2) 
   ORDER BY SUM(current_alloc) DESC
   LIMIT 10;
   "
   ```

2. **Check connection pool:**
   ```bash
   # Monitor MySQL connections
   mysql -u vedfolnir -p -e "
   SELECT 
       'Current Connections' as metric,
       (SELECT VARIABLE_VALUE FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Threads_connected') as value
   UNION ALL
   SELECT 
       'Max Connections',
       (SELECT VARIABLE_VALUE FROM performance_schema.global_variables WHERE VARIABLE_NAME = 'max_connections');
   "
   ```

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
   
   # Clean up old database records
   mysql -u vedfolnir -p vedfolnir -e "
   DELETE FROM images 
   WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
   AND processing_status = 'completed';
   "
   ```

3. **Optimize Connection Pool:**
   ```python
   # In config.py - reduce connection pool size
   SQLALCHEMY_ENGINE_OPTIONS = {
       'pool_size': 10,
       'max_overflow': 20,
       'pool_timeout': 30,
       'pool_recycle': 3600
   }
   ```

4. **Use Smaller Model:**
   ```bash
   # Use smaller Ollama model
   OLLAMA_MODEL=llava:7b python main.py --users username
   ```

## Security Issues

### Credential Security

#### Problem: Concerns about credential storage security

**Diagnostic Steps:**

1. **Verify encryption in MySQL:**
   ```bash
   # Check that credentials are encrypted in database
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       id,
       name,
       platform_type,
       LEFT(access_token, 20) as token_sample
   FROM platform_connections 
   LIMIT 3;
   "
   # Should show encrypted data, not plaintext
   ```

2. **Check encryption key:**
   ```bash
   # Verify encryption key is set
   grep PLATFORM_ENCRYPTION_KEY .env
   ```

3. **Check MySQL SSL:**
   ```bash
   # Verify SSL is enabled
   mysql -u vedfolnir -p -e "SHOW VARIABLES LIKE 'have_ssl';"
   mysql -u vedfolnir -p -e "SHOW STATUS LIKE 'Ssl_cipher';"
   ```

**Solutions:**

1. **Regenerate Encryption Key:**
   ```bash
   # Generate new encryption key
   python -c "from cryptography.fernet import Fernet; print(f'PLATFORM_ENCRYPTION_KEY={Fernet.generate_key().decode()}')"
   ```

2. **Enable MySQL SSL:**
   ```bash
   # Generate SSL certificates
   sudo mysql_ssl_rsa_setup --uid=mysql
   
   # Update MySQL configuration
   echo "
   [mysqld]
   ssl-ca=/var/lib/mysql/ca.pem
   ssl-cert=/var/lib/mysql/server-cert.pem
   ssl-key=/var/lib/mysql/server-key.pem
   require_secure_transport=ON
   " | sudo tee -a /etc/mysql/conf.d/ssl.cnf
   
   # Restart MySQL
   sudo systemctl restart mysql
   ```

3. **Rotate Platform Credentials:**
   - Regenerate access tokens on platforms
   - Update platform connections in web interface
   - Test connections after update

### Access Control Issues

#### Problem: Users can access other users' data

**Diagnostic Steps:**

1. **Check user isolation in MySQL:**
   ```bash
   # Verify platform connections are user-specific
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       u.username, 
       COUNT(pc.id) as platform_count,
       GROUP_CONCAT(pc.name) as platforms
   FROM users u 
   LEFT JOIN platform_connections pc ON u.id = pc.user_id 
   GROUP BY u.id, u.username
   ORDER BY u.username;
   "
   ```

2. **Check session isolation:**
   ```bash
   # Check Redis session data
   redis-cli keys "vedfolnir:session:*" | head -5
   
   # Check MySQL session data
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       session_id,
       user_id,
       active_platform_id,
       created_at
   FROM user_sessions
   ORDER BY created_at DESC
   LIMIT 10;
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
   echo "CSRF_ENABLED=true" >> .env
   ```

3. **Audit Database Access:**
   ```bash
   # Enable MySQL general log (temporarily for auditing)
   mysql -u root -p -e "
   SET GLOBAL general_log = 'ON';
   SET GLOBAL general_log_file = '/var/log/mysql/general.log';
   "
   
   # Review access patterns
   sudo tail -f /var/log/mysql/general.log
   ```

## Getting Help

### Collecting Diagnostic Information

When seeking help, collect this information:

1. **System Information:**
   ```bash
   # System details
   uname -a
   python --version
   mysql --version
   redis-server --version
   
   # Python packages
   pip list | grep -E "(flask|sqlalchemy|pymysql|redis)"
   ```

2. **MySQL Configuration:**
   ```bash
   # MySQL status and configuration (sanitized)
   mysql -u vedfolnir -p -e "
   SELECT 
       VARIABLE_NAME,
       VARIABLE_VALUE
   FROM performance_schema.global_variables 
   WHERE VARIABLE_NAME IN (
       'version',
       'character_set_server',
       'collation_server',
       'max_connections',
       'innodb_buffer_pool_size'
   );
   "
   ```

3. **Recent Logs:**
   ```bash
   # Collect recent logs
   tail -n 100 logs/vedfolnir.log > debug_logs.txt
   tail -n 100 logs/webapp.log >> debug_logs.txt
   sudo tail -n 50 /var/log/mysql/error.log >> debug_logs.txt
   ```

4. **Database State:**
   ```bash
   # Database statistics
   mysql -u vedfolnir -p vedfolnir -e "
   SELECT 
       'users' as table_name, COUNT(*) as count FROM users
   UNION ALL
   SELECT 'platform_connections', COUNT(*) FROM platform_connections
   UNION ALL
   SELECT 'posts', COUNT(*) FROM posts
   UNION ALL
   SELECT 'images', COUNT(*) FROM images
   UNION ALL
   SELECT 'captions', COUNT(*) FROM captions;
   " > database_stats.txt
   ```

### Emergency Procedures

#### Complete System Reset

If all else fails, you can reset the system:

```bash
# 1. Backup everything
mkdir -p emergency_backup_$(date +%Y%m%d_%H%M%S)
mysqldump -u vedfolnir -p vedfolnir > emergency_backup_$(date +%Y%m%d_%H%M%S)/database_backup.sql
cp -r storage emergency_backup_$(date +%Y%m%d_%H%M%S)/
cp .env emergency_backup_$(date +%Y%m%d_%H%M%S)/

# 2. Stop all processes
pkill -f "python web_app.py"
pkill -f "python main.py"

# 3. Reset MySQL database
mysql -u root -p -e "
DROP DATABASE IF EXISTS vedfolnir;
CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"

# 4. Reinitialize database
python -c "
from database import init_db
init_db()
print('Database reinitialized')
"

# 5. Recreate admin user
python scripts/setup/init_admin_user.py

# 6. Clear Redis cache
redis-cli FLUSHDB

# 7. Start web application
python web_app.py
```

#### Data Recovery

If you need to recover data from backups:

```bash
# Find available MySQL backups
ls -la /backup/vedfolnir/mysql/

# Restore specific backup
mysql -u vedfolnir -p vedfolnir < /backup/vedfolnir/mysql/vedfolnir_full_YYYYMMDD_HHMMSS.sql

# Verify restored data
mysql -u vedfolnir -p vedfolnir -e "
SELECT 
    table_name,
    table_rows
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir'
ORDER BY table_name;
"
```

## Additional Resources

For comprehensive MySQL troubleshooting, see these specialized guides:

- **[MySQL Performance Tuning Guide](troubleshooting/mysql-performance-tuning.md)** - Detailed performance optimization
- **[MySQL Error Messages Guide](troubleshooting/mysql-error-messages.md)** - Complete error message reference
- **[MySQL Deployment Guide](deployment/mysql-deployment-guide.md)** - Production deployment procedures
- **[MySQL Backup Guide](deployment/mysql-backup-maintenance.md)** - Backup and recovery procedures

This comprehensive troubleshooting guide should help resolve most MySQL-related issues with Vedfolnir. For complex issues, don't hesitate to seek support with detailed diagnostic information.