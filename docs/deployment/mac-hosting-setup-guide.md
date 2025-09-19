# Mac Hosting Setup Guide

Complete guide for setting up Vedfolnir hosting on macOS with Gunicorn and Redis Queue integration.

## Quick Setup

For a fully automated setup, run:

```bash
# Make sure you're in the project root directory
cd /path/to/vedfolnir

# Run the automated setup script
./scripts/setup/setup_mac_hosting.sh
```

This script will:
- Install all required system dependencies (Homebrew, Python, MySQL, Redis, Nginx)
- Set up Python virtual environment with pyenv
- Configure database and generate environment secrets
- Install and configure Gunicorn service with launchd
- Create management scripts for easy service control

## Manual Setup Steps

If you prefer manual setup or need to troubleshoot:

### 1. System Dependencies

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install system dependencies
brew install pyenv pyenv-virtualenv mysql redis nginx
brew install openssl readline sqlite3 xz zlib tcl-tk

# Start services
brew services start mysql
brew services start redis
```

### 2. Python Environment

```bash
# Install Python 3.12.5
pyenv install 3.12.5

# Create virtual environment
pyenv virtualenv 3.12.5 gunicorn-host

# Activate virtual environment
pyenv activate gunicorn-host

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn eventlet
```

### 3. Database Setup

```bash
# Generate environment configuration
python scripts/setup/generate_env_secrets.py

# Initialize database
python scripts/setup/mysql_init_and_migrate.py

# Create admin user
python scripts/setup/setup_admin_user.py
```

### 4. Gunicorn Service Configuration

The setup script creates these files:

- `start_gunicorn.sh` - Gunicorn startup script
- `com.vedfolnir.gunicorn.plist` - launchd service configuration
- `scripts/manage_services.sh` - Service management script

Install the service:

```bash
# Copy service configuration
cp com.vedfolnir.gunicorn.plist ~/Library/LaunchAgents/

# Load and start service
launchctl load ~/Library/LaunchAgents/com.vedfolnir.gunicorn.plist
launchctl start com.vedfolnir.gunicorn
```

## Service Management

Use the management script for easy service control:

```bash
# Start all services
./scripts/manage_services.sh start

# Stop Gunicorn service
./scripts/manage_services.sh stop

# Restart Gunicorn service
./scripts/manage_services.sh restart

# Check service status
./scripts/manage_services.sh status

# View recent logs
./scripts/manage_services.sh logs
```

## Manual Service Commands

### Gunicorn Service

```bash
# Start service
launchctl start com.vedfolnir.gunicorn

# Stop service
launchctl stop com.vedfolnir.gunicorn

# Restart service
launchctl stop com.vedfolnir.gunicorn && launchctl start com.vedfolnir.gunicorn

# Check if service is running
launchctl list | grep com.vedfolnir.gunicorn

# View service logs
tail -f logs/vedfolnir.log
tail -f logs/vedfolnir.err
```

### System Services

```bash
# MySQL
brew services start mysql
brew services stop mysql
brew services restart mysql

# Redis
brew services start redis
brew services stop redis
brew services restart redis

# Nginx (optional)
sudo brew services start nginx
sudo brew services stop nginx
sudo brew services restart nginx
```

## Configuration Files

### Gunicorn Configuration

The `start_gunicorn.sh` script configures Gunicorn with:

- **Workers**: 4 (adjust based on CPU cores)
- **Worker Class**: eventlet (for WebSocket support)
- **Bind Address**: 127.0.0.1:8000
- **Timeout**: 120 seconds
- **Preload**: Enabled for better performance
- **Logging**: Access and error logs in `logs/` directory

### Environment Variables

Key environment variables in `.env`:

```bash
# Database
DATABASE_URL=mysql+pymysql://vedfolnir_user:password@localhost/vedfolnir?charset=utf8mb4

# Redis
REDIS_URL=redis://localhost:6379/0

# Flask
FLASK_SECRET_KEY=<generated-key>

# RQ Workers
RQ_ENABLE_INTEGRATED_WORKERS=true
RQ_ENABLE_EXTERNAL_WORKERS=false
```

### Redis Queue Integration

The setup includes integrated RQ workers that run within Gunicorn processes:

- **Integrated Workers**: Run as daemon threads within Gunicorn
- **Worker Coordination**: Redis-based coordination prevents duplicate processing
- **Graceful Shutdown**: Workers complete current tasks before shutdown
- **Monitoring**: Built-in performance and health monitoring

## Nginx Configuration (Optional)

If you enabled Nginx during setup, it's configured as a reverse proxy:

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Validation

Validate your setup:

```bash
# Run comprehensive validation
./scripts/setup/validate_mac_setup.sh

# Quick service test
curl -I http://127.0.0.1:8000
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   tail -f logs/vedfolnir.err
   
   # Check service status
   launchctl list | grep vedfolnir
   ```

2. **Database connection errors**
   ```bash
   # Test MySQL connection
   mysql -u vedfolnir_user -p vedfolnir
   
   # Check database configuration
   python -c "from config import Config; print(Config().DATABASE_URL)"
   ```

3. **Redis connection errors**
   ```bash
   # Test Redis connection
   redis-cli ping
   
   # Check Redis service
   brew services list | grep redis
   ```

4. **Python environment issues**
   ```bash
   # Check virtual environment
   pyenv versions
   
   # Activate environment
   pyenv activate gunicorn-host
   
   # Check Python packages
   pip list
   ```

### Log Files

Monitor these log files for issues:

- `logs/vedfolnir.log` - Application stdout
- `logs/vedfolnir.err` - Application stderr  
- `logs/access.log` - Gunicorn access logs
- `logs/error.log` - Gunicorn error logs

### Performance Tuning

Adjust Gunicorn workers based on your Mac:

```bash
# For M1/M2 Macs (8+ cores)
--workers 4

# For Intel Macs (4+ cores)  
--workers 2

# For high-traffic sites
--workers $((2 * CPU_CORES + 1))
```

## Security Considerations

### Production Deployment

For production use:

1. **SSL/TLS**: Configure SSL certificates with Nginx
2. **Firewall**: Configure macOS firewall rules
3. **Updates**: Keep system and dependencies updated
4. **Monitoring**: Set up log monitoring and alerting
5. **Backups**: Configure automated database backups

### Environment Security

- Store sensitive configuration in `.env` file (not in version control)
- Use strong passwords for database and admin accounts
- Regularly update Python dependencies
- Monitor security logs

## Integration with Redis Queue Migration

This setup is designed to work with the Redis Queue migration:

- **Integrated Workers**: RQ workers run within Gunicorn processes
- **Coordination**: Redis-based worker coordination prevents conflicts
- **Monitoring**: Built-in RQ monitoring and metrics
- **Scalability**: Easy scaling of workers and queues

The setup automatically configures:
- RQ worker integration with Gunicorn
- Redis connection pooling
- Worker health monitoring
- Graceful shutdown handling

## Next Steps

After setup completion:

1. **Access Application**: Visit http://127.0.0.1:8000 (or http://localhost if Nginx enabled)
2. **Configure Platforms**: Add your ActivityPub platform connections
3. **Test Functionality**: Generate test captions to verify everything works
4. **Monitor Performance**: Check logs and system resources
5. **Production Hardening**: Implement SSL, monitoring, and backups as needed

## Support

For issues or questions:

1. Check the validation script output: `./scripts/setup/validate_mac_setup.sh`
2. Review log files in the `logs/` directory
3. Consult the troubleshooting section above
4. Check the Redis Queue migration documentation for RQ-specific issues