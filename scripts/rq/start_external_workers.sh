#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
# Start External RQ Workers
#
# Script to start RQ workers as separate processes using the `rq worker` command.
# This is useful for production deployments with heavy workloads.
#

set -e

# Configuration
REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
WORKER_COUNT=${RQ_EXTERNAL_WORKER_COUNT:-3}
WORKER_TIMEOUT=${RQ_EXTERNAL_WORKER_TIMEOUT:-7200}
LOG_LEVEL=${RQ_LOG_LEVEL:-INFO}
PID_DIR=${RQ_PID_DIR:-"/tmp/rq_workers"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if RQ is installed
check_rq_installation() {
    if ! command -v rq &> /dev/null; then
        log_error "RQ command not found. Please install RQ: pip install rq"
        exit 1
    fi
    log_info "RQ installation found"
}

# Check Redis connectivity
check_redis_connection() {
    log_info "Checking Redis connection..."
    
    if command -v redis-cli &> /dev/null; then
        if redis-cli -u "$REDIS_URL" ping > /dev/null 2>&1; then
            log_info "Redis connection successful"
        else
            log_error "Cannot connect to Redis at $REDIS_URL"
            exit 1
        fi
    else
        log_warn "redis-cli not found, skipping Redis connectivity check"
    fi
}

# Create PID directory
create_pid_directory() {
    if [ ! -d "$PID_DIR" ]; then
        mkdir -p "$PID_DIR"
        log_info "Created PID directory: $PID_DIR"
    fi
}

# Start a single worker
start_worker() {
    local worker_name=$1
    local queues=$2
    local pid_file="$PID_DIR/${worker_name}.pid"
    local log_file="$PID_DIR/${worker_name}.log"
    
    log_info "Starting worker: $worker_name for queues: $queues"
    
    # Check if worker is already running
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        log_warn "Worker $worker_name is already running (PID: $(cat "$pid_file"))"
        return 0
    fi
    
    # Start the worker
    nohup rq worker \
        --url "$REDIS_URL" \
        --name "$worker_name" \
        --job-timeout "$WORKER_TIMEOUT" \
        --verbose \
        $queues \
        > "$log_file" 2>&1 &
    
    local worker_pid=$!
    echo $worker_pid > "$pid_file"
    
    # Wait a moment and check if worker started successfully
    sleep 2
    if kill -0 $worker_pid 2>/dev/null; then
        log_info "Worker $worker_name started successfully (PID: $worker_pid)"
        return 0
    else
        log_error "Worker $worker_name failed to start"
        rm -f "$pid_file"
        return 1
    fi
}

# Start all workers
start_all_workers() {
    log_info "Starting $WORKER_COUNT external RQ workers..."
    
    local success_count=0
    
    # Start urgent/high priority workers
    for i in $(seq 1 2); do
        if start_worker "external-urgent-high-$i" "urgent high"; then
            ((success_count++))
        fi
    done
    
    # Start normal priority workers
    for i in $(seq 1 $((WORKER_COUNT - 2))); do
        if start_worker "external-normal-$i" "normal"; then
            ((success_count++))
        fi
    done
    
    # Start low priority workers
    for i in $(seq 1 2); do
        if start_worker "external-low-$i" "low"; then
            ((success_count++))
        fi
    done
    
    log_info "Started $success_count workers successfully"
    
    if [ $success_count -eq 0 ]; then
        log_error "No workers started successfully"
        exit 1
    fi
}

# Stop a single worker
stop_worker() {
    local worker_name=$1
    local pid_file="$PID_DIR/${worker_name}.pid"
    
    if [ ! -f "$pid_file" ]; then
        log_warn "PID file not found for worker: $worker_name"
        return 0
    fi
    
    local worker_pid=$(cat "$pid_file")
    
    if kill -0 $worker_pid 2>/dev/null; then
        log_info "Stopping worker: $worker_name (PID: $worker_pid)"
        
        # Send SIGTERM for graceful shutdown
        kill -TERM $worker_pid
        
        # Wait for graceful shutdown
        local timeout=30
        while [ $timeout -gt 0 ] && kill -0 $worker_pid 2>/dev/null; do
            sleep 1
            ((timeout--))
        done
        
        # Force kill if still running
        if kill -0 $worker_pid 2>/dev/null; then
            log_warn "Worker $worker_name did not stop gracefully, force killing"
            kill -KILL $worker_pid
        fi
        
        rm -f "$pid_file"
        log_info "Worker $worker_name stopped"
    else
        log_warn "Worker $worker_name is not running"
        rm -f "$pid_file"
    fi
}

# Stop all workers
stop_all_workers() {
    log_info "Stopping all external RQ workers..."
    
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            local worker_name=$(basename "$pid_file" .pid)
            stop_worker "$worker_name"
        fi
    done
    
    log_info "All workers stopped"
}

# Show worker status
show_status() {
    log_info "External RQ Worker Status:"
    echo
    
    local running_count=0
    
    for pid_file in "$PID_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            local worker_name=$(basename "$pid_file" .pid)
            local worker_pid=$(cat "$pid_file")
            
            if kill -0 $worker_pid 2>/dev/null; then
                echo "  ✓ $worker_name (PID: $worker_pid) - RUNNING"
                ((running_count++))
            else
                echo "  ✗ $worker_name - STOPPED"
                rm -f "$pid_file"
            fi
        fi
    done
    
    if [ $running_count -eq 0 ]; then
        echo "  No workers running"
    else
        echo
        log_info "$running_count workers running"
    fi
}

# Restart all workers
restart_workers() {
    log_info "Restarting all external RQ workers..."
    stop_all_workers
    sleep 2
    start_all_workers
}

# Show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|status}"
    echo
    echo "Commands:"
    echo "  start    - Start external RQ workers"
    echo "  stop     - Stop all external RQ workers"
    echo "  restart  - Restart all external RQ workers"
    echo "  status   - Show worker status"
    echo
    echo "Environment Variables:"
    echo "  REDIS_URL                    - Redis connection URL (default: redis://localhost:6379/0)"
    echo "  RQ_EXTERNAL_WORKER_COUNT     - Number of workers to start (default: 3)"
    echo "  RQ_EXTERNAL_WORKER_TIMEOUT   - Worker job timeout in seconds (default: 7200)"
    echo "  RQ_LOG_LEVEL                 - Log level (default: INFO)"
    echo "  RQ_PID_DIR                   - Directory for PID files (default: /tmp/rq_workers)"
}

# Main script logic
main() {
    local command=${1:-""}
    
    case "$command" in
        start)
            check_rq_installation
            check_redis_connection
            create_pid_directory
            start_all_workers
            ;;
        stop)
            stop_all_workers
            ;;
        restart)
            check_rq_installation
            check_redis_connection
            create_pid_directory
            restart_workers
            ;;
        status)
            show_status
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"