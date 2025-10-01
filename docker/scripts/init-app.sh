#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Production application initialization script for Docker containers
# Handles database migrations, RQ worker setup, and application startup

set -e

# Configuration
APP_DIR="/app"
LOG_DIR="/app/logs"
STORAGE_DIR="/app/storage"
CONFIG_DIR="/app/config"

# Environment detection
CONTAINER_ENV=${CONTAINER_ENV:-true}
FLASK_ENV=${FLASK_ENV:-production}
RQ_ENABLE_INTEGRATED_WORKERS=${RQ_ENABLE_INTEGRATED_WORKERS:-true}

# Logging functions
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1"
}

# Create necessary directories
create_directories() {
    log_info "Creating application directories..."
    
    mkdir -p "$LOG_DIR"/{app,gunicorn,rq,audit}
    mkdir -p "$STORAGE_DIR"/{images,backups,temp}
    mkdir -p "$CONFIG_DIR"
    
    # Set proper permissions
    chown -R vedfolnir:vedfolnir "$LOG_DIR" "$STORAGE_DIR" "$CONFIG_DIR" 2>/dev/null || true
    
    log_info "Directories created successfully"
}

# Wait for dependencies
wait_for_dependencies() {
    log_info "Waiting for dependencies..."
    
    # Wait for MySQL
    if [ -n "$DATABASE_URL" ]; then
        log_info "Waiting for MySQL database..."
        
        # Extract MySQL connection details from DATABASE_URL
        # Format: mysql+pymysql://user:password@host:port/database
        MYSQL_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        MYSQL_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -n "$MYSQL_HOST" ] && [ -n "$MYSQL_PORT" ]; then
            timeout=60
            while [ $timeout -gt 0 ]; do
                if nc -z "$MYSQL_HOST" "$MYSQL_PORT" 2>/dev/null; then
                    log_info "MySQL is ready"
                    break
                fi
                log_info "Waiting for MySQL... ($timeout seconds remaining)"
                sleep 2
                timeout=$((timeout - 2))
            done
            
            if [ $timeout -le 0 ]; then
                log_error "MySQL connection timeout"
                exit 1
            fi
        fi
    fi
    
    # Wait for Redis
    if [ -n "$REDIS_URL" ]; then
        log_info "Waiting for Redis..."
        
        # Extract Redis connection details
        REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        if [ -z "$REDIS_HOST" ]; then
            REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/redis:\/\/\([^:]*\):.*/\1/p')
        fi
        REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
            timeout=30
            while [ $timeout -gt 0 ]; do
                if nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; then
                    log_info "Redis is ready"
                    break
                fi
                log_info "Waiting for Redis... ($timeout seconds remaining)"
                sleep 2
                timeout=$((timeout - 2))
            done
            
            if [ $timeout -le 0 ]; then
                log_warn "Redis connection timeout - continuing without Redis"
            fi
        fi
    fi
    
    # Wait for Vault (if configured)
    if [ -n "$VAULT_ADDR" ]; then
        log_info "Waiting for Vault..."
        timeout=30
        while [ $timeout -gt 0 ]; do
            if curl -s "$VAULT_ADDR/v1/sys/health" >/dev/null 2>&1; then
                log_info "Vault is ready"
                break
            fi
            log_info "Waiting for Vault... ($timeout seconds remaining)"
            sleep 2
            timeout=$((timeout - 2))
        done
        
        if [ $timeout -le 0 ]; then
            log_warn "Vault connection timeout - continuing without Vault"
        fi
    fi
}

# Initialize database
initialize_database() {
    log_info "Initializing database..."
    
    cd "$APP_DIR"
    
    # Run database migrations if needed
    if [ -f "scripts/setup/verify_env_setup.py" ]; then
        log_info "Running database setup verification..."
        python scripts/setup/verify_env_setup.py || {
            log_error "Database setup verification failed"
            exit 1
        }
    fi
    
    # Check if database needs initialization
    python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
try:
    config = Config()
    db_manager = DatabaseManager(config)
    with db_manager.get_session() as session:
        session.execute('SELECT 1')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" || {
        log_error "Database connection test failed"
        exit 1
    }
    
    log_info "Database initialized successfully"
}

# Configure RQ workers
configure_rq_workers() {
    if [ "$RQ_ENABLE_INTEGRATED_WORKERS" = "true" ]; then
        log_info "Configuring integrated RQ workers..."
        
        # Set RQ environment variables
        export RQ_ENABLE_INTEGRATED_WORKERS=true
        export RQ_ENABLE_EXTERNAL_WORKERS=false
        export RQ_STARTUP_DELAY=${RQ_STARTUP_DELAY:-10}
        export RQ_SHUTDOWN_TIMEOUT=${RQ_SHUTDOWN_TIMEOUT:-30}
        
        log_info "RQ workers configured for integrated mode"
    else
        log_info "RQ workers disabled"
        export RQ_ENABLE_INTEGRATED_WORKERS=false
    fi
}

# Setup monitoring and health checks
setup_monitoring() {
    log_info "Setting up monitoring and health checks..."
    
    # Configure structured logging for containers
    export ENABLE_JSON_LOGGING=${ENABLE_JSON_LOGGING:-true}
    export LOG_LEVEL=${LOG_LEVEL:-INFO}
    
    # Configure health check endpoint
    export HEALTH_CHECK_ENABLED=true
    export HEALTH_CHECK_ENDPOINT=/health
    
    # Configure performance monitoring
    export PERFORMANCE_MONITORING_ENABLED=true
    export METRICS_COLLECTION_ENABLED=true
    
    log_info "Monitoring configured successfully"
}

# Validate configuration
validate_configuration() {
    log_info "Validating configuration..."
    
    # Check required environment variables
    required_vars=("DATABASE_URL" "FLASK_SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate database URL format
    if [[ ! "$DATABASE_URL" =~ ^mysql\+pymysql:// ]]; then
        log_error "DATABASE_URL must use mysql+pymysql driver"
        exit 1
    fi
    
    # Check file permissions
    if [ ! -w "$LOG_DIR" ]; then
        log_error "Log directory is not writable: $LOG_DIR"
        exit 1
    fi
    
    if [ ! -w "$STORAGE_DIR" ]; then
        log_error "Storage directory is not writable: $STORAGE_DIR"
        exit 1
    fi
    
    log_info "Configuration validation successful"
}

# Setup resource limits
setup_resource_limits() {
    log_info "Configuring resource limits..."
    
    # Memory limits
    MEMORY_LIMIT=${MEMORY_LIMIT:-2g}
    CPU_LIMIT=${CPU_LIMIT:-2}
    
    # Configure Gunicorn workers based on resources
    if [ -n "$MEMORY_LIMIT" ]; then
        if [[ "$MEMORY_LIMIT" =~ ^([0-9]+)g$ ]]; then
            memory_gb=${BASH_REMATCH[1]}
            if [ "$memory_gb" -lt 2 ]; then
                export GUNICORN_WORKERS=2
            elif [ "$memory_gb" -lt 4 ]; then
                export GUNICORN_WORKERS=3
            else
                export GUNICORN_WORKERS=4
            fi
        fi
    fi
    
    log_info "Resource limits configured - Memory: $MEMORY_LIMIT, CPU: $CPU_LIMIT, Workers: ${GUNICORN_WORKERS:-auto}"
}

# Pre-flight checks
preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check Python version
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    log_info "Python version: $python_version"
    
    # Check available memory
    if [ -f /proc/meminfo ]; then
        available_memory=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        available_memory_mb=$((available_memory / 1024))
        log_info "Available memory: ${available_memory_mb}MB"
        
        if [ "$available_memory_mb" -lt 512 ]; then
            log_warn "Low memory available: ${available_memory_mb}MB"
        fi
    fi
    
    # Check disk space
    disk_usage=$(df "$APP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
    log_info "Disk usage: ${disk_usage}%"
    
    if [ "$disk_usage" -gt 90 ]; then
        log_warn "High disk usage: ${disk_usage}%"
    fi
    
    log_info "Pre-flight checks completed"
}

# Main initialization function
main() {
    log_info "Starting Vedfolnir application initialization..."
    log_info "Environment: $FLASK_ENV, Container: $CONTAINER_ENV"
    
    # Run initialization steps
    create_directories
    validate_configuration
    setup_resource_limits
    preflight_checks
    wait_for_dependencies
    initialize_database
    configure_rq_workers
    setup_monitoring
    
    log_info "Application initialization completed successfully"
    log_info "Starting Gunicorn with integrated RQ workers..."
    
    # Start the application
    exec gunicorn --config gunicorn.conf.py web_app:app
}

# Handle signals for graceful shutdown
trap 'log_info "Received shutdown signal, cleaning up..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"