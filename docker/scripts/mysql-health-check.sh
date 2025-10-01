#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Enhanced MySQL health check script for Docker container
# Performs comprehensive health checks beyond basic ping

set -e

# Configuration
MYSQL_HOST="localhost"
MYSQL_PORT="3306"
HEALTH_CHECK_USER="healthcheck"
HEALTH_CHECK_PASSWORD="healthcheck_password"
MAX_CONNECTIONS_WARNING=180
MAX_CONNECTIONS_CRITICAL=190

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check basic connectivity
check_basic_connectivity() {
    log "Checking basic MySQL connectivity..."
    if ! mysqladmin ping -h "$MYSQL_HOST" -P "$MYSQL_PORT" --silent; then
        log "${RED}ERROR: MySQL is not responding to ping${NC}"
        return 1
    fi
    log "${GREEN}✓ MySQL basic connectivity OK${NC}"
    return 0
}

# Function to check database accessibility
check_database_access() {
    log "Checking database access..."
    if ! mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$HEALTH_CHECK_USER" -p"$HEALTH_CHECK_PASSWORD" -e "SELECT 1;" >/dev/null 2>&1; then
        log "${RED}ERROR: Cannot access MySQL database${NC}"
        return 1
    fi
    log "${GREEN}✓ Database access OK${NC}"
    return 0
}

# Function to check connection count
check_connections() {
    log "Checking connection count..."
    local connection_count
    connection_count=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$HEALTH_CHECK_USER" -p"$HEALTH_CHECK_PASSWORD" -e "SELECT COUNT(*) FROM information_schema.PROCESSLIST;" -s -N 2>/dev/null || echo "0")
    
    if [ "$connection_count" -gt "$MAX_CONNECTIONS_CRITICAL" ]; then
        log "${RED}CRITICAL: Too many connections ($connection_count > $MAX_CONNECTIONS_CRITICAL)${NC}"
        return 1
    elif [ "$connection_count" -gt "$MAX_CONNECTIONS_WARNING" ]; then
        log "${YELLOW}WARNING: High connection count ($connection_count > $MAX_CONNECTIONS_WARNING)${NC}"
    else
        log "${GREEN}✓ Connection count OK ($connection_count)${NC}"
    fi
    return 0
}

# Function to check InnoDB status
check_innodb_status() {
    log "Checking InnoDB status..."
    local innodb_status
    innodb_status=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$HEALTH_CHECK_USER" -p"$HEALTH_CHECK_PASSWORD" -e "SHOW ENGINE INNODB STATUS\G" 2>/dev/null | grep -c "ACTIVE" || echo "0")
    
    if [ "$innodb_status" -eq 0 ]; then
        log "${RED}ERROR: InnoDB engine not active${NC}"
        return 1
    fi
    log "${GREEN}✓ InnoDB status OK${NC}"
    return 0
}

# Function to check disk space
check_disk_space() {
    log "Checking disk space..."
    local disk_usage
    disk_usage=$(df /var/lib/mysql | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt 90 ]; then
        log "${RED}CRITICAL: Disk usage too high (${disk_usage}%)${NC}"
        return 1
    elif [ "$disk_usage" -gt 80 ]; then
        log "${YELLOW}WARNING: High disk usage (${disk_usage}%)${NC}"
    else
        log "${GREEN}✓ Disk usage OK (${disk_usage}%)${NC}"
    fi
    return 0
}

# Function to run comprehensive health check
run_comprehensive_check() {
    log "Running comprehensive MySQL health check..."
    
    # Try to call the stored procedure if it exists
    if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$HEALTH_CHECK_USER" -p"$HEALTH_CHECK_PASSWORD" -e "USE vedfolnir; CALL CheckDatabaseHealth();" >/dev/null 2>&1; then
        log "${GREEN}✓ Comprehensive health check completed${NC}"
    else
        log "${YELLOW}WARNING: Comprehensive health check procedure not available${NC}"
    fi
}

# Main health check function
main() {
    log "Starting MySQL health check..."
    
    local exit_code=0
    
    # Run all health checks
    check_basic_connectivity || exit_code=1
    check_database_access || exit_code=1
    check_connections || exit_code=1
    check_innodb_status || exit_code=1
    check_disk_space || exit_code=1
    run_comprehensive_check
    
    if [ $exit_code -eq 0 ]; then
        log "${GREEN}✓ All MySQL health checks passed${NC}"
    else
        log "${RED}✗ Some MySQL health checks failed${NC}"
    fi
    
    return $exit_code
}

# Handle script arguments
case "${1:-}" in
    "basic")
        check_basic_connectivity
        ;;
    "full")
        main
        ;;
    *)
        # Default to basic check for Docker health check
        check_basic_connectivity
        ;;
esac