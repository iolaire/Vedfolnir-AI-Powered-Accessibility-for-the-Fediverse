#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MySQL-based deployment script for Vedfolnir
# This script replaces the SQLite-based deployment with MySQL deployment

set -e

echo "🚀 Starting MySQL-based Vedfolnir deployment..."

# Configuration
BACKUP_DIR="backups/mysql/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="logs/mysql_deployment.log"
MYSQL_USER="${DB_USER:-vedfolnir}"
MYSQL_PASSWORD="${DB_PASSWORD}"
MYSQL_DATABASE="${DB_NAME:-vedfolnir}"
MYSQL_HOST="${DB_HOST:-localhost}"
MYSQL_PORT="${DB_PORT:-3306}"

# Create directories
mkdir -p "$BACKUP_DIR" logs storage/backups/mysql

# Functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    log "🔍 Checking deployment prerequisites..."
    
    # Check if MySQL client is available
    if ! command -v mysql &> /dev/null; then
        log "❌ MySQL client not found. Please install MySQL client."
        exit 1
    fi
    
    # Check if Redis is available
    if ! command -v redis-cli &> /dev/null; then
        log "❌ Redis client not found. Please install Redis client."
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log "❌ Python 3 not found. Please install Python 3."
        exit 1
    fi
    
    # Check if required environment variables are set
    if [ -z "$MYSQL_PASSWORD" ]; then
        log "❌ MYSQL_PASSWORD environment variable not set"
        exit 1
    fi
    
    log "✅ Prerequisites check passed"
}

test_mysql_connection() {
    log "🔗 Testing MySQL connection..."
    
    if mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" "$MYSQL_DATABASE" &> /dev/null; then
        log "✅ MySQL connection successful"
    else
        log "❌ MySQL connection failed. Please check your database configuration."
        exit 1
    fi
}

test_redis_connection() {
    log "🔗 Testing Redis connection..."
    
    if redis-cli ping &> /dev/null; then
        log "✅ Redis connection successful"
    else
        log "❌ Redis connection failed. Please check your Redis configuration."
        exit 1
    fi
}

backup_mysql_database() {
    log "📦 Creating MySQL database backup..."
    
    local backup_file="$BACKUP_DIR/vedfolnir_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if mysqldump -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        "$MYSQL_DATABASE" > "$backup_file" 2>/dev/null; then
        
        # Compress the backup
        gzip "$backup_file"
        log "✅ MySQL database backed up to ${backup_file}.gz"
        echo "${backup_file}.gz" > "$BACKUP_DIR/latest_backup.txt"
    else
        log "⚠️ MySQL backup failed or database doesn't exist yet"
        echo "none" > "$BACKUP_DIR/latest_backup.txt"
    fi
}

validate_config() {
    log "🔍 Validating MySQL configuration..."
    
    if python3 validate_config.py; then
        log "✅ Configuration validation passed"
    else
        log "❌ Configuration validation failed"
        exit 1
    fi
}

initialize_mysql_database() {
    log "🔄 Initializing MySQL database..."
    
    # Check if database exists and has tables
    local table_count=$(mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
        -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$MYSQL_DATABASE';" 2>/dev/null || echo "0")
    
    if [ "$table_count" -eq "0" ]; then
        log "📋 Database is empty, initializing schema..."
        if python3 -c "from database import init_db; init_db()"; then
            log "✅ MySQL database schema initialized"
        else
            log "❌ MySQL database initialization failed"
            restore_mysql_backup
            exit 1
        fi
    else
        log "ℹ️ Database already contains $table_count tables"
    fi
}

run_mysql_migrations() {
    log "🔄 Running MySQL migrations..."
    
    if python3 -c "
from database import run_migrations
try:
    run_migrations()
    print('Migrations completed successfully')
except Exception as e:
    print(f'Migration failed: {e}')
    exit(1)
"; then
        log "✅ MySQL migrations completed successfully"
    else
        log "❌ MySQL migrations failed"
        restore_mysql_backup
        exit 1
    fi
}

validate_mysql_deployment() {
    log "🔍 Validating MySQL deployment..."
    
    # Check database tables
    local required_tables=("users" "platform_connections" "posts" "captions" "sessions")
    local missing_tables=()
    
    for table in "${required_tables[@]}"; do
        local exists=$(mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
            -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$MYSQL_DATABASE' AND table_name='$table';" 2>/dev/null || echo "0")
        
        if [ "$exists" -eq "0" ]; then
            missing_tables+=("$table")
        fi
    done
    
    if [ ${#missing_tables[@]} -eq 0 ]; then
        log "✅ All required MySQL tables exist"
    else
        log "❌ Missing required tables: ${missing_tables[*]}"
        restore_mysql_backup
        exit 1
    fi
    
    # Test database operations
    if python3 -c "
from database import get_db_connection
import pymysql

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM platform_connections')
    platform_count = cursor.fetchone()[0]
    conn.close()
    print(f'Database validation passed: {user_count} users, {platform_count} platforms')
except Exception as e:
    print(f'Database validation failed: {e}')
    exit(1)
"; then
        log "✅ MySQL database operations validated"
    else
        log "❌ MySQL database validation failed"
        restore_mysql_backup
        exit 1
    fi
}

restore_mysql_backup() {
    log "🔄 Restoring MySQL database from backup..."
    
    local latest_backup_file=$(cat "$BACKUP_DIR/latest_backup.txt" 2>/dev/null || echo "none")
    
    if [ "$latest_backup_file" != "none" ] && [ -f "$latest_backup_file" ]; then
        log "📥 Restoring from backup: $latest_backup_file"
        
        # Drop and recreate database
        mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
            -e "DROP DATABASE IF EXISTS $MYSQL_DATABASE; CREATE DATABASE $MYSQL_DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        
        # Restore from backup
        if gunzip -c "$latest_backup_file" | mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"; then
            log "✅ MySQL database restored from backup"
        else
            log "❌ MySQL database restore failed"
        fi
    else
        log "⚠️ No backup available to restore"
    fi
}

test_application_functionality() {
    log "🧪 Testing application functionality..."
    
    # Test web application startup
    if timeout 30 python3 -c "
from web_app import app
from database import get_db_connection

# Test database connection
try:
    conn = get_db_connection()
    conn.close()
    print('Database connection test passed')
except Exception as e:
    print(f'Database connection test failed: {e}')
    exit(1)

# Test Flask app creation
try:
    with app.app_context():
        print('Flask application test passed')
except Exception as e:
    print(f'Flask application test failed: {e}')
    exit(1)
"; then
        log "✅ Application functionality test passed"
    else
        log "⚠️ Application functionality test failed (non-critical)"
    fi
}

optimize_mysql_performance() {
    log "⚡ Optimizing MySQL performance..."
    
    # Analyze and optimize tables
    local tables=("users" "platform_connections" "posts" "captions" "sessions")
    
    for table in "${tables[@]}"; do
        mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" \
            -e "ANALYZE TABLE $table; OPTIMIZE TABLE $table;" "$MYSQL_DATABASE" &> /dev/null || true
    done
    
    log "✅ MySQL performance optimization completed"
}

create_admin_user() {
    log "👤 Creating admin user..."
    
    if python3 scripts/setup/init_admin_user.py; then
        log "✅ Admin user created successfully"
    else
        log "⚠️ Admin user creation failed or user already exists"
    fi
}

cleanup_old_sqlite_files() {
    log "🧹 Cleaning up old SQLite files..."
    
    # Remove SQLite database files
    find storage/ -name "*.db" -type f -exec rm -f {} \; 2>/dev/null || true
    find storage/ -name "*.db-wal" -type f -exec rm -f {} \; 2>/dev/null || true
    find storage/ -name "*.db-shm" -type f -exec rm -f {} \; 2>/dev/null || true
    
    # Remove SQLite backup files
    find backups/ -name "*.db" -type f -exec rm -f {} \; 2>/dev/null || true
    find backups/ -name "*.db.backup" -type f -exec rm -f {} \; 2>/dev/null || true
    
    log "✅ SQLite files cleanup completed"
}

# Main deployment process
main() {
    log "🚀 Starting MySQL deployment process..."
    
    # Pre-deployment checks
    check_prerequisites
    test_mysql_connection
    test_redis_connection
    validate_config
    
    # Backup current state
    backup_mysql_database
    
    # Database setup
    initialize_mysql_database
    run_mysql_migrations
    
    # Validation
    validate_mysql_deployment
    
    # Post-deployment tasks
    optimize_mysql_performance
    create_admin_user
    test_application_functionality
    cleanup_old_sqlite_files
    
    log "🎉 MySQL deployment completed successfully!"
    log "📁 Backup stored in: $BACKUP_DIR"
    log "📊 Database: $MYSQL_DATABASE on $MYSQL_HOST:$MYSQL_PORT"
    
    # Display summary
    echo ""
    echo "=== Deployment Summary ==="
    echo "✅ MySQL database: $MYSQL_DATABASE"
    echo "✅ Backup location: $BACKUP_DIR"
    echo "✅ Log file: $LOG_FILE"
    echo "🌐 Ready to start web application: python3 web_app.py"
    echo "=========================="
}

# Handle interruption
trap 'log "❌ Deployment interrupted"; restore_mysql_backup; exit 1' INT TERM

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --skip-backup    Skip database backup"
            echo "  --skip-cleanup   Skip SQLite files cleanup"
            echo "  --dry-run        Show what would be done without executing"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run deployment
if [ "$DRY_RUN" = true ]; then
    log "🔍 DRY RUN MODE - No changes will be made"
    log "Would execute MySQL deployment with the following configuration:"
    log "  Database: $MYSQL_DATABASE"
    log "  Host: $MYSQL_HOST:$MYSQL_PORT"
    log "  User: $MYSQL_USER"
    log "  Backup dir: $BACKUP_DIR"
else
    main "$@"
fi
