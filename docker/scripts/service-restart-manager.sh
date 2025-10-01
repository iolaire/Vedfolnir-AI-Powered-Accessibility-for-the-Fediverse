#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Service restart policy and failure handling manager
# Handles service failures, restarts, and recovery procedures

set -e

# Configuration
RESTART_ATTEMPTS=${SERVICE_RESTART_ATTEMPTS:-3}
RESTART_DELAY=${SERVICE_RESTART_DELAY:-10}
HEALTH_CHECK_TIMEOUT=${SERVICE_HEALTH_TIMEOUT:-30}
LOG_FILE=${SERVICE_RESTART_LOG:-"/app/logs/service-restart.log"}
VERBOSE=${SERVICE_RESTART_VERBOSE:-true}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    if [ "$VERBOSE" = "true" ]; then
        echo -e "$message"
    fi
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

error_log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo -e "${RED}$message${NC}" >&2
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

success_log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1"
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${GREEN}$message${NC}"
    fi
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

warning_log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1"
    echo -e "${YELLOW}$message${NC}"
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

info_log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${BLUE}$message${NC}"
    fi
    echo "$message" >> "$LOG_FILE" 2>/dev/null || true
}

# Check if a service is running
is_service_running() {
    local service_name="$1"
    docker-compose ps "$service_name" | grep -q "Up" 2>/dev/null
}

# Check if a service is healthy
is_service_healthy() {
    local service_name="$1"
    
    case "$service_name" in
        "mysql")
            docker-compose exec -T mysql mysqladmin ping -h localhost --silent >/dev/null 2>&1
            ;;
        "redis")
            docker-compose exec -T redis redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" ping >/dev/null 2>&1
            ;;
        "vault")
            docker-compose exec -T vault vault status >/dev/null 2>&1
            ;;
        "vedfolnir")
            docker-compose exec -T vedfolnir curl -f -s http://localhost:5000/health >/dev/null 2>&1
            ;;
        "nginx")
            docker-compose exec -T nginx nginx -t >/dev/null 2>&1
            ;;
        "prometheus")
            docker-compose exec -T prometheus wget --no-verbose --tries=1 --spider http://localhost:9090/-/healthy >/dev/null 2>&1
            ;;
        "grafana")
            docker-compose exec -T grafana curl -f -s http://localhost:3000/api/health >/dev/null 2>&1
            ;;
        "loki")
            docker-compose exec -T loki wget --no-verbose --tries=1 --spider http://localhost:3100/ready >/dev/null 2>&1
            ;;
        *)
            warning_log "Unknown service: $service_name"
            return 1
            ;;
    esac
}

# Get service status
get_service_status() {
    local service_name="$1"
    
    if is_service_running "$service_name"; then
        if is_service_healthy "$service_name"; then
            echo "healthy"
        else
            echo "unhealthy"
        fi
    else
        echo "stopped"
    fi
}

# Restart a service
restart_service() {
    local service_name="$1"
    local attempt="$2"
    
    info_log "Restarting $service_name (attempt $attempt/$RESTART_ATTEMPTS)"
    
    # Stop the service gracefully
    if docker-compose stop "$service_name" >/dev/null 2>&1; then
        info_log "$service_name stopped gracefully"
    else
        warning_log "$service_name did not stop gracefully, forcing stop"
        docker-compose kill "$service_name" >/dev/null 2>&1 || true
    fi
    
    # Wait for restart delay
    if [ "$RESTART_DELAY" -gt 0 ]; then
        info_log "Waiting ${RESTART_DELAY}s before restarting $service_name"
        sleep "$RESTART_DELAY"
    fi
    
    # Start the service
    if docker-compose up -d "$service_name" >/dev/null 2>&1; then
        info_log "$service_name started"
        
        # Wait for service to become healthy
        local wait_time=0
        while [ $wait_time -lt $HEALTH_CHECK_TIMEOUT ]; do
            if is_service_healthy "$service_name"; then
                success_log "$service_name is healthy after restart"
                return 0
            fi
            
            sleep 5
            wait_time=$((wait_time + 5))
            info_log "Waiting for $service_name to become healthy... (${wait_time}s)"
        done
        
        error_log "$service_name failed to become healthy after restart"
        return 1
    else
        error_log "Failed to start $service_name"
        return 1
    fi
}

# Handle service failure
handle_service_failure() {
    local service_name="$1"
    local failure_reason="$2"
    
    error_log "Service failure detected: $service_name ($failure_reason)"
    
    # Check if service has dependent services
    local dependent_services=""
    case "$service_name" in
        "mysql")
            dependent_services="vedfolnir"
            ;;
        "redis")
            dependent_services="vedfolnir"
            ;;
        "vedfolnir")
            dependent_services="nginx"
            ;;
        "vault")
            dependent_services=""  # Non-critical
            ;;
    esac
    
    # Attempt to restart the service
    local attempt=1
    while [ $attempt -le $RESTART_ATTEMPTS ]; do
        if restart_service "$service_name" "$attempt"; then
            success_log "$service_name successfully restarted"
            
            # Restart dependent services if needed
            if [ -n "$dependent_services" ]; then
                for dep_service in $dependent_services; do
                    if ! is_service_healthy "$dep_service"; then
                        warning_log "Dependent service $dep_service is unhealthy, restarting"
                        restart_service "$dep_service" 1
                    fi
                done
            fi
            
            return 0
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -le $RESTART_ATTEMPTS ]; then
            warning_log "Restart attempt $((attempt - 1)) failed, trying again"
        fi
    done
    
    error_log "$service_name failed to restart after $RESTART_ATTEMPTS attempts"
    
    # Send alert or notification (placeholder for future implementation)
    send_failure_alert "$service_name" "Failed to restart after $RESTART_ATTEMPTS attempts"
    
    return 1
}

# Send failure alert (placeholder)
send_failure_alert() {
    local service_name="$1"
    local message="$2"
    
    error_log "ALERT: $service_name - $message"
    
    # Future implementation could include:
    # - Email notifications
    # - Slack/Discord webhooks
    # - PagerDuty integration
    # - System notifications
}

# Monitor all services
monitor_services() {
    local services=("mysql" "redis" "vault" "vedfolnir" "nginx" "prometheus" "grafana" "loki")
    local failed_services=()
    
    info_log "Starting service health monitoring"
    
    for service in "${services[@]}"; do
        local status=$(get_service_status "$service")
        
        case "$status" in
            "healthy")
                info_log "$service: healthy"
                ;;
            "unhealthy")
                warning_log "$service: unhealthy"
                failed_services+=("$service:unhealthy")
                ;;
            "stopped")
                error_log "$service: stopped"
                failed_services+=("$service:stopped")
                ;;
        esac
    done
    
    # Handle failed services
    if [ ${#failed_services[@]} -gt 0 ]; then
        error_log "Found ${#failed_services[@]} failed services"
        
        for failed_service in "${failed_services[@]}"; do
            local service_name=$(echo "$failed_service" | cut -d':' -f1)
            local failure_reason=$(echo "$failed_service" | cut -d':' -f2)
            
            handle_service_failure "$service_name" "$failure_reason"
        done
    else
        success_log "All services are healthy"
    fi
}

# Graceful shutdown of all services
graceful_shutdown() {
    local services=("nginx" "vedfolnir" "grafana" "loki" "prometheus" "vault" "redis" "mysql")
    
    info_log "Starting graceful shutdown of all services"
    
    for service in "${services[@]}"; do
        if is_service_running "$service"; then
            info_log "Stopping $service"
            docker-compose stop "$service" >/dev/null 2>&1 || {
                warning_log "$service did not stop gracefully, forcing stop"
                docker-compose kill "$service" >/dev/null 2>&1 || true
            }
        fi
    done
    
    success_log "All services stopped"
}

# Emergency restart of all services
emergency_restart() {
    warning_log "Performing emergency restart of all services"
    
    # Stop all services
    docker-compose down >/dev/null 2>&1 || true
    
    # Wait for cleanup
    sleep 10
    
    # Start all services
    if docker-compose up -d >/dev/null 2>&1; then
        success_log "Emergency restart completed"
        
        # Wait for services to become healthy
        sleep 30
        monitor_services
    else
        error_log "Emergency restart failed"
        return 1
    fi
}

# Generate service status report
generate_status_report() {
    local services=("mysql" "redis" "vault" "vedfolnir" "nginx" "prometheus" "grafana" "loki")
    
    echo "=== Service Status Report ==="
    echo "Timestamp: $(date -Iseconds)"
    echo ""
    
    for service in "${services[@]}"; do
        local status=$(get_service_status "$service")
        local uptime=""
        
        if is_service_running "$service"; then
            uptime=$(docker-compose ps "$service" | tail -1 | awk '{print $5}' 2>/dev/null || echo "unknown")
        fi
        
        printf "%-12s: %-10s %s\n" "$service" "$status" "$uptime"
    done
    
    echo ""
    echo "=========================="
}

# Main function
main() {
    local action="${1:-monitor}"
    
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    
    case "$action" in
        "monitor")
            monitor_services
            ;;
        "restart")
            local service_name="$2"
            if [ -z "$service_name" ]; then
                error_log "Service name required for restart"
                exit 1
            fi
            restart_service "$service_name" 1
            ;;
        "shutdown")
            graceful_shutdown
            ;;
        "emergency")
            emergency_restart
            ;;
        "status")
            generate_status_report
            ;;
        "health")
            local service_name="$2"
            if [ -z "$service_name" ]; then
                monitor_services
            else
                local status=$(get_service_status "$service_name")
                echo "$service_name: $status"
            fi
            ;;
        *)
            echo "Usage: $0 {monitor|restart <service>|shutdown|emergency|status|health [service]}"
            exit 1
            ;;
    esac
}

# Handle signals for graceful shutdown
trap 'graceful_shutdown; exit 0' SIGTERM SIGINT

# Run main function
main "$@"