#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MySQL container management script
# Provides comprehensive management operations for MySQL in Docker

set -e

# Configuration
CONTAINER_NAME="vedfolnir_mysql"
MYSQL_USER="root"
DATABASE_NAME="vedfolnir"

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

# Function to check if container is running
check_container() {
    if ! docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
        log "${RED}ERROR: MySQL container '$CONTAINER_NAME' is not running${NC}"
        return 1
    fi
    return 0
}

# Function to execute command in MySQL container
exec_in_container() {
    local command="$1"
    docker exec -it "$CONTAINER_NAME" $command
}

# Function to execute MySQL command
exec_mysql() {
    local query="$1"
    docker exec -i "$CONTAINER_NAME" mysql -u "$MYSQL_USER" -p"${MYSQL_ROOT_PASSWORD}" -e "$query"
}

# Function to show container status
show_status() {
    log "${BLUE}=== MySQL Container Status ===${NC}"
    
    if check_container; then
        log "${GREEN}✓ Container is running${NC}"
        
        # Show container details
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        # Show resource usage
        log "${BLUE}Resource Usage:${NC}"
        docker stats "$CONTAINER_NAME" --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
        
        # Show MySQL status
        log "${BLUE}MySQL Status:${NC}"
        if exec_mysql "SELECT 'MySQL is accessible' as status;" 2>/dev/null; then
            log "${GREEN}✓ MySQL is accessible${NC}"
        else
            log "${RED}✗ MySQL is not accessible${NC}"
        fi
    else
        log "${RED}✗ Container is not running${NC}"
        
        # Show container if it exists but is stopped
        if docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
            log "${YELLOW}Container exists but is stopped:${NC}"
            docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        fi
    fi
}

# Function to show logs
show_logs() {
    local lines="${1:-50}"
    
    log "${BLUE}=== MySQL Container Logs (last $lines lines) ===${NC}"
    
    if check_container; then
        docker logs --tail "$lines" "$CONTAINER_NAME"
    else
        return 1
    fi
}

# Function to follow logs
follow_logs() {
    log "${BLUE}=== Following MySQL Container Logs (Ctrl+C to stop) ===${NC}"
    
    if check_container; then
        docker logs -f "$CONTAINER_NAME"
    else
        return 1
    fi
}

# Function to connect to MySQL shell
connect_mysql() {
    log "${BLUE}=== Connecting to MySQL Shell ===${NC}"
    
    if check_container; then
        exec_in_container "mysql -u $MYSQL_USER -p"
    else
        return 1
    fi
}

# Function to run health check
run_health_check() {
    log "${BLUE}=== Running MySQL Health Check ===${NC}"
    
    if check_container; then
        exec_in_container "/scripts/mysql-health-check.sh full"
    else
        return 1
    fi
}

# Function to run performance monitor
run_performance_monitor() {
    log "${BLUE}=== Running MySQL Performance Monitor ===${NC}"
    
    if check_container; then
        exec_in_container "MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD /scripts/mysql-performance-monitor.sh report"
    else
        return 1
    fi
}

# Function to create backup
create_backup() {
    local backup_type="${1:-full}"
    
    log "${BLUE}=== Creating MySQL Backup (type: $backup_type) ===${NC}"
    
    if check_container; then
        case "$backup_type" in
            "full")
                exec_in_container "MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD /scripts/mysql-backup.sh full"
                ;;
            "schema")
                exec_in_container "MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD /scripts/mysql-backup.sh schema"
                ;;
            *)
                log "${RED}ERROR: Invalid backup type. Use 'full' or 'schema'${NC}"
                return 1
                ;;
        esac
    else
        return 1
    fi
}

# Function to list backups
list_backups() {
    log "${BLUE}=== Listing MySQL Backups ===${NC}"
    
    if check_container; then
        exec_in_container "/scripts/mysql-backup.sh list"
    else
        return 1
    fi
}

# Function to show database information
show_database_info() {
    log "${BLUE}=== Database Information ===${NC}"
    
    if check_container; then
        log "MySQL Version:"
        exec_mysql "SELECT VERSION();"
        
        log "Database Size:"
        exec_mysql "SELECT 
            table_schema as 'Database',
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as 'Size (MB)'
            FROM information_schema.tables 
            WHERE table_schema = '$DATABASE_NAME'
            GROUP BY table_schema;"
        
        log "Table Count:"
        exec_mysql "SELECT COUNT(*) as 'Table Count' FROM information_schema.tables WHERE table_schema = '$DATABASE_NAME';"
        
        log "Tables:"
        exec_mysql "SELECT 
            table_name as 'Table',
            table_rows as 'Rows',
            ROUND((data_length + index_length) / 1024 / 1024, 2) as 'Size (MB)'
            FROM information_schema.tables 
            WHERE table_schema = '$DATABASE_NAME'
            ORDER BY (data_length + index_length) DESC;"
    else
        return 1
    fi
}

# Function to restart container
restart_container() {
    log "${BLUE}=== Restarting MySQL Container ===${NC}"
    
    log "Stopping container..."
    docker stop "$CONTAINER_NAME" || true
    
    log "Starting container..."
    docker start "$CONTAINER_NAME"
    
    # Wait for container to be ready
    log "Waiting for MySQL to be ready..."
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        if docker exec "$CONTAINER_NAME" mysqladmin ping -h localhost --silent 2>/dev/null; then
            log "${GREEN}✓ MySQL is ready${NC}"
            return 0
        fi
        
        sleep 2
        ((attempts++))
        log "Waiting... ($attempts/$max_attempts)"
    done
    
    log "${RED}✗ MySQL failed to start within expected time${NC}"
    return 1
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {command} [options]"
    echo
    echo "Commands:"
    echo "  status              - Show container and MySQL status"
    echo "  logs [lines]        - Show container logs (default: 50 lines)"
    echo "  follow-logs         - Follow container logs in real-time"
    echo "  connect             - Connect to MySQL shell"
    echo "  health              - Run comprehensive health check"
    echo "  performance         - Run performance monitoring"
    echo "  backup [full|schema] - Create database backup"
    echo "  list-backups        - List available backups"
    echo "  database-info       - Show database information"
    echo "  restart             - Restart MySQL container"
    echo
    echo "Environment Variables:"
    echo "  MYSQL_ROOT_PASSWORD - MySQL root password (required)"
    echo
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 logs 100"
    echo "  $0 backup full"
    echo "  $0 health"
}

# Main function
main() {
    # Check if MySQL root password is set
    if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
        log "${RED}ERROR: MYSQL_ROOT_PASSWORD environment variable not set${NC}"
        exit 1
    fi
    
    # Handle commands
    case "${1:-}" in
        "status")
            show_status
            ;;
        "logs")
            show_logs "${2:-50}"
            ;;
        "follow-logs")
            follow_logs
            ;;
        "connect")
            connect_mysql
            ;;
        "health")
            run_health_check
            ;;
        "performance")
            run_performance_monitor
            ;;
        "backup")
            create_backup "${2:-full}"
            ;;
        "list-backups")
            list_backups
            ;;
        "database-info")
            show_database_info
            ;;
        "restart")
            restart_container
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"