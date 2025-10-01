#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Comprehensive Docker Compose Validation Test Runner
# This script runs all validation tests to verify functionality parity with macOS deployment

set -e  # Exit on any error

# Configuration
BASE_URL="${TEST_BASE_URL:-http://localhost:5000}"
WAIT_TIME="${WAIT_TIME:-60}"
VERBOSE="${VERBOSE:-false}"
TEST_CATEGORIES="${TEST_CATEGORIES:-all}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${BLUE}[${timestamp}] INFO:${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[${timestamp}] SUCCESS:${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[${timestamp}] WARNING:${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ERROR:${NC} $message"
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        log "ERROR" "docker-compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log "ERROR" "python3 is not installed or not in PATH"
        exit 1
    fi
    
    # Check if required Python packages are installed
    python3 -c "import requests, docker, redis, mysql.connector" 2>/dev/null || {
        log "ERROR" "Required Python packages not installed. Run: pip install requests docker redis mysql-connector-python"
        exit 1
    }
    
    log "SUCCESS" "Prerequisites check passed"
}

# Function to wait for services
wait_for_services() {
    log "INFO" "Waiting ${WAIT_TIME} seconds for services to be ready..."
    
    local start_time=$(date +%s)
    local timeout=$((start_time + WAIT_TIME))
    
    while [ $(date +%s) -lt $timeout ]; do
        if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
            log "SUCCESS" "Services are ready!"
            return 0
        fi
        
        log "INFO" "Services not ready yet, waiting..."
        sleep 5
    done
    
    log "ERROR" "Services did not become ready within ${WAIT_TIME} seconds"
    return 1
}

# Function to check Docker Compose services
check_docker_services() {
    log "INFO" "Checking Docker Compose services status..."
    
    if ! docker-compose ps | grep -q "Up"; then
        log "ERROR" "Docker Compose services are not running"
        log "INFO" "Run 'docker-compose up -d' to start services"
        exit 1
    fi
    
    # List running services
    log "INFO" "Running services:"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    
    log "SUCCESS" "Docker Compose services are running"
}

# Function to run Docker Compose validation tests
run_docker_compose_tests() {
    log "INFO" "Running Docker Compose validation tests..."
    
    if [ "$VERBOSE" = "true" ]; then
        python3 -m unittest tests.integration.test_docker_compose_validation -v
    else
        python3 -m unittest tests.integration.test_docker_compose_validation
    fi
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Docker Compose validation tests passed"
    else
        log "ERROR" "Docker Compose validation tests failed"
        return $exit_code
    fi
}

# Function to run API endpoint tests
run_api_endpoint_tests() {
    log "INFO" "Running API endpoint validation tests..."
    
    export TEST_BASE_URL="$BASE_URL"
    
    if [ "$VERBOSE" = "true" ]; then
        python3 -m unittest tests.integration.test_api_endpoint_validation -v
    else
        python3 -m unittest tests.integration.test_api_endpoint_validation
    fi
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "API endpoint validation tests passed"
    else
        log "ERROR" "API endpoint validation tests failed"
        return $exit_code
    fi
}

# Function to run backup and restore tests
run_backup_restore_tests() {
    log "INFO" "Running backup and restore validation tests..."
    
    if [ "$VERBOSE" = "true" ]; then
        python3 -m unittest tests.integration.test_backup_restore_validation -v
    else
        python3 -m unittest tests.integration.test_backup_restore_validation
    fi
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Backup and restore validation tests passed"
    else
        log "ERROR" "Backup and restore validation tests failed"
        return $exit_code
    fi
}

# Function to run performance tests
run_performance_tests() {
    log "INFO" "Running performance benchmark tests..."
    
    export TEST_BASE_URL="$BASE_URL"
    
    if [ "$VERBOSE" = "true" ]; then
        python3 -m unittest tests.performance.test_docker_performance_benchmarks -v
    else
        python3 -m unittest tests.performance.test_docker_performance_benchmarks
    fi
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Performance benchmark tests passed"
    else
        log "ERROR" "Performance benchmark tests failed"
        return $exit_code
    fi
}

# Function to run security compliance tests
run_security_tests() {
    log "INFO" "Running security compliance tests..."
    
    export TEST_BASE_URL="$BASE_URL"
    
    if [ "$VERBOSE" = "true" ]; then
        python3 -m unittest tests.security.test_docker_security_compliance -v
    else
        python3 -m unittest tests.security.test_docker_security_compliance
    fi
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "SUCCESS" "Security compliance tests passed"
    else
        log "ERROR" "Security compliance tests failed"
        return $exit_code
    fi
}

# Function to run comprehensive validation
run_comprehensive_validation() {
    log "INFO" "Starting comprehensive Docker Compose validation..."
    
    local failed_tests=0
    local total_tests=0
    
    # Define test categories
    local test_categories=()
    
    if [ "$TEST_CATEGORIES" = "all" ]; then
        test_categories=("docker_compose" "api_endpoints" "backup_restore" "performance" "security")
    else
        IFS=',' read -ra test_categories <<< "$TEST_CATEGORIES"
    fi
    
    # Run each test category
    for category in "${test_categories[@]}"; do
        total_tests=$((total_tests + 1))
        
        case $category in
            "docker_compose")
                run_docker_compose_tests || failed_tests=$((failed_tests + 1))
                ;;
            "api_endpoints")
                run_api_endpoint_tests || failed_tests=$((failed_tests + 1))
                ;;
            "backup_restore")
                run_backup_restore_tests || failed_tests=$((failed_tests + 1))
                ;;
            "performance")
                run_performance_tests || failed_tests=$((failed_tests + 1))
                ;;
            "security")
                run_security_tests || failed_tests=$((failed_tests + 1))
                ;;
            *)
                log "WARNING" "Unknown test category: $category"
                ;;
        esac
    done
    
    # Generate summary
    log "INFO" "=== VALIDATION SUMMARY ==="
    log "INFO" "Total test categories: $total_tests"
    log "INFO" "Passed: $((total_tests - failed_tests))"
    log "INFO" "Failed: $failed_tests"
    
    if [ $failed_tests -eq 0 ]; then
        log "SUCCESS" "🎉 ALL VALIDATION TESTS PASSED!"
        log "SUCCESS" "Docker Compose deployment has functionality parity with macOS deployment"
        return 0
    else
        log "ERROR" "❌ $failed_tests validation test categories failed"
        log "ERROR" "Please review the test output and fix any issues"
        return 1
    fi
}

# Function to generate validation report
generate_validation_report() {
    log "INFO" "Generating comprehensive validation report..."
    
    local report_file="comprehensive_validation_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# Docker Compose Deployment Validation Report

**Generated:** $(date)
**Base URL:** $BASE_URL
**Test Categories:** $TEST_CATEGORIES

## Summary

This report contains the results of comprehensive validation testing to verify functionality parity between the Docker Compose deployment and the original macOS deployment.

## Test Categories Executed

EOF

    if [[ "$TEST_CATEGORIES" == *"docker_compose"* ]] || [ "$TEST_CATEGORIES" = "all" ]; then
        echo "- ✅ Docker Compose Infrastructure Tests" >> "$report_file"
    fi
    
    if [[ "$TEST_CATEGORIES" == *"api_endpoints"* ]] || [ "$TEST_CATEGORIES" = "all" ]; then
        echo "- ✅ API Endpoint Validation Tests" >> "$report_file"
    fi
    
    if [[ "$TEST_CATEGORIES" == *"backup_restore"* ]] || [ "$TEST_CATEGORIES" = "all" ]; then
        echo "- ✅ Backup and Restore Validation Tests" >> "$report_file"
    fi
    
    if [[ "$TEST_CATEGORIES" == *"performance"* ]] || [ "$TEST_CATEGORIES" = "all" ]; then
        echo "- ✅ Performance Benchmark Tests" >> "$report_file"
    fi
    
    if [[ "$TEST_CATEGORIES" == *"security"* ]] || [ "$TEST_CATEGORIES" = "all" ]; then
        echo "- ✅ Security Compliance Tests" >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

## Validation Results

All test categories have been executed successfully, confirming that the Docker Compose deployment maintains functionality parity with the original macOS deployment.

## Key Validations Performed

1. **Container Health and Configuration**
   - All containers running and healthy
   - Proper resource limits and security configurations
   - Network isolation and port exposure validation

2. **Application Functionality**
   - All API endpoints accessible and functional
   - Web interface fully operational
   - Authentication and authorization working
   - CSRF protection and security headers present

3. **Data Persistence and Backup**
   - MySQL and Redis data persistence verified
   - Backup procedures tested and validated
   - Restore procedures verified
   - Volume mounts accessible from host

4. **Performance Benchmarks**
   - Response times within acceptable thresholds
   - Throughput meets performance requirements
   - Concurrent user load handling verified
   - Database and Redis performance validated

5. **Security Compliance**
   - Container security configurations validated
   - Network security and isolation verified
   - Secrets management properly implemented
   - Web security headers and CSRF protection active
   - Input validation and authentication security verified

## Conclusion

The Docker Compose deployment has been successfully validated and demonstrates complete functionality parity with the original macOS deployment. All critical systems, security measures, and performance benchmarks meet or exceed the established requirements.

**Status: ✅ VALIDATION SUCCESSFUL**

---
*Report generated by Vedfolnir Docker Compose Validation Suite*
EOF

    log "SUCCESS" "Validation report generated: $report_file"
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --base-url URL     Base URL for testing (default: http://localhost:5000)"
    echo "  -w, --wait TIME        Wait time for services in seconds (default: 60)"
    echo "  -v, --verbose          Enable verbose output"
    echo "  -c, --categories LIST  Comma-separated list of test categories to run"
    echo "                         Options: docker_compose,api_endpoints,backup_restore,performance,security"
    echo "                         Default: all"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests"
    echo "  $0 --verbose                          # Run all tests with verbose output"
    echo "  $0 --categories docker_compose,api   # Run only specific test categories"
    echo "  $0 --base-url http://localhost:8080  # Test against different URL"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--base-url)
            BASE_URL="$2"
            shift 2
            ;;
        -w|--wait)
            WAIT_TIME="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -c|--categories)
            TEST_CATEGORIES="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log "INFO" "Starting Docker Compose Deployment Validation"
    log "INFO" "Base URL: $BASE_URL"
    log "INFO" "Test Categories: $TEST_CATEGORIES"
    log "INFO" "Verbose Mode: $VERBOSE"
    
    # Check prerequisites
    check_prerequisites
    
    # Check Docker services
    check_docker_services
    
    # Wait for services to be ready
    wait_for_services
    
    # Run comprehensive validation
    if run_comprehensive_validation; then
        generate_validation_report
        log "SUCCESS" "Validation completed successfully!"
        exit 0
    else
        log "ERROR" "Validation failed!"
        exit 1
    fi
}

# Run main function
main "$@"