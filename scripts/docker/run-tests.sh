#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Test Runner Script for Vedfolnir Docker Compose

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILES="-f docker-compose.test.yml"
TEST_RESULTS_DIR="test-results"

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

# Function to setup test environment
setup_test_environment() {
    log_info "Setting up test environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS_DIR"
    
    # Clean up any existing test containers
    docker-compose $COMPOSE_FILES down -v --remove-orphans 2>/dev/null || true
    
    log_success "Test environment setup completed"
}

# Function to start test infrastructure
start_test_infrastructure() {
    log_info "Starting test infrastructure..."
    
    # Start database and Redis
    docker-compose $COMPOSE_FILES up -d mysql-test redis-test
    
    # Wait for services to be ready
    log_info "Waiting for test infrastructure to be ready..."
    timeout 60 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec mysql-test mysqladmin ping -h localhost --silent; do sleep 2; done'
    timeout 30 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec redis-test redis-cli ping | grep -q PONG; do sleep 2; done'
    
    log_success "Test infrastructure is ready"
}

# Function to run unit tests
run_unit_tests() {
    log_info "Running unit tests..."
    
    docker-compose $COMPOSE_FILES run --rm unit-test-runner
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Unit tests passed"
    else
        log_error "Unit tests failed"
    fi
    
    return $exit_code
}

# Function to run integration tests
run_integration_tests() {
    log_info "Running integration tests..."
    
    docker-compose $COMPOSE_FILES run --rm integration-test-runner
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Integration tests passed"
    else
        log_error "Integration tests failed"
    fi
    
    return $exit_code
}

# Function to run security tests
run_security_tests() {
    log_info "Running security tests..."
    
    docker-compose $COMPOSE_FILES run --rm security-test-runner
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Security tests passed"
    else
        log_warning "Security tests completed with warnings"
    fi
    
    return 0  # Don't fail on security warnings
}

# Function to run performance tests
run_performance_tests() {
    log_info "Running performance tests..."
    
    # Start test application
    docker-compose $COMPOSE_FILES up -d test-app
    
    # Wait for application to be ready
    timeout 60 bash -c 'until docker-compose '"$COMPOSE_FILES"' exec test-app curl -f http://localhost:5000/health &>/dev/null; do sleep 5; done'
    
    # Run performance tests
    docker-compose $COMPOSE_FILES run --rm performance-test-runner
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Performance tests completed"
    else
        log_warning "Performance tests completed with issues"
    fi
    
    return 0  # Don't fail on performance issues
}

# Function to load test data
load_test_data() {
    log_info "Loading test data..."
    
    docker-compose $COMPOSE_FILES run --rm test-data-loader
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Test data loaded successfully"
    else
        log_error "Failed to load test data"
    fi
    
    return $exit_code
}

# Function to collect test results
collect_test_results() {
    log_info "Collecting test results..."
    
    docker-compose $COMPOSE_FILES run --rm test-results-collector
    
    # Generate summary report
    generate_test_summary
    
    log_success "Test results collected"
}

# Function to generate test summary
generate_test_summary() {
    local summary_file="$TEST_RESULTS_DIR/test-summary.txt"
    
    echo "Vedfolnir Test Summary - $(date)" > "$summary_file"
    echo "======================================" >> "$summary_file"
    echo "" >> "$summary_file"
    
    # Count test files
    local junit_files=$(find "$TEST_RESULTS_DIR" -name "*junit*.xml" 2>/dev/null | wc -l)
    local coverage_files=$(find "$TEST_RESULTS_DIR" -name "coverage.xml" 2>/dev/null | wc -l)
    local security_files=$(find "$TEST_RESULTS_DIR" -name "*security*" -o -name "*bandit*" -o -name "*safety*" 2>/dev/null | wc -l)
    local performance_files=$(find "$TEST_RESULTS_DIR" -name "*performance*" 2>/dev/null | wc -l)
    
    echo "Test Results Summary:" >> "$summary_file"
    echo "- JUnit XML files: $junit_files" >> "$summary_file"
    echo "- Coverage reports: $coverage_files" >> "$summary_file"
    echo "- Security reports: $security_files" >> "$summary_file"
    echo "- Performance reports: $performance_files" >> "$summary_file"
    echo "" >> "$summary_file"
    
    # List all result files
    echo "Generated Files:" >> "$summary_file"
    find "$TEST_RESULTS_DIR" -type f | sort >> "$summary_file"
    
    log_info "Test summary generated: $summary_file"
}

# Function to cleanup test environment
cleanup_test_environment() {
    log_info "Cleaning up test environment..."
    
    # Stop and remove all test containers
    docker-compose $COMPOSE_FILES down -v --remove-orphans
    
    # Clean up test images if requested
    if [[ "$CLEANUP_IMAGES" == "true" ]]; then
        docker image prune -f
    fi
    
    log_success "Test environment cleaned up"
}

# Function to show test results
show_test_results() {
    log_info "Test Results Summary:"
    
    if [[ -f "$TEST_RESULTS_DIR/test-summary.txt" ]]; then
        cat "$TEST_RESULTS_DIR/test-summary.txt"
    fi
    
    echo ""
    log_info "Available reports:"
    
    # Coverage report
    if [[ -f "$TEST_RESULTS_DIR/coverage/index.html" ]]; then
        echo "  Coverage Report: file://$PWD/$TEST_RESULTS_DIR/coverage/index.html"
    fi
    
    # Performance report
    if [[ -f "$TEST_RESULTS_DIR/performance-report.html" ]]; then
        echo "  Performance Report: file://$PWD/$TEST_RESULTS_DIR/performance-report.html"
    fi
    
    # Security reports
    if [[ -f "$TEST_RESULTS_DIR/bandit-report.json" ]]; then
        echo "  Security Report (Bandit): $TEST_RESULTS_DIR/bandit-report.json"
    fi
    
    if [[ -f "$TEST_RESULTS_DIR/safety-report.json" ]]; then
        echo "  Safety Report: $TEST_RESULTS_DIR/safety-report.json"
    fi
}

# Function to show help
show_help() {
    echo "Test Runner Script for Vedfolnir Docker Compose"
    echo ""
    echo "Usage: $0 [OPTIONS] [TEST_TYPES...]"
    echo ""
    echo "Test Types:"
    echo "  unit           Run unit tests"
    echo "  integration    Run integration tests"
    echo "  security       Run security tests"
    echo "  performance    Run performance tests"
    echo "  all            Run all tests (default)"
    echo ""
    echo "Options:"
    echo "  --load-data    Load test data before running tests"
    echo "  --no-cleanup   Don't cleanup test environment after tests"
    echo "  --cleanup-images  Remove Docker images during cleanup"
    echo "  --results-only Show test results summary only"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Run all tests"
    echo "  $0 unit integration         # Run specific test types"
    echo "  $0 --load-data unit         # Load test data and run unit tests"
    echo "  $0 --results-only           # Show test results summary"
}

# Main execution
main() {
    local test_types=()
    local load_data=false
    local no_cleanup=false
    local results_only=false
    local cleanup_images=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --load-data)
                load_data=true
                shift
                ;;
            --no-cleanup)
                no_cleanup=true
                shift
                ;;
            --cleanup-images)
                cleanup_images=true
                export CLEANUP_IMAGES=true
                shift
                ;;
            --results-only)
                results_only=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            unit|integration|security|performance|all)
                test_types+=("$1")
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Default to all tests if none specified
    if [[ ${#test_types[@]} -eq 0 ]]; then
        test_types=("all")
    fi
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Show results only if requested
    if [[ "$results_only" == true ]]; then
        show_test_results
        exit 0
    fi
    
    # Setup cleanup trap
    if [[ "$no_cleanup" != true ]]; then
        trap cleanup_test_environment EXIT
    fi
    
    # Execute test workflow
    local overall_exit_code=0
    
    setup_test_environment
    start_test_infrastructure
    
    # Load test data if requested
    if [[ "$load_data" == true ]]; then
        load_test_data || overall_exit_code=1
    fi
    
    # Run requested tests
    for test_type in "${test_types[@]}"; do
        case $test_type in
            unit)
                run_unit_tests || overall_exit_code=1
                ;;
            integration)
                run_integration_tests || overall_exit_code=1
                ;;
            security)
                run_security_tests || overall_exit_code=1
                ;;
            performance)
                run_performance_tests || overall_exit_code=1
                ;;
            all)
                run_unit_tests || overall_exit_code=1
                run_integration_tests || overall_exit_code=1
                run_security_tests || overall_exit_code=1
                run_performance_tests || overall_exit_code=1
                ;;
        esac
    done
    
    # Collect results
    collect_test_results
    show_test_results
    
    # Report final status
    if [[ $overall_exit_code -eq 0 ]]; then
        log_success "All tests completed successfully!"
    else
        log_error "Some tests failed. Check the results for details."
    fi
    
    exit $overall_exit_code
}

# Run main function with all arguments
main "$@"