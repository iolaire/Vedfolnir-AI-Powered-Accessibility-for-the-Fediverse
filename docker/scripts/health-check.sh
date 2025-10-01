#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Production health check script for Docker containers
# Comprehensive health validation for container orchestration

set -e

# Configuration
HEALTH_ENDPOINT=${HEALTH_CHECK_ENDPOINT:-/health}
APP_PORT=${APP_PORT:-5000}
TIMEOUT=${HEALTH_CHECK_TIMEOUT:-10}
MAX_RETRIES=${HEALTH_CHECK_RETRIES:-3}

# Health check functions
check_application_health() {
    local url="http://localhost:${APP_PORT}${HEALTH_ENDPOINT}"
    local retry=0
    
    while [ $retry -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time "$TIMEOUT" "$url" >/dev/null 2>&1; then
            return 0
        fi
        
        retry=$((retry + 1))
        if [ $retry -lt $MAX_RETRIES ]; then
            sleep 1
        fi
    done
    
    return 1
}

check_database_connectivity() {
    if [ -n "$DATABASE_URL" ]; then
        python3 -c "
import sys
import os
sys.path.insert(0, '/app')

try:
    from config import Config
    from app.core.database.core.database_manager import DatabaseManager
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        session.execute('SELECT 1')
    
    print('Database: OK')
    sys.exit(0)
except Exception as e:
    print(f'Database: FAIL - {e}')
    sys.exit(1)
"
        return $?
    else
        echo "Database: SKIP - No DATABASE_URL configured"
        return 0
    fi
}

check_redis_connectivity() {
    if [ -n "$REDIS_URL" ]; then
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
        socket_timeout=5
    )
    
    r.ping()
    print('Redis: OK')
    sys.exit(0)
except Exception as e:
    print(f'Redis: FAIL - {e}')
    sys.exit(1)
"
        return $?
    else
        echo "Redis: SKIP - No REDIS_URL configured"
        return 0
    fi
}

check_rq_workers() {
    if [ "$RQ_ENABLE_INTEGRATED_WORKERS" = "true" ]; then
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
            print('RQ Workers: OK')
            sys.exit(0)
        else:
            print('RQ Workers: FAIL - Not initialized')
            sys.exit(1)
    else:
        print('RQ Workers: FAIL - Integration not found')
        sys.exit(1)
except Exception as e:
    print(f'RQ Workers: FAIL - {e}')
    sys.exit(1)
"
        return $?
    else
        echo "RQ Workers: SKIP - Integrated workers disabled"
        return 0
    fi
}

check_disk_space() {
    local usage
    usage=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$usage" -gt 95 ]; then
        echo "Disk Space: CRITICAL - ${usage}% used"
        return 1
    elif [ "$usage" -gt 85 ]; then
        echo "Disk Space: WARNING - ${usage}% used"
        return 0
    else
        echo "Disk Space: OK - ${usage}% used"
        return 0
    fi
}

check_memory_usage() {
    if [ -f /proc/meminfo ]; then
        local total_memory available_memory usage_percent
        
        total_memory=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        available_memory=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        
        usage_percent=$(( (total_memory - available_memory) * 100 / total_memory ))
        
        if [ "$usage_percent" -gt 95 ]; then
            echo "Memory: CRITICAL - ${usage_percent}% used"
            return 1
        elif [ "$usage_percent" -gt 85 ]; then
            echo "Memory: WARNING - ${usage_percent}% used"
            return 0
        else
            echo "Memory: OK - ${usage_percent}% used"
            return 0
        fi
    else
        echo "Memory: SKIP - /proc/meminfo not available"
        return 0
    fi
}

check_process_health() {
    # Check if Gunicorn master process is running
    if pgrep -f "gunicorn.*web_app:app" >/dev/null; then
        local worker_count
        worker_count=$(pgrep -f "gunicorn.*web_app:app" | wc -l)
        echo "Processes: OK - Gunicorn running with $worker_count processes"
        return 0
    else
        echo "Processes: FAIL - Gunicorn not running"
        return 1
    fi
}

# Main health check function
main() {
    local exit_code=0
    local checks_passed=0
    local checks_failed=0
    
    echo "=== Vedfolnir Container Health Check ==="
    echo "Timestamp: $(date -Iseconds)"
    echo "Container: $(hostname)"
    echo ""
    
    # Core health checks
    echo "Core Services:"
    
    if check_application_health; then
        checks_passed=$((checks_passed + 1))
    else
        echo "Application: FAIL - Health endpoint not responding"
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_process_health; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    echo ""
    echo "Dependencies:"
    
    if check_database_connectivity; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_redis_connectivity; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        # Redis failure is not critical
    fi
    
    if check_rq_workers; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        # RQ worker failure is not critical if disabled
        if [ "$RQ_ENABLE_INTEGRATED_WORKERS" = "true" ]; then
            exit_code=1
        fi
    fi
    
    echo ""
    echo "Resources:"
    
    if check_disk_space; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    if check_memory_usage; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    echo ""
    echo "=== Health Check Summary ==="
    echo "Passed: $checks_passed"
    echo "Failed: $checks_failed"
    
    if [ $exit_code -eq 0 ]; then
        echo "Status: HEALTHY"
    else
        echo "Status: UNHEALTHY"
    fi
    
    echo "==================================="
    
    exit $exit_code
}

# Run health check
main "$@"