#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -euo pipefail

# Docker Compose Deployment Automation Script
# Automated setup script for initial Docker Compose deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env.docker"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create directory structure
create_directory_structure() {
    log_info "Creating directory structure..."
    
    local directories=(
        "data/mysql"
        "data/redis"
        "data/prometheus"
        "data/grafana"
        "data/loki"
        "data/vault"
        "logs/app"
        "logs/nginx"
        "logs/mysql"
        "logs/redis"
        "logs/vault"
        "logs/audit"
        "storage/backups/mysql"
        "storage/backups/redis"
        "storage/backups/app"
        "storage/images"
        "storage/temp"
        "config/mysql"
        "config/redis"
        "config/nginx"
        "config/prometheus"
        "config/grafana"
        "config/loki"
        "config/vault"
        "config/app"
        "secrets/database"
        "secrets/redis"
        "secrets/app"
        "ssl/certs"
        "ssl/keys"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$PROJECT_ROOT/$dir"
        log_info "Created directory: $dir"
    done
    
    log_success "Directory structure created"
}

# Generate secrets
generate_secrets() {
    log_info "Generating secrets..."
    
    local secrets_dir="$PROJECT_ROOT/secrets"
    
    # Generate Flask secret key
    if [[ ! -f "$secrets_dir/flask_secret_key.txt" ]]; then
        openssl rand -base64 32 > "$secrets_dir/flask_secret_key.txt"
        log_info "Generated Flask secret key"
    fi
    
    # Generate platform encryption key
    if [[ ! -f "$secrets_dir/platform_encryption_key.txt" ]]; then
        python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > "$secrets_dir/platform_encryption_key.txt"
        log_info "Generated platform encryption key"
    fi
    
    # Generate MySQL passwords
    if [[ ! -f "$secrets_dir/mysql_root_password.txt" ]]; then
        openssl rand -base64 32 > "$secrets_dir/mysql_root_password.txt"
        log_info "Generated MySQL root password"
    fi
    
    if [[ ! -f "$secrets_dir/mysql_password.txt" ]]; then
        openssl rand -base64 32 > "$secrets_dir/mysql_password.txt"
        log_info "Generated MySQL user password"
    fi
    
    # Generate Redis password
    if [[ ! -f "$secrets_dir/redis_password.txt" ]]; then
        openssl rand -base64 32 > "$secrets_dir/redis_password.txt"
        log_info "Generated Redis password"
    fi
    
    # Generate Vault token
    if [[ ! -f "$secrets_dir/vault_root_token.txt" ]]; then
        openssl rand -base64 32 > "$secrets_dir/vault_root_token.txt"
        log_info "Generated Vault root token"
    fi
    
    if [[ ! -f "$secrets_dir/vault_token.txt" ]]; then
        openssl rand -base64 32 > "$secrets_dir/vault_token.txt"
        log_info "Generated Vault token"
    fi
    
    # Set proper permissions
    chmod 600 "$secrets_dir"/*.txt
    
    log_success "Secrets generated and secured"
}

# Create environment file
create_environment_file() {
    log_info "Creating Docker environment file..."
    
    if [[ -f "$ENV_FILE" ]]; then
        log_warning "Environment file already exists. Creating backup..."
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    cat > "$ENV_FILE" << 'EOF'
# Docker Compose Environment Configuration
# Generated by deployment automation script

# Application Configuration
FLASK_ENV=production
FLASK_DEBUG=false
LOG_LEVEL=INFO

# Database Configuration (MySQL)
MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password
MYSQL_PASSWORD_FILE=/run/secrets/mysql_password
MYSQL_DATABASE=vedfolnir
MYSQL_USER=vedfolnir
DATABASE_URL=mysql+pymysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir?charset=utf8mb4

# Redis Configuration
REDIS_PASSWORD_FILE=/run/secrets/redis_password
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_SESSION_PREFIX=vedfolnir:session:
REDIS_SESSION_TIMEOUT=7200

# Ollama Configuration (External Service)
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llava:7b

# Security Configuration
FLASK_SECRET_KEY_FILE=/run/secrets/flask_secret_key
PLATFORM_ENCRYPTION_KEY_FILE=/run/secrets/platform_encryption_key
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true

# Session Configuration
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=Lax
DB_SESSION_FALLBACK=true
DB_SESSION_SYNC=true

# RQ Configuration
RQ_ENABLE_INTEGRATED_WORKERS=true
RQ_ENABLE_EXTERNAL_WORKERS=false

# Observability Configuration
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100
GRAFANA_URL=http://grafana:3000

# Vault Configuration
VAULT_ADDR=http://vault:8200
VAULT_TOKEN_FILE=/run/secrets/vault_token

# Resource Limits
MEMORY_LIMIT=2g
CPU_LIMIT=2

# Backup Configuration
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=0 2 * * *

# Network Configuration
COMPOSE_PROJECT_NAME=vedfolnir
EOF
    
    log_success "Environment file created: $ENV_FILE"
}

# Initialize services
initialize_services() {
    log_info "Initializing Docker Compose services..."
    
    cd "$PROJECT_ROOT"
    
    # Pull images
    log_info "Pulling Docker images..."
    docker-compose pull
    
    # Build application image
    log_info "Building application image..."
    docker-compose build
    
    # Start infrastructure services first
    log_info "Starting infrastructure services..."
    docker-compose up -d mysql redis vault
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Initialize database
    log_info "Initializing database..."
    docker-compose exec mysql mysql -u root -p"$(cat secrets/mysql_root_password.txt)" -e "
        CREATE DATABASE IF NOT EXISTS vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE USER IF NOT EXISTS 'vedfolnir'@'%' IDENTIFIED BY '$(cat secrets/mysql_password.txt)';
        GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'%';
        FLUSH PRIVILEGES;
    "
    
    # Start remaining services
    log_info "Starting all services..."
    docker-compose up -d
    
    log_success "Services initialized successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check service health
    local services=("mysql" "redis" "vedfolnir" "nginx" "prometheus" "grafana" "loki" "vault")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "$service is running"
        else
            log_error "$service is not running"
            return 1
        fi
    done
    
    # Test application endpoint
    log_info "Testing application endpoint..."
    sleep 10
    if curl -f -s http://localhost:80/health > /dev/null; then
        log_success "Application is responding"
    else
        log_warning "Application health check failed - this may be normal during initial startup"
    fi
    
    log_success "Deployment verification completed"
}

# Main deployment function
deploy() {
    log_info "Starting Docker Compose deployment..."
    
    check_prerequisites
    create_directory_structure
    generate_secrets
    create_environment_file
    initialize_services
    verify_deployment
    
    log_success "Docker Compose deployment completed successfully!"
    log_info "Services are available at:"
    log_info "  - Application: http://localhost:80"
    log_info "  - Grafana: http://localhost:3000"
    log_info "  - Prometheus: http://localhost:9090"
    log_info ""
    log_info "Use the following commands to manage your deployment:"
    log_info "  - View logs: docker-compose logs -f"
    log_info "  - Stop services: docker-compose down"
    log_info "  - Restart services: docker-compose restart"
    log_info "  - Update services: docker-compose pull && docker-compose up -d"
}

# Script usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --dry-run      Show what would be done without executing"
    echo "  --force        Force deployment even if services are running"
    echo ""
    echo "This script performs initial Docker Compose deployment setup."
}

# Parse command line arguments
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if services are already running
if [[ "$FORCE" != "true" ]] && docker-compose ps | grep -q "Up"; then
    log_warning "Services are already running. Use --force to redeploy."
    exit 1
fi

# Execute deployment
if [[ "$DRY_RUN" == "true" ]]; then
    log_info "DRY RUN - Would perform deployment steps"
    exit 0
else
    deploy
fi