#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Production Environment Deployment Script for Vedfolnir Docker Compose

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="backups/pre-deployment"

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

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking production prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check available disk space (minimum 10GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 10485760 ]]; then  # 10GB in KB
        log_warning "Less than 10GB disk space available"
    fi
    
    # Check available memory (minimum 4GB)
    available_memory=$(free -m | awk 'NR==2{print $7}')
    if [[ $available_memory -lt 4096 ]]; then
        log_warning "Less than 4GB memory available"
    fi
    
    log_success "Prerequisites check passed"
}

# Function to validate secrets
validate_secrets() {
    log_info "Validating production secrets..."
    
    local secrets_dir="secrets"
    local required_secrets=(
        "flask_secret_key.txt"
        "platform_encryption_key.txt"
        "mysql_root_password.txt"
        "mysql_password.txt"
        "redis_password.txt"
        "vault_token.txt"
        "grafana_admin_password.txt"
    )
    
    for secret in "${required_secrets[@]}"; do
        if [[ ! -f "$secrets_dir/$secret" ]]; then
            log_error "Required secret file missing: $secrets_dir/$secret"
            exit 1
        fi
        
        # Check if secret file is not empty
        if [[ ! -s "$secrets_dir/$secret" ]]; then
            log_error "Secret file is empty: $secrets_dir/$secret"
            exit 1
        fi
    done
    
    log_success "All required secrets are present"
}

# Function to create backup
create_backup() {
    log_info "Creating pre-deployment backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup current data if services are running
    if docker-compose $COMPOSE_FILES ps | grep -q "Up"; then
        # Backup MySQL
        if docker-compose $COMPOSE_FILES ps mysql | grep -q "Up"; then
            log_info "Backing up MySQL database..."
            docker-compose $COMPOSE_FILES exec -T mysql mysqldump --all-databases --single-transaction --routines --triggers | gzip > "$backup_path/mysql_backup.sql.gz"
        fi
        
        # Backup Redis
        if docker-compose $COMPOSE_FILES ps redis | grep -q "Up"; then
            log_info "Backing up Redis data..."
            docker-compose $COMPOSE_FILES exec -T redis redis-cli BGSAVE
            sleep 5
            docker cp $(docker-compose $COMPOSE_FILES ps -q redis):/data/dump.rdb "$backup_path/redis_backup.rdb"
        fi
    fi
    
    # Backup configuration files
    tar -czf "$backup_path/config_backup.tar.gz" config/ || true
    tar -czf "$backup_path/secrets_backup.tar.gz" secrets/ || true
    
    log_success "Backup created at $backup_path"
}

# Function to setup production environment
setup_production_environment() {
    log_info "Setting up production environment..."
    
    cd "$PROJECT_ROOT"
    
    # Copy environment file if it doesn't exist
    if [[ ! -f .env ]]; then
        if [[ -f "$ENV_FILE" ]]; then
            cp "$ENV_FILE" .env
            log_success "Copied $ENV_FILE to .env"
        else
            log_error "Environment file $ENV_FILE not found"
            exit 1
        fi
    fi
    
    # Validate environment variables
    source .env
    
    if [[ -z "$MYSQL_PASSWORD" ]]; then
        log_error "MYSQL_PASSWORD not set in environment"
        exit 1
    fi
    
    if [[ -z "$REDIS_PASSWORD" ]]; then
        log_error "REDIS_PASSWORD not set in environment"
        exit 1
    fi
    
    # Create necessary directories with proper permissions
    mkdir -p {data/{mysql,redis,prometheus,grafana,loki,vault},logs/{app,nginx,mysql,redis,vault,audit},storage/{images,backups,temp},config}
    
    # Set secure permissions for production
    chmod 700 secrets/
    chmod 600 secrets/*
    chmod 755 data/
    chmod 755 logs/
    chmod 755 storage/
    
    log_success "Production environment setup completed"
}

# Function to build production images
build_production_images() {
    log_info "Building production Docker images..."
    
    # Build with production target
    docker-compose $COMPOSE_FILES build --parallel --no-cache
    
    # Tag images for production
    local image_tag="vedfolnir:production-$(date +%Y%m%d_%H%M%S)"
    docker tag vedfolnir_vedfolnir "$image_tag"
    
    log_success "Production Docker images built successfully"
}

# Function to perform rolling deployment
rolling_deployment() {
    log_info "Performing rolling deployment..."
    
    # Start infrastructure services first
    docker-compose $COMPOSE_FILES up -d mysql redis vault
    
    # Wait for infrastructure to be ready
    log_info "Waiting for infrastructure services..."
    timeout 120 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec mysql mysqladmin ping -h localhost --silent; do sleep 5; done'
    timeout 60 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec redis redis-cli ping | grep -q PONG; do sleep 2; done'
    timeout 60 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec vault vault status; do sleep 5; done'
    
    # Start monitoring services
    docker-compose $COMPOSE_FILES up -d prometheus loki grafana
    
    # Wait for monitoring to be ready
    log_info "Waiting for monitoring services..."
    sleep 30
    
    # Start application with rolling update
    docker-compose $COMPOSE_FILES up -d --scale vedfolnir=2 vedfolnir
    
    # Wait for application to be ready
    log_info "Waiting for application to be ready..."
    timeout 180 bash -c 'until curl -f http://localhost:5000/health &>/dev/null; do sleep 10; done'
    
    # Start reverse proxy
    docker-compose $COMPOSE_FILES up -d nginx
    
    # Final health check
    timeout 60 bash -c 'until curl -f http://localhost/health &>/dev/null; do sleep 5; done'
    
    log_success "Rolling deployment completed successfully"
}

# Function to run production health checks
run_health_checks() {
    log_info "Running production health checks..."
    
    local health_checks=(
        "http://localhost/health"
        "http://localhost:3000/api/health"  # Grafana
    )
    
    for endpoint in "${health_checks[@]}"; do
        if curl -f "$endpoint" &>/dev/null; then
            log_success "Health check passed: $endpoint"
        else
            log_error "Health check failed: $endpoint"
            return 1
        fi
    done
    
    # Check service status
    local failed_services=$(docker-compose $COMPOSE_FILES ps --services --filter "status=exited")
    if [[ -n "$failed_services" ]]; then
        log_error "Failed services detected: $failed_services"
        return 1
    fi
    
    log_success "All health checks passed"
}

# Function to show production status
show_production_status() {
    log_info "Production deployment status:"
    docker-compose $COMPOSE_FILES ps
    
    echo ""
    log_info "Service URLs:"
    echo "  Application: https://your-domain.com"
    echo "  Admin: https://your-domain.com/admin"
    echo "  API: https://your-domain.com/api"
    echo "  Grafana: http://localhost:3000"
    
    echo ""
    log_info "Monitoring commands:"
    echo "  View logs: docker-compose $COMPOSE_FILES logs -f [service]"
    echo "  Service status: docker-compose $COMPOSE_FILES ps"
    echo "  Resource usage: docker stats"
    echo "  System health: curl -f http://localhost/health"
}

# Function to rollback deployment
rollback_deployment() {
    log_error "Rolling back deployment..."
    
    # Stop current services
    docker-compose $COMPOSE_FILES down
    
    # Restore from backup if available
    local latest_backup=$(ls -t "$BACKUP_DIR" | head -n1)
    if [[ -n "$latest_backup" ]]; then
        log_info "Restoring from backup: $latest_backup"
        
        # Restore MySQL
        if [[ -f "$BACKUP_DIR/$latest_backup/mysql_backup.sql.gz" ]]; then
            docker-compose $COMPOSE_FILES up -d mysql
            sleep 30
            zcat "$BACKUP_DIR/$latest_backup/mysql_backup.sql.gz" | docker-compose $COMPOSE_FILES exec -T mysql mysql
        fi
        
        # Restore Redis
        if [[ -f "$BACKUP_DIR/$latest_backup/redis_backup.rdb" ]]; then
            docker cp "$BACKUP_DIR/$latest_backup/redis_backup.rdb" $(docker-compose $COMPOSE_FILES ps -q redis):/data/dump.rdb
            docker-compose $COMPOSE_FILES restart redis
        fi
    fi
    
    log_success "Rollback completed"
}

# Function to show help
show_help() {
    echo "Production Environment Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --build-only      Build images only, don't deploy"
    echo "  --no-build        Skip building images"
    echo "  --no-backup       Skip creating backup"
    echo "  --health-check    Run health checks only"
    echo "  --status          Show production status"
    echo "  --rollback        Rollback to previous deployment"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Full production deployment"
    echo "  $0 --build-only         # Build production images only"
    echo "  $0 --no-backup          # Deploy without backup"
    echo "  $0 --health-check       # Run health checks"
    echo "  $0 --rollback           # Rollback deployment"
}

# Main execution
main() {
    local build_only=false
    local no_build=false
    local no_backup=false
    local health_check_only=false
    local status_only=false
    local rollback=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                build_only=true
                shift
                ;;
            --no-build)
                no_build=true
                shift
                ;;
            --no-backup)
                no_backup=true
                shift
                ;;
            --health-check)
                health_check_only=true
                shift
                ;;
            --status)
                status_only=true
                shift
                ;;
            --rollback)
                rollback=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    if [[ "$status_only" == true ]]; then
        show_production_status
        exit 0
    fi
    
    if [[ "$health_check_only" == true ]]; then
        run_health_checks
        exit $?
    fi
    
    if [[ "$rollback" == true ]]; then
        rollback_deployment
        exit 0
    fi
    
    # Execute deployment steps
    check_prerequisites
    validate_secrets
    
    if [[ "$no_backup" != true ]]; then
        create_backup
    fi
    
    setup_production_environment
    
    if [[ "$no_build" != true ]]; then
        build_production_images
    fi
    
    if [[ "$build_only" != true ]]; then
        # Set up error handling for rollback
        trap 'rollback_deployment' ERR
        
        rolling_deployment
        run_health_checks
        show_production_status
        
        # Remove error trap on success
        trap - ERR
    fi
    
    log_success "Production deployment completed successfully!"
}

# Run main function with all arguments
main "$@"