# Deployment Guide - Web Caption Generation

## Overview
This guide covers deploying the web-based caption generation system with WebSocket support and background task processing.

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 10GB free space minimum
- **CPU**: 2+ cores recommended
- **Network**: Stable internet connection

### Dependencies
- **Ollama**: AI model server with LLaVA model
- **Redis**: Session storage and task queuing (optional but recommended)
- **Nginx**: Reverse proxy for production (recommended)
- **Supervisor**: Process management (recommended)

## Installation

### 1. Basic Setup
```bash
# Clone repository
git clone <repository-url>
cd vedfolnir

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Initialize database
python migrate_to_platform_aware.py

# Create admin user
python init_admin_user.py
```

### 3. Ollama Setup
```bash
# Install Ollama (see https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required model
ollama pull llava:7b

# Start Ollama service
ollama serve
```

## Configuration

### Environment Variables
Create `.env` file:
```bash
# Basic Configuration
FLASK_SECRET_KEY=your-secure-random-key-here
AUTH_ADMIN_PASSWORD=your-admin-password

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b

# WebSocket Configuration
SOCKETIO_ASYNC_MODE=threading
SOCKETIO_CORS_ALLOWED_ORIGINS=*

# Task Processing
MAX_CONCURRENT_TASKS=5
TASK_TIMEOUT_MINUTES=60
BACKGROUND_TASK_WORKERS=2

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_TASKS_PER_HOUR=10

# Logging
LOG_LEVEL=INFO
LOGS_DIR=logs

# Security
SESSION_TIMEOUT=3600
SECURITY_HEADERS_ENABLED=true
```

### Production Configuration
```bash
# Production Settings
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Database
DATABASE_URL=sqlite:///storage/database/vedfolnir.db
DATABASE_POOL_SIZE=20
DATABASE_POOL_TIMEOUT=30

# Redis (recommended for production)
REDIS_URL=redis://localhost:6379/0
USE_REDIS_SESSIONS=true

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Docker Compose Setup
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  vedfolnir:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
      - ./.env:/app/.env
    environment:
      - FLASK_HOST=0.0.0.0
      - REDIS_URL=redis://redis:6379/0
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - redis
      - ollama
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    command: ["ollama", "serve"]

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - vedfolnir
    restart: unless-stopped

volumes:
  redis_data:
  ollama_data:
```

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage/images storage/database logs

# Initialize database
RUN python migrate_to_platform_aware.py

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Start application
CMD ["python", "web_app.py"]
```

#### Deploy with Docker
```bash
# Build and start services
docker-compose up -d

# Initialize Ollama model
docker-compose exec ollama ollama pull llava:7b

# Check status
docker-compose ps
docker-compose logs vedfolnir
```

### Option 2: Manual Deployment

#### System Service Setup
Create `/etc/systemd/system/vedfolnir.service`:
```ini
[Unit]
Description=Vedfolnir Web Service
After=network.target

[Service]
Type=simple
User=alttext
Group=alttext
WorkingDirectory=/opt/vedfolnir
Environment=PATH=/opt/vedfolnir/venv/bin
ExecStart=/opt/vedfolnir/venv/bin/python web_app.py
Restart=always
RestartSec=10

# Resource limits
LimitNOFILE=65536
MemoryMax=2G

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vedfolnir

[Install]
WantedBy=multi-user.target
```

#### Background Task Worker Service
Create `/etc/systemd/system/vedfolnir-worker.service`:
```ini
[Unit]
Description=Vedfolnir Background Worker
After=network.target vedfolnir.service

[Service]
Type=simple
User=alttext
Group=alttext
WorkingDirectory=/opt/vedfolnir
Environment=PATH=/opt/vedfolnir/venv/bin
ExecStart=/opt/vedfolnir/venv/bin/python background_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Services
```bash
# Enable services
sudo systemctl enable vedfolnir
sudo systemctl enable vedfolnir-worker

# Start services
sudo systemctl start vedfolnir
sudo systemctl start vedfolnir-worker

# Check status
sudo systemctl status vedfolnir
sudo systemctl status vedfolnir-worker
```

### Option 3: Supervisor Deployment

#### Supervisor Configuration
Create `/etc/supervisor/conf.d/vedfolnir.conf`:
```ini
[group:vedfolnir]
programs=web-app,background-worker

[program:web-app]
command=/opt/vedfolnir/venv/bin/python web_app.py
directory=/opt/vedfolnir
user=alttext
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/vedfolnir/web-app.log
environment=PATH="/opt/vedfolnir/venv/bin"

[program:background-worker]
command=/opt/vedfolnir/venv/bin/python background_worker.py
directory=/opt/vedfolnir
user=alttext
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/vedfolnir/worker.log
environment=PATH="/opt/vedfolnir/venv/bin"
```

## Reverse Proxy Configuration

### Nginx Configuration
Create `/etc/nginx/sites-available/vedfolnir`:
```nginx
upstream vedfolnir {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # WebSocket Support
    location /socket.io/ {
        proxy_pass http://vedfolnir;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Main Application
    location / {
        proxy_pass http://vedfolnir;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static Files
    location /static/ {
        alias /opt/vedfolnir/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health Check
    location /health {
        proxy_pass http://vedfolnir;
        access_log off;
    }
}
```

### Apache Configuration (Alternative)
```apache
<VirtualHost *:443>
    ServerName your-domain.com
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/cert.pem
    SSLCertificateKeyFile /etc/ssl/private/key.pem
    
    # WebSocket Support
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://127.0.0.1:5000/$1" [P,L]
    
    # Main Proxy
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    
    # Headers
    ProxyPassReverse / http://127.0.0.1:5000/
    ProxyPassReverseMatch ^(/.*) http://127.0.0.1:5000$1
</VirtualHost>
```

## Monitoring and Health Checks

### Health Check Endpoint
The application provides health check endpoints:
```bash
# Basic health check
curl http://localhost:5000/health

# Detailed health check
curl http://localhost:5000/health/detailed
```

### Monitoring Setup
```bash
# Install monitoring tools
pip install prometheus-client

# Add to requirements.txt
echo "prometheus-client==0.19.0" >> requirements.txt
```

### Log Monitoring
```bash
# Monitor application logs
tail -f logs/vedfolnir.log

# Monitor error logs
grep "ERROR" logs/vedfolnir.log | tail -20

# Monitor WebSocket connections
grep "WebSocket" logs/webapp.log | tail -10
```

## Scaling and Performance

### Horizontal Scaling
```yaml
# docker-compose.yml for multiple workers
services:
  vedfolnir-1:
    build: .
    ports:
      - "5001:5000"
    # ... other config

  vedfolnir-2:
    build: .
    ports:
      - "5002:5000"
    # ... other config

  nginx:
    # ... nginx config with load balancing
```

### Load Balancer Configuration
```nginx
upstream vedfolnir_cluster {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}
```

### Performance Tuning
```bash
# Increase worker processes
export BACKGROUND_TASK_WORKERS=4

# Tune database connections
export DATABASE_POOL_SIZE=50

# Optimize WebSocket connections
export SOCKETIO_MAX_CONNECTIONS=1000
```

## Security Considerations

### SSL/TLS Setup
```bash
# Generate SSL certificate (Let's Encrypt)
certbot --nginx -d your-domain.com

# Or use self-signed for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

### Firewall Configuration
```bash
# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow SSH (if needed)
sudo ufw allow 22

# Block direct access to application port
sudo ufw deny 5000
```

### Security Headers
Ensure these headers are set in your reverse proxy:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

## Backup and Recovery

### Database Backup
```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp storage/database/vedfolnir.db backups/vedfolnir_$DATE.db
find backups/ -name "*.db" -mtime +7 -delete
```

### Full System Backup
```bash
# Backup entire application
tar -czf alt_text_bot_backup_$(date +%Y%m%d).tar.gz \
    /opt/vedfolnir \
    --exclude=/opt/vedfolnir/venv \
    --exclude=/opt/vedfolnir/logs
```

## Troubleshooting

### Common Issues

#### WebSocket Connection Failures
```bash
# Check WebSocket support
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
     http://localhost:5000/socket.io/

# Check proxy configuration
nginx -t
systemctl reload nginx
```

#### High Memory Usage
```bash
# Monitor memory usage
ps aux | grep python | grep web_app
free -h

# Check for memory leaks
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

#### Task Processing Issues
```bash
# Check background worker status
systemctl status vedfolnir-worker

# Monitor task queue
python -c "
from task_queue_manager import TaskQueueManager
from database import DatabaseManager
from config import Config
manager = TaskQueueManager(DatabaseManager(Config()))
print(manager.get_queue_stats())
"
```

### Log Analysis
```bash
# Application errors
grep "ERROR" logs/vedfolnir.log | tail -20

# WebSocket issues
grep "WebSocket" logs/webapp.log | grep "ERROR"

# Task failures
grep "Task.*failed" logs/vedfolnir.log
```