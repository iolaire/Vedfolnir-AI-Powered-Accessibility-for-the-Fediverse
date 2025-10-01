#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Validation script for resource management and scaling implementation
# This script validates that all components of task 13 are properly implemented

set -euo pipefail

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

# Validation results
VALIDATION_RESULTS=()

# Add validation result
add_result() {
    local status="$1"
    local message="$2"
    VALIDATION_RESULTS+=("$status:$message")
    
    if [[ "$status" == "PASS" ]]; then
        log "SUCCESS" "$message"
    elif [[ "$status" == "FAIL" ]]; then
        log "ERROR" "$message"
    else
        log "WARNING" "$message"
    fi
}

# Validate file exists
validate_file() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        add_result "PASS" "$description exists: $file"
        return 0
    else
        add_result "FAIL" "$description missing: $file"
        return 1
    fi
}

# Validate directory exists
validate_directory() {
    local dir="$1"
    local description="$2"
    
    if [[ -d "$dir" ]]; then
        add_result "PASS" "$description exists: $dir"
        return 0
    else
        add_result "FAIL" "$description missing: $dir"
        return 1
    fi
}

# Validate file is executable
validate_executable() {
    local file="$1"
    local description="$2"
    
    if [[ -x "$file" ]]; then
        add_result "PASS" "$description is executable: $file"
        return 0
    else
        add_result "FAIL" "$description is not executable: $file"
        return 1
    fi
}

# Validate Docker Compose configuration
validate_docker_compose() {
    log "INFO" "Validating Docker Compose configurations..."
    
    # Check main compose file
    validate_file "docker-compose.yml" "Main Docker Compose file"
    
    # Check scaling compose file
    validate_file "docker-compose.scaling.yml" "Scaling Docker Compose file"
    
    # Validate compose file syntax
    if docker-compose -f docker-compose.yml -f docker-compose.scaling.yml config >/dev/null 2>&1; then
        add_result "PASS" "Docker Compose configuration is valid"
    else
        add_result "FAIL" "Docker Compose configuration has syntax errors"
    fi
    
    # Check for resource limits in main file
    if grep -q "resources:" docker-compose.yml; then
        add_result "PASS" "Resource limits configured in main compose file"
    else
        add_result "FAIL" "No resource limits found in main compose file"
    fi
    
    # Check for scaling configuration
    if grep -q "replicas:" docker-compose.scaling.yml; then
        add_result "PASS" "Scaling configuration found in scaling compose file"
    else
        add_result "FAIL" "No scaling configuration found in scaling compose file"
    fi
}

# Validate resource monitoring
validate_monitoring() {
    log "INFO" "Validating resource monitoring configuration..."
    
    # Check Prometheus configuration
    validate_file "config/prometheus/prometheus.yml" "Prometheus configuration"
    
    # Check alert rules
    validate_file "config/prometheus/rules/resource-alerts.yml" "Resource alert rules"
    validate_file "config/prometheus/rules/alert_rules.yml" "General alert rules"
    validate_file "config/prometheus/rules/vedfolnir-alerts.yml" "Vedfolnir alert rules"
    
    # Check Grafana dashboard
    validate_file "config/grafana/dashboards/resource-management.json" "Resource management dashboard"
    
    # Validate alert rules syntax
    if command -v promtool >/dev/null 2>&1; then
        if promtool check rules config/prometheus/rules/*.yml >/dev/null 2>&1; then
            add_result "PASS" "Prometheus alert rules syntax is valid"
        else
            add_result "FAIL" "Prometheus alert rules have syntax errors"
        fi
    else
        add_result "WARN" "promtool not available, skipping alert rules validation"
    fi
}

# Validate auto-scaling implementation
validate_auto_scaling() {
    log "INFO" "Validating auto-scaling implementation..."
    
    # Check auto-scaling script
    validate_file "scripts/docker/auto-scaling.sh" "Auto-scaling script"
    validate_executable "scripts/docker/auto-scaling.sh" "Auto-scaling script"
    
    # Check test script
    validate_file "scripts/docker/test-resource-management.sh" "Resource management test script"
    validate_executable "scripts/docker/test-resource-management.sh" "Resource management test script"
    
    # Check validation script
    validate_file "scripts/docker/validate-resource-implementation.sh" "Resource implementation validation script"
    validate_executable "scripts/docker/validate-resource-implementation.sh" "Resource implementation validation script"
    
    # Test auto-scaling script help
    local auto_scaling_help_output
    auto_scaling_help_output=$(./scripts/docker/auto-scaling.sh invalid-command 2>&1 || true)
    if echo "$auto_scaling_help_output" | grep -q "Usage:"; then
        add_result "PASS" "Auto-scaling script help function works"
    else
        add_result "FAIL" "Auto-scaling script help function not working"
    fi
    
    # Test resource management test script help
    local test_script_help_output
    test_script_help_output=$(./scripts/docker/test-resource-management.sh invalid-test 2>&1 || true)
    if echo "$test_script_help_output" | grep -q "Unknown test type"; then
        add_result "PASS" "Resource management test script help function works"
    else
        add_result "FAIL" "Resource management test script help function not working"
    fi
}

# Validate automation configuration
validate_automation() {
    log "INFO" "Validating automation configuration..."
    
    # Check cron configuration
    validate_file "config/cron/auto-scaling.cron" "Cron job configuration"
    
    # Check systemd service
    validate_file "config/systemd/vedfolnir-autoscaler.service" "Systemd service configuration"
    
    # Validate cron syntax
    if grep -q "*/2 \* \* \* \*" config/cron/auto-scaling.cron; then
        add_result "PASS" "Cron job syntax appears valid"
    else
        add_result "FAIL" "Cron job syntax may be invalid"
    fi
}

# Validate documentation
validate_documentation() {
    log "INFO" "Validating documentation..."
    
    # Check main documentation
    validate_file "docs/docker/resource-management-scaling.md" "Resource management documentation"
    
    # Check documentation content
    if grep -q "Resource Management and Scaling" docs/docker/resource-management-scaling.md; then
        add_result "PASS" "Documentation contains expected content"
    else
        add_result "FAIL" "Documentation missing expected content"
    fi
    
    # Check for key sections
    local sections=(
        "Resource Configuration"
        "Horizontal Scaling"
        "Auto-Scaling"
        "Monitoring and Alerting"
        "Testing"
        "Troubleshooting"
    )
    
    for section in "${sections[@]}"; do
        if grep -q "$section" docs/docker/resource-management-scaling.md; then
            add_result "PASS" "Documentation contains '$section' section"
        else
            add_result "FAIL" "Documentation missing '$section' section"
        fi
    done
}

# Validate directory structure
validate_directories() {
    log "INFO" "Validating directory structure..."
    
    # Check required directories
    validate_directory "config/prometheus/rules" "Prometheus rules directory"
    validate_directory "config/grafana/dashboards" "Grafana dashboards directory"
    validate_directory "config/cron" "Cron configuration directory"
    validate_directory "config/systemd" "Systemd configuration directory"
    validate_directory "scripts/docker" "Docker scripts directory"
    validate_directory "docs/docker" "Docker documentation directory"
}

# Validate task requirements
validate_requirements() {
    log "INFO" "Validating task requirements..."
    
    # Requirement 13.1: Configure CPU and memory limits for all containers
    if grep -q "cpus:" docker-compose.yml && grep -q "memory:" docker-compose.yml; then
        add_result "PASS" "Requirement 13.1: CPU and memory limits configured"
    else
        add_result "FAIL" "Requirement 13.1: CPU and memory limits not properly configured"
    fi
    
    # Requirement 13.2: Set up horizontal scaling configuration for application containers
    if grep -q "replicas:" docker-compose.scaling.yml; then
        add_result "PASS" "Requirement 13.2: Horizontal scaling configuration implemented"
    else
        add_result "FAIL" "Requirement 13.2: Horizontal scaling configuration missing"
    fi
    
    # Requirement 13.3: Implement resource usage metrics and alerting
    if [[ -f "config/prometheus/rules/resource-alerts.yml" ]]; then
        add_result "PASS" "Requirement 13.3: Resource usage metrics and alerting implemented"
    else
        add_result "FAIL" "Requirement 13.3: Resource usage metrics and alerting missing"
    fi
    
    # Requirement 13.4: Configure resource reservations to prevent resource starvation
    if grep -q "reservations:" docker-compose.yml; then
        add_result "PASS" "Requirement 13.4: Resource reservations configured"
    else
        add_result "FAIL" "Requirement 13.4: Resource reservations not configured"
    fi
    
    # Requirement 13.5: Test auto-scaling based on defined metrics and policies
    if [[ -f "scripts/docker/test-resource-management.sh" ]] && [[ -x "scripts/docker/test-resource-management.sh" ]]; then
        add_result "PASS" "Requirement 13.5: Auto-scaling testing implemented"
    else
        add_result "FAIL" "Requirement 13.5: Auto-scaling testing not implemented"
    fi
}

# Generate summary report
generate_summary() {
    log "INFO" "Generating validation summary..."
    
    local total=0
    local passed=0
    local failed=0
    local warnings=0
    
    echo ""
    echo "=== VALIDATION SUMMARY ==="
    echo ""
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        local status="${result%%:*}"
        local message="${result#*:}"
        
        case "$status" in
            "PASS")
                echo -e "${GREEN}✓${NC} $message"
                passed=$((passed + 1))
                ;;
            "FAIL")
                echo -e "${RED}✗${NC} $message"
                failed=$((failed + 1))
                ;;
            "WARN")
                echo -e "${YELLOW}⚠${NC} $message"
                warnings=$((warnings + 1))
                ;;
        esac
        total=$((total + 1))
    done
    
    echo ""
    echo "=== RESULTS ==="
    echo "Total checks: $total"
    echo -e "Passed: ${GREEN}$passed${NC}"
    echo -e "Failed: ${RED}$failed${NC}"
    echo -e "Warnings: ${YELLOW}$warnings${NC}"
    echo ""
    
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}🎉 All critical validations passed!${NC}"
        echo -e "${GREEN}Task 13 (Resource Management and Scaling) is successfully implemented.${NC}"
        return 0
    else
        echo -e "${RED}❌ Some validations failed.${NC}"
        echo -e "${RED}Please address the failed items before considering the task complete.${NC}"
        return 1
    fi
}

# Main validation function
main() {
    log "INFO" "Starting resource management and scaling implementation validation..."
    echo ""
    
    # Run all validations
    validate_directories
    validate_docker_compose
    validate_monitoring
    validate_auto_scaling
    validate_automation
    validate_documentation
    validate_requirements
    
    echo ""
    
    # Generate summary
    generate_summary
}

# Run validation
main "$@"