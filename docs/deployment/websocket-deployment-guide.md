# WebSocket Deployment Guide

## Overview

This guide provides comprehensive deployment instructions for the WebSocket CORS standardization system across development, staging, and production environments. It covers environment setup, configuration management, and deployment best practices.

## Development Environment Deployment

### Prerequisites

- Python 3.8+
- Redis server (for session management)
- MySQL/MariaDB database
- Node.js (for frontend development)

### Setup Steps

1. **Clone and Setup Repository**:
   ```bash
   git clone <repository-url>
   cd vedfolnir
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   ```bash
   # Start MySQL service
   sudo systemctl start mysql  # Linux
   brew services start mysql   # macOS
   
   # Create database
   mysql -u root -p
   CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'vedfolnir_dev'@'localhost' IDENTIFIED BY 'dev_password';
   GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_dev'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

3. **Redis Setup**:
   ```bash
   # Install and start Redis
   sudo systemctl start redis  # Linux
   brew services start redis   # macOS
   
   # Test Redis connection
   redis-cli ping  # Should return PONG
   ```

4. **Environment Configuration**:
   ```bash
   # Copy development environment template
   cp config/websocket.env.development .env
   
   # Edit configuration
   nano .env
   ```

   **Development .env Configuration**:
   ```bash
   # Flask Configuration
   FLASK_HOST=localhost
   FLASK_PORT=5000
   FLASK_ENV=development
   FLASK_DEBUG=true
   FLASK_SECRET_KEY=dev-secret-key-change-in-production
   
   # Database Configuration
   DATABASE_URL=mysql+pymysql://vedfolnir_dev:dev_password@localhost/vedfolnir?charset=utf8mb4
   
   # Redis Configuration
   REDIS_URL=redis://localhost:6379/0
   
   # WebSocket Development Settings
   SOCKETIO_DEBUG=true
   SOCKETIO_LOG_LEVEL=DEBUG
   SOCKETIO_CORS_CREDENTIALS=true
   SOCKETIO_TRANSPORTS=websocket,polling
   SOCKETIO_CSRF_PROTECTION=false
   SOCKETIO_RATE_LIMITING=false
   SOCKETIO_MAX_CONNECTIONS_PER_USER=10
   
   # Development Security (relaxed)
   SESSION_COOKIE_SECURE=false
   SESSION_COOKIE_SAMESITE=Lax
   ```

5. **Database Migration**:
   ```bash
   # Run database migrations
   python scripts/setup/init_database.py
   
   # Create admin user
   python scripts/setup/init_admin_user.py
   ```

6. **Start Development Server**:
   ```bash
   # Start the application (non-blocking for development)
   python web_app.py & sleep 10
   
   # Verify WebSocket functionality
   python scripts/test_websocket_connection.py
   ```

7. **Frontend Development Setup**:
   ```bash
   # Install frontend dependencies (if applicable)
   npm install
   
   # Start frontend development server
   npm run dev
   ```

### Development Testing

```bash
# Test WebSocket CORS configuration
python scripts/test_websocket_cors.py --environment development

# Test authentication integration
python scripts/test_websocket_auth.py

# Run comprehensive WebSocket tests
python -m unittest discover tests/websocket -v
```

## Staging Environment Deployment

### Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Docker and Docker Compose (optional)
- SSL certificate for HTTPS
- Domain name configured

### Setup Steps

1. **Server Preparation**:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install required packages
   sudo apt install -y python3 python3-pip python3-venv nginx mysql-server redis-server
   
   # Configure firewall
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS
   sudo ufw enable
   ```

2. **Application Deployment**:
   ```bash
   # Create application user
   sudo useradd -m -s /bin/bash vedfolnir
   sudo su - vedfolnir
   
   # Clone repository
   git clone <repository-url>
   cd vedfolnir
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Database Configuration**:
   ```bash
   # Secure MySQL installation
   sudo mysql_secure_installation
   
   # Create staging database
   sudo mysql -u root -p
   CREATE DATABASE vedfolnir_staging CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'vedfolnir_staging'@'localhost' IDENTIFIED BY 'secure_staging_password';
   GRANT ALL PRIVILEGES ON vedfolnir_staging.* TO 'vedfolnir_staging'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

4. **Redis Configuration**:
   ```bash
   # Configure Redis for staging
   sudo nano /etc/redis/redis.conf
   
   # Add password authentication
   requirepass staging_redis_password
   
   # Restart Redis
   sudo systemctl restart redis
   ```

5. **Environment Configuration**:
   ```bash
   # Copy staging environment template
   cp config/websocket.env.staging .env
   
   # Edit configuration
   nano .env
   ```

   **Staging .env Configuration**:
   ```bash
   # Flask Configuration
   FLASK_HOST=staging.example.com
   FLASK_PORT=443
   FLASK_ENV=staging
   FLASK_DEBUG=false
   FLASK_SECRET_KEY=secure-staging-secret-key
   
   # Database Configuration
   DATABASE_URL=mysql+pymysql://vedfolnir_staging:secure_staging_password@localhost/vedfolnir_staging?charset=utf8mb4
   
   # Redis Configuration
   REDIS_URL=redis://:staging_redis_password@localhost:6379/0
   
   # WebSocket Staging Settings
   SOCKETIO_DEBUG=false
   SOCKETIO_LOG_LEVEL=INFO
   SOCKETIO_CORS_CREDENTIALS=true
   SOCKETIO_TRANSPORTS=websocket,polling
   SOCKETIO_CSRF_PROTECTION=true
   SOCKETIO_RATE_LIMITING=true
   SOCKETIO_MAX_CONNECTIONS_PER_USER=5
   
   # Staging Security
   SESSION_COOKIE_SECURE=true
   SESSION_COOKIE_SAMESITE=Lax
   
   # SSL Configuration
   SSL_CERT_PATH=/etc/ssl/certs/staging.example.com.crt
   SSL_KEY_PATH=/etc/ssl/private/staging.example.com.key
   ```

6. **SSL Certificate Setup**:
   ```bash
   # Using Let's Encrypt (recommended)
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d staging.example.com
   
   # Or upload custom certificates
   sudo cp staging.example.com.crt /etc/ssl/certs/
   sudo cp staging.example.com.key /etc/ssl/private/
   sudo chmod 600 /etc/ssl/private/staging.example.com.key
   ```

7. **Nginx Configuration**:
   ```bash
   # Create Nginx configuration
   sudo nano /etc/nginx/sites-available/vedfolnir-staging
   ```

   **Nginx Configuration**:
   ```nginx
   server {
       listen 80;
       server_name staging.example.com;
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl http2;
       server_name staging.example.com;
   
       ssl_certificate /etc/ssl/certs/staging.example.com.crt;
       ssl_certificate_key /etc/ssl/private/staging.example.com.key;
   
       # SSL configuration
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
       ssl_prefer_server_ciphers off;
   
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   
       # WebSocket support
       location /socket.io/ {
           proxy_pass http://127.0.0.1:5000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

   ```bash
   # Enable site and restart Nginx
   sudo ln -s /etc/nginx/sites-available/vedfolnir-staging /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

8. **Systemd Service Setup**:
   ```bash
   # Create systemd service
   sudo nano /etc/systemd/system/vedfolnir-staging.service
   ```

   **Systemd Service Configuration**:
   ```ini
   [Unit]
   Description=Vedfolnir Staging WebSocket Application
   After=network.target mysql.service redis.service
   
   [Service]
   Type=simple
   User=vedfolnir
   WorkingDirectory=/home/vedfolnir/vedfolnir
   Environment=PATH=/home/vedfolnir/vedfolnir/venv/bin
   ExecStart=/home/vedfolnir/vedfolnir/venv/bin/python web_app.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   # Enable and start service
   sudo systemctl daemon-reload
   sudo systemctl enable vedfolnir-staging
   sudo systemctl start vedfolnir-staging
   ```

### Staging Verification

```bash
# Check service status
sudo systemctl status vedfolnir-staging

# Test WebSocket connectivity
python scripts/test_websocket_connection.py --host staging.example.com --port 443 --ssl

# Test CORS configuration
python scripts/test_websocket_cors.py --environment staging

# Monitor logs
sudo journalctl -u vedfolnir-staging -f
```

## Production Environment Deployment

### Prerequisites

- Production-grade server infrastructure
- Load balancer (optional but recommended)
- SSL certificate from trusted CA
- Monitoring and alerting system
- Backup and disaster recovery plan

### High-Availability Setup

1. **Load Balancer Configuration** (Nginx):
   ```nginx
   upstream vedfolnir_backend {
       server 10.0.1.10:5000 weight=1 max_fails=3 fail_timeout=30s;
       server 10.0.1.11:5000 weight=1 max_fails=3 fail_timeout=30s;
       server 10.0.1.12:5000 weight=1 max_fails=3 fail_timeout=30s;
   }
   
   server {
       listen 443 ssl http2;
       server_name app.example.com;
   
       location / {
           proxy_pass http://vedfolnir_backend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   
       # WebSocket support with sticky sessions
       location /socket.io/ {
           proxy_pass http://vedfolnir_backend;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           
           # Sticky sessions for WebSocket
           ip_hash;
       }
   }
   ```

2. **Database Cluster Setup**:
   ```bash
   # MySQL Master-Slave configuration
   # Master server configuration
   [mysqld]
   server-id = 1
   log-bin = mysql-bin
   binlog-do-db = vedfolnir_production
   
   # Slave server configuration
   [mysqld]
   server-id = 2
   relay-log = mysql-relay-bin
   log-slave-updates = 1
   read-only = 1
   ```

3. **Redis Cluster Setup**:
   ```bash
   # Redis Sentinel configuration for high availability
   # sentinel.conf
   sentinel monitor vedfolnir-master 10.0.1.20 6379 2
   sentinel auth-pass vedfolnir-master production_redis_password
   sentinel down-after-milliseconds vedfolnir-master 5000
   sentinel failover-timeout vedfolnir-master 10000
   ```

### Production Environment Configuration

**Production .env Configuration**:
```bash
# Flask Configuration
FLASK_HOST=app.example.com
FLASK_PORT=443
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_SECRET_KEY=ultra-secure-production-secret-key

# Database Configuration (with connection pooling)
DATABASE_URL=mysql+pymysql://vedfolnir_prod:ultra_secure_password@db-cluster.example.com/vedfolnir_production?charset=utf8mb4
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Redis Configuration (with Sentinel)
REDIS_SENTINEL_HOSTS=10.0.1.21:26379,10.0.1.22:26379,10.0.1.23:26379
REDIS_SENTINEL_SERVICE=vedfolnir-master
REDIS_PASSWORD=ultra_secure_redis_password

# WebSocket Production Settings
SOCKETIO_DEBUG=false
SOCKETIO_LOG_LEVEL=WARNING
SOCKETIO_CORS_CREDENTIALS=true
SOCKETIO_TRANSPORTS=websocket,polling
SOCKETIO_ASYNC_MODE=eventlet

# Maximum Security
SOCKETIO_CSRF_PROTECTION=true
SOCKETIO_RATE_LIMITING=true
SOCKETIO_MAX_CONNECTIONS_PER_USER=3
SOCKETIO_PING_TIMEOUT=30
SOCKETIO_PING_INTERVAL=15

# Explicit CORS origins for security
SOCKETIO_CORS_ORIGINS=https://app.example.com,https://www.example.com

# Production Security
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=Strict
SESSION_COOKIE_HTTPONLY=true

# Performance Optimization
SOCKETIO_CONNECTION_POOL_SIZE=200
SOCKETIO_MESSAGE_QUEUE_SIZE=2000
SOCKETIO_MESSAGE_BATCH_SIZE=20

# Monitoring and Logging
SOCKETIO_METRICS_ENABLED=true
SOCKETIO_HEALTH_CHECK_ENABLED=true
LOG_LEVEL=WARNING
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Container Deployment (Docker)

1. **Dockerfile**:
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       default-libmysqlclient-dev \
       pkg-config \
       && rm -rf /var/lib/apt/lists/*
   
   # Copy requirements and install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY . .
   
   # Create non-root user
   RUN useradd -m -u 1000 vedfolnir && chown -R vedfolnir:vedfolnir /app
   USER vedfolnir
   
   EXPOSE 5000
   
   CMD ["python", "web_app.py"]
   ```

2. **Docker Compose**:
   ```yaml
   version: '3.8'
   
   services:
     app:
       build: .
       ports:
         - "5000:5000"
       environment:
         - FLASK_ENV=production
       env_file:
         - .env.production
       depends_on:
         - mysql
         - redis
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
   
     mysql:
       image: mysql:8.0
       environment:
         MYSQL_ROOT_PASSWORD: root_password
         MYSQL_DATABASE: vedfolnir_production
         MYSQL_USER: vedfolnir_prod
         MYSQL_PASSWORD: secure_password
       volumes:
         - mysql_data:/var/lib/mysql
       restart: unless-stopped
   
     redis:
       image: redis:7-alpine
       command: redis-server --requirepass redis_password
       volumes:
         - redis_data:/data
       restart: unless-stopped
   
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/ssl/certs
       depends_on:
         - app
       restart: unless-stopped
   
   volumes:
     mysql_data:
     redis_data:
   ```

### Kubernetes Deployment

1. **Deployment Configuration**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: vedfolnir-websocket
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: vedfolnir-websocket
     template:
       metadata:
         labels:
           app: vedfolnir-websocket
       spec:
         containers:
         - name: vedfolnir
           image: vedfolnir:latest
           ports:
           - containerPort: 5000
           env:
           - name: FLASK_ENV
             value: "production"
           envFrom:
           - secretRef:
               name: vedfolnir-secrets
           livenessProbe:
             httpGet:
               path: /health
               port: 5000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health/ready
               port: 5000
             initialDelaySeconds: 5
             periodSeconds: 5
   ```

2. **Service Configuration**:
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: vedfolnir-websocket-service
   spec:
     selector:
       app: vedfolnir-websocket
     ports:
     - protocol: TCP
       port: 80
       targetPort: 5000
     type: LoadBalancer
   ```

### Monitoring and Alerting

1. **Prometheus Metrics**:
   ```python
   # Add to web_app.py
   from prometheus_client import Counter, Histogram, generate_latest
   
   websocket_connections = Counter('websocket_connections_total', 'Total WebSocket connections')
   websocket_latency = Histogram('websocket_latency_seconds', 'WebSocket connection latency')
   
   @app.route('/metrics')
   def metrics():
       return generate_latest()
   ```

2. **Health Check Endpoints**:
   ```python
   @app.route('/health')
   def health_check():
       return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
   
   @app.route('/health/ready')
   def readiness_check():
       # Check database and Redis connectivity
       return {'status': 'ready', 'services': {'database': 'ok', 'redis': 'ok'}}
   ```

### Backup and Recovery

1. **Database Backup**:
   ```bash
   # Automated backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   mysqldump -u backup_user -p vedfolnir_production > /backups/vedfolnir_${DATE}.sql
   gzip /backups/vedfolnir_${DATE}.sql
   
   # Upload to S3 or other cloud storage
   aws s3 cp /backups/vedfolnir_${DATE}.sql.gz s3://vedfolnir-backups/
   ```

2. **Redis Backup**:
   ```bash
   # Redis backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   redis-cli --rdb /backups/redis_${DATE}.rdb
   gzip /backups/redis_${DATE}.rdb
   ```

### Security Hardening

1. **Firewall Configuration**:
   ```bash
   # UFW rules for production
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 22/tcp    # SSH (restrict to specific IPs)
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

2. **SSL/TLS Configuration**:
   ```nginx
   # Strong SSL configuration
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
   ssl_prefer_server_ciphers off;
   ssl_session_cache shared:SSL:10m;
   ssl_session_timeout 10m;
   
   # HSTS
   add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
   ```

### Performance Optimization

1. **Application Tuning**:
   ```bash
   # Gunicorn configuration for production
   gunicorn --workers 4 --worker-class eventlet --bind 0.0.0.0:5000 web_app:app
   ```

2. **Database Optimization**:
   ```sql
   -- MySQL optimization
   SET GLOBAL innodb_buffer_pool_size = 2G;
   SET GLOBAL max_connections = 200;
   SET GLOBAL query_cache_size = 256M;
   ```

### Deployment Checklist

**Pre-Deployment:**
- [ ] Environment configuration reviewed and validated
- [ ] SSL certificates installed and tested
- [ ] Database migrations tested
- [ ] Backup procedures verified
- [ ] Monitoring and alerting configured
- [ ] Load testing completed
- [ ] Security audit completed

**Deployment:**
- [ ] Application deployed to all instances
- [ ] Health checks passing
- [ ] WebSocket connectivity verified
- [ ] CORS configuration tested
- [ ] Authentication flow tested
- [ ] Performance metrics within acceptable ranges

**Post-Deployment:**
- [ ] Monitor application logs for errors
- [ ] Verify WebSocket connections are stable
- [ ] Check database and Redis performance
- [ ] Validate SSL certificate expiration dates
- [ ] Update documentation with any changes
- [ ] Schedule regular maintenance windows

This comprehensive deployment guide ensures reliable, secure, and performant WebSocket functionality across all environments.