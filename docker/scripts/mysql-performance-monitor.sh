#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MySQL performance monitoring script for Docker container
# Provides detailed performance metrics and optimization recommendations

set -e

# Configuration
MYSQL_HOST="localhost"
MYSQL_PORT="3306"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to execute MySQL query
mysql_query() {
    local query="$1"
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "$query" -s -N 2>/dev/null
}

# Function to get MySQL status variable
get_status_var() {
    local var_name="$1"
    mysql_query "SHOW GLOBAL STATUS LIKE '$var_name';" | awk '{print $2}'
}

# Function to get MySQL variable
get_variable() {
    local var_name="$1"
    mysql_query "SHOW GLOBAL VARIABLES LIKE '$var_name';" | awk '{print $2}'
}

# Function to check buffer pool efficiency
check_buffer_pool() {
    log "${BLUE}=== InnoDB Buffer Pool Analysis ===${NC}"
    
    local buffer_pool_size=$(get_variable "innodb_buffer_pool_size")
    local buffer_pool_reads=$(get_status_var "Innodb_buffer_pool_reads")
    local buffer_pool_read_requests=$(get_status_var "Innodb_buffer_pool_read_requests")
    
    if [ -n "$buffer_pool_reads" ] && [ -n "$buffer_pool_read_requests" ] && [ "$buffer_pool_read_requests" -gt 0 ]; then
        local hit_rate=$(echo "scale=2; (1 - $buffer_pool_reads / $buffer_pool_read_requests) * 100" | bc -l)
        log "Buffer Pool Size: $(echo "scale=2; $buffer_pool_size / 1024 / 1024 / 1024" | bc -l) GB"
        log "Buffer Pool Hit Rate: ${hit_rate}%"
        
        if (( $(echo "$hit_rate >= 99.0" | bc -l) )); then
            log "${GREEN}✓ Excellent buffer pool hit rate${NC}"
        elif (( $(echo "$hit_rate >= 95.0" | bc -l) )); then
            log "${YELLOW}⚠ Good buffer pool hit rate${NC}"
        else
            log "${RED}✗ Poor buffer pool hit rate - consider increasing innodb_buffer_pool_size${NC}"
        fi
    else
        log "${YELLOW}⚠ Buffer pool statistics not available yet${NC}"
    fi
}

# Function to check connection usage
check_connections() {
    log "${BLUE}=== Connection Analysis ===${NC}"
    
    local max_connections=$(get_variable "max_connections")
    local current_connections=$(mysql_query "SELECT COUNT(*) FROM information_schema.PROCESSLIST;")
    local max_used_connections=$(get_status_var "Max_used_connections")
    
    local usage_percent=$(echo "scale=2; $current_connections / $max_connections * 100" | bc -l)
    local max_usage_percent=$(echo "scale=2; $max_used_connections / $max_connections * 100" | bc -l)
    
    log "Max Connections: $max_connections"
    log "Current Connections: $current_connections (${usage_percent}%)"
    log "Peak Connections: $max_used_connections (${max_usage_percent}%)"
    
    if (( $(echo "$max_usage_percent >= 85.0" | bc -l) )); then
        log "${RED}✗ High connection usage - consider increasing max_connections${NC}"
    elif (( $(echo "$max_usage_percent >= 70.0" | bc -l) )); then
        log "${YELLOW}⚠ Moderate connection usage${NC}"
    else
        log "${GREEN}✓ Good connection usage${NC}"
    fi
}

# Function to check query performance
check_query_performance() {
    log "${BLUE}=== Query Performance Analysis ===${NC}"
    
    local slow_queries=$(get_status_var "Slow_queries")
    local questions=$(get_status_var "Questions")
    local uptime=$(get_status_var "Uptime")
    
    if [ -n "$questions" ] && [ "$questions" -gt 0 ]; then
        local slow_query_percent=$(echo "scale=4; $slow_queries / $questions * 100" | bc -l)
        local queries_per_second=$(echo "scale=2; $questions / $uptime" | bc -l)
        
        log "Total Queries: $questions"
        log "Slow Queries: $slow_queries (${slow_query_percent}%)"
        log "Queries per Second: $queries_per_second"
        
        if (( $(echo "$slow_query_percent >= 5.0" | bc -l) )); then
            log "${RED}✗ High percentage of slow queries - review query optimization${NC}"
        elif (( $(echo "$slow_query_percent >= 1.0" | bc -l) )); then
            log "${YELLOW}⚠ Moderate slow query rate${NC}"
        else
            log "${GREEN}✓ Good query performance${NC}"
        fi
    else
        log "${YELLOW}⚠ Query statistics not available yet${NC}"
    fi
}

# Function to check table cache
check_table_cache() {
    log "${BLUE}=== Table Cache Analysis ===${NC}"
    
    local table_open_cache=$(get_variable "table_open_cache")
    local opened_tables=$(get_status_var "Opened_tables")
    local open_tables=$(get_status_var "Open_tables")
    
    local cache_usage_percent=$(echo "scale=2; $open_tables / $table_open_cache * 100" | bc -l)
    
    log "Table Open Cache: $table_open_cache"
    log "Currently Open Tables: $open_tables (${cache_usage_percent}%)"
    log "Total Opened Tables: $opened_tables"
    
    if (( $(echo "$cache_usage_percent >= 95.0" | bc -l) )); then
        log "${RED}✗ Table cache nearly full - consider increasing table_open_cache${NC}"
    elif (( $(echo "$cache_usage_percent >= 80.0" | bc -l) )); then
        log "${YELLOW}⚠ High table cache usage${NC}"
    else
        log "${GREEN}✓ Good table cache usage${NC}"
    fi
}

# Function to check temporary tables
check_temp_tables() {
    log "${BLUE}=== Temporary Table Analysis ===${NC}"
    
    local created_tmp_tables=$(get_status_var "Created_tmp_tables")
    local created_tmp_disk_tables=$(get_status_var "Created_tmp_disk_tables")
    
    if [ -n "$created_tmp_tables" ] && [ "$created_tmp_tables" -gt 0 ]; then
        local disk_tmp_percent=$(echo "scale=2; $created_tmp_disk_tables / $created_tmp_tables * 100" | bc -l)
        
        log "Temporary Tables Created: $created_tmp_tables"
        log "Disk Temporary Tables: $created_tmp_disk_tables (${disk_tmp_percent}%)"
        
        if (( $(echo "$disk_tmp_percent >= 25.0" | bc -l) )); then
            log "${RED}✗ High disk temporary table usage - consider increasing tmp_table_size${NC}"
        elif (( $(echo "$disk_tmp_percent >= 10.0" | bc -l) )); then
            log "${YELLOW}⚠ Moderate disk temporary table usage${NC}"
        else
            log "${GREEN}✓ Good temporary table performance${NC}"
        fi
    else
        log "${YELLOW}⚠ Temporary table statistics not available yet${NC}"
    fi
}

# Function to show top processes
show_top_processes() {
    log "${BLUE}=== Current Top Processes ===${NC}"
    
    mysql_query "SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, LEFT(INFO, 50) as QUERY 
                 FROM information_schema.PROCESSLIST 
                 WHERE COMMAND != 'Sleep' 
                 ORDER BY TIME DESC 
                 LIMIT 10;" | while read line; do
        log "$line"
    done
}

# Function to generate performance report
generate_report() {
    log "${BLUE}=== MySQL Performance Report ===${NC}"
    log "Generated at: $(date)"
    log "MySQL Version: $(mysql_query "SELECT VERSION();")"
    log "Uptime: $(get_status_var "Uptime") seconds"
    echo
    
    check_buffer_pool
    echo
    check_connections
    echo
    check_query_performance
    echo
    check_table_cache
    echo
    check_temp_tables
    echo
    show_top_processes
    
    log "${BLUE}=== End of Report ===${NC}"
}

# Main function
main() {
    if [ -z "$MYSQL_PASSWORD" ]; then
        log "${RED}ERROR: MYSQL_ROOT_PASSWORD environment variable not set${NC}"
        exit 1
    fi
    
    # Test MySQL connection
    if ! mysql_query "SELECT 1;" >/dev/null 2>&1; then
        log "${RED}ERROR: Cannot connect to MySQL${NC}"
        exit 1
    fi
    
    generate_report
}

# Handle script arguments
case "${1:-}" in
    "report")
        main
        ;;
    "buffer")
        check_buffer_pool
        ;;
    "connections")
        check_connections
        ;;
    "queries")
        check_query_performance
        ;;
    "processes")
        show_top_processes
        ;;
    *)
        log "Usage: $0 {report|buffer|connections|queries|processes}"
        log "  report      - Generate full performance report"
        log "  buffer      - Check buffer pool efficiency"
        log "  connections - Check connection usage"
        log "  queries     - Check query performance"
        log "  processes   - Show current processes"
        exit 1
        ;;
esac