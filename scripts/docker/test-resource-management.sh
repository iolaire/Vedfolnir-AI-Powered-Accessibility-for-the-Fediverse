#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Resource management and scaling test script for Vedfolnir Docker deployment
# This script tests resource limits, scaling behavior, and monitoring

set -euo pipefail

# Configuration
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SCALING_FILE="${SCALING_FILE:-docker-compose.scaling.yml}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
TEST_DURATION="${TEST_DURATION:-300}"  # 5 minutes
LOAD_INTENSITY="${LOAD_INTENSITY:-medium}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    local color="$NC"
    shift
    
    case "$level" in
        "ERROR") color="$RED" ;;
        "SUCCESS") color="$GREEN" ;;
        "WARNING") color="$YELLOW" ;;
        "INFO") color="$BLUE" ;;
    esac
    
    echo -e "${color}[$(date '+%H:%M:%S')] [$level]${NC} $*"
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check if Docker Compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        log "ERROR" "docker-compose is not installed"
        return 1
    fi
    
    # Check if required files exist
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log "ERROR" "Docker Compose file not found: $COMPOSE_FILE"
        return 1
    fi
    
    if [[ ! -f "$SCALING_FILE" ]]; then
        log "ERROR" "Scaling configuration file not found: $SCALING_FILE"
        return 1
    fi
    
    # Check if curl is available for API calls
    if ! command -v curl >/dev/null 2>&1; then
        log "ERROR" "curl is not installed"
        return 1
    fi
    
    # Check if jq is available for JSON parsing
    if ! command -v jq >/dev/null 2>&1; then
        log "ERROR" "jq is not installed"
        return 1
    fi
    
    log "SUCCESS" "Prerequisites check passed"
    return 0
}

# Start services with scaling configuration
start_services() {
    log "INFO" "Starting services with scaling configuration..."
    
    docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" up -d
    
    # Wait for services to be healthy
    log "INFO" "Waiting for services to be healthy..."
    local max_wait=300
    local wait_time=0
    
    while [[ $wait_time -lt $max_wait ]]; do
        local healthy_count
        healthy_count=$(docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" ps --format json | jq -r '.[] | select(.Health == "healthy") | .Name' | wc -l)
        local total_count
        total_count=$(docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" ps --format json | jq length)
        
        if [[ $healthy_count -eq $total_count ]] && [[ $total_count -gt 0 ]]; then
            log "SUCCESS" "All services are healthy"
            return 0
        fi
        
        log "INFO" "Waiting for services to be healthy ($healthy_count/$total_count)..."
        sleep 10
        wait_time=$((wait_time + 10))
    done
    
    log "ERROR" "Services did not become healthy within $max_wait seconds"
    return 1
}

# Test resource limits
test_resource_limits() {
    log "INFO" "Testing resource limits..."
    
    # Get container resource information
    local containers
    containers=$(docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" ps --format json | jq -r '.[].Name')
    
    for container in $containers; do
        log "INFO" "Checking resource limits for $container"
        
        # Get container resource limits
        local cpu_limit
        local memory_limit
        
        cpu_limit=$(docker inspect "$container" | jq -r '.[0].HostConfig.CpuQuota // "unlimited"')
        memory_limit=$(docker inspect "$container" | jq -r '.[0].HostConfig.Memory // "unlimited"')
        
        if [[ "$cpu_limit" != "unlimited" ]] && [[ "$cpu_limit" != "null" ]]; then
            log "SUCCESS" "$container has CPU limit: $cpu_limit"
        else
            log "WARNING" "$container has no CPU limit set"
        fi
        
        if [[ "$memory_limit" != "unlimited" ]] && [[ "$memory_limit" != "null" ]] && [[ "$memory_limit" != "0" ]]; then
            log "SUCCESS" "$container has memory limit: $(($memory_limit / 1024 / 1024))MB"
        else
            log "WARNING" "$container has no memory limit set"
        fi
    done
}

# Test scaling functionality
test_scaling() {
    log "INFO" "Testing scaling functionality..."
    
    # Get initial replica count
    local initial_replicas
    initial_replicas=$(docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" ps vedfolnir --format json | jq length)
    log "INFO" "Initial Vedfolnir replicas: $initial_replicas"
    
    # Scale up
    log "INFO" "Scaling up to 3 replicas..."
    docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" up -d --scale vedfolnir=3
    
    # Wait for scaling to complete
    sleep 30
    
    local scaled_replicas
    scaled_replicas=$(docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" ps vedfolnir --format json | jq length)
    
    if [[ $scaled_replicas -eq 3 ]]; then
        log "SUCCESS" "Successfully scaled up to 3 replicas"
    else
        log "ERROR" "Scaling up failed. Expected 3, got $scaled_replicas"
        return 1
    fi
    
    # Test load balancing
    log "INFO" "Testing load balancing across replicas..."
    local app_url="http://localhost:5000"
    local success_count=0
    
    for i in {1..10}; do
        if curl -s "$app_url/health" >/dev/null; then
            success_count=$((success_count + 1))
        fi
        sleep 1
    done
    
    if [[ $success_count -ge 8 ]]; then
        log "SUCCESS" "Load balancing test passed ($success_count/10 requests successful)"
    else
        log "WARNING" "Load balancing test partially failed ($success_count/10 requests successful)"
    fi
    
    # Scale back down
    log "INFO" "Scaling back down to $initial_replicas replicas..."
    docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" up -d --scale "vedfolnir=$initial_replicas"
    
    sleep 30
    
    local final_replicas
    final_replicas=$(docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" ps vedfolnir --format json | jq length)
    
    if [[ $final_replicas -eq $initial_replicas ]]; then
        log "SUCCESS" "Successfully scaled back down to $initial_replicas replicas"
    else
        log "ERROR" "Scaling down failed. Expected $initial_replicas, got $final_replicas"
        return 1
    fi
}

# Test metrics collection
test_metrics() {
    log "INFO" "Testing metrics collection..."
    
    # Check if Prometheus is accessible
    if ! curl -s "$PROMETHEUS_URL/api/v1/query" --data-urlencode "query=up" --get >/dev/null; then
        log "ERROR" "Cannot connect to Prometheus at $PROMETHEUS_URL"
        return 1
    fi
    
    log "SUCCESS" "Prometheus is accessible"
    
    # Test key metrics
    local metrics=(
        "vedfolnir:cpu_usage_avg"
        "vedfolnir:memory_usage_avg"
        "vedfolnir:instance_count"
        "vedfolnir:queue_depth"
        "vedfolnir:response_time_p95"
        "vedfolnir:scale_up_score"
        "vedfolnir:scale_down_score"
    )
    
    for metric in "${metrics[@]}"; do
        local result
        result=$(curl -s "$PROMETHEUS_URL/api/v1/query" \
            --data-urlencode "query=$metric" \
            --get | jq -r '.data.result[0].value[1] // "null"')
        
        if [[ "$result" != "null" ]]; then
            log "SUCCESS" "Metric $metric: $result"
        else
            log "WARNING" "Metric $metric: no data"
        fi
    done
}

# Test alerting rules
test_alerting() {
    log "INFO" "Testing alerting rules..."
    
    # Get alert rules from Prometheus
    local rules_response
    rules_response=$(curl -s "$PROMETHEUS_URL/api/v1/rules")
    
    local rule_count
    rule_count=$(echo "$rules_response" | jq '.data.groups | map(.rules | length) | add')
    
    if [[ $rule_count -gt 0 ]]; then
        log "SUCCESS" "Found $rule_count alert rules"
    else
        log "ERROR" "No alert rules found"
        return 1
    fi
    
    # Check for active alerts
    local alerts_response
    alerts_response=$(curl -s "$PROMETHEUS_URL/api/v1/alerts")
    
    local active_alerts
    active_alerts=$(echo "$alerts_response" | jq '.data.alerts | length')
    
    log "INFO" "Active alerts: $active_alerts"
    
    if [[ $active_alerts -gt 0 ]]; then
        log "WARNING" "There are active alerts:"
        echo "$alerts_response" | jq -r '.data.alerts[] | "- \(.labels.alertname): \(.annotations.summary)"'
    fi
}

# Generate load for testing
generate_load() {
    local duration="$1"
    local intensity="$2"
    
    log "INFO" "Generating load for $duration seconds (intensity: $intensity)..."
    
    local concurrent_requests=5
    local request_delay=1
    
    case "$intensity" in
        "low")
            concurrent_requests=2
            request_delay=2
            ;;
        "medium")
            concurrent_requests=5
            request_delay=1
            ;;
        "high")
            concurrent_requests=10
            request_delay=0.5
            ;;
    esac
    
    local app_url="http://localhost:5000"
    local end_time=$(($(date +%s) + duration))
    
    # Start background load generators
    local pids=()
    
    for ((i=1; i<=concurrent_requests; i++)); do
        (
            while [[ $(date +%s) -lt $end_time ]]; do
                curl -s "$app_url/" >/dev/null 2>&1 || true
                curl -s "$app_url/health" >/dev/null 2>&1 || true
                sleep "$request_delay"
            done
        ) &
        pids+=($!)
    done
    
    # Wait for load generation to complete
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    log "SUCCESS" "Load generation completed"
}

# Test auto-scaling behavior
test_auto_scaling() {
    log "INFO" "Testing auto-scaling behavior..."
    
    # Check if auto-scaling script exists
    if [[ ! -f "scripts/docker/auto-scaling.sh" ]]; then
        log "WARNING" "Auto-scaling script not found, skipping auto-scaling test"
        return 0
    fi
    
    # Test auto-scaling script health check
    if bash scripts/docker/auto-scaling.sh health; then
        log "SUCCESS" "Auto-scaling script health check passed"
    else
        log "ERROR" "Auto-scaling script health check failed"
        return 1
    fi
    
    # Generate report
    log "INFO" "Generating auto-scaling report..."
    bash scripts/docker/auto-scaling.sh report
}

# Performance benchmark
run_performance_benchmark() {
    log "INFO" "Running performance benchmark..."
    
    local app_url="http://localhost:5000"
    local benchmark_duration=60
    local total_requests=0
    local successful_requests=0
    local start_time=$(date +%s)
    local end_time=$((start_time + benchmark_duration))
    
    while [[ $(date +%s) -lt $end_time ]]; do
        if curl -s -w "%{http_code}" "$app_url/health" -o /dev/null | grep -q "200"; then
            successful_requests=$((successful_requests + 1))
        fi
        total_requests=$((total_requests + 1))
        sleep 0.1
    done
    
    local success_rate=$((successful_requests * 100 / total_requests))
    local rps=$((total_requests / benchmark_duration))
    
    log "INFO" "Performance benchmark results:"
    log "INFO" "  Total requests: $total_requests"
    log "INFO" "  Successful requests: $successful_requests"
    log "INFO" "  Success rate: $success_rate%"
    log "INFO" "  Requests per second: $rps"
    
    if [[ $success_rate -ge 95 ]]; then
        log "SUCCESS" "Performance benchmark passed"
    else
        log "WARNING" "Performance benchmark below threshold (95%)"
    fi
}

# Cleanup function
cleanup() {
    log "INFO" "Cleaning up test environment..."
    
    # Stop any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # Reset scaling to default
    docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" up -d --scale vedfolnir=2 2>/dev/null || true
    
    log "INFO" "Cleanup completed"
}

# Main test function
run_tests() {
    local test_type="${1:-all}"
    
    log "INFO" "Starting resource management and scaling tests (type: $test_type)"
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    case "$test_type" in
        "prerequisites")
            check_prerequisites
            ;;
        "limits")
            check_prerequisites
            start_services
            test_resource_limits
            ;;
        "scaling")
            check_prerequisites
            start_services
            test_scaling
            ;;
        "metrics")
            check_prerequisites
            start_services
            test_metrics
            ;;
        "alerting")
            check_prerequisites
            start_services
            test_alerting
            ;;
        "auto-scaling")
            check_prerequisites
            start_services
            test_auto_scaling
            ;;
        "performance")
            check_prerequisites
            start_services
            run_performance_benchmark
            ;;
        "load")
            check_prerequisites
            start_services
            generate_load "$TEST_DURATION" "$LOAD_INTENSITY"
            ;;
        "all")
            check_prerequisites
            start_services
            test_resource_limits
            test_scaling
            test_metrics
            test_alerting
            test_auto_scaling
            generate_load 60 "medium"
            run_performance_benchmark
            ;;
        *)
            log "ERROR" "Unknown test type: $test_type"
            echo "Usage: $0 [prerequisites|limits|scaling|metrics|alerting|auto-scaling|performance|load|all]"
            exit 1
            ;;
    esac
    
    log "SUCCESS" "Resource management and scaling tests completed"
}

# Run tests
run_tests "$@"