#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Generate secure environment variables for Vedfolnir

This script generates the required secure environment variables and creates
a properly configured .env file.
"""

import secrets
import string
import sys
import os
import re
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole

def generate_flask_secret_key():
    """Generate a secure Flask secret key"""
    return secrets.token_urlsafe(32)

def generate_platform_encryption_key():
    """Generate a Fernet encryption key for platform credentials"""
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        print("Error: cryptography package is required. Install with: pip install cryptography")
        sys.exit(1)

def generate_secure_password(length=24):
    """Generate a secure password"""
    # Use a mix of characters but avoid ambiguous ones
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(chars) for _ in range(length))

def create_admin_user(username, email, password):
    """Create or update admin user in database"""
    try:
        # Load environment first to get config
        from dotenv import load_dotenv
        load_dotenv()
        
        from config import Config
        config = Config()
        
        # Initialize database
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            # Check if admin user already exists
            existing_user = session.query(User).filter_by(username=username).first()
            
            if existing_user:
                print(f"   Updating existing admin user: {username}")
                existing_user.email = email
                existing_user.set_password(password)
                existing_user.role = UserRole.ADMIN
                existing_user.is_active = True
                existing_user.email_verified = True
            else:
                print(f"   Creating new admin user: {username}")
                admin_user = User(
                    username=username,
                    email=email,
                    role=UserRole.ADMIN,
                    is_active=True,
                    email_verified=True
                )
                admin_user.set_password(password)
                session.add(admin_user)
            
            session.commit()
            return True
            
    except Exception as e:
        print(f"   ❌ Error creating admin user: {e}")
        return False

def generate_redis_password():
    """Generate a secure Redis password"""
    return secrets.token_urlsafe(16)

def test_mysql_connection(host, port, user, password, database, socket_path=None):
    """Test MySQL connection with provided credentials"""
    try:
        import pymysql
        
        connect_args = {
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4'
        }
        
        if socket_path:
            connect_args['unix_socket'] = socket_path
        else:
            connect_args['host'] = host
            connect_args['port'] = int(port)
        
        connection = pymysql.connect(**connect_args)
        connection.close()
        return True, "Connection successful"
    except ImportError:
        return False, "PyMySQL not installed. Run: pip install pymysql"
    except Exception as e:
        return False, str(e)

def url_encode_password(password):
    """URL encode password for database URL"""
    import urllib.parse
    return urllib.parse.quote(password, safe='')

def main():
    print("🔐 Vedfolnir Environment Secrets Generator")
    print("=" * 50)
    print()
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        print("⚠️  Warning: .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted. Existing .env file preserved.")
            print("You can manually edit your .env file or delete it and run this script again.")
            sys.exit(0)
    
    # Check if .env.example exists
    env_example_path = Path(".env.example")
    if not env_example_path.exists():
        print("⚠️  Warning: .env.example file not found!")
        print("This script will create a basic .env file, but you may want to copy from .env.example first.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Aborted. Please ensure .env.example exists or run from the project root directory.")
            sys.exit(0)
    
    print("Generating secure environment variables...")
    print()
    
    # Generate all required values
    flask_secret = generate_flask_secret_key()
    encryption_key = generate_platform_encryption_key()
    admin_password = generate_secure_password()
    redis_password = generate_redis_password()
    
    # Database Configuration
    print("Database Configuration:")
    print("Choose database type:")
    print("1. MySQL (default, good for development)")
    print("2. MySQL/MariaDB (recommended for production)")
    
    while True:
        db_choice = input("Enter choice (1-2) [1]: ").strip() or '1'
        if db_choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    database_settings = {}
    if db_choice == '2':
        print("\nMySQL/MariaDB Configuration:")
        
        # Connection method
        print("Choose connection method:")
        print("1. Unix socket (recommended for local installations)")
        print("2. TCP/IP (host and port)")
        
        while True:
            conn_choice = input("Enter choice (1-2) [1]: ").strip() or '1'
            if conn_choice in ['1', '2']:
                break
            print("Invalid choice. Please enter 1 or 2.")
        
        database_settings['DB_TYPE'] = 'mysql'
        database_settings['DB_NAME'] = input("Database name (default: vedfolnir): ").strip() or "vedfolnir"
        database_settings['DB_USER'] = input("Database username: ").strip()
        
        if not database_settings['DB_USER']:
            print("Error: Database username is required")
            sys.exit(1)
        
        database_settings['DB_PASSWORD'] = input("Database password: ").strip()
        
        if not database_settings['DB_PASSWORD']:
            print("Error: Database password is required")
            sys.exit(1)
        
        if conn_choice == '1':
            # Unix socket
            default_socket = "/tmp/mysql.sock"
            database_settings['DB_UNIX_SOCKET'] = input(f"Unix socket path (default: {default_socket}): ").strip() or default_socket
            
            # Build connection URL for unix socket
            encoded_password = url_encode_password(database_settings['DB_PASSWORD'])
            database_settings['DATABASE_URL'] = f"mysql+pymysql://{database_settings['DB_USER']}:{encoded_password}@localhost/{database_settings['DB_NAME']}?unix_socket={database_settings['DB_UNIX_SOCKET']}&charset=utf8mb4"
            
            # Test connection
            print("Testing MySQL connection...")
            success, message = test_mysql_connection(
                None, None, 
                database_settings['DB_USER'], 
                database_settings['DB_PASSWORD'], 
                database_settings['DB_NAME'],
                database_settings['DB_UNIX_SOCKET']
            )
            
        else:
            # TCP/IP
            database_settings['DB_HOST'] = input("Database host (default: localhost): ").strip() or "localhost"
            database_settings['DB_PORT'] = input("Database port (default: 3306): ").strip() or "3306"
            
            # Build connection URL for TCP/IP
            encoded_password = url_encode_password(database_settings['DB_PASSWORD'])
            database_settings['DATABASE_URL'] = f"mysql+pymysql://{database_settings['DB_USER']}:{encoded_password}@{database_settings['DB_HOST']}:{database_settings['DB_PORT']}/{database_settings['DB_NAME']}?charset=utf8mb4"
            
            # Test connection
            print("Testing MySQL connection...")
            success, message = test_mysql_connection(
                database_settings['DB_HOST'], 
                database_settings['DB_PORT'],
                database_settings['DB_USER'], 
                database_settings['DB_PASSWORD'], 
                database_settings['DB_NAME']
            )
        
        if success:
            print("✅ MySQL connection successful!")
        else:
            print(f"❌ MySQL connection failed: {message}")
            print("You can continue setup and fix the connection later.")
            continue_anyway = input("Continue with setup anyway? (y/N): ").strip().lower()
            if continue_anyway != 'y':
                print("Setup aborted. Please fix MySQL connection and try again.")
                sys.exit(1)
        
        # MySQL performance settings
        print("\nMySQL Performance Settings:")
        database_settings['DB_POOL_SIZE'] = input("Connection pool size (default: 20): ").strip() or "20"
        database_settings['DB_MAX_OVERFLOW'] = input("Max overflow connections (default: 50): ").strip() or "50"
        database_settings['DB_POOL_TIMEOUT'] = input("Pool timeout seconds (default: 30): ").strip() or "30"
        database_settings['DB_POOL_RECYCLE'] = input("Pool recycle seconds (default: 3600): ").strip() or "3600"
        
        # MySQL advanced configuration from Tasks 13-20
        print("\nMySQL Advanced Configuration (Tasks 13-20):")
        
        # Security hardening settings
        print("Security Hardening Settings:")
        database_settings['MYSQL_PASSWORD_MIN_LENGTH'] = input("Minimum password length (default: 12): ").strip() or "12"
        database_settings['MYSQL_MAX_FAILED_LOGINS'] = input("Max failed logins (default: 5): ").strip() or "5"
        database_settings['MYSQL_SESSION_TIMEOUT'] = input("Session timeout seconds (default: 3600): ").strip() or "3600"
        database_settings['MYSQL_CERT_EXPIRY_WARNING_DAYS'] = input("Certificate expiry warning days (default: 30): ").strip() or "30"
        database_settings['MYSQL_SECURITY_KEY_FILE'] = input("Security key file (default: .mysql_security_key): ").strip() or ".mysql_security_key"
        
        # Backup and recovery settings
        print("\nBackup and Recovery Settings:")
        database_settings['MYSQL_BACKUP_DIR'] = input("Backup directory (default: ./backups): ").strip() or "./backups"
        database_settings['MYSQL_BACKUP_RETENTION_DAYS'] = input("Backup retention days (default: 30): ").strip() or "30"
        database_settings['MYSQL_BACKUP_COMPRESSION_LEVEL'] = input("Backup compression level 1-9 (default: 6): ").strip() or "6"
        database_settings['MYSQL_MAX_BACKUP_SIZE_GB'] = input("Max backup size GB (default: 10): ").strip() or "10"
        database_settings['MYSQL_BACKUP_TIMEOUT_MINUTES'] = input("Backup timeout minutes (default: 60): ").strip() or "60"
        database_settings['MYSQL_PARALLEL_BACKUP_JOBS'] = input("Parallel backup jobs (default: 2): ").strip() or "2"
        database_settings['MYSQL_BACKUP_ENCRYPTION_KEY_FILE'] = input("Backup encryption key file (default: .mysql_backup_key): ").strip() or ".mysql_backup_key"
        
        # Cloud storage for backups
        configure_s3_backup = input("Configure AWS S3 for backups? (y/N): ").strip().lower() == 'y'
        if configure_s3_backup:
            database_settings['MYSQL_BACKUP_S3_BUCKET'] = input("S3 bucket name for backups: ").strip()
            database_settings['AWS_ACCESS_KEY_ID'] = input("AWS Access Key ID: ").strip()
            database_settings['AWS_SECRET_ACCESS_KEY'] = input("AWS Secret Access Key: ").strip()
            database_settings['AWS_DEFAULT_REGION'] = input("AWS region (default: us-east-1): ").strip() or "us-east-1"
        
        # Performance monitoring settings
        print("\nPerformance Monitoring Settings:")
        database_settings['MYSQL_MONITORING_INTERVAL'] = input("Monitoring interval seconds (default: 300): ").strip() or "300"
        database_settings['MYSQL_AUTO_OPTIMIZE_INTERVAL'] = input("Auto-optimize interval seconds (default: 3600): ").strip() or "3600"
        database_settings['MYSQL_AUTO_OPTIMIZE_ENABLED'] = input("Enable auto-optimization? (y/N): ").strip().lower() == 'y'
        database_settings['MYSQL_SLOW_QUERY_THRESHOLD_MS'] = input("Slow query threshold ms (default: 1000): ").strip() or "1000"
        database_settings['MYSQL_QUERY_CACHE_SIZE'] = input("Query cache size (default: 100): ").strip() or "100"
        
        # Dashboard settings
        print("\nDashboard Settings:")
        database_settings['MYSQL_DASHBOARD_UPDATE_INTERVAL'] = input("Dashboard update interval seconds (default: 30): ").strip() or "30"
        database_settings['MYSQL_DASHBOARD_RETENTION_HOURS'] = input("Dashboard data retention hours (default: 168): ").strip() or "168"
        database_settings['MYSQL_DASHBOARD_REAL_TIME'] = input("Enable real-time dashboard? (Y/n): ").strip().lower() != 'n'
        database_settings['MYSQL_DASHBOARD_MAX_CHART_POINTS'] = input("Max chart points (default: 100): ").strip() or "100"
        
        # Connection usage thresholds
        print("\nPerformance Thresholds:")
        database_settings['MYSQL_CONNECTION_USAGE_CRITICAL'] = input("Connection usage critical % (default: 90): ").strip() or "90"
        database_settings['MYSQL_CONNECTION_USAGE_WARNING'] = input("Connection usage warning % (default: 75): ").strip() or "75"
        database_settings['MYSQL_SLOW_QUERY_RATIO_CRITICAL'] = input("Slow query ratio critical % (default: 20): ").strip() or "20"
        database_settings['MYSQL_SLOW_QUERY_RATIO_WARNING'] = input("Slow query ratio warning % (default: 10): ").strip() or "10"
        database_settings['MYSQL_AVG_QUERY_TIME_CRITICAL'] = input("Avg query time critical ms (default: 2000): ").strip() or "2000"
        database_settings['MYSQL_AVG_QUERY_TIME_WARNING'] = input("Avg query time warning ms (default: 1000): ").strip() or "1000"
        database_settings['MYSQL_BUFFER_POOL_HIT_RATIO_CRITICAL'] = input("Buffer pool hit ratio critical % (default: 90): ").strip() or "90"
        database_settings['MYSQL_BUFFER_POOL_HIT_RATIO_WARNING'] = input("Buffer pool hit ratio warning % (default: 95): ").strip() or "95"
        
    else:
        # MySQL
        database_settings = {
            'DB_TYPE': 'MySQL',
            'DATABASE_URL': "MySQL database",
            'DB_POOL_SIZE': '50',
            'DB_MAX_OVERFLOW': '100',
            'DB_POOL_TIMEOUT': '30',
            'DB_POOL_RECYCLE': '1800'
        }
    
    # Get Ollama configuration from user
    print("\nOllama Configuration:")
    ollama_url = input("Ollama URL (default: http://localhost:11434): ").strip() or "http://localhost:11434"
    ollama_model = input("Ollama model (default: llava:7b): ").strip() or "llava:7b"
    
    # Get storage configuration from user
    print("\nStorage Configuration:")
    print("Configure storage limits for image caption generation")
    storage_max_gb = input("Maximum storage for images in GB (default: 10): ").strip() or "10"
    storage_warning_threshold = input("Warning threshold percentage (default: 80): ").strip() or "80"
    storage_monitoring_enabled = input("Enable storage monitoring? (Y/n): ").strip().lower() != 'n'
    
    # Validate storage configuration
    try:
        storage_max_gb_float = float(storage_max_gb)
        if storage_max_gb_float <= 0:
            print("Warning: Storage limit must be positive, using default value of 10GB")
            storage_max_gb = "10"
    except ValueError:
        print("Warning: Invalid storage limit, using default value of 10GB")
        storage_max_gb = "10"
    
    try:
        storage_warning_threshold_float = float(storage_warning_threshold)
        if storage_warning_threshold_float <= 0 or storage_warning_threshold_float > 100:
            print("Warning: Warning threshold must be between 0 and 100, using default value of 80%")
            storage_warning_threshold = "80"
    except ValueError:
        print("Warning: Invalid warning threshold, using default value of 80%")
        storage_warning_threshold = "80"
    
    # Get email configuration from user
    print("\nEmail Configuration:")
    print("Configure email settings for user notifications (verification, password reset, etc.)")
    configure_email = input("Configure email settings? (y/N) (default: y): ").strip().lower() == 'y' or "y"
    
    email_settings = {}
    if configure_email:
        email_settings['MAIL_SERVER'] = input("SMTP server (e.g., smtp.gmail.com): ").strip()
        email_settings['MAIL_PORT'] = input("SMTP port (default: 587): ").strip() or "587"
        email_settings['MAIL_USE_TLS'] = input("Use TLS? (Y/n): ").strip().lower() != 'n'
        email_settings['MAIL_USERNAME'] = input("SMTP username/email: ").strip()
        email_settings['MAIL_PASSWORD'] = input("SMTP password/app password: ").strip()
        email_settings['MAIL_DEFAULT_SENDER'] = input(f"Default sender email (default: {email_settings['MAIL_USERNAME']}): ").strip() or email_settings['MAIL_USERNAME']
    else:
        # Set default/disabled email settings
        email_settings = {
            'MAIL_SERVER': 'localhost',
            'MAIL_PORT': '587',
            'MAIL_USE_TLS': True,
            'MAIL_USERNAME': '',
            'MAIL_PASSWORD': '',
            'MAIL_DEFAULT_SENDER': 'noreply@localhost'
        }
    
    # Get security configuration
    print("\nSecurity Configuration:")
    print("Choose security mode:")
    print("1. Development (disable security) - Default")
    print("2. Testing (partial security)")
    print("3. Production (full security)")
    
    while True:
        choice = input("Enter choice (1-3) [1]: ").strip() or '1'
        if choice == '1':
            security_mode = 'development'
            security_settings = {
                'SECURITY_CSRF_ENABLED': 'false',
                'SECURITY_RATE_LIMITING_ENABLED': 'false',
                'SECURITY_INPUT_VALIDATION_ENABLED': 'false'
            }
            break
        elif choice == '2':
            security_mode = 'testing'
            security_settings = {
                'SECURITY_CSRF_ENABLED': 'false',
                'SECURITY_RATE_LIMITING_ENABLED': 'true',
                'SECURITY_INPUT_VALIDATION_ENABLED': 'true'
            }
            break
        elif choice == '3':
            security_mode = 'production'
            security_settings = {
                'SECURITY_CSRF_ENABLED': 'true',
                'SECURITY_RATE_LIMITING_ENABLED': 'true',
                'SECURITY_INPUT_VALIDATION_ENABLED': 'true'
            }
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    print(f"Selected: {security_mode.title()} mode")

    # Get Redis configuration
    print("\nRedis Configuration:")
    print("Configure Redis for session management (recommended for production)")
    configure_redis = input("Configure Redis settings? (Y/n) (default: Y): ").strip().lower() != 'n'
    
    redis_settings = {}
    if configure_redis:
        redis_settings['REDIS_HOST'] = input("Redis host (default: localhost): ").strip() or "localhost"
        redis_settings['REDIS_PORT'] = input("Redis port (default: 6379): ").strip() or "6379"
        redis_settings['REDIS_DB'] = input("Redis database number (default: 0): ").strip() or "0"
        
        # Ask if they want to use a password
        use_redis_password = input("Use Redis password? (Y/n): ").strip().lower() != 'n'
        if use_redis_password:
            custom_password = input(f"Redis password (press Enter to generate: {redis_password[:8]}...): ").strip()
            redis_settings['REDIS_PASSWORD'] = custom_password or redis_password
        else:
            redis_settings['REDIS_PASSWORD'] = ""
        
        redis_settings['REDIS_SSL'] = input("Use SSL? (y/N): ").strip().lower() == 'y'
        redis_settings['SESSION_STORAGE'] = 'redis'
        
        # Build Redis URL
        if redis_settings['REDIS_PASSWORD']:
            redis_settings['REDIS_URL'] = f"redis://:{redis_settings['REDIS_PASSWORD']}@{redis_settings['REDIS_HOST']}:{redis_settings['REDIS_PORT']}/{redis_settings['REDIS_DB']}"
        else:
            redis_settings['REDIS_URL'] = f"redis://{redis_settings['REDIS_HOST']}:{redis_settings['REDIS_PORT']}/{redis_settings['REDIS_DB']}"
    else:
        # Set default Redis settings but use database for sessions
        redis_settings = {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0',
            'REDIS_PASSWORD': redis_password,
            'REDIS_SSL': False,
            'SESSION_STORAGE': 'database',
            'REDIS_URL': f'redis://:{redis_password}@localhost:6379/0'
        }
    
    # Get WebSocket configuration
    print("\nWebSocket Configuration:")
    print("Configure WebSocket settings for real-time communication")
    configure_websocket = input("Configure WebSocket settings? (Y/n): ").strip().lower() != 'n'
    
    websocket_settings = {}
    if configure_websocket:
        print("Choose WebSocket configuration profile:")
        print("1. Development (relaxed security, verbose logging)")
        print("2. Testing (partial security, moderate logging)")
        print("3. Production (full security, minimal logging)")
        
        while True:
            ws_choice = input(f"Enter choice (1-3) [based on security mode: {security_mode}]: ").strip()
            if not ws_choice:
                # Use security mode to determine WebSocket profile
                if security_mode == 'development':
                    ws_choice = '1'
                elif security_mode == 'testing':
                    ws_choice = '2'
                else:
                    ws_choice = '3'
            
            if ws_choice == '1':
                websocket_profile = 'development'
                websocket_settings.update({
                    'SOCKETIO_REQUIRE_AUTH': 'false',  # WORKING: relaxed for development
                    'SOCKETIO_SESSION_VALIDATION': 'false',  # WORKING: relaxed for development
                    'SOCKETIO_RATE_LIMITING': 'false',  # WORKING: relaxed for development
                    'SOCKETIO_CSRF_PROTECTION': 'false',  # WORKING: relaxed for development
                    'SOCKETIO_LOG_LEVEL': 'WARNING',
                    'SOCKETIO_LOG_CONNECTIONS': 'true',
                    'SOCKETIO_DEBUG': 'true',
                    'SOCKETIO_ENGINEIO_LOGGER': 'true'
                })
                break
            elif ws_choice == '2':
                websocket_profile = 'testing'
                websocket_settings.update({
                    'SOCKETIO_REQUIRE_AUTH': 'true',
                    'SOCKETIO_SESSION_VALIDATION': 'true',
                    'SOCKETIO_RATE_LIMITING': 'true',
                    'SOCKETIO_CSRF_PROTECTION': 'false',
                    'SOCKETIO_LOG_LEVEL': 'WARNING',
                    'SOCKETIO_LOG_CONNECTIONS': 'true',
                    'SOCKETIO_DEBUG': 'false',
                    'SOCKETIO_ENGINEIO_LOGGER': 'false'
                })
                break
            elif ws_choice == '3':
                websocket_profile = 'production'
                websocket_settings.update({
                    'SOCKETIO_REQUIRE_AUTH': 'true',
                    'SOCKETIO_SESSION_VALIDATION': 'true',
                    'SOCKETIO_RATE_LIMITING': 'true',
                    'SOCKETIO_CSRF_PROTECTION': 'true',
                    'SOCKETIO_LOG_LEVEL': 'WARNING',
                    'SOCKETIO_LOG_CONNECTIONS': 'false',
                    'SOCKETIO_DEBUG': 'false',
                    'SOCKETIO_ENGINEIO_LOGGER': 'false'
                })
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        
        print(f"Selected WebSocket profile: {websocket_profile}")
        
        # Common WebSocket settings (Final working configuration - UPDATED)
        websocket_settings.update({
            'SOCKETIO_TRANSPORTS': 'polling,websocket',  # FIXED: polling first for better compatibility
            'SOCKETIO_PING_TIMEOUT': '60',  # seconds
            'SOCKETIO_PING_INTERVAL': '25',  # seconds
            'SOCKETIO_ASYNC_MODE': 'threading',
            'SOCKETIO_CORS_ORIGINS': 'http://127.0.0.1:5000,http://localhost:5000,http://localhost:3000,http://127.0.0.1:3000',
            'SOCKETIO_CORS_CREDENTIALS': 'true',
            'SOCKETIO_CORS_METHODS': 'GET,POST',
            'SOCKETIO_CORS_HEADERS': 'Content-Type,Authorization',
            'SOCKETIO_RECONNECTION': 'true',
            'SOCKETIO_RECONNECTION_ATTEMPTS': '10',  # UPDATED: increased for better reliability
            'SOCKETIO_RECONNECTION_DELAY': '500',  # UPDATED: faster reconnection
            'SOCKETIO_RECONNECTION_DELAY_MAX': '3000',  # UPDATED: faster max delay
            'SOCKETIO_TIMEOUT': '20000',
            'SOCKETIO_FORCE_NEW': 'false',
            'SOCKETIO_UPGRADE': 'true',
            'SOCKETIO_REMEMBER_UPGRADE': 'true',
            'SOCKETIO_WITH_CREDENTIALS': 'true',
            'SOCKETIO_MAX_CONNECTIONS': '1000',
            'SOCKETIO_CONNECTION_POOL_SIZE': '10',
            'SOCKETIO_MAX_HTTP_BUFFER_SIZE': '1000000'
        })
        
        # Advanced WebSocket settings (optional)
        configure_advanced = input("Configure advanced WebSocket settings? (y/N): ").strip().lower() == 'y'
        if configure_advanced:
            print("\nAdvanced WebSocket Configuration:")
            
            # Transport settings
            custom_transports = input("Transport methods (default: websocket,polling): ").strip()
            if custom_transports:
                websocket_settings['SOCKETIO_TRANSPORTS'] = custom_transports
            
            # Timeout settings
            custom_ping_timeout = input("Ping timeout in ms (default: 60000): ").strip()
            if custom_ping_timeout:
                websocket_settings['SOCKETIO_PING_TIMEOUT'] = custom_ping_timeout
            
            custom_ping_interval = input("Ping interval in ms (default: 25000): ").strip()
            if custom_ping_interval:
                websocket_settings['SOCKETIO_PING_INTERVAL'] = custom_ping_interval
            
            # Connection limits
            custom_max_connections = input("Max connections (default: 1000): ").strip()
            if custom_max_connections:
                websocket_settings['SOCKETIO_MAX_CONNECTIONS'] = custom_max_connections
            
            custom_pool_size = input("Connection pool size (default: 10): ").strip()
            if custom_pool_size:
                websocket_settings['SOCKETIO_CONNECTION_POOL_SIZE'] = custom_pool_size
        
        print(f"✅ WebSocket configuration applied: {websocket_profile} profile")
        
    else:
        # Use default WebSocket settings based on security mode (Final working configuration)
        if security_mode == 'development':
            websocket_settings = {
                'SOCKETIO_TRANSPORTS': 'polling,websocket',  # FIXED: polling first for better compatibility
                'SOCKETIO_PING_TIMEOUT': '60',
                'SOCKETIO_PING_INTERVAL': '25',
                'SOCKETIO_ASYNC_MODE': 'threading',
                'SOCKETIO_CORS_ORIGINS': 'http://127.0.0.1:5000,http://localhost:5000,http://localhost:3000,http://127.0.0.1:3000',
                'SOCKETIO_CORS_CREDENTIALS': 'true',
                'SOCKETIO_CORS_METHODS': 'GET,POST',
                'SOCKETIO_CORS_HEADERS': 'Content-Type,Authorization',
                'SOCKETIO_FORCE_NEW': 'false',
                'SOCKETIO_UPGRADE': 'true',
                'SOCKETIO_REMEMBER_UPGRADE': 'true',
                'SOCKETIO_WITH_CREDENTIALS': 'true',
                'SOCKETIO_RECONNECTION': 'true',
                'SOCKETIO_RECONNECTION_ATTEMPTS': '10',
                'SOCKETIO_RECONNECTION_DELAY': '500',
                'SOCKETIO_RECONNECTION_DELAY_MAX': '3000',
                'SOCKETIO_TIMEOUT': '20000',
                'SOCKETIO_MAX_CONNECTIONS': '100',
                'SOCKETIO_CONNECTION_POOL_SIZE': '5',
                'SOCKETIO_MAX_HTTP_BUFFER_SIZE': '500000',
                'SOCKETIO_REQUIRE_AUTH': 'false',  # FIXED: relaxed for development
                'SOCKETIO_SESSION_VALIDATION': 'false',  # FIXED: relaxed for development
                'SOCKETIO_RATE_LIMITING': 'false',  # FIXED: relaxed for development
                'SOCKETIO_CSRF_PROTECTION': 'false',  # FIXED: relaxed for development
                'SOCKETIO_LOG_LEVEL': 'WARNING',
                'SOCKETIO_LOG_CONNECTIONS': 'true',
                'SOCKETIO_DEBUG': 'true',
                'SOCKETIO_ENGINEIO_LOGGER': 'true'
            }
        else:
            websocket_settings = {
                'SOCKETIO_TRANSPORTS': 'websocket,polling',
                'SOCKETIO_PING_TIMEOUT': '60',
                'SOCKETIO_PING_INTERVAL': '25',
                'SOCKETIO_ASYNC_MODE': 'threading',
                'SOCKETIO_CORS_ORIGINS': 'http://127.0.0.1:5000,http://localhost:5000',
                'SOCKETIO_CORS_CREDENTIALS': 'true',
                'SOCKETIO_CORS_METHODS': 'GET,POST',
                'SOCKETIO_CORS_HEADERS': 'Content-Type,Authorization',
                'SOCKETIO_FORCE_NEW': 'false',
                'SOCKETIO_UPGRADE': 'true',
                'SOCKETIO_REMEMBER_UPGRADE': 'true',
                'SOCKETIO_WITH_CREDENTIALS': 'true',
                'SOCKETIO_RECONNECTION': 'true',
                'SOCKETIO_RECONNECTION_ATTEMPTS': '5',
                'SOCKETIO_RECONNECTION_DELAY': '1000',
                'SOCKETIO_RECONNECTION_DELAY_MAX': '5000',
                'SOCKETIO_TIMEOUT': '20000',
                'SOCKETIO_MAX_CONNECTIONS': '1000',
                'SOCKETIO_CONNECTION_POOL_SIZE': '10',
                'SOCKETIO_MAX_HTTP_BUFFER_SIZE': '1000000',
                'SOCKETIO_REQUIRE_AUTH': 'true',
                'SOCKETIO_SESSION_VALIDATION': 'true',
                'SOCKETIO_RATE_LIMITING': 'true',
                'SOCKETIO_CSRF_PROTECTION': 'true',
                'SOCKETIO_LOG_LEVEL': 'WARNING',
                'SOCKETIO_LOG_CONNECTIONS': 'false',
                'SOCKETIO_DEBUG': 'false',
                'SOCKETIO_ENGINEIO_LOGGER': 'false'
            }
        
        print(f"✅ Default WebSocket settings applied for {security_mode} mode")
    
    # Get admin details from user
    print("\nAdmin User Configuration:")
    admin_username = input("Admin username (default: admin): ").strip() or "admin"
    admin_email = input("Admin email: ").strip()
    
    if not admin_email:
        print("Error: Admin email is required")
        sys.exit(1)
    
    # Validate email format (basic)
    if "@" not in admin_email or "." not in admin_email.split("@")[-1]:
        print("Error: Please enter a valid email address")
        sys.exit(1)
    
    print()
    print("Generated values:")
    print(f"  Flask Secret Key: {flask_secret[:16]}... (32 chars)")
    print(f"  Encryption Key: {encryption_key[:16]}... (44 chars)")
    print(f"  Admin Username: {admin_username}")
    print(f"  Admin Email: {admin_email}")
    print(f"  Admin Password: {admin_password[:8]}... (24 chars)")
    
    # Show database configuration
    if database_settings.get('DB_TYPE') == 'mysql':
        print(f"  Database: MySQL - {database_settings['DB_NAME']}")
        print(f"  DB User: {database_settings['DB_USER']}")
        if 'DB_UNIX_SOCKET' in database_settings:
            print(f"  Connection: Unix socket ({database_settings['DB_UNIX_SOCKET']})")
        else:
            print(f"  Connection: TCP/IP ({database_settings.get('DB_HOST', 'localhost')}:{database_settings.get('DB_PORT', '3306')})")
    else:
        print(f"  Database: MySQL")
    
    # Show Redis configuration
    if configure_redis:
        print(f"  Redis: {redis_settings['REDIS_HOST']}:{redis_settings['REDIS_PORT']}")
        if redis_settings['REDIS_PASSWORD']:
            print(f"  Redis Password: {redis_settings['REDIS_PASSWORD'][:8]}... ({len(redis_settings['REDIS_PASSWORD'])} chars)")
        else:
            print(f"  Redis Password: (none)")
    
    # Show email configuration
    if configure_email:
        print(f"  Email Server: {email_settings['MAIL_SERVER']}:{email_settings['MAIL_PORT']}")
        print(f"  Email Username: {email_settings['MAIL_USERNAME']}")
    
    # Show WebSocket configuration
    if websocket_settings:
        print(f"  WebSocket Transports: {websocket_settings['SOCKETIO_TRANSPORTS']}")
        print(f"  WebSocket Security: Auth={websocket_settings['SOCKETIO_REQUIRE_AUTH']}, CSRF={websocket_settings['SOCKETIO_CSRF_PROTECTION']}")
        print(f"  WebSocket Logging: Level={websocket_settings['SOCKETIO_LOG_LEVEL']}, Debug={websocket_settings['SOCKETIO_DEBUG']}")
    print()
    
    # Create .env file
    try:
        # If .env.example exists, use it as a template
        if env_example_path.exists():
            print("Using .env.example as template...")
            with open(".env.example", "r") as f:
                env_content = f.read()
            
            # Replace placeholder values with generated ones
            env_content = env_content.replace(
                "FLASK_SECRET_KEY=CHANGE_ME_TO_A_SECURE_32_CHAR_SECRET_KEY",
                f"FLASK_SECRET_KEY={flask_secret}"
            )
            env_content = env_content.replace(
                "PLATFORM_ENCRYPTION_KEY=CHANGE_ME_TO_A_FERNET_ENCRYPTION_KEY",
                f"PLATFORM_ENCRYPTION_KEY={encryption_key}"
            )
            env_content = env_content.replace(
                "OLLAMA_URL=CHANGE_ME_TO_OLLAMA_URL_AND_PORT",
                f"OLLAMA_URL={ollama_url}"
            )
            env_content = env_content.replace(
                "OLLAMA_MODEL=CHANGE_ME_TO_OLLAMA_MODEL",
                f"OLLAMA_MODEL={ollama_model}"
            )
            
            # Update storage configuration
            env_content = re.sub(
                r'^CAPTION_MAX_STORAGE_GB=.*$',
                f'CAPTION_MAX_STORAGE_GB={storage_max_gb}',
                env_content, flags=re.MULTILINE
            )
            
            # Add storage configuration if not present
            if 'STORAGE_WARNING_THRESHOLD=' not in env_content:
                storage_config = f"""
# Storage Management Configuration
STORAGE_WARNING_THRESHOLD={storage_warning_threshold}
STORAGE_MONITORING_ENABLED={'true' if storage_monitoring_enabled else 'false'}
"""
                # Insert after CAPTION_MAX_STORAGE_GB line
                env_content = re.sub(
                    r'(^CAPTION_MAX_STORAGE_GB=.*$)',
                    r'\1' + storage_config,
                    env_content, flags=re.MULTILINE
                )
            
            # Update database configuration
            if database_settings.get('DB_TYPE') == 'mysql':
                # Replace DATABASE_URL
                env_content = re.sub(
                    r'^DATABASE_URL=.*$',
                    f'DATABASE_URL={database_settings["DATABASE_URL"]}',
                    env_content, flags=re.MULTILINE
                )
                
                # Add MySQL-specific settings if not present
                mysql_config_lines = []
                if 'DB_TYPE=' not in env_content:
                    mysql_config_lines.extend([
                        f'DB_TYPE={database_settings["DB_TYPE"]}',
                        f'DB_NAME={database_settings["DB_NAME"]}',
                        f'DB_USER={database_settings["DB_USER"]}',
                        f'DB_PASSWORD={database_settings["DB_PASSWORD"]}'
                    ])
                    
                    if 'DB_UNIX_SOCKET' in database_settings:
                        mysql_config_lines.append(f'DB_UNIX_SOCKET={database_settings["DB_UNIX_SOCKET"]}')
                    else:
                        mysql_config_lines.extend([
                            f'DB_HOST={database_settings.get("DB_HOST", "localhost")}',
                            f'DB_PORT={database_settings.get("DB_PORT", "3306")}'
                        ])
                    
                    mysql_config_lines.extend([
                        f'DB_POOL_SIZE={database_settings["DB_POOL_SIZE"]}',
                        f'DB_MAX_OVERFLOW={database_settings["DB_MAX_OVERFLOW"]}',
                        f'DB_POOL_TIMEOUT={database_settings["DB_POOL_TIMEOUT"]}',
                        f'DB_POOL_RECYCLE={database_settings["DB_POOL_RECYCLE"]}'
                    ])
                    
                    # Insert MySQL config after DATABASE_URL line
                    mysql_config = '\n' + '\n'.join(mysql_config_lines) + '\n'
                    env_content = re.sub(
                        r'(^DATABASE_URL=.*$)',
                        r'\1' + mysql_config,
                        env_content, flags=re.MULTILINE
                    )
            
            # Update Redis configuration
            if 'REDIS_URL=' in env_content:
                env_content = re.sub(
                    r'^REDIS_URL=.*$',
                    f'REDIS_URL={redis_settings["REDIS_URL"]}',
                    env_content, flags=re.MULTILINE
                )
            
            if 'REDIS_PASSWORD=' in env_content:
                env_content = re.sub(
                    r'^REDIS_PASSWORD=.*$',
                    f'REDIS_PASSWORD={redis_settings["REDIS_PASSWORD"]}',
                    env_content, flags=re.MULTILINE
                )
            
            # Apply security settings
            for setting, value in security_settings.items():
                pattern = f'^{setting}=.*$'
                replacement = f'{setting}={value}'
                env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
            
            # Update email settings
            for setting, value in email_settings.items():
                if f'{setting}=' in env_content:
                    pattern = f'^{setting}=.*$'
                    replacement = f'{setting}={value}'
                    env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
            
            # Add email settings if not already present
            if 'MAIL_SERVER=' not in env_content:
                email_config = f"""
# Email Configuration (for user notifications)
MAIL_SERVER={email_settings['MAIL_SERVER']}
MAIL_PORT={email_settings['MAIL_PORT']}
MAIL_USE_TLS={'true' if email_settings['MAIL_USE_TLS'] else 'false'}
MAIL_USERNAME={email_settings['MAIL_USERNAME']}
MAIL_PASSWORD={email_settings['MAIL_PASSWORD']}
MAIL_DEFAULT_SENDER={email_settings['MAIL_DEFAULT_SENDER']}
"""
                env_content += email_config
            
            # Add WebSocket settings if not already present
            if websocket_settings and 'SOCKETIO_TRANSPORTS=' not in env_content:
                websocket_config = f"""
# WebSocket Configuration (for real-time communication)
SOCKETIO_TRANSPORTS={websocket_settings['SOCKETIO_TRANSPORTS']}
SOCKETIO_PING_TIMEOUT={websocket_settings['SOCKETIO_PING_TIMEOUT']}
SOCKETIO_PING_INTERVAL={websocket_settings['SOCKETIO_PING_INTERVAL']}
SOCKETIO_CORS_CREDENTIALS={websocket_settings['SOCKETIO_CORS_CREDENTIALS']}
SOCKETIO_CORS_METHODS={websocket_settings['SOCKETIO_CORS_METHODS']}
SOCKETIO_CORS_HEADERS={websocket_settings['SOCKETIO_CORS_HEADERS']}
SOCKETIO_RECONNECTION={websocket_settings['SOCKETIO_RECONNECTION']}
SOCKETIO_RECONNECTION_ATTEMPTS={websocket_settings['SOCKETIO_RECONNECTION_ATTEMPTS']}
SOCKETIO_RECONNECTION_DELAY={websocket_settings['SOCKETIO_RECONNECTION_DELAY']}
SOCKETIO_RECONNECTION_DELAY_MAX={websocket_settings['SOCKETIO_RECONNECTION_DELAY_MAX']}
SOCKETIO_TIMEOUT={websocket_settings['SOCKETIO_TIMEOUT']}
SOCKETIO_FORCE_NEW={websocket_settings['SOCKETIO_FORCE_NEW']}
SOCKETIO_UPGRADE={websocket_settings['SOCKETIO_UPGRADE']}
SOCKETIO_REMEMBER_UPGRADE={websocket_settings['SOCKETIO_REMEMBER_UPGRADE']}
SOCKETIO_WITH_CREDENTIALS={websocket_settings['SOCKETIO_WITH_CREDENTIALS']}
SOCKETIO_MAX_CONNECTIONS={websocket_settings['SOCKETIO_MAX_CONNECTIONS']}
SOCKETIO_CONNECTION_POOL_SIZE={websocket_settings['SOCKETIO_CONNECTION_POOL_SIZE']}
SOCKETIO_MAX_HTTP_BUFFER_SIZE={websocket_settings['SOCKETIO_MAX_HTTP_BUFFER_SIZE']}
SOCKETIO_REQUIRE_AUTH={websocket_settings['SOCKETIO_REQUIRE_AUTH']}
SOCKETIO_SESSION_VALIDATION={websocket_settings['SOCKETIO_SESSION_VALIDATION']}
SOCKETIO_RATE_LIMITING={websocket_settings['SOCKETIO_RATE_LIMITING']}
SOCKETIO_CSRF_PROTECTION={websocket_settings['SOCKETIO_CSRF_PROTECTION']}
SOCKETIO_LOG_LEVEL={websocket_settings['SOCKETIO_LOG_LEVEL']}
SOCKETIO_LOG_CONNECTIONS={websocket_settings['SOCKETIO_LOG_CONNECTIONS']}
SOCKETIO_DEBUG={websocket_settings['SOCKETIO_DEBUG']}
SOCKETIO_ENGINEIO_LOGGER={websocket_settings['SOCKETIO_ENGINEIO_LOGGER']}
"""
                env_content += websocket_config
        else:
            # Create a basic .env file
            database_config = ""
            if database_settings.get('DB_TYPE') == 'mysql':
                database_config = f"""
# Database Configuration - MySQL
DB_TYPE={database_settings['DB_TYPE']}
DB_NAME={database_settings['DB_NAME']}
DB_USER={database_settings['DB_USER']}
DB_PASSWORD={database_settings['DB_PASSWORD']}"""
                
                if 'DB_UNIX_SOCKET' in database_settings:
                    database_config += f"\nDB_UNIX_SOCKET={database_settings['DB_UNIX_SOCKET']}"
                else:
                    database_config += f"""
DB_HOST={database_settings.get('DB_HOST', 'localhost')}
DB_PORT={database_settings.get('DB_PORT', '3306')}"""
                
                database_config += f"""
DATABASE_URL={database_settings['DATABASE_URL']}

# Database Performance Configuration
DB_POOL_SIZE={database_settings['DB_POOL_SIZE']}
DB_MAX_OVERFLOW={database_settings['DB_MAX_OVERFLOW']}
DB_POOL_TIMEOUT={database_settings['DB_POOL_TIMEOUT']}
DB_POOL_RECYCLE={database_settings['DB_POOL_RECYCLE']}

# MySQL Security Hardening (Tasks 13-20)
MYSQL_PASSWORD_MIN_LENGTH={database_settings['MYSQL_PASSWORD_MIN_LENGTH']}
MYSQL_MAX_FAILED_LOGINS={database_settings['MYSQL_MAX_FAILED_LOGINS']}
MYSQL_SESSION_TIMEOUT={database_settings['MYSQL_SESSION_TIMEOUT']}
MYSQL_CERT_EXPIRY_WARNING_DAYS={database_settings['MYSQL_CERT_EXPIRY_WARNING_DAYS']}
MYSQL_SECURITY_KEY_FILE={database_settings['MYSQL_SECURITY_KEY_FILE']}

# MySQL Backup and Recovery
MYSQL_BACKUP_DIR={database_settings['MYSQL_BACKUP_DIR']}
MYSQL_BACKUP_RETENTION_DAYS={database_settings['MYSQL_BACKUP_RETENTION_DAYS']}
MYSQL_BACKUP_COMPRESSION_LEVEL={database_settings['MYSQL_BACKUP_COMPRESSION_LEVEL']}
MYSQL_MAX_BACKUP_SIZE_GB={database_settings['MYSQL_MAX_BACKUP_SIZE_GB']}
MYSQL_BACKUP_TIMEOUT_MINUTES={database_settings['MYSQL_BACKUP_TIMEOUT_MINUTES']}
MYSQL_PARALLEL_BACKUP_JOBS={database_settings['MYSQL_PARALLEL_BACKUP_JOBS']}
MYSQL_BACKUP_ENCRYPTION_KEY_FILE={database_settings['MYSQL_BACKUP_ENCRYPTION_KEY_FILE']}"""
                
                # Add S3 backup settings if configured
                if database_settings.get('MYSQL_BACKUP_S3_BUCKET'):
                    database_config += f"""

# AWS S3 Backup Configuration
MYSQL_BACKUP_S3_BUCKET={database_settings['MYSQL_BACKUP_S3_BUCKET']}
AWS_ACCESS_KEY_ID={database_settings['AWS_ACCESS_KEY_ID']}
AWS_SECRET_ACCESS_KEY={database_settings['AWS_SECRET_ACCESS_KEY']}
AWS_DEFAULT_REGION={database_settings['AWS_DEFAULT_REGION']}"""
                
                database_config += f"""

# MySQL Performance Monitoring
MYSQL_MONITORING_INTERVAL={database_settings['MYSQL_MONITORING_INTERVAL']}
MYSQL_AUTO_OPTIMIZE_INTERVAL={database_settings['MYSQL_AUTO_OPTIMIZE_INTERVAL']}
MYSQL_AUTO_OPTIMIZE_ENABLED={'true' if database_settings['MYSQL_AUTO_OPTIMIZE_ENABLED'] else 'false'}
MYSQL_SLOW_QUERY_THRESHOLD_MS={database_settings['MYSQL_SLOW_QUERY_THRESHOLD_MS']}
MYSQL_QUERY_CACHE_SIZE={database_settings['MYSQL_QUERY_CACHE_SIZE']}

# MySQL Dashboard Configuration
MYSQL_DASHBOARD_UPDATE_INTERVAL={database_settings['MYSQL_DASHBOARD_UPDATE_INTERVAL']}
MYSQL_DASHBOARD_RETENTION_HOURS={database_settings['MYSQL_DASHBOARD_RETENTION_HOURS']}
MYSQL_DASHBOARD_REAL_TIME={'true' if database_settings['MYSQL_DASHBOARD_REAL_TIME'] else 'false'}
MYSQL_DASHBOARD_MAX_CHART_POINTS={database_settings['MYSQL_DASHBOARD_MAX_CHART_POINTS']}

# MySQL Performance Thresholds
MYSQL_CONNECTION_USAGE_CRITICAL={database_settings['MYSQL_CONNECTION_USAGE_CRITICAL']}
MYSQL_CONNECTION_USAGE_WARNING={database_settings['MYSQL_CONNECTION_USAGE_WARNING']}
MYSQL_SLOW_QUERY_RATIO_CRITICAL={database_settings['MYSQL_SLOW_QUERY_RATIO_CRITICAL']}
MYSQL_SLOW_QUERY_RATIO_WARNING={database_settings['MYSQL_SLOW_QUERY_RATIO_WARNING']}
MYSQL_AVG_QUERY_TIME_CRITICAL={database_settings['MYSQL_AVG_QUERY_TIME_CRITICAL']}
MYSQL_AVG_QUERY_TIME_WARNING={database_settings['MYSQL_AVG_QUERY_TIME_WARNING']}
MYSQL_BUFFER_POOL_HIT_RATIO_CRITICAL={database_settings['MYSQL_BUFFER_POOL_HIT_RATIO_CRITICAL']}
MYSQL_BUFFER_POOL_HIT_RATIO_WARNING={database_settings['MYSQL_BUFFER_POOL_HIT_RATIO_WARNING']}"""
            else:
                database_config = f"""
# Database Configuration - MySQL
DATABASE_URL={database_settings['DATABASE_URL']}

# Database Performance Configuration
DB_POOL_SIZE={database_settings['DB_POOL_SIZE']}
DB_MAX_OVERFLOW={database_settings['DB_MAX_OVERFLOW']}
DB_POOL_TIMEOUT={database_settings['DB_POOL_TIMEOUT']}
DB_POOL_RECYCLE={database_settings['DB_POOL_RECYCLE']}

# MySQL Security Hardening (Tasks 13-20)
MYSQL_PASSWORD_MIN_LENGTH=12
MYSQL_MAX_FAILED_LOGINS=5
MYSQL_SESSION_TIMEOUT=3600
MYSQL_CERT_EXPIRY_WARNING_DAYS=30
MYSQL_SECURITY_KEY_FILE=.mysql_security_key

# MySQL Backup and Recovery
MYSQL_BACKUP_DIR=./backups
MYSQL_BACKUP_RETENTION_DAYS=30
MYSQL_BACKUP_COMPRESSION_LEVEL=6
MYSQL_MAX_BACKUP_SIZE_GB=10
MYSQL_BACKUP_TIMEOUT_MINUTES=60
MYSQL_PARALLEL_BACKUP_JOBS=2
MYSQL_BACKUP_ENCRYPTION_KEY_FILE=.mysql_backup_key

# MySQL Performance Monitoring
MYSQL_MONITORING_INTERVAL=300
MYSQL_AUTO_OPTIMIZE_INTERVAL=3600
MYSQL_AUTO_OPTIMIZE_ENABLED=false
MYSQL_SLOW_QUERY_THRESHOLD_MS=1000
MYSQL_QUERY_CACHE_SIZE=100

# MySQL Dashboard Configuration
MYSQL_DASHBOARD_UPDATE_INTERVAL=30
MYSQL_DASHBOARD_RETENTION_HOURS=168
MYSQL_DASHBOARD_REAL_TIME=true
MYSQL_DASHBOARD_MAX_CHART_POINTS=100

# MySQL Performance Thresholds
MYSQL_CONNECTION_USAGE_CRITICAL=90
MYSQL_CONNECTION_USAGE_WARNING=75
MYSQL_SLOW_QUERY_RATIO_CRITICAL=20
MYSQL_SLOW_QUERY_RATIO_WARNING=10
MYSQL_AVG_QUERY_TIME_CRITICAL=2000
MYSQL_AVG_QUERY_TIME_WARNING=1000
MYSQL_BUFFER_POOL_HIT_RATIO_CRITICAL=90
MYSQL_BUFFER_POOL_HIT_RATIO_WARNING=95"""
            
            redis_config = f"""
# Redis Configuration
REDIS_URL={redis_settings['REDIS_URL']}
REDIS_HOST={redis_settings['REDIS_HOST']}
REDIS_PORT={redis_settings['REDIS_PORT']}
REDIS_DB={redis_settings['REDIS_DB']}
REDIS_PASSWORD={redis_settings['REDIS_PASSWORD']}
REDIS_SSL={'true' if redis_settings.get('REDIS_SSL') else 'false'}
SESSION_STORAGE={redis_settings['SESSION_STORAGE']}"""
            
            env_content = f"""# Vedfolnir Configuration
# Generated automatically - DO NOT COMMIT TO VERSION CONTROL

# Flask Secret Key (for session security)
FLASK_SECRET_KEY={flask_secret}

# Platform Encryption Key (for database credential encryption)
PLATFORM_ENCRYPTION_KEY={encryption_key}

# Basic application settings
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=false
LOG_LEVEL=WARNING
{database_config}
{redis_config}

# Ollama Configuration
OLLAMA_URL={ollama_url}
OLLAMA_MODEL={ollama_model}

# Storage Management Configuration
CAPTION_MAX_STORAGE_GB={storage_max_gb}
STORAGE_WARNING_THRESHOLD={storage_warning_threshold}
STORAGE_MONITORING_ENABLED={'true' if storage_monitoring_enabled else 'false'}

# Security Settings
SECURITY_CSRF_ENABLED={security_settings['SECURITY_CSRF_ENABLED']}
SECURITY_RATE_LIMITING_ENABLED={security_settings['SECURITY_RATE_LIMITING_ENABLED']}
SECURITY_INPUT_VALIDATION_ENABLED={security_settings['SECURITY_INPUT_VALIDATION_ENABLED']}

# Email Configuration (for user notifications)
MAIL_SERVER={email_settings['MAIL_SERVER']}
MAIL_PORT={email_settings['MAIL_PORT']}
MAIL_USE_TLS={'true' if email_settings['MAIL_USE_TLS'] else 'false'}
MAIL_USERNAME={email_settings['MAIL_USERNAME']}
MAIL_PASSWORD={email_settings['MAIL_PASSWORD']}
MAIL_DEFAULT_SENDER={email_settings['MAIL_DEFAULT_SENDER']}
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        # Set restrictive permissions (Unix-like systems only)
        if os.name != 'nt':  # Not Windows
            os.chmod(".env", 0o600)  # Read/write for owner only
        
        print("✅ Successfully created .env file!")
        print()
        
        # Create admin user in database
        print("Creating admin user in database...")
        if create_admin_user(admin_username, admin_email, admin_password):
            print("✅ Successfully created admin user in database!")
        else:
            print("❌ Failed to create admin user. You may need to run the application first to initialize the database.")
        
        print()
        print("Next steps:")
        
        if database_settings.get('DB_TYPE') == 'mysql':
            print("1. Ensure MySQL/MariaDB is running and accessible")
            print("2. Install MySQL connector: pip install pymysql")
            print("3. Start the application:")
        else:
            print("1. Start the application:")
        
        print("   python web_app.py")
        print()
        print("2. Log in with your admin credentials:")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        print()
        
        if database_settings.get('DB_TYPE') == 'mysql':
            print("3. The application will automatically create MySQL tables on first startup")
            print()
        
        print("⚠️  IMPORTANT: Save your admin password securely!")
        print("   Consider using a password manager.")
        print()
        
        if database_settings.get('DB_TYPE') == 'mysql':
            print("📋 Database Information:")
            print(f"   Type: MySQL/MariaDB")
            print(f"   Database: {database_settings['DB_NAME']}")
            print(f"   User: {database_settings['DB_USER']}")
            if 'DB_UNIX_SOCKET' in database_settings:
                print(f"   Connection: Unix socket ({database_settings['DB_UNIX_SOCKET']})")
            else:
                print(f"   Connection: {database_settings.get('DB_HOST')}:{database_settings.get('DB_PORT')}")
            print()
        
        if configure_redis and redis_settings['REDIS_PASSWORD']:
            print("🔑 Redis Information:")
            print(f"   Host: {redis_settings['REDIS_HOST']}:{redis_settings['REDIS_PORT']}")
            print(f"   Password: {redis_settings['REDIS_PASSWORD']}")
            print("   Make sure Redis is running with authentication enabled")
            print()
        
        print("📖 For more information, see: docs/security/environment-setup.md")
        
    except Exception as e:
        print(f"Error creating .env file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()