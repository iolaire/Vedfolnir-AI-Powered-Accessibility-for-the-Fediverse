#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Comprehensive health check script for Vedfolnir application container
# Used by Docker Compose healthcheck and monitoring systems

set -e

# Configuration
HEALTH_ENDPOINT=${HEALTH_CHECK_ENDPOINT:-/health}
APP_PORT=${APP_PORT:-5000}
TIMEOUT=${HEALTH_CHECK_TIMEOUT:-15}
MAX_RETRIES=${HEALTH_CHECK_RETRIES:-3}
VERBOSE=${HEALTH_CHECK_VERBOSE:-false}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
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
    if [ "$VERBOSE" = "true" ]; then
        echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING:${NC} $1"
    fi
}

# Check if application is responding
check_application_endpoint() {
    local url="http://localhost:${APP_PORT}${HEALTH_ENDPOINT}"
    local retry=0
    
    log "Checking application health endpoint: $url"
    
    while [ $retry -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time "$TIMEOUT" "$url" >/dev/null 2>&1; then
            success_log "Application health endpoint responding"
            return 0
        fi
        
        retry=$((retry + 1))
        if [ $retry -lt $MAX_RETRIES ]; then
            warning_log "Health endpoint check failed, retrying ($retry/$MAX_RETRIES)..."
            sleep 2
        fi
    done
    
    error_log "Application health endpoint not responding after $MAX_RETRIES attempts"
    return 1
}

# Check if Gunicorn processes are running
check_gunicorn_processes() {
    log "Checking Gunicorn processes..."
    
    local master_pid=$(pgrep -f "gunicorn.*web_app:app" | head -1)
    if [ -z "$master_pid" ]; then
        error_log "Gunicorn master process not found"
        return 1
    fi
    
    local worker_count=$(pgrep -f "gunicorn.*web_app:app" | wc -l)
    if [ "$worker_count" -lt 1 ]; then
        error_log "No Gunicorn worker processes found"
        return 1
    fi
    
    success_log "Gunicorn running with $worker_count processes (master PID: $master_pid)"
    return 0
}

# Check database connectivity
check_database_connectivity() {
    log "Checking database connectivity..."
    
    if [ -z "$DATABASE_URL" ]; then
        warning_log "DATABASE_URL not set, skipping database check"
        return 0
    fi
    
    python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from config import Config
    from app.core.database.core.database_manager import DatabaseManager
    from sqlalchemy import text
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        result = session.execute(text('SELECT 1')).scalar()
        if result == 1:
            print('Database connectivity: OK')
            sys.exit(0)
        else:
            print('Database connectivity: FAIL - Unexpected result')
            sys.exit(1)
except Exception as e:
    print(f'Database connectivity: FAIL - {e}')
    sys.exit(1)
" 2>/dev/null
    
    local db_result=$?
    if [ $db_result -eq 0 ]; then
        success_log "Database connectivity OK"
        return 0
    else
        error_log "Database connectivity failed"
        return 1
    fi
}

# Check Redis connectivity
check_redis_connectivity() {
    log "Checking Redis connectivity..."
    
    if [ -z "$REDIS_URL" ]; then
        warning_log "REDIS_URL not set, skipping Redis check"
        return 0
    fi
    
    python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    import redis
    from urllib.parse import urlparse
    
    redis_url = os.getenv('REDIS_URL')
    parsed = urlparse(redis_url)
    
    r = redis.Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        password=parsed.password,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    
    # Test ping
    if r.ping():
        # Test basic operations
        test_key = 'health_check_test'
        r.set(test_key, 'test_value', ex=60)
        value = r.get(test_key)
        r.delete(test_key)
        
        if value == b'test_value':
            print('Redis connectivity: OK')
            sys.exit(0)
        else:
            print('Redis connectivity: FAIL - Operations failed')
            sys.exit(1)
    else:
        print('Redis connectivity: FAIL - Ping failed')
        sys.exit(1)
except Exception as e:
    print(f'Redis connectivity: FAIL - {e}')
    sys.exit(1)
" 2>/dev/null
    
    local redis_result=$?
    if [ $redis_result -eq 0 ]; then
        success_log "Redis connectivity OK"
        return 0
    else
        error_log "Redis connectivity failed"
        return 1
    fi
}

# Check external Ollama API connectivity
check_ollama_connectivity() {
    log "Checking Ollama API connectivity..."
    
    local ollama_url=${OLLAMA_URL:-"http://host.docker.internal:11434"}
    
    if curl -f -s --max-time 10 "$ollama_url/api/version" >/dev/null 2>&1; then
        success_log "Ollama API connectivity OK"
        return 0
    else
        warning_log "Ollama API connectivity failed (non-critical)"
        return 0  # Non-critical for basic health
    fi
}

# Check RQ workers if enabled
check_rq_workers() {
    log "Checking RQ workers..."
    
    if [ "$RQ_ENABLE_INTEGRATED_WORKERS" != "true" ]; then
        log "RQ integrated workers disabled, skipping check"
        return 0
    fi
    
    python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from app.services.task.rq.gunicorn_integration import get_rq_integration
    
    integration = get_rq_integration()
    if integration:
        status = integration.get_worker_status()
        if status.get('initialized', False):
            worker_count = status.get('worker_count', 0)
            print(f'RQ workers: OK ({worker_count} workers)')
            sys.exit(0)
        else:
            print('RQ workers: FAIL - Not initialized')
            sys.exit(1)
    else:
        print('RQ workers: FAIL - Integration not found')
        sys.exit(1)
except ImportError:
    print('RQ workers: SKIP - Module not available')
    sys.exit(0)
except Exception as e:
    print(f'RQ workers: FAIL - {e}')
    sys.exit(1)
" 2>/dev/null
    
    local rq_result=$?
    if [ $rq_result -eq 0 ]; then
        success_log "RQ workers OK"
        return 0
    else
        error_log "RQ workers check failed"
        return 1
    fi
}

# Check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # Check disk space
    local disk_usage=$(df /app 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
    if [ "$disk_usage" -gt 95 ]; then
        error_log "Critical disk usage: ${disk_usage}%"
        return 1
    elif [ "$disk_usage" -gt 85 ]; then
        warning_log "High disk usage: ${disk_usage}%"
    else
        success_log "Disk usage OK: ${disk_usage}%"
    fi
    
    # Check memory usage
    if [ -f /proc/meminfo ]; then
        local total_memory=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        local available_memory=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        local usage_percent=$(( (total_memory - available_memory) * 100 / total_memory ))
        
        if [ "$usage_percent" -gt 95 ]; then
            error_log "Critical memory usage: ${usage_percent}%"
            return 1
        elif [ "$usage_percent" -gt 85 ]; then
            warning_log "High memory usage: ${usage_percent}%"
        else
            success_log "Memory usage OK: ${usage_percent}%"
        fi
    else
        warning_log "Memory information not available"
    fi
    
    return 0
}

# Check file permissions and directories
check_file_permissions() {
    log "Checking file permissions and directories..."
    
    # Check if required directories exist and are writable
    local required_dirs=("/app/logs" "/app/storage" "/app/storage/temp")
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            warning_log "Directory $dir does not exist"
        elif [ ! -w "$dir" ]; then
            error_log "Directory $dir is not writable"
            return 1
        else
            success_log "Directory $dir OK"
        fi
    done
    
    return 0
}

# Main health check function
main() {
    local exit_code=0
    local checks_passed=0
    local checks_failed=0
    local checks_warned=0
    
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${BLUE}=== Vedfolnir Container Health Check ===${NC}"
        echo "Timestamp: $(date -Iseconds)"
        echo "Container: $(hostname)"
        echo "Health endpoint: http://localhost:${APP_PORT}${HEALTH_ENDPOINT}"
        echo ""
    fi
    
    # Critical health checks (must pass)
    local critical_checks=(
        "check_application_endpoint"
        "check_gunicorn_processes"
        "check_database_connectivity"
        "check_system_resources"
        "check_file_permissions"
    )
    
    # Important but non-critical checks
    local important_checks=(
        "check_redis_connectivity"
        "check_rq_workers"
    )
    
    # Optional checks
    local optional_checks=(
        "check_ollama_connectivity"
    )
    
    # Run critical checks
    for check in "${critical_checks[@]}"; do
        if $check; then
            checks_passed=$((checks_passed + 1))
        else
            checks_failed=$((checks_failed + 1))
            exit_code=1
        fi
    done
    
    # Run important checks
    for check in "${important_checks[@]}"; do
        if $check; then
            checks_passed=$((checks_passed + 1))
        else
            checks_failed=$((checks_failed + 1))
            # Redis and RQ failures are not critical if properly configured
            if [ "$check" = "check_redis_connectivity" ] && [ -z "$REDIS_URL" ]; then
                checks_warned=$((checks_warned + 1))
                checks_failed=$((checks_failed - 1))
            elif [ "$check" = "check_rq_workers" ] && [ "$RQ_ENABLE_INTEGRATED_WORKERS" != "true" ]; then
                checks_warned=$((checks_warned + 1))
                checks_failed=$((checks_failed - 1))
            else
                exit_code=1
            fi
        fi
    done
    
    # Run optional checks
    for check in "${optional_checks[@]}"; do
        if $check; then
            checks_passed=$((checks_passed + 1))
        else
            checks_warned=$((checks_warned + 1))
        fi
    done
    
    if [ "$VERBOSE" = "true" ]; then
        echo ""
        echo -e "${BLUE}=== Health Check Summary ===${NC}"
        echo -e "${GREEN}Passed: $checks_passed${NC}"
        echo -e "${RED}Failed: $checks_failed${NC}"
        echo -e "${YELLOW}Warnings: $checks_warned${NC}"
        
        if [ $exit_code -eq 0 ]; then
            echo -e "Status: ${GREEN}HEALTHY${NC}"
        else
            echo -e "Status: ${RED}UNHEALTHY${NC}"
        fi
        echo -e "${BLUE}=================================${NC}"
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
        # Quick check - only application endpoint
        check_application_endpoint
        ;;
    "endpoint")
        # Only check the health endpoint
        check_application_endpoint
        ;;
    *)
        # Default comprehensive check
        main
        ;;
esac