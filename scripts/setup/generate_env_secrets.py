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
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database import DatabaseManager
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
    print("1. SQLite (default, good for development)")
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
        
    else:
        # SQLite
        database_settings = {
            'DB_TYPE': 'sqlite',
            'DATABASE_URL': 'sqlite:///storage/database/vedfolnir.db',
            'DB_POOL_SIZE': '50',
            'DB_MAX_OVERFLOW': '100',
            'DB_POOL_TIMEOUT': '30',
            'DB_POOL_RECYCLE': '1800'
        }
    
    # Get Ollama configuration from user
    print("\nOllama Configuration:")
    ollama_url = input("Ollama URL (default: http://localhost:11434): ").strip() or "http://localhost:11434"
    ollama_model = input("Ollama model (default: llava:7b): ").strip() or "llava:7b"
    
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
        print(f"  Database: SQLite")
    
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
            
            # Update database configuration
            import re
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
DB_POOL_RECYCLE={database_settings['DB_POOL_RECYCLE']}"""
            else:
                database_config = f"""
# Database Configuration - SQLite
DATABASE_URL={database_settings['DATABASE_URL']}

# Database Performance Configuration
DB_POOL_SIZE={database_settings['DB_POOL_SIZE']}
DB_MAX_OVERFLOW={database_settings['DB_MAX_OVERFLOW']}
DB_POOL_TIMEOUT={database_settings['DB_POOL_TIMEOUT']}
DB_POOL_RECYCLE={database_settings['DB_POOL_RECYCLE']}"""
            
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
LOG_LEVEL=INFO
{database_config}
{redis_config}

# Ollama Configuration
OLLAMA_URL={ollama_url}
OLLAMA_MODEL={ollama_model}

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