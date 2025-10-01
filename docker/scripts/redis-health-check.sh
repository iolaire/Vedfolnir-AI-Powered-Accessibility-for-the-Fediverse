#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Redis health check script for Docker container
# Used by Docker Compose healthcheck

set -e

# Get Redis password from environment or secrets
if [ -f "/run/secrets/redis_password" ]; then
    REDIS_PASSWORD=$(cat /run/secrets/redis_password)
elif [ -n "$REDIS_PASSWORD" ]; then
    # Use environment variable
    REDIS_PASSWORD="$REDIS_PASSWORD"
else
    echo "Redis password not found"
    exit 1
fi

# Basic ping test
if ! redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
    echo "Redis ping failed"
    exit 1
fi

# Test basic operations
if ! redis-cli --no-auth-warning -a "$REDIS_PASSWORD" set health_check_key "$(date)" EX 60 > /dev/null 2>&1; then
    echo "Redis SET operation failed"
    exit 1
fi

if ! redis-cli --no-auth-warning -a "$REDIS_PASSWORD" get health_check_key > /dev/null 2>&1; then
    echo "Redis GET operation failed"
    exit 1
fi

# Clean up test key
redis-cli --no-auth-warning -a "$REDIS_PASSWORD" del health_check_key > /dev/null 2>&1

# Check memory usage (warn if > 90%)
MEMORY_INFO=$(redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info memory)
USED_MEMORY=$(echo "$MEMORY_INFO" | grep "^used_memory:" | cut -d: -f2 | tr -d '\r')
MAX_MEMORY=$(echo "$MEMORY_INFO" | grep "^maxmemory:" | cut -d: -f2 | tr -d '\r')

if [ "$MAX_MEMORY" -gt 0 ]; then
    MEMORY_USAGE_PERCENT=$((USED_MEMORY * 100 / MAX_MEMORY))
    if [ "$MEMORY_USAGE_PERCENT" -gt 90 ]; then
        echo "Warning: Redis memory usage is ${MEMORY_USAGE_PERCENT}%"
    fi
fi

# Check replication status
REPLICATION_INFO=$(redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info replication)
ROLE=$(echo "$REPLICATION_INFO" | grep "^role:" | cut -d: -f2 | tr -d '\r')

if [ "$ROLE" != "master" ] && [ "$ROLE" != "slave" ]; then
    echo "Redis replication role is invalid: $ROLE"
    exit 1
fi

# Check persistence status
PERSISTENCE_INFO=$(redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info persistence)
RDB_LAST_SAVE=$(echo "$PERSISTENCE_INFO" | grep "^rdb_last_save_time:" | cut -d: -f2 | tr -d '\r')
CURRENT_TIME=$(date +%s)
TIME_SINCE_SAVE=$((CURRENT_TIME - RDB_LAST_SAVE))

# Warn if no save in last 24 hours (86400 seconds)
if [ "$TIME_SINCE_SAVE" -gt 86400 ]; then
    echo "Warning: Redis RDB last save was $TIME_SINCE_SAVE seconds ago"
fi

# Check for AOF if enabled
AOF_ENABLED=$(echo "$PERSISTENCE_INFO" | grep "^aof_enabled:" | cut -d: -f2 | tr -d '\r')
if [ "$AOF_ENABLED" = "1" ]; then
    AOF_LAST_REWRITE=$(echo "$PERSISTENCE_INFO" | grep "^aof_last_rewrite_time_sec:" | cut -d: -f2 | tr -d '\r')
    if [ "$AOF_LAST_REWRITE" = "-1" ]; then
        echo "Warning: AOF has never been rewritten"
    fi
fi

echo "Redis health check passed"
exit 0