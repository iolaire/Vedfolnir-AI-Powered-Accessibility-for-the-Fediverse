# Docker Deployment Guide with MySQL and Redis

This guide provides comprehensive Docker deployment instructions for Vedfolnir using MySQL and Redis, replacing all SQLite-based Docker configurations.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Production Docker Setup](#production-docker-setup)
3. [Docker Compose Configuration](#docker-compose-configuration)
4. [Container Management](#container-management)
5. [Backup and Recovery](#backup-and-recovery)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM available
- 20GB+ disk space

### Rapid Deployment

```bash
# Clone repository
git clone <repository-url> vedfolnir
cd vedfolnir

# Create environment file
cp .env.example .env

# Edit environment variables
nano .env

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec vedfolnir python -c "
from database import init_db
init_db()
print('Database initialized')
"

# Create admin user
docker-compose exec vedfolnir python scripts/setup/init_admin_user.py

# Check status
docker-compose ps
```

## Production Docker Setup

### Directory Structure

```
vedfolnir-production/
├── docker-compose.yml
├── docker-compose.override.yml
├── .env
├── .env.production
├── Dockerfile
├── docker/
│   ├── mysql/
│   │   ├── conf.d/
│   │   │   └── vedfolnir.cnf
│   │   └── init/
│   │       └── 01-init.sql
│   ├── redis/
│   │   └── redis.conf
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── ssl/
│   └── scripts/
│       ├── wait-for-mysql.sh
│       ├── backup.sh
│       └── health-check.sh
├── logs/
├── backups/
└── ssl/
```

### Production Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  vedfolnir:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - BUILD_ENV=production
    image: vedfolnir:latest
    container_name: vedfolnir_app
    restart: unless-stopped
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=mysql+pymysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir?charset=utf8mb4
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
      - ./backups:/app/backups
    networks:
      - vedfolnir_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  mysql:
    image: mysql:8.0
    container_name: vedfolnir_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: vedfolnir
      MYSQL_USER: vedfolnir
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/conf.d:/etc/mysql/conf.d:ro
      - ./docker/mysql/init:/docker-entrypoint-initdb.d:ro
      - ./backups/mysql:/backups
    ports:
      - "127.0.0.1:3306:3306"  # Only bind to localhost
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --innodb-buffer-pool-size=1G
      --innodb-log-file-size=256M
      --max-connections=200
      --slow-query-log=1
      --slow-query-log-file=/var/log/mysql/slow.log
      --long-query-time=2
    networks:
      - vedfolnir_network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "vedfolnir", "-p${MYSQL_PASSWORD}"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

  redis:
    image: redis:7-alpine
    container_name: vedfolnir_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
      - ./docker/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
    ports:
      - "127.0.0.1:6379:6379"  # Only bind to localhost
    command: redis-server /usr/local/etc/redis/redis.conf
    networks:
      - vedfolnir_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    container_name: vedfolnir_ollama
    restart: unless-stopped
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "127.0.0.1:11434:11434"
    environment:
      - OLLAMA_ORIGINS=*
    networks:
      - vedfolnir_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/version"]
      interval: 60s
      timeout: 30s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: vedfolnir_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - vedfolnir
    networks:
      - vedfolnir_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local
  ollama_data:
    driver: local

networks:
  vedfolnir_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Production Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    default-mysql-client \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r vedfolnir && useradd -r -g vedfolnir vedfolnir
RUN chown -R vedfolnir:vedfolnir /app

# Create necessary directories
RUN mkdir -p storage/images logs backups && \
    chown -R vedfolnir:vedfolnir storage logs backups

# Copy and set up scripts
COPY docker/scripts/wait-for-mysql.sh /usr/local/bin/
COPY docker/scripts/health-check.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh

# Switch to non-root user
USER vedfolnir

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/health-check.sh

EXPOSE 5000

CMD ["/usr/local/bin/wait-for-mysql.sh", "mysql", "python", "web_app.py"]
```

### Configuration Files

#### MySQL Configuration
```ini
# docker/mysql/conf.d/vedfolnir.cnf
[mysqld]
# Character set
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# InnoDB settings
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_log_buffer_size = 16M
innodb_flush_log_at_trx_commit = 2
innodb_file_per_table = 1

# Connection settings
max_connections = 200
max_connect_errors = 1000
connect_timeout = 60
wait_timeout = 28800

# Logging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
log_queries_not_using_indexes = 1

# Security
local_infile = 0
```

#### Redis Configuration
```conf
# docker/redis/redis.conf
# Network
bind 0.0.0.0
port 6379
timeout 300

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Security
requirepass ${REDIS_PASSWORD}

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
```

#### Nginx Configuration
```nginx
# docker/nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream vedfolnir {
        server vedfolnir:5000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    server {
        listen 80;
        server_name _;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name _;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://vedfolnir;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        location /auth/login {
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://vedfolnir;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://vedfolnir/health;
            access_log off;
        }
    }
}
```

### Helper Scripts

#### Wait for MySQL Script
```bash
#!/bin/bash
# docker/scripts/wait-for-mysql.sh
set -e

host="$1"
shift
cmd="$@"

until mysql -h"$host" -u"vedfolnir" -p"$MYSQL_PASSWORD" -e 'SELECT 1' vedfolnir >/dev/null 2>&1; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 2
done

>&2 echo "MySQL is up - executing command"
exec $cmd
```

#### Health Check Script
```bash
#!/bin/bash
# docker/scripts/health-check.sh
set -e

# Check application health
if ! curl -f http://localhost:5000/health >/dev/null 2>&1; then
    echo "Application health check failed"
    exit 1
fi

# Check database connection
if ! python -c "
from database import get_db_connection
try:
    conn = get_db_connection()
    conn.close()
    print('Database connection OK')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" >/dev/null 2>&1; then
    echo "Database health check failed"
    exit 1
fi

echo "Health check passed"
```

## Container Management

### Deployment Commands

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Development deployment
docker-compose up -d

# Update application
docker-compose pull
docker-compose up -d --build vedfolnir

# Scale application (if using load balancer)
docker-compose up -d --scale vedfolnir=3

# View logs
docker-compose logs -f vedfolnir
docker-compose logs -f mysql
docker-compose logs -f redis

# Execute commands in containers
docker-compose exec vedfolnir bash
docker-compose exec mysql mysql -u vedfolnir -p vedfolnir
docker-compose exec redis redis-cli
```

### Service Management

```bash
# Start specific services
docker-compose up -d mysql redis
docker-compose up -d vedfolnir

# Restart services
docker-compose restart vedfolnir
docker-compose restart mysql

# Stop services
docker-compose stop
docker-compose down

# Remove everything (including volumes)
docker-compose down -v --remove-orphans
```

## Backup and Recovery

### Automated Backup Script

```bash
#!/bin/bash
# docker/scripts/backup.sh

set -euo pipefail

BACKUP_DIR="/app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# MySQL backup
docker-compose exec -T mysql mysqldump \
    -u vedfolnir \
    -p"$MYSQL_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    vedfolnir | gzip > "$BACKUP_DIR/mysql_$DATE.sql.gz"

# Redis backup
docker-compose exec redis redis-cli BGSAVE
docker cp vedfolnir_redis:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Application data backup
tar -czf "$BACKUP_DIR/storage_$DATE.tar.gz" storage/

# Cleanup old backups
find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.rdb" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

### Recovery Procedures

```bash
# Restore MySQL database
gunzip -c backup_file.sql.gz | docker-compose exec -T mysql mysql -u vedfolnir -p"$MYSQL_PASSWORD" vedfolnir

# Restore Redis data
docker-compose stop redis
docker cp backup_file.rdb vedfolnir_redis:/data/dump.rdb
docker-compose start redis

# Restore application data
tar -xzf storage_backup.tar.gz
```

## Monitoring and Logging

### Log Management

```yaml
# Add to docker-compose.yml services
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Monitoring Stack

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - vedfolnir_network

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - vedfolnir_network

volumes:
  grafana_data:
```

### Health Monitoring

```bash
# Monitor container health
docker-compose ps
docker stats

# Check service health
curl http://localhost/health
docker-compose exec mysql mysqladmin ping
docker-compose exec redis redis-cli ping

# Monitor logs in real-time
docker-compose logs -f --tail=100 vedfolnir
```

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs vedfolnir

# Check resource usage
docker stats

# Verify environment variables
docker-compose config
```

**Database connection issues:**
```bash
# Test MySQL connectivity
docker-compose exec vedfolnir mysql -h mysql -u vedfolnir -p vedfolnir

# Check MySQL logs
docker-compose logs mysql

# Verify network connectivity
docker-compose exec vedfolnir ping mysql
```

**Performance issues:**
```bash
# Monitor resource usage
docker stats

# Check MySQL performance
docker-compose exec mysql mysql -u vedfolnir -p -e "SHOW PROCESSLIST;"

# Monitor Redis memory usage
docker-compose exec redis redis-cli info memory
```

### Debug Mode

```yaml
# docker-compose.debug.yml
version: '3.8'

services:
  vedfolnir:
    environment:
      - FLASK_DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - .:/app  # Mount source code for development
    ports:
      - "5000:5000"  # Expose port for debugging
```

This comprehensive Docker deployment guide ensures a robust, scalable, and maintainable MySQL-based deployment for Vedfolnir.
