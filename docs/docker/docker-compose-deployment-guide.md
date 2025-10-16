# Vedfolnir Docker Deployment Guide

## Overview

Vedfolnir uses a comprehensive Docker setup with multiple environment configurations for development, production, and testing. This guide covers all aspects of the Docker deployment including email configuration, environment management, and service orchestration.

## 📧 Email Configuration Across Environments

### Current Email Setup

Your email configuration is handled differently across environments:

#### **Development Environment**
- **Service**: MailHog container (local email testing)
- **Configuration**: Uses `.env.development`
- **SMTP**: `mailhog:1025` (internal container network)
- **Web UI**: http://localhost:8025
- **Benefits**: No external dependencies, visual email testing

#### **Production Environment** 
- **Service**: Mailtrap (your existing configuration)
- **Configuration**: Uses `.env.production` → falls back to `.env`
- **SMTP**: `sandbox.smtp.mailtrap.io:587`
- **Credentials**: Your existing Mailtrap account
- **Benefits**: Real email delivery testing

#### **Test Environment**
- **Service**: Mailtrap (same as production)
- **Configuration**: Uses `.env.test` → falls back to `.env`
- **SMTP**: Same as production but isolated database

### Email Configuration Files

Your existing `.env` file contains:
```bash
# Email Configuration (sandbox defaults)
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=587
MAIL_USE_TLS=false
MAIL_USERNAME=24cc1476b47de6
MAIL_PASSWORD=7be97c03d858ab
MAIL_DEFAULT_SENDER=iolaire@vedfolnir.org
```

**✅ This configuration will be used for production and test environments automatically.**

## 🐳 Docker Architecture

### Service Overview

| Service | Purpose | Networks | Ports (Dev) | Ports (Prod) |
|---------|---------|----------|-------------|--------------|
| **vedfolnir** | Main application | internal, external | 5000, 5678 | - |
| **mysql** | MariaDB database | internal | 3306 | - |
| **redis** | Session & cache | internal | 6379 | - |
| **nginx** | Reverse proxy | external, internal | 80, 443 | 80, 443 |
| **vault** | Secrets management | internal | - | - |
| **prometheus** | Metrics collection | monitoring, internal | - | - |
| **grafana** | Monitoring dashboard | monitoring, external | - | 3000 |
| **loki** | Log aggregation | monitoring | - | - |

### Development-Only Services

| Service | Purpose | Port | Access |
|---------|---------|------|--------|
| **mailhog** | Email testing | 8025 | http://localhost:8025 |
| **phpmyadmin** | MySQL management | 8080 | http://localhost:8080 |
| **redis-commander** | Redis management | 8081 | http://localhost:8081 |

## 🚀 Quick Start Commands

### Development Environment
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f vedfolnir

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

### Production Environment
```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop production environment
docker-compose -f docker-compose.prod.yml down
```

### Test Environment
```bash
# Run unit tests
docker-compose -f docker-compose.test.yml --profile unit-tests up --abort-on-container-exit

# Run integration tests
docker-compose -f docker-compose.test.yml --profile integration-tests up --abort-on-container-exit

# Run performance tests
docker-compose -f docker-compose.test.yml --profile performance-tests up --abort-on-container-exit
```

## 📁 Environment File Structure

### Environment File Priority
Docker Compose loads environment files in this order:
1. **Environment-specific file** (`.env.development`, `.env.production`)
2. **Default file** (`.env`) - as fallback
3. **Docker Compose environment section** - overrides files
4. **System environment variables** - highest priority

### Current Environment Files

#### `.env` (Default/Fallback)
- Contains your Mailtrap email configuration
- Used as fallback for all environments
- Contains development defaults

#### `.env.development` (Development)
- MailHog email configuration (`MAIL_SERVER=mailhog`)
- Development database settings
- Debug and profiling enabled
- Relaxed security settings

#### `.env.production` (Production)
- References your `.env` email settings via variables
- Production database settings
- Strict security settings
- Performance optimizations

## 🔧 Detailed Service Configuration

### Vedfolnir Application

#### Development Configuration
```yaml
services:
  vedfolnir:
    build:
      target: development
    ports:
      - "5000:5000"    # Flask application
      - "5678:5678"    # Python debugger
    volumes:
      - .:/app         # Hot reloading
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=true
      - MAIL_SERVER=mailhog  # Uses MailHog
```

#### Production Configuration
```yaml
services:
  vedfolnir:
    build:
      target: production
    # No direct port exposure (via nginx)
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=false
      - MAIL_SERVER=${MAIL_SERVER}  # Uses your Mailtrap config
```

### Database Services

#### MariaDB (MySQL)
- **Development**: Exposed on port 3306 for external tools
- **Production**: Internal network only for security
- **Volumes**: Persistent data storage
- **Health checks**: Automatic service dependency management

#### Redis
- **Development**: Exposed on port 6379 for external tools
- **Production**: Internal network only for security
- **Configuration**: Session storage and caching
- **Persistence**: AOF and RDB snapshots

### Monitoring Stack

#### Prometheus
- Metrics collection from all services
- Custom application metrics
- Resource usage monitoring
- Alert rule configuration

#### Grafana
- Visual dashboards for metrics
- Real-time monitoring
- Custom dashboard provisioning
- Alert notifications

#### Loki
- Centralized log aggregation
- Structured logging support
- Log retention policies
- Integration with Grafana

## 🔐 Security Configuration

### Network Isolation
- **vedfolnir_internal**: Secure internal communication
- **vedfolnir_external**: Public-facing services
- **vedfolnir_monitoring**: Monitoring services isolation

### Secrets Management
```yaml
secrets:
  flask_secret_key:
    file: ./secrets/flask_secret_key.txt
  mysql_password:
    file: ./secrets/mysql_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
```

### Production Security Features
- No direct port exposure for internal services
- Docker secrets for sensitive data
- Non-root user execution
- Security options and capabilities

## 📊 Monitoring and Observability

### Available Dashboards
- **Grafana**: http://localhost:3000 (production)
- **Prometheus**: Internal network only
- **Application metrics**: Built-in Flask metrics

### Log Management
- **Structured logging**: JSON format in production
- **Log rotation**: Automatic size-based rotation
- **Centralized logs**: Loki aggregation
- **Retention policies**: Configurable retention periods

## 🧪 Testing Framework

### Test Profiles
```bash
# Unit tests
docker-compose -f docker-compose.test.yml --profile unit-tests up

# Integration tests  
docker-compose -f docker-compose.test.yml --profile integration-tests up

# Performance tests
docker-compose -f docker-compose.test.yml --profile performance-tests up

# Security tests
docker-compose -f docker-compose.test.yml --profile security-tests up
```

### Test Database
- Isolated MariaDB instance
- Temporary data (tmpfs for speed)
- Separate Redis instance
- Clean state for each test run

## 🔄 Development Workflow

### Hot Reloading Setup
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View application logs
docker-compose -f docker-compose.dev.yml logs -f vedfolnir

# Access development tools
open http://localhost:5000      # Application
open http://localhost:8025      # MailHog (email testing)
open http://localhost:8080      # phpMyAdmin (database)
open http://localhost:8081      # Redis Commander
```

### Debugging
```bash
# Enable debugger (modify docker-compose.dev.yml)
command: ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "web_app.py"]

# Connect debugger to localhost:5678
```

## 🚀 Production Deployment

### Prerequisites
1. **Secrets Setup**:
   ```bash
   mkdir -p secrets
   echo "your-flask-secret" > secrets/flask_secret_key.txt
   echo "your-mysql-password" > secrets/mysql_password.txt
   echo "your-redis-password" > secrets/redis_password.txt
   ```

2. **SSL Certificates**:
   ```bash
   mkdir -p ssl/certs ssl/keys
   # Place your SSL certificates in ssl/ directory
   ```

3. **Configuration**:
   ```bash
   # Update .env.production with your domain
   BASE_URL=https://your-domain.com
   ```

### Production Startup
```bash
# Start all production services
docker-compose -f docker-compose.prod.yml up -d

# Verify services are healthy
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Production Monitoring
- **Application**: https://your-domain.com
- **Grafana**: https://your-domain.com:3000
- **Health checks**: Built-in service health monitoring

## 🔧 Maintenance Commands

### Database Management
```bash
# Backup database
docker-compose -f docker-compose.prod.yml exec mysql mysqldump -u root -p vedfolnir > backup.sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T mysql mysql -u root -p vedfolnir < backup.sql
```

### Log Management
```bash
# View application logs
docker-compose logs -f vedfolnir

# View all service logs
docker-compose logs -f

# Clear logs
docker-compose down && docker system prune -f
```

### Updates and Scaling
```bash
# Update application
docker-compose -f docker-compose.prod.yml build vedfolnir
docker-compose -f docker-compose.prod.yml up -d vedfolnir

# Scale application (production)
docker-compose -f docker-compose.prod.yml up -d --scale vedfolnir=3
```

## 🐛 Troubleshooting

### Common Issues

#### Email Not Working
1. **Development**: Check MailHog is running at http://localhost:8025
2. **Production**: Verify Mailtrap credentials in `.env`
3. **Check logs**: `docker-compose logs -f vedfolnir`

#### Database Connection Issues
1. **Check service health**: `docker-compose ps`
2. **Verify credentials**: Check environment files
3. **Network connectivity**: Ensure services are on same network

#### Performance Issues
1. **Check resource usage**: `docker stats`
2. **Review logs**: Look for memory/CPU warnings
3. **Monitor metrics**: Use Grafana dashboards

### Debug Commands
```bash
# Enter application container
docker-compose exec vedfolnir bash

# Check service health
docker-compose ps

# View resource usage
docker stats

# Check networks
docker network ls
docker network inspect vedfolnir_vedfolnir_internal
```

## 📋 Environment Variables Reference

### Email Configuration
| Variable | Development | Production | Description |
|----------|-------------|------------|-------------|
| `MAIL_SERVER` | `mailhog` | `sandbox.smtp.mailtrap.io` | SMTP server |
| `MAIL_PORT` | `1025` | `587` | SMTP port |
| `MAIL_USE_TLS` | `false` | `false` | TLS encryption |
| `MAIL_USERNAME` | `` | `24cc1476b47de6` | SMTP username |
| `MAIL_PASSWORD` | `` | `7be97c03d858ab` | SMTP password |

### Database Configuration
| Variable | Development | Production | Description |
|----------|-------------|------------|-------------|
| `DATABASE_URL` | `mysql://vedfolnir:dev_password@mysql:3306/vedfolnir_dev` | `mysql://vedfolnir:${MYSQL_PASSWORD}@mysql:3306/vedfolnir` | Database connection |
| `DB_POOL_SIZE` | `10` | `20` | Connection pool size |
| `DB_MAX_OVERFLOW` | `20` | `30` | Max overflow connections |

### Security Configuration
| Variable | Development | Production | Description |
|----------|-------------|------------|-------------|
| `SECURITY_CSRF_ENABLED` | `true` | `true` | CSRF protection |
| `SECURITY_RATE_LIMITING_ENABLED` | `false` | `true` | Rate limiting |
| `SESSION_COOKIE_SECURE` | `false` | `true` | Secure cookies |

## 🎯 Best Practices

### Development
- Use MailHog for email testing
- Enable debug mode and profiling
- Mount source code for hot reloading
- Use exposed ports for external tools

### Production
- Use Docker secrets for sensitive data
- Enable all security features
- Use internal networks only
- Implement proper SSL/TLS
- Monitor resource usage
- Set up automated backups

### Testing
- Use isolated test databases
- Implement comprehensive test coverage
- Use tmpfs for faster test execution
- Clean up test data between runs

## 📞 Support

For issues with the Docker setup:
1. Check service logs: `docker-compose logs -f [service]`
2. Verify environment configuration
3. Check network connectivity
4. Review resource usage
5. Consult troubleshooting section above

---

**Note**: Your existing email configuration in `.env` will automatically be used for production and test environments, while development uses the local MailHog container f

# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image vedfolnir_vedfolnir

# Update secrets
./scripts/security/rotate_secrets.sh
```

## Integration Testing

### Automated Testing
```bash
# Run integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Test specific functionality
./scripts/test/test_platform_integration.sh
./scripts/test/test_ollama_integration.sh
./scripts/test/test_websocket_functionality.sh
```

### Manual Testing
```bash
# Test web interface
curl -f http://localhost/
curl -f http://localhost/login
curl -f http://localhost/health

# Test API endpoints
curl -f http://localhost/api/health
curl -f http://localhost/api/platforms

# Test WebSocket connectivity
wscat -c ws://localhost/ws/progress
```

## Migration from macOS

See the dedicated [Migration Guide](migration-from-macos-guide.md) for detailed instructions on migrating from the previous macOS deployment.

## Support and Resources

### Documentation
- [Troubleshooting Guide](docker-compose-troubleshooting-guide.md)
- [Migration Guide](migration-from-macos-guide.md)
- [Operations Guide](docker-compose-operations-guide.md)
- [Security Guide](docker-compose-security-guide.md)

### Community
- GitHub Issues: Report bugs and feature requests
- Documentation: Contribute to documentation improvements
- Testing: Help test new features and deployments

### Professional Support
For enterprise deployments and professional support, contact the development team for:
- Custom deployment configurations
- Performance optimization consulting
- Security auditing and compliance
- Training and onboarding