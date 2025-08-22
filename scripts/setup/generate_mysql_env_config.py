#!/usr/bin/env python3
"""
MySQL Environment Configuration Generator for Vedfolnir

This script generates secure environment configurations for different deployment scenarios:
- Development
- Production  
- Docker
- Testing

It replaces all SQLite references with MySQL configurations and generates secure keys.
"""

import os
import sys
import secrets
import argparse
from pathlib import Path
from cryptography.fernet import Fernet

def generate_secure_key(length=32):
    """Generate a secure random key."""
    return secrets.token_urlsafe(length)

def generate_fernet_key():
    """Generate a Fernet encryption key."""
    return Fernet.generate_key().decode()

def generate_mysql_password(length=16):
    """Generate a secure MySQL password."""
    # Use a mix of letters, numbers, and safe symbols
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_development_env():
    """Create development environment configuration."""
    config = f"""# Vedfolnir Development Environment Configuration
# Generated automatically - customize as needed

# =============================================================================
# DEVELOPMENT ENVIRONMENT SETTINGS
# =============================================================================

ENVIRONMENT=development
FLASK_ENV=development
FLASK_DEBUG=true
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
APP_VERSION=0.001-dev

# Security Keys (Generated securely)
FLASK_SECRET_KEY={generate_secure_key()}
PLATFORM_ENCRYPTION_KEY={generate_fernet_key()}

# =============================================================================
# DEVELOPMENT MYSQL CONFIGURATION
# =============================================================================

DB_TYPE=mysql
DB_NAME=vedfolnir_dev
DB_USER=vedfolnir_dev
DB_PASSWORD={generate_mysql_password()}
DB_HOST=localhost
DB_PORT=3306

# Development Database URL
DATABASE_URL=mysql+pymysql://vedfolnir_dev:{generate_mysql_password()}@localhost:3306/vedfolnir_dev?charset=utf8mb4

# Development Connection Pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_QUERY_LOGGING=true

# MySQL Development Settings
MYSQL_SSL_ENABLED=false
MYSQL_CHARSET=utf8mb4
MYSQL_COLLATION=utf8mb4_unicode_ci
MYSQL_ENGINE=InnoDB

# =============================================================================
# DEVELOPMENT REDIS CONFIGURATION
# =============================================================================

REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false

REDIS_SESSION_PREFIX=vedfolnir_dev:session:
REDIS_SESSION_TIMEOUT=7200
SESSION_COOKIE_SECURE=false

# =============================================================================
# DEVELOPMENT AI/ML CONFIGURATION
# =============================================================================

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b
OLLAMA_TIMEOUT=120.0
OLLAMA_MAX_CONCURRENT_REQUESTS=1

# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================

LOG_LEVEL=DEBUG
MYSQL_LOG_QUERIES=true
MYSQL_LOG_SLOW_QUERIES=true
DEBUG_TOOLBAR_ENABLED=true
DEVELOPMENT_MODE=true

# Security (relaxed for development)
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=false
SECURITY_HEADERS_ENABLED=true

# Processing
DRY_RUN=true
MAX_POSTS_PER_RUN=5
USER_PROCESSING_DELAY=2

# Storage
STORAGE_BASE_DIR=storage/dev
STORAGE_IMAGES_DIR=storage/dev/images
LOGS_DIR=logs/dev

# Testing
TEST_DATABASE_URL=mysql+pymysql://vedfolnir_test:{generate_mysql_password()}@localhost:3306/vedfolnir_test?charset=utf8mb4
TEST_REDIS_URL=redis://localhost:6379/1
TESTING_MODE=false
"""
    return config

def create_production_env():
    """Create production environment configuration."""
    mysql_password = generate_mysql_password(24)
    redis_password = generate_mysql_password(20)
    
    config = f"""# Vedfolnir Production Environment Configuration
# SECURITY WARNING: Customize all values for your production environment

# =============================================================================
# PRODUCTION ENVIRONMENT SETTINGS
# =============================================================================

ENVIRONMENT=production
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
APP_VERSION=1.0.0

# Security Keys (Generated securely - KEEP THESE SECURE)
FLASK_SECRET_KEY={generate_secure_key(48)}
PLATFORM_ENCRYPTION_KEY={generate_fernet_key()}

# =============================================================================
# PRODUCTION MYSQL CONFIGURATION
# =============================================================================

DB_TYPE=mysql
DB_NAME=vedfolnir
DB_USER=vedfolnir_prod
DB_PASSWORD={mysql_password}
DB_HOST=mysql.production.example.com
DB_PORT=3306

# Production Database URL with SSL
DATABASE_URL=mysql+pymysql://vedfolnir_prod:{mysql_password}@mysql.production.example.com:3306/vedfolnir?charset=utf8mb4&ssl_disabled=false&ssl_verify_cert=true

# Production Connection Pool
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_QUERY_LOGGING=false

# MySQL Production Settings
MYSQL_SSL_ENABLED=true
MYSQL_SSL_REQUIRED=true
MYSQL_SSL_VERIFY_CERT=true
MYSQL_SSL_VERIFY_IDENTITY=true
MYSQL_CHARSET=utf8mb4
MYSQL_COLLATION=utf8mb4_unicode_ci
MYSQL_ENGINE=InnoDB

# =============================================================================
# PRODUCTION REDIS CONFIGURATION
# =============================================================================

REDIS_URL=redis://:{redis_password}@redis.production.example.com:6380/0
REDIS_HOST=redis.production.example.com
REDIS_PORT=6380
REDIS_DB=0
REDIS_PASSWORD={redis_password}
REDIS_SSL=true

REDIS_SESSION_PREFIX=vedfolnir_prod:session:
REDIS_SESSION_TIMEOUT=7200
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict

# =============================================================================
# PRODUCTION AI/ML CONFIGURATION
# =============================================================================

OLLAMA_URL=http://ollama.production.example.com:11434
OLLAMA_MODEL=llava:13b
OLLAMA_TIMEOUT=60.0
OLLAMA_MAX_CONCURRENT_REQUESTS=10

# =============================================================================
# PRODUCTION SETTINGS
# =============================================================================

LOG_LEVEL=WARNING
MYSQL_LOG_QUERIES=false
MYSQL_LOG_SLOW_QUERIES=true
DEBUG_TOOLBAR_ENABLED=false
PRODUCTION_MODE=true
OPTIMIZE_FOR_PRODUCTION=true

# Security (full security enabled)
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_HEADERS_ENABLED=true
SECURITY_SESSION_VALIDATION_ENABLED=true
SECURITY_ADMIN_CHECKS_ENABLED=true

# Authentication
AUTH_REQUIRE_AUTH=true
AUTH_SESSION_LIFETIME=28800
PASSWORD_MIN_LENGTH=16
PASSWORD_HASH_ROUNDS=14

# Processing
DRY_RUN=false
MAX_POSTS_PER_RUN=50
USER_PROCESSING_DELAY=5
MAX_USERS_PER_RUN=20

# Rate Limiting (strict)
RATE_LIMIT_REQUESTS_PER_MINUTE=30
RATE_LIMIT_REQUESTS_PER_HOUR=500
RATE_LIMIT_REQUESTS_PER_DAY=5000

# Storage
STORAGE_BASE_DIR=/var/lib/vedfolnir/storage
STORAGE_IMAGES_DIR=/var/lib/vedfolnir/storage/images
LOGS_DIR=/var/log/vedfolnir
MYSQL_BACKUP_DIR=/var/lib/vedfolnir/backups/mysql

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true
MYSQL_PERFORMANCE_MONITORING=true

# Email
MAIL_SERVER=smtp.production.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=vedfolnir@production.example.com
MAIL_PASSWORD=REPLACE_WITH_EMAIL_PASSWORD
MAIL_DEFAULT_SENDER=noreply@production.example.com
"""
    return config

def create_docker_env():
    """Create Docker environment configuration."""
    mysql_password = generate_mysql_password(20)
    mysql_root_password = generate_mysql_password(24)
    redis_password = generate_mysql_password(16)
    
    config = f"""# Vedfolnir Docker Environment Configuration
# Generated for Docker Compose deployment

# =============================================================================
# DOCKER ENVIRONMENT SETTINGS
# =============================================================================

ENVIRONMENT=docker
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
APP_VERSION=1.0.0-docker

# Security Keys (Generated securely)
FLASK_SECRET_KEY={generate_secure_key(40)}
PLATFORM_ENCRYPTION_KEY={generate_fernet_key()}

# =============================================================================
# DOCKER MYSQL CONFIGURATION
# =============================================================================

DB_TYPE=mysql
DB_NAME=vedfolnir
DB_USER=vedfolnir
DB_PASSWORD={mysql_password}
DB_HOST=mysql
DB_PORT=3306

# Docker Database URL
DATABASE_URL=mysql+pymysql://vedfolnir:{mysql_password}@mysql:3306/vedfolnir?charset=utf8mb4

# Docker Connection Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_QUERY_LOGGING=false

# MySQL Docker Settings
MYSQL_CHARSET=utf8mb4
MYSQL_COLLATION=utf8mb4_unicode_ci
MYSQL_ENGINE=InnoDB
MYSQL_SSL_ENABLED=false

# MySQL Container Environment
MYSQL_ROOT_PASSWORD={mysql_root_password}
MYSQL_DATABASE=vedfolnir
MYSQL_USER=vedfolnir
MYSQL_PASSWORD={mysql_password}

# =============================================================================
# DOCKER REDIS CONFIGURATION
# =============================================================================

REDIS_URL=redis://:{redis_password}@redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD={redis_password}
REDIS_SSL=false

REDIS_SESSION_PREFIX=vedfolnir_docker:session:
REDIS_SESSION_TIMEOUT=7200
SESSION_COOKIE_SECURE=true

# =============================================================================
# DOCKER AI/ML CONFIGURATION
# =============================================================================

OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llava:7b
OLLAMA_TIMEOUT=90.0
OLLAMA_MAX_CONCURRENT_REQUESTS=5

# =============================================================================
# DOCKER SETTINGS
# =============================================================================

LOG_LEVEL=INFO
MYSQL_LOG_QUERIES=false
MYSQL_LOG_SLOW_QUERIES=true
DOCKER_DEPLOYMENT=true
CONTAINER_NAME=vedfolnir_app

# Security
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_HEADERS_ENABLED=true

# Processing
DRY_RUN=false
MAX_POSTS_PER_RUN=20
USER_PROCESSING_DELAY=3

# Storage (container paths)
STORAGE_BASE_DIR=/app/storage
STORAGE_IMAGES_DIR=/app/storage/images
LOGS_DIR=/app/logs
MYSQL_BACKUP_DIR=/app/backups

# Health Checks
HEALTH_CHECK_ENABLED=true
DOCKER_HEALTH_CHECK_INTERVAL=30s
DOCKER_HEALTH_CHECK_TIMEOUT=10s
DOCKER_HEALTH_CHECK_RETRIES=3

# Performance
CACHE_ENABLED=true
CACHE_TYPE=redis
ENABLE_GZIP_COMPRESSION=true
"""
    return config

def create_testing_env():
    """Create testing environment configuration."""
    config = f"""# Vedfolnir Testing Environment Configuration
# Generated for automated testing

# =============================================================================
# TESTING ENVIRONMENT SETTINGS
# =============================================================================

ENVIRONMENT=testing
FLASK_ENV=testing
FLASK_DEBUG=false
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
APP_VERSION=0.001-test

# Security Keys (Generated for testing)
FLASK_SECRET_KEY={generate_secure_key()}
PLATFORM_ENCRYPTION_KEY={generate_fernet_key()}

# =============================================================================
# TESTING MYSQL CONFIGURATION
# =============================================================================

DB_TYPE=mysql
DB_NAME=vedfolnir_test
DB_USER=vedfolnir_test
DB_PASSWORD={generate_mysql_password()}
DB_HOST=localhost
DB_PORT=3306

# Testing Database URL
DATABASE_URL=mysql+pymysql://vedfolnir_test:{generate_mysql_password()}@localhost:3306/vedfolnir_test?charset=utf8mb4

# Testing Connection Pool (minimal)
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=300
DB_POOL_PRE_PING=true
DB_QUERY_LOGGING=false

# MySQL Testing Settings
MYSQL_SSL_ENABLED=false
MYSQL_CHARSET=utf8mb4
MYSQL_COLLATION=utf8mb4_unicode_ci
MYSQL_ENGINE=InnoDB

# =============================================================================
# TESTING REDIS CONFIGURATION
# =============================================================================

REDIS_URL=redis://localhost:6379/15
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=15
REDIS_PASSWORD=
REDIS_SSL=false

REDIS_SESSION_PREFIX=vedfolnir_test:session:
REDIS_SESSION_TIMEOUT=3600
SESSION_COOKIE_SECURE=false

# =============================================================================
# TESTING SETTINGS
# =============================================================================

LOG_LEVEL=ERROR
MYSQL_LOG_QUERIES=false
MYSQL_LOG_SLOW_QUERIES=false
TESTING_MODE=true
TEST_DATA_CLEANUP=true
TEST_FIXTURES_ENABLED=true
TEST_MOCK_EXTERNAL_APIS=true

# Security (minimal for testing)
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=false
SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_HEADERS_ENABLED=false

# Processing (fast for testing)
DRY_RUN=true
MAX_POSTS_PER_RUN=2
USER_PROCESSING_DELAY=0.1

# Storage (temporary)
STORAGE_BASE_DIR=storage/test
STORAGE_IMAGES_DIR=storage/test/images
LOGS_DIR=logs/test

# Disable external services for testing
HEALTH_CHECK_ENABLED=false
METRICS_ENABLED=false
MAIL_SUPPRESS_SEND=true
"""
    return config

def write_env_file(content, filename):
    """Write environment configuration to file."""
    try:
        with open(filename, 'w') as f:
            f.write(content)
        print(f"✓ Created {filename}")
        return True
    except Exception as e:
        print(f"✗ Failed to create {filename}: {e}")
        return False

def create_database_setup_script(env_type):
    """Create MySQL database setup script for the environment."""
    if env_type == 'development':
        db_name = 'vedfolnir_dev'
        db_user = 'vedfolnir_dev'
        test_db_name = 'vedfolnir_test'
        test_db_user = 'vedfolnir_test'
    elif env_type == 'testing':
        db_name = 'vedfolnir_test'
        db_user = 'vedfolnir_test'
        test_db_name = None
        test_db_user = None
    else:
        db_name = 'vedfolnir'
        db_user = 'vedfolnir_prod'
        test_db_name = None
        test_db_user = None
    
    script = f"""#!/bin/bash
# MySQL Database Setup Script for {env_type.title()} Environment
# Generated automatically by generate_mysql_env_config.py

set -e

echo "Setting up MySQL databases for {env_type} environment..."

# Create main database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY 'REPLACE_WITH_PASSWORD';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';"

"""
    
    if test_db_name:
        script += f"""
# Create test database
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS {test_db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p -e "CREATE USER IF NOT EXISTS '{test_db_user}'@'localhost' IDENTIFIED BY 'REPLACE_WITH_TEST_PASSWORD';"
mysql -u root -p -e "GRANT ALL PRIVILEGES ON {test_db_name}.* TO '{test_db_user}'@'localhost';"
"""
    
    script += """
mysql -u root -p -e "FLUSH PRIVILEGES;"

echo "✓ MySQL databases created successfully"
echo "⚠️  Remember to update the passwords in your .env file"
"""
    
    return script

def main():
    parser = argparse.ArgumentParser(description='Generate MySQL environment configurations for Vedfolnir')
    parser.add_argument('--type', choices=['development', 'production', 'docker', 'testing', 'all'], 
                       default='all', help='Type of environment configuration to generate')
    parser.add_argument('--output-dir', default='.', help='Output directory for configuration files')
    parser.add_argument('--create-db-scripts', action='store_true', 
                       help='Create MySQL database setup scripts')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print("🔧 Generating MySQL environment configurations for Vedfolnir...")
    print("⚠️  All SQLite references have been replaced with MySQL configurations")
    print()
    
    success_count = 0
    total_count = 0
    
    if args.type in ['development', 'all']:
        total_count += 1
        if write_env_file(create_development_env(), output_dir / '.env.development'):
            success_count += 1
            if args.create_db_scripts:
                script_content = create_database_setup_script('development')
                script_path = output_dir / 'setup_mysql_development.sh'
                with open(script_path, 'w') as f:
                    f.write(script_content)
                os.chmod(script_path, 0o755)
                print(f"✓ Created {script_path}")
    
    if args.type in ['production', 'all']:
        total_count += 1
        if write_env_file(create_production_env(), output_dir / '.env.production'):
            success_count += 1
            if args.create_db_scripts:
                script_content = create_database_setup_script('production')
                script_path = output_dir / 'setup_mysql_production.sh'
                with open(script_path, 'w') as f:
                    f.write(script_content)
                os.chmod(script_path, 0o755)
                print(f"✓ Created {script_path}")
    
    if args.type in ['docker', 'all']:
        total_count += 1
        if write_env_file(create_docker_env(), output_dir / '.env.docker'):
            success_count += 1
    
    if args.type in ['testing', 'all']:
        total_count += 1
        if write_env_file(create_testing_env(), output_dir / '.env.testing'):
            success_count += 1
            if args.create_db_scripts:
                script_content = create_database_setup_script('testing')
                script_path = output_dir / 'setup_mysql_testing.sh'
                with open(script_path, 'w') as f:
                    f.write(script_content)
                os.chmod(script_path, 0o755)
                print(f"✓ Created {script_path}")
    
    print()
    print(f"📊 Generated {success_count}/{total_count} configuration files successfully")
    
    if success_count > 0:
        print()
        print("🔐 SECURITY REMINDERS:")
        print("• All configurations use MySQL instead of SQLite")
        print("• Secure keys and passwords have been generated automatically")
        print("• Review and customize all configuration values for your environment")
        print("• Never commit .env files to version control")
        print("• Set up SSL/TLS for production MySQL and Redis connections")
        print("• Regularly rotate encryption keys and passwords")
        print()
        print("📚 NEXT STEPS:")
        print("1. Copy the appropriate .env.* file to .env")
        print("2. Customize database hosts, ports, and other settings")
        print("3. Set up MySQL and Redis servers")
        print("4. Run database setup scripts if generated")
        print("5. Initialize the database: python -c 'from database import init_db; init_db()'")
        print("6. Create admin user: python scripts/setup/init_admin_user.py")
        print("7. Test the configuration: python scripts/setup/verify_env_setup.py")
    
    return 0 if success_count == total_count else 1

if __name__ == '__main__':
    sys.exit(main())
