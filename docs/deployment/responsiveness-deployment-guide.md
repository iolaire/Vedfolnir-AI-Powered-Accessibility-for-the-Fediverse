# Responsiveness Monitoring Deployment Guide

## Overview

This guide covers deployment considerations, configuration, and best practices for implementing the Flask App Responsiveness Monitoring system in production environments. It provides step-by-step instructions for various deployment scenarios.

## Pre-Deployment Requirements

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores, 2.4 GHz
- **Memory**: 4 GB RAM
- **Storage**: 20 GB available space
- **Network**: Stable internet connection
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)

#### Recommended Requirements
- **CPU**: 4+ cores, 3.0 GHz
- **Memory**: 8+ GB RAM
- **Storage**: 50+ GB SSD storage
- **Network**: High-speed connection with low latency
- **OS**: Linux with systemd support

#### Production Requirements
- **CPU**: 8+ cores, 3.2 GHz
- **Memory**: 16+ GB RAM
- **Storage**: 100+ GB NVMe SSD
- **Network**: Redundant network connections
- **OS**: Enterprise Linux distribution

### Software Dependencies

#### Core Dependencies
```bash
# Python and package management
python3.8+
pip3
virtualenv

# Database systems
mysql-server 8.0+
redis-server 6.0+

# System monitoring tools
htop
iotop
nethogs
```

#### Optional Dependencies
```bash
# Performance monitoring
prometheus
grafana
node_exporter

# Log management
logrotate
rsyslog

# Process management
supervisor
systemd
```

## Deployment Scenarios

### 1. Single Server Deployment

#### Architecture Overview
```
┌─────────────────────────────────────┐
│           Single Server             │
├─────────────────────────────────────┤
│  Flask App + Responsiveness Monitor │
│  MySQL Database                     │
│  Redis Cache                        │
│  Web Server (Nginx/Apache)         │
└─────────────────────────────────────┘
```

#### Installation Steps
```bash
# 1. System preparation
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv mysql-server redis-server nginx -y

# 2. Create application user
sudo useradd -m -s /bin/bash vedfolnir
sudo usermod -aG sudo vedfolnir

# 3. Setup application directory
sudo mkdir -p /opt/vedfolnir
sudo chown vedfolnir:vedfolnir /opt/vedfolnir
cd /opt/vedfolnir

# 4. Clone and setup application
git clone <repository-url> .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Configure databases
sudo mysql_secure_installation
mysql -u root -p < scripts/setup/create_database.sql

# 6. Configure Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 7. Setup environment configuration
cp .env.example .env
python scripts/setup/generate_env_secrets.py
```

#### Configuration Files

**Environment Configuration** (`.env`):
```bash
# Application settings
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=<generated-secret-key>

# Database configuration
DATABASE_URL=mysql+pymysql://vedfolnir_user:secure_password@localhost/vedfolnir?charset=utf8mb4
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Redis configuration
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_PREFIX=vedfolnir:session:
REDIS_SESSION_TIMEOUT=7200

# Responsiveness monitoring
RESPONSIVENESS_MONITORING_ENABLED=true
RESPONSIVENESS_MONITORING_INTERVAL=30
RESPONSIVENESS_MEMORY_WARNING_THRESHOLD=0.8
RESPONSIVENESS_MEMORY_CRITICAL_THRESHOLD=0.9
RESPONSIVENESS_CPU_WARNING_THRESHOLD=0.8
RESPONSIVENESS_CPU_CRITICAL_THRESHOLD=0.9
RESPONSIVENESS_CLEANUP_ENABLED=true
RESPONSIVENESS_CLEANUP_INTERVAL=300
```

**Systemd Service** (`/etc/systemd/system/vedfolnir.service`):
```ini
[Unit]
Description=Vedfolnir Flask Application
After=network.target mysql.service redis.service
Requires=mysql.service redis.service

[Service]
Type=simple
User=vedfolnir
Group=vedfolnir
WorkingDirectory=/opt/vedfolnir
Environment=PATH=/opt/vedfolnir/venv/bin
ExecStart=/opt/vedfolnir/venv/bin/python web_app.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Nginx Configuration** (`/etc/nginx/sites-available/vedfolnir`):
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL configuration
    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Static files
    location /static {
        alias /opt/vedfolnir/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Application proxy
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }
}
```

### 2. Multi-Server Deployment

#### Architecture Overview
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Load Balancer │  │   App Server 1  │  │   App Server 2  │
│     (Nginx)     │  │  Flask + Monitor│  │  Flask + Monitor│
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  MySQL Cluster  │  │  Redis Cluster  │  │  Shared Storage │
│   (Primary/     │  │   (Master/      │  │   (NFS/GlusterFS│
│    Replica)     │  │    Replica)     │  │    /Ceph)       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

#### Load Balancer Configuration
```nginx
upstream vedfolnir_backend {
    least_conn;
    server app1.internal:5000 max_fails=3 fail_timeout=30s;
    server app2.internal:5000 max_fails=3 fail_timeout=30s;
    
    # Health checks
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://vedfolnir_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Session affinity for WebSocket connections
        ip_hash;
        
        # Health checks
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### Database Cluster Configuration
```bash
# MySQL Master-Slave setup
# Master server configuration (my.cnf)
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
gtid-mode = ON
enforce-gtid-consistency = ON

# Slave server configuration (my.cnf)
[mysqld]
server-id = 2
relay-log = mysql-relay-bin
log-slave-updates = ON
gtid-mode = ON
enforce-gtid-consistency = ON
read-only = ON
```

#### Redis Cluster Configuration
```bash
# Redis Master configuration (redis.conf)
port 6379
bind 0.0.0.0
protected-mode yes
requirepass your-redis-password
save 900 1
save 300 10
save 60 10000

# Redis Sentinel configuration (sentinel.conf)
port 26379
sentinel monitor vedfolnir-redis 192.168.1.10 6379 2
sentinel auth-pass vedfolnir-redis your-redis-password
sentinel down-after-milliseconds vedfolnir-redis 5000
sentinel failover-timeout vedfolnir-redis 10000
```

### 3. Container Deployment (Docker)

#### Docker Compose Configuration
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=mysql+pymysql://vedfolnir:password@db:3306/vedfolnir
      - REDIS_URL=redis://redis:6379/0
      - RESPONSIVENESS_MONITORING_ENABLED=true
    depends_on:
      - db
      - redis
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=vedfolnir
      - MYSQL_USER=vedfolnir
      - MYSQL_PASSWORD=password
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/my.cnf:/etc/mysql/conf.d/my.cnf
    ports:
      - "3306:3306"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:6.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./docker/redis/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/nginx/ssl:/etc/nginx/ssl
      - ./static:/var/www/static
    depends_on:
      - app
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:
```

#### Dockerfile
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd -m -s /bin/bash vedfolnir

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs storage/images storage/backups

# Set ownership
RUN chown -R vedfolnir:vedfolnir /app

# Switch to application user
USER vedfolnir

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start application
CMD ["python", "web_app.py"]
```

## Configuration Management

### Environment-Specific Configurations

#### Development Configuration
```bash
# Development environment settings
FLASK_ENV=development
FLASK_DEBUG=true
RESPONSIVENESS_MONITORING_INTERVAL=60
RESPONSIVENESS_CLEANUP_INTERVAL=600
LOG_LEVEL=DEBUG
```

#### Staging Configuration
```bash
# Staging environment settings
FLASK_ENV=staging
FLASK_DEBUG=false
RESPONSIVENESS_MONITORING_INTERVAL=45
RESPONSIVENESS_CLEANUP_INTERVAL=450
LOG_LEVEL=INFO
```

#### Production Configuration
```bash
# Production environment settings
FLASK_ENV=production
FLASK_DEBUG=false
RESPONSIVENESS_MONITORING_INTERVAL=30
RESPONSIVENESS_CLEANUP_INTERVAL=300
LOG_LEVEL=WARNING
```

### Configuration Validation

#### Pre-Deployment Validation Script
```bash
#!/bin/bash
# validate_deployment.sh

echo "=== Deployment Configuration Validation ==="

# Check required environment variables
required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "SECRET_KEY"
    "RESPONSIVENESS_MONITORING_ENABLED"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    else
        echo "✅ $var is set"
    fi
done

# Test database connectivity
echo "Testing database connectivity..."
if python -c "from app.core.database.core.database_manager import DatabaseManager; from config import Config; DatabaseManager(Config()).test_mysql_connection()" 2>/dev/null; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed"
    exit 1
fi

# Test Redis connectivity
echo "Testing Redis connectivity..."
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis connection successful"
else
    echo "❌ Redis connection failed"
    exit 1
fi

# Validate responsiveness configuration
echo "Validating responsiveness configuration..."
python -c "
from config import Config
config = Config()
rc = config.responsiveness_config
assert 0 < rc.memory_warning_threshold < 1, 'Invalid memory warning threshold'
assert 0 < rc.memory_critical_threshold < 1, 'Invalid memory critical threshold'
assert rc.memory_warning_threshold < rc.memory_critical_threshold, 'Warning threshold must be less than critical'
print('✅ Responsiveness configuration valid')
"

echo "=== Validation Complete ==="
```

## Performance Optimization

### System-Level Optimizations

#### Kernel Parameters
```bash
# /etc/sysctl.conf optimizations
# Network optimizations
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 10

# Memory optimizations
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# File system optimizations
fs.file-max = 2097152
fs.nr_open = 1048576

# Apply changes
sudo sysctl -p
```

#### System Limits
```bash
# /etc/security/limits.conf
vedfolnir soft nofile 65535
vedfolnir hard nofile 65535
vedfolnir soft nproc 32768
vedfolnir hard nproc 32768

# /etc/systemd/system.conf
DefaultLimitNOFILE=65535
DefaultLimitNPROC=32768
```

### Application-Level Optimizations

#### Production Configuration Tuning
```bash
# High-performance production settings
RESPONSIVENESS_MONITORING_INTERVAL=15
RESPONSIVENESS_CLEANUP_INTERVAL=180
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
REDIS_CONNECTION_POOL_SIZE=50
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_WORKER_CONNECTIONS=1000
```

#### Database Optimizations
```sql
-- MySQL performance tuning
SET GLOBAL innodb_buffer_pool_size = 2147483648; -- 2GB
SET GLOBAL innodb_log_file_size = 268435456; -- 256MB
SET GLOBAL innodb_flush_log_at_trx_commit = 2;
SET GLOBAL query_cache_size = 134217728; -- 128MB
SET GLOBAL query_cache_type = 1;
SET GLOBAL max_connections = 200;
SET GLOBAL thread_cache_size = 16;
SET GLOBAL table_open_cache = 4000;
```

#### Redis Optimizations
```bash
# Redis performance tuning (redis.conf)
maxmemory 1gb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
tcp-backlog 511
databases 16
save 900 1
save 300 10
save 60 10000
```

## Monitoring and Alerting

### System Monitoring Setup

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "vedfolnir_rules.yml"

scrape_configs:
  - job_name: 'vedfolnir'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "Vedfolnir Responsiveness Monitoring",
    "panels": [
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "vedfolnir_memory_usage_percent",
            "legendFormat": "Memory Usage %"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "vedfolnir_response_time_seconds",
            "legendFormat": "Response Time"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "vedfolnir_db_connections_active",
            "legendFormat": "Active Connections"
          }
        ]
      }
    ]
  }
}
```

### Alert Rules

#### Prometheus Alert Rules
```yaml
# vedfolnir_rules.yml
groups:
  - name: vedfolnir_alerts
    rules:
      - alert: HighMemoryUsage
        expr: vedfolnir_memory_usage_percent > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is {{ $value }}% for more than 5 minutes"

      - alert: CriticalMemoryUsage
        expr: vedfolnir_memory_usage_percent > 95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical memory usage detected"
          description: "Memory usage is {{ $value }}% for more than 2 minutes"

      - alert: SlowResponseTime
        expr: vedfolnir_response_time_seconds > 5
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time detected"
          description: "Average response time is {{ $value }}s for more than 3 minutes"

      - alert: DatabaseConnectionPoolExhaustion
        expr: vedfolnir_db_connection_pool_utilization > 90
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "Connection pool utilization is {{ $value }}%"
```

## Security Considerations

### Network Security

#### Firewall Configuration
```bash
# UFW firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from 10.0.0.0/8 to any port 3306  # MySQL internal
sudo ufw allow from 10.0.0.0/8 to any port 6379  # Redis internal
sudo ufw enable
```

#### SSL/TLS Configuration
```bash
# Generate SSL certificate (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Or use custom certificate
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/vedfolnir.key \
    -out /etc/nginx/ssl/vedfolnir.crt
```

### Application Security

#### Security Headers Configuration
```python
# security_config.py
SECURITY_HEADERS = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    'Referrer-Policy': 'strict-origin-when-cross-origin'
}
```

#### Database Security
```sql
-- Create dedicated database user with minimal privileges
CREATE USER 'vedfolnir_app'@'localhost' IDENTIFIED BY 'secure_random_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON vedfolnir.* TO 'vedfolnir_app'@'localhost';
FLUSH PRIVILEGES;

-- Remove unnecessary privileges
REVOKE ALL PRIVILEGES ON *.* FROM 'vedfolnir_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON vedfolnir.* TO 'vedfolnir_app'@'localhost';
```

## Backup and Recovery

### Automated Backup Strategy

#### Database Backup Script
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/opt/vedfolnir/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="vedfolnir"
DB_USER="backup_user"
DB_PASS="backup_password"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
mysqldump -u $DB_USER -p$DB_PASS --single-transaction --routines --triggers $DB_NAME > $BACKUP_DIR/vedfolnir_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/vedfolnir_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "vedfolnir_*.sql.gz" -mtime +30 -delete

echo "Database backup completed: vedfolnir_$DATE.sql.gz"
```

#### Redis Backup Script
```bash
#!/bin/bash
# backup_redis.sh

BACKUP_DIR="/opt/vedfolnir/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Create Redis backup
redis-cli BGSAVE
sleep 10  # Wait for background save to complete

# Copy RDB file
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Compress backup
gzip $BACKUP_DIR/redis_$DATE.rdb

echo "Redis backup completed: redis_$DATE.rdb.gz"
```

#### Automated Backup Scheduling
```bash
# Add to crontab
0 2 * * * /opt/vedfolnir/scripts/backup_database.sh >> /var/log/vedfolnir_backup.log 2>&1
15 2 * * * /opt/vedfolnir/scripts/backup_redis.sh >> /var/log/vedfolnir_backup.log 2>&1
```

### Disaster Recovery Procedures

#### Database Recovery
```bash
# Stop application
sudo systemctl stop vedfolnir

# Restore database from backup
gunzip -c /opt/vedfolnir/backups/vedfolnir_20250106_020000.sql.gz | mysql -u root -p vedfolnir

# Restart application
sudo systemctl start vedfolnir
```

#### Redis Recovery
```bash
# Stop Redis
sudo systemctl stop redis

# Restore Redis data
gunzip -c /opt/vedfolnir/backups/redis_20250106_020000.rdb.gz > /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis
```

## Post-Deployment Verification

### Deployment Verification Checklist

#### Functional Testing
```bash
# 1. Application health check
curl -f http://localhost:5000/health

# 2. Admin dashboard access
curl -f http://localhost:5000/admin

# 3. Database connectivity
python -c "from app.core.database.core.database_manager import DatabaseManager; from config import Config; print(DatabaseManager(Config()).test_mysql_connection())"

# 4. Redis connectivity
redis-cli ping

# 5. Responsiveness monitoring
curl -f http://localhost:5000/admin/api/health/responsiveness
```

#### Performance Testing
```bash
# Load testing with Apache Bench
ab -n 1000 -c 10 http://localhost:5000/

# Memory usage monitoring
watch -n 5 'free -h'

# Database performance
mysql -u root -p -e "SHOW PROCESSLIST;"
```

#### Security Testing
```bash
# SSL certificate validation
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Security headers check
curl -I https://your-domain.com

# Port scanning
nmap -sS -O localhost
```

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks
- Monitor system health and alerts
- Review application logs for errors
- Check backup completion status
- Verify responsiveness metrics

#### Weekly Tasks
- Analyze performance trends
- Review and optimize slow queries
- Update system packages
- Test backup restoration procedures

#### Monthly Tasks
- Security updates and patches
- Performance optimization review
- Capacity planning assessment
- Documentation updates

### Maintenance Scripts

#### System Health Check
```bash
#!/bin/bash
# system_health_check.sh

echo "=== System Health Check - $(date) ==="

# Check disk space
df -h | grep -E "(/$|/opt|/var)"

# Check memory usage
free -h

# Check CPU load
uptime

# Check service status
systemctl status vedfolnir mysql redis nginx

# Check log errors
tail -50 /var/log/vedfolnir/webapp.log | grep -i error

echo "=== Health Check Complete ==="
```

This deployment guide provides comprehensive coverage of responsiveness monitoring deployment scenarios. For additional support or specific deployment questions, refer to the technical documentation or contact the development team.