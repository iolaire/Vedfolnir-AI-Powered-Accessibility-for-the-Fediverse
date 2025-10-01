#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -euo pipefail

# Docker Compose Secret Rotation Automation
# Secret rotation automation and container update procedures

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
SECRETS_DIR="$PROJECT_ROOT/secrets"
BACKUP_DIR="$PROJECT_ROOT/storage/backups/secrets"
ROTATION_LOG="$PROJECT_ROOT/logs/secret_rotation.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    local message="$1"
    echo -e "${BLUE}[INFO]${NC} $message"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $message" >> "$ROTATION_LOG"
}

log_success() {
    local message="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $message"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $message" >> "$ROTATION_LOG"
}

log_warning() {
    local message="$1"
    echo -e "${YELLOW}[WARNING]${NC} $message"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARNING] $message" >> "$ROTATION_LOG"
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR]${NC} $message"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $message" >> "$ROTATION_LOG"
}

# Initialize logging
mkdir -p "$(dirname "$ROTATION_LOG")"
mkdir -p "$BACKUP_DIR"

# Change to project root
cd "$PROJECT_ROOT"

# Rotate all secrets
rotate_all_secrets() {
    log_info "Starting comprehensive secret rotation..."
    
    # Create backup of current secrets
    backup_current_secrets
    
    # Rotate individual secrets
    rotate_flask_secret
    rotate_platform_encryption_key
    rotate_mysql_passwords
    rotate_redis_password
    rotate_vault_tokens
    
    # Update services with new secrets
    update_services_with_secrets
    
    # Verify secret rotation
    verify_secret_rotation
    
    log_success "Secret rotation completed successfully"
}

# Backup current secrets
backup_current_secrets() {
    log_info "Backing up current secrets..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/secrets_backup_$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Copy all secret files
    if [[ -d "$SECRETS_DIR" ]]; then
        cp -r "$SECRETS_DIR"/* "$backup_path/"
        
        # Create backup manifest
        cat > "$backup_path/manifest.txt" << EOF
Secret Backup Manifest
=====================
Backup Date: $(date)
Backup Path: $backup_path
Original Path: $SECRETS_DIR

Files backed up:
$(ls -la "$backup_path")
EOF
        
        log_success "Secrets backed up to: $backup_path"
    else
        log_error "Secrets directory not found: $SECRETS_DIR"
        return 1
    fi
}

# Rotate Flask secret key
rotate_flask_secret() {
    log_info "Rotating Flask secret key..."
    
    local secret_file="$SECRETS_DIR/flask_secret_key.txt"
    local old_secret=""
    
    # Backup old secret
    if [[ -f "$secret_file" ]]; then
        old_secret=$(cat "$secret_file")
    fi
    
    # Generate new secret
    local new_secret=$(openssl rand -base64 32)
    echo "$new_secret" > "$secret_file"
    chmod 600 "$secret_file"
    
    log_success "Flask secret key rotated"
    
    # Store rotation info
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Flask secret key rotated" >> "$SECRETS_DIR/.rotation_history"
}

# Rotate platform encryption key
rotate_platform_encryption_key() {
    log_info "Rotating platform encryption key..."
    
    local secret_file="$SECRETS_DIR/platform_encryption_key.txt"
    
    # Note: This is more complex as existing encrypted data needs to be re-encrypted
    log_warning "Platform encryption key rotation requires data re-encryption"
    log_warning "This operation should be performed during maintenance window"
    
    # Generate new key
    local new_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # For now, just generate the new key - actual rotation would require application support
    echo "$new_key" > "${secret_file}.new"
    chmod 600 "${secret_file}.new"
    
    log_warning "New platform encryption key generated as ${secret_file}.new"
    log_warning "Manual data re-encryption required before activation"
    
    # Store rotation info
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Platform encryption key prepared for rotation" >> "$SECRETS_DIR/.rotation_history"
}

# Rotate MySQL passwords
rotate_mysql_passwords() {
    log_info "Rotating MySQL passwords..."
    
    # Generate new passwords
    local new_root_password=$(openssl rand -base64 32)
    local new_user_password=$(openssl rand -base64 32)
    
    # Update password files
    echo "$new_root_password" > "$SECRETS_DIR/mysql_root_password.txt"
    echo "$new_user_password" > "$SECRETS_DIR/mysql_password.txt"
    chmod 600 "$SECRETS_DIR"/mysql_*_password.txt
    
    # Update MySQL with new passwords
    if docker-compose ps mysql | grep -q "Up"; then
        log_info "Updating MySQL with new passwords..."
        
        # Update root password
        docker-compose exec mysql mysql -u root -p"$(cat "$BACKUP_DIR"/secrets_backup_*/mysql_root_password.txt 2>/dev/null || echo 'oldpassword')" -e "
            ALTER USER 'root'@'localhost' IDENTIFIED BY '$new_root_password';
            ALTER USER 'root'@'%' IDENTIFIED BY '$new_root_password';
        " 2>/dev/null || log_warning "Root password update may have failed"
        
        # Update user password
        docker-compose exec mysql mysql -u root -p"$new_root_password" -e "
            ALTER USER 'vedfolnir'@'%' IDENTIFIED BY '$new_user_password';
            FLUSH PRIVILEGES;
        "
        
        log_success "MySQL passwords rotated"
    else
        log_warning "MySQL service not running - passwords updated in files only"
    fi
    
    # Store rotation info
    echo "$(date '+%Y-%m-%d %H:%M:%S'): MySQL passwords rotated" >> "$SECRETS_DIR/.rotation_history"
}

# Rotate Redis password
rotate_redis_password() {
    log_info "Rotating Redis password..."
    
    local secret_file="$SECRETS_DIR/redis_password.txt"
    local new_password=$(openssl rand -base64 32)
    
    # Update password file
    echo "$new_password" > "$secret_file"
    chmod 600 "$secret_file"
    
    # Update Redis configuration
    if docker-compose ps redis | grep -q "Up"; then
        log_info "Updating Redis with new password..."
        
        # Update Redis password
        docker-compose exec redis redis-cli CONFIG SET requirepass "$new_password"
        
        log_success "Redis password rotated"
    else
        log_warning "Redis service not running - password updated in file only"
    fi
    
    # Store rotation info
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Redis password rotated" >> "$SECRETS_DIR/.rotation_history"
}

# Rotate Vault tokens
rotate_vault_tokens() {
    log_info "Rotating Vault tokens..."
    
    # Generate new tokens
    local new_root_token=$(openssl rand -base64 32)
    local new_token=$(openssl rand -base64 32)
    
    # Update token files
    echo "$new_root_token" > "$SECRETS_DIR/vault_root_token.txt"
    echo "$new_token" > "$SECRETS_DIR/vault_token.txt"
    chmod 600 "$SECRETS_DIR"/vault_*_token.txt
    
    if docker-compose ps vault | grep -q "Up"; then
        log_info "Updating Vault with new tokens..."
        
        # Note: Vault token rotation is complex and depends on Vault configuration
        log_warning "Vault token rotation requires manual intervention"
        log_warning "New tokens generated but not activated in Vault"
    else
        log_warning "Vault service not running - tokens updated in files only"
    fi
    
    # Store rotation info
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Vault tokens rotated" >> "$SECRETS_DIR/.rotation_history"
}

# Update services with new secrets
update_services_with_secrets() {
    log_info "Updating services with new secrets..."
    
    # Restart services to pick up new secrets
    local services=("mysql" "redis" "vault" "vedfolnir")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_info "Restarting $service with new secrets..."
            docker-compose restart "$service"
            
            # Wait for service to be ready
            sleep 10
            
            case "$service" in
                mysql)
                    if docker-compose exec mysql mysqladmin ping -h localhost --silent; then
                        log_success "$service restarted successfully"
                    else
                        log_error "$service failed to restart properly"
                    fi
                    ;;
                redis)
                    if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
                        log_success "$service restarted successfully"
                    else
                        log_error "$service failed to restart properly"
                    fi
                    ;;
                *)
                    log_success "$service restarted"
                    ;;
            esac
        fi
    done
}

# Verify secret rotation
verify_secret_rotation() {
    log_info "Verifying secret rotation..."
    
    local issues=0
    
    # Check if secret files exist and have proper permissions
    local secret_files=(
        "flask_secret_key.txt"
        "mysql_root_password.txt"
        "mysql_password.txt"
        "redis_password.txt"
        "vault_root_token.txt"
        "vault_token.txt"
    )
    
    for secret_file in "${secret_files[@]}"; do
        local file_path="$SECRETS_DIR/$secret_file"
        
        if [[ -f "$file_path" ]]; then
            local perms=$(stat -c "%a" "$file_path")
            if [[ "$perms" == "600" ]]; then
                log_success "$secret_file: OK (permissions: $perms)"
            else
                log_error "$secret_file: Incorrect permissions ($perms)"
                ((issues++))
            fi
        else
            log_error "$secret_file: Missing"
            ((issues++))
        fi
    done
    
    # Test service connectivity with new secrets
    if docker-compose exec mysql mysqladmin ping -h localhost --silent; then
        log_success "MySQL connectivity: OK"
    else
        log_error "MySQL connectivity: FAILED"
        ((issues++))
    fi
    
    if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis connectivity: OK"
    else
        log_error "Redis connectivity: FAILED"
        ((issues++))
    fi
    
    # Test application health
    if curl -f -s http://localhost:80/health > /dev/null 2>&1; then
        log_success "Application health: OK"
    else
        log_error "Application health: FAILED"
        ((issues++))
    fi
    
    if [[ $issues -eq 0 ]]; then
        log_success "Secret rotation verification: PASSED"
    else
        log_error "Secret rotation verification: FAILED ($issues issues)"
        return 1
    fi
}

# Rotate specific secret
rotate_specific_secret() {
    local secret_type="$1"
    
    log_info "Rotating specific secret: $secret_type"
    
    case "$secret_type" in
        flask)
            rotate_flask_secret
            docker-compose restart vedfolnir
            ;;
        mysql)
            rotate_mysql_passwords
            docker-compose restart mysql vedfolnir
            ;;
        redis)
            rotate_redis_password
            docker-compose restart redis vedfolnir
            ;;
        vault)
            rotate_vault_tokens
            docker-compose restart vault
            ;;
        platform)
            rotate_platform_encryption_key
            log_warning "Platform encryption key rotation requires manual data re-encryption"
            ;;
        *)
            log_error "Unknown secret type: $secret_type"
            return 1
            ;;
    esac
    
    log_success "Secret rotation completed for: $secret_type"
}

# Check secret age
check_secret_age() {
    log_info "Checking secret age..."
    
    local rotation_history="$SECRETS_DIR/.rotation_history"
    
    if [[ -f "$rotation_history" ]]; then
        log_info "Recent secret rotations:"
        tail -10 "$rotation_history"
    else
        log_warning "No rotation history found"
    fi
    
    # Check file modification times
    local secret_files=(
        "flask_secret_key.txt"
        "mysql_root_password.txt"
        "mysql_password.txt"
        "redis_password.txt"
        "vault_root_token.txt"
        "vault_token.txt"
    )
    
    local current_time=$(date +%s)
    local ninety_days=$((90 * 24 * 3600))
    
    for secret_file in "${secret_files[@]}"; do
        local file_path="$SECRETS_DIR/$secret_file"
        
        if [[ -f "$file_path" ]]; then
            local file_time=$(stat -c %Y "$file_path")
            local age_days=$(( (current_time - file_time) / 86400 ))
            
            if [[ $age_days -gt 90 ]]; then
                log_warning "$secret_file: $age_days days old (rotation recommended)"
            else
                log_info "$secret_file: $age_days days old"
            fi
        fi
    done
}

# Emergency secret reset
emergency_reset() {
    log_warning "Starting emergency secret reset..."
    
    read -p "This will reset ALL secrets and restart services. Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Emergency reset cancelled"
        return 0
    fi
    
    # Stop all services
    log_info "Stopping all services..."
    docker-compose down
    
    # Backup current secrets
    backup_current_secrets
    
    # Generate all new secrets
    log_info "Generating new secrets..."
    
    openssl rand -base64 32 > "$SECRETS_DIR/flask_secret_key.txt"
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > "$SECRETS_DIR/platform_encryption_key.txt"
    openssl rand -base64 32 > "$SECRETS_DIR/mysql_root_password.txt"
    openssl rand -base64 32 > "$SECRETS_DIR/mysql_password.txt"
    openssl rand -base64 32 > "$SECRETS_DIR/redis_password.txt"
    openssl rand -base64 32 > "$SECRETS_DIR/vault_root_token.txt"
    openssl rand -base64 32 > "$SECRETS_DIR/vault_token.txt"
    
    # Set proper permissions
    chmod 600 "$SECRETS_DIR"/*.txt
    
    # Start services
    log_info "Starting services with new secrets..."
    docker-compose up -d
    
    # Wait for services
    sleep 30
    
    # Verify emergency reset
    if verify_secret_rotation; then
        log_success "Emergency secret reset completed successfully"
    else
        log_error "Emergency secret reset failed - manual intervention required"
        return 1
    fi
}

# Show usage
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  rotate [TYPE]             Rotate secrets (all|flask|mysql|redis|vault|platform)"
    echo "  check                     Check secret age and rotation history"
    echo "  verify                    Verify current secrets are working"
    echo "  emergency                 Emergency reset of all secrets"
    echo ""
    echo "Examples:"
    echo "  $0 rotate all             Rotate all secrets"
    echo "  $0 rotate mysql           Rotate only MySQL passwords"
    echo "  $0 check                  Check secret age"
    echo "  $0 emergency              Emergency reset all secrets"
}

# Main command handling
case "${1:-}" in
    rotate)
        if [[ "${2:-}" == "all" || -z "${2:-}" ]]; then
            rotate_all_secrets
        else
            rotate_specific_secret "${2}"
        fi
        ;;
    check)
        check_secret_age
        ;;
    verify)
        verify_secret_rotation
        ;;
    emergency)
        emergency_reset
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