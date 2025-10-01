# Docker Compose Integration Tests

This directory contains comprehensive integration tests for the Docker Compose deployment of Vedfolnir. These tests verify that all services work correctly in the containerized environment and maintain performance parity with the macOS deployment.

## Test Coverage

### 1. Service Interactions (`test_service_interactions.py`)
- Container health checks and status verification
- Database connectivity from application containers
- Redis connectivity and session management
- Nginx reverse proxy functionality
- Prometheus metrics collection
- Grafana dashboard access
- Vault secrets management integration
- Loki log aggregation
- Service network isolation
- Volume persistence and data integrity
- Resource limits and container performance
- Service startup dependencies

### 2. ActivityPub Platform Integration (`test_activitypub_integration.py`)
- Pixelfed post fetching in containerized environment
- Mastodon post fetching in containerized environment
- Caption publishing to ActivityPub platforms
- Platform connection validation
- API calls from containers to external platforms
- Platform credential encryption/decryption
- Multi-platform batch processing
- Platform rate limiting
- ActivityPub webhook handling
- Platform error handling and recovery

### 3. Ollama Integration (`test_ollama_integration.py`)
- Connectivity from containers to external Ollama service
- LLaVA model availability and access
- Caption generation from containerized app to external Ollama
- API timeout handling and configuration
- Error handling for Ollama service failures
- Batch processing with Ollama
- Model switching capabilities
- Performance metrics collection
- WebSocket progress updates for caption generation
- Configuration management for container-to-host communication
- Health monitoring of external Ollama service

### 4. WebSocket Functionality (`test_websocket_functionality.py`)
- WebSocket connection establishment in containers
- Real-time progress updates during caption generation
- Real-time notifications and messaging
- Session-specific WebSocket management
- WebSocket error handling and recovery
- Authentication for WebSocket connections
- Concurrent WebSocket connections
- WebSocket performance in containerized environment
- Nginx proxy compatibility for WebSocket connections

### 5. Performance Benchmarks (`test_performance_benchmarks.py`)
- Web interface response time benchmarking
- Database query performance validation
- Concurrent request handling capacity
- Memory usage monitoring and limits
- API endpoint performance testing
- Static file serving performance
- Session management performance with Redis
- Container resource efficiency analysis
- Performance parity validation with macOS deployment

## Prerequisites

### Docker Compose Services
Ensure Docker Compose services are running before executing tests:

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check service health
docker-compose exec vedfolnir curl -f http://localhost:5000/health
```

### External Dependencies
- **Ollama Service**: Must be running on host system at `localhost:11434`
- **LLaVA Model**: Must be available in Ollama (`ollama pull llava:7b`)
- **Network Access**: Containers must be able to access `host.docker.internal:11434`

## Running Tests

### Quick Test Execution
```bash
# Navigate to test directory
cd tests/integration/docker_compose

# Run all integration tests
python run_integration_tests.py

# Run with verbose output
python run_integration_tests.py --verbose

# Run specific test module
python run_integration_tests.py --test service_interactions

# Run tests matching pattern
python run_integration_tests.py --pattern "ollama"
```

### Individual Test Modules
```bash
# Service interactions
python -m unittest test_service_interactions -v

# ActivityPub integration
python -m unittest test_activitypub_integration -v

# Ollama integration
python -m unittest test_ollama_integration -v

# WebSocket functionality
python -m unittest test_websocket_functionality -v

# Performance benchmarks
python -m unittest test_performance_benchmarks -v
```

### Using Docker Compose Test Environment
```bash
# Run tests in isolated test environment
docker-compose -f docker-compose.test.yml up --build

# Run specific test in container
docker-compose -f docker-compose.test.yml run test-runner python -m unittest test_service_interactions -v

# Clean up test environment
docker-compose -f docker-compose.test.yml down -v
```

## Test Configuration

### Environment Variables
```bash
# Test configuration
TESTING=true
DATABASE_URL=mysql+pymysql://test:test@mysql-test:3306/vedfolnir_test
REDIS_URL=redis://redis-test:6379/0
OLLAMA_URL=http://host.docker.internal:11434
FLASK_ENV=testing
LOG_LEVEL=DEBUG
```

### Performance Thresholds
The performance tests use the following thresholds to ensure parity with macOS deployment:

- **Response Time (95th percentile)**: < 2.0 seconds
- **Response Time (average)**: < 0.5 seconds
- **Throughput**: > 10 requests/second
- **Database Query Time**: < 0.1 seconds
- **Memory Usage**: < 2048 MB
- **CPU Usage**: < 80%

### Network Configuration
Tests use isolated Docker networks to verify:
- Internal service communication
- External API access (Ollama)
- Network security and isolation
- Port exposure and proxy functionality

## Test Data Management

### Mock Data Creation
Tests use the `tests.test_helpers` module for consistent test data:
- Mock users with platform connections
- Test posts and images
- Encrypted platform credentials
- Session data and authentication

### Cleanup Procedures
All tests include proper cleanup:
- Database test data removal
- Redis session cleanup
- WebSocket connection termination
- Container resource cleanup

## Troubleshooting

### Common Issues

#### Services Not Ready
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs vedfolnir
docker-compose logs mysql
docker-compose logs redis

# Restart services
docker-compose restart
```

#### Database Connection Issues
```bash
# Check MySQL container
docker-compose exec mysql mysql -u vedfolnir -p -e "SELECT 1"

# Verify database configuration
docker-compose exec vedfolnir env | grep DATABASE_URL
```

#### Redis Connection Issues
```bash
# Check Redis container
docker-compose exec redis redis-cli ping

# Verify Redis configuration
docker-compose exec vedfolnir env | grep REDIS_URL
```

#### Ollama Integration Issues
```bash
# Check external Ollama service
curl http://localhost:11434/api/version

# Test from container
docker-compose exec vedfolnir curl http://host.docker.internal:11434/api/version

# Check available models
curl http://localhost:11434/api/tags
```

#### WebSocket Connection Issues
```bash
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:5000/ws/progress

# Verify Nginx WebSocket proxy configuration
docker-compose exec nginx nginx -t
```

### Performance Issues
```bash
# Monitor container resources
docker stats

# Check application metrics
curl http://localhost:5000/api/system/metrics

# Monitor database performance
docker-compose exec mysql mysqladmin processlist

# Check Redis performance
docker-compose exec redis redis-cli info stats
```

## Continuous Integration

### GitHub Actions Integration
```yaml
name: Docker Compose Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start Docker Compose services
        run: docker-compose up -d
      
      - name: Wait for services
        run: sleep 30
      
      - name: Run integration tests
        run: |
          cd tests/integration/docker_compose
          python run_integration_tests.py --verbose
      
      - name: Collect test results
        if: always()
        run: |
          docker-compose logs > docker-compose.log
          docker-compose down -v
```

### Test Reporting
Tests generate detailed reports including:
- Performance metrics and benchmarks
- Service health status
- Error logs and stack traces
- Resource usage statistics
- Network connectivity results

## Contributing

When adding new integration tests:

1. **Follow naming conventions**: `test_*.py` for test files
2. **Include copyright headers**: All files must include AGPL headers
3. **Use test helpers**: Leverage existing mock data utilities
4. **Implement cleanup**: Always clean up test data
5. **Document requirements**: Update this README with new dependencies
6. **Add performance checks**: Include relevant performance validations
7. **Test error conditions**: Include negative test cases
8. **Verify isolation**: Ensure tests don't interfere with each other

### Test Structure Template
```python
class DockerComposeNewFeatureTest(unittest.TestCase):
    """Test new feature in Docker Compose environment"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Initialize test environment
        pass
    
    def setUp(self):
        """Set up test data for each test"""
        # Create test data
        pass
    
    def tearDown(self):
        """Clean up test data"""
        # Clean up test data
        pass
    
    def test_feature_functionality(self):
        """Test feature works correctly in containers"""
        # Test implementation
        pass
```

## Requirements Mapping

This test suite validates the following requirements from the Docker Compose migration specification:

- **9.6**: Automated integration tests for all service interactions
- **9.7**: ActivityPub platform integrations work correctly in containers  
- **9.8**: Ollama integration from containerized application to external host-based service
- **9.9**: WebSocket functionality and real-time features in containers
- **8.3**: Performance benchmarking tests to ensure parity with macOS deployment

All tests are designed to verify that the containerized deployment maintains full functionality and performance parity with the original macOS deployment.