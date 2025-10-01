# Docker Compose Troubleshooting Guide

## Common Issues and Solutions

### Container Startup Issues

#### Services Won't Start
**Symptoms:**
- Containers exit immediately
- Services show "Exited (1)" status
- Error messages in logs

**Diagnosis:**
```bash
# Check container status
docker-compose ps

# View logs for specific service
docker-compose logs vedfolnir
docker-compose logs mysql
docker-compose logs redis

# Check resource usage
docker stats
```

**Solutions:**
1. **Insufficient Resources:**
   ```bash
   # Check available resources
   free -h
   df -h
   
   # Reduce resource limits in docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 1G  # Reduce from 2G
   ```

2. **Port Conflicts:**
   ```bash
   # Check port usage
   netstat -tulpn | grep :80
   netstat -tulpn | grep :3306
   
   # Change ports in docker-compose.yml
   ports:
     - "8080:80"  # Use different host port
   ```

3. **Permission Issues:**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 data/
   sudo chown -R 999:999 data/mysql/
   sudo chmod -R 755 logs/
   ```

#### Database Connection Failures
**Symptoms:**
- Application can't connect to MySQL
- "Connection refused" errors
- Database initialization failures

**Diagnosis:**
```bash
# Check MySQL container status
docker-compose logs mysql

# Test database connectivity
docker-compose exec mysql mysql -u root -p -e "SELECT 1;"

# Check network connectivity
docker-compose exec vedfolnir ping mysql
```

**Solutions:**
1. **MySQL Not Ready:**
   ```bash
   # Wait for MySQL to be ready
   docker-compose exec mysql mysqladmin ping -h localhost -u root -p
   
   # Add health checks to docker-compose.yml
   healthcheck:
     test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
     timeout: 20s
     retries: 10
   ```

2. **Wrong Credentials:**
   ```bash
   # Verify secret files
   cat secrets/mysql_password.txt
   cat secrets/mysql_root_password.txt
   
   # Reset MySQL password
   docker-compose exec mysql mysql -u root -p -e "
   ALTER USER 'vedfolnir'@'%' IDENTIFIED BY 'new_password';
   FLUSH PRIVILEGES;"
   ```

3. **Database Not Created:**
   ```bash
   # Create database manually
   docker-compose exec mysql mysql -u root -p -e "
   CREATE DATABASE IF NOT EXISTS vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir'@'%';
   FLUSH PRIVILEGES;"
   ```

#### Redis Connection Issues
**Symptoms:**
- Session data not persisting
- Queue workers not processing jobs
- Redis connection timeouts

**Diagnosis:**
```bash
# Check Redis status
docker-compose logs redis
docker-compose exec redis redis-cli ping

# Test Redis connectivity from app
docker-compose exec vedfolnir python -c "
import redis
r = redis.Redis(host='redis', port=6379, password='$(cat secrets/redis_password.txt)')
print(r.ping())
"
```

**Solutions:**
1. **Redis Authentication:**
   ```bash
   # Verify Redis password
   docker-compose exec redis redis-cli -a "$(cat secrets/redis_password.txt)" ping
   
   # Update Redis configuration
   # In config/redis/redis.conf:
   requirepass your_redis_password
   ```

2. **Memory Issues:**
   ```bash
   # Check Redis memory usage
   docker-compose exec redis redis-cli info memory
   
   # Configure memory limits in redis.conf
   maxmemory 512mb
   maxmemory-policy allkeys-lru
   ```

### Application Issues

#### Web Interface Not Accessible
**Symptoms:**
- HTTP 502/503 errors
- Connection timeouts
- Nginx errors

**Diagnosis:**
```bash
# Check Nginx status and logs
docker-compose logs nginx
curl -I http://localhost/

# Check application status
docker-compose logs vedfolnir
curl -f http://localhost:5000/health  # Direct app access
```

**Solutions:**
1. **Nginx Configuration:**
   ```bash
   # Test Nginx configuration
   docker-compose exec nginx nginx -t
   
   # Reload Nginx configuration
   docker-compose exec nginx nginx -s reload
   ```

2. **Application Not Ready:**
   ```bash
   # Check application startup
   docker-compose logs -f vedfolnir
   
   # Verify application health
   docker-compose exec vedfolnir curl -f http://localhost:5000/health
   ```

3. **SSL Certificate Issues:**
   ```bash
   # Check certificate validity
   openssl x509 -in ssl/certs/vedfolnir.crt -text -noout
   
   # Regenerate self-signed certificate
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout ssl/keys/vedfolnir.key \
     -out ssl/certs/vedfolnir.crt
   ```

#### Ollama Integration Failures
**Symptoms:**
- Caption generation fails
- "Connection refused" to Ollama API
- AI model not responding

**Diagnosis:**
```bash
# Test Ollama connectivity from host
curl http://localhost:11434/api/version

# Test from container
docker-compose exec vedfolnir curl -f http://host.docker.internal:11434/api/version

# Check Ollama model availability
curl http://localhost:11434/api/tags
```

**Solutions:**
1. **Ollama Not Running:**
   ```bash
   # Start Ollama service
   ollama serve
   
   # Pull required model
   ollama pull llava:7b
   ```

2. **Network Connectivity:**
   ```bash
   # Test host.docker.internal resolution
   docker-compose exec vedfolnir nslookup host.docker.internal
   
   # Alternative: Use host IP directly
   # In .env.docker:
   OLLAMA_URL=http://192.168.1.100:11434
   ```

3. **Model Loading Issues:**
   ```bash
   # Check Ollama logs
   journalctl -u ollama -f
   
   # Restart Ollama service
   sudo systemctl restart ollama
   ```

### Performance Issues

#### Slow Response Times
**Symptoms:**
- Web interface loads slowly
- Database queries timeout
- High CPU/memory usage

**Diagnosis:**
```bash
# Monitor resource usage
docker stats
htop

# Check database performance
docker-compose exec mysql mysqladmin processlist -u root -p

# Analyze slow queries
docker-compose exec mysql mysql -u root -p -e "
SELECT * FROM information_schema.processlist WHERE time > 5;
"
```

**Solutions:**
1. **Resource Constraints:**
   ```bash
   # Increase container limits
   # In docker-compose.yml:
   deploy:
     resources:
       limits:
         cpus: '4.0'
         memory: 4G
   ```

2. **Database Optimization:**
   ```bash
   # Optimize database tables
   docker-compose exec mysql mysqlcheck --optimize --all-databases
   
   # Update MySQL configuration
   # In config/mysql/vedfolnir.cnf:
   innodb_buffer_pool_size = 1G
   query_cache_size = 128M
   ```

3. **Connection Pool Tuning:**
   ```bash
   # Update database connection settings
   # In .env.docker:
   DB_POOL_SIZE=30
   DB_MAX_OVERFLOW=50
   ```

#### Memory Leaks
**Symptoms:**
- Containers consuming increasing memory
- Out of memory errors
- System becomes unresponsive

**Diagnosis:**
```bash
# Monitor memory usage over time
watch docker stats

# Check for memory leaks in application
docker-compose exec vedfolnir python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

**Solutions:**
1. **Restart Containers:**
   ```bash
   # Restart specific service
   docker-compose restart vedfolnir
   
   # Restart all services
   docker-compose restart
   ```

2. **Memory Limits:**
   ```bash
   # Set strict memory limits
   deploy:
     resources:
       limits:
         memory: 2G
       reservations:
         memory: 1G
   ```

### Storage and Volume Issues

#### Volume Mount Failures
**Symptoms:**
- Data not persisting
- Permission denied errors
- Files not accessible from host

**Diagnosis:**
```bash
# Check volume mounts
docker-compose exec vedfolnir ls -la /app/storage
docker-compose exec mysql ls -la /var/lib/mysql

# Check host permissions
ls -la data/
ls -la storage/
```

**Solutions:**
1. **Permission Issues:**
   ```bash
   # Fix ownership
   sudo chown -R $(id -u):$(id -g) storage/
   sudo chown -R 999:999 data/mysql/
   sudo chown -R 1001:1001 data/redis/
   
   # Set proper permissions
   chmod -R 755 storage/
   chmod -R 700 data/mysql/
   ```

2. **SELinux Issues (RHEL/CentOS):**
   ```bash
   # Set SELinux context
   sudo setsebool -P container_manage_cgroup on
   sudo chcon -Rt svirt_sandbox_file_t storage/
   ```

#### Disk Space Issues
**Symptoms:**
- "No space left on device" errors
- Containers failing to start
- Log files growing too large

**Diagnosis:**
```bash
# Check disk usage
df -h
du -sh data/
du -sh logs/

# Check Docker space usage
docker system df
```

**Solutions:**
1. **Clean Up Docker:**
   ```bash
   # Remove unused containers, networks, images
   docker system prune -f
   
   # Remove unused volumes
   docker volume prune -f
   ```

2. **Log Rotation:**
   ```bash
   # Configure log rotation
   # In docker-compose.yml:
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

3. **Move Data Directory:**
   ```bash
   # Move to larger partition
   sudo mv data/ /var/lib/vedfolnir/data/
   ln -s /var/lib/vedfolnir/data/ data
   ```

### Security Issues

#### SSL/TLS Certificate Problems
**Symptoms:**
- Browser security warnings
- Certificate expired errors
- HTTPS not working

**Diagnosis:**
```bash
# Check certificate validity
openssl x509 -in ssl/certs/vedfolnir.crt -text -noout | grep -A2 "Validity"

# Test SSL connection
openssl s_client -connect localhost:443 -servername localhost
```

**Solutions:**
1. **Renew Certificates:**
   ```bash
   # Let's Encrypt renewal
   certbot renew
   docker-compose restart nginx
   
   # Generate new self-signed certificate
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout ssl/keys/vedfolnir.key \
     -out ssl/certs/vedfolnir.crt
   ```

2. **Certificate Path Issues:**
   ```bash
   # Verify certificate files exist
   ls -la ssl/certs/vedfolnir.crt
   ls -la ssl/keys/vedfolnir.key
   
   # Check Nginx configuration
   docker-compose exec nginx nginx -t
   ```

#### Secrets Management Issues
**Symptoms:**
- Authentication failures
- Vault access denied
- Secret rotation failures

**Diagnosis:**
```bash
# Check secret files
ls -la secrets/
cat secrets/flask_secret_key.txt

# Test Vault connectivity
docker-compose exec vault vault status
```

**Solutions:**
1. **Regenerate Secrets:**
   ```bash
   # Generate new secrets
   openssl rand -base64 32 > secrets/flask_secret_key.txt
   openssl rand -base64 32 > secrets/platform_encryption_key.txt
   
   # Restart services
   docker-compose restart vedfolnir
   ```

2. **Vault Initialization:**
   ```bash
   # Initialize Vault
   docker-compose exec vault vault operator init
   
   # Unseal Vault
   docker-compose exec vault vault operator unseal
   ```

### Monitoring and Logging Issues

#### Grafana Dashboard Not Loading
**Symptoms:**
- Grafana interface not accessible
- Dashboards showing no data
- Authentication failures

**Diagnosis:**
```bash
# Check Grafana status
docker-compose logs grafana
curl -f http://localhost:3000/

# Check Prometheus connectivity
docker-compose exec grafana curl -f http://prometheus:9090/api/v1/status/config
```

**Solutions:**
1. **Reset Grafana:**
   ```bash
   # Reset Grafana data
   docker-compose stop grafana
   sudo rm -rf data/grafana/
   docker-compose up -d grafana
   ```

2. **Data Source Configuration:**
   ```bash
   # Verify Prometheus data source
   # Access Grafana at http://localhost:3000
   # Default credentials: admin/admin
   # Add Prometheus data source: http://prometheus:9090
   ```

#### Log Aggregation Issues
**Symptoms:**
- Logs not appearing in Loki
- Grafana can't query logs
- Log parsing errors

**Diagnosis:**
```bash
# Check Loki status
docker-compose logs loki
curl -f http://localhost:3100/ready

# Test log ingestion
docker-compose exec loki curl -f http://localhost:3100/loki/api/v1/labels
```

**Solutions:**
1. **Restart Log Services:**
   ```bash
   docker-compose restart loki
   docker-compose restart grafana
   ```

2. **Log Driver Configuration:**
   ```bash
   # Update logging configuration in docker-compose.yml
   logging:
     driver: loki
     options:
       loki-url: "http://loki:3100/loki/api/v1/push"
   ```

## Diagnostic Commands

### Health Check Script
```bash
#!/bin/bash
# health_check.sh

echo "=== Vedfolnir Docker Compose Health Check ==="

# Check container status
echo "Container Status:"
docker-compose ps

# Check service health
echo -e "\nService Health:"
curl -f http://localhost/health && echo "✅ Web interface OK" || echo "❌ Web interface FAILED"
curl -f http://localhost:3000/ && echo "✅ Grafana OK" || echo "❌ Grafana FAILED"

# Check database connectivity
echo -e "\nDatabase Connectivity:"
docker-compose exec -T mysql mysql -u root -p$(cat secrets/mysql_root_password.txt) -e "SELECT 1;" && echo "✅ MySQL OK" || echo "❌ MySQL FAILED"

# Check Redis connectivity
echo -e "\nRedis Connectivity:"
docker-compose exec -T redis redis-cli -a "$(cat secrets/redis_password.txt)" ping && echo "✅ Redis OK" || echo "❌ Redis FAILED"

# Check Ollama connectivity
echo -e "\nOllama Connectivity:"
docker-compose exec -T vedfolnir curl -f http://host.docker.internal:11434/api/version && echo "✅ Ollama OK" || echo "❌ Ollama FAILED"

# Check disk space
echo -e "\nDisk Usage:"
df -h | grep -E "(Filesystem|/dev/)"
du -sh data/ logs/ storage/

# Check resource usage
echo -e "\nResource Usage:"
docker stats --no-stream

echo -e "\n=== Health Check Complete ==="
```

### Log Collection Script
```bash
#!/bin/bash
# collect_logs.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="debug_logs_$TIMESTAMP"

mkdir -p "$LOG_DIR"

echo "Collecting logs to $LOG_DIR..."

# Container logs
docker-compose logs --no-color > "$LOG_DIR/docker-compose.log"
docker-compose logs --no-color vedfolnir > "$LOG_DIR/vedfolnir.log"
docker-compose logs --no-color mysql > "$LOG_DIR/mysql.log"
docker-compose logs --no-color redis > "$LOG_DIR/redis.log"
docker-compose logs --no-color nginx > "$LOG_DIR/nginx.log"

# System information
docker-compose ps > "$LOG_DIR/container_status.txt"
docker stats --no-stream > "$LOG_DIR/resource_usage.txt"
df -h > "$LOG_DIR/disk_usage.txt"
free -h > "$LOG_DIR/memory_usage.txt"

# Configuration files
cp docker-compose.yml "$LOG_DIR/"
cp .env.docker "$LOG_DIR/env_config.txt"

# Application logs
cp -r logs/ "$LOG_DIR/app_logs/" 2>/dev/null || true

echo "Logs collected in $LOG_DIR"
echo "Please include this directory when reporting issues."
```

## Getting Help

### Before Reporting Issues
1. Run the health check script
2. Collect logs using the log collection script
3. Check this troubleshooting guide
4. Search existing GitHub issues

### Reporting Issues
Include the following information:
- Operating system and version
- Docker and Docker Compose versions
- Complete error messages
- Steps to reproduce the issue
- Health check results
- Relevant log files

### Community Resources
- GitHub Issues: https://github.com/your-repo/vedfolnir/issues
- Documentation: https://docs.vedfolnir.com
- Community Forum: https://community.vedfolnir.com

### Emergency Procedures
If the system is completely unresponsive:

1. **Stop all services:**
   ```bash
   docker-compose down
   ```

2. **Clean up resources:**
   ```bash
   docker system prune -f
   docker volume prune -f
   ```

3. **Restore from backup:**
   ```bash
   ./scripts/backup/restore_backup.sh /path/to/latest/backup
   ```

4. **Start services:**
   ```bash
   docker-compose up -d
   ```

5. **Verify functionality:**
   ```bash
   ./scripts/health_check.sh
   ```