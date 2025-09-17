#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# RQ Worker Deployment Shell Script
# Provides easy deployment of RQ workers in different modes

set -e

# Default configuration
DEFAULT_MODE="integrated"
DEFAULT_WORKERS=4
DEFAULT_BIND="0.0.0.0:8000"
DEFAULT_TIMEOUT=120

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
RQ Worker Deployment Script

Usage: $0 [ACTION] [OPTIONS]

Actions:
    start       Start RQ workers
    stop        Stop RQ workers
    restart     Restart RQ workers
    status      Show worker status
    logs        Show worker logs

Options:
    --mode MODE         Deployment mode: integrated, external, hybrid (default: $DEFAULT_MODE)
    --workers N         Number of Gunicorn workers (default: $DEFAULT_WORKERS)
    --bind ADDR         Bind address (default: $DEFAULT_BIND)
    --timeout SEC       Worker timeout (default: $DEFAULT_TIMEOUT)
    --config-check      Check configuration before deployment
    --daemon            Run in daemon mode
    --help              Show this help

Environment Variables:
    WORKER_MODE                     Worker deployment mode
    GUNICORN_WORKERS               Number of Gunicorn workers
    GUNICORN_BIND                  Bind address
    GUNICORN_TIMEOUT               Worker timeout
    RQ_ENABLE_INTEGRATED_WORKERS   Enable integrated workers (true/false)
    RQ_ENABLE_EXTERNAL_WORKERS     Enable external workers (true/false)
    RQ_STARTUP_DELAY               Startup delay in seconds
    REDIS_URL                      Redis connection URL

Examples:
    $0 start --mode integrated
    $0 start --mode external --workers 6
    $0 start --mode hybrid --daemon
    $0 stop
    $0 restart --mode integrated
    $0 status

EOF
}

# Parse command line arguments
ACTION=""
MODE="$DEFAULT_MODE"
WORKERS="$DEFAULT_WORKERS"
BIND="$DEFAULT_BIND"
TIMEOUT="$DEFAULT_TIMEOUT"
CONFIG_CHECK=false
DAEMON=false

while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|status|logs)
            ACTION="$1"
            shift
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --bind)
            BIND="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --config-check)
            CONFIG_CHECK=true
            shift
            ;;
        --daemon)
            DAEMON=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate action
if [[ -z "$ACTION" ]]; then
    log_error "No action specified"
    show_help
    exit 1
fi

# Validate mode
if [[ "$MODE" != "integrated" && "$MODE" != "external" && "$MODE" != "hybrid" ]]; then
    log_error "Invalid mode: $MODE. Must be integrated, external, or hybrid"
    exit 1
fi

# Set environment variables
export WORKER_MODE="$MODE"
export GUNICORN_WORKERS="$WORKERS"
export GUNICORN_BIND="$BIND"
export GUNICORN_TIMEOUT="$TIMEOUT"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    log_warning "No virtual environment detected. Make sure you have activated your Python environment."
fi

# Check if required files exist
if [[ ! -f "web_app.py" ]]; then
    log_error "web_app.py not found. Make sure you're in the project root directory."
    exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
    log_error "requirements.txt not found. Make sure you're in the project root directory."
    exit 1
fi

# Function to check if Redis is available
check_redis() {
    log_info "Checking Redis connection..."
    
    python3 -c "
import redis
import os
import sys

try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    r = redis.from_url(redis_url)
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
" || {
        log_error "Redis connection failed. Make sure Redis is running and accessible."
        exit 1
    }
}

# Function to check configuration
check_config() {
    log_info "Checking RQ configuration..."
    
    python3 -c "
import sys
import os
sys.path.insert(0, '.')

try:
    from app.services.task.rq.rq_config import RQConfig
    config = RQConfig()
    if config.validate_config():
        print('✅ Configuration validation passed')
    else:
        print('❌ Configuration validation failed')
        sys.exit(1)
except Exception as e:
    print(f'❌ Configuration check failed: {e}')
    sys.exit(1)
" || {
        log_error "Configuration validation failed"
        exit 1
    }
}

# Function to start workers
start_workers() {
    log_info "Starting RQ workers in $MODE mode..."
    
    # Check prerequisites
    check_redis
    
    if [[ "$CONFIG_CHECK" == true ]] || [[ "$ACTION" == "start" ]]; then
        check_config
    fi
    
    # Set mode-specific environment variables
    case "$MODE" in
        integrated)
            export RQ_ENABLE_INTEGRATED_WORKERS=true
            export RQ_ENABLE_EXTERNAL_WORKERS=false
            ;;
        external)
            export RQ_ENABLE_INTEGRATED_WORKERS=false
            export RQ_ENABLE_EXTERNAL_WORKERS=true
            ;;
        hybrid)
            export RQ_ENABLE_INTEGRATED_WORKERS=true
            export RQ_ENABLE_EXTERNAL_WORKERS=true
            ;;
    esac
    
    # Start deployment
    if [[ "$DAEMON" == true ]]; then
        log_info "Starting in daemon mode..."
        nohup python3 "$SCRIPT_DIR/deploy_rq_workers.py" start --mode "$MODE" > rq_workers.log 2>&1 &
        echo $! > rq_workers.pid
        log_success "RQ workers started in daemon mode (PID: $(cat rq_workers.pid))"
        log_info "Logs: tail -f rq_workers.log"
    else
        python3 "$SCRIPT_DIR/deploy_rq_workers.py" start --mode "$MODE"
    fi
}

# Function to stop workers
stop_workers() {
    log_info "Stopping RQ workers..."
    
    # Stop via deployment script
    python3 "$SCRIPT_DIR/deploy_rq_workers.py" stop
    
    # Clean up daemon PID file if it exists
    if [[ -f "rq_workers.pid" ]]; then
        PID=$(cat rq_workers.pid)
        if kill -0 "$PID" 2>/dev/null; then
            log_info "Stopping daemon process (PID: $PID)..."
            kill "$PID"
        fi
        rm -f rq_workers.pid
    fi
    
    log_success "RQ workers stopped"
}

# Function to restart workers
restart_workers() {
    log_info "Restarting RQ workers in $MODE mode..."
    
    stop_workers
    sleep 2
    start_workers
}

# Function to show status
show_status() {
    log_info "Checking RQ worker status..."
    
    python3 "$SCRIPT_DIR/deploy_rq_workers.py" status
    
    # Check daemon status if PID file exists
    if [[ -f "rq_workers.pid" ]]; then
        PID=$(cat rq_workers.pid)
        if kill -0 "$PID" 2>/dev/null; then
            log_info "Daemon process running (PID: $PID)"
        else
            log_warning "Daemon PID file exists but process not running"
        fi
    fi
}

# Function to show logs
show_logs() {
    log_info "Showing RQ worker logs..."
    
    if [[ -f "rq_workers.log" ]]; then
        tail -f rq_workers.log
    else
        log_warning "No log file found (rq_workers.log)"
        log_info "If workers are running in foreground mode, logs will be in the terminal"
    fi
}

# Execute action
case "$ACTION" in
    start)
        start_workers
        ;;
    stop)
        stop_workers
        ;;
    restart)
        restart_workers
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        log_error "Unknown action: $ACTION"
        show_help
        exit 1
        ;;
esac