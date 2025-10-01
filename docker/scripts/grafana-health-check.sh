#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Grafana health check script for Docker container
# Comprehensive health validation for monitoring dashboard

set -e

# Configuration
GRAFANA_URL="http://localhost:3000"
TIMEOUT=${GRAFANA_HEALTH_TIMEOUT:-10}
VERBOSE=${GRAFANA_HEALTH_VERBOSE:-false}

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

# Check Grafana health endpoint
check_grafana_health() {
    log "Checking Grafana health endpoint"
    
    if curl -f -s --max-time "$TIMEOUT" "$GRAFANA_URL/api/health" >/dev/null 2>&1; then
        success_log "Grafana health endpoint OK"
        return 0
    else
        error_log "Grafana health endpoint not responding"
        return 1
    fi
}

# Check Grafana login page
check_grafana_login() {
    log "Checking Grafana login page"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$GRAFANA_URL/login" 2>/dev/null); then
        if echo "$response" | grep -q "Grafana" 2>/dev/null; then
            success_log "Grafana login page accessible"
            return 0
        else
            error_log "Grafana login page content invalid"
            return 1
        fi
    else
        error_log "Grafana login page not accessible"
        return 1
    fi
}

# Check Grafana database
check_grafana_database() {
    log "Checking Grafana database connectivity"
    
    # Check if data directory exists and is writable
    if [ ! -d "/var/lib/grafana" ]; then
        error_log "Grafana data directory not found"
        return 1
    fi
    
    if [ ! -w "/var/lib/grafana" ]; then
        error_log "Grafana data directory not writable"
        return 1
    fi
    
    # Check if SQLite database exists (default Grafana setup)
    if [ -f "/var/lib/grafana/grafana.db" ]; then
        success_log "Grafana database file exists"
        return 0
    else
        warning_log "Grafana database file not found (may be first startup)"
        return 0  # Non-critical on first startup
    fi
}

# Check Grafana storage
check_grafana_storage() {
    log "Checking Grafana storage status"
    
    # Check disk usage
    local disk_usage=$(df /var/lib/grafana 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
    if [ "$disk_usage" -gt 90 ]; then
        error_log "Grafana storage critical: ${disk_usage}% used"
        return 1
    elif [ "$disk_usage" -gt 80 ]; then
        warning_log "Grafana storage high: ${disk_usage}% used"
    else
        success_log "Grafana storage OK: ${disk_usage}% used"
    fi
    
    return 0
}

# Check Grafana plugins
check_grafana_plugins() {
    log "Checking Grafana plugins"
    
    # Check if plugins directory exists
    if [ -d "/var/lib/grafana/plugins" ]; then
        local plugin_count=$(find /var/lib/grafana/plugins -maxdepth 1 -type d | wc -l)
        plugin_count=$((plugin_count - 1))  # Subtract the plugins directory itself
        success_log "Grafana plugins directory OK ($plugin_count plugins)"
        return 0
    else
        warning_log "Grafana plugins directory not found"
        return 0  # Non-critical
    fi
}

# Check Grafana configuration
check_grafana_config() {
    log "Checking Grafana configuration"
    
    # Check if configuration file exists
    if [ -f "/etc/grafana/grafana.ini" ]; then
        success_log "Grafana configuration file exists"
        return 0
    else
        warning_log "Grafana configuration file not found (using defaults)"
        return 0  # Non-critical, Grafana can use defaults
    fi
}

# Check Grafana process
check_grafana_process() {
    log "Checking Grafana process"
    
    if pgrep -f "grafana-server" >/dev/null; then
        local process_count=$(pgrep -f "grafana-server" | wc -l)
        success_log "Grafana process running ($process_count processes)"
        return 0
    else
        error_log "Grafana process not found"
        return 1
    fi
}

# Main health check function
main() {
    local exit_code=0
    local checks_passed=0
    local checks_failed=0
    local checks_warned=0
    
    if [ "$VERBOSE" = "true" ]; then
        echo "=== Grafana Health Check ==="
        echo "Timestamp: $(date -Iseconds)"
        echo "Grafana URL: $GRAFANA_URL"
        echo ""
    fi
    
    # Critical checks
    if check_grafana_process; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_grafana_health; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_grafana_login; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_grafana_storage; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    # Important but non-critical checks
    if check_grafana_database; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warned=$((checks_warned + 1))
    fi
    
    if check_grafana_config; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warned=$((checks_warned + 1))
    fi
    
    if check_grafana_plugins; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warned=$((checks_warned + 1))
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        echo ""
        echo "=== Grafana Health Check Summary ==="
        echo "Passed: $checks_passed"
        echo "Failed: $checks_failed"
        echo "Warnings: $checks_warned"
        
        if [ $exit_code -eq 0 ]; then
            echo -e "Status: ${GREEN}HEALTHY${NC}"
        else
            echo -e "Status: ${RED}UNHEALTHY${NC}"
        fi
        echo "===================================="
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
        # Basic check - only health endpoint and login page
        check_grafana_health && check_grafana_login
        ;;
    *)
        # Default comprehensive check
        main
        ;;
esac