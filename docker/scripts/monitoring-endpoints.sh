#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Monitoring endpoints configuration and testing script
# Provides comprehensive monitoring endpoint information for external tools

set -e

# Configuration
VERBOSE=${MONITORING_VERBOSE:-true}
OUTPUT_FORMAT=${MONITORING_OUTPUT_FORMAT:-json}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    fi
}

error_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}ERROR:${NC} $1" >&2
}

success_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}SUCCESS:${NC} $1"
}

warning_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING:${NC} $1"
}

info_log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${BLUE}INFO:${NC} $1"
}

# Test endpoint accessibility
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
    
    if [ "$response_code" = "$expected_status" ]; then
        success_log "$name endpoint OK ($url)"
        return 0
    else
        error_log "$name endpoint failed ($url) - HTTP $response_code"
        return 1
    fi
}

# Get all monitoring endpoints
get_monitoring_endpoints() {
    local endpoints=()
    
    # Application health endpoints
    endpoints+=("vedfolnir_health|http://localhost:5000/health|200")
    endpoints+=("vedfolnir_ready|http://localhost:5000/health/ready|200")
    endpoints+=("vedfolnir_live|http://localhost:5000/health/live|200")
    endpoints+=("vedfolnir_metrics|http://localhost:5000/metrics|200")
    
    # Prometheus endpoints
    endpoints+=("prometheus_health|http://localhost:9090/-/healthy|200")
    endpoints+=("prometheus_ready|http://localhost:9090/-/ready|200")
    endpoints+=("prometheus_config|http://localhost:9090/api/v1/status/config|200")
    endpoints+=("prometheus_targets|http://localhost:9090/api/v1/targets|200")
    endpoints+=("prometheus_metrics|http://localhost:9090/metrics|200")
    
    # Grafana endpoints
    endpoints+=("grafana_health|http://localhost:3000/api/health|200")
    endpoints+=("grafana_login|http://localhost:3000/login|200")
    
    # Loki endpoints
    endpoints+=("loki_ready|http://localhost:3100/ready|200")
    endpoints+=("loki_metrics|http://localhost:3100/metrics|200")
    endpoints+=("loki_config|http://localhost:3100/config|200")
    
    # Nginx endpoints
    endpoints+=("nginx_status|http://localhost:8080/nginx_status|200")
    
    # Metrics exporters
    endpoints+=("mysql_exporter|http://localhost:9104/metrics|200")
    endpoints+=("redis_exporter|http://localhost:9121/metrics|200")
    endpoints+=("nginx_exporter|http://localhost:9113/metrics|200")
    endpoints+=("node_exporter|http://localhost:9100/metrics|200")
    endpoints+=("cadvisor|http://localhost:8080/metrics|200")
    
    # External services
    endpoints+=("ollama_version|http://host.docker.internal:11434/api/version|200")
    
    printf '%s\n' "${endpoints[@]}"
}

# Test all endpoints
test_all_endpoints() {
    info_log "Testing all monitoring endpoints..."
    
    local total=0
    local passed=0
    local failed=0
    
    while IFS='|' read -r name url expected_status; do
        total=$((total + 1))
        if test_endpoint "$name" "$url" "$expected_status"; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
    done < <(get_monitoring_endpoints)
    
    echo ""
    info_log "Endpoint test summary:"
    success_log "Passed: $passed"
    error_log "Failed: $failed"
    info_log "Total: $total"
    
    if [ $failed -eq 0 ]; then
        success_log "All monitoring endpoints are accessible"
        return 0
    else
        error_log "$failed monitoring endpoints are not accessible"
        return 1
    fi
}

# Generate endpoint configuration for external monitoring tools
generate_endpoint_config() {
    local format="$1"
    
    case "$format" in
        "json")
            generate_json_config
            ;;
        "yaml")
            generate_yaml_config
            ;;
        "prometheus")
            generate_prometheus_config
            ;;
        "text")
            generate_text_config
            ;;
        *)
            error_log "Unknown format: $format"
            return 1
            ;;
    esac
}

# Generate JSON configuration
generate_json_config() {
    cat <<EOF
{
  "monitoring_endpoints": {
    "application": {
      "health": "http://localhost:5000/health",
      "ready": "http://localhost:5000/health/ready",
      "live": "http://localhost:5000/health/live",
      "metrics": "http://localhost:5000/metrics"
    },
    "prometheus": {
      "health": "http://localhost:9090/-/healthy",
      "ready": "http://localhost:9090/-/ready",
      "config": "http://localhost:9090/api/v1/status/config",
      "targets": "http://localhost:9090/api/v1/targets",
      "metrics": "http://localhost:9090/metrics"
    },
    "grafana": {
      "health": "http://localhost:3000/api/health",
      "login": "http://localhost:3000/login"
    },
    "loki": {
      "ready": "http://localhost:3100/ready",
      "metrics": "http://localhost:3100/metrics",
      "config": "http://localhost:3100/config"
    },
    "nginx": {
      "status": "http://localhost:8080/nginx_status"
    },
    "exporters": {
      "mysql": "http://localhost:9104/metrics",
      "redis": "http://localhost:9121/metrics",
      "nginx": "http://localhost:9113/metrics",
      "node": "http://localhost:9100/metrics",
      "cadvisor": "http://localhost:8080/metrics"
    },
    "external": {
      "ollama": "http://host.docker.internal:11434/api/version"
    }
  },
  "generated_at": "$(date -Iseconds)",
  "version": "1.0.0"
}
EOF
}

# Generate YAML configuration
generate_yaml_config() {
    cat <<EOF
monitoring_endpoints:
  application:
    health: "http://localhost:5000/health"
    ready: "http://localhost:5000/health/ready"
    live: "http://localhost:5000/health/live"
    metrics: "http://localhost:5000/metrics"
  prometheus:
    health: "http://localhost:9090/-/healthy"
    ready: "http://localhost:9090/-/ready"
    config: "http://localhost:9090/api/v1/status/config"
    targets: "http://localhost:9090/api/v1/targets"
    metrics: "http://localhost:9090/metrics"
  grafana:
    health: "http://localhost:3000/api/health"
    login: "http://localhost:3000/login"
  loki:
    ready: "http://localhost:3100/ready"
    metrics: "http://localhost:3100/metrics"
    config: "http://localhost:3100/config"
  nginx:
    status: "http://localhost:8080/nginx_status"
  exporters:
    mysql: "http://localhost:9104/metrics"
    redis: "http://localhost:9121/metrics"
    nginx: "http://localhost:9113/metrics"
    node: "http://localhost:9100/metrics"
    cadvisor: "http://localhost:8080/metrics"
  external:
    ollama: "http://host.docker.internal:11434/api/version"
generated_at: "$(date -Iseconds)"
version: "1.0.0"
EOF
}

# Generate Prometheus scrape configuration
generate_prometheus_config() {
    cat <<EOF
# Prometheus scrape configuration for Vedfolnir monitoring
scrape_configs:
  - job_name: 'vedfolnir-app'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s
    
  - job_name: 'mysql-exporter'
    static_configs:
      - targets: ['localhost:9104']
    scrape_interval: 15s
    scrape_timeout: 10s
    
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['localhost:9121']
    scrape_interval: 15s
    scrape_timeout: 10s
    
  - job_name: 'nginx-exporter'
    static_configs:
      - targets: ['localhost:9113']
    scrape_interval: 15s
    scrape_timeout: 10s
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 15s
    scrape_timeout: 10s
    
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s

# Health check endpoints for monitoring
health_check_endpoints:
  - name: 'vedfolnir-health'
    url: 'http://localhost:5000/health'
    interval: '30s'
    timeout: '10s'
    
  - name: 'prometheus-health'
    url: 'http://localhost:9090/-/healthy'
    interval: '30s'
    timeout: '10s'
    
  - name: 'grafana-health'
    url: 'http://localhost:3000/api/health'
    interval: '30s'
    timeout: '10s'
    
  - name: 'loki-ready'
    url: 'http://localhost:3100/ready'
    interval: '30s'
    timeout: '10s'
EOF
}

# Generate text configuration
generate_text_config() {
    echo "=== Vedfolnir Monitoring Endpoints ==="
    echo "Generated: $(date -Iseconds)"
    echo ""
    
    echo "Application Endpoints:"
    echo "  Health:   http://localhost:5000/health"
    echo "  Ready:    http://localhost:5000/health/ready"
    echo "  Live:     http://localhost:5000/health/live"
    echo "  Metrics:  http://localhost:5000/metrics"
    echo ""
    
    echo "Prometheus Endpoints:"
    echo "  Health:   http://localhost:9090/-/healthy"
    echo "  Ready:    http://localhost:9090/-/ready"
    echo "  Config:   http://localhost:9090/api/v1/status/config"
    echo "  Targets:  http://localhost:9090/api/v1/targets"
    echo "  Metrics:  http://localhost:9090/metrics"
    echo ""
    
    echo "Grafana Endpoints:"
    echo "  Health:   http://localhost:3000/api/health"
    echo "  Login:    http://localhost:3000/login"
    echo ""
    
    echo "Loki Endpoints:"
    echo "  Ready:    http://localhost:3100/ready"
    echo "  Metrics:  http://localhost:3100/metrics"
    echo "  Config:   http://localhost:3100/config"
    echo ""
    
    echo "Nginx Endpoints:"
    echo "  Status:   http://localhost:8080/nginx_status"
    echo ""
    
    echo "Metrics Exporters:"
    echo "  MySQL:    http://localhost:9104/metrics"
    echo "  Redis:    http://localhost:9121/metrics"
    echo "  Nginx:    http://localhost:9113/metrics"
    echo "  Node:     http://localhost:9100/metrics"
    echo "  cAdvisor: http://localhost:8080/metrics"
    echo ""
    
    echo "External Services:"
    echo "  Ollama:   http://host.docker.internal:11434/api/version"
    echo ""
    echo "======================================="
}

# Main function
main() {
    local action="${1:-test}"
    local format="${2:-json}"
    
    case "$action" in
        "test")
            test_all_endpoints
            ;;
        "config")
            generate_endpoint_config "$format"
            ;;
        "list")
            generate_text_config
            ;;
        "endpoints")
            get_monitoring_endpoints
            ;;
        *)
            echo "Usage: $0 {test|config [format]|list|endpoints}"
            echo ""
            echo "Actions:"
            echo "  test      - Test all monitoring endpoints"
            echo "  config    - Generate configuration for external tools"
            echo "  list      - List all endpoints in text format"
            echo "  endpoints - List raw endpoint data"
            echo ""
            echo "Formats (for config):"
            echo "  json       - JSON format (default)"
            echo "  yaml       - YAML format"
            echo "  prometheus - Prometheus scrape config"
            echo "  text       - Human-readable text"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"