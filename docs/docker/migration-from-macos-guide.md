# Migration from macOS to Docker Compose Guide

## Overview

This guide provides step-by-step instructions for migrating Vedfolnir from the previous macOS-specific deployment to the new Docker Compose containerized architecture. The migration process ensures data integrity while transitioning to a more portable and scalable deployment model.

## Pre-Migration Assessment

### Current macOS Setup Inventory
Before starting the migration, document your current setup:

```bash
# Document current configuration
echo "=== Current Vedfolnir macOS Setup ===" > migration_inventory.txt

# Python environment
echo "Python Version:" >> migration_inventory.txt
python --version >> migration_inventory.txt

# Database information
echo -e "\nMySQL Status:" >> migration_inventory.txt
brew services list | grep mysql >> migration_inventory.txt
mysql --version >> migration_inventory.txt

# Redis information
echo -e "\nRedis Status:" >> migration_inventory.txt
brew services list | grep redis >> migration_inventory.txt
redis-server --version >> migration_inventory.txt

# Ollama information
echo -e "\nOllama Status:" >> migration_inventory.txt
ollama --version >> migration_inventory.txt
ollama list >> migration_inventory.txt

# Application data
echo -e "\nApplication Data:" >> migration_inventory.txt
ls -la storage/ >> migration_inventory.txt
du -sh storage/ logs/ >> migration_inventory.txt

# Configuration
echo -e "\nConfiguration Files:" >> migration_inventory.txt
ls -la .env* >> migration_inventory.txt
```

### Prerequisites Check
Ensure the following before migration:

1. **Docker Installation:**
   ```bash
   # Install Docker Desktop for macOS
   # Download from: https://www.docker.com/products/docker-desktop
   
   # Verify installation
   docker --version
   docker-compose --version
   ```

2. **Backup Current System:**
   ```bash
   # Create complete backup
   ./scripts/backup/create_full_backup.sh
   
   # Verify backup integrity
   ./scripts/backup/verify_backup.sh
   ```

3. **Free Disk Space:**
   ```bash
   # Check available space (need at least 10GB)
   df -h
   
   # Clean up if needed
   docker system prune -f
   ```

## Migration Process

### Phase 1: Data Export from macOS

#### 1.1 Stop Current Services
```bash
# Stop Vedfolnir application
pkill -f "python.*web_app.py"
pkill -f "python.*main.py"

# Stop launchd services (if configured)
launchctl unload ~/Library/LaunchAgents/com.vedfolnir.webapp.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.vedfolnir.worker.plist 2>/dev/null || true

# Stop Homebrew services
brew services stop mysql
brew services stop redis
```

#### 1.2 Export MySQL Database
```bash
# Create database export
mkdir -p migration_data/mysql

# Export all databases
mysqldump --single-transaction --routines --triggers --all-databases \
  -u root -p > migration_data/mysql/full_backup.sql

# Export Vedfolnir database specifically
mysqldump --single-transaction --routines --triggers \
  -u root -p vedfolnir > migration_data/mysql/vedfolnir_backup.sql

# Verify export
echo "Database export size:"
ls -lh migration_data/mysql/
```

#### 1.3 Export Redis Data
```bash
# Create Redis export
mkdir -p migration_data/redis

# Save Redis data
redis-cli BGSAVE
sleep 5

# Copy Redis dump
cp /usr/local/var/db/redis/dump.rdb migration_data/redis/

# Export Redis configuration
cp /usr/local/etc/redis.conf migration_data/redis/ 2>/dev/null || \
  redis-cli CONFIG GET '*' > migration_data/redis/redis_config.txt
```

#### 1.4 Export Application Data
```bash
# Create application data export
mkdir -p migration_data/app

# Copy storage directory
cp -r storage/ migration_data/app/

# Copy logs (recent only)
mkdir -p migration_data/app/logs
find logs/ -name "*.log" -mtime -30 -exec cp {} migration_data/app/logs/ \;

# Copy configuration
cp .env migration_data/app/env_backup
cp config.py migration_data/app/ 2>/dev/null || true

# Copy any custom scripts or configurations
cp -r scripts/ migration_data/app/ 2>/dev/null || true
```

#### 1.5 Export Secrets and Credentials
```bash
# Create secure secrets backup
mkdir -p migration_data/secrets

# Extract secrets from environment
echo "FLASK_SECRET_KEY=$(grep FLASK_SECRET_KEY .env | cut -d'=' -f2)" > migration_data/secrets/flask_secret.txt
echo "PLATFORM_ENCRYPTION_KEY=$(grep PLATFORM_ENCRYPTION_KEY .env | cut -d'=' -f2)" > migration_data/secrets/platform_key.txt

# Export platform credentials (encrypted)
python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import PlatformConnection
import json

config = Config()
db_manager = DatabaseManager(config)

with db_manager.get_session() as session:
    platforms = session.query(PlatformConnection).all()
    platform_data = []
    for platform in platforms:
        platform_data.append({
            'id': platform.id,
            'user_id': platform.user_id,
            'platform_name': platform.platform_name,
            'instance_url': platform.instance_url,
            'username': platform.username,
            # Note: encrypted credentials will be migrated separately
        })
    
    with open('migration_data/secrets/platforms.json', 'w') as f:
        json.dump(platform_data, f, indent=2)
"

# Set secure permissions
chmod 600 migration_data/secrets/*
```

### Phase 2: Docker Environment Setup

#### 2.1 Prepare Docker Compose Environment
```bash
# Create Docker Compose directory structure
mkdir -p docker-vedfolnir
cd docker-vedfolnir

# Create required directories
mkdir -p data/{mysql,redis,prometheus,grafana,loki,vault}
mkdir -p logs/{app,nginx,mysql,vault,audit}
mkdir -p storage/{images,backups,temp}
mkdir -p config/{mysql,redis,nginx,prometheus,grafana,loki,vault,app}
mkdir -p secrets
mkdir -p ssl/{certs,keys}

# Copy application files
cp -r ../app/ .
cp -r ../templates/ .
cp -r ../static/ .
cp -r ../admin/ .
cp ../main.py ../web_app.py ../config.py ../models.py .
cp -r ../scripts/ .
```

#### 2.2 Generate Docker Secrets
```bash
# Generate new secrets for Docker environment
openssl rand -base64 32 > secrets/flask_secret_key.txt
openssl rand -base64 32 > secrets/platform_encryption_key.txt
openssl rand -base64 32 > secrets/mysql_root_password.txt
openssl rand -base64 32 > secrets/mysql_password.txt
openssl rand -base64 32 > secrets/redis_password.txt
openssl rand -base64 32 > secrets/vault_root_token.txt
openssl rand -base64 32 > secrets/vault_token.txt

# Set proper permissions
chmod 600 secrets/*
```

#### 2.3 Create Docker Compose Configuration
```bash
# Copy Docker Compose files
cp ../docker-compose.yml .
cp ../docker-compose.dev.yml .
cp ../docker-compose.prod.yml .

# Create environment configuration
cat > .env.docker << 'EOF'
# Database Configuration
DATABASE_URL=mysql+pymysql://vedfolnir:$(cat secrets/mysql_password.txt)@mysql:3306/vedfolnir?charset=utf8mb4
MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password
MYSQL_PASSWORD_FILE=/run/secrets/mysql_password
MYSQL_DATABASE=vedfolnir
MYSQL_USER=vedfolnir

# Redis Configuration
REDIS_URL=redis://:$(cat secrets/redis_password.txt)@redis:6379/0
REDIS_PASSWORD_FILE=/run/secrets/redis_password

# Application Configuration
FLASK_SECRET_KEY_FILE=/run/secrets/flask_secret_key
PLATFORM_ENCRYPTION_KEY_FILE=/run/secrets/platform_encryption_key
FLASK_ENV=production

# External Ollama API (running on host)
OLLAMA_URL=http://host.docker.internal:11434

# Security
SECURITY_CSRF_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true

# Observability
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000
LOKI_URL=http://loki:3100

# Vault Configuration
VAULT_ADDR=http://vault:8200
VAULT_TOKEN_FILE=/run/secrets/vault_token
EOF
```

### Phase 3: Data Migration

#### 3.1 Start Docker Services
```bash
# Start database services first
docker-compose up -d mysql redis vault

# Wait for services to be ready
echo "Waiting for MySQL to be ready..."
until docker-compose exec mysql mysqladmin ping -h localhost --silent; do
  sleep 2
done

echo "Waiting for Redis to be ready..."
until docker-compose exec redis redis-cli ping; do
  sleep 2
done
```

#### 3.2 Import MySQL Data
```bash
# Import database
echo "Importing MySQL database..."
docker-compose exec -T mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) < ../migration_data/mysql/vedfolnir_backup.sql

# Create Vedfolnir user and grant permissions
docker-compose exec mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "
CREATE USER IF NOT EXISTS 'vedfolnir'@'%' IDENTIFIED BY '$(cat secrets/mysql_password.txt)';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'%';
FLUSH PRIVILEGES;
"

# Verify database import
docker-compose exec mysql mysql -u vedfolnir -p$(cat secrets/mysql_password.txt) vedfolnir -e "
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as platform_count FROM platform_connections;
SELECT COUNT(*) as post_count FROM posts;
"
```

#### 3.3 Import Redis Data
```bash
# Stop Redis temporarily
docker-compose stop redis

# Import Redis data
docker cp ../migration_data/redis/dump.rdb vedfolnir_redis:/data/

# Start Redis
docker-compose start redis

# Verify Redis data
docker-compose exec redis redis-cli info keyspace
```

#### 3.4 Import Application Data
```bash
# Import storage data
cp -r ../migration_data/app/storage/* storage/

# Import logs
cp -r ../migration_data/app/logs/* logs/app/

# Set proper permissions
sudo chown -R 1000:1000 storage/
sudo chown -R 1000:1000 logs/
```

#### 3.5 Migrate Secrets and Configuration
```bash
# Update secrets with migrated values (if needed)
# Note: New secrets were generated for security, but you can use old ones if required

# Migrate platform credentials
python3 << 'EOF'
import json
import os
from cryptography.fernet import Fernet

# Load old platform data
with open('../migration_data/secrets/platforms.json', 'r') as f:
    platforms = json.load(f)

# Generate new encryption key for Docker environment
new_key = Fernet.generate_key()
with open('secrets/platform_encryption_key.txt', 'wb') as f:
    f.write(new_key)

print(f"Migrated {len(platforms)} platform connections")
print("Platform credentials will need to be re-entered in the web interface")
EOF
```

### Phase 4: Service Startup and Validation

#### 4.1 Start All Services
```bash
# Start all services
docker-compose up -d

# Monitor startup
docker-compose logs -f
```

#### 4.2 Validate Migration
```bash
# Create validation script
cat > validate_migration.sh << 'EOF'
#!/bin/bash
echo "=== Vedfolnir Migration Validation ==="

# Check container health
echo "Container Status:"
docker-compose ps

# Test web interface
echo -e "\nWeb Interface:"
curl -f http://localhost/health && echo "✅ Web interface OK" || echo "❌ Web interface FAILED"

# Test database connectivity
echo -e "\nDatabase Connectivity:"
docker-compose exec vedfolnir python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    result = session.execute('SELECT COUNT(*) FROM users').scalar()
    print(f'✅ Database OK - {result} users found')
" || echo "❌ Database FAILED"

# Test Redis connectivity
echo -e "\nRedis Connectivity:"
docker-compose exec redis redis-cli ping && echo "✅ Redis OK" || echo "❌ Redis FAILED"

# Test Ollama connectivity
echo -e "\nOllama Connectivity:"
docker-compose exec vedfolnir curl -f http://host.docker.internal:11434/api/version && echo "✅ Ollama OK" || echo "❌ Ollama FAILED"

# Check data integrity
echo -e "\nData Integrity:"
echo "Storage directory:"
ls -la storage/images/ | head -5
echo "Log files:"
ls -la logs/app/ | head -5

echo -e "\n=== Migration Validation Complete ==="
EOF

chmod +x validate_migration.sh
./validate_migration.sh
```

#### 4.3 Test Core Functionality
```bash
# Test user authentication
echo "Testing user authentication..."
curl -c cookies.txt -b cookies.txt -X GET http://localhost/login

# Test platform management
echo "Testing platform management..."
curl -c cookies.txt -b cookies.txt -X GET http://localhost/platforms

# Test caption generation (if platforms configured)
echo "Testing caption generation..."
curl -c cookies.txt -b cookies.txt -X GET http://localhost/caption

# Clean up test cookies
rm -f cookies.txt
```

### Phase 5: Post-Migration Configuration

#### 5.1 Reconfigure Platform Connections
Since platform credentials are encrypted with a new key, they need to be reconfigured:

1. **Access Web Interface:**
   ```bash
   open http://localhost/
   ```

2. **Login with Admin Account**
3. **Navigate to Platform Management**
4. **Re-enter Platform Credentials** for each platform connection

#### 5.2 Update Monitoring and Alerting
```bash
# Access Grafana dashboard
open http://localhost:3000/
# Default credentials: admin/admin

# Import pre-configured dashboards
# Navigate to Dashboards > Import
# Import dashboard JSON files from config/grafana/dashboards/
```

#### 5.3 Configure SSL/TLS (Production)
```bash
# Generate SSL certificate for production
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/keys/vedfolnir.key \
  -out ssl/certs/vedfolnir.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# Or use Let's Encrypt
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/certs/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/keys/

# Restart Nginx
docker-compose restart nginx
```

### Phase 6: Cleanup and Optimization

#### 6.1 Clean Up macOS Installation
```bash
# Stop and remove launchd services
launchctl unload ~/Library/LaunchAgents/com.vedfolnir.*.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.vedfolnir.*.plist

# Archive old installation
cd ..
tar -czf vedfolnir_macos_backup_$(date +%Y%m%d).tar.gz \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.git' \
  vedfolnir/

# Optional: Remove old installation after verification
# rm -rf vedfolnir/
```

#### 6.2 Optimize Docker Environment
```bash
# Clean up unused Docker resources
docker system prune -f

# Optimize container resource usage
# Edit docker-compose.yml to adjust resource limits based on your system

# Set up log rotation
# Configure logging limits in docker-compose.yml:
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Rollback Procedures

If migration fails or issues arise, you can rollback to the macOS deployment:

### Emergency Rollback
```bash
# Stop Docker services
docker-compose down

# Restore macOS services
brew services start mysql
brew services start redis

# Restore database from backup
mysql -u root -p < migration_data/mysql/vedfolnir_backup.sql

# Restore Redis data
cp migration_data/redis/dump.rdb /usr/local/var/db/redis/
brew services restart redis

# Restore application files
cp migration_data/app/env_backup .env

# Start application
python web_app.py & sleep 10
```

### Planned Rollback
```bash
# Create rollback script
cat > rollback_to_macos.sh << 'EOF'
#!/bin/bash
echo "Rolling back to macOS deployment..."

# Stop Docker services
docker-compose down

# Restore Homebrew services
brew services start mysql
brew services start redis

# Wait for services
sleep 10

# Restore database
mysql -u root -p < migration_data/mysql/vedfolnir_backup.sql

# Restore Redis
redis-cli FLUSHALL
cp migration_data/redis/dump.rdb /usr/local/var/db/redis/
brew services restart redis

# Restore application data
cp -r migration_data/app/storage/* storage/
cp migration_data/app/env_backup .env

echo "Rollback complete. Start application with: python web_app.py"
EOF

chmod +x rollback_to_macos.sh
```

## Migration Verification Checklist

- [ ] All containers are running and healthy
- [ ] Web interface is accessible at http://localhost/
- [ ] Database contains all migrated data (users, platforms, posts)
- [ ] Redis sessions are working
- [ ] Ollama integration is functional
- [ ] Storage files are accessible
- [ ] Platform connections can be reconfigured
- [ ] Caption generation works
- [ ] Monitoring dashboards are accessible
- [ ] SSL/TLS is configured (production)
- [ ] Backups are working
- [ ] Performance is acceptable

## Performance Comparison

After migration, compare performance metrics:

```bash
# Create performance test script
cat > performance_test.sh << 'EOF'
#!/bin/bash
echo "=== Performance Test ==="

# Web interface response time
echo "Web interface response time:"
time curl -s http://localhost/ > /dev/null

# Database query performance
echo "Database query performance:"
time docker-compose exec vedfolnir python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
config = Config()
db_manager = DatabaseManager(config)
with db_manager.get_session() as session:
    result = session.execute('SELECT COUNT(*) FROM posts').scalar()
    print(f'Posts: {result}')
"

# Redis performance
echo "Redis performance:"
time docker-compose exec redis redis-cli ping

echo "=== Performance Test Complete ==="
EOF

chmod +x performance_test.sh
./performance_test.sh
```

## Support and Troubleshooting

If you encounter issues during migration:

1. **Check the troubleshooting guide:** `docs/docker/docker-compose-troubleshooting-guide.md`
2. **Review migration logs:** All commands above log their output
3. **Validate each phase:** Don't proceed if a phase fails
4. **Use rollback procedures:** If migration fails, rollback and retry
5. **Seek help:** Create GitHub issue with migration logs and error messages

## Post-Migration Benefits

After successful migration, you'll have:

- **Improved Portability:** Run on any system with Docker
- **Better Scalability:** Easy horizontal scaling
- **Enhanced Security:** Containerized isolation and secrets management
- **Comprehensive Monitoring:** Built-in observability stack
- **Simplified Deployment:** Single command deployment
- **Better Backup/Recovery:** Automated backup procedures
- **Development Environment:** Consistent dev/prod environments