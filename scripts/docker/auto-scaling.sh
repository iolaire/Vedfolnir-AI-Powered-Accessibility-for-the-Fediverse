#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Auto-scaling script for Vedfolnir Docker Compose deployment
# This script monitors metrics and automatically scales services based on resource usage

set -euo pipefail

# Configuration
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SCALING_FILE="${SCALING_FILE:-docker-compose.scaling.yml}"
LOG_FILE="${LOG_FILE:-./logs/auto-scaling.log}"
DRY_RUN="${DRY_RUN:-false}"

# Scaling parameters
MIN_REPLICAS=2
MAX_REPLICAS=5
SCALE_UP_THRESHOLD=0.7
SCALE_DOWN_THRESHOLD=0.3
SCALE_UP_COOLDOWN=300  # 5 minutes
SCALE_DOWN_COOLDOWN=600  # 10 minutes
QUEUE_SCALE_UP_THRESHOLD=50
RESPONSE_TIME_THRESHOLD=3.0

# State file to track last scaling action
STATE_FILE="./data/auto-scaling-state.json"

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Initialize state file if it doesn't exist
init_state() {
    if [[ ! -f "$STATE_FILE" ]]; then
        cat > "$STATE_FILE" << EOF
{
    "last_scale_up": 0,
    "last_scale_down": 0,
    "current_replicas": 2,
    "scaling_history": []
}
EOF
    fi
}

# Query Prometheus for metrics
query_prometheus() {
    local query="$1"
    local result
    
    result=$(curl -s "${PROMETHEUS_URL}/api/v1/query" \
        --data-urlencode "query=${query}" \
        --get | jq -r '.data.result[0].value[1] // "0"')
    
    echo "$result"
}

# Get current replica count
get_current_replicas() {
    docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" ps vedfolnir --format json | jq length
}

# Scale service
scale_service() {
    local service="$1"
    local replicas="$2"
    local reason="$3"
    
    log "INFO" "Scaling $service to $replicas replicas. Reason: $reason"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "DRY RUN: Would scale $service to $replicas replicas"
        return 0
    fi
    
    # Update state file
    local timestamp=$(date +%s)
    local current_state=$(cat "$STATE_FILE")
    local new_state
    
    if [[ $replicas -gt $(echo "$current_state" | jq -r '.current_replicas') ]]; then
        new_state=$(echo "$current_state" | jq ".last_scale_up = $timestamp | .current_replicas = $replicas")
    else
        new_state=$(echo "$current_state" | jq ".last_scale_down = $timestamp | .current_replicas = $replicas")
    fi
    
    # Add to scaling history
    new_state=$(echo "$new_state" | jq ".scaling_history += [{\"timestamp\": $timestamp, \"replicas\": $replicas, \"reason\": \"$reason\"}]")
    
    # Keep only last 100 history entries
    new_state=$(echo "$new_state" | jq '.scaling_history = (.scaling_history | sort_by(.timestamp) | .[-100:])')
    
    echo "$new_state" > "$STATE_FILE"
    
    # Perform scaling
    docker-compose -f "$COMPOSE_FILE" -f "$SCALING_FILE" up -d --scale "$service=$replicas"
    
    if [[ $? -eq 0 ]]; then
        log "INFO" "Successfully scaled $service to $replicas replicas"
        
        # Send notification (if configured)
        if command -v curl >/dev/null && [[ -n "${WEBHOOK_URL:-}" ]]; then
            curl -X POST "$WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -d "{\"text\": \"Vedfolnir auto-scaled $service to $replicas replicas. Reason: $reason\"}" \
                >/dev/null 2>&1 || true
        fi
    else
        log "ERROR" "Failed to scale $service to $replicas replicas"
        return 1
    fi
}

# Check if scaling is allowed (cooldown period)
can_scale_up() {
    local current_state=$(cat "$STATE_FILE")
    local last_scale_up=$(echo "$current_state" | jq -r '.last_scale_up')
    local current_time=$(date +%s)
    
    [[ $((current_time - last_scale_up)) -gt $SCALE_UP_COOLDOWN ]]
}

can_scale_down() {
    local current_state=$(cat "$STATE_FILE")
    local last_scale_down=$(echo "$current_state" | jq -r '.last_scale_down')
    local current_time=$(date +%s)
    
    [[ $((current_time - last_scale_down)) -gt $SCALE_DOWN_COOLDOWN ]]
}

# Main scaling logic
check_and_scale() {
    local current_replicas
    current_replicas=$(get_current_replicas)
    
    log "INFO" "Current replicas: $current_replicas"
    
    # Get metrics
    local cpu_usage
    local memory_usage
    local queue_depth
    local response_time
    local error_rate
    
    cpu_usage=$(query_prometheus "vedfolnir:cpu_usage_avg")
    memory_usage=$(query_prometheus "vedfolnir:memory_usage_avg")
    queue_depth=$(query_prometheus "vedfolnir:queue_depth")
    response_time=$(query_prometheus "vedfolnir:response_time_p95")
    error_rate=$(query_prometheus "vedfolnir:error_rate")
    
    log "INFO" "Metrics - CPU: ${cpu_usage}, Memory: ${memory_usage}, Queue: ${queue_depth}, Response Time: ${response_time}, Error Rate: ${error_rate}"
    
    # Calculate scaling scores
    local scale_up_score
    local scale_down_score
    
    scale_up_score=$(query_prometheus "vedfolnir:scale_up_score")
    scale_down_score=$(query_prometheus "vedfolnir:scale_down_score")
    
    log "INFO" "Scaling scores - Up: ${scale_up_score}, Down: ${scale_down_score}"
    
    # Scaling decision logic
    if [[ $(echo "$scale_up_score >= 5" | bc -l) -eq 1 ]] && [[ $current_replicas -lt $MAX_REPLICAS ]] && can_scale_up; then
        local new_replicas=$((current_replicas + 1))
        local reason="High resource usage (score: $scale_up_score)"
        
        # Additional checks for urgent scaling
        if [[ $(echo "$queue_depth > 100" | bc -l) -eq 1 ]] || [[ $(echo "$error_rate > 0.1" | bc -l) -eq 1 ]]; then
            new_replicas=$((current_replicas + 2))
            if [[ $new_replicas -gt $MAX_REPLICAS ]]; then
                new_replicas=$MAX_REPLICAS
            fi
            reason="Urgent scaling needed - high queue depth or error rate"
        fi
        
        scale_service "vedfolnir" "$new_replicas" "$reason"
        
    elif [[ $(echo "$scale_down_score >= 5" | bc -l) -eq 1 ]] && [[ $current_replicas -gt $MIN_REPLICAS ]] && can_scale_down; then
        local new_replicas=$((current_replicas - 1))
        local reason="Low resource usage (score: $scale_down_score)"
        
        scale_service "vedfolnir" "$new_replicas" "$reason"
        
    else
        log "INFO" "No scaling action needed"
    fi
}

# Health check function
health_check() {
    log "INFO" "Performing health check"
    
    # Check if Prometheus is accessible
    if ! curl -s "${PROMETHEUS_URL}/api/v1/query" --data-urlencode "query=up" --get >/dev/null; then
        log "ERROR" "Cannot connect to Prometheus at $PROMETHEUS_URL"
        return 1
    fi
    
    # Check if Docker Compose is working
    if ! docker-compose -f "$COMPOSE_FILE" ps >/dev/null 2>&1; then
        log "ERROR" "Docker Compose is not working properly"
        return 1
    fi
    
    # Check if services are running
    local vedfolnir_count
    vedfolnir_count=$(docker-compose -f "$COMPOSE_FILE" ps vedfolnir --format json | jq length)
    
    if [[ $vedfolnir_count -eq 0 ]]; then
        log "ERROR" "No Vedfolnir containers are running"
        return 1
    fi
    
    log "INFO" "Health check passed"
    return 0
}

# Generate scaling report
generate_report() {
    local state=$(cat "$STATE_FILE")
    local current_replicas=$(echo "$state" | jq -r '.current_replicas')
    local last_scale_up=$(echo "$state" | jq -r '.last_scale_up')
    local last_scale_down=$(echo "$state" | jq -r '.last_scale_down')
    
    echo "=== Vedfolnir Auto-Scaling Report ==="
    echo "Generated: $(date)"
    echo "Current Replicas: $current_replicas"
    echo "Last Scale Up: $(date -d @$last_scale_up 2>/dev/null || echo 'Never')"
    echo "Last Scale Down: $(date -d @$last_scale_down 2>/dev/null || echo 'Never')"
    echo ""
    echo "Recent Scaling History:"
    echo "$state" | jq -r '.scaling_history[-10:] | .[] | "\(.timestamp | strftime("%Y-%m-%d %H:%M:%S")) - \(.replicas) replicas - \(.reason)"'
    echo ""
    echo "Current Metrics:"
    echo "CPU Usage: $(query_prometheus "vedfolnir:cpu_usage_avg")"
    echo "Memory Usage: $(query_prometheus "vedfolnir:memory_usage_avg")"
    echo "Queue Depth: $(query_prometheus "vedfolnir:queue_depth")"
    echo "Response Time P95: $(query_prometheus "vedfolnir:response_time_p95")"
    echo "Error Rate: $(query_prometheus "vedfolnir:error_rate")"
}

# Main function
main() {
    local command="${1:-check}"
    
    case "$command" in
        "check")
            init_state
            if health_check; then
                check_and_scale
            else
                log "ERROR" "Health check failed, skipping scaling"
                exit 1
            fi
            ;;
        "report")
            init_state
            generate_report
            ;;
        "health")
            health_check
            ;;
        "scale-up")
            local replicas="${2:-$(($(get_current_replicas) + 1))}"
            scale_service "vedfolnir" "$replicas" "Manual scale up"
            ;;
        "scale-down")
            local replicas="${2:-$(($(get_current_replicas) - 1))}"
            if [[ $replicas -lt $MIN_REPLICAS ]]; then
                replicas=$MIN_REPLICAS
            fi
            scale_service "vedfolnir" "$replicas" "Manual scale down"
            ;;
        "reset")
            echo '{"last_scale_up": 0, "last_scale_down": 0, "current_replicas": 2, "scaling_history": []}' > "$STATE_FILE"
            log "INFO" "Auto-scaling state reset"
            ;;
        *)
            echo "Usage: $0 {check|report|health|scale-up [replicas]|scale-down [replicas]|reset}"
            echo ""
            echo "Commands:"
            echo "  check      - Check metrics and scale if needed"
            echo "  report     - Generate scaling report"
            echo "  health     - Perform health check"
            echo "  scale-up   - Manually scale up"
            echo "  scale-down - Manually scale down"
            echo "  reset      - Reset scaling state"
            echo ""
            echo "Environment variables:"
            echo "  PROMETHEUS_URL - Prometheus endpoint (default: http://localhost:9090)"
            echo "  DRY_RUN        - Set to 'true' for dry run mode"
            echo "  WEBHOOK_URL    - Webhook for notifications"
            exit 1
            ;;
    esac
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$STATE_FILE")"

# Run main function
main "$@"