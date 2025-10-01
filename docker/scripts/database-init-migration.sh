#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Database initialization and migration handling for Docker containers
# Handles database setup, schema creation, and data migration

set -e

# Configuration
DB_INIT_TIMEOUT=${DB_INIT_TIMEOUT:-120}
DB_MIGRATION_TIMEOUT=${DB_MIGRATION_TIMEOUT:-300}
BACKUP_DIR=${DB_BACKUP_DIR:-"/app/storage/backups/mysql"}
VERBOSE=${DB_INIT_VERBOSE:-true}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    fi
}

error_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}ERROR:${NC} $1" >&2
}

success_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}SUCCESS:${NC} $1"
}

warning_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING:${NC} $1"
}

info_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${BLUE}INFO:${NC} $1"
}

# Wait for MySQL to be ready
wait_for_mysql() {
    info_log "Waiting for MySQL to be ready..."
    
    local start_time=$(date +%s)
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $DB_INIT_TIMEOUT ]; then
            error_log "MySQL readiness check timed out after ${DB_INIT_TIMEOUT}s"
            return 1
        fi
        
        if mysqladmin ping -h mysql -u root -p"$(cat /run/secrets/mysql_root_password)" --silent 2>/dev/null; then
            success_log "MySQL is ready (took ${elapsed}s)"
            return 0
        fi
        
        log "Waiting for MySQL... (${elapsed}s elapsed)"
        sleep 5
    done
}

# Check if database exists
database_exists() {
    local db_name="$1"
    mysql -h mysql -u root -p"$(cat /run/secrets/mysql_root_password)" -e "USE $db_name;" >/dev/null 2>&1
}

# Check if database has tables
database_has_tables() {
    local db_name="$1"
    local table_count=$(mysql -h mysql -u root -p"$(cat /run/secrets/mysql_root_password)" -e "USE $db_name; SHOW TABLES;" 2>/dev/null | wc -l)
    [ "$table_count" -gt 1 ]  # More than 1 line (header + tables)
}

# Create database if it doesn't exist
create_database() {
    local db_name="$1"
    local db_user="$2"
    local db_password="$3"
    
    info_log "Creating database: $db_name"
    
    mysql -h mysql -u root -p"$(cat /run/secrets/mysql_root_password)" <<EOF
CREATE DATABASE IF NOT EXISTS $db_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$db_user'@'%' IDENTIFIED BY '$db_password';
GRANT ALL PRIVILEGES ON $db_name.* TO '$db_user'@'%';
FLUSH PRIVILEGES;
EOF
    
    if [ $? -eq 0 ]; then
        success_log "Database $db_name created successfully"
        return 0
    else
        error_log "Failed to create database $db_name"
        return 1
    fi
}

# Initialize database schema using Python application
initialize_database_schema() {
    info_log "Initializing database schema..."
    
    python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from config import Config
    from app.core.database.core.database_manager import DatabaseManager
    from models import Base
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Create all tables
    engine = db_manager.get_engine()
    Base.metadata.create_all(engine)
    
    print('Database schema initialized successfully')
    sys.exit(0)
except Exception as e:
    print(f'Database schema initialization failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        success_log "Database schema initialized"
        return 0
    else
        error_log "Database schema initialization failed"
        return 1
    fi
}

# Run database migrations
run_database_migrations() {
    info_log "Running database migrations..."
    
    # Check if Alembic is available
    if [ -f "/app/alembic.ini" ]; then
        info_log "Running Alembic migrations..."
        
        cd /app
        python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config('/app/alembic.ini')
    command.upgrade(alembic_cfg, 'head')
    
    print('Alembic migrations completed successfully')
    sys.exit(0)
except Exception as e:
    print(f'Alembic migrations failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
        
        if [ $? -eq 0 ]; then
            success_log "Database migrations completed"
            return 0
        else
            error_log "Database migrations failed"
            return 1
        fi
    else
        warning_log "Alembic configuration not found, skipping migrations"
        return 0
    fi
}

# Create initial admin user if needed
create_initial_admin() {
    info_log "Checking for initial admin user..."
    
    python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from config import Config
    from app.core.database.core.database_manager import DatabaseManager
    from models import User, UserRole
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        # Check if any admin users exist
        admin_count = session.query(User).filter_by(role=UserRole.ADMIN).count()
        
        if admin_count == 0:
            print('No admin users found, creating initial admin user')
            
            # Create initial admin user
            from werkzeug.security import generate_password_hash
            import secrets
            
            admin_password = os.getenv('INITIAL_ADMIN_PASSWORD', secrets.token_urlsafe(16))
            
            admin_user = User(
                username='admin',
                email='admin@localhost',
                password_hash=generate_password_hash(admin_password),
                role=UserRole.ADMIN,
                is_active=True
            )
            
            session.add(admin_user)
            session.commit()
            
            print(f'Initial admin user created: admin / {admin_password}')
            print('IMPORTANT: Change the admin password after first login!')
            
            # Save password to file for reference
            with open('/app/logs/initial_admin_password.txt', 'w') as f:
                f.write(f'Username: admin\\nPassword: {admin_password}\\n')
            
            sys.exit(0)
        else:
            print(f'Found {admin_count} admin users, skipping initial admin creation')
            sys.exit(0)
            
except Exception as e:
    print(f'Initial admin user creation failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        success_log "Initial admin user check completed"
        return 0
    else
        error_log "Initial admin user creation failed"
        return 1
    fi
}

# Backup database before major operations
backup_database() {
    local backup_name="$1"
    local db_name="${2:-vedfolnir}"
    
    info_log "Creating database backup: $backup_name"
    
    # Ensure backup directory exists
    mkdir -p "$BACKUP_DIR"
    
    local backup_file="$BACKUP_DIR/${backup_name}_$(date +%Y%m%d_%H%M%S).sql"
    
    if mysqldump -h mysql -u root -p"$(cat /run/secrets/mysql_root_password)" \
        --single-transaction \
        --routines \
        --triggers \
        "$db_name" > "$backup_file" 2>/dev/null; then
        
        # Compress backup
        gzip "$backup_file"
        success_log "Database backup created: ${backup_file}.gz"
        return 0
    else
        error_log "Database backup failed"
        return 1
    fi
}

# Restore database from backup
restore_database() {
    local backup_file="$1"
    local db_name="${2:-vedfolnir}"
    
    info_log "Restoring database from backup: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        error_log "Backup file not found: $backup_file"
        return 1
    fi
    
    # Decompress if needed
    local restore_file="$backup_file"
    if [[ "$backup_file" == *.gz ]]; then
        restore_file="${backup_file%.gz}"
        gunzip -c "$backup_file" > "$restore_file"
    fi
    
    if mysql -h mysql -u root -p"$(cat /run/secrets/mysql_root_password)" "$db_name" < "$restore_file" 2>/dev/null; then
        success_log "Database restored successfully"
        
        # Clean up temporary file
        if [[ "$backup_file" == *.gz ]]; then
            rm -f "$restore_file"
        fi
        
        return 0
    else
        error_log "Database restore failed"
        return 1
    fi
}

# Validate database integrity
validate_database() {
    info_log "Validating database integrity..."
    
    python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from config import Config
    from app.core.database.core.database_manager import DatabaseManager
    from models import User, PlatformConnection, Post, Image
    from sqlalchemy import text
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        # Check core tables exist and are accessible
        tables_to_check = ['users', 'platform_connections', 'posts', 'images']
        
        for table in tables_to_check:
            try:
                result = session.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
                print(f'Table {table}: {result} records')
            except Exception as e:
                print(f'Table {table}: ERROR - {e}')
                sys.exit(1)
        
        # Check foreign key constraints
        session.execute(text('SET FOREIGN_KEY_CHECKS=1'))
        
        print('Database integrity validation passed')
        sys.exit(0)
        
except Exception as e:
    print(f'Database validation failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        success_log "Database integrity validation passed"
        return 0
    else
        error_log "Database integrity validation failed"
        return 1
    fi
}

# Main initialization function
main() {
    local action="${1:-init}"
    
    echo -e "${BLUE}=== Database Initialization and Migration Manager ===${NC}"
    echo "Action: $action"
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    
    case "$action" in
        "init")
            # Full initialization process
            wait_for_mysql || exit 1
            
            if ! database_exists "vedfolnir"; then
                create_database "vedfolnir" "vedfolnir" "$(cat /run/secrets/mysql_password)" || exit 1
            else
                info_log "Database 'vedfolnir' already exists"
            fi
            
            if ! database_has_tables "vedfolnir"; then
                initialize_database_schema || exit 1
            else
                info_log "Database schema already exists"
            fi
            
            run_database_migrations || exit 1
            create_initial_admin || exit 1
            validate_database || exit 1
            
            success_log "Database initialization completed successfully"
            ;;
            
        "migrate")
            # Run migrations only
            wait_for_mysql || exit 1
            run_database_migrations || exit 1
            validate_database || exit 1
            ;;
            
        "backup")
            # Create backup
            local backup_name="${2:-manual_backup}"
            wait_for_mysql || exit 1
            backup_database "$backup_name" || exit 1
            ;;
            
        "restore")
            # Restore from backup
            local backup_file="$2"
            if [ -z "$backup_file" ]; then
                error_log "Backup file path required for restore"
                exit 1
            fi
            wait_for_mysql || exit 1
            restore_database "$backup_file" || exit 1
            validate_database || exit 1
            ;;
            
        "validate")
            # Validate database only
            wait_for_mysql || exit 1
            validate_database || exit 1
            ;;
            
        "reset")
            # Reset database (dangerous!)
            warning_log "Database reset requested - this will destroy all data!"
            read -p "Are you sure? Type 'yes' to confirm: " confirm
            if [ "$confirm" = "yes" ]; then
                wait_for_mysql || exit 1
                backup_database "pre_reset_backup" || exit 1
                
                mysql -h mysql -u root -p"$(cat /run/secrets/mysql_root_password)" -e "DROP DATABASE IF EXISTS vedfolnir;" || exit 1
                create_database "vedfolnir" "vedfolnir" "$(cat /run/secrets/mysql_password)" || exit 1
                initialize_database_schema || exit 1
                create_initial_admin || exit 1
                
                success_log "Database reset completed"
            else
                info_log "Database reset cancelled"
            fi
            ;;
            
        *)
            echo "Usage: $0 {init|migrate|backup [name]|restore <file>|validate|reset}"
            echo ""
            echo "Actions:"
            echo "  init     - Full database initialization (default)"
            echo "  migrate  - Run database migrations only"
            echo "  backup   - Create database backup"
            echo "  restore  - Restore from backup file"
            echo "  validate - Validate database integrity"
            echo "  reset    - Reset database (destroys all data!)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"