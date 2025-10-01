#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Redis management script for Vedfolnir Docker deployment
# Provides monitoring, backup, and maintenance operations

set -e

REDIS_CONTAINER="vedfolnir_redis"
BACKUP_DIR="./storage/backups/redis"
LOG_DIR="./logs/redis"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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

# Check if Redis container is running
check_redis_container() {
    if ! docker ps | grep -q "$REDIS_CONTAINER"; then
        error "Redis container '$REDIS_CONTAINER' is not running"
        return 1
    fi
    return 0
}

# Get Redis password from secrets
get_redis_password() {
    if [ -f "./secrets/redis_password.txt" ]; then
        cat "./secrets/redis_password.txt"
    else
        error "Redis password file not found at ./secrets/redis_password.txt"
        return 1
    fi
}

# Redis health check
redis_health_check() {
    log "Performing Redis health check..."
    
    if ! check_redis_container; then
        return 1
    fi
    
    local password=$(get_redis_password)
    
    # Basic connectivity test
    if docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" ping > /dev/null 2>&1; then
        success "Redis ping successful"
    else
        error "Redis ping failed"
        return 1
    fi
    
    # Get Redis info
    log "Redis server information:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info server | grep -E "(redis_version|uptime_in_seconds|tcp_port)"
    
    # Memory usage
    log "Memory usage:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info memory | grep -E "(used_memory_human|maxmemory_human|mem_fragmentation_ratio)"
    
    # Connected clients
    log "Client connections:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info clients | grep -E "(connected_clients|blocked_clients)"
    
    # Keyspace information
    log "Keyspace information:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info keyspace
    
    # Persistence information
    log "Persistence information:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info persistence | grep -E "(rdb_last_save_time|aof_enabled|aof_last_rewrite_time_sec)"
    
    success "Redis health check completed"
}

# Redis performance monitoring
redis_performance_monitor() {
    log "Monitoring Redis performance..."
    
    if ! check_redis_container; then
        return 1
    fi
    
    local password=$(get_redis_password)
    
    # Slow log analysis
    log "Recent slow queries:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" slowlog get 10
    
    # Latency monitoring
    log "Latency information:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" latency latest
    
    # Memory fragmentation
    local fragmentation=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info memory | grep mem_fragmentation_ratio | cut -d: -f2 | tr -d '\r')
    log "Memory fragmentation ratio: $fragmentation"
    
    if (( $(echo "$fragmentation > 1.5" | bc -l) )); then
        warning "High memory fragmentation detected ($fragmentation). Consider running MEMORY DOCTOR."
    fi
    
    # Check for expired keys
    local expired_keys=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info stats | grep expired_keys | cut -d: -f2 | tr -d '\r')
    log "Expired keys: $expired_keys"
    
    success "Performance monitoring completed"
}

# Backup Redis data
redis_backup() {
    log "Starting Redis backup..."
    
    if ! check_redis_container; then
        return 1
    fi
    
    local password=$(get_redis_password)
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/redis_backup_$timestamp"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Trigger background save
    log "Triggering Redis BGSAVE..."
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" bgsave
    
    # Wait for background save to complete
    log "Waiting for background save to complete..."
    while [ "$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" lastsave)" = "$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" lastsave)" ]; do
        sleep 1
    done
    
    # Copy RDB file
    log "Copying RDB file..."
    docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$backup_file.rdb"
    
    # Copy AOF file if it exists
    if docker exec "$REDIS_CONTAINER" test -f /data/appendonly.aof; then
        log "Copying AOF file..."
        docker cp "$REDIS_CONTAINER:/data/appendonly.aof" "$backup_file.aof"
    fi
    
    # Create backup metadata
    cat > "$backup_file.meta" << EOF
Backup created: $(date)
Redis version: $(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info server | grep redis_version | cut -d: -f2 | tr -d '\r')
Database size: $(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" dbsize)
Memory usage: $(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
EOF
    
    # Compress backup files
    log "Compressing backup files..."
    tar -czf "$backup_file.tar.gz" -C "$BACKUP_DIR" "$(basename "$backup_file")".*
    rm -f "$backup_file".rdb "$backup_file".aof "$backup_file".meta
    
    success "Redis backup completed: $backup_file.tar.gz"
}

# Restore Redis data
redis_restore() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Please specify backup file to restore"
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    warning "This will stop Redis and replace all data. Continue? (y/N)"
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log "Restore cancelled"
        return 0
    fi
    
    log "Starting Redis restore from $backup_file..."
    
    # Stop Redis container
    log "Stopping Redis container..."
    docker-compose stop redis
    
    # Extract backup
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"
    
    # Copy files to Redis data volume
    log "Restoring data files..."
    if [ -f "$temp_dir/redis_backup_*.rdb" ]; then
        docker run --rm -v vedfolnir_redis_data:/data -v "$temp_dir":/backup alpine cp /backup/*.rdb /data/dump.rdb
    fi
    
    if [ -f "$temp_dir/redis_backup_*.aof" ]; then
        docker run --rm -v vedfolnir_redis_data:/data -v "$temp_dir":/backup alpine cp /backup/*.aof /data/appendonly.aof
    fi
    
    # Cleanup
    rm -rf "$temp_dir"
    
    # Start Redis container
    log "Starting Redis container..."
    docker-compose start redis
    
    # Wait for Redis to be ready
    sleep 5
    
    # Verify restore
    if redis_health_check > /dev/null 2>&1; then
        success "Redis restore completed successfully"
    else
        error "Redis restore may have failed. Check logs."
        return 1
    fi
}

# Clean up old backups
redis_cleanup_backups() {
    local retention_days=${1:-30}
    
    log "Cleaning up Redis backups older than $retention_days days..."
    
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -name "redis_backup_*.tar.gz" -mtime +$retention_days -delete
        success "Old backups cleaned up"
    else
        warning "Backup directory not found: $BACKUP_DIR"
    fi
}

# Redis session analysis
redis_session_analysis() {
    log "Analyzing Redis session data..."
    
    if ! check_redis_container; then
        return 1
    fi
    
    local password=$(get_redis_password)
    
    # Count session keys
    local session_count=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" eval "return #redis.call('keys', 'vedfolnir:session:*')" 0)
    log "Active sessions: $session_count"
    
    # Count RQ job keys
    local rq_count=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" eval "return #redis.call('keys', 'rq:*')" 0)
    log "RQ job keys: $rq_count"
    
    # Memory usage by key pattern
    log "Memory usage analysis:"
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" --bigkeys
    
    success "Session analysis completed"
}

# Main function
main() {
    case "${1:-help}" in
        "health"|"status")
            redis_health_check
            ;;
        "monitor"|"perf")
            redis_performance_monitor
            ;;
        "backup")
            redis_backup
            ;;
        "restore")
            redis_restore "$2"
            ;;
        "cleanup")
            redis_cleanup_backups "$2"
            ;;
        "sessions"|"analyze")
            redis_session_analysis
            ;;
        "help"|*)
            echo "Redis Management Script for Vedfolnir"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  health          - Perform Redis health check"
            echo "  monitor         - Monitor Redis performance"
            echo "  backup          - Create Redis backup"
            echo "  restore <file>  - Restore Redis from backup"
            echo "  cleanup [days]  - Clean up old backups (default: 30 days)"
            echo "  sessions        - Analyze session and queue data"
            echo "  help            - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 health"
            echo "  $0 backup"
            echo "  $0 restore ./storage/backups/redis/redis_backup_20250101_120000.tar.gz"
            echo "  $0 cleanup 7"
            ;;
    esac
}

# Run main function with all arguments
main "$@"