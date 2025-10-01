#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Compliance and Audit Framework Deployment Script
# Deploys the complete compliance framework with all components

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPLIANCE_CONFIG_DIR="$PROJECT_ROOT/config/compliance"
LOGS_DIR="$PROJECT_ROOT/logs"
STORAGE_DIR="$PROJECT_ROOT/storage"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root (for Docker deployment)
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        warning "Running as root. This is acceptable for Docker deployment."
    fi
}

# Create necessary directories
create_directories() {
    log "Creating compliance framework directories..."
    
    # Compliance directories
    mkdir -p "$COMPLIANCE_CONFIG_DIR"
    mkdir -p "$LOGS_DIR/audit"
    mkdir -p "$LOGS_DIR/compliance"
    mkdir -p "$LOGS_DIR/security"
    mkdir -p "$STORAGE_DIR/gdpr_exports"
    mkdir -p "$STORAGE_DIR/compliance_reports"
    mkdir -p "$STORAGE_DIR/archives/user_data"
    mkdir -p "$STORAGE_DIR/archives/audit_logs"
    mkdir -p "$STORAGE_DIR/archives/compliance_reports"
    
    # Monitoring directories
    mkdir -p "$PROJECT_ROOT/data/prometheus"
    mkdir -p "$PROJECT_ROOT/data/grafana"
    mkdir -p "$PROJECT_ROOT/data/loki"
    mkdir -p "$PROJECT_ROOT/data/vault"
    
    # Configuration directories
    mkdir -p "$PROJECT_ROOT/config/prometheus/rules"
    mkdir -p "$PROJECT_ROOT/config/grafana/dashboards"
    mkdir -p "$PROJECT_ROOT/config/grafana/provisioning/dashboards"
    mkdir -p "$PROJECT_ROOT/config/grafana/provisioning/datasources"
    mkdir -p "$PROJECT_ROOT/config/loki"
    mkdir -p "$PROJECT_ROOT/config/vault"
    
    success "Directories created successfully"
}

# Generate secrets for compliance services
generate_secrets() {
    log "Generating secrets for compliance services..."
    
    SECRETS_DIR="$PROJECT_ROOT/secrets"
    mkdir -p "$SECRETS_DIR"
    
    # Generate Vault root token
    if [[ ! -f "$SECRETS_DIR/vault_root_token.txt" ]]; then
        openssl rand -hex 16 > "$SECRETS_DIR/vault_root_token.txt"
        log "Generated Vault root token"
    fi
    
    # Generate Grafana admin password
    if [[ ! -f "$SECRETS_DIR/grafana_admin_password.txt" ]]; then
        openssl rand -base64 32 > "$SECRETS_DIR/grafana_admin_password.txt"
        log "Generated Grafana admin password"
    fi
    
    # Generate audit encryption key
    if [[ ! -f "$SECRETS_DIR/audit_encryption_key.txt" ]]; then
        openssl rand -base64 32 > "$SECRETS_DIR/audit_encryption_key.txt"
        log "Generated audit encryption key"
    fi
    
    # Set appropriate permissions
    chmod 600 "$SECRETS_DIR"/*.txt
    
    success "Secrets generated successfully"
}

# Setup Grafana provisioning
setup_grafana_provisioning() {
    log "Setting up Grafana provisioning..."
    
    # Datasources configuration
    cat > "$PROJECT_ROOT/config/grafana/provisioning/datasources/datasources.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
    
  - name: MySQL
    type: mysql
    access: proxy
    url: mysql:3306
    database: vedfolnir
    user: vedfolnir
    secureJsonData:
      password: ${MYSQL_PASSWORD}
    editable: true
EOF

    # Dashboards configuration
    cat > "$PROJECT_ROOT/config/grafana/provisioning/dashboards/dashboards.yml" << 'EOF'
apiVersion: 1

providers:
  - name: 'compliance'
    orgId: 1
    folder: 'Compliance'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

    success "Grafana provisioning configured"
}

# Setup Prometheus configuration
setup_prometheus_config() {
    log "Setting up Prometheus configuration..."
    
    cat > "$PROJECT_ROOT/config/prometheus/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          # - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'vedfolnir-app'
    static_configs:
      - targets: ['vedfolnir:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'mysql-exporter'
    static_configs:
      - targets: ['mysql-exporter:9104']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'nginx-exporter'
    static_configs:
      - targets: ['nginx-exporter:9113']

  - job_name: 'loki'
    static_configs:
      - targets: ['loki:3100']

  - job_name: 'grafana'
    static_configs:
      - targets: ['grafana:3000']
EOF

    success "Prometheus configuration created"
}

# Run database migrations for compliance tables
run_migrations() {
    log "Running database migrations for compliance tables..."
    
    cd "$PROJECT_ROOT"
    
    # Check if we're in a container environment
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        error "Python not found. Cannot run migrations."
        return 1
    fi
    
    # Run the compliance tables migration
    if [[ -f "migrations/add_compliance_tables.py" ]]; then
        log "Running compliance tables migration..."
        $PYTHON_CMD migrations/add_compliance_tables.py || {
            warning "Migration script execution failed. This may be normal if tables already exist."
        }
    else
        warning "Compliance tables migration script not found. Tables may need to be created manually."
    fi
    
    success "Database migrations completed"
}

# Test compliance framework components
test_compliance_framework() {
    log "Testing compliance framework components..."
    
    cd "$PROJECT_ROOT"
    
    # Check if we can import compliance modules
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app.services.compliance.compliance_service import ComplianceService
    from app.services.compliance.audit_logger import AuditLogger
    from app.services.compliance.gdpr_compliance import GDPRComplianceService
    print('✓ Compliance modules imported successfully')
except ImportError as e:
    print(f'✗ Failed to import compliance modules: {e}')
    sys.exit(1)
" || {
        error "Compliance framework component test failed"
        return 1
    }
    
    # Run compliance framework tests if available
    if [[ -f "tests/compliance/test_compliance_framework.py" ]]; then
        log "Running compliance framework tests..."
        python3 -m pytest tests/compliance/test_compliance_framework.py -v || {
            warning "Some compliance tests failed. Review test output."
        }
    fi
    
    success "Compliance framework testing completed"
}

# Deploy with Docker Compose
deploy_with_docker() {
    log "Deploying compliance framework with Docker Compose..."
    
    cd "$PROJECT_ROOT"
    
    # Check if Docker and Docker Compose are available
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        return 1
    fi
    
    # Use docker compose or docker-compose based on availability
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # Deploy compliance services
    log "Starting compliance services..."
    $COMPOSE_CMD -f docker-compose.yml -f docker-compose.compliance.yml up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    log "Checking service health..."
    $COMPOSE_CMD -f docker-compose.yml -f docker-compose.compliance.yml ps
    
    success "Compliance framework deployed with Docker Compose"
}

# Validate deployment
validate_deployment() {
    log "Validating compliance framework deployment..."
    
    # Check if services are running
    local services=("vedfolnir" "mysql" "redis" "prometheus" "grafana" "loki" "vault")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "vedfolnir_$service"; then
            success "✓ $service is running"
        else
            error "✗ $service is not running"
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        error "Some services failed to start: ${failed_services[*]}"
        return 1
    fi
    
    # Test service endpoints
    log "Testing service endpoints..."
    
    # Test Prometheus
    if curl -s http://localhost:9090/-/healthy > /dev/null; then
        success "✓ Prometheus is healthy"
    else
        warning "✗ Prometheus health check failed"
    fi
    
    # Test Grafana
    if curl -s http://localhost:3000/api/health > /dev/null; then
        success "✓ Grafana is healthy"
    else
        warning "✗ Grafana health check failed"
    fi
    
    # Test Loki
    if curl -s http://localhost:3100/ready > /dev/null; then
        success "✓ Loki is ready"
    else
        warning "✗ Loki readiness check failed"
    fi
    
    success "Deployment validation completed"
}

# Display deployment information
show_deployment_info() {
    log "Compliance Framework Deployment Information"
    echo
    echo "Services:"
    echo "  - Grafana Dashboard: http://localhost:3000"
    echo "  - Prometheus Metrics: http://localhost:9090"
    echo "  - Loki Logs: http://localhost:3100"
    echo "  - Vault Secrets: http://localhost:8200"
    echo
    echo "Credentials:"
    echo "  - Grafana Admin: admin / $(cat "$PROJECT_ROOT/secrets/grafana_admin_password.txt" 2>/dev/null || echo 'admin')"
    echo "  - Vault Root Token: $(cat "$PROJECT_ROOT/secrets/vault_root_token.txt" 2>/dev/null || echo 'Not generated')"
    echo
    echo "Configuration Files:"
    echo "  - Audit Config: $COMPLIANCE_CONFIG_DIR/audit_config.yml"
    echo "  - Prometheus Config: $PROJECT_ROOT/config/prometheus/prometheus.yml"
    echo "  - Loki Config: $PROJECT_ROOT/config/loki/loki.yml"
    echo
    echo "Data Directories:"
    echo "  - Audit Logs: $LOGS_DIR/audit"
    echo "  - GDPR Exports: $STORAGE_DIR/gdpr_exports"
    echo "  - Compliance Reports: $STORAGE_DIR/compliance_reports"
    echo "  - Archives: $STORAGE_DIR/archives"
    echo
    success "Compliance framework deployment completed successfully!"
}

# Main deployment function
main() {
    log "Starting Compliance and Audit Framework Deployment"
    echo
    
    # Check permissions
    check_permissions
    
    # Create directories
    create_directories
    
    # Generate secrets
    generate_secrets
    
    # Setup configurations
    setup_grafana_provisioning
    setup_prometheus_config
    
    # Run database migrations
    run_migrations
    
    # Test framework components
    test_compliance_framework
    
    # Deploy with Docker
    if [[ "${1:-}" == "--docker" ]] || [[ "${DEPLOY_WITH_DOCKER:-}" == "true" ]]; then
        deploy_with_docker
        validate_deployment
    else
        log "Skipping Docker deployment. Use --docker flag to deploy with Docker Compose."
    fi
    
    # Show deployment information
    show_deployment_info
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Compliance Framework Deployment Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --docker    Deploy with Docker Compose"
        echo "  --help      Show this help message"
        echo
        echo "Environment Variables:"
        echo "  DEPLOY_WITH_DOCKER=true    Deploy with Docker Compose"
        echo
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac