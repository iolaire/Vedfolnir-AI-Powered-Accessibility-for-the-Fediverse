#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Development health check script for Docker containers
# Relaxed health validation for development environment

set -e

# Configuration
HEALTH_ENDPOINT=${HEALTH_CHECK_ENDPOINT:-/health}
APP_PORT=${APP_PORT:-5000}
TIMEOUT=${HEALTH_CHECK_TIMEOUT:-5}
MAX_RETRIES=${HEALTH_CHECK_RETRIES:-2}

# Health check functions (relaxed for development)
check_application_health() {
    local url="http://localhost:${APP_PORT}${HEALTH_ENDPOINT}"
    local retry=0
    
    while [ $retry -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time "$TIMEOUT" "$url" >/dev/null 2>&1; then
            echo "Application: OK"
            return 0
        fi
        
        retry=$((retry + 1))
        if [ $retry -lt $MAX_RETRIES ]; then
            sleep 1
        fi
    done
    
    echo "Application: FAIL - Health endpoint not responding"
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
        socket_timeout=3
    )
    
    r.ping()
    print('Redis: OK')
    sys.exit(0)
except Exception as e:
    print(f'Redis: WARNING - {e}')
    sys.exit(0)  # Non-critical in development
"
        return $?
    else
        echo "Redis: SKIP - No REDIS_URL configured"
        return 0
    fi
}

check_development_tools() {
    local tools_available=0
    
    if command -v debugpy >/dev/null 2>&1; then
        echo "Debugpy: OK"
        tools_available=$((tools_available + 1))
    else
        echo "Debugpy: MISSING"
    fi
    
    if command -v pytest >/dev/null 2>&1; then
        echo "Pytest: OK"
        tools_available=$((tools_available + 1))
    else
        echo "Pytest: MISSING"
    fi
    
    if command -v black >/dev/null 2>&1; then
        echo "Black: OK"
        tools_available=$((tools_available + 1))
    else
        echo "Black: MISSING"
    fi
    
    if [ $tools_available -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

check_debug_ports() {
    local debugpy_port=${DEBUGPY_PORT:-5678}
    
    if [ "$DEBUGPY_ENABLED" = "true" ]; then
        if netstat -ln 2>/dev/null | grep ":$debugpy_port " >/dev/null; then
            echo "Debug Port: OK - Port $debugpy_port is listening"
            return 0
        else
            echo "Debug Port: WARNING - Port $debugpy_port not listening"
            return 0  # Non-critical
        fi
    else
        echo "Debug Port: SKIP - Debugpy disabled"
        return 0
    fi
}

check_file_permissions() {
    local issues=0
    
    if [ ! -w "/app/logs" ]; then
        echo "Permissions: FAIL - /app/logs not writable"
        issues=$((issues + 1))
    fi
    
    if [ ! -w "/app/storage" ]; then
        echo "Permissions: FAIL - /app/storage not writable"
        issues=$((issues + 1))
    fi
    
    if [ ! -w "/app/test-results" ]; then
        echo "Permissions: WARNING - /app/test-results not writable"
        # Non-critical
    fi
    
    if [ $issues -eq 0 ]; then
        echo "Permissions: OK"
        return 0
    else
        return 1
    fi
}

check_process_health() {
    # In development, we might be running Flask directly or with debugpy
    if pgrep -f "python.*web_app.py" >/dev/null || pgrep -f "debugpy.*web_app.py" >/dev/null; then
        echo "Processes: OK - Application process running"
        return 0
    else
        echo "Processes: FAIL - No application process found"
        return 1
    fi
}

# Main development health check function
main() {
    local exit_code=0
    local checks_passed=0
    local checks_failed=0
    local checks_warning=0
    
    echo "=== Vedfolnir Development Health Check ==="
    echo "Timestamp: $(date -Iseconds)"
    echo "Container: $(hostname)"
    echo "Environment: ${FLASK_ENV:-development}"
    echo ""
    
    # Core health checks
    echo "Core Services:"
    
    if check_application_health; then
        checks_passed=$((checks_passed + 1))
    else
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
    
    # Redis is optional in development
    check_redis_connectivity
    checks_passed=$((checks_passed + 1))
    
    echo ""
    echo "Development Tools:"
    
    if check_development_tools; then
        checks_passed=$((checks_passed + 1))
    else
        checks_warning=$((checks_warning + 1))
        echo "Development Tools: WARNING - Some tools missing"
    fi
    
    check_debug_ports
    checks_passed=$((checks_passed + 1))
    
    echo ""
    echo "Environment:"
    
    if check_file_permissions; then
        checks_passed=$((checks_passed + 1))
    else
        checks_failed=$((checks_failed + 1))
        exit_code=1
    fi
    
    # Show environment variables
    echo "Flask Debug: ${FLASK_DEBUG:-0}"
    echo "RQ Workers: ${RQ_ENABLE_INTEGRATED_WORKERS:-false}"
    echo "Log Level: ${LOG_LEVEL:-INFO}"
    
    echo ""
    echo "=== Development Health Check Summary ==="
    echo "Passed: $checks_passed"
    echo "Failed: $checks_failed"
    echo "Warnings: $checks_warning"
    
    if [ $exit_code -eq 0 ]; then
        echo "Status: HEALTHY (Development)"
    else
        echo "Status: UNHEALTHY"
    fi
    
    echo "============================================"
    
    exit $exit_code
}

# Run development health check
main "$@"