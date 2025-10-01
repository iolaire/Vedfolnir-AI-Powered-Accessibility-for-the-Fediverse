# Docker Compose Validation Tools

This directory contains comprehensive validation tools to verify functionality parity between the Docker Compose deployment and the original macOS deployment.

## Overview

The validation suite includes:

1. **Comprehensive Validation Script** - Full end-to-end validation
2. **Individual Component Tests** - Quick testing of specific components
3. **Performance Benchmarks** - Performance testing and comparison
4. **Security Compliance Tests** - Security configuration validation
5. **Backup/Restore Tests** - Data persistence and recovery validation

## Quick Start

### Prerequisites

Ensure you have the required Python packages installed:

```bash
pip install requests docker redis mysql-connector-python psutil
```

### Run Complete Validation

```bash
# Run all validation tests
./scripts/validation/run_comprehensive_validation.sh

# Run with verbose output
./scripts/validation/run_comprehensive_validation.sh --verbose

# Run specific test categories
./scripts/validation/run_comprehensive_validation.sh --categories docker_compose,api_endpoints
```

### Quick Component Check

```bash
# Test all components quickly
python3 scripts/validation/test_individual_components.py

# Test specific component
python3 scripts/validation/test_individual_components.py --component database

# Test with custom URL
python3 scripts/validation/test_individual_components.py --base-url http://localhost:8080
```

## Validation Test Categories

### 1. Docker Compose Infrastructure Tests

**File:** `tests/integration/test_docker_compose_validation.py`

**What it tests:**
- Container health and status
- Service dependencies and startup order
- Network connectivity between services
- Volume mounts and data persistence
- Resource limits and configuration
- Monitoring endpoints (Prometheus, Grafana)

**Run individually:**
```bash
python3 -m unittest tests.integration.test_docker_compose_validation -v
```

### 2. API Endpoint Validation Tests

**File:** `tests/integration/test_api_endpoint_validation.py`

**What it tests:**
- Public endpoints (landing page, health checks, static files)
- Protected endpoints (dashboard, profile, platform management)
- Admin endpoints (user management, system monitoring)
- API functionality and data formats
- WebSocket endpoints
- CSRF protection
- Rate limiting
- Error handling
- Response times

**Run individually:**
```bash
export TEST_BASE_URL=http://localhost:5000
python3 -m unittest tests.integration.test_api_endpoint_validation -v
```

### 3. Backup and Restore Validation Tests

**File:** `tests/integration/test_backup_restore_validation.py`

**What it tests:**
- MySQL database backup and restore procedures
- Redis data backup and restore procedures
- Application data backup (storage, logs, config)
- Backup integrity verification
- Disaster recovery procedures
- Recovery time objectives (RTO)

**Run individually:**
```bash
python3 -m unittest tests.integration.test_backup_restore_validation -v
```

### 4. Performance Benchmark Tests

**File:** `tests/performance/test_docker_performance_benchmarks.py`

**What it tests:**
- Response time benchmarks for key endpoints
- Throughput benchmarks (requests per second)
- Concurrent user load handling
- Database performance in containerized environment
- Redis performance benchmarks
- Memory usage monitoring
- Performance comparison with macOS deployment

**Run individually:**
```bash
export TEST_BASE_URL=http://localhost:5000
python3 -m unittest tests.performance.test_docker_performance_benchmarks -v
```

### 5. Security Compliance Tests

**File:** `tests/security/test_docker_security_compliance.py`

**What it tests:**
- Container security configurations
- Network security and isolation
- Secrets management
- Web security headers
- CSRF protection
- Input validation and sanitization
- Authentication security measures
- Data encryption (in transit and at rest)
- Audit logging capabilities
- GDPR compliance features

**Run individually:**
```bash
export TEST_BASE_URL=http://localhost:5000
python3 -m unittest tests.security.test_docker_security_compliance -v
```

## Usage Examples

### Complete Validation Workflow

```bash
# 1. Start Docker Compose services
docker-compose up -d

# 2. Wait for services to be ready
sleep 60

# 3. Run comprehensive validation
./scripts/validation/run_comprehensive_validation.sh --verbose

# 4. Check results
ls -la *_results_*.json *_report_*.md
```

### Troubleshooting Specific Issues

```bash
# Quick connectivity check
python3 scripts/validation/test_individual_components.py --component connectivity

# Database issues
python3 scripts/validation/test_individual_components.py --component database

# Redis issues
python3 scripts/validation/test_individual_components.py --component redis

# Container status
python3 scripts/validation/test_individual_components.py --component containers
```

### Performance Testing

```bash
# Run performance benchmarks
python3 -m unittest tests.performance.test_docker_performance_benchmarks -v

# Check performance results
cat performance_results_*.json
```

### Security Audit

```bash
# Run security compliance tests
python3 -m unittest tests.security.test_docker_security_compliance -v

# Check security results
cat security_compliance_results_*.json
```

## Configuration Options

### Environment Variables

- `TEST_BASE_URL` - Base URL for testing (default: http://localhost:5000)
- `TEST_ADMIN_USERNAME` - Admin username for protected endpoint testing
- `TEST_ADMIN_PASSWORD` - Admin password for protected endpoint testing
- `REDIS_URL` - Redis connection URL
- `DATABASE_URL` - Database connection URL
- `OLLAMA_URL` - Ollama API URL

### Command Line Options

**Comprehensive Validation Script:**
- `--base-url URL` - Base URL for testing
- `--wait TIME` - Wait time for services in seconds
- `--verbose` - Enable verbose output
- `--categories LIST` - Specific test categories to run

**Individual Component Tests:**
- `--base-url URL` - Base URL for testing
- `--component NAME` - Specific component to test
- `--wait TIME` - Wait time before testing

## Output Files

The validation tools generate several output files:

- `validation_report_YYYYMMDD_HHMMSS.json` - Comprehensive validation results
- `comprehensive_validation_report_YYYYMMDD_HHMMSS.md` - Human-readable report
- `performance_results_YYYYMMDD_HHMMSS.json` - Performance benchmark results
- `security_compliance_results_YYYYMMDD_HHMMSS.json` - Security test results

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Docker Compose Validation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install requests docker redis mysql-connector-python psutil
      
      - name: Start Docker Compose
        run: docker-compose up -d
      
      - name: Run validation
        run: |
          ./scripts/validation/run_comprehensive_validation.sh --wait 120
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: validation-results
          path: |
            *_results_*.json
            *_report_*.md
```

## Troubleshooting

### Common Issues

1. **Services not ready**
   - Increase wait time: `--wait 120`
   - Check container logs: `docker-compose logs`

2. **Database connection failed**
   - Verify MySQL container is running: `docker-compose ps mysql`
   - Check database credentials in environment

3. **Redis connection failed**
   - Verify Redis container is running: `docker-compose ps redis`
   - Check Redis URL configuration

4. **Authentication required for tests**
   - Set `TEST_ADMIN_USERNAME` and `TEST_ADMIN_PASSWORD` environment variables
   - Or create admin user manually

5. **Performance tests failing**
   - Check system resources
   - Adjust performance thresholds in test files

### Debug Mode

Run tests with maximum verbosity:

```bash
# Comprehensive validation with debug output
./scripts/validation/run_comprehensive_validation.sh --verbose

# Individual tests with debug output
python3 -m unittest tests.integration.test_docker_compose_validation -v
```

## Contributing

When adding new validation tests:

1. Follow the existing test structure and naming conventions
2. Include comprehensive docstrings and comments
3. Add appropriate assertions and error handling
4. Update this README with new test descriptions
5. Ensure tests are idempotent and don't interfere with each other

## Requirements Mapping

This validation suite addresses the following requirements from the Docker Compose migration spec:

- **Requirement 1.4**: Validate same functionality as macOS deployment
- **Requirement 8.3**: Performance characteristics validation
- **Requirement 9.4**: Functionality parity verification
- **Requirement 10.4**: Troubleshooting and validation procedures