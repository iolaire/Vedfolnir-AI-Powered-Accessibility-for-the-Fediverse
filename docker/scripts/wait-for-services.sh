#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Service dependency and startup coordination script
# Waits for all required services to be healthy before starting dependent services

set -e

# Configuration
MAX_WAIT_TIME=${SERVICE_WAIT_TIMEOUT:-300}  # 5 minutes default
CHECK_INTERVAL=${SERVICE_CHECK_INTERVAL:-5}  # 5 seconds default
VERBOSE=${SERVICE_WAIT_VERBOSE:-true}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    fi
}

error_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}ERROR:${NC} $1" >&2
}

success_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}SUCCESS:${NC} $1"
}

warning_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING:${NC} $1"
}

info_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${BLUE}INFO:${NC} $1"
}

# Wait for a specific service to be healthy
wait_for_service() {
    local service_name="$1"
    local health_check_command="$2"
    local timeout="$3"
    local start_time=$(date +%s)
    
    info_log "Waiting for $service_name to be healthy..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            error_log "$service_name health check timed out after ${timeout}s"
            return 1
        fi
        
        if eval "$health_check_command" >/dev/null 2>&1; then
            success_log "$service_name is healthy (took ${elapsed}s)"
            return 0
        fi
        
        log "Waiting for $service_name... (${elapsed}s elapsed)"
        sleep $CHECK_INTERVAL
    done
}

# Check if MySQL is healthy
check_mysql_health() {
    docker-compose exec -T mysql mysqladmin ping -h localhost --silent 2>/dev/null && \
    docker-compose exec -T mysql mysql -h localhost -e 'SELECT 1' >/dev/null 2>&1
}

# Check if Redis is healthy
check_redis_health() {
    docker-compose exec -T redis redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" ping >/dev/null 2>&1 && \
    docker-compose exec -T redis redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" info replication >/dev/null 2>&1
}

# Check if Vault is healthy
check_vault_health() {
    docker-compose exec -T vault vault status >/dev/null 2>&1
}

# Check if Vedfolnir application is healthy
check_vedfolnir_health() {
    docker-compose exec -T vedfolnir curl -f -s http://localhost:5000/health >/dev/null 2>&1
}

# Check if Nginx is healthy
check_nginx_health() {
    docker-compose exec -T nginx nginx -t >/dev/null 2>&1 && \
    curl -f -s http://localhost:80 >/dev/null 2>&1
}

# Check if Prometheus is healthy
check_prometheus_health() {
    docker-compose exec -T prometheus wget --no-verbose --tries=1 --spider http://localhost:9090/-/healthy >/dev/null 2>&1
}

# Check if Grafana is healthy
check_grafana_health() {
    docker-compose exec -T grafana curl -f -s http://localhost:3000/api/health >/dev/null 2>&1
}

# Check if Loki is healthy
check_loki_health() {
    docker-compose exec -T loki wget --no-verbose --tries=1 --spider http://localhost:3100/ready >/dev/null 2>&1
}

# Check if external Ollama is accessible
check_ollama_health() {
    curl -f -s --max-time 10 http://host.docker.internal:11434/api/version >/dev/null 2>&1
}

# Wait for core infrastructure services
wait_for_infrastructure() {
    info_log "Waiting for core infrastructure services..."
    
    # MySQL - Critical dependency
    wait_for_service "MySQL" "check_mysql_health" 120 || return 1
    
    # Redis - Critical dependency
    wait_for_service "Redis" "check_redis_health" 60 || return 1
    
    # Vault - Important for secrets
    wait_for_service "Vault" "check_vault_health" 60 || {
        warning_log "Vault health check failed, continuing without Vault"
    }
    
    success_log "Core infrastructure services are ready"
    return 0
}

# Wait for application services
wait_for_application() {
    info_log "Waiting for application services..."
    
    # Vedfolnir application - Critical
    wait_for_service "Vedfolnir Application" "check_vedfolnir_health" 180 || return 1
    
    # Nginx - Critical for external access
    wait_for_service "Nginx" "check_nginx_health" 60 || return 1
    
    success_log "Application services are ready"
    return 0
}

# Wait for monitoring services
wait_for_monitoring() {
    info_log "Waiting for monitoring services..."
    
    # Prometheus - Important for monitoring
    wait_for_service "Prometheus" "check_prometheus_health" 90 || {
        warning_log "Prometheus health check failed, continuing without Prometheus"
    }
    
    # Grafana - Important for dashboards
    wait_for_service "Grafana" "check_grafana_health" 90 || {
        warning_log "Grafana health check failed, continuing without Grafana"
    }
    
    # Loki - Important for log aggregation
    wait_for_service "Loki" "check_loki_health" 90 || {
        warning_log "Loki health check failed, continuing without Loki"
    }
    
    success_log "Monitoring services startup completed"
    return 0
}

# Wait for external services
wait_for_external() {
    info_log "Checking external services..."
    
    # Ollama - External service, non-critical
    if check_ollama_health; then
        success_log "External Ollama API is accessible"
    else
        warning_log "External Ollama API is not accessible (non-critical)"
    fi
    
    return 0
}

# Perform database initialization if needed
initialize_database() {
    info_log "Checking database initialization..."
    
    # Check if database needs initialization
    if docker-compose exec -T vedfolnir python -c "
import sys
sys.path.insert(0, '/app')
try:
    from config import Config
    from app.core.database.core.database_manager import DatabaseManager
    from sqlalchemy import text
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        result = session.execute(text('SHOW TABLES')).fetchall()
        if len(result) == 0:
            print('Database needs initialization')
            sys.exit(1)
        else:
            print('Database already initialized')
            sys.exit(0)
except Exception as e:
    print(f'Database check failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        success_log "Database is already initialized"
    else
        info_log "Initializing database..."
        
        # Run database initialization
        if docker-compose exec -T vedfolnir python -c "
import sys
sys.path.insert(0, '/app')
try:
    from config import Config
    from app.core.database.core.database_manager import DatabaseManager
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Initialize database schema
    db_manager.initialize_database()
    print('Database initialization completed')
    sys.exit(0)
except Exception as e:
    print(f'Database initialization failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
            success_log "Database initialization completed"
        else
            error_log "Database initialization failed"
            return 1
        fi
    fi
    
    return 0
}

# Main function
main() {
    local start_time=$(date +%s)
    
    echo -e "${BLUE}=== Docker Compose Service Dependency Manager ===${NC}"
    echo "Start time: $(date -Iseconds)"
    echo "Max wait time: ${MAX_WAIT_TIME}s"
    echo "Check interval: ${CHECK_INTERVAL}s"
    echo ""
    
    # Wait for services in dependency order
    if ! wait_for_infrastructure; then
        error_log "Infrastructure services failed to start"
        exit 1
    fi
    
    # Initialize database if needed
    if ! initialize_database; then
        error_log "Database initialization failed"
        exit 1
    fi
    
    if ! wait_for_application; then
        error_log "Application services failed to start"
        exit 1
    fi
    
    # Monitoring services are non-critical
    wait_for_monitoring
    
    # External services check
    wait_for_external
    
    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))
    
    echo ""
    success_log "All services are ready!"
    echo -e "${BLUE}Total startup time: ${total_time}s${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    return 0
}

# Handle script arguments
case "${1:-}" in
    "infrastructure")
        wait_for_infrastructure
        ;;
    "application")
        wait_for_application
        ;;
    "monitoring")
        wait_for_monitoring
        ;;
    "external")
        wait_for_external
        ;;
    "database")
        initialize_database
        ;;
    "quick")
        # Quick check - only critical services
        wait_for_infrastructure && wait_for_application
        ;;
    *)
        # Default comprehensive startup
        main
        ;;
esac