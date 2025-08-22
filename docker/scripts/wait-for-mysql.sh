#!/bin/bash
# Wait for MySQL to be ready before starting the application
# This script replaces any SQLite-based initialization

set -e

host="$1"
shift
cmd="$@"

# Default MySQL connection parameters
MYSQL_HOST="${host:-mysql}"
MYSQL_PORT="${DB_PORT:-3306}"
MYSQL_USER="${DB_USER:-vedfolnir}"
MYSQL_PASSWORD="${DB_PASSWORD}"
MYSQL_DATABASE="${DB_NAME:-vedfolnir}"

echo "Waiting for MySQL at $MYSQL_HOST:$MYSQL_PORT..."

# Wait for MySQL to be ready
max_attempts=60
attempt=1

while [ $attempt -le $max_attempts ]; do
    if mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" "$MYSQL_DATABASE" >/dev/null 2>&1; then
        echo "✅ MySQL is ready at $MYSQL_HOST:$MYSQL_PORT"
        break
    fi
    
    echo "⏳ Waiting for MySQL... (attempt $attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ MySQL is not ready after $max_attempts attempts"
    exit 1
fi

# Wait for Redis if configured
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis at $REDIS_HOST:${REDIS_PORT:-6379}..."
    
    redis_attempts=30
    redis_attempt=1
    
    while [ $redis_attempt -le $redis_attempts ]; do
        if redis-cli -h "$REDIS_HOST" -p "${REDIS_PORT:-6379}" ${REDIS_PASSWORD:+-a "$REDIS_PASSWORD"} ping >/dev/null 2>&1; then
            echo "✅ Redis is ready at $REDIS_HOST:${REDIS_PORT:-6379}"
            break
        fi
        
        echo "⏳ Waiting for Redis... (attempt $redis_attempt/$redis_attempts)"
        sleep 1
        redis_attempt=$((redis_attempt + 1))
    done
    
    if [ $redis_attempt -gt $redis_attempts ]; then
        echo "⚠️ Redis is not ready, but continuing anyway"
    fi
fi

echo "🚀 Starting application: $cmd"
exec $cmd
