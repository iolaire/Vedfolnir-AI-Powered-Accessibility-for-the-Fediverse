#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vedfolnir Docker Compose Management Script
# Provides convenient commands for managing the Docker Compose deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
DEV_COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env"
SECRETS_DIR="secrets"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found. Creating from .env.docker template..."
        if [ -f ".env.docker" ]; then
            cp .env.docker .env
            log_info "Please edit .env file with your configuration before continuing."
            exit 1
        else
            log_error ".env.docker template not found. Please create .env file manually."
            exit 1
        fi
    fi
    
    # Check if secrets directory exists
    if [ ! -d "$SECRETS_DIR" ]; then
        log_warning "Secrets directory not found. Run 'generate-secrets' command first."
    fi
    
    log_success "Prerequisites check passed"
}

generate_secrets() {
    log_info "Generating Docker secrets..."
    
    if [ ! -f "scripts/setup/generate_docker_secrets.py" ]; then
        log_error "Secret generation script not found."
        exit 1
    fi
    
    python3 scripts/setup/generate_docker_secrets.py
    
    log_success "Secrets generated successfully"
    log_info "Please update your .env file with the generated values"
}

start_services() {
    local mode="$1"
    
    check_prerequisites
    
    if [ "$mode" = "dev" ]; then
        log_info "Starting services in development mode..."
        docker-compose -f "$COMPOSE_FILE" -f "$DEV_COMPOSE_FILE" up -d
    else
        log_info "Starting services in production mode..."
        docker-compose up -d
    fi
    
    log_success "Services started successfully"
    
    # Wait a moment for services to initialize
    sleep 5
    
    # Show service status
    show_status
}

stop_services() {
    log_info "Stopping services..."
    docker-compose down
    log_success "Services stopped successfully"
}

restart_services() {
    local mode="$1"
    
    log_info "Restarting services..."
    stop_services
    start_services "$mode"
}

show_status() {
    log_info "Service status:"
    docker-compose ps
    
    echo
    log_info "Service health:"
    
    # Check individual service health
    services=("mysql" "redis" "ollama" "vault" "vedfolnir" "nginx" "prometheus" "grafana" "loki")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            if docker-compose exec -T "$service" echo "OK" &> /dev/null; then
                log_success "$service: Running and accessible"
            else
                log_warning "$service: Running but not accessible"
            fi
        else
            log_error "$service: Not running"
        fi
    done
}

show_logs() {
    local service="$1"
    local follow="$2"
    
    if [ -z "$service" ]; then
        if [ "$follow" = "-f" ]; then
            docker-compose logs -f
        else
            docker-compose logs --tail=50
        fi
    else
        if [ "$follow" = "-f" ]; then
            docker-compose logs -f "$service"
        else
            docker-compose logs --tail=50 "$service"
        fi
    fi
}

validate_networking() {
    log_info "Validating Docker networking..."
    
    if [ ! -f "scripts/setup/validate_docker_networking.py" ]; then
        log_error "Network validation script not found."
        exit 1
    fi
    
    # Set Docker deployment flag for validation
    export DOCKER_DEPLOYMENT=true
    
    python3 scripts/setup/validate_docker_networking.py
}

backup_data() {
    local backup_dir="storage/backups/docker/$(date +%Y%m%d_%H%M%S)"
    
    log_info "Creating backup in $backup_dir..."
    
    mkdir -p "$backup_dir"
    
    # Backup MySQL data
    log_info "Backing up MySQL data..."
    docker-compose exec -T mysql mysqldump --all-databases --single-transaction --routines --triggers | gzip > "$backup_dir/mysql_backup.sql.gz"
    
    # Backup Redis data
    log_info "Backing up Redis data..."
    docker-compose exec -T redis redis-cli BGSAVE
    sleep 2
    docker cp "$(docker-compose ps -q redis):/data/dump.rdb" "$backup_dir/redis_backup.rdb"
    
    # Backup application data
    log_info "Backing up application data..."
    tar -czf "$backup_dir/storage_backup.tar.gz" storage/ --exclude="storage/backups"
    
    # Backup configuration
    log_info "Backing up configuration..."
    tar -czf "$backup_dir/config_backup.tar.gz" config/ .env docker-compose.yml
    
    log_success "Backup completed: $backup_dir"
}

update_containers() {
    log_info "Updating containers..."
    
    # Pull latest images
    docker-compose pull
    
    # Rebuild and restart services
    docker-compose up -d --build
    
    log_success "Containers updated successfully"
}

cleanup_resources() {
    log_info "Cleaning up Docker resources..."
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful with this)
    read -p "Remove unused volumes? This may delete data! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    # Remove unused networks
    docker network prune -f
    
    log_success "Cleanup completed"
}

show_help() {
    echo "Vedfolnir Docker Compose Management Script"
    echo
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  generate-secrets    Generate Docker secrets"
    echo "  start [dev]         Start services (add 'dev' for development mode)"
    echo "  stop               Stop services"
    echo "  restart [dev]      Restart services (add 'dev' for development mode)"
    echo "  status             Show service status"
    echo "  logs [service] [-f] Show logs (optionally for specific service, -f to follow)"
    echo "  validate           Validate Docker networking configuration"
    echo "  backup             Create backup of all data"
    echo "  update             Update containers to latest versions"
    echo "  cleanup            Clean up unused Docker resources"
    echo "  help               Show this help message"
    echo
    echo "Examples:"
    echo "  $0 generate-secrets"
    echo "  $0 start"
    echo "  $0 start dev"
    echo "  $0 logs vedfolnir -f"
    echo "  $0 validate"
    echo "  $0 backup"
}

# Main script logic
case "$1" in
    "generate-secrets")
        generate_secrets
        ;;
    "start")
        start_services "$2"
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services "$2"
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "$2" "$3"
        ;;
    "validate")
        validate_networking
        ;;
    "backup")
        backup_data
        ;;
    "update")
        update_containers
        ;;
    "cleanup")
        cleanup_resources
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac