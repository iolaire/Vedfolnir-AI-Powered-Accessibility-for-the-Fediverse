#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Redis performance monitoring script for Vedfolnir Docker deployment
# Provides real-time monitoring and performance analysis

set -e

REDIS_CONTAINER="vedfolnir_redis"
MONITOR_INTERVAL=5
LOG_FILE="./logs/redis/performance_monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp]${NC} $1"
    echo "[$timestamp] $1" >> "$LOG_FILE" 2>/dev/null || true
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

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Get Redis password
get_redis_password() {
    if [ -f "./secrets/redis_password.txt" ]; then
        cat "./secrets/redis_password.txt"
    else
        error "Redis password file not found"
        exit 1
    fi
}

# Check if Redis container is running
check_redis_container() {
    if ! docker ps | grep -q "$REDIS_CONTAINER"; then
        error "Redis container '$REDIS_CONTAINER' is not running"
        exit 1
    fi
}

# Get Redis info
get_redis_info() {
    local section="$1"
    local password=$(get_redis_password)
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" info "$section" 2>/dev/null
}

# Get Redis config value
get_redis_config() {
    local key="$1"
    local password=$(get_redis_password)
    docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" config get "$key" 2>/dev/null | tail -n 1
}

# Format bytes to human readable
format_bytes() {
    local bytes=$1
    if [ "$bytes" -ge 1073741824 ]; then
        echo "$(echo "scale=2; $bytes / 1073741824" | bc)GB"
    elif [ "$bytes" -ge 1048576 ]; then
        echo "$(echo "scale=2; $bytes / 1048576" | bc)MB"
    elif [ "$bytes" -ge 1024 ]; then
        echo "$(echo "scale=2; $bytes / 1024" | bc)KB"
    else
        echo "${bytes}B"
    fi
}

# Display Redis server information
show_server_info() {
    info "Redis Server Information:"
    local server_info=$(get_redis_info server)
    
    local version=$(echo "$server_info" | grep "^redis_version:" | cut -d: -f2 | tr -d '\r')
    local uptime=$(echo "$server_info" | grep "^uptime_in_seconds:" | cut -d: -f2 | tr -d '\r')
    local uptime_days=$((uptime / 86400))
    local uptime_hours=$(((uptime % 86400) / 3600))
    local uptime_minutes=$(((uptime % 3600) / 60))
    
    echo "  Version: $version"
    echo "  Uptime: ${uptime_days}d ${uptime_hours}h ${uptime_minutes}m"
    echo ""
}

# Display memory information
show_memory_info() {
    info "Memory Information:"
    local memory_info=$(get_redis_info memory)
    
    local used_memory=$(echo "$memory_info" | grep "^used_memory:" | cut -d: -f2 | tr -d '\r')
    local used_memory_human=$(echo "$memory_info" | grep "^used_memory_human:" | cut -d: -f2 | tr -d '\r')
    local used_memory_rss=$(echo "$memory_info" | grep "^used_memory_rss:" | cut -d: -f2 | tr -d '\r')
    local used_memory_peak=$(echo "$memory_info" | grep "^used_memory_peak:" | cut -d: -f2 | tr -d '\r')
    local used_memory_peak_human=$(echo "$memory_info" | grep "^used_memory_peak_human:" | cut -d: -f2 | tr -d '\r')
    local mem_fragmentation_ratio=$(echo "$memory_info" | grep "^mem_fragmentation_ratio:" | cut -d: -f2 | tr -d '\r')
    
    local maxmemory=$(get_redis_config maxmemory)
    local maxmemory_policy=$(get_redis_config maxmemory-policy)
    
    echo "  Used Memory: $used_memory_human ($used_memory bytes)"
    echo "  RSS Memory: $(format_bytes $used_memory_rss)"
    echo "  Peak Memory: $used_memory_peak_human"
    echo "  Max Memory: $(format_bytes $maxmemory)"
    echo "  Memory Policy: $maxmemory_policy"
    echo "  Fragmentation Ratio: $mem_fragmentation_ratio"
    
    # Memory usage percentage
    if [ "$maxmemory" -gt 0 ]; then
        local usage_percent=$((used_memory * 100 / maxmemory))
        echo "  Memory Usage: ${usage_percent}%"
        
        if [ "$usage_percent" -gt 90 ]; then
            warning "  High memory usage detected!"
        elif [ "$usage_percent" -gt 75 ]; then
            warning "  Memory usage approaching limit"
        fi
    fi
    
    # Fragmentation warning
    if (( $(echo "$mem_fragmentation_ratio > 1.5" | bc -l 2>/dev/null || echo "0") )); then
        warning "  High memory fragmentation detected"
    fi
    
    echo ""
}

# Display client information
show_client_info() {
    info "Client Information:"
    local clients_info=$(get_redis_info clients)
    
    local connected_clients=$(echo "$clients_info" | grep "^connected_clients:" | cut -d: -f2 | tr -d '\r')
    local blocked_clients=$(echo "$clients_info" | grep "^blocked_clients:" | cut -d: -f2 | tr -d '\r')
    local tracking_clients=$(echo "$clients_info" | grep "^tracking_clients:" | cut -d: -f2 | tr -d '\r')
    
    echo "  Connected Clients: $connected_clients"
    echo "  Blocked Clients: $blocked_clients"
    echo "  Tracking Clients: $tracking_clients"
    echo ""
}

# Display keyspace information
show_keyspace_info() {
    info "Keyspace Information:"
    local keyspace_info=$(get_redis_info keyspace)
    
    if [ -z "$keyspace_info" ]; then
        echo "  No databases with keys"
    else
        echo "$keyspace_info" | grep "^db" | while read -r line; do
            local db=$(echo "$line" | cut -d: -f1)
            local stats=$(echo "$line" | cut -d: -f2)
            echo "  $db: $stats"
        done
    fi
    echo ""
}

# Display persistence information
show_persistence_info() {
    info "Persistence Information:"
    local persistence_info=$(get_redis_info persistence)
    
    local rdb_changes_since_last_save=$(echo "$persistence_info" | grep "^rdb_changes_since_last_save:" | cut -d: -f2 | tr -d '\r')
    local rdb_last_save_time=$(echo "$persistence_info" | grep "^rdb_last_save_time:" | cut -d: -f2 | tr -d '\r')
    local aof_enabled=$(echo "$persistence_info" | grep "^aof_enabled:" | cut -d: -f2 | tr -d '\r')
    local aof_current_size=$(echo "$persistence_info" | grep "^aof_current_size:" | cut -d: -f2 | tr -d '\r')
    
    echo "  RDB Changes Since Last Save: $rdb_changes_since_last_save"
    echo "  RDB Last Save: $(date -d @$rdb_last_save_time 2>/dev/null || echo "Unknown")"
    echo "  AOF Enabled: $aof_enabled"
    
    if [ "$aof_enabled" = "1" ]; then
        echo "  AOF Current Size: $(format_bytes $aof_current_size)"
    fi
    echo ""
}

# Display statistics
show_stats_info() {
    info "Statistics:"
    local stats_info=$(get_redis_info stats)
    
    local total_connections_received=$(echo "$stats_info" | grep "^total_connections_received:" | cut -d: -f2 | tr -d '\r')
    local total_commands_processed=$(echo "$stats_info" | grep "^total_commands_processed:" | cut -d: -f2 | tr -d '\r')
    local instantaneous_ops_per_sec=$(echo "$stats_info" | grep "^instantaneous_ops_per_sec:" | cut -d: -f2 | tr -d '\r')
    local keyspace_hits=$(echo "$stats_info" | grep "^keyspace_hits:" | cut -d: -f2 | tr -d '\r')
    local keyspace_misses=$(echo "$stats_info" | grep "^keyspace_misses:" | cut -d: -f2 | tr -d '\r')
    local expired_keys=$(echo "$stats_info" | grep "^expired_keys:" | cut -d: -f2 | tr -d '\r')
    local evicted_keys=$(echo "$stats_info" | grep "^evicted_keys:" | cut -d: -f2 | tr -d '\r')
    
    echo "  Total Connections: $total_connections_received"
    echo "  Total Commands: $total_commands_processed"
    echo "  Operations/sec: $instantaneous_ops_per_sec"
    echo "  Keyspace Hits: $keyspace_hits"
    echo "  Keyspace Misses: $keyspace_misses"
    echo "  Expired Keys: $expired_keys"
    echo "  Evicted Keys: $evicted_keys"
    
    # Calculate hit ratio
    if [ "$keyspace_hits" -gt 0 ] || [ "$keyspace_misses" -gt 0 ]; then
        local total_requests=$((keyspace_hits + keyspace_misses))
        local hit_ratio=$((keyspace_hits * 100 / total_requests))
        echo "  Hit Ratio: ${hit_ratio}%"
        
        if [ "$hit_ratio" -lt 80 ]; then
            warning "  Low cache hit ratio detected"
        fi
    fi
    echo ""
}

# Show slow log
show_slow_log() {
    info "Slow Log (last 5 entries):"
    local password=$(get_redis_password)
    local slow_log=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" slowlog get 5 2>/dev/null)
    
    if [ -z "$slow_log" ] || [ "$slow_log" = "(empty list or set)" ]; then
        echo "  No slow queries"
    else
        echo "$slow_log" | head -20  # Limit output
    fi
    echo ""
}

# Show session analysis
show_session_analysis() {
    info "Session Analysis:"
    local password=$(get_redis_password)
    
    # Count session keys
    local session_count=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" eval "return #redis.call('keys', 'vedfolnir:session:*')" 0 2>/dev/null || echo "0")
    echo "  Active Sessions: $session_count"
    
    # Count RQ keys
    local rq_count=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" eval "return #redis.call('keys', 'rq:*')" 0 2>/dev/null || echo "0")
    echo "  RQ Job Keys: $rq_count"
    
    # Sample session TTL
    if [ "$session_count" -gt 0 ]; then
        local sample_session=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" eval "return redis.call('keys', 'vedfolnir:session:*')[1]" 0 2>/dev/null)
        if [ -n "$sample_session" ]; then
            local ttl=$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$password" ttl "$sample_session" 2>/dev/null || echo "-1")
            echo "  Sample Session TTL: ${ttl}s"
        fi
    fi
    echo ""
}

# Real-time monitoring
real_time_monitor() {
    log "Starting real-time Redis monitoring (Ctrl+C to stop)..."
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    while true; do
        clear
        echo "Redis Performance Monitor - $(date)"
        echo "========================================"
        
        show_server_info
        show_memory_info
        show_client_info
        show_keyspace_info
        show_stats_info
        show_session_analysis
        
        echo "Press Ctrl+C to stop monitoring"
        sleep "$MONITOR_INTERVAL"
    done
}

# One-time snapshot
snapshot_monitor() {
    log "Redis Performance Snapshot - $(date)"
    
    show_server_info
    show_memory_info
    show_client_info
    show_keyspace_info
    show_persistence_info
    show_stats_info
    show_slow_log
    show_session_analysis
}

# Main function
main() {
    check_redis_container
    
    case "${1:-snapshot}" in
        "monitor"|"real-time"|"rt")
            real_time_monitor
            ;;
        "snapshot"|"snap"|*)
            snapshot_monitor
            ;;
    esac
}

# Show help
show_help() {
    echo "Redis Performance Monitor for Vedfolnir"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  monitor     - Real-time monitoring (updates every ${MONITOR_INTERVAL}s)"
    echo "  snapshot    - One-time performance snapshot (default)"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 snapshot"
    echo "  $0 monitor"
}

# Parse arguments
case "${1:-}" in
    "--help"|"-h"|"help")
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac