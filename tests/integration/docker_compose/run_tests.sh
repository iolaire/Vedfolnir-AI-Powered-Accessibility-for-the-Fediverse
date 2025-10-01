#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Docker Compose Integration Test Runner Script
# Comprehensive test execution with environment setup and validation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
TEST_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.test.yml"

# Default values
RUN_ALL_TESTS=true
VERBOSE=false
USE_TEST_ENVIRONMENT=false
CLEANUP_AFTER=false
WAIT_TIME=30

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Docker Compose Integration Test Runner

Usage: $0 [OPTIONS] [TEST_NAME]

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -t, --test-env          Use isolated test environment
    -c, --cleanup           Cleanup after tests
    -w, --wait SECONDS      Wait time for services (default: 30)
    --service-tests         Run service interaction tests only
    --activitypub-tests     Run ActivityPub integration tests only
    --ollama-tests          Run Ollama integration tests only
    --websocket-tests       Run WebSocket functionality tests only
    --performance-tests     Run performance benchmark tests only
    --list                  List available tests

EXAMPLES:
    $0                                  # Run all tests
    $0 --verbose                        # Run all tests with verbose output
    $0 --test-env --cleanup            # Run in isolated test environment
    $0 --service-tests                 # Run only service interaction tests
    $0 test_service_interactions       # Run specific test module
    $0 --ollama-tests --verbose        # Run Ollama tests with verbose output

PREREQUISITES:
    - Docker and Docker Compose installed
    - Vedfolnir Docker Compose services running (unless using --test-env)
    - External Ollama service running at localhost:11434
    - LLaVA model available in Ollama

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to check Docker Compose services
check_services() {
    print_status "Checking Docker Compose services..."
    
    if [ "$USE_TEST_ENVIRONMENT" = true ]; then
        print_status "Using isolated test environment"
        return 0
    fi
    
    # Check if main services are running
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        print_warning "Main Docker Compose services are not running"
        print_status "Starting Docker Compose services..."
        
        cd "$PROJECT_ROOT"
        docker-compose up -d
        
        print_status "Waiting ${WAIT_TIME} seconds for services to start..."
        sleep "$WAIT_TIME"
    fi
    
    # Verify services are healthy
    print_status "Verifying service health..."
    
    # Check web application
    for i in {1..30}; do
        if curl -s http://localhost:5000/health > /dev/null 2>&1; then
            print_success "Web application is healthy"
            break
        fi
        
        if [ $i -eq 30 ]; then
            print_error "Web application failed to start"
            exit 1
        fi
        
        sleep 2
    done
    
    print_success "Services are ready"
}

# Function to check external dependencies
check_external_dependencies() {
    print_status "Checking external dependencies..."
    
    # Check Ollama service
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        print_success "External Ollama service is available"
        
        # Check for LLaVA model
        if curl -s http://localhost:11434/api/tags | grep -q "llava"; then
            print_success "LLaVA model is available"
        else
            print_warning "LLaVA model not found in Ollama"
            print_status "Some Ollama tests may be skipped"
        fi
    else
        print_warning "External Ollama service not available at localhost:11434"
        print_status "Ollama integration tests will be skipped"
    fi
}

# Function to run tests in main environment
run_main_tests() {
    print_status "Running tests in main Docker Compose environment..."
    
    cd "$SCRIPT_DIR"
    
    local test_args=""
    
    if [ "$VERBOSE" = true ]; then
        test_args="$test_args --verbose"
    fi
    
    if [ -n "$TEST_PATTERN" ]; then
        test_args="$test_args --test $TEST_PATTERN"
    fi
    
    python run_integration_tests.py $test_args
}

# Function to run tests in isolated test environment
run_test_environment() {
    print_status "Running tests in isolated test environment..."
    
    cd "$SCRIPT_DIR"
    
    # Start test environment
    print_status "Starting test environment..."
    docker-compose -f "$TEST_COMPOSE_FILE" up -d
    
    # Wait for test services
    print_status "Waiting for test services to start..."
    sleep "$WAIT_TIME"
    
    # Run tests in container
    print_status "Executing tests in container..."
    
    local test_cmd="python -m unittest discover tests/integration/docker_compose/ -v"
    
    if [ -n "$TEST_PATTERN" ]; then
        test_cmd="python -m unittest tests.integration.docker_compose.test_${TEST_PATTERN} -v"
    fi
    
    docker-compose -f "$TEST_COMPOSE_FILE" exec -T test-runner $test_cmd
    
    local test_result=$?
    
    # Cleanup test environment if requested
    if [ "$CLEANUP_AFTER" = true ]; then
        print_status "Cleaning up test environment..."
        docker-compose -f "$TEST_COMPOSE_FILE" down -v
    fi
    
    return $test_result
}

# Function to run specific test suite
run_specific_tests() {
    local test_type="$1"
    
    case "$test_type" in
        "service")
            TEST_PATTERN="service_interactions"
            ;;
        "activitypub")
            TEST_PATTERN="activitypub_integration"
            ;;
        "ollama")
            TEST_PATTERN="ollama_integration"
            ;;
        "websocket")
            TEST_PATTERN="websocket_functionality"
            ;;
        "performance")
            TEST_PATTERN="performance_benchmarks"
            ;;
        *)
            print_error "Unknown test type: $test_type"
            exit 1
            ;;
    esac
    
    print_status "Running $test_type tests..."
}

# Function to list available tests
list_tests() {
    print_status "Available test modules:"
    echo "  • test_service_interactions      - Service interaction tests"
    echo "  • test_activitypub_integration   - ActivityPub platform integration tests"
    echo "  • test_ollama_integration        - Ollama AI service integration tests"
    echo "  • test_websocket_functionality   - WebSocket and real-time feature tests"
    echo "  • test_performance_benchmarks    - Performance benchmarking tests"
    echo ""
    print_status "Test suites:"
    echo "  • --service-tests                - Service interaction tests"
    echo "  • --activitypub-tests           - ActivityPub integration tests"
    echo "  • --ollama-tests                - Ollama integration tests"
    echo "  • --websocket-tests             - WebSocket functionality tests"
    echo "  • --performance-tests           - Performance benchmark tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--test-env)
            USE_TEST_ENVIRONMENT=true
            shift
            ;;
        -c|--cleanup)
            CLEANUP_AFTER=true
            shift
            ;;
        -w|--wait)
            WAIT_TIME="$2"
            shift 2
            ;;
        --service-tests)
            run_specific_tests "service"
            shift
            ;;
        --activitypub-tests)
            run_specific_tests "activitypub"
            shift
            ;;
        --ollama-tests)
            run_specific_tests "ollama"
            shift
            ;;
        --websocket-tests)
            run_specific_tests "websocket"
            shift
            ;;
        --performance-tests)
            run_specific_tests "performance"
            shift
            ;;
        --list)
            list_tests
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            TEST_PATTERN="$1"
            RUN_ALL_TESTS=false
            shift
            ;;
    esac
done

# Main execution
main() {
    print_status "Docker Compose Integration Test Runner"
    print_status "======================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Check services and dependencies
    if [ "$USE_TEST_ENVIRONMENT" = false ]; then
        check_services
        check_external_dependencies
    fi
    
    # Run tests
    local test_result=0
    
    if [ "$USE_TEST_ENVIRONMENT" = true ]; then
        run_test_environment
        test_result=$?
    else
        run_main_tests
        test_result=$?
    fi
    
    # Report results
    if [ $test_result -eq 0 ]; then
        print_success "All tests completed successfully!"
        print_success "Docker Compose integration is working correctly"
    else
        print_error "Some tests failed"
        print_error "Please review the test output above"
    fi
    
    exit $test_result
}

# Run main function
main "$@"