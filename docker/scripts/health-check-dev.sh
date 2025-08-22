#!/bin/bash
# Development health check script for Vedfolnir Docker container

set -e

# Check if the web application is responding
if ! curl -f http://localhost:5000/health >/dev/null 2>&1; then
    echo "❌ Development web application health check failed"
    exit 1
fi

# Check MySQL connection (development database)
if ! python3 -c "
from database import get_db_connection
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    result = cursor.fetchone()
    conn.close()
    if result[0] != 1:
        raise Exception('Invalid result')
except Exception as e:
    print(f'❌ Development MySQL health check failed: {e}')
    exit(1)
" >/dev/null 2>&1; then
    echo "❌ Development MySQL health check failed"
    exit 1
fi

# Check Redis connection (development)
if [ -n "$REDIS_HOST" ]; then
    if ! redis-cli -h "$REDIS_HOST" -p "${REDIS_PORT:-6379}" ping >/dev/null 2>&1; then
        echo "❌ Development Redis health check failed"
        exit 1
    fi
fi

echo "✅ Development health checks passed"
exit 0
