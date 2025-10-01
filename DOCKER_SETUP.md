# Vedfolnir Docker Compose Setup

This document provides instructions for setting up Vedfolnir using Docker Compose with comprehensive infrastructure including monitoring, logging, and security.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 8GB RAM available for containers
- At least 20GB disk space for volumes and images
- **Ollama service running on host system** (see [External Ollama Setup](docs/deployment/external-ollama-setup.md))

## Quick Start

1. **Clone and prepare the environment:**
   ```bash
   git clone <repository-url>
   cd vedfolnir
   ```

2. **Set up external Ollama service:**
   ```bash
   # Install and start Ollama on host system
   # See docs/deployment/external-ollama-setup.md for detailed instructions
   
   # Quick setup:
   brew install ollama  # macOS
   ollama serve &
   ollama pull llava:7b
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.docker .env
   # Edit .env with your specific configuration
   ```

4. **Generate secure secrets:**
   ```bash
   # Generate Flask secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/flask_secret_key.txt
   
   # Generate platform encryption key (Fernet key)
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/platform_encryption_key.txt
   
   # Generate secure passwords
   python -c "import secrets; print(secrets.token_urlsafe(24))" > secrets/mysql_root_password.txt
   python -c "import secrets; print(secrets.token_urlsafe(24))" > secrets/mysql_password.txt
   python -c "import secrets; print(secrets.token_urlsafe(24))" > secrets/redis_password.txt
   python -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/vault_token.txt
   ```

5. **Build and start services:**
   ```bash
   docker-compose up -d
   ```

6. **Verify deployment:**
   ```bash
   docker-compose ps
   curl http://localhost/health
   ```

## Service Architecture

### Core Services
- **vedfolnir**: Main application (port 5000, proxied via nginx)
- **mysql**: Database server (port 3306, localhost only)
- **redis**: Session and queue storage (port 6379, localhost only)
- **nginx**: Reverse proxy and SSL termination (ports 80, 443)

### External Services
- **ollama**: AI model server running on host system (port 11434, accessed via host.docker.internal)

### Observability Stack
- **prometheus**: Metrics collection (port 9090, localhost only)
- **grafana**: Monitoring dashboards (port 3000)
- **loki**: Log aggregation (port 3100, localhost only)

### Security
- **vault**: Secrets management (port 8200, localhost only)

## Volume Mounts

### Persistent Data
- `./storage/`: Application data, images, backups
- `./logs/`: Application and service logs
- `./config/`: Service configurations

### Docker Volumes
- `mysql_data`: MySQL database files
- `redis_data`: Redis persistence
- `ollama_data`: AI model data
- `prometheus_data`: Metrics storage
- `grafana_data`: Dashboard configurations
- `loki_data`: Log storage
- `vault_data`: Secrets storage

## Network Security

### Network Isolation
- **vedfolnir_internal**: Internal service communication
- **vedfolnir_monitoring**: Monitoring services
- **vedfolnir_external**: External-facing services

### Port Exposure
- Only nginx (80, 443) and grafana (3000) are exposed externally
- All other services accessible only via localhost or internal networks

## Configuration

### Environment Variables
Edit `.env` file to customize:
- Database passwords
- Redis authentication
- Vault tokens
- Resource limits
- SSL certificate paths

### Service Configuration
- **MySQL**: `config/mysql/vedfolnir.cnf`
- **Redis**: `config/redis/redis.conf`
- **Nginx**: `config/nginx/default.conf`
- **Prometheus**: `config/prometheus/prometheus.yml`
- **Grafana**: `config/grafana/grafana.ini`
- **Loki**: `config/loki/loki.yml`
- **Vault**: `config/vault/vault.hcl`

## SSL/TLS Setup

### Self-Signed Certificates (Development)
```bash
mkdir -p ssl/{certs,keys}
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/keys/vedfolnir.key \
  -out ssl/certs/vedfolnir.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Production Certificates
Place your SSL certificates in:
- `ssl/certs/vedfolnir.crt`
- `ssl/keys/vedfolnir.key`

## Management Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f vedfolnir
```

### Scale Application
```bash
docker-compose up -d --scale vedfolnir=3
```

### Backup Data
```bash
# MySQL backup
docker-compose exec mysql mysqldump -u root -p vedfolnir > backup.sql

# Redis backup
docker-compose exec redis redis-cli BGSAVE
```

## Monitoring and Observability

### Access Points
- **Application**: http://localhost (or https with SSL)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090 (localhost only)

### Key Metrics
- Application performance and error rates
- Database connection pools and query performance
- Redis memory usage and session metrics
- Container resource utilization
- Network traffic and security events

## Troubleshooting

### Common Issues

1. **Services not starting:**
   ```bash
   docker-compose logs <service-name>
   ```

2. **Database connection errors:**
   - Check MySQL container logs
   - Verify password in secrets files
   - Ensure database initialization completed

3. **Redis connection errors:**
   - Check Redis container logs
   - Verify Redis password configuration
   - Check network connectivity

4. **SSL certificate errors:**
   - Verify certificate files exist and are readable
   - Check certificate validity and paths

### Health Checks
```bash
# Check all service health
docker-compose ps

# Test application health
curl http://localhost/health

# Check database connectivity
docker-compose exec vedfolnir python -c "from config import Config; print('DB OK')"
```

## Security Considerations

### Secrets Management
- All sensitive data stored in Docker secrets
- Secrets files should have restricted permissions (600)
- Regular secret rotation recommended

### Network Security
- Internal networks isolate services
- Only necessary ports exposed to host
- Rate limiting configured in nginx

### Container Security
- Non-root users in all containers
- Read-only root filesystems where possible
- Resource limits prevent resource exhaustion

## Development vs Production

### Development Override
Create `docker-compose.dev.yml`:
```yaml
version: '3.8'
services:
  vedfolnir:
    build:
      target: development
    volumes:
      - .:/app
    environment:
      - FLASK_DEBUG=true
    ports:
      - "5000:5000"
      - "5678:5678"  # Debugger port
```

Run with: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d`

### Production Optimizations
- Use production Dockerfile target
- Enable SSL/TLS with valid certificates
- Configure proper resource limits
- Set up log rotation and monitoring alerts
- Implement backup automation

## Migration from macOS

If migrating from existing macOS deployment:

1. **Export existing data:**
   ```bash
   # MySQL export
   mysqldump -u root -p vedfolnir > vedfolnir_export.sql
   
   # Copy storage files
   cp -r storage/ docker-storage/
   ```

2. **Import to containers:**
   ```bash
   # Start containers
   docker-compose up -d mysql
   
   # Import database
   docker-compose exec -T mysql mysql -u root -p vedfolnir < vedfolnir_export.sql
   
   # Copy storage files
   docker cp docker-storage/. vedfolnir_vedfolnir_1:/app/storage/
   ```

3. **Update configuration:**
   - Update database connection strings
   - Verify environment variables
   - Test all functionality

## Support

For issues and questions:
1. Check container logs: `docker-compose logs <service>`
2. Verify configuration files
3. Check network connectivity between services
4. Review security and firewall settings