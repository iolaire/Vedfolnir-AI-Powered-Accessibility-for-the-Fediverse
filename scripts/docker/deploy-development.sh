#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Development Environment Deployment Script for Vedfolnir Docker Compose

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
ENV_FILE=".env.development"

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

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to setup environment
setup_environment() {
    log_info "Setting up development environment..."
    
    cd "$PROJECT_ROOT"
    
    # Copy environment file if it doesn't exist
    if [[ ! -f .env ]]; then
        if [[ -f "$ENV_FILE" ]]; then
            cp "$ENV_FILE" .env
            log_success "Copied $ENV_FILE to .env"
        else
            log_error "Environment file $ENV_FILE not found"
            exit 1
        fi
    fi
    
    # Create secrets directory and files if they don't exist
    mkdir -p secrets
    
    if [[ ! -f secrets/flask_secret_key.txt ]]; then
        openssl rand -hex 32 > secrets/flask_secret_key.txt
        log_success "Generated Flask secret key"
    fi
    
    if [[ ! -f secrets/platform_encryption_key.txt ]]; then
        python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/platform_encryption_key.txt
        log_success "Generated platform encryption key"
    fi
    
    if [[ ! -f secrets/mysql_root_password.txt ]]; then
        openssl rand -base64 32 > secrets/mysql_root_password.txt
        log_success "Generated MySQL root password"
    fi
    
    if [[ ! -f secrets/mysql_password.txt ]]; then
        openssl rand -base64 32 > secrets/mysql_password.txt
        log_success "Generated MySQL user password"
    fi
    
    if [[ ! -f secrets/redis_password.txt ]]; then
        echo "" > secrets/redis_password.txt  # No password for development
        log_success "Created empty Redis password file (development)"
    fi
    
    if [[ ! -f secrets/vault_token.txt ]]; then
        openssl rand -hex 32 > secrets/vault_token.txt
        log_success "Generated Vault token"
    fi
    
    if [[ ! -f secrets/grafana_admin_password.txt ]]; then
        openssl rand -base64 16 > secrets/grafana_admin_password.txt
        log_success "Generated Grafana admin password"
    fi
    
    # Create necessary directories
    mkdir -p {data/{mysql,redis,prometheus,grafana,loki,vault},logs/{app,nginx,mysql,redis,vault},storage/{images,backups,temp},config}
    
    log_success "Environment setup completed"
}

# Function to build images
build_images() {
    log_info "Building Docker images..."
    
    docker-compose $COMPOSE_FILES build --parallel
    
    log_success "Docker images built successfully"
}

# Function to start services
start_services() {
    log_info "Starting development services..."
    
    # Start core services first
    docker-compose $COMPOSE_FILES up -d mysql redis
    
    # Wait for database to be ready
    log_info "Waiting for MySQL to be ready..."
    timeout 60 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec mysql mysqladmin ping -h localhost --silent; do sleep 2; done'
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    timeout 30 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec redis redis-cli ping | grep -q PONG; do sleep 2; done'
    
    # Start application and other services
    docker-compose $COMPOSE_FILES up -d
    
    # Wait for application to be ready
    log_info "Waiting for application to be ready..."
    timeout 120 bash -c 'until curl -f http://localhost:5000/health &>/dev/null; do sleep 5; done'
    
    log_success "All services started successfully"
}

# Function to show service status
show_status() {
    log_info "Service status:"
    docker-compose $COMPOSE_FILES ps
    
    echo ""
    log_info "Service URLs:"
    echo "  Application: http://localhost:5000"
    echo "  phpMyAdmin: http://localhost:8080"
    echo "  Redis Commander: http://localhost:8081"
    echo "  MailHog: http://localhost:8025"
    echo "  Grafana: http://localhost:3000 (if enabled)"
    
    echo ""
    log_info "Useful commands:"
    echo "  View logs: docker-compose $COMPOSE_FILES logs -f [service]"
    echo "  Stop services: docker-compose $COMPOSE_FILES down"
    echo "  Restart service: docker-compose $COMPOSE_FILES restart [service]"
    echo "  Shell access: docker-compose $COMPOSE_FILES exec [service] bash"
}

# Function to run tests
run_tests() {
    log_info "Running development tests..."
    
    # Run unit tests
    docker-compose $COMPOSE_FILES run --rm test-runner python -m pytest tests/unit/ -v
    
    # Run integration tests
    docker-compose $COMPOSE_FILES run --rm test-runner python -m pytest tests/integration/ -v
    
    log_success "Tests completed"
}

# Function to show help
show_help() {
    echo "Development Environment Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --build-only    Build images only, don't start services"
    echo "  --no-build      Skip building images"
    echo "  --test          Run tests after deployment"
    echo "  --status        Show service status and URLs"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Full deployment"
    echo "  $0 --build-only       # Build images only"
    echo "  $0 --no-build --test  # Start services and run tests"
}

# Main execution
main() {
    local build_only=false
    local no_build=false
    local run_tests_flag=false
    local status_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                build_only=true
                shift
                ;;
            --no-build)
                no_build=true
                shift
                ;;
            --test)
                run_tests_flag=true
                shift
                ;;
            --status)
                status_only=true
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
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    if [[ "$status_only" == true ]]; then
        show_status
        exit 0
    fi
    
    # Execute deployment steps
    check_prerequisites
    setup_environment
    
    if [[ "$no_build" != true ]]; then
        build_images
    fi
    
    if [[ "$build_only" != true ]]; then
        start_services
        show_status
        
        if [[ "$run_tests_flag" == true ]]; then
            run_tests
        fi
    fi
    
    log_success "Development environment deployment completed!"
}

# Run main function with all arguments
main "$@"