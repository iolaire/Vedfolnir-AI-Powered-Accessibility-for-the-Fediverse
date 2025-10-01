#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Service startup coordinator for Docker Compose
# Manages service dependencies, startup order, and initialization

set -e

# Configuration
STARTUP_TIMEOUT=${SERVICE_STARTUP_TIMEOUT:-600}  # 10 minutes
CHECK_INTERVAL=${SERVICE_CHECK_INTERVAL:-5}
VERBOSE=${SERVICE_STARTUP_VERBOSE:-true}
DRY_RUN=${SERVICE_STARTUP_DRY_RUN:-false}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

stage_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${CYAN}STAGE:${NC} $1"
}

# Execute command with dry run support
execute_command() {
    local command="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = "true" ]; then
        info_log "DRY RUN: $description"
        info_log "Command: $command"
        return 0
    else
        info_log "$description"
        eval "$command"
        return $?
    fi
}

# Check if service is running
is_service_running() {
    local service_name="$1"
    docker-compose ps "$service_name" 2>/dev/null | grep -q "Up"
}

# Check if service is healthy
is_service_healthy() {
    local service_name="$1"
    local health_status
    health_status=$(docker-compose ps "$service_name" 2>/dev/null | grep "$service_name" | awk '{print $4}' || echo "unknown")
    [[ "$health_status" == *"healthy"* ]]
}

# Wait for service to be healthy
wait_for_service_health() {
    local service_name="$1"
    local timeout="$2"
    local start_time=$(date +%s)
    
    info_log "Waiting for $service_name to be healthy (timeout: ${timeout}s)..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            error_log "$service_name health check timed out after ${timeout}s"
            return 1
        fi
        
        if is_service_healthy "$service_name"; then
            success_log "$service_name is healthy (took ${elapsed}s)"
            return 0
        fi
        
        if ! is_service_running "$service_name"; then
            error_log "$service_name is not running"
            return 1
        fi
        
        log "Waiting for $service_name health... (${elapsed}s elapsed)"
        sleep $CHECK_INTERVAL
    done
}

# Start service with dependencies
start_service_with_deps() {
    local service_name="$1"
    shift
    local dependencies=("$@")
    
    info_log "Starting $service_name with dependencies: ${dependencies[*]}"
    
    # Check dependencies first
    for dep in "${dependencies[@]}"; do
        if ! is_service_healthy "$dep"; then
            error_log "Dependency $dep is not healthy, cannot start $service_name"
            return 1
        fi
    done
    
    # Start the service
    if execute_command "docker-compose up -d $service_name" "Starting $service_name"; then
        success_log "$service_name started successfully"
        return 0
    else
        error_log "Failed to start $service_name"
        return 1
    fi
}

# Stage 1: Infrastructure Services
start_infrastructure_services() {
    stage_log "Starting infrastructure services..."
    
    # Start MySQL first (critical dependency)
    if execute_command "docker-compose up -d mysql" "Starting MySQL database"; then
        if wait_for_service_health "mysql" 120; then
            success_log "MySQL is ready"
        else
            error_log "MySQL failed to become healthy"
            return 1
        fi
    else
        error_log "Failed to start MySQL"
        return 1
    fi
    
    # Start Redis (critical dependency)
    if execute_command "docker-compose up -d redis" "Starting Redis cache"; then
        if wait_for_service_health "redis" 60; then
            success_log "Redis is ready"
        else
            error_log "Redis failed to become healthy"
            return 1
        fi
    else
        error_log "Failed to start Redis"
        return 1
    fi
    
    # Start Vault (important for secrets)
    if execute_command "docker-compose up -d vault" "Starting Vault secrets manager"; then
        if wait_for_service_health "vault" 60; then
            success_log "Vault is ready"
        else
            warning_log "Vault failed to become healthy, continuing without Vault"
        fi
    else
        warning_log "Failed to start Vault, continuing without Vault"
    fi
    
    success_log "Infrastructure services startup completed"
    return 0
}

# Stage 2: Database Initialization
initialize_database() {
    stage_log "Initializing database..."
    
    if execute_command "/scripts/database-init-migration.sh init" "Running database initialization"; then
        success_log "Database initialization completed"
        return 0
    else
        error_log "Database initialization failed"
        return 1
    fi
}

# Stage 3: Application Services
start_application_services() {
    stage_log "Starting application services..."
    
    # Start Vedfolnir application (depends on MySQL and Redis)
    if start_service_with_deps "vedfolnir" "mysql" "redis"; then
        if wait_for_service_health "vedfolnir" 180; then
            success_log "Vedfolnir application is ready"
        else
            error_log "Vedfolnir application failed to become healthy"
            return 1
        fi
    else
        error_log "Failed to start Vedfolnir application"
        return 1
    fi
    
    # Start Nginx (depends on Vedfolnir)
    if start_service_with_deps "nginx" "vedfolnir"; then
        if wait_for_service_health "nginx" 60; then
            success_log "Nginx reverse proxy is ready"
        else
            error_log "Nginx failed to become healthy"
            return 1
        fi
    else
        error_log "Failed to start Nginx"
        return 1
    fi
    
    success_log "Application services startup completed"
    return 0
}

# Stage 4: Monitoring Services
start_monitoring_services() {
    stage_log "Starting monitoring services..."
    
    # Start Prometheus
    if execute_command "docker-compose up -d prometheus" "Starting Prometheus metrics collector"; then
        if wait_for_service_health "prometheus" 90; then
            success_log "Prometheus is ready"
        else
            warning_log "Prometheus failed to become healthy"
        fi
    else
        warning_log "Failed to start Prometheus"
    fi
    
    # Start Loki
    if execute_command "docker-compose up -d loki" "Starting Loki log aggregator"; then
        if wait_for_service_health "loki" 90; then
            success_log "Loki is ready"
        else
            warning_log "Loki failed to become healthy"
        fi
    else
        warning_log "Failed to start Loki"
    fi
    
    # Start Grafana (depends on Prometheus)
    if execute_command "docker-compose up -d grafana" "Starting Grafana dashboard"; then
        if wait_for_service_health "grafana" 90; then
            success_log "Grafana is ready"
        else
            warning_log "Grafana failed to become healthy"
        fi
    else
        warning_log "Failed to start Grafana"
    fi
    
    success_log "Monitoring services startup completed"
    return 0
}

# Stage 5: Metrics Exporters
start_metrics_exporters() {
    stage_log "Starting metrics exporters..."
    
    local exporters=("mysql-exporter" "redis-exporter" "nginx-exporter" "node-exporter" "cadvisor")
    
    for exporter in "${exporters[@]}"; do
        if execute_command "docker-compose up -d $exporter" "Starting $exporter"; then
            # Give exporters time to start (they don't have health checks)
            sleep 5
            if is_service_running "$exporter"; then
                success_log "$exporter is running"
            else
                warning_log "$exporter failed to start"
            fi
        else
            warning_log "Failed to start $exporter"
        fi
    done
    
    success_log "Metrics exporters startup completed"
    return 0
}

# Stage 6: External Service Validation
validate_external_services() {
    stage_log "Validating external services..."
    
    # Check Ollama API accessibility
    if curl -f -s --max-time 10 "http://host.docker.internal:11434/api/version" >/dev/null 2>&1; then
        success_log "External Ollama API is accessible"
    else
        warning_log "External Ollama API is not accessible (non-critical)"
    fi
    
    success_log "External service validation completed"
    return 0
}

# Generate startup report
generate_startup_report() {
    local services=("mysql" "redis" "vault" "vedfolnir" "nginx" "prometheus" "grafana" "loki")
    local exporters=("mysql-exporter" "redis-exporter" "nginx-exporter" "node-exporter" "cadvisor")
    
    echo ""
    echo -e "${CYAN}=== Service Startup Report ===${NC}"
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    
    echo "Core Services:"
    for service in "${services[@]}"; do
        local status="STOPPED"
        local health="N/A"
        
        if is_service_running "$service"; then
            status="RUNNING"
            if is_service_healthy "$service"; then
                health="HEALTHY"
            else
                health="UNHEALTHY"
            fi
        fi
        
        printf "  %-12s: %-8s %-10s\n" "$service" "$status" "$health"
    done
    
    echo ""
    echo "Metrics Exporters:"
    for exporter in "${exporters[@]}"; do
        local status="STOPPED"
        if is_service_running "$exporter"; then
            status="RUNNING"
        fi
        
        printf "  %-15s: %-8s\n" "$exporter" "$status"
    done
    
    echo ""
    echo -e "${CYAN}==============================${NC}"
}

# Comprehensive startup procedure
full_startup() {
    local start_time=$(date +%s)
    
    echo -e "${CYAN}=== Vedfolnir Docker Compose Startup Coordinator ===${NC}"
    echo "Start time: $(date -Iseconds)"
    echo "Timeout: ${STARTUP_TIMEOUT}s"
    echo "Dry run: $DRY_RUN"
    echo ""
    
    # Stage 1: Infrastructure
    if ! start_infrastructure_services; then
        error_log "Infrastructure services startup failed"
        return 1
    fi
    
    # Stage 2: Database initialization
    if ! initialize_database; then
        error_log "Database initialization failed"
        return 1
    fi
    
    # Stage 3: Application
    if ! start_application_services; then
        error_log "Application services startup failed"
        return 1
    fi
    
    # Stage 4: Monitoring (non-critical)
    start_monitoring_services
    
    # Stage 5: Exporters (non-critical)
    start_metrics_exporters
    
    # Stage 6: External validation
    validate_external_services
    
    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))
    
    generate_startup_report
    
    echo ""
    success_log "Vedfolnir startup completed successfully!"
    info_log "Total startup time: ${total_time}s"
    echo -e "${CYAN}================================================${NC}"
    
    return 0
}

# Quick startup (critical services only)
quick_startup() {
    info_log "Starting critical services only..."
    
    start_infrastructure_services || return 1
    initialize_database || return 1
    start_application_services || return 1
    
    success_log "Critical services startup completed"
    return 0
}

# Graceful shutdown
graceful_shutdown() {
    stage_log "Performing graceful shutdown..."
    
    local services=("nginx" "vedfolnir" "grafana" "loki" "prometheus" "vault" "redis" "mysql")
    local exporters=("cadvisor" "node-exporter" "nginx-exporter" "redis-exporter" "mysql-exporter")
    
    # Stop exporters first
    for exporter in "${exporters[@]}"; do
        if is_service_running "$exporter"; then
            execute_command "docker-compose stop $exporter" "Stopping $exporter"
        fi
    done
    
    # Stop services in reverse dependency order
    for service in "${services[@]}"; do
        if is_service_running "$service"; then
            execute_command "docker-compose stop $service" "Stopping $service"
        fi
    done
    
    success_log "Graceful shutdown completed"
}

# Main function
main() {
    local action="${1:-full}"
    
    case "$action" in
        "full")
            full_startup
            ;;
        "quick")
            quick_startup
            ;;
        "infrastructure")
            start_infrastructure_services
            ;;
        "application")
            start_application_services
            ;;
        "monitoring")
            start_monitoring_services
            ;;
        "exporters")
            start_metrics_exporters
            ;;
        "database")
            initialize_database
            ;;
        "shutdown")
            graceful_shutdown
            ;;
        "report")
            generate_startup_report
            ;;
        "dry-run")
            DRY_RUN=true
            full_startup
            ;;
        *)
            echo "Usage: $0 {full|quick|infrastructure|application|monitoring|exporters|database|shutdown|report|dry-run}"
            echo ""
            echo "Actions:"
            echo "  full           - Complete startup with all services (default)"
            echo "  quick          - Start critical services only"
            echo "  infrastructure - Start infrastructure services (MySQL, Redis, Vault)"
            echo "  application    - Start application services (Vedfolnir, Nginx)"
            echo "  monitoring     - Start monitoring services (Prometheus, Grafana, Loki)"
            echo "  exporters      - Start metrics exporters"
            echo "  database       - Initialize database only"
            echo "  shutdown       - Graceful shutdown of all services"
            echo "  report         - Generate service status report"
            echo "  dry-run        - Show what would be done without executing"
            exit 1
            ;;
    esac
}

# Handle signals for graceful shutdown
trap 'graceful_shutdown; exit 0' SIGTERM SIGINT

# Run main function
main "$@"