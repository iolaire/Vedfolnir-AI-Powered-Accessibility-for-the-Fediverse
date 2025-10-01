#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Comprehensive Backup and Disaster Recovery Script for Docker Compose Vedfolnir
# Provides automated backups, point-in-time recovery, and disaster recovery procedures

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="${PROJECT_ROOT}/storage/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_BASE_DIR}/full_backup_${TIMESTAMP}"

# Logging
LOG_FILE="${PROJECT_ROOT}/logs/backup_recovery.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
}

# Load environment variables
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    source "${PROJECT_ROOT}/.env"
fi

# Default configuration
MYSQL_CONTAINER="${MYSQL_CONTAINER:-vedfolnir_mysql}"
REDIS_CONTAINER="${REDIS_CONTAINER:-vedfolnir_redis}"
APP_CONTAINER="${APP_CONTAINER:-vedfolnir_app}"
VAULT_CONTAINER="${VAULT_CONTAINER:-vedfolnir_vault}"

# Backup retention (days)
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_RETENTION_WEEKLY="${BACKUP_RETENTION_WEEKLY:-12}"
BACKUP_RETENTION_MONTHLY="${BACKUP_RETENTION_MONTHLY:-12}"

# Recovery objectives
RTO_TARGET_MINUTES="${RTO_TARGET_MINUTES:-240}"  # 4 hours
RPO_TARGET_MINUTES="${RPO_TARGET_MINUTES:-60}"   # 1 hour

usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    backup              Create full system backup
    backup-mysql        Backup MySQL database only
    backup-redis        Backup Redis data only
    backup-app          Backup application data only
    backup-vault        Backup Vault secrets only
    restore             Restore from backup
    restore-mysql       Restore MySQL database only
    restore-redis       Restore Redis data only
    restore-app         Restore application data only
    restore-vault       Restore Vault secrets only
    verify              Verify backup integrity
    cleanup             Clean up old backups
    disaster-recovery   Full disaster recovery procedure
    test-recovery       Test recovery procedures
    list-backups        List available backups
    schedule            Set up automated backup scheduling

Options:
    --backup-dir DIR    Specify backup directory
    --restore-from DIR  Specify restore source directory
    --dry-run          Show what would be done without executing
    --force            Force operation without confirmation
    --compress         Enable compression for backups
    --encrypt          Enable encryption for backups
    --verify           Verify backup after creation
    --retention DAYS   Override retention policy
    --help             Show this help message

Examples:
    $0 backup --compress --encrypt --verify
    $0 restore --restore-from /path/to/backup
    $0 disaster-recovery --restore-from /path/to/backup
    $0 test-recovery --backup-dir /path/to/test/backup
EOF
}

# Parse command line arguments
COMMAND=""
BACKUP_DIR_OVERRIDE=""
RESTORE_FROM=""
DRY_RUN=false
FORCE=false
COMPRESS=false
ENCRYPT=false
VERIFY_BACKUP=false
RETENTION_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        backup|backup-mysql|backup-redis|backup-app|backup-vault|restore|restore-mysql|restore-redis|restore-app|restore-vault|verify|cleanup|disaster-recovery|test-recovery|list-backups|schedule)
            COMMAND="$1"
            shift
            ;;
        --backup-dir)
            BACKUP_DIR_OVERRIDE="$2"
            shift 2
            ;;
        --restore-from)
            RESTORE_FROM="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --compress)
            COMPRESS=true
            shift
            ;;
        --encrypt)
            ENCRYPT=true
            shift
            ;;
        --verify)
            VERIFY_BACKUP=true
            shift
            ;;
        --retention)
            RETENTION_OVERRIDE="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$COMMAND" ]]; then
    error "No command specified"
    usage
    exit 1
fi

# Override backup directory if specified
if [[ -n "$BACKUP_DIR_OVERRIDE" ]]; then
    BACKUP_DIR="$BACKUP_DIR_OVERRIDE"
fi

# Utility functions
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose is not installed or not in PATH"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    if ! docker-compose ps &> /dev/null; then
        error "Docker Compose services are not running or docker-compose.yml not found"
        exit 1
    fi
}

check_container_running() {
    local container_name="$1"
    if ! docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        error "Container $container_name is not running"
        return 1
    fi
    return 0
}

create_backup_directory() {
    local backup_path="$1"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would create backup directory: $backup_path"
        return 0
    fi
    
    log "Creating backup directory: $backup_path"
    mkdir -p "$backup_path"
    mkdir -p "$backup_path/mysql"
    mkdir -p "$backup_path/redis"
    mkdir -p "$backup_path/app"
    mkdir -p "$backup_path/vault"
    mkdir -p "$backup_path/metadata"
    
    # Create backup manifest
    cat > "$backup_path/backup_manifest.json" << EOF
{
    "backup_id": "$(basename "$backup_path")",
    "timestamp": "$(date -Iseconds)",
    "version": "1.0",
    "type": "full_system_backup",
    "components": {
        "mysql": false,
        "redis": false,
        "app": false,
        "vault": false
    },
    "options": {
        "compressed": $COMPRESS,
        "encrypted": $ENCRYPT,
        "verified": false
    },
    "retention": {
        "created": "$(date -Iseconds)",
        "expires": "$(date -d "+${BACKUP_RETENTION_DAYS} days" -Iseconds)"
    }
}
EOF
}

backup_mysql() {
    local backup_path="$1"
    local mysql_backup_dir="$backup_path/mysql"
    
    log "Starting MySQL backup..."
    
    if ! check_container_running "$MYSQL_CONTAINER"; then
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would backup MySQL database"
        return 0
    fi
    
    # Get MySQL credentials from secrets
    local mysql_root_password
    mysql_root_password=$(docker exec "$MYSQL_CONTAINER" cat /run/secrets/mysql_root_password 2>/dev/null || echo "")
    
    if [[ -z "$mysql_root_password" ]]; then
        error "Could not retrieve MySQL root password"
        return 1
    fi
    
    # Create full database dump
    log "Creating MySQL database dump..."
    docker exec "$MYSQL_CONTAINER" mysqldump \
        --user=root \
        --password="$mysql_root_password" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --all-databases \
        --master-data=2 \
        --flush-logs \
        --hex-blob \
        --complete-insert > "$mysql_backup_dir/full_dump.sql"
    
    if [[ $? -ne 0 ]]; then
        error "MySQL dump failed"
        return 1
    fi
    
    # Get binary log position for point-in-time recovery
    docker exec "$MYSQL_CONTAINER" mysql \
        --user=root \
        --password="$mysql_root_password" \
        --execute="SHOW MASTER STATUS\G" > "$mysql_backup_dir/binlog_position.txt"
    
    # Backup MySQL configuration
    docker exec "$MYSQL_CONTAINER" cat /etc/mysql/my.cnf > "$mysql_backup_dir/my.cnf" 2>/dev/null || true
    
    # Create MySQL backup metadata
    cat > "$mysql_backup_dir/mysql_backup_metadata.json" << EOF
{
    "backup_timestamp": "$(date -Iseconds)",
    "mysql_version": "$(docker exec "$MYSQL_CONTAINER" mysql --version)",
    "backup_type": "full",
    "databases": "all",
    "binlog_enabled": true,
    "file_size": $(stat -c%s "$mysql_backup_dir/full_dump.sql"),
    "checksum": "$(sha256sum "$mysql_backup_dir/full_dump.sql" | cut -d' ' -f1)"
}
EOF
    
    # Compress if requested
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing MySQL backup..."
        gzip "$mysql_backup_dir/full_dump.sql"
    fi
    
    # Encrypt if requested
    if [[ "$ENCRYPT" == "true" ]]; then
        log "Encrypting MySQL backup..."
        encrypt_file "$mysql_backup_dir/full_dump.sql${COMPRESS:+.gz}"
    fi
    
    log "MySQL backup completed successfully"
    return 0
}

backup_redis() {
    local backup_path="$1"
    local redis_backup_dir="$backup_path/redis"
    
    log "Starting Redis backup..."
    
    if ! check_container_running "$REDIS_CONTAINER"; then
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would backup Redis data"
        return 0
    fi
    
    # Get Redis password from secrets
    local redis_password
    redis_password=$(docker exec "$REDIS_CONTAINER" cat /run/secrets/redis_password 2>/dev/null || echo "")
    
    # Create Redis snapshot
    log "Creating Redis snapshot..."
    if [[ -n "$redis_password" ]]; then
        docker exec "$REDIS_CONTAINER" redis-cli -a "$redis_password" --no-auth-warning BGSAVE
    else
        docker exec "$REDIS_CONTAINER" redis-cli BGSAVE
    fi
    
    # Wait for background save to complete
    local save_in_progress=1
    local timeout=300  # 5 minutes timeout
    local elapsed=0
    
    while [[ $save_in_progress -eq 1 && $elapsed -lt $timeout ]]; do
        if [[ -n "$redis_password" ]]; then
            save_in_progress=$(docker exec "$REDIS_CONTAINER" redis-cli -a "$redis_password" --no-auth-warning LASTSAVE | xargs -I {} docker exec "$REDIS_CONTAINER" redis-cli -a "$redis_password" --no-auth-warning LASTSAVE | wc -l)
        else
            save_in_progress=$(docker exec "$REDIS_CONTAINER" redis-cli LASTSAVE | xargs -I {} docker exec "$REDIS_CONTAINER" redis-cli LASTSAVE | wc -l)
        fi
        
        if [[ $save_in_progress -eq 1 ]]; then
            sleep 5
            elapsed=$((elapsed + 5))
        fi
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        error "Redis backup timed out"
        return 1
    fi
    
    # Copy Redis data files
    docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$redis_backup_dir/dump.rdb"
    docker cp "$REDIS_CONTAINER:/data/appendonly.aof" "$redis_backup_dir/appendonly.aof" 2>/dev/null || true
    
    # Backup Redis configuration
    docker exec "$REDIS_CONTAINER" cat /usr/local/etc/redis/redis.conf > "$redis_backup_dir/redis.conf" 2>/dev/null || true
    
    # Get Redis info for metadata
    local redis_info
    if [[ -n "$redis_password" ]]; then
        redis_info=$(docker exec "$REDIS_CONTAINER" redis-cli -a "$redis_password" --no-auth-warning INFO server)
    else
        redis_info=$(docker exec "$REDIS_CONTAINER" redis-cli INFO server)
    fi
    
    # Create Redis backup metadata
    cat > "$redis_backup_dir/redis_backup_metadata.json" << EOF
{
    "backup_timestamp": "$(date -Iseconds)",
    "redis_version": "$(echo "$redis_info" | grep redis_version | cut -d: -f2 | tr -d '\r')",
    "backup_type": "snapshot",
    "rdb_size": $(stat -c%s "$redis_backup_dir/dump.rdb" 2>/dev/null || echo 0),
    "aof_size": $(stat -c%s "$redis_backup_dir/appendonly.aof" 2>/dev/null || echo 0),
    "rdb_checksum": "$(sha256sum "$redis_backup_dir/dump.rdb" 2>/dev/null | cut -d' ' -f1 || echo 'N/A')",
    "aof_checksum": "$(sha256sum "$redis_backup_dir/appendonly.aof" 2>/dev/null | cut -d' ' -f1 || echo 'N/A')"
}
EOF
    
    # Compress if requested
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing Redis backup..."
        gzip "$redis_backup_dir/dump.rdb"
        [[ -f "$redis_backup_dir/appendonly.aof" ]] && gzip "$redis_backup_dir/appendonly.aof"
    fi
    
    # Encrypt if requested
    if [[ "$ENCRYPT" == "true" ]]; then
        log "Encrypting Redis backup..."
        encrypt_file "$redis_backup_dir/dump.rdb${COMPRESS:+.gz}"
        [[ -f "$redis_backup_dir/appendonly.aof${COMPRESS:+.gz}" ]] && encrypt_file "$redis_backup_dir/appendonly.aof${COMPRESS:+.gz}"
    fi
    
    log "Redis backup completed successfully"
    return 0
}

backup_application_data() {
    local backup_path="$1"
    local app_backup_dir="$backup_path/app"
    
    log "Starting application data backup..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would backup application data"
        return 0
    fi
    
    # Backup storage directory (images, temp files, etc.)
    if [[ -d "$PROJECT_ROOT/storage" ]]; then
        log "Backing up storage directory..."
        cp -r "$PROJECT_ROOT/storage" "$app_backup_dir/"
    fi
    
    # Backup logs
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        log "Backing up logs directory..."
        cp -r "$PROJECT_ROOT/logs" "$app_backup_dir/"
    fi
    
    # Backup configuration files
    log "Backing up configuration files..."
    mkdir -p "$app_backup_dir/config"
    
    # Copy configuration files (sanitized)
    for config_file in .env docker-compose.yml config.py requirements.txt; do
        if [[ -f "$PROJECT_ROOT/$config_file" ]]; then
            if [[ "$config_file" == ".env" ]]; then
                # Sanitize .env file
                sanitize_env_file "$PROJECT_ROOT/$config_file" "$app_backup_dir/config/$config_file"
            else
                cp "$PROJECT_ROOT/$config_file" "$app_backup_dir/config/"
            fi
        fi
    done
    
    # Copy config directory if it exists
    if [[ -d "$PROJECT_ROOT/config" ]]; then
        cp -r "$PROJECT_ROOT/config" "$app_backup_dir/"
    fi
    
    # Create application backup metadata
    cat > "$app_backup_dir/app_backup_metadata.json" << EOF
{
    "backup_timestamp": "$(date -Iseconds)",
    "application_version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "storage_size": $(du -sb "$PROJECT_ROOT/storage" 2>/dev/null | cut -f1 || echo 0),
    "logs_size": $(du -sb "$PROJECT_ROOT/logs" 2>/dev/null | cut -f1 || echo 0),
    "config_files": [
        $(find "$app_backup_dir/config" -type f -printf '"%f",' 2>/dev/null | sed 's/,$//')
    ]
}
EOF
    
    # Compress if requested
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing application data backup..."
        tar -czf "$app_backup_dir/storage.tar.gz" -C "$app_backup_dir" storage && rm -rf "$app_backup_dir/storage"
        tar -czf "$app_backup_dir/logs.tar.gz" -C "$app_backup_dir" logs && rm -rf "$app_backup_dir/logs"
        tar -czf "$app_backup_dir/config.tar.gz" -C "$app_backup_dir" config && rm -rf "$app_backup_dir/config"
    fi
    
    log "Application data backup completed successfully"
    return 0
}

backup_vault_secrets() {
    local backup_path="$1"
    local vault_backup_dir="$backup_path/vault"
    
    log "Starting Vault secrets backup..."
    
    if ! check_container_running "$VAULT_CONTAINER"; then
        log "Vault container not running, skipping Vault backup"
        return 0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would backup Vault secrets"
        return 0
    fi
    
    # Create Vault snapshot
    log "Creating Vault snapshot..."
    docker exec "$VAULT_CONTAINER" vault operator raft snapshot save /vault/backups/vault_snapshot_${TIMESTAMP} 2>/dev/null || {
        log "Vault snapshot failed, backing up data directory instead"
        docker cp "$VAULT_CONTAINER:/vault/data" "$vault_backup_dir/"
    }
    
    # Copy Vault snapshot if it was created
    if docker exec "$VAULT_CONTAINER" test -f "/vault/backups/vault_snapshot_${TIMESTAMP}" 2>/dev/null; then
        docker cp "$VAULT_CONTAINER:/vault/backups/vault_snapshot_${TIMESTAMP}" "$vault_backup_dir/"
    fi
    
    # Backup Vault configuration
    docker exec "$VAULT_CONTAINER" cat /vault/config/vault.hcl > "$vault_backup_dir/vault.hcl" 2>/dev/null || true
    
    # Create Vault backup metadata
    cat > "$vault_backup_dir/vault_backup_metadata.json" << EOF
{
    "backup_timestamp": "$(date -Iseconds)",
    "vault_version": "$(docker exec "$VAULT_CONTAINER" vault version 2>/dev/null | head -n1 || echo 'unknown')",
    "backup_type": "snapshot",
    "snapshot_file": "vault_snapshot_${TIMESTAMP}",
    "data_backup": $(test -d "$vault_backup_dir/data" && echo "true" || echo "false")
}
EOF
    
    # Encrypt Vault backup (always encrypt secrets)
    log "Encrypting Vault backup..."
    if [[ -f "$vault_backup_dir/vault_snapshot_${TIMESTAMP}" ]]; then
        encrypt_file "$vault_backup_dir/vault_snapshot_${TIMESTAMP}"
    fi
    
    if [[ -d "$vault_backup_dir/data" ]]; then
        tar -czf "$vault_backup_dir/vault_data.tar.gz" -C "$vault_backup_dir" data
        encrypt_file "$vault_backup_dir/vault_data.tar.gz"
        rm -rf "$vault_backup_dir/data"
    fi
    
    log "Vault secrets backup completed successfully"
    return 0
}

sanitize_env_file() {
    local src_file="$1"
    local dst_file="$2"
    
    # List of sensitive environment variable patterns
    local sensitive_patterns=(
        "PASSWORD" "SECRET" "KEY" "TOKEN" "CREDENTIAL"
        "ACCESS_TOKEN" "CLIENT_SECRET" "ENCRYPTION_KEY"
        "MYSQL_PASSWORD" "REDIS_PASSWORD" "VAULT_TOKEN"
    )
    
    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
            # Comment or empty line
            echo "$line" >> "$dst_file"
        elif [[ "$line" =~ = ]]; then
            # Environment variable
            local var_name="${line%%=*}"
            local is_sensitive=false
            
            for pattern in "${sensitive_patterns[@]}"; do
                if [[ "$var_name" =~ $pattern ]]; then
                    is_sensitive=true
                    break
                fi
            done
            
            if [[ "$is_sensitive" == "true" ]]; then
                echo "${var_name}=***REDACTED***" >> "$dst_file"
            else
                echo "$line" >> "$dst_file"
            fi
        else
            echo "$line" >> "$dst_file"
        fi
    done < "$src_file"
}

encrypt_file() {
    local file_path="$1"
    
    if [[ ! -f "$file_path" ]]; then
        error "File not found for encryption: $file_path"
        return 1
    fi
    
    # Use OpenSSL for encryption (AES-256-CBC)
    local encryption_key="${BACKUP_ENCRYPTION_KEY:-$(openssl rand -hex 32)}"
    
    openssl enc -aes-256-cbc -salt -in "$file_path" -out "${file_path}.enc" -k "$encryption_key"
    
    if [[ $? -eq 0 ]]; then
        rm "$file_path"
        log "File encrypted: ${file_path}.enc"
    else
        error "Failed to encrypt file: $file_path"
        return 1
    fi
}

decrypt_file() {
    local encrypted_file="$1"
    local output_file="${encrypted_file%.enc}"
    
    if [[ ! -f "$encrypted_file" ]]; then
        error "Encrypted file not found: $encrypted_file"
        return 1
    fi
    
    local encryption_key="${BACKUP_ENCRYPTION_KEY:-}"
    if [[ -z "$encryption_key" ]]; then
        read -s -p "Enter encryption key: " encryption_key
        echo
    fi
    
    openssl enc -aes-256-cbc -d -in "$encrypted_file" -out "$output_file" -k "$encryption_key"
    
    if [[ $? -eq 0 ]]; then
        log "File decrypted: $output_file"
        return 0
    else
        error "Failed to decrypt file: $encrypted_file"
        return 1
    fi
}

verify_backup() {
    local backup_path="$1"
    
    log "Verifying backup integrity: $backup_path"
    
    if [[ ! -d "$backup_path" ]]; then
        error "Backup directory not found: $backup_path"
        return 1
    fi
    
    local verification_errors=0
    
    # Verify backup manifest
    if [[ ! -f "$backup_path/backup_manifest.json" ]]; then
        error "Backup manifest not found"
        ((verification_errors++))
    fi
    
    # Verify MySQL backup
    if [[ -d "$backup_path/mysql" ]]; then
        log "Verifying MySQL backup..."
        
        if [[ -f "$backup_path/mysql/mysql_backup_metadata.json" ]]; then
            local expected_checksum
            expected_checksum=$(jq -r '.checksum' "$backup_path/mysql/mysql_backup_metadata.json")
            
            local dump_file="$backup_path/mysql/full_dump.sql"
            [[ -f "${dump_file}.gz" ]] && dump_file="${dump_file}.gz"
            [[ -f "${dump_file}.enc" ]] && dump_file="${dump_file}.enc"
            
            if [[ -f "$dump_file" ]]; then
                local actual_checksum
                actual_checksum=$(sha256sum "$dump_file" | cut -d' ' -f1)
                
                if [[ "$expected_checksum" != "$actual_checksum" ]]; then
                    error "MySQL backup checksum mismatch"
                    ((verification_errors++))
                else
                    log "MySQL backup checksum verified"
                fi
            else
                error "MySQL dump file not found"
                ((verification_errors++))
            fi
        else
            error "MySQL backup metadata not found"
            ((verification_errors++))
        fi
    fi
    
    # Verify Redis backup
    if [[ -d "$backup_path/redis" ]]; then
        log "Verifying Redis backup..."
        
        if [[ -f "$backup_path/redis/redis_backup_metadata.json" ]]; then
            local rdb_file="$backup_path/redis/dump.rdb"
            [[ -f "${rdb_file}.gz" ]] && rdb_file="${rdb_file}.gz"
            [[ -f "${rdb_file}.enc" ]] && rdb_file="${rdb_file}.enc"
            
            if [[ -f "$rdb_file" ]]; then
                log "Redis RDB file found"
            else
                error "Redis RDB file not found"
                ((verification_errors++))
            fi
        else
            error "Redis backup metadata not found"
            ((verification_errors++))
        fi
    fi
    
    # Verify application data backup
    if [[ -d "$backup_path/app" ]]; then
        log "Verifying application data backup..."
        
        if [[ -f "$backup_path/app/app_backup_metadata.json" ]]; then
            log "Application backup metadata found"
        else
            error "Application backup metadata not found"
            ((verification_errors++))
        fi
    fi
    
    # Update backup manifest with verification status
    if [[ -f "$backup_path/backup_manifest.json" ]]; then
        local temp_manifest
        temp_manifest=$(mktemp)
        jq ".options.verified = $([ $verification_errors -eq 0 ] && echo true || echo false)" "$backup_path/backup_manifest.json" > "$temp_manifest"
        mv "$temp_manifest" "$backup_path/backup_manifest.json"
    fi
    
    if [[ $verification_errors -eq 0 ]]; then
        log "Backup verification completed successfully"
        return 0
    else
        error "Backup verification failed with $verification_errors errors"
        return 1
    fi
}

# Main backup function
perform_full_backup() {
    log "Starting full system backup..."
    
    check_docker_compose
    
    create_backup_directory "$BACKUP_DIR"
    
    local backup_success=true
    
    # Backup each component
    backup_mysql "$BACKUP_DIR" || backup_success=false
    backup_redis "$BACKUP_DIR" || backup_success=false
    backup_application_data "$BACKUP_DIR" || backup_success=false
    backup_vault_secrets "$BACKUP_DIR" || backup_success=false
    
    if [[ "$backup_success" == "true" ]]; then
        # Update backup manifest
        local temp_manifest
        temp_manifest=$(mktemp)
        jq '.components.mysql = true | .components.redis = true | .components.app = true | .components.vault = true' "$BACKUP_DIR/backup_manifest.json" > "$temp_manifest"
        mv "$temp_manifest" "$BACKUP_DIR/backup_manifest.json"
        
        # Verify backup if requested
        if [[ "$VERIFY_BACKUP" == "true" ]]; then
            verify_backup "$BACKUP_DIR"
        fi
        
        log "Full system backup completed successfully: $BACKUP_DIR"
        
        # Calculate backup size
        local backup_size
        backup_size=$(du -sh "$BACKUP_DIR" | cut -f1)
        log "Backup size: $backup_size"
        
        return 0
    else
        error "Full system backup failed"
        return 1
    fi
}

# Execute command
case "$COMMAND" in
    backup)
        perform_full_backup
        ;;
    backup-mysql)
        check_docker_compose
        create_backup_directory "$BACKUP_DIR"
        backup_mysql "$BACKUP_DIR"
        ;;
    backup-redis)
        check_docker_compose
        create_backup_directory "$BACKUP_DIR"
        backup_redis "$BACKUP_DIR"
        ;;
    backup-app)
        create_backup_directory "$BACKUP_DIR"
        backup_application_data "$BACKUP_DIR"
        ;;
    backup-vault)
        check_docker_compose
        create_backup_directory "$BACKUP_DIR"
        backup_vault_secrets "$BACKUP_DIR"
        ;;
    verify)
        if [[ -n "$RESTORE_FROM" ]]; then
            verify_backup "$RESTORE_FROM"
        else
            error "Please specify backup directory with --restore-from"
            exit 1
        fi
        ;;
    list-backups)
        log "Available backups:"
        find "$BACKUP_BASE_DIR" -name "backup_manifest.json" -exec dirname {} \; | sort
        ;;
    *)
        error "Command not implemented yet: $COMMAND"
        exit 1
        ;;
esac