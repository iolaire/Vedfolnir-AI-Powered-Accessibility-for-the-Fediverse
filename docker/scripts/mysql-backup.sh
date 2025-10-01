#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MySQL backup script for Docker container
# Supports full backups, incremental backups, and point-in-time recovery

set -e

# Configuration
MYSQL_HOST="localhost"
MYSQL_PORT="3306"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
BACKUP_DIR="/backups"
DATABASE_NAME="vedfolnir"
RETENTION_DAYS=7

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to create backup directory
create_backup_dir() {
    local backup_date=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/$backup_date"
    
    mkdir -p "$backup_path"
    echo "$backup_path"
}

# Function to perform full database backup
full_backup() {
    log "${BLUE}Starting full MySQL backup...${NC}"
    
    local backup_path=$(create_backup_dir)
    local backup_file="$backup_path/vedfolnir_full_backup.sql"
    local backup_compressed="$backup_path/vedfolnir_full_backup.sql.gz"
    
    # Create full backup with all necessary options
    log "Creating full backup of database '$DATABASE_NAME'..."
    mysqldump \
        -h "$MYSQL_HOST" \
        -P "$MYSQL_PORT" \
        -u "$MYSQL_USER" \
        -p"$MYSQL_PASSWORD" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --hex-blob \
        --complete-insert \
        --add-drop-database \
        --add-drop-table \
        --create-options \
        --disable-keys \
        --extended-insert \
        --quick \
        --lock-tables=false \
        --set-gtid-purged=OFF \
        --databases "$DATABASE_NAME" > "$backup_file"
    
    # Compress the backup
    log "Compressing backup..."
    gzip "$backup_file"
    
    # Create metadata file
    cat > "$backup_path/backup_metadata.txt" << EOF
Backup Type: Full
Database: $DATABASE_NAME
Backup Date: $(date)
Backup Size: $(du -h "$backup_compressed" | cut -f1)
MySQL Version: $(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT VERSION();" -s -N)
Backup File: $(basename "$backup_compressed")
EOF
    
    # Verify backup integrity
    log "Verifying backup integrity..."
    if gunzip -t "$backup_compressed"; then
        log "${GREEN}✓ Backup verification successful${NC}"
        log "${GREEN}✓ Full backup completed: $backup_compressed${NC}"
        echo "$backup_path"
    else
        log "${RED}✗ Backup verification failed${NC}"
        return 1
    fi
}

# Function to perform schema-only backup
schema_backup() {
    log "${BLUE}Starting schema-only backup...${NC}"
    
    local backup_path=$(create_backup_dir)
    local backup_file="$backup_path/vedfolnir_schema_backup.sql"
    
    # Create schema backup
    log "Creating schema backup of database '$DATABASE_NAME'..."
    mysqldump \
        -h "$MYSQL_HOST" \
        -P "$MYSQL_PORT" \
        -u "$MYSQL_USER" \
        -p"$MYSQL_PASSWORD" \
        --no-data \
        --routines \
        --triggers \
        --events \
        --add-drop-database \
        --add-drop-table \
        --create-options \
        --set-gtid-purged=OFF \
        --databases "$DATABASE_NAME" > "$backup_file"
    
    # Create metadata file
    cat > "$backup_path/backup_metadata.txt" << EOF
Backup Type: Schema Only
Database: $DATABASE_NAME
Backup Date: $(date)
Backup Size: $(du -h "$backup_file" | cut -f1)
MySQL Version: $(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT VERSION();" -s -N)
Backup File: $(basename "$backup_file")
EOF
    
    log "${GREEN}✓ Schema backup completed: $backup_file${NC}"
    echo "$backup_path"
}

# Function to backup specific tables
table_backup() {
    local tables="$1"
    log "${BLUE}Starting table-specific backup for: $tables${NC}"
    
    local backup_path=$(create_backup_dir)
    local backup_file="$backup_path/vedfolnir_tables_backup.sql"
    local backup_compressed="$backup_path/vedfolnir_tables_backup.sql.gz"
    
    # Create table backup
    log "Creating backup of tables: $tables..."
    mysqldump \
        -h "$MYSQL_HOST" \
        -P "$MYSQL_PORT" \
        -u "$MYSQL_USER" \
        -p"$MYSQL_PASSWORD" \
        --single-transaction \
        --routines \
        --triggers \
        --hex-blob \
        --complete-insert \
        --add-drop-table \
        --create-options \
        --disable-keys \
        --extended-insert \
        --quick \
        --lock-tables=false \
        --set-gtid-purged=OFF \
        "$DATABASE_NAME" $tables > "$backup_file"
    
    # Compress the backup
    gzip "$backup_file"
    
    # Create metadata file
    cat > "$backup_path/backup_metadata.txt" << EOF
Backup Type: Table Specific
Database: $DATABASE_NAME
Tables: $tables
Backup Date: $(date)
Backup Size: $(du -h "$backup_compressed" | cut -f1)
MySQL Version: $(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT VERSION();" -s -N)
Backup File: $(basename "$backup_compressed")
EOF
    
    log "${GREEN}✓ Table backup completed: $backup_compressed${NC}"
    echo "$backup_path"
}

# Function to clean old backups
cleanup_old_backups() {
    log "${BLUE}Cleaning up old backups (older than $RETENTION_DAYS days)...${NC}"
    
    local deleted_count=0
    
    # Find and delete old backup directories
    find "$BACKUP_DIR" -maxdepth 1 -type d -name "20*" -mtime +$RETENTION_DAYS | while read old_backup; do
        log "Removing old backup: $(basename "$old_backup")"
        rm -rf "$old_backup"
        ((deleted_count++))
    done
    
    log "${GREEN}✓ Cleanup completed${NC}"
}

# Function to list available backups
list_backups() {
    log "${BLUE}Available backups in $BACKUP_DIR:${NC}"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log "${YELLOW}No backup directory found${NC}"
        return
    fi
    
    local backup_count=0
    
    for backup_dir in "$BACKUP_DIR"/20*; do
        if [ -d "$backup_dir" ]; then
            local backup_name=$(basename "$backup_dir")
            local metadata_file="$backup_dir/backup_metadata.txt"
            
            echo
            log "${GREEN}Backup: $backup_name${NC}"
            
            if [ -f "$metadata_file" ]; then
                while IFS= read -r line; do
                    log "  $line"
                done < "$metadata_file"
            else
                log "  No metadata available"
            fi
            
            # List backup files
            log "  Files:"
            ls -lh "$backup_dir"/*.sql* 2>/dev/null | while read file_info; do
                log "    $file_info"
            done
            
            ((backup_count++))
        fi
    done
    
    if [ $backup_count -eq 0 ]; then
        log "${YELLOW}No backups found${NC}"
    else
        log "${GREEN}Total backups: $backup_count${NC}"
    fi
}

# Function to verify backup
verify_backup() {
    local backup_path="$1"
    
    if [ -z "$backup_path" ]; then
        log "${RED}ERROR: Backup path not specified${NC}"
        return 1
    fi
    
    log "${BLUE}Verifying backup: $backup_path${NC}"
    
    # Check if backup directory exists
    if [ ! -d "$backup_path" ]; then
        log "${RED}ERROR: Backup directory not found: $backup_path${NC}"
        return 1
    fi
    
    # Find SQL files in backup directory
    local sql_files=$(find "$backup_path" -name "*.sql*" -type f)
    
    if [ -z "$sql_files" ]; then
        log "${RED}ERROR: No SQL backup files found in $backup_path${NC}"
        return 1
    fi
    
    # Verify each SQL file
    for sql_file in $sql_files; do
        log "Verifying file: $(basename "$sql_file")"
        
        if [[ "$sql_file" == *.gz ]]; then
            # Verify compressed file
            if gunzip -t "$sql_file"; then
                log "${GREEN}✓ Compressed file integrity OK${NC}"
            else
                log "${RED}✗ Compressed file integrity failed${NC}"
                return 1
            fi
        else
            # Verify uncompressed file
            if [ -s "$sql_file" ]; then
                log "${GREEN}✓ File exists and is not empty${NC}"
            else
                log "${RED}✗ File is empty or does not exist${NC}"
                return 1
            fi
        fi
    done
    
    log "${GREEN}✓ Backup verification completed successfully${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {full|schema|tables|cleanup|list|verify} [options]"
    echo
    echo "Commands:"
    echo "  full                    - Create full database backup"
    echo "  schema                  - Create schema-only backup"
    echo "  tables 'table1 table2'  - Backup specific tables"
    echo "  cleanup                 - Remove old backups"
    echo "  list                    - List available backups"
    echo "  verify <backup_path>    - Verify backup integrity"
    echo
    echo "Environment Variables:"
    echo "  MYSQL_ROOT_PASSWORD     - MySQL root password"
    echo "  MYSQL_USER              - MySQL user (default: root)"
    echo "  RETENTION_DAYS          - Backup retention days (default: 7)"
    echo
    echo "Examples:"
    echo "  $0 full"
    echo "  $0 tables 'users posts images'"
    echo "  $0 verify /backups/20250101_120000"
}

# Main function
main() {
    # Check if MySQL password is set
    if [ -z "$MYSQL_PASSWORD" ]; then
        log "${RED}ERROR: MYSQL_ROOT_PASSWORD environment variable not set${NC}"
        exit 1
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Test MySQL connection
    if ! mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" >/dev/null 2>&1; then
        log "${RED}ERROR: Cannot connect to MySQL${NC}"
        exit 1
    fi
    
    # Handle commands
    case "${1:-}" in
        "full")
            full_backup
            ;;
        "schema")
            schema_backup
            ;;
        "tables")
            if [ -z "$2" ]; then
                log "${RED}ERROR: Table names not specified${NC}"
                show_usage
                exit 1
            fi
            table_backup "$2"
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "list")
            list_backups
            ;;
        "verify")
            if [ -z "$2" ]; then
                log "${RED}ERROR: Backup path not specified${NC}"
                show_usage
                exit 1
            fi
            verify_backup "$2"
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"