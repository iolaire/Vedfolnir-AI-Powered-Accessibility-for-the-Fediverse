#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Loki health check script for Docker container
# Comprehensive health validation for log aggregation

set -e

# Configuration
LOKI_URL="http://localhost:3100"
TIMEOUT=${LOKI_HEALTH_TIMEOUT:-10}
VERBOSE=${LOKI_HEALTH_VERBOSE:-false}

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

# Check Loki ready endpoint
check_loki_ready() {
    log "Checking Loki ready endpoint"
    
    if curl -f -s --max-time "$TIMEOUT" "$LOKI_URL/ready" >/dev/null 2>&1; then
        success_log "Loki ready endpoint OK"
        return 0
    else
        error_log "Loki ready endpoint not responding"
        return 1
    fi
}

# Check Loki metrics endpoint
check_loki_metrics() {
    log "Checking Loki metrics endpoint"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$LOKI_URL/metrics" 2>/dev/null); then
        if echo "$response" | grep -q "loki_" 2>/dev/null; then
            success_log "Loki metrics endpoint OK"
            return 0
        else
            error_log "Loki metrics endpoint invalid response"
            return 1
        fi
    else
        error_log "Loki metrics endpoint not accessible"
        return 1
    fi
}

# Check Loki configuration
check_loki_config() {
    log "Checking Loki configuration"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$LOKI_URL/config" 2>/dev/null); then
        if echo "$response" | grep -q "server:" 2>/dev/null; then
            success_log "Loki configuration accessible"
            return 0
        else
            error_log "Loki configuration invalid"
            return 1
        fi
    else
        error_log "Loki configuration not accessible"
        return 1
    fi
}

# Check Loki storage
check_loki_storage() {
    log "Checking Loki storage status"
    
    # Check if data directory exists and is writable
    if [ ! -d "/loki" ]; then
        error_log "Loki data directory not found"
        return 1
    fi
    
    if [ ! -w "/loki" ]; then
        error_log "Loki data directory not writable"
        return 1
    fi
    
    # Check disk usage
    local disk_usage=$(df /loki 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
    if [ "$disk_usage" -gt 90 ]; then
        error_log "Loki storage critical: ${disk_usage}% used"
        return 1
    elif [ "$disk_usage" -gt 80 ]; then
        warning_log "Loki storage high: ${disk_usage}% used"
    else
        success_log "Loki storage OK: ${disk_usage}% used"
    fi
    
    return 0
}

# Check Loki labels API
check_loki_labels() {
    log "Checking Loki labels API"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$LOKI_URL/loki/api/v1/labels" 2>/dev/null); then
        if echo "$response" | grep -q '"status":"success"' 2>/dev/null; then
            local label_count=$(echo "$response" | grep -o '"[^"]*"' | wc -l 2>/dev/null || echo "0")
            success_log "Loki labels API OK ($label_count labels)"
            return 0
        else
            warning_log "Loki labels API returned no data (may be empty)"
            return 0  # Non-critical if no logs yet
        fi
    else
        error_log "Loki labels API not accessible"
        return 1
    fi
}

# Check Loki process
check_loki_process() {
    log "Checking Loki process"
    
    if pgrep -f "loki" >/dev/null; then
        local process_count=$(pgrep -f "loki" | wc -l)
        success_log "Loki process running ($process_count processes)"
        return 0
    else
        error_log "Loki process not found"
        return 1
    fi
}

# Test log ingestion capability
check_loki_ingestion() {
    log "Testing Loki log ingestion capability"
    
    # Create a test log entry
    local timestamp=$(date +%s)000000000  # Nanoseconds
    local test_log="{\"streams\": [{\"stream\": {\"job\": \"health-check\", \"instance\": \"test\"}, \"values\": [[\"$timestamp\", \"health check test log\"]]}]}"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" -X POST \
        -H "Content-Type: application/json" \
        -d "$test_log" \
        "$LOKI_URL/loki/api/v1/push" 2>/dev/null); then
        success_log "Loki log ingestion test OK"
        return 0
    else
        warning_log "Loki log ingestion test failed (may be read-only)"
        return 0  # Non-critical for health check
    fi
}

# Main health check function
main() {
    local exit_code=0
    local checks_passed=0
    local checks_failed=0
    local checks_warned=0
    
    if [ "$VERBOSE" = "true" ]; then
        echo "=== Loki Health Check ==="
        echo "Timestamp: $(date -Iseconds)"
        echo "Loki URL: $LOKI_URL"
        echo ""
    fi
    
    # Critical checks
    if check_loki_process; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_loki_ready; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_loki_metrics; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_loki_config; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_loki_storage; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    # Important but non-critical checks
    if check_loki_labels; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warned=$((checks_warned + 1))
    fi
    
    if check_loki_ingestion; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warned=$((checks_warned + 1))
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        echo ""
        echo "=== Loki Health Check Summary ==="
        echo "Passed: $checks_passed"
        echo "Failed: $checks_failed"
        echo "Warnings: $checks_warned"
        
        if [ $exit_code -eq 0 ]; then
            echo -e "Status: ${GREEN}HEALTHY${NC}"
        else
            echo -e "Status: ${RED}UNHEALTHY${NC}"
        fi
        echo "================================="
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
        # Basic check - only ready and metrics endpoints
        check_loki_ready && check_loki_metrics
        ;;
    *)
        # Default comprehensive check
        main
        ;;
esac