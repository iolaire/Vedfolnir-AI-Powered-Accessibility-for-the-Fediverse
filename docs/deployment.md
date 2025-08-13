# Deployment Guide

This guide covers deploying the Vedfolnir in various environments, from development to production.

## Overview

The Vedfolnir consists of several components:
- **Main Bot**: Processes posts and generates captions
- **Web Interface**: Flask application for reviewing captions
- **Database**: SQLite database for storing data
- **Ollama**: AI service for caption generation
- **Storage**: File system storage for images and logs

## Deployment Options

### 1. Docker Deployment (Recommended)

Docker provides the easiest and most consistent deployment method.

#### Prerequisites
- Docker and Docker Compose installed
- Access to a Pixelfed or Mastodon instance
- Basic understanding of Docker

#### Setup

1. **Create the deployment directory:**
   ```bash
   mkdir vedfolnir-deploy
   cd vedfolnir-deploy
   ```

2. **Create docker-compose.yml:**
   ```yaml
   version: '3.8'
   
   services:
     vedfolnir:
       image: vedfolnir:latest
       build:
         context: .
         dockerfile: Dockerfile
       ports:
         - "5000:5000"
       volumes:
         - ./storage:/app/storage
         - ./logs:/app/logs
         - ./.env:/app/.env:ro
       environment:
         - FLASK_HOST=0.0.0.0
         - OLLAMA_URL=http://ollama:11434
       depends_on:
         - ollama
       restart: unless-stopped
   
     ollama:
       image: ollama/ollama:latest
       ports:
         - "11434:11434"
       volumes:
         - ollama_data:/root/.ollama
       environment:
         - OLLAMA_ORIGINS=*
       restart: unless-stopped
   
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf:ro
         - ./ssl:/etc/nginx/ssl:ro
       depends_on:
         - vedfolnir
       restart: unless-stopped
   
   volumes:
     ollama_data:
   ```

3. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       curl \
       && rm -rf /var/lib/apt/lists/*
   
   WORKDIR /app
   
   # Copy requirements and install Python dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application code
   COPY . .
   
   # Create necessary directories
   RUN mkdir -p storage/images storage/database logs
   
   # Set permissions
   RUN chmod +x *.py
   
   # Initialize database (will be skipped if already exists)
   RUN python init_migrations.py || true
   
   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
     CMD curl -f http://localhost:5000/health || exit 1
   
   EXPOSE 5000
   
   CMD ["python", "web_app.py"]
   ```

4. **Create nginx.conf:**
   ```nginx
   events {
       worker_connections 1024;
   }
   
   http {
       upstream vedfolnir {
           server vedfolnir:5000;
       }
   
       server {
           listen 80;
           server_name your-domain.com;
           
           # Redirect HTTP to HTTPS
           return 301 https://$server_name$request_uri;
       }
   
       server {
           listen 443 ssl http2;
           server_name your-domain.com;
   
           ssl_certificate /etc/nginx/ssl/cert.pem;
           ssl_certificate_key /etc/nginx/ssl/key.pem;
           
           ssl_protocols TLSv1.2 TLSv1.3;
           ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
           ssl_prefer_server_ciphers off;
   
           location / {
               proxy_pass http://vedfolnir;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
               
               # Increase timeout for long-running requests
               proxy_read_timeout 300s;
               proxy_connect_timeout 75s;
           }
           
           # Health check endpoint
           location /health {
               proxy_pass http://vedfolnir/health;
               access_log off;
           }
       }
   }
   ```

5. **Configure environment:**
   ```bash
   # Copy example configuration
   cp .env.example .env
   
   # Edit .env with your settings
   nano .env
   ```

6. **Deploy:**
   ```bash
   # Pull Ollama model
   docker-compose run --rm ollama ollama pull llava:7b
   
   # Start services
   docker-compose up -d
   
   # Check status
   docker-compose ps
   
   # View logs
   docker-compose logs -f vedfolnir
   ```

#### Docker Management Commands

```bash
# Update the application
docker-compose pull
docker-compose up -d --build

# Backup data
docker-compose exec vedfolnir python -c "
import shutil
shutil.copy('storage/database/vedfolnir.db', 'storage/database/backup.db')
"

# Access application shell
docker-compose exec vedfolnir bash

# View logs
docker-compose logs -f vedfolnir
docker-compose logs -f ollama

# Restart services
docker-compose restart vedfolnir
```

### 2. Manual Deployment

For more control or when Docker isn't available.

#### Prerequisites
- Python 3.8+
- Virtual environment support
- Systemd (Linux) or equivalent service manager
- Nginx or Apache (optional, for reverse proxy)

#### Setup

1. **Create deployment user:**
   ```bash
   sudo useradd -m -s /bin/bash alttext
   sudo su - alttext
   ```

2. **Clone and setup application:**
   ```bash
   git clone <repository-url> vedfolnir
   cd vedfolnir
   
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env
   
   # Set production values
   FLASK_DEBUG=false
   FLASK_HOST=0.0.0.0
   FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

4. **Initialize database:**
   ```bash
   python init_migrations.py
   python init_admin_user.py
   ```

5. **Test the setup:**
   ```bash
   python validate_config.py
   python main.py --users test_user --log-level DEBUG
   ```

6. **Create systemd service:**
   ```bash
   sudo tee /etc/systemd/system/vedfolnir.service > /dev/null <<EOF
   [Unit]
   Description=Vedfolnir Web Service
   After=network.target
   
   [Service]
   Type=simple
   User=alttext
   Group=alttext
   WorkingDirectory=/home/alttext/vedfolnir
   Environment=PATH=/home/alttext/vedfolnir/venv/bin
   ExecStart=/home/alttext/vedfolnir/venv/bin/python web_app.py
   ExecReload=/bin/kill -HUP \$MAINPID
   Restart=always
   RestartSec=10
   
   # Security settings
   NoNewPrivileges=true
   PrivateTmp=true
   ProtectSystem=strict
   ReadWritePaths=/home/alttext/vedfolnir/storage /home/alttext/vedfolnir/logs
   
   [Install]
   WantedBy=multi-user.target
   EOF
   ```

7. **Enable and start service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vedfolnir
   sudo systemctl start vedfolnir
   sudo systemctl status vedfolnir
   ```

#### Manual Deployment Management

```bash
# Check service status
sudo systemctl status vedfolnir

# View logs
sudo journalctl -u vedfolnir -f

# Restart service
sudo systemctl restart vedfolnir

# Update application
sudo su - alttext
cd vedfolnir
git pull
source venv/bin/activate
pip install -r requirements.txt
exit
sudo systemctl restart vedfolnir
```

### 3. Kubernetes Deployment

For large-scale or cloud deployments.

#### Prerequisites
- Kubernetes cluster
- kubectl configured
- Persistent volume support

#### Setup

1. **Create namespace:**
   ```yaml
   # namespace.yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: vedfolnir
   ```

2. **Create ConfigMap:**
   ```yaml
   # configmap.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: vedfolnir-config
     namespace: vedfolnir
   data:
     FLASK_HOST: "0.0.0.0"
     FLASK_PORT: "5000"
     OLLAMA_URL: "http://ollama:11434"
     LOG_LEVEL: "INFO"
   ```

3. **Create Secret:**
   ```yaml
   # secret.yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: vedfolnir-secret
     namespace: vedfolnir
   type: Opaque
   stringData:
     ACTIVITYPUB_ACCESS_TOKEN: "your-access-token"
     MASTODON_CLIENT_KEY: "your-client-key"
     MASTODON_CLIENT_SECRET: "your-client-secret"
     FLASK_SECRET_KEY: "your-secret-key"
   ```

4. **Create Deployment:**
   ```yaml
   # deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: vedfolnir
     namespace: vedfolnir
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: vedfolnir
     template:
       metadata:
         labels:
           app: vedfolnir
       spec:
         containers:
         - name: vedfolnir
           image: vedfolnir:latest
           ports:
           - containerPort: 5000
           envFrom:
           - configMapRef:
               name: vedfolnir-config
           - secretRef:
               name: vedfolnir-secret
           volumeMounts:
           - name: storage
             mountPath: /app/storage
           - name: logs
             mountPath: /app/logs
           livenessProbe:
             httpGet:
               path: /health
               port: 5000
             initialDelaySeconds: 30
             periodSeconds: 30
           readinessProbe:
             httpGet:
               path: /health
               port: 5000
             initialDelaySeconds: 5
             periodSeconds: 10
         volumes:
         - name: storage
           persistentVolumeClaim:
             claimName: vedfolnir-storage
         - name: logs
           persistentVolumeClaim:
             claimName: vedfolnir-logs
   ```

5. **Deploy:**
   ```bash
   kubectl apply -f namespace.yaml
   kubectl apply -f configmap.yaml
   kubectl apply -f secret.yaml
   kubectl apply -f deployment.yaml
   ```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.development
FLASK_DEBUG=true
LOG_LEVEL=DEBUG
DRY_RUN=true
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

### Staging Environment

```bash
# .env.staging
FLASK_DEBUG=false
LOG_LEVEL=INFO
DRY_RUN=true  # Test without making actual changes
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### Production Environment

```bash
# .env.production
FLASK_DEBUG=false
LOG_LEVEL=WARNING
DRY_RUN=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_SECRET_KEY=your-secure-random-key
AUTH_ADMIN_PASSWORD=your-secure-password
```

## Monitoring and Maintenance

### Health Checks

The application provides several health check endpoints:

```bash
# Basic health check
curl http://localhost:5000/health

# Detailed system status
curl http://localhost:5000/health/detailed

# Database health
curl http://localhost:5000/health/database

# Ollama connectivity
curl http://localhost:5000/health/ollama
```

### Logging

Configure log rotation to prevent disk space issues:

```bash
# /etc/logrotate.d/vedfolnir
/home/alttext/vedfolnir/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 alttext alttext
    postrotate
        systemctl reload vedfolnir
    endscript
}
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Daily backup script

BACKUP_DIR="/backup/vedfolnir"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
cp /home/alttext/vedfolnir/storage/database/vedfolnir.db \
   "$BACKUP_DIR/database_$DATE.db"

# Backup configuration
cp /home/alttext/vedfolnir/.env \
   "$BACKUP_DIR/config_$DATE.env"

# Compress and remove old backups
gzip "$BACKUP_DIR/database_$DATE.db"
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
```

### Performance Monitoring

Monitor key metrics:

```bash
# System resources
htop
df -h
free -h

# Application logs
tail -f /home/alttext/vedfolnir/logs/vedfolnir.log

# Database size
ls -lh /home/alttext/vedfolnir/storage/database/

# Service status
systemctl status vedfolnir
```

## Security Considerations

### Application Security

1. **Use strong secrets:**
   ```bash
   # Generate secure secret key
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Restrict file permissions:**
   ```bash
   chmod 600 .env
   chmod 755 storage/
   chmod 644 storage/database/*.db
   ```

3. **Use HTTPS in production:**
   - Configure SSL certificates
   - Use secure headers
   - Enable HSTS

### Network Security

1. **Firewall configuration:**
   ```bash
   # Allow only necessary ports
   ufw allow 22/tcp   # SSH
   ufw allow 80/tcp   # HTTP
   ufw allow 443/tcp  # HTTPS
   ufw enable
   ```

2. **Reverse proxy security:**
   - Hide server information
   - Rate limiting
   - Request size limits

### Access Control

1. **Use strong admin passwords**
2. **Enable authentication for web interface**
3. **Regularly rotate API tokens**
4. **Monitor access logs**

## Troubleshooting Deployment Issues

### Common Deployment Problems

**Service won't start:**
```bash
# Check service status
systemctl status vedfolnir

# Check logs
journalctl -u vedfolnir -n 50

# Check configuration
python validate_config.py
```

**Database issues:**
```bash
# Check database permissions
ls -la storage/database/

# Test database connection
python check_db.py

# Recreate database if corrupted
mv storage/database/vedfolnir.db storage/database/vedfolnir.db.backup
python init_migrations.py
```

**Ollama connectivity:**
```bash
# Test Ollama connection
curl http://localhost:11434/api/version

# Check if model is available
curl http://localhost:11434/api/tags

# Pull model if missing
ollama pull llava:7b
```

### Performance Issues

**High memory usage:**
- Reduce MAX_POSTS_PER_RUN
- Increase USER_PROCESSING_DELAY
- Monitor Ollama memory usage

**Slow response times:**
- Check database performance
- Monitor disk I/O
- Consider using faster storage

**Rate limiting:**
- Adjust rate limit settings
- Increase delays between requests
- Monitor API usage

This deployment guide should help you successfully deploy the Vedfolnir in various environments. Choose the deployment method that best fits your infrastructure and requirements.