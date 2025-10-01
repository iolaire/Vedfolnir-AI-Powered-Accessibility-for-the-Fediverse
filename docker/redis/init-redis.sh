#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Redis initialization script for Vedfolnir Docker container
# Sets up access controls, optimizations, and monitoring

set -e

echo "Initializing Redis for Vedfolnir..."

# Wait for Redis to be ready
until redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; do
    echo "Waiting for Redis to be ready..."
    sleep 2
done

echo "Redis is ready. Configuring access controls and optimizations..."

# Configure Redis for session storage and RQ queue optimization
redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" <<EOF

# Set up access control for application user
ACL SETUSER vedfolnir_app on >${REDIS_PASSWORD} ~vedfolnir:* ~rq:* +@all -flushall -flushdb -debug -config -shutdown

# Configure memory optimization for session data
CONFIG SET hash-max-ziplist-entries 1024
CONFIG SET hash-max-ziplist-value 256
CONFIG SET list-max-ziplist-size -1
CONFIG SET set-max-intset-entries 1024

# Configure persistence settings
CONFIG SET save "900 1 300 10 60 10000 30 100000"
CONFIG SET appendonly yes
CONFIG SET appendfsync everysec

# Configure memory management for session storage
CONFIG SET maxmemory-policy volatile-lru
CONFIG SET maxmemory-samples 10

# Enable keyspace notifications for session expiration tracking
CONFIG SET notify-keyspace-events Ex

# Configure client timeouts
CONFIG SET timeout 300
CONFIG SET tcp-keepalive 60

# Configure slow log for monitoring
CONFIG SET slowlog-log-slower-than 10000
CONFIG SET slowlog-max-len 128

# Configure latency monitoring
CONFIG SET latency-monitor-threshold 100

# Save configuration
CONFIG REWRITE

EOF

echo "Redis configuration completed successfully."

# Create monitoring script for Redis health
cat > /usr/local/bin/redis-health-check.sh << 'HEALTH_EOF'
#!/bin/sh
# Redis health check script for Docker container

# Check Redis ping
if ! redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; then
    echo "Redis ping failed"
    exit 1
fi

# Check memory usage
MEMORY_USAGE=$(redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
echo "Redis memory usage: ${MEMORY_USAGE}"

# Check connected clients
CLIENTS=$(redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
echo "Connected clients: ${CLIENTS}"

# Check keyspace
KEYSPACE=$(redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" info keyspace | grep db0 | cut -d: -f2 | tr -d '\r')
if [ -n "$KEYSPACE" ]; then
    echo "Keyspace db0: ${KEYSPACE}"
else
    echo "Keyspace db0: empty"
fi

# Check replication status
REPLICATION=$(redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" info replication | grep role | cut -d: -f2 | tr -d '\r')
echo "Replication role: ${REPLICATION}"

echo "Redis health check completed successfully"
HEALTH_EOF

chmod +x /usr/local/bin/redis-health-check.sh

echo "Redis initialization completed successfully."