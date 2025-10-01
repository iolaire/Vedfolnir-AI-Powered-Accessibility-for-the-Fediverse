#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -euo pipefail

# Docker Compose Update and Maintenance Scripts
# Update and maintenance scripts for container management

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

# Update all services
update_all() {
    log_info "Starting comprehensive system update..."
    
    # Create backup before update
    log_info "Creating pre-update backup..."
    "$SCRIPT_DIR/backup.sh" backup full "pre_update_$(date +%Y%m%d_%H%M%S)"
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose pull
    
    # Rebuild application image
    log_info "Rebuilding application image..."
    docker-compose build --no-cache vedfolnir
    
    # Update services with rolling restart
    rolling_update
    
    # Clean up old images
    log_info "Cleaning up old images..."
    docker image prune -f
    
    # Verify update
    verify_update
    
    log_success "System update completed successfully"
}

# Rolling update to minimize downtime
rolling_update() {
    log_info "Performing rolling update..."
    
    local services=("mysql" "redis" "vault" "vedfolnir" "nginx" "prometheus" "grafana" "loki")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_info "Updating service: $service"
            
            # Graceful restart
            docker-compose stop "$service"
            docker-compose up -d "$service"
            
            # Wait for service to be ready
            wait_for_service "$service"
            
            log_success "Service $service updated successfully"
        else
            log_warning "Service $service is not running, skipping"
        fi
    done
}

# Wait for service to be ready
wait_for_service() {
    local service="$1"
    local timeout=60
    local elapsed=0
    
    log_info "Waiting for $service to be ready..."
    
    while [[ $elapsed -lt $timeout ]]; do
        if docker-compose ps "$service" | grep -q "Up"; then
            case "$service" in
                mysql)
                    if docker-compose exec mysql mysqladmin ping -h localhost --silent; then
                        return 0
                    fi
                    ;;
                redis)
                    if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
                        return 0
                    fi
                    ;;
                vedfolnir)
                    if curl -f -s http://localhost:80/health > /dev/null 2>&1; then
                        return 0
                    fi
                    ;;
                nginx)
                    if curl -f -s http://localhost:80 > /dev/null 2>&1; then
                        return 0
                    fi
                    ;;
                *)
                    # For other services, just check if container is up
                    return 0
                    ;;
            esac
        fi
        
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    log_warning "Service $service may not be fully ready (timeout reached)"
    return 1
}

# Verify update
verify_update() {
    log_info "Verifying system update..."
    
    # Check service health
    local services=("mysql" "redis" "vedfolnir" "nginx")
    local healthy=0
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "$service: Running"
            ((healthy++))
        else
            log_error "$service: Not running"
        fi
    done
    
    # Test application endpoints
    if curl -f -s http://localhost:80/health > /dev/null; then
        log_success "Application health check: PASSED"
    else
        log_error "Application health check: FAILED"
    fi
    
    if [[ $healthy -eq ${#services[@]} ]]; then
        log_success "Update verification passed"
    else
        log_error "Update verification failed - some services are not running"
        return 1
    fi
}

# System maintenance
system_maintenance() {
    log_info "Starting system maintenance..."
    
    # Clean up Docker resources
    cleanup_docker_resources
    
    # Rotate logs
    rotate_logs
    
    # Clean up old backups
    "$SCRIPT_DIR/backup.sh" cleanup
    
    # Update system packages in containers (if needed)
    update_container_packages
    
    # Optimize database
    optimize_database
    
    # Check disk space
    check_disk_space
    
    log_success "System maintenance completed"
}

# Clean up Docker resources
cleanup_docker_resources() {
    log_info "Cleaning up Docker resources..."
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused networks
    docker network prune -f
    
    # Remove build cache
    docker builder prune -f
    
    log_success "Docker cleanup completed"
}

# Rotate logs
rotate_logs() {
    log_info "Rotating logs..."
    
    local log_dirs=("logs/app" "logs/nginx" "logs/mysql" "logs/redis" "logs/vault" "logs/audit")
    
    for log_dir in "${log_dirs[@]}"; do
        if [[ -d "$PROJECT_ROOT/$log_dir" ]]; then
            # Compress logs older than 7 days
            find "$PROJECT_ROOT/$log_dir" -name "*.log" -mtime +7 -exec gzip {} \;
            
            # Remove compressed logs older than 30 days
            find "$PROJECT_ROOT/$log_dir" -name "*.log.gz" -mtime +30 -delete
            
            log_info "Rotated logs in $log_dir"
        fi
    done
    
    # Restart services to reopen log files
    docker-compose restart
    
    log_success "Log rotation completed"
}

# Update container packages
update_container_packages() {
    log_info "Updating container packages..."
    
    # Update packages in application container
    if docker-compose ps vedfolnir | grep -q "Up"; then
        docker-compose exec vedfolnir apt-get update
        docker-compose exec vedfolnir apt-get upgrade -y
        log_success "Application container packages updated"
    fi
    
    # Note: Other containers use official images that should be updated via image pulls
}

# Optimize database
optimize_database() {
    log_info "Optimizing database..."
    
    if ! docker-compose ps mysql | grep -q "Up"; then
        log_warning "MySQL service is not running, skipping database optimization"
        return 0
    fi
    
    # Analyze and optimize tables
    docker-compose exec mysql mysql -u root -p"$(cat secrets/mysql_root_password.txt)" -e "
        USE vedfolnir;
        ANALYZE TABLE users, platform_connections, posts, images, processing_runs, user_sessions;
        OPTIMIZE TABLE users, platform_connections, posts, images, processing_runs, user_sessions;
    "
    
    log_success "Database optimization completed"
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space..."
    
    local threshold=80
    local usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $usage -gt $threshold ]]; then
        log_warning "Disk usage is high: ${usage}%"
        
        # Show largest directories
        log_info "Largest directories:"
        du -sh "$PROJECT_ROOT"/* | sort -hr | head -10
        
        # Suggest cleanup
        log_info "Consider running cleanup commands or expanding storage"
    else
        log_success "Disk usage is acceptable: ${usage}%"
    fi
}

# Security updates
security_update() {
    log_info "Performing security updates..."
    
    # Update base images
    log_info "Pulling latest base images..."
    docker pull python:3.12-slim
    docker pull mysql:8.0
    docker pull redis:7-alpine
    docker pull nginx:alpine
    docker pull prom/prometheus:latest
    docker pull grafana/grafana:latest
    docker pull grafana/loki:latest
    docker pull vault:latest
    
    # Rebuild application with latest base image
    log_info "Rebuilding application with latest base image..."
    docker-compose build --no-cache --pull vedfolnir
    
    # Update container packages
    update_container_packages
    
    # Restart services with new images
    log_info "Restarting services with updated images..."
    docker-compose up -d
    
    # Verify security update
    verify_update
    
    log_success "Security updates completed"
}

# Performance tuning
performance_tuning() {
    log_info "Performing performance tuning..."
    
    # Optimize MySQL configuration
    if docker-compose ps mysql | grep -q "Up"; then
        log_info "Optimizing MySQL configuration..."
        
        # Update MySQL configuration for better performance
        cat > "$PROJECT_ROOT/config/mysql/performance.cnf" << 'EOF'
[mysqld]
# Performance optimizations
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT
query_cache_type = 1
query_cache_size = 128M
max_connections = 200
thread_cache_size = 16
table_open_cache = 2000
EOF
        
        # Restart MySQL to apply changes
        docker-compose restart mysql
        wait_for_service mysql
    fi
    
    # Optimize Redis configuration
    if docker-compose ps redis | grep -q "Up"; then
        log_info "Optimizing Redis configuration..."
        
        # Update Redis configuration for better performance
        cat > "$PROJECT_ROOT/config/redis/performance.conf" << 'EOF'
# Performance optimizations
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
save 900 1
save 300 10
save 60 10000
EOF
        
        # Restart Redis to apply changes
        docker-compose restart redis
        wait_for_service redis
    fi
    
    log_success "Performance tuning completed"
}

# Health monitoring
health_monitoring() {
    log_info "Performing health monitoring..."
    
    # Check service health
    local services=("mysql" "redis" "vedfolnir" "nginx" "prometheus" "grafana" "loki" "vault")
    local issues=0
    
    for service in "${services[@]}"; do
        if ! docker-compose ps "$service" | grep -q "Up"; then
            log_error "$service is not running"
            ((issues++))
        fi
    done
    
    # Check resource usage
    log_info "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    # Check application health
    if curl -f -s http://localhost:80/health > /dev/null; then
        log_success "Application health check: PASSED"
    else
        log_error "Application health check: FAILED"
        ((issues++))
    fi
    
    # Check database connectivity
    if docker-compose exec mysql mysqladmin ping -h localhost --silent; then
        log_success "Database connectivity: OK"
    else
        log_error "Database connectivity: FAILED"
        ((issues++))
    fi
    
    # Check Redis connectivity
    if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis connectivity: OK"
    else
        log_error "Redis connectivity: FAILED"
        ((issues++))
    fi
    
    if [[ $issues -eq 0 ]]; then
        log_success "Health monitoring: All systems healthy"
    else
        log_warning "Health monitoring: $issues issues detected"
    fi
    
    return $issues
}

# Emergency recovery
emergency_recovery() {
    log_warning "Starting emergency recovery procedure..."
    
    # Stop all services
    log_info "Stopping all services..."
    docker-compose down
    
    # Find latest backup
    local latest_backup=$(find "$PROJECT_ROOT/storage/backups" -maxdepth 1 -type d -name "*_*" | sort | tail -1)
    
    if [[ -z "$latest_backup" ]]; then
        log_error "No backups found for emergency recovery"
        return 1
    fi
    
    log_info "Using backup: $latest_backup"
    
    # Restore from latest backup
    "$SCRIPT_DIR/backup.sh" restore "$latest_backup"
    
    # Verify recovery
    if health_monitoring; then
        log_success "Emergency recovery completed successfully"
    else
        log_error "Emergency recovery failed - manual intervention required"
        return 1
    fi
}

# Show usage
usage() {
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  update                    Update all services and images"
    echo "  maintenance               Perform system maintenance"
    echo "  security                  Perform security updates"
    echo "  performance               Optimize system performance"
    echo "  health                    Check system health"
    echo "  recovery                  Emergency recovery from latest backup"
    echo ""
    echo "Examples:"
    echo "  $0 update                 Update all services"
    echo "  $0 maintenance            Run maintenance tasks"
    echo "  $0 health                 Check system health"
}

# Main command handling
case "${1:-}" in
    update)
        update_all
        ;;
    maintenance)
        system_maintenance
        ;;
    security)
        security_update
        ;;
    performance)
        performance_tuning
        ;;
    health)
        health_monitoring
        ;;
    recovery)
        emergency_recovery
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