#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Ollama health check script for Docker containers
# Tests connectivity to external Ollama API service running on host system

set -e

# Configuration
OLLAMA_URL=${OLLAMA_URL:-"http://host.docker.internal:11434"}
TIMEOUT=${OLLAMA_HEALTH_TIMEOUT:-10}
VERBOSE=${OLLAMA_HEALTH_VERBOSE:-false}

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

# Check if Ollama API is accessible
check_ollama_version() {
    log "Checking Ollama API version endpoint: $OLLAMA_URL/api/version"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$OLLAMA_URL/api/version" 2>/dev/null); then
        local version=$(echo "$response" | grep -o '"version":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
        success_log "Ollama API version: $version"
        return 0
    else
        error_log "Ollama API version endpoint not accessible"
        return 1
    fi
}

# Check if Ollama API tags endpoint is accessible
check_ollama_tags() {
    log "Checking Ollama API tags endpoint: $OLLAMA_URL/api/tags"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$OLLAMA_URL/api/tags" 2>/dev/null); then
        local model_count=$(echo "$response" | grep -o '"name"' | wc -l 2>/dev/null || echo "0")
        success_log "Ollama API tags accessible (models available: $model_count)"
        return 0
    else
        error_log "Ollama API tags endpoint not accessible"
        return 1
    fi
}

# Check if LLaVA model is available
check_llava_model() {
    log "Checking for LLaVA model availability"
    
    local response
    if response=$(curl -f -s --max-time "$TIMEOUT" "$OLLAMA_URL/api/tags" 2>/dev/null); then
        if echo "$response" | grep -q "llava" 2>/dev/null; then
            success_log "LLaVA model found in Ollama"
            return 0
        else
            warning_log "LLaVA model not found in Ollama (may need to be pulled)"
            return 1
        fi
    else
        error_log "Cannot check LLaVA model availability - API not accessible"
        return 1
    fi
}

# Test basic connectivity to host system
check_host_connectivity() {
    log "Checking basic connectivity to Docker host"
    
    # Extract host from OLLAMA_URL
    local host=$(echo "$OLLAMA_URL" | sed 's|http://||' | sed 's|https://||' | cut -d':' -f1)
    local port=$(echo "$OLLAMA_URL" | sed 's|http://||' | sed 's|https://||' | cut -d':' -f2 | cut -d'/' -f1)
    
    if [ "$port" = "$host" ]; then
        port="11434"  # Default Ollama port
    fi
    
    log "Testing connectivity to $host:$port"
    
    if timeout "$TIMEOUT" bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        success_log "Host connectivity OK ($host:$port)"
        return 0
    else
        error_log "Cannot connect to $host:$port"
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
        echo "=== Ollama API Health Check ==="
        echo "Timestamp: $(date -Iseconds)"
        echo "Ollama URL: $OLLAMA_URL"
        echo "Timeout: ${TIMEOUT}s"
        echo ""
    fi
    
    # Check basic host connectivity first
    if check_host_connectivity; then
        checks_passed=$((checks_passed + 1))
        
        # Check Ollama API version
        if check_ollama_version; then
            checks_passed=$((checks_passed + 1))
            
            # Check tags endpoint
            if check_ollama_tags; then
                checks_passed=$((checks_passed + 1))
                
                # Check for LLaVA model (warning if not found)
                if check_llava_model; then
                    checks_passed=$((checks_passed + 1))
                else
                    checks_warned=$((checks_warned + 1))
                fi
            else
                checks_failed=$((checks_failed + 1))
                exit_code=1
            fi
        else
            checks_failed=$((checks_failed + 1))
            exit_code=1
        fi
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        echo ""
        echo "=== Ollama Health Check Summary ==="
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
    "quick")
        # Quick check - only version endpoint
        check_ollama_version
        ;;
    "connectivity")
        # Only check host connectivity
        check_host_connectivity
        ;;
    *)
        # Default comprehensive check
        main
        ;;
esac