#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -euo pipefail

# Docker Compose Management Script
# Management scripts for common operations (start, stop, restart, logs, backup)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

# Start services
start_services() {
    log_info "Starting Docker Compose services..."
    
    if [[ "${1:-}" == "--build" ]]; then
        log_info "Building images before starting..."
        docker-compose up -d --build
    else
        docker-compose up -d
    fi
    
    log_success "Services started successfully"
    show_status
}

# Stop services
stop_services() {
    log_info "Stopping Docker Compose services..."
    
    if [[ "${1:-}" == "--remove" ]]; then
        log_info "Removing containers and networks..."
        docker-compose down --remove-orphans
    else
        docker-compose stop
    fi
    
    log_success "Services stopped successfully"
}

# Restart services
restart_services() {
    log_info "Restarting Docker Compose services..."
    
    local service="${1:-}"
    
    if [[ -n "$service" ]]; then
        log_info "Restarting service: $service"
        docker-compose restart "$service"
    else
        log_info "Restarting all services"
        docker-compose restart
    fi
    
    log_success "Services restarted successfully"
    show_status
}

# Show service status
show_status() {
    log_info "Service Status:"
    docker-compose ps
    
    echo ""
    log_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Show logs
show_logs() {
    local service="${1:-}"
    local follow="${2:-false}"
    
    if [[ -n "$service" ]]; then
        log_info "Showing logs for service: $service"
        if [[ "$follow" == "true" ]]; then
            docker-compose logs -f "$service"
        else
            docker-compose logs --tail=100 "$service"
        fi
    else
        log_info "Showing logs for all services"
        if [[ "$follow" == "true" ]]; then
            docker-compose logs -f
        else
            docker-compose logs --tail=100
        fi
    fi
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    local services=("mysql" "redis" "vedfolnir" "nginx" "prometheus" "grafana" "loki" "vault")
    local healthy=0
    local total=${#services[@]}
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "$service: Healthy"
            ((healthy++))
        else
            log_error "$service: Unhealthy"
        fi
    done
    
    echo ""
    log_info "Health Summary: $healthy/$total services healthy"
    
    # Test application endpoints
    log_info "Testing application endpoints..."
    
    if curl -f -s http://localhost:80/health > /dev/null; then
        log_success "Application health endpoint: OK"
    else
        log_error "Application health endpoint: FAILED"
    fi
    
    if curl -f -s http://localhost:3000/api/health > /dev/null 2>&1; then
        log_success "Grafana health endpoint: OK"
    else
        log_warning "Grafana health endpoint: Not accessible (may be normal)"
    fi
}

# Update services
update_services() {
    log_info "Updating Docker Compose services..."
    
    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose pull
    
    # Rebuild application image
    log_info "Rebuilding application image..."
    docker-compose build --no-cache vedfolnir
    
    # Restart services with new images
    log_info "Restarting services with updated images..."
    docker-compose up -d
    
    # Clean up old images
    log_info "Cleaning up old images..."
    docker image prune -f
    
    log_success "Services updated successfully"
    show_status
}

# Backup data
backup_data() {
    log_info "Creating backup of containerized data..."
    
    local backup_dir="$PROJECT_ROOT/storage/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup MySQL
    log_info "Backing up MySQL database..."
    docker-compose exec -T mysql mysqldump \
        --single-transaction \
        --routines \
        --triggers \
        --all-databases \
        -u root -p"$(cat secrets/mysql_root_password.txt)" | gzip > "$backup_dir/mysql_full.sql.gz"
    
    # Backup Redis
    log_info "Backing up Redis data..."
    docker-compose exec redis redis-cli BGSAVE
    sleep 5
    docker cp "$(docker-compose ps -q redis)":/data/dump.rdb "$backup_dir/redis.rdb"
    
    # Backup application data
    log_info "Backing up application data..."
    tar -czf "$backup_dir/storage.tar.gz" -C "$PROJECT_ROOT" storage/images storage/temp
    tar -czf "$backup_dir/config.tar.gz" -C "$PROJECT_ROOT" config/
    
    # Backup Vault data
    log_info "Backing up Vault data..."
    if docker-compose ps vault | grep -q "Up"; then
        docker-compose exec vault vault operator raft snapshot save /tmp/vault_snapshot
        docker cp "$(docker-compose ps -q vault)":/tmp/vault_snapshot "$backup_dir/"
    fi
    
    # Create backup manifest
    cat > "$backup_dir/manifest.txt" << EOF
Backup created: $(date)
MySQL backup: mysql_full.sql.gz
Redis backup: redis.rdb
Storage backup: storage.tar.gz
Config backup: config.tar.gz
Vault backup: vault_snapshot
EOF
    
    log_success "Backup created: $backup_dir"
}

# Restore data
restore_data() {
    local backup_dir="${1:-}"
    
    if [[ -z "$backup_dir" ]]; then
        log_error "Please specify backup directory"
        return 1
    fi
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory does not exist: $backup_dir"
        return 1
    fi
    
    log_warning "This will restore data from: $backup_dir"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        return 0
    fi
    
    log_info "Restoring data from backup..."
    
    # Stop services
    log_info "Stopping services for restore..."
    docker-compose stop
    
    # Restore MySQL
    if [[ -f "$backup_dir/mysql_full.sql.gz" ]]; then
        log_info "Restoring MySQL database..."
        docker-compose start mysql
        sleep 10
        zcat "$backup_dir/mysql_full.sql.gz" | docker-compose exec -T mysql mysql -u root -p"$(cat secrets/mysql_root_password.txt)"
    fi
    
    # Restore Redis
    if [[ -f "$backup_dir/redis.rdb" ]]; then
        log_info "Restoring Redis data..."
        docker-compose stop redis
        docker cp "$backup_dir/redis.rdb" "$(docker-compose ps -q redis)":/data/dump.rdb
        docker-compose start redis
    fi
    
    # Restore application data
    if [[ -f "$backup_dir/storage.tar.gz" ]]; then
        log_info "Restoring application data..."
        tar -xzf "$backup_dir/storage.tar.gz" -C "$PROJECT_ROOT"
    fi
    
    if [[ -f "$backup_dir/config.tar.gz" ]]; then
        log_info "Restoring configuration..."
        tar -xzf "$backup_dir/config.tar.gz" -C "$PROJECT_ROOT"
    fi
    
    # Restore Vault
    if [[ -f "$backup_dir/vault_snapshot" ]]; then
        log_info "Restoring Vault data..."
        docker-compose start vault
        sleep 10
        docker cp "$backup_dir/vault_snapshot" "$(docker-compose ps -q vault)":/tmp/vault_snapshot
        docker-compose exec vault vault operator raft snapshot restore /tmp/vault_snapshot
    fi
    
    # Start all services
    log_info "Starting all services..."
    docker-compose up -d
    
    log_success "Data restored successfully"
}

# Clean up resources
cleanup() {
    log_info "Cleaning up Docker resources..."
    
    # Remove stopped containers
    log_info "Removing stopped containers..."
    docker container prune -f
    
    # Remove unused images
    log_info "Removing unused images..."
    docker image prune -f
    
    # Remove unused volumes (with confirmation)
    read -p "Remove unused volumes? This may delete data! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    # Remove unused networks
    log_info "Removing unused networks..."
    docker network prune -f
    
    log_success "Cleanup completed"
}

# Show usage
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [--build]           Start services (optionally rebuild)"
    echo "  stop [--remove]           Stop services (optionally remove containers)"
    echo "  restart [SERVICE]         Restart services or specific service"
    echo "  status                    Show service status and resource usage"
    echo "  logs [SERVICE] [--follow] Show logs for all services or specific service"
    echo "  health                    Perform health check on all services"
    echo "  update                    Update services to latest versions"
    echo "  backup                    Create backup of all data"
    echo "  restore BACKUP_DIR        Restore data from backup directory"
    echo "  cleanup                   Clean up unused Docker resources"
    echo ""
    echo "Examples:"
    echo "  $0 start --build          Start services and rebuild images"
    echo "  $0 logs vedfolnir --follow Follow logs for vedfolnir service"
    echo "  $0 restart mysql          Restart only MySQL service"
    echo "  $0 restore storage/backups/20250101_120000"
}

# Main command handling
case "${1:-}" in
    start)
        start_services "${2:-}"
        ;;
    stop)
        stop_services "${2:-}"
        ;;
    restart)
        restart_services "${2:-}"
        ;;
    status)
        show_status
        ;;
    logs)
        if [[ "${3:-}" == "--follow" ]]; then
            show_logs "${2:-}" true
        else
            show_logs "${2:-}" false
        fi
        ;;
    health)
        health_check
        ;;
    update)
        update_services
        ;;
    backup)
        backup_data
        ;;
    restore)
        restore_data "${2:-}"
        ;;
    cleanup)
        cleanup
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