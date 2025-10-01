#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Development application initialization script for Docker containers
# Includes hot reloading, debugging support, and development tools

set -e

# Configuration
APP_DIR="/app"
LOG_DIR="/app/logs"
STORAGE_DIR="/app/storage"
CONFIG_DIR="/app/config"

# Development environment settings
CONTAINER_ENV=${CONTAINER_ENV:-true}
FLASK_ENV=${FLASK_ENV:-development}
FLASK_DEBUG=${FLASK_DEBUG:-1}
RQ_ENABLE_INTEGRATED_WORKERS=${RQ_ENABLE_INTEGRATED_WORKERS:-false}  # Disabled in dev by default

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
    log_info "Creating development directories..."
    
    mkdir -p "$LOG_DIR"/{app,gunicorn,rq,audit,debug}
    mkdir -p "$STORAGE_DIR"/{images,backups,temp,debug}
    mkdir -p "$CONFIG_DIR"
    mkdir -p /app/test-results
    
    # Set proper permissions
    chown -R vedfolnir:vedfolnir "$LOG_DIR" "$STORAGE_DIR" "$CONFIG_DIR" /app/test-results 2>/dev/null || true
    
    log_info "Development directories created successfully"
}

# Wait for dependencies (simplified for development)
wait_for_dependencies() {
    log_info "Waiting for development dependencies..."
    
    # Wait for MySQL (required)
    if [ -n "$DATABASE_URL" ]; then
        log_info "Waiting for MySQL database..."
        
        MYSQL_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        MYSQL_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -n "$MYSQL_HOST" ] && [ -n "$MYSQL_PORT" ]; then
            timeout=30
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
    
    # Redis is optional in development
    if [ -n "$REDIS_URL" ]; then
        log_info "Checking Redis availability..."
        
        REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        if [ -z "$REDIS_HOST" ]; then
            REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/redis:\/\/\([^:]*\):.*/\1/p')
        fi
        REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
            if nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; then
                log_info "Redis is available"
            else
                log_warn "Redis is not available - continuing in development mode"
            fi
        fi
    fi
}

# Initialize database for development
initialize_database() {
    log_info "Initializing development database..."
    
    cd "$APP_DIR"
    
    # Test database connection
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
    
    log_info "Development database initialized successfully"
}

# Configure development environment
configure_development() {
    log_info "Configuring development environment..."
    
    # Development-specific environment variables
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONUNBUFFERED=1
    
    # Disable RQ workers by default in development
    export RQ_ENABLE_INTEGRATED_WORKERS=${RQ_ENABLE_INTEGRATED_WORKERS:-false}
    export RQ_ENABLE_EXTERNAL_WORKERS=false
    
    # Development logging
    export ENABLE_JSON_LOGGING=false  # Use regular logging in development
    export LOG_LEVEL=DEBUG
    
    # Development monitoring
    export PERFORMANCE_MONITORING_ENABLED=true
    export METRICS_COLLECTION_ENABLED=false  # Disable metrics collection in dev
    
    # Hot reloading
    export FLASK_RELOAD=true
    
    log_info "Development environment configured"
}

# Setup debugging
setup_debugging() {
    log_info "Setting up debugging support..."
    
    # Configure debugpy for remote debugging
    export DEBUGPY_ENABLED=${DEBUGPY_ENABLED:-true}
    export DEBUGPY_PORT=${DEBUGPY_PORT:-5678}
    export DEBUGPY_WAIT_FOR_CLIENT=${DEBUGPY_WAIT_FOR_CLIENT:-false}
    
    # Configure development tools
    export TESTING_ENABLED=true
    export COVERAGE_ENABLED=true
    
    log_info "Debugging support configured"
}

# Install development dependencies
install_dev_dependencies() {
    log_info "Checking development dependencies..."
    
    # Check if development packages are installed
    python -c "
import sys
try:
    import debugpy
    import pytest
    import black
    print('Development dependencies are available')
except ImportError as e:
    print(f'Missing development dependency: {e}')
    sys.exit(1)
" || {
        log_warn "Some development dependencies are missing"
        log_info "Installing development dependencies..."
        pip install debugpy pytest pytest-cov black flake8 mypy
    }
}

# Validate development configuration
validate_dev_configuration() {
    log_info "Validating development configuration..."
    
    # Check required environment variables (relaxed for development)
    if [ -z "$DATABASE_URL" ]; then
        log_error "DATABASE_URL is required even in development"
        exit 1
    fi
    
    if [ -z "$FLASK_SECRET_KEY" ]; then
        log_warn "FLASK_SECRET_KEY not set, using development default"
        export FLASK_SECRET_KEY="dev-secret-key-change-in-production"
    fi
    
    # Check file permissions
    if [ ! -w "$LOG_DIR" ]; then
        log_error "Log directory is not writable: $LOG_DIR"
        exit 1
    fi
    
    log_info "Development configuration validation successful"
}

# Development pre-flight checks
dev_preflight_checks() {
    log_info "Running development pre-flight checks..."
    
    # Check Python version
    python_version=$(python --version 2>&1 | cut -d' ' -f2)
    log_info "Python version: $python_version"
    
    # Check development tools
    if command -v black >/dev/null 2>&1; then
        log_info "Code formatter (black) available"
    else
        log_warn "Code formatter (black) not available"
    fi
    
    if command -v pytest >/dev/null 2>&1; then
        log_info "Test runner (pytest) available"
    else
        log_warn "Test runner (pytest) not available"
    fi
    
    # Check available memory (less strict in development)
    if [ -f /proc/meminfo ]; then
        available_memory=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
        available_memory_mb=$((available_memory / 1024))
        log_info "Available memory: ${available_memory_mb}MB"
    fi
    
    log_info "Development pre-flight checks completed"
}

# Start development server
start_dev_server() {
    log_info "Starting development server..."
    
    cd "$APP_DIR"
    
    # Choose startup method based on configuration
    if [ "$DEBUGPY_ENABLED" = "true" ]; then
        log_info "Starting with debugpy support on port $DEBUGPY_PORT"
        
        if [ "$DEBUGPY_WAIT_FOR_CLIENT" = "true" ]; then
            log_info "Waiting for debugger client to connect..."
            exec python -m debugpy --listen "0.0.0.0:$DEBUGPY_PORT" --wait-for-client web_app.py
        else
            exec python -m debugpy --listen "0.0.0.0:$DEBUGPY_PORT" web_app.py
        fi
    else
        log_info "Starting Flask development server"
        exec python web_app.py
    fi
}

# Main development initialization function
main() {
    log_info "Starting Vedfolnir development environment initialization..."
    log_info "Environment: $FLASK_ENV, Debug: $FLASK_DEBUG"
    
    # Run initialization steps
    create_directories
    validate_dev_configuration
    install_dev_dependencies
    dev_preflight_checks
    wait_for_dependencies
    initialize_database
    configure_development
    setup_debugging
    
    log_info "Development environment initialization completed successfully"
    
    # Start the development server
    start_dev_server
}

# Handle signals for graceful shutdown
trap 'log_info "Received shutdown signal, cleaning up..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"