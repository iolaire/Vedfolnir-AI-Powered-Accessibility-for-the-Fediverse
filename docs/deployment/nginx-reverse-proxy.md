# Nginx Reverse Proxy Configuration

## Overview

The Nginx reverse proxy provides SSL termination, security headers, rate limiting, and static file serving for the Vedfolnir Docker Compose deployment. It acts as the entry point for all HTTP/HTTPS traffic and forwards requests to the appropriate backend services.

## Architecture

```
Internet → Nginx (Port 80/443) → Vedfolnir App (Port 5000)
                ↓
         Static Files (Direct Serving)
                ↓
         WebSocket Proxy → Vedfolnir WebSocket
                ↓
         Monitoring (Port 8080) → Prometheus/Grafana
```

## Features

### SSL/TLS Termination
- **Modern TLS Configuration**: TLS 1.2 and 1.3 support
- **Strong Cipher Suites**: ECDHE and ChaCha20-Poly1305 ciphers
- **OCSP Stapling**: Improved SSL performance
- **Self-Signed Certificates**: Automatic generation for development
- **Production Ready**: Easy certificate replacement for production

### Security Headers
- **HSTS**: HTTP Strict Transport Security with preload
- **CSP**: Content Security Policy with strict directives
- **X-Frame-Options**: Clickjacking protection
- **X-Content-Type-Options**: MIME type sniffing protection
- **X-XSS-Protection**: Cross-site scripting protection
- **Referrer-Policy**: Referrer information control

### Rate Limiting
- **Login Protection**: 5 requests per minute for login endpoints
- **API Protection**: 30 requests per minute for API endpoints
- **General Protection**: 60 requests per minute for general traffic
- **Connection Limiting**: 20 concurrent connections per IP

### Performance Optimization
- **Gzip Compression**: Automatic compression for text content
- **Static File Caching**: 1-year cache for static assets
- **Connection Keep-Alive**: Persistent connections
- **Proxy Buffering**: Optimized proxy buffer settings

### WebSocket Support
- **Real-Time Features**: Full WebSocket proxy support
- **Progress Updates**: Caption generation progress streaming
- **Connection Upgrade**: Proper HTTP to WebSocket upgrade handling

## Configuration Files

### Main Configuration (`config/nginx/nginx.conf`)
Global Nginx settings including:
- Worker processes and connections
- Logging configuration
- Gzip compression settings
- SSL session management
- Security defaults

### Server Configuration (`config/nginx/default.conf`)
Virtual host configuration including:
- HTTP to HTTPS redirect
- SSL certificate configuration
- Security headers
- Rate limiting rules
- Proxy configuration
- Static file serving
- WebSocket proxy setup

### Status Configuration (`config/nginx/nginx_status.conf`)
Monitoring endpoint configuration:
- Nginx status endpoint (`/nginx_status`)
- Health check endpoint (`/health`)
- Metrics endpoint for Prometheus

## Setup and Deployment

### Automatic Setup
```bash
# Run the setup script
./scripts/docker/setup-nginx.sh

# This will:
# - Create required directories
# - Generate SSL certificates
# - Validate configuration
# - Create management scripts
```

### Manual Setup
```bash
# Create directories
mkdir -p config/nginx ssl/certs ssl/keys logs/nginx

# Generate SSL certificates
./scripts/docker/generate-ssl-certs.sh

# Start Nginx service
docker-compose up -d nginx
```

### Development Setup
```bash
# Use development override
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d nginx

# This exposes additional ports for development:
# - Application: http://localhost:5000
# - File Browser: http://localhost:8080
# - MailHog: http://localhost:8025
```

## Management Commands

### Service Management
```bash
# Start Nginx
./scripts/docker/manage-nginx.sh start

# Stop Nginx
./scripts/docker/manage-nginx.sh stop

# Restart Nginx
./scripts/docker/manage-nginx.sh restart

# Reload configuration
./scripts/docker/manage-nginx.sh reload

# Test configuration
./scripts/docker/manage-nginx.sh test

# View logs
./scripts/docker/manage-nginx.sh logs

# Check status
./scripts/docker/manage-nginx.sh status

# View statistics
./scripts/docker/manage-nginx.sh stats

# SSL certificate info
./scripts/docker/manage-nginx.sh ssl-info
```

### Security Validation
```bash
# Validate security configuration
./scripts/docker/validate-nginx-security.sh

# This tests:
# - Security headers
# - SSL configuration
# - Rate limiting
# - TLS protocols
```

## Monitoring and Logging

### Access Logs
- **Location**: `logs/nginx/access.log`
- **Format**: Extended format with response times
- **Rotation**: Automatic with Docker logging driver

### Error Logs
- **Location**: `logs/nginx/error.log`
- **Level**: Warning and above
- **Security Events**: Rate limiting and blocked requests

### Status Endpoint
- **URL**: `http://localhost:8080/nginx_status`
- **Metrics**: Active connections, request statistics
- **Access**: Internal networks only

### Prometheus Integration
- **Exporter**: nginx-prometheus-exporter
- **Metrics**: Connection counts, request rates, response times
- **Grafana**: Pre-configured dashboards

## SSL Certificate Management

### Development Certificates
```bash
# Generate self-signed certificates
./scripts/docker/generate-ssl-certs.sh

# Certificates are created in:
# - ssl/certs/vedfolnir.crt
# - ssl/keys/vedfolnir.key
```

### Production Certificates
```bash
# Replace development certificates with production ones
cp /path/to/production.crt ssl/certs/vedfolnir.crt
cp /path/to/production.key ssl/keys/vedfolnir.key

# Set proper permissions
chmod 644 ssl/certs/vedfolnir.crt
chmod 600 ssl/keys/vedfolnir.key

# Reload Nginx
./scripts/docker/manage-nginx.sh reload
```

### Let's Encrypt Integration
```bash
# For production, consider using Let's Encrypt
# This requires domain name and external access

# Example with certbot
certbot certonly --webroot -w /var/www/html -d yourdomain.com

# Copy certificates to ssl directory
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/certs/vedfolnir.crt
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/keys/vedfolnir.key
```

## Security Configuration

### Rate Limiting Zones
```nginx
# Login protection
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# API protection
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

# General protection
limit_req_zone $binary_remote_addr zone=general:10m rate=60r/m;
```

### Security Headers
```nginx
# HSTS with preload
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; ..." always;

# Frame protection
add_header X-Frame-Options DENY always;

# MIME type protection
add_header X-Content-Type-Options nosniff always;
```

### Access Control
```nginx
# Block sensitive files
location ~ /\. {
    deny all;
}

# Block configuration files
location ~ \.(sql|log|conf)$ {
    deny all;
}

# Internal status endpoint
location /nginx_status {
    allow 127.0.0.1;
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    allow 192.168.0.0/16;
    deny all;
}
```

## Performance Tuning

### Worker Configuration
```nginx
worker_processes auto;
worker_connections 4096;
worker_rlimit_nofile 65535;
```

### Buffer Settings
```nginx
client_body_buffer_size 128k;
client_max_body_size 50m;
proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
```

### Caching Configuration
```nginx
# Static files
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# API responses (if cacheable)
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;
```

## Troubleshooting

### Common Issues

#### SSL Certificate Errors
```bash
# Check certificate validity
openssl x509 -in ssl/certs/vedfolnir.crt -text -noout

# Verify certificate and key match
openssl x509 -noout -modulus -in ssl/certs/vedfolnir.crt | openssl md5
openssl rsa -noout -modulus -in ssl/keys/vedfolnir.key | openssl md5
```

#### Configuration Errors
```bash
# Test configuration syntax
docker exec vedfolnir_nginx nginx -t

# Check error logs
docker logs vedfolnir_nginx

# Validate configuration files
./scripts/docker/manage-nginx.sh test
```

#### Connection Issues
```bash
# Check if Nginx is running
docker ps | grep nginx

# Test connectivity
curl -I http://localhost
curl -k -I https://localhost

# Check port binding
netstat -tlnp | grep :80
netstat -tlnp | grep :443
```

#### Rate Limiting Issues
```bash
# Check rate limit status
curl -I http://localhost/api/test

# Monitor rate limiting in logs
tail -f logs/nginx/access.log | grep 429

# Adjust rate limits in configuration if needed
```

### Performance Issues
```bash
# Monitor connection statistics
curl http://localhost:8080/nginx_status

# Check resource usage
docker stats vedfolnir_nginx

# Analyze access logs for slow requests
awk '$NF > 1.0 {print $0}' logs/nginx/access.log
```

## Testing

### Integration Tests
```bash
# Run Nginx proxy tests
python -m unittest tests.integration.test_nginx_proxy -v

# Test security configuration
./scripts/docker/validate-nginx-security.sh

# Performance testing
python -m unittest tests.integration.test_nginx_proxy.TestNginxPerformance -v
```

### Manual Testing
```bash
# Test HTTP to HTTPS redirect
curl -I http://localhost

# Test security headers
curl -I https://localhost -k

# Test rate limiting
for i in {1..10}; do curl -I http://localhost/api/test; done

# Test WebSocket proxy
curl -H "Upgrade: websocket" -H "Connection: Upgrade" http://localhost/ws
```

## Production Considerations

### Security Hardening
- Replace self-signed certificates with valid SSL certificates
- Configure firewall rules to restrict access
- Enable fail2ban for additional protection
- Regular security updates for Nginx image

### Performance Optimization
- Tune worker processes based on CPU cores
- Adjust buffer sizes based on traffic patterns
- Implement caching strategies for dynamic content
- Consider CDN integration for static assets

### Monitoring and Alerting
- Set up alerts for high error rates
- Monitor SSL certificate expiration
- Track response times and connection counts
- Log analysis for security events

### Backup and Recovery
- Backup SSL certificates and keys
- Version control Nginx configuration
- Document custom configuration changes
- Test recovery procedures regularly

## Integration with Other Services

### Prometheus Monitoring
- Nginx metrics exported via nginx-prometheus-exporter
- Custom dashboards in Grafana
- Alerting rules for critical metrics

### Log Aggregation
- Logs forwarded to Loki
- Structured logging format
- Real-time log analysis in Grafana

### Load Balancing
- Ready for multiple application instances
- Health check integration
- Automatic failover support

This Nginx configuration provides a robust, secure, and performant reverse proxy solution for the Vedfolnir Docker Compose deployment, with comprehensive monitoring, security, and management capabilities.