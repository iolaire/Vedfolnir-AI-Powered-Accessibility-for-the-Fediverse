#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Prometheus health check script for Docker container
# Comprehensive health validation for metrics collection

set -e

# Configuration
PROMETHEUS_URL="http://localhost:9090"
TIMEOUT=${PROMETHEUS_HEALTH_TIMEOUT:-10}
VERBOSE=${PROMETHEUS_HEALTH_VERBOSE:-false}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
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
    if [ "$VERBOSE" = "true" ]; then
        echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}SUCCESS:${NC} $1"
    fi
}

warning_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING:${NC} $1"
}

# Check Prometheus health endpoint
check_prometheus_health() {
    log "Checking Prometheus health endpoint"
    
    if curl -f -s --max-time "$TIMEOUT" "$PROMETHEUS_URL/-/healthy" >/dev/null 2>&1; then
        success_log "Prometheus health endpoint OK"
        return 0
    else
        error_log "Prometheus health endpoint not responding"
        return 1
    fi
}

# Check Prometheus readiness
check_prometheus_ready() {
    log "Checking Prometheus readiness endpoint"
    
    if curl -f -s --max-time "$TIMEOUT" "$PROMETHEUS_URL/-/ready" >/dev/null 2>&1; then
        success_log "Prometheus ready endpoint OK"
        return 0
    else
        error_log "Prometheus not ready"
        return 1
    fi
}

# Check Prometheus configuration
check_prometheus_config() {
    log "Checking Prometheus configuration status"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$PROMETHEUS_URL/api/v1/status/config" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"success"' 2>/dev/null; then
            success_log "Prometheus configuration valid"
            return 0
        else
            error_log "Prometheus configuration invalid"
            return 1
        fi
    else
        error_log "Cannot check Prometheus configuration"
        return 1
    fi
}

# Check Prometheus targets
check_prometheus_targets() {
    log "Checking Prometheus targets status"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"success"' 2>/dev/null; then
            local active_targets=$(echo "$response" | grep -o '"health":"up"' | wc -l 2>/dev/null || echo "0")
            local total_targets=$(echo "$response" | grep -o '"health":"' | wc -l 2>/dev/null || echo "0")
            
            if [ "$active_targets" -gt 0 ]; then
                success_log "Prometheus targets OK ($active_targets/$total_targets active)"
                return 0
            else
                warning_log "No active Prometheus targets found"
                return 1
            fi
        else
            error_log "Prometheus targets API error"
            return 1
        fi
    else
        error_log "Cannot check Prometheus targets"
        return 1
    fi
}

# Check Prometheus storage
check_prometheus_storage() {
    log "Checking Prometheus storage status"
    
    # Check if data directory exists and is writable
    if [ ! -d "/prometheus" ]; then
        error_log "Prometheus data directory not found"
        return 1
    fi
    
    if [ ! -w "/prometheus" ]; then
        error_log "Prometheus data directory not writable"
        return 1
    fi
    
    # Check disk usage
    local disk_usage=$(df /prometheus 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
    if [ "$disk_usage" -gt 90 ]; then
        error_log "Prometheus storage critical: ${disk_usage}% used"
        return 1
    elif [ "$disk_usage" -gt 80 ]; then
        warning_log "Prometheus storage high: ${disk_usage}% used"
    else
        success_log "Prometheus storage OK: ${disk_usage}% used"
    fi
    
    return 0
}

# Check Prometheus rules
check_prometheus_rules() {
    log "Checking Prometheus rules status"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$PROMETHEUS_URL/api/v1/rules" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"success"' 2>/dev/null; then
            local rule_groups=$(echo "$response" | grep -o '"name":"' | wc -l 2>/dev/null || echo "0")
            success_log "Prometheus rules OK ($rule_groups rule groups)"
            return 0
        else
            error_log "Prometheus rules API error"
            return 1
        fi
    else
        warning_log "Cannot check Prometheus rules (may not be configured)"
        return 0  # Non-critical
    fi
}

# Main health check function
main() {
    local exit_code=0
    local checks_passed=0
    local checks_failed=0
    local checks_warned=0
    
    if [ "$VERBOSE" = "true" ]; then
        echo "=== Prometheus Health Check ==="
        echo "Timestamp: $(date -Iseconds)"
        echo "Prometheus URL: $PROMETHEUS_URL"
        echo ""
    fi
    
    # Critical checks
    if check_prometheus_health; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_prometheus_ready; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_prometheus_config; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_prometheus_storage; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    # Important but non-critical checks
    if check_prometheus_targets; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warned=$((checks_warned + 1))
    fi
    
    if check_prometheus_rules; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warned=$((checks_warned + 1))
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        echo ""
        echo "=== Prometheus Health Check Summary ==="
        echo "Passed: $checks_passed"
        echo "Failed: $checks_failed"
        echo "Warnings: $checks_warned"
        
        if [ $exit_code -eq 0 ]; then
            echo -e "Status: ${GREEN}HEALTHY${NC}"
        else
            echo -e "Status: ${RED}UNHEALTHY${NC}"
        fi
        echo "======================================="
    fi
    
    exit $exit_code
}

# Handle script arguments
case "${1:-}" in
    "verbose")
        VERBOSE=true
        main
        ;;
    "basic")
        # Basic check - only health and ready endpoints
        check_prometheus_health && check_prometheus_ready
        ;;
    *)
        # Default comprehensive check
        main
        ;;
esac