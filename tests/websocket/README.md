# WebSocket CORS Standardization Test Suite

This directory contains a comprehensive test suite for the WebSocket CORS standardization system, providing thorough validation of all components through unit tests, integration tests, network simulation, and performance testing.

## Test Structure

### Test Files

- **`test_websocket_cors_comprehensive.py`** - Main comprehensive test suite with unit tests for all core components
- **`test_websocket_integration_scenarios.py`** - End-to-end integration tests for WebSocket connection scenarios
- **`test_websocket_network_simulation.py`** - Network condition simulation and error recovery testing
- **`test_websocket_performance_load.py`** - Performance and load testing for connection throughput and memory usage
- **`run_comprehensive_websocket_tests.py`** - Comprehensive test runner with categorized execution and detailed reporting

### Test Categories

#### 1. Unit Tests
Tests individual WebSocket components in isolation:
- **WebSocketConfigManager** - Configuration loading, validation, and environment variable parsing
- **CORSManager** - Origin validation, protocol detection, and localhost variant handling
- **WebSocketAuthHandler** - Authentication, authorization, rate limiting, and security event logging
- **WebSocketFactory** - SocketIO instance creation, namespace configuration, and error handling

#### 2. Integration Tests
End-to-end testing of WebSocket connection scenarios:
- **Connection Scenarios** - Complete connection flow from configuration to SocketIO instance
- **Namespace Integration** - User and admin namespace setup and authentication
- **Authentication Flow** - Complete authentication flow from session to context
- **Cross-Browser Compatibility** - Browser-specific origin handling and transport fallback

#### 3. CORS Tests
CORS-specific testing with multiple origin configurations:
- **Multiple Origins** - Explicit origin configuration and wildcard handling
- **Environment-Based Origins** - Development vs production origin generation
- **Custom Host Origins** - Dynamic origin generation for custom hosts
- **Edge Cases** - Origin validation edge cases and error handling

#### 4. Network Simulation Tests
Network condition simulation and error recovery:
- **Connection Failures** - Intermittent connection failures and timeout scenarios
- **Transport Fallback** - WebSocket to polling fallback and invalid transport handling
- **Resilience Testing** - Rate limiting under attack and distributed attack simulation
- **Latency Simulation** - High network latency and variable latency handling

#### 5. Performance Tests
Performance and load testing:
- **Configuration Performance** - Configuration loading and CORS validation throughput
- **Authentication Performance** - Authentication throughput and concurrent authentication
- **Factory Performance** - SocketIO instance creation and configuration validation
- **Memory Usage** - Memory leak detection and sustained load stability

## Running Tests

### Quick Start

Run all tests:
```bash
python tests/websocket/run_comprehensive_websocket_tests.py
```

### Category-Specific Testing

Run specific test categories:
```bash
# Unit tests only
python tests/websocket/run_comprehensive_websocket_tests.py --categories unit

# Integration and CORS tests
python tests/websocket/run_comprehensive_websocket_tests.py --categories integration cors

# Performance tests only
python tests/websocket/run_comprehensive_websocket_tests.py --categories performance
```

### Individual Test Files

Run individual test files:
```bash
# Comprehensive unit tests
python tests/websocket/test_websocket_cors_comprehensive.py

# Integration scenarios
python tests/websocket/test_websocket_integration_scenarios.py

# Network simulation
python tests/websocket/test_websocket_network_simulation.py

# Performance testing
python tests/websocket/test_websocket_performance_load.py
```

### Test Runner Options

```bash
# List available categories
python tests/websocket/run_comprehensive_websocket_tests.py --list-categories

# Adjust verbosity (0=quiet, 1=normal, 2=verbose)
python tests/websocket/run_comprehensive_websocket_tests.py --verbosity 1

# Run specific categories with custom verbosity
python tests/websocket/run_comprehensive_websocket_tests.py --categories unit integration --verbosity 2
```

## Test Requirements

### Dependencies

The test suite requires the following dependencies:
- `unittest` (built-in)
- `psutil` (for memory and CPU monitoring)
- `flask` and `flask-socketio` (for WebSocket testing)
- All WebSocket CORS standardization components

### Environment Setup

Tests can run with minimal environment setup, but some tests benefit from specific configurations:

```bash
# Optional environment variables for enhanced testing
export FLASK_HOST=localhost
export FLASK_PORT=5000
export SOCKETIO_CORS_ORIGINS=http://localhost:3000,https://app.example.com
export SOCKETIO_TRANSPORTS=websocket,polling
export SOCKETIO_PING_TIMEOUT=60
export SOCKETIO_PING_INTERVAL=25
```

### Mock Dependencies

The test suite uses extensive mocking for external dependencies:
- **Database connections** - Mocked to avoid requiring actual database setup
- **Redis sessions** - Mocked to avoid requiring Redis server
- **Network requests** - Mocked to simulate various network conditions
- **System resources** - Real monitoring with `psutil` for performance tests

## Test Coverage

### Functional Coverage

- ✅ **Configuration Management** - Environment variable parsing, validation, fallback handling
- ✅ **CORS Origin Handling** - Dynamic origin generation, protocol detection, validation
- ✅ **Authentication & Authorization** - Session validation, role-based access, rate limiting
- ✅ **WebSocket Factory** - SocketIO instance creation, namespace setup, error handling
- ✅ **Integration Scenarios** - End-to-end connection flows, cross-component integration
- ✅ **Error Recovery** - Network failures, service degradation, graceful fallback
- ✅ **Performance & Scalability** - Load testing, memory usage, concurrent operations

### Requirements Validation

The test suite validates all requirements from the WebSocket CORS standardization specification:

- **Requirement 1** - Dynamic CORS Configuration ✅
- **Requirement 2** - Unified Socket.IO Configuration ✅
- **Requirement 3** - Environment-Based Configuration Management ✅
- **Requirement 4** - Robust CORS Error Handling ✅
- **Requirement 5** - Standardized Client Connection Logic ✅
- **Requirement 6** - Enhanced Security and Authentication ✅
- **Requirement 7** - Comprehensive Error Recovery ✅
- **Requirement 8** - Real-Time Notification Standardization ✅
- **Requirement 9** - Development and Debugging Support ✅
- **Requirement 10** - Performance and Scalability ✅

## Performance Benchmarks

### Expected Performance Metrics

The test suite validates the following performance benchmarks:

#### Configuration Performance
- **Configuration Loading**: < 50ms average response time
- **CORS Validation**: < 5ms average response time, > 500 validations/second
- **Memory Efficiency**: < 5MB per configuration manager instance

#### Authentication Performance
- **Authentication Throughput**: < 100ms average response time, > 10 authentications/second
- **Concurrent Authentication**: < 200ms average response time, > 5 concurrent auths/second
- **Rate Limiting**: < 10ms average response time, > 200 rate limit checks/second

#### Memory Usage
- **Memory Leak Prevention**: < 50MB increase after 100 configuration cycles
- **Memory Recovery**: > 80% memory recovery after cleanup
- **Sustained Load Stability**: < 50MB memory trend over sustained operations

## Troubleshooting

### Common Issues

#### Test Failures
1. **Configuration Tests Failing**
   - Check environment variables are not conflicting
   - Ensure no other processes are using test ports
   - Verify all required dependencies are installed

2. **Performance Tests Failing**
   - Performance thresholds may need adjustment for slower systems
   - Ensure system is not under heavy load during testing
   - Check available memory and CPU resources

3. **Network Simulation Tests Failing**
   - Some tests use timing-sensitive operations
   - Ensure system clock is accurate
   - Check for interference from network monitoring tools

#### Memory Issues
- Run `gc.collect()` between test iterations if memory usage is high
- Monitor system memory usage with `htop` or similar tools
- Adjust performance test thresholds for systems with limited memory

### Debug Mode

Enable debug logging for detailed test execution information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Isolation

Each test is designed to be isolated and can run independently:
- Tests clean up their own resources
- Mock objects are reset between tests
- Environment variables are restored after tests

## Contributing

### Adding New Tests

When adding new tests to the WebSocket test suite:

1. **Follow Naming Conventions**
   - Test files: `test_websocket_*.py`
   - Test classes: `TestWebSocket*`
   - Test methods: `test_*`

2. **Use Appropriate Test Category**
   - Unit tests for individual components
   - Integration tests for cross-component scenarios
   - Performance tests for load and throughput validation

3. **Include Proper Documentation**
   - Docstrings for test classes and methods
   - Comments explaining complex test scenarios
   - Performance benchmark documentation

4. **Mock External Dependencies**
   - Use `unittest.mock` for database and network dependencies
   - Provide realistic mock responses
   - Test both success and failure scenarios

### Test Quality Guidelines

- **Comprehensive Coverage** - Test both happy path and edge cases
- **Performance Awareness** - Include performance assertions where appropriate
- **Error Handling** - Test error conditions and recovery scenarios
- **Documentation** - Clear test descriptions and expected outcomes
- **Isolation** - Tests should not depend on external state or other tests

## License

This test suite is part of the Vedfolnir project and is licensed under the GNU Affero General Public License v3.0.