#!/bin/bash
# Health check script for Vedfolnir Docker container with MySQL

set -e

# Check if the web application is responding
if ! curl -f http://localhost:5000/health >/dev/null 2>&1; then
    echo "❌ Web application health check failed"
    exit 1
fi

# Check MySQL connection
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
    print('✅ MySQL connection healthy')
except Exception as e:
    print(f'❌ MySQL health check failed: {e}')
    exit(1)
" >/dev/null 2>&1; then
    echo "❌ MySQL health check failed"
    exit 1
fi

# Check Redis connection if configured
if [ -n "$REDIS_HOST" ]; then
    if ! redis-cli -h "$REDIS_HOST" -p "${REDIS_PORT:-6379}" ${REDIS_PASSWORD:+-a "$REDIS_PASSWORD"} ping >/dev/null 2>&1; then
        echo "❌ Redis health check failed"
        exit 1
    fi
fi

echo "✅ All health checks passed"
exit 0
