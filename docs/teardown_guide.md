# Vedfolnir Teardown Guide

Complete guide for uninstalling and removing Vedfolnir from your system.

## Quick Start

```bash
# Preview what will be removed (recommended first step)
./scripts/maintenance/teardown.sh --dry-run

# Complete removal with confirmation prompts
./scripts/maintenance/teardown.sh

# Complete removal without prompts
./scripts/maintenance/teardown.sh --yes
```

## What Gets Removed

The teardown script handles complete removal of:

### 1. Running Services
- Web application processes (`web_app.py`)
- Bot processes (`main.py`)
- Gunicorn servers
- Caption workers
- launchd services (macOS)
- Docker containers and volumes

### 2. Data Storage
- Redis session data
- Redis platform cache
- MySQL database and user
- Image files in `storage/images/`
- Temporary files in `storage/temp/`
- Backup files in `storage/backups/`

### 3. Application Files
- Log files
- Python cache (`__pycache__`)
- Test cache (`.pytest_cache`)
- Environment files (`.env`, `.env.development`, `.env.production`)
- Virtual environment (`venv/`)
- Node modules (`node_modules/`)
- SQLite database (if present)

## Usage Options

### Basic Usage

```bash
# Show help
./scripts/maintenance/teardown.sh --help

# Dry run (preview only)
./scripts/maintenance/teardown.sh --dry-run

# Interactive mode (default)
./scripts/maintenance/teardown.sh

# Non-interactive mode
./scripts/maintenance/teardown.sh --yes
```

### Selective Removal

```bash
# Keep MySQL database
./scripts/maintenance/teardown.sh --keep-database

# Keep Redis data
./scripts/maintenance/teardown.sh --keep-redis

# Keep application files (only remove services/data)
./scripts/maintenance/teardown.sh --keep-files

# Keep everything except services
./scripts/maintenance/teardown.sh --keep-database --keep-redis --keep-files
```

### Combined Options

```bash
# Preview selective removal
./scripts/maintenance/teardown.sh --dry-run --keep-database

# Non-interactive with database preservation
./scripts/maintenance/teardown.sh --yes --keep-database

# Remove only services and Redis, keep everything else
./scripts/maintenance/teardown.sh --keep-database --keep-files
```

## Step-by-Step Teardown

### 1. Preview Changes (Recommended)

Always start with a dry run to see what will be removed:

```bash
cd /path/to/vedfolnir
./scripts/maintenance/teardown.sh --dry-run
```

Review the output carefully to ensure you understand what will be removed.

### 2. Backup Important Data (Optional)

If you want to preserve any data before removal:

```bash
# Backup database
mysqldump -u vedfolnir_user -p vedfolnir > vedfolnir_backup.sql

# Backup images
tar -czf images_backup.tar.gz storage/images/

# Backup configuration
cp .env .env.backup
```

### 3. Run Teardown

Choose your teardown approach:

**Interactive (Recommended for first-time users):**
```bash
./scripts/maintenance/teardown.sh
```

**Non-Interactive (For automation):**
```bash
./scripts/maintenance/teardown.sh --yes
```

**Selective (Keep specific components):**
```bash
./scripts/maintenance/teardown.sh --keep-database --keep-redis
```

### 4. Verify Removal

Check that services are stopped:

```bash
# Check for running processes
ps aux | grep -E "web_app|main.py|gunicorn" | grep -v grep

# Check Docker containers
docker ps | grep vedfolnir

# Check launchd services (macOS)
launchctl list | grep vedfolnir
```

### 5. Remove Application Directory (Optional)

If you want to completely remove the application:

```bash
cd ..
rm -rf vedfolnir
```

## Manual Cleanup

If the script doesn't remove everything or you need manual cleanup:

### Stop Services Manually

```bash
# Stop Python processes
pkill -f "python.*web_app.py"
pkill -f "python.*main.py"
pkill -f gunicorn

# Stop Docker
docker-compose down -v

# Unload launchd service (macOS)
launchctl unload ~/Library/LaunchAgents/com.vedfolnir.gunicorn.plist
rm ~/Library/LaunchAgents/com.vedfolnir.gunicorn.plist
```

### Clear Redis Manually

```bash
# Connect to Redis
redis-cli

# Clear Vedfolnir keys
KEYS vedfolnir:*
KEYS user_platforms:*
KEYS platform:*
KEYS platform_stats:*

# Delete keys (replace * with actual keys)
DEL vedfolnir:session:*
```

### Remove MySQL Database Manually

```bash
# Connect to MySQL
mysql -u root -p

# Remove database and user
DROP DATABASE IF EXISTS vedfolnir;
DROP USER IF EXISTS 'vedfolnir_user'@'localhost';
FLUSH PRIVILEGES;
```

### Remove Files Manually

```bash
cd /path/to/vedfolnir

# Remove data
rm -rf storage/images/*
rm -rf storage/temp/*
rm -rf storage/backups/*
rm -rf logs/*

# Remove cache
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf .pytest_cache

# Remove environment
rm -f .env .env.development .env.production
rm -rf venv/
rm -rf node_modules/
```

## Troubleshooting

### Permission Denied

If you get permission errors:

```bash
# Make script executable
chmod +x scripts/maintenance/teardown.sh

# Run with sudo if needed (not recommended)
sudo ./scripts/maintenance/teardown.sh
```

### MySQL Password

The script automatically uses credentials from `.env` file:
- `DATABASE_URL` - Contains database user and password
- `DB_ROOT_PASSWORD` - Optional root password for user removal

If credentials are not in `.env`, the script will:
1. Try to drop database with user credentials
2. Prompt for root password in interactive mode
3. Skip database removal in non-interactive mode

```bash
# Add root password to .env (optional)
echo "DB_ROOT_PASSWORD=your_root_password" >> .env

# Or skip database removal
./scripts/maintenance/teardown.sh --keep-database

# Or remove manually later
mysql -u root -p -e "DROP DATABASE vedfolnir; DROP USER 'vedfolnir_user'@'%';"
```

### Redis Connection Failed

The script uses Redis credentials from `.env`:
- `REDIS_HOST` - Redis server hostname
- `REDIS_PORT` - Redis server port
- `REDIS_PASSWORD` - Redis authentication password
- `REDIS_DB` - Redis database number

If Redis cleanup fails:

```bash
# Check Redis is running
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping

# Check connection details in .env
cat .env | grep REDIS

# Clear manually with credentials from .env
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD -n $REDIS_DB --scan --pattern "vedfolnir:*" | xargs redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD -n $REDIS_DB DEL
```

### Processes Won't Stop

If processes continue running:

```bash
# Force kill
pkill -9 -f "python.*web_app.py"
pkill -9 -f "python.*main.py"
pkill -9 -f gunicorn

# Check again
ps aux | grep -E "web_app|main.py|gunicorn" | grep -v grep
```

## Reinstallation

After teardown, to reinstall Vedfolnir:

```bash
# Pull latest code
git pull

# Run setup
python scripts/setup/generate_env_secrets.py
python scripts/setup/verify_env_setup.py

# Start application
python web_app.py
```

## Safety Features

The teardown script includes several safety features:

1. **Dry Run Mode**: Preview changes before making them
2. **Interactive Confirmations**: Prompts before destructive operations
3. **Selective Removal**: Keep specific components
4. **Error Handling**: Continues even if some steps fail
5. **Clear Output**: Color-coded status messages

## Exit Codes

- `0`: Success
- `1`: User cancelled or error occurred

## Support

If you encounter issues:

1. Run with `--dry-run` to diagnose
2. Check the troubleshooting section above
3. Review logs in `logs/` directory
4. Check GitHub issues for similar problems

## Related Scripts

- `scripts/maintenance/reset_app.py` - Reset application data only
- `scripts/maintenance/data_cleanup.py` - Clean up old data
- `scripts/setup/generate_env_secrets.py` - Generate new configuration
