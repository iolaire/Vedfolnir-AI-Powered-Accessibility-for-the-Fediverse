#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Redis setup validation script for Vedfolnir Docker deployment
# Validates Redis configuration, connectivity, and optimization settings

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

REDIS_CONTAINER="vedfolnir_redis"
VALIDATION_ERRORS=0

# Increment error counter
add_error() {
    VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
    error "$1"
}

# Check if Redis container exists and is running
check_container_status() {
    log "Checking Redis container status..."
    
    if ! docker ps --format "table {{.Names}}" | grep -q "^$REDIS_CONTAINER$"; then
        add_error "Redis container '$REDIS_CONTAINER' is not running"
        return 1
    fi
    
    success "Redis container is running"
    return 0
}

# Validate Redis configuration files
validate_config_files() {
    log "Validating Redis configuration files..."
    
    # Check if config file exists
    if [ ! -f "./config/redis/redis.conf" ]; then
        add_error "Redis configuration file not found: ./config/redis/redis.conf"
        return 1
    fi
    
    # Check config file syntax (basic validation)
    if ! grep -q "^bind 0.0.0.0" "./config/redis/redis.conf"; then
        add_error "Redis config missing bind directive"
    fi
    
    if ! grep -q "^port 6379" "./config/redis/redis.conf"; then
        add_error "Redis config missing port directive"
    fi
    
    if ! grep -q "^maxmemory" "./config/redis/redis.conf"; then
        add_error "Redis config missing maxmemory directive"
    fi
    
    if ! grep -q "^appendonly yes" "./config/redis/redis.conf"; then
        add_error "Redis config missing AOF persistence"
    fi
    
    success "Redis configuration files validated"
}

# Validate Redis secrets
validate_secrets() {
    log "Validating Redis secrets..."
    
    if [ ! -f "./secrets/redis_password.txt" ]; then
        add_error "Redis password file not found: ./secrets/redis_password.txt"
        return 1
    fi
    
    local password=$(cat "./secrets/redis_password.txt")
    if [ ${#password} -lt 16 ]; then
        add_error "Redis password is too short (minimum 16 characters)"
    fi
    
    if [ "$password" = "CHANGE_ME_SECURE_REDIS_PASSWORD" ]; then
        add_error "Redis password is still set to default value"
    fi
    
    success "Redis secrets validated"
}

# Test Redis connectivity and authentication
test_redis_connectivity() {
    log "Testing Redis connectivity..."
    
    if ! check_container_status; then
        return 1
    fi
    
    local password=$(cat "./secrets/redis_password.txt" 2>/dev/null || echo "")
    
    # Test ping
    if ! docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" ping > /dev/null 2>&1; then
        add_error "Redis ping test failed"
        return 1
    fi
    
    # Test basic operations
    if ! docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" set test_key "test_value" > /dev/null 2>&1; then
        add_error "Redis SET operation failed"
        return 1
    fi
    
    if ! docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" get test_key > /dev/null 2>&1; then
        add_error "Redis GET operation failed"
        return 1
    fi
    
    # Clean up test key
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" del test_key > /dev/null 2>&1
    
    success "Redis connectivity test passed"
}

# Validate Redis configuration settings
validate_redis_settings() {
    log "Validating Redis configuration settings..."
    
    if ! check_container_status; then
        return 1
    fi
    
    local password=$(cat "./secrets/redis_password.txt" 2>/dev/null || echo "")
    
    # Check memory policy
    local memory_policy=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" config get maxmemory-policy | tail -n 1)
    if [ "$memory_policy" != "volatile-lru" ]; then
        warning "Redis memory policy is '$memory_policy', expected 'volatile-lru' for session storage"
    fi
    
    # Check AOF persistence
    local aof_enabled=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" config get appendonly | tail -n 1)
    if [ "$aof_enabled" != "yes" ]; then
        add_error "Redis AOF persistence is not enabled"
    fi
    
    # Check save configuration
    local save_config=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" config get save | tail -n 1)
    if [ -z "$save_config" ] || [ "$save_config" = '""' ]; then
        add_error "Redis RDB save configuration is empty"
    fi
    
    # Check keyspace notifications
    local notify_config=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" config get notify-keyspace-events | tail -n 1)
    if [[ "$notify_config" != *"E"* ]] || [[ "$notify_config" != *"x"* ]]; then
        warning "Redis keyspace notifications not configured for session expiration tracking"
    fi
    
    success "Redis configuration settings validated"
}

# Check Redis performance and optimization
check_redis_performance() {
    log "Checking Redis performance settings..."
    
    if ! check_container_status; then
        return 1
    fi
    
    local password=$(cat "./secrets/redis_password.txt" 2>/dev/null || echo "")
    
    # Check memory usage
    local memory_info=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info memory)
    local used_memory=$(echo "$memory_info" | grep "^used_memory_human:" | cut -d: -f2 | tr -d '\r')
    local max_memory=$(echo "$memory_info" | grep "^maxmemory_human:" | cut -d: -f2 | tr -d '\r')
    
    log "Memory usage: $used_memory / $max_memory"
    
    # Check fragmentation ratio
    local fragmentation=$(echo "$memory_info" | grep "^mem_fragmentation_ratio:" | cut -d: -f2 | tr -d '\r')
    if (( $(echo "$fragmentation > 2.0" | bc -l 2>/dev/null || echo "0") )); then
        warning "High memory fragmentation ratio: $fragmentation"
    fi
    
    # Check connected clients
    local clients_info=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info clients)
    local connected_clients=$(echo "$clients_info" | grep "^connected_clients:" | cut -d: -f2 | tr -d '\r')
    log "Connected clients: $connected_clients"
    
    # Check slow log
    local slow_log_len=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" slowlog len)
    if [ "$slow_log_len" -gt 0 ]; then
        warning "Redis slow log contains $slow_log_len entries"
    fi
    
    success "Redis performance check completed"
}

# Validate volume mounts
validate_volume_mounts() {
    log "Validating Redis volume mounts..."
    
    # Check if data directory exists in container
    if ! docker exec "$REDIS_CONTAINER" test -d /data; then
        add_error "Redis data directory /data not found in container"
    fi
    
    # Check if config file is mounted
    if ! docker exec "$REDIS_CONTAINER" test -f /usr/local/etc/redis/redis.conf; then
        add_error "Redis config file not mounted in container"
    fi
    
    # Check if backup directory is accessible
    if ! docker exec "$REDIS_CONTAINER" test -d /backups; then
        warning "Redis backup directory not mounted in container"
    fi
    
    # Check data persistence
    if ! docker exec "$REDIS_CONTAINER" test -f /data/dump.rdb; then
        warning "Redis RDB file not found (may be normal for new installation)"
    fi
    
    success "Redis volume mounts validated"
}

# Test session storage functionality
test_session_functionality() {
    log "Testing Redis session storage functionality..."
    
    if ! check_container_status; then
        return 1
    fi
    
    local password=$(cat "./secrets/redis_password.txt" 2>/dev/null || echo "")
    
    # Test session key operations
    local session_key="vedfolnir:session:test_session_$(date +%s)"
    local session_data='{"user_id": 1, "username": "test", "created_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
    
    # Set session with TTL
    if ! docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" setex "$session_key" 3600 "$session_data" > /dev/null 2>&1; then
        add_error "Failed to set session key with TTL"
        return 1
    fi
    
    # Get session data
    local retrieved_data=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" get "$session_key")
    if [ "$retrieved_data" != "$session_data" ]; then
        add_error "Session data retrieval failed"
        return 1
    fi
    
    # Check TTL
    local ttl=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" ttl "$session_key")
    if [ "$ttl" -le 0 ]; then
        add_error "Session TTL not set correctly"
        return 1
    fi
    
    # Clean up test session
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" del "$session_key" > /dev/null 2>&1
    
    success "Redis session functionality test passed"
}

# Test RQ queue functionality
test_rq_functionality() {
    log "Testing Redis RQ queue functionality..."
    
    if ! check_container_status; then
        return 1
    fi
    
    local password=$(cat "./secrets/redis_password.txt" 2>/dev/null || echo "")
    
    # Test queue operations
    local queue_key="rq:queue:test_queue"
    local job_data='{"id": "test_job_'$(date +%s)'", "func": "test.function", "args": [], "kwargs": {}}'
    
    # Push job to queue
    if ! docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" lpush "$queue_key" "$job_data" > /dev/null 2>&1; then
        add_error "Failed to push job to RQ queue"
        return 1
    fi
    
    # Check queue length
    local queue_len=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" llen "$queue_key")
    if [ "$queue_len" -eq 0 ]; then
        add_error "RQ queue length is 0 after push"
        return 1
    fi
    
    # Pop job from queue
    local popped_job=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" rpop "$queue_key")
    if [ "$popped_job" != "$job_data" ]; then
        add_error "RQ job data retrieval failed"
        return 1
    fi
    
    success "Redis RQ functionality test passed"
}

# Main validation function
main() {
    log "Starting Redis setup validation for Vedfolnir..."
    
    validate_config_files
    validate_secrets
    validate_volume_mounts
    test_redis_connectivity
    validate_redis_settings
    check_redis_performance
    test_session_functionality
    test_rq_functionality
    
    echo ""
    if [ $VALIDATION_ERRORS -eq 0 ]; then
        success "Redis setup validation completed successfully!"
        log "Redis is properly configured for session storage and RQ queue management"
        exit 0
    else
        error "Redis setup validation failed with $VALIDATION_ERRORS error(s)"
        log "Please fix the errors above before proceeding"
        exit 1
    fi
}

# Show help
show_help() {
    echo "Redis Setup Validation Script for Vedfolnir"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "This script validates:"
    echo "  - Redis container status"
    echo "  - Configuration files"
    echo "  - Secrets and authentication"
    echo "  - Volume mounts"
    echo "  - Connectivity and basic operations"
    echo "  - Performance settings"
    echo "  - Session storage functionality"
    echo "  - RQ queue functionality"
}

# Parse command line arguments
case "${1:-}" in
    "--help"|"-h")
        show_help
        exit 0
        ;;
    *)
        main
        ;;
esac