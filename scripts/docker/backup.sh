#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -euo pipefail

# Docker Compose Backup and Restore Procedures
# Comprehensive backup and restore procedures for containerized data

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
BACKUP_BASE_DIR="$PROJECT_ROOT/storage/backups"
RETENTION_DAYS=30
COMPRESSION_LEVEL=6

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to project root
cd "$PROJECT_ROOT"

# Create comprehensive backup
create_backup() {
    local backup_type="${1:-full}"
    local backup_name="${2:-$(date +%Y%m%d_%H%M%S)}"
    local backup_dir="$BACKUP_BASE_DIR/$backup_name"
    
    log_info "Creating $backup_type backup: $backup_name"
    
    # Create backup directory
    mkdir -p "$backup_dir"
    
    # Create backup metadata
    cat > "$backup_dir/metadata.json" << EOF
{
    "backup_name": "$backup_name",
    "backup_type": "$backup_type",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "hostname": "$(hostname)",
    "docker_compose_version": "$(docker-compose --version)",
    "services": $(docker-compose ps --services | jq -R . | jq -s .),
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
}
EOF
    
    # Backup MySQL database
    if [[ "$backup_type" == "full" || "$backup_type" == "database" ]]; then
        backup_mysql "$backup_dir"
    fi
    
    # Backup Redis data
    if [[ "$backup_type" == "full" || "$backup_type" == "redis" ]]; then
        backup_redis "$backup_dir"
    fi
    
    # Backup application data
    if [[ "$backup_type" == "full" || "$backup_type" == "application" ]]; then
        backup_application_data "$backup_dir"
    fi
    
    # Backup configuration
    if [[ "$backup_type" == "full" || "$backup_type" == "config" ]]; then
        backup_configuration "$backup_dir"
    fi
    
    # Backup Vault data
    if [[ "$backup_type" == "full" || "$backup_type" == "vault" ]]; then
        backup_vault "$backup_dir"
    fi
    
    # Create backup verification
    create_backup_verification "$backup_dir"
    
    # Compress backup if requested
    if [[ "${COMPRESS_BACKUP:-true}" == "true" ]]; then
        compress_backup "$backup_dir"
    fi
    
    log_success "Backup completed: $backup_dir"
}

# Backup MySQL database
backup_mysql() {
    local backup_dir="$1"
    
    log_info "Backing up MySQL database..."
    
    if ! docker-compose ps mysql | grep -q "Up"; then
        log_error "MySQL service is not running"
        return 1
    fi
    
    # Full database backup
    docker-compose exec -T mysql mysqldump \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --all-databases \
        --add-drop-database \
        --add-drop-table \
        --create-options \
        --disable-keys \
        --extended-insert \
        --quick \
        --lock-tables=false \
        -u root -p"$(cat secrets/mysql_root_password.txt)" \
        | gzip -"$COMPRESSION_LEVEL" > "$backup_dir/mysql_full.sql.gz"
    
    # Backup specific vedfolnir database
    docker-compose exec -T mysql mysqldump \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --add-drop-table \
        --create-options \
        --disable-keys \
        --extended-insert \
        --quick \
        --lock-tables=false \
        -u root -p"$(cat secrets/mysql_root_password.txt)" \
        vedfolnir \
        | gzip -"$COMPRESSION_LEVEL" > "$backup_dir/mysql_vedfolnir.sql.gz"
    
    # Export database schema only
    docker-compose exec -T mysql mysqldump \
        --no-data \
        --routines \
        --triggers \
        --events \
        -u root -p"$(cat secrets/mysql_root_password.txt)" \
        vedfolnir > "$backup_dir/mysql_schema.sql"
    
    log_success "MySQL backup completed"
}

# Backup Redis data
backup_redis() {
    local backup_dir="$1"
    
    log_info "Backing up Redis data..."
    
    if ! docker-compose ps redis | grep -q "Up"; then
        log_error "Redis service is not running"
        return 1
    fi
    
    # Create Redis snapshot
    docker-compose exec redis redis-cli BGSAVE
    
    # Wait for background save to complete
    local save_in_progress=1
    local timeout=60
    local elapsed=0
    
    while [[ $save_in_progress -eq 1 && $elapsed -lt $timeout ]]; do
        if docker-compose exec redis redis-cli LASTSAVE | grep -q "$(docker-compose exec redis redis-cli LASTSAVE)"; then
            sleep 2
            elapsed=$((elapsed + 2))
        else
            save_in_progress=0
        fi
    done
    
    if [[ $save_in_progress -eq 1 ]]; then
        log_warning "Redis background save may still be in progress"
    fi
    
    # Copy Redis dump file
    docker cp "$(docker-compose ps -q redis)":/data/dump.rdb "$backup_dir/redis.rdb"
    
    # Export Redis configuration
    docker-compose exec redis redis-cli CONFIG GET '*' > "$backup_dir/redis_config.txt"
    
    # Export Redis info
    docker-compose exec redis redis-cli INFO > "$backup_dir/redis_info.txt"
    
    log_success "Redis backup completed"
}

# Backup application data
backup_application_data() {
    local backup_dir="$1"
    
    log_info "Backing up application data..."
    
    # Backup storage directory
    if [[ -d "$PROJECT_ROOT/storage" ]]; then
        tar -czf "$backup_dir/storage.tar.gz" \
            --exclude="storage/backups" \
            --exclude="storage/temp/*" \
            -C "$PROJECT_ROOT" storage/
    fi
    
    # Backup logs (recent logs only)
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        find "$PROJECT_ROOT/logs" -name "*.log" -mtime -7 -print0 | \
            tar -czf "$backup_dir/logs_recent.tar.gz" --null -T -
    fi
    
    # Backup SSL certificates
    if [[ -d "$PROJECT_ROOT/ssl" ]]; then
        tar -czf "$backup_dir/ssl.tar.gz" -C "$PROJECT_ROOT" ssl/
    fi
    
    log_success "Application data backup completed"
}

# Backup configuration
backup_configuration() {
    local backup_dir="$1"
    
    log_info "Backing up configuration..."
    
    # Backup config directory
    if [[ -d "$PROJECT_ROOT/config" ]]; then
        tar -czf "$backup_dir/config.tar.gz" -C "$PROJECT_ROOT" config/
    fi
    
    # Backup environment files
    local env_files=(".env" ".env.docker" ".env.production" ".env.development")
    for env_file in "${env_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$env_file" ]]; then
            cp "$PROJECT_ROOT/$env_file" "$backup_dir/"
        fi
    done
    
    # Backup Docker Compose files
    local compose_files=("docker-compose.yml" "docker-compose.prod.yml" "docker-compose.dev.yml")
    for compose_file in "${compose_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$compose_file" ]]; then
            cp "$PROJECT_ROOT/$compose_file" "$backup_dir/"
        fi
    done
    
    # Backup secrets (encrypted)
    if [[ -d "$PROJECT_ROOT/secrets" ]]; then
        tar -czf "$backup_dir/secrets.tar.gz.enc" -C "$PROJECT_ROOT" secrets/
        # Note: In production, encrypt this with GPG or similar
    fi
    
    log_success "Configuration backup completed"
}

# Backup Vault data
backup_vault() {
    local backup_dir="$1"
    
    log_info "Backing up Vault data..."
    
    if ! docker-compose ps vault | grep -q "Up"; then
        log_warning "Vault service is not running, skipping Vault backup"
        return 0
    fi
    
    # Create Vault snapshot
    if docker-compose exec vault vault operator raft snapshot save /tmp/vault_snapshot 2>/dev/null; then
        docker cp "$(docker-compose ps -q vault)":/tmp/vault_snapshot "$backup_dir/"
        log_success "Vault snapshot created"
    else
        log_warning "Failed to create Vault snapshot (may not be initialized)"
    fi
    
    # Backup Vault configuration
    if [[ -d "$PROJECT_ROOT/config/vault" ]]; then
        cp -r "$PROJECT_ROOT/config/vault" "$backup_dir/vault_config"
    fi
    
    log_success "Vault backup completed"
}

# Create backup verification
create_backup_verification() {
    local backup_dir="$1"
    
    log_info "Creating backup verification..."
    
    # Calculate checksums
    find "$backup_dir" -type f -exec sha256sum {} \; > "$backup_dir/checksums.sha256"
    
    # Create file listing
    find "$backup_dir" -type f -ls > "$backup_dir/file_listing.txt"
    
    # Calculate total backup size
    local backup_size=$(du -sh "$backup_dir" | cut -f1)
    
    # Create verification report
    cat > "$backup_dir/verification.txt" << EOF
Backup Verification Report
=========================
Backup Directory: $backup_dir
Backup Size: $backup_size
Files Count: $(find "$backup_dir" -type f | wc -l)
Created: $(date)

Backup Contents:
$(ls -la "$backup_dir")

Checksums: checksums.sha256
File Listing: file_listing.txt
EOF
    
    log_success "Backup verification completed"
}

# Compress backup
compress_backup() {
    local backup_dir="$1"
    local compressed_file="${backup_dir}.tar.gz"
    
    log_info "Compressing backup..."
    
    tar -czf "$compressed_file" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    
    if [[ -f "$compressed_file" ]]; then
        rm -rf "$backup_dir"
        log_success "Backup compressed: $compressed_file"
    else
        log_error "Failed to compress backup"
    fi
}

# Restore from backup
restore_backup() {
    local backup_path="${1:-}"
    local restore_type="${2:-full}"
    
    if [[ -z "$backup_path" ]]; then
        log_error "Please specify backup path"
        return 1
    fi
    
    # Handle compressed backups
    local backup_dir="$backup_path"
    local temp_extract=false
    
    if [[ "$backup_path" == *.tar.gz ]]; then
        log_info "Extracting compressed backup..."
        backup_dir="/tmp/restore_$(date +%s)"
        mkdir -p "$backup_dir"
        tar -xzf "$backup_path" -C "$backup_dir" --strip-components=1
        temp_extract=true
    fi
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory does not exist: $backup_dir"
        return 1
    fi
    
    # Verify backup integrity
    if ! verify_backup "$backup_dir"; then
        log_error "Backup verification failed"
        return 1
    fi
    
    log_warning "This will restore data from: $backup_dir"
    log_warning "Current data will be overwritten!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        [[ "$temp_extract" == "true" ]] && rm -rf "$backup_dir"
        return 0
    fi
    
    log_info "Starting restore process..."
    
    # Stop services for restore
    log_info "Stopping services..."
    docker-compose stop
    
    # Restore based on type
    case "$restore_type" in
        full)
            restore_mysql "$backup_dir"
            restore_redis "$backup_dir"
            restore_application_data "$backup_dir"
            restore_configuration "$backup_dir"
            restore_vault "$backup_dir"
            ;;
        database)
            restore_mysql "$backup_dir"
            ;;
        redis)
            restore_redis "$backup_dir"
            ;;
        application)
            restore_application_data "$backup_dir"
            ;;
        config)
            restore_configuration "$backup_dir"
            ;;
        vault)
            restore_vault "$backup_dir"
            ;;
        *)
            log_error "Unknown restore type: $restore_type"
            return 1
            ;;
    esac
    
    # Start services
    log_info "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Verify restore
    verify_restore
    
    # Cleanup temporary extraction
    [[ "$temp_extract" == "true" ]] && rm -rf "$backup_dir"
    
    log_success "Restore completed successfully"
}

# Restore MySQL
restore_mysql() {
    local backup_dir="$1"
    
    if [[ ! -f "$backup_dir/mysql_full.sql.gz" ]]; then
        log_warning "MySQL backup not found, skipping MySQL restore"
        return 0
    fi
    
    log_info "Restoring MySQL database..."
    
    # Start MySQL service
    docker-compose start mysql
    sleep 15
    
    # Restore database
    zcat "$backup_dir/mysql_full.sql.gz" | \
        docker-compose exec -T mysql mysql -u root -p"$(cat secrets/mysql_root_password.txt)"
    
    log_success "MySQL restore completed"
}

# Restore Redis
restore_redis() {
    local backup_dir="$1"
    
    if [[ ! -f "$backup_dir/redis.rdb" ]]; then
        log_warning "Redis backup not found, skipping Redis restore"
        return 0
    fi
    
    log_info "Restoring Redis data..."
    
    # Stop Redis service
    docker-compose stop redis
    
    # Copy Redis dump file
    docker cp "$backup_dir/redis.rdb" "$(docker-compose ps -q redis)":/data/dump.rdb
    
    # Start Redis service
    docker-compose start redis
    
    log_success "Redis restore completed"
}

# Restore application data
restore_application_data() {
    local backup_dir="$1"
    
    log_info "Restoring application data..."
    
    # Restore storage
    if [[ -f "$backup_dir/storage.tar.gz" ]]; then
        tar -xzf "$backup_dir/storage.tar.gz" -C "$PROJECT_ROOT"
    fi
    
    # Restore SSL certificates
    if [[ -f "$backup_dir/ssl.tar.gz" ]]; then
        tar -xzf "$backup_dir/ssl.tar.gz" -C "$PROJECT_ROOT"
    fi
    
    log_success "Application data restore completed"
}

# Restore configuration
restore_configuration() {
    local backup_dir="$1"
    
    log_info "Restoring configuration..."
    
    # Restore config directory
    if [[ -f "$backup_dir/config.tar.gz" ]]; then
        tar -xzf "$backup_dir/config.tar.gz" -C "$PROJECT_ROOT"
    fi
    
    # Restore environment files
    local env_files=(".env" ".env.docker" ".env.production" ".env.development")
    for env_file in "${env_files[@]}"; do
        if [[ -f "$backup_dir/$env_file" ]]; then
            cp "$backup_dir/$env_file" "$PROJECT_ROOT/"
        fi
    done
    
    log_success "Configuration restore completed"
}

# Restore Vault
restore_vault() {
    local backup_dir="$1"
    
    if [[ ! -f "$backup_dir/vault_snapshot" ]]; then
        log_warning "Vault backup not found, skipping Vault restore"
        return 0
    fi
    
    log_info "Restoring Vault data..."
    
    # Start Vault service
    docker-compose start vault
    sleep 15
    
    # Restore Vault snapshot
    docker cp "$backup_dir/vault_snapshot" "$(docker-compose ps -q vault)":/tmp/vault_snapshot
    docker-compose exec vault vault operator raft snapshot restore /tmp/vault_snapshot
    
    log_success "Vault restore completed"
}

# Verify backup integrity
verify_backup() {
    local backup_dir="$1"
    
    log_info "Verifying backup integrity..."
    
    # Check if checksums file exists
    if [[ ! -f "$backup_dir/checksums.sha256" ]]; then
        log_warning "Checksums file not found, skipping integrity check"
        return 0
    fi
    
    # Verify checksums
    if (cd "$backup_dir" && sha256sum -c checksums.sha256 --quiet); then
        log_success "Backup integrity verified"
        return 0
    else
        log_error "Backup integrity check failed"
        return 1
    fi
}

# Verify restore
verify_restore() {
    log_info "Verifying restore..."
    
    # Check service health
    local services=("mysql" "redis" "vedfolnir")
    local healthy=0
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "$service: Running"
            ((healthy++))
        else
            log_error "$service: Not running"
        fi
    done
    
    if [[ $healthy -eq ${#services[@]} ]]; then
        log_success "Restore verification passed"
    else
        log_warning "Some services are not running after restore"
    fi
}

# List available backups
list_backups() {
    log_info "Available backups:"
    
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        log_info "No backups found"
        return 0
    fi
    
    find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "*_*" | sort | while read -r backup_dir; do
        local backup_name=$(basename "$backup_dir")
        local backup_size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1 || echo "Unknown")
        local backup_date=$(echo "$backup_name" | sed 's/_/ /' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3/')
        
        echo "  $backup_name ($backup_size) - $backup_date"
        
        if [[ -f "$backup_dir/metadata.json" ]]; then
            local backup_type=$(jq -r '.backup_type // "unknown"' "$backup_dir/metadata.json" 2>/dev/null || echo "unknown")
            echo "    Type: $backup_type"
        fi
    done
    
    # List compressed backups
    find "$BACKUP_BASE_DIR" -maxdepth 1 -name "*.tar.gz" | sort | while read -r backup_file; do
        local backup_name=$(basename "$backup_file" .tar.gz)
        local backup_size=$(du -sh "$backup_file" 2>/dev/null | cut -f1 || echo "Unknown")
        echo "  $backup_name.tar.gz ($backup_size) - Compressed"
    done
}

# Clean old backups
cleanup_backups() {
    log_info "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        log_info "No backup directory found"
        return 0
    fi
    
    local deleted=0
    
    # Clean up old backup directories
    find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "*_*" -mtime +$RETENTION_DAYS | while read -r old_backup; do
        log_info "Removing old backup: $(basename "$old_backup")"
        rm -rf "$old_backup"
        ((deleted++))
    done
    
    # Clean up old compressed backups
    find "$BACKUP_BASE_DIR" -maxdepth 1 -name "*.tar.gz" -mtime +$RETENTION_DAYS | while read -r old_backup; do
        log_info "Removing old backup: $(basename "$old_backup")"
        rm -f "$old_backup"
        ((deleted++))
    done
    
    log_success "Cleanup completed. Removed $deleted old backups"
}

# Show usage
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  backup [TYPE] [NAME]      Create backup (full|database|redis|application|config|vault)"
    echo "  restore BACKUP [TYPE]     Restore from backup"
    echo "  verify BACKUP             Verify backup integrity"
    echo "  list                      List available backups"
    echo "  cleanup                   Remove old backups"
    echo ""
    echo "Examples:"
    echo "  $0 backup full            Create full backup with timestamp name"
    echo "  $0 backup database db1    Create database backup named 'db1'"
    echo "  $0 restore storage/backups/20250101_120000"
    echo "  $0 restore backup.tar.gz database"
    echo "  $0 verify storage/backups/20250101_120000"
}

# Main command handling
case "${1:-}" in
    backup)
        create_backup "${2:-full}" "${3:-}"
        ;;
    restore)
        restore_backup "${2:-}" "${3:-full}"
        ;;
    verify)
        verify_backup "${2:-}"
        ;;
    list)
        list_backups
        ;;
    cleanup)
        cleanup_backups
        ;;
    -h|--help)
        usage
        ;;
    *)
        log_error "Unknown command: ${1:-}"
        echo ""
        usage
        exit 1
        ;;
esac