#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Docker health check script for external Ollama API connectivity
# This script is designed to run inside Docker containers

set -e

# Configuration
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"
TIMEOUT="${OLLAMA_TIMEOUT:-10}"
VERBOSE="${OLLAMA_HEALTH_VERBOSE:-false}"

# Function to log messages
log() {
    if [ "$VERBOSE" = "true" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    fi
}

# Function to check if curl is available
check_curl() {
    if ! command -v curl &> /dev/null; then
        echo "ERROR: curl is not available in container"
        exit 1
    fi
}

# Function to test Ollama API version endpoint
test_version_endpoint() {
    log "Testing Ollama version endpoint: $OLLAMA_URL/api/version"
    
    if curl -f -s --max-time "$TIMEOUT" "$OLLAMA_URL/api/version" > /dev/null 2>&1; then
        log "✅ Version endpoint accessible"
        return 0
    else
        log "❌ Version endpoint not accessible"
        return 1
    fi
}

# Function to test Ollama API tags endpoint
test_tags_endpoint() {
    log "Testing Ollama tags endpoint: $OLLAMA_URL/api/tags"
    
    if curl -f -s --max-time "$TIMEOUT" "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        log "✅ Tags endpoint accessible"
        return 0
    else
        log "❌ Tags endpoint not accessible"
        return 1
    fi
}

# Function to get Ollama version
get_version() {
    local version_response
    version_response=$(curl -f -s --max-time "$TIMEOUT" "$OLLAMA_URL/api/version" 2>/dev/null || echo "")
    
    if [ -n "$version_response" ]; then
        # Try to extract version using basic text processing (no jq dependency)
        local version
        version=$(echo "$version_response" | grep -o '"version":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
        log "Ollama version: $version"
    fi
}

# Function to check model availability
check_model_availability() {
    local model_name="${OLLAMA_MODEL:-llava:7b}"
    log "Checking for model: $model_name"
    
    local tags_response
    tags_response=$(curl -f -s --max-time "$TIMEOUT" "$OLLAMA_URL/api/tags" 2>/dev/null || echo "")
    
    if [ -n "$tags_response" ]; then
        if echo "$tags_response" | grep -q "\"name\":\"$model_name\""; then
            log "✅ Required model '$model_name' is available"
            return 0
        else
            log "⚠️  Required model '$model_name' not found"
            return 1
        fi
    else
        log "❌ Could not retrieve model list"
        return 1
    fi
}

# Main health check function
main() {
    log "Starting Ollama external API health check"
    log "Ollama URL: $OLLAMA_URL"
    
    # Check if curl is available
    check_curl
    
    # Test version endpoint (primary health check)
    if ! test_version_endpoint; then
        echo "UNHEALTHY: Ollama API version endpoint not accessible"
        exit 1
    fi
    
    # Get version information
    get_version
    
    # Test tags endpoint
    if ! test_tags_endpoint; then
        echo "UNHEALTHY: Ollama API tags endpoint not accessible"
        exit 1
    fi
    
    # Check model availability (warning only, not fatal)
    check_model_availability || true
    
    log "✅ All health checks passed"
    echo "HEALTHY: Ollama external API is accessible"
    exit 0
}

# Handle command line arguments
case "${1:-}" in
    --verbose|-v)
        VERBOSE="true"
        ;;
    --help|-h)
        echo "Usage: $0 [--verbose|-v] [--help|-h]"
        echo "Environment variables:"
        echo "  OLLAMA_URL: Ollama API URL (default: http://host.docker.internal:11434)"
        echo "  OLLAMA_TIMEOUT: Request timeout in seconds (default: 10)"
        echo "  OLLAMA_MODEL: Model name to check (default: llava:7b)"
        echo "  OLLAMA_HEALTH_VERBOSE: Enable verbose output (default: false)"
        exit 0
        ;;
esac

# Run main function
main