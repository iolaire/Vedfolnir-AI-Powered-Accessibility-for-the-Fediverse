#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vault Management Script for Vedfolnir Docker Compose
# Provides management commands for HashiCorp Vault integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"

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

# Check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        log_error "Docker Compose not found. Please install Docker and Docker Compose."
        exit 1
    fi
    
    # Use docker compose if available, fallback to docker-compose
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
}

# Create required directories
create_directories() {
    log_info "Creating required directories..."
    
    mkdir -p "$PROJECT_ROOT/data/vault"
    mkdir -p "$PROJECT_ROOT/logs/vault"
    mkdir -p "$PROJECT_ROOT/config/vault"
    mkdir -p "$PROJECT_ROOT/data/vault/secrets"
    mkdir -p "$PROJECT_ROOT/secrets"
    
    # Set proper permissions
    chmod 700 "$PROJECT_ROOT/data/vault"
    chmod 700 "$PROJECT_ROOT/data/vault/secrets"
    chmod 700 "$PROJECT_ROOT/secrets"
    
    log_success "Directories created successfully"
}

# Generate initial secrets
generate_initial_secrets() {
    log_info "Generating initial secrets..."
    
    # Generate MySQL root password
    if [ ! -f "$PROJECT_ROOT/secrets/mysql_root_password.txt" ]; then
        openssl rand -base64 32 > "$PROJECT_ROOT/secrets/mysql_root_password.txt"
        chmod 600 "$PROJECT_ROOT/secrets/mysql_root_password.txt"
        log_success "Generated MySQL root password"
    fi
    
    # Generate Redis password
    if [ ! -f "$PROJECT_ROOT/data/vault/secrets/redis_password.txt" ]; then
        openssl rand -base64 32 > "$PROJECT_ROOT/data/vault/secrets/redis_password.txt"
        chmod 600 "$PROJECT_ROOT/data/vault/secrets/redis_password.txt"
        log_success "Generated Redis password"
    fi
    
    # Generate Vault root token (for development)
    if [ ! -f "$PROJECT_ROOT/secrets/vault_root_token.txt" ]; then
        openssl rand -base64 32 > "$PROJECT_ROOT/secrets/vault_root_token.txt"
        chmod 600 "$PROJECT_ROOT/secrets/vault_root_token.txt"
        log_success "Generated Vault root token"
    fi
}

# Start Vault services
start_vault() {
    log_info "Starting Vault services..."
    
    cd "$DOCKER_DIR"
    
    # Start Vault and dependencies
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml up -d vault mysql redis
    
    # Wait for Vault to be ready
    log_info "Waiting for Vault to be ready..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -s "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
            log_success "Vault is ready!"
            break
        fi
        sleep 2
        ((timeout--))
    done
    
    if [ $timeout -eq 0 ]; then
        log_error "Vault failed to start within timeout"
        return 1
    fi
    
    # Start initialization service
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml up -d vault-init
    
    # Wait for initialization to complete
    log_info "Waiting for Vault initialization..."
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml logs -f vault-init
    
    # Start secret management services
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml up -d vault-rotation vault-secrets
    
    log_success "Vault services started successfully"
}

# Stop Vault services
stop_vault() {
    log_info "Stopping Vault services..."
    
    cd "$DOCKER_DIR"
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml down
    
    log_success "Vault services stopped"
}

# Check Vault status
status_vault() {
    log_info "Checking Vault status..."
    
    # Check if Vault is running
    if curl -s "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        log_success "Vault is running and accessible"
        
        # Get detailed status
        vault_status=$(curl -s "$VAULT_ADDR/v1/sys/health" | python3 -m json.tool 2>/dev/null || echo "Failed to parse status")
        echo "$vault_status"
    else
        log_error "Vault is not accessible at $VAULT_ADDR"
        return 1
    fi
    
    # Check Docker services
    cd "$DOCKER_DIR"
    log_info "Docker services status:"
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml ps vault vault-init vault-rotation vault-secrets
}

# Test Vault integration
test_vault() {
    log_info "Testing Vault integration..."
    
    cd "$DOCKER_DIR"
    
    # Run integration tests
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec vault-secrets python /app/test-vault-integration.py
    
    if [ $? -eq 0 ]; then
        log_success "Vault integration tests passed"
    else
        log_error "Vault integration tests failed"
        return 1
    fi
}

# Rotate secrets
rotate_secrets() {
    log_info "Rotating secrets..."
    
    cd "$DOCKER_DIR"
    
    if [ -n "$1" ]; then
        # Rotate specific secret
        log_info "Rotating secret: $1"
        $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec vault-rotation python /app/secret-rotation.py --rotate "$1"
    else
        # Rotate all secrets that need it
        log_info "Rotating all secrets that need rotation"
        $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec vault-rotation python /app/secret-rotation.py --rotate-all
    fi
    
    if [ $? -eq 0 ]; then
        log_success "Secret rotation completed"
        
        # Sync secrets to Docker files
        log_info "Syncing rotated secrets..."
        $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec vault-secrets python /app/docker-secrets-integration.py --sync
    else
        log_error "Secret rotation failed"
        return 1
    fi
}

# Check secret status
check_secrets() {
    log_info "Checking secret status..."
    
    cd "$DOCKER_DIR"
    
    # Check rotation status
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec vault-rotation python /app/secret-rotation.py --report
    
    # Check secrets validation
    log_info "Validating Docker secrets..."
    $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec vault-secrets python /app/docker-secrets-integration.py --validate
}

# Backup Vault data
backup_vault() {
    log_info "Creating Vault backup..."
    
    backup_dir="$PROJECT_ROOT/backups/vault_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup Vault data
    cp -r "$PROJECT_ROOT/data/vault" "$backup_dir/"
    
    # Backup secrets
    cp -r "$PROJECT_ROOT/data/vault/secrets" "$backup_dir/"
    
    # Create snapshot if Vault is running
    if curl -s "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        cd "$DOCKER_DIR"
        $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec vault vault operator raft snapshot save /vault/data/backup_snapshot || true
        cp "$PROJECT_ROOT/data/vault/backup_snapshot" "$backup_dir/" 2>/dev/null || true
    fi
    
    # Compress backup
    tar -czf "${backup_dir}.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
    rm -rf "$backup_dir"
    
    log_success "Vault backup created: ${backup_dir}.tar.gz"
}

# Restore Vault data
restore_vault() {
    if [ -z "$1" ]; then
        log_error "Please specify backup file to restore"
        return 1
    fi
    
    backup_file="$1"
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_warning "This will overwrite existing Vault data. Continue? (y/N)"
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "Restore cancelled"
        return 0
    fi
    
    log_info "Stopping Vault services..."
    stop_vault
    
    log_info "Restoring Vault data from: $backup_file"
    
    # Extract backup
    temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"
    
    # Restore data
    backup_name=$(basename "$backup_file" .tar.gz)
    cp -r "$temp_dir/$backup_name/vault" "$PROJECT_ROOT/data/"
    cp -r "$temp_dir/$backup_name/secrets" "$PROJECT_ROOT/data/vault/"
    
    # Cleanup
    rm -rf "$temp_dir"
    
    log_success "Vault data restored successfully"
    log_info "Starting Vault services..."
    start_vault
}

# Show logs
show_logs() {
    cd "$DOCKER_DIR"
    
    if [ -n "$1" ]; then
        # Show logs for specific service
        $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml logs -f "$1"
    else
        # Show logs for all Vault services
        $DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml logs -f vault vault-init vault-rotation vault-secrets
    fi
}

# Show help
show_help() {
    echo "Vault Management Script for Vedfolnir"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup                 - Create directories and generate initial secrets"
    echo "  start                 - Start Vault services"
    echo "  stop                  - Stop Vault services"
    echo "  restart               - Restart Vault services"
    echo "  status                - Check Vault status"
    echo "  test                  - Run Vault integration tests"
    echo "  rotate [secret]       - Rotate secrets (all or specific secret)"
    echo "  check-secrets         - Check secret status and rotation needs"
    echo "  backup                - Create Vault backup"
    echo "  restore <file>        - Restore Vault from backup"
    echo "  logs [service]        - Show logs (all Vault services or specific service)"
    echo "  help                  - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup              - Initial setup"
    echo "  $0 start              - Start all Vault services"
    echo "  $0 rotate flask       - Rotate Flask secret key"
    echo "  $0 logs vault         - Show Vault server logs"
    echo ""
    echo "Environment Variables:"
    echo "  VAULT_ADDR            - Vault server address (default: http://localhost:8200)"
}

# Main command handling
main() {
    check_docker_compose
    
    case "${1:-help}" in
        setup)
            create_directories
            generate_initial_secrets
            ;;
        start)
            create_directories
            generate_initial_secrets
            start_vault
            ;;
        stop)
            stop_vault
            ;;
        restart)
            stop_vault
            sleep 2
            start_vault
            ;;
        status)
            status_vault
            ;;
        test)
            test_vault
            ;;
        rotate)
            rotate_secrets "$2"
            ;;
        check-secrets)
            check_secrets
            ;;
        backup)
            backup_vault
            ;;
        restore)
            restore_vault "$2"
            ;;
        logs)
            show_logs "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"