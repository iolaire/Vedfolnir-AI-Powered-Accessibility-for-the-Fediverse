# Configuration System Integration Tests

This directory contains comprehensive integration tests for the system configuration integration feature. These tests validate the complete configuration flow from Admin UI to application behavior, including performance testing and failure scenario validation.

## Test Structure

### End-to-End Integration Tests (`test_configuration_system_e2e.py`)

Tests the complete configuration flow:
- **Admin UI → Database**: Configuration updates through system manager
- **Database → Service**: Configuration propagation to ConfigurationService
- **Service → Application**: Configuration changes affecting application behavior
- **Change Propagation**: Real-time configuration change notifications
- **Restart Requirements**: Tracking configurations requiring restart
- **Environment Overrides**: Environment variable precedence
- **Schema Defaults**: Fallback to schema defaults
- **Feature Integration**: Feature flags and maintenance mode
- **Validation Integration**: Configuration validation across the system
- **Cache Performance**: Configuration cache behavior
- **Concurrent Access**: Thread-safe configuration access
- **Error Handling**: Graceful error handling throughout the system

### Load Testing (`../performance/test_configuration_system_load.py`)

Performance tests under high load:
- **High-Frequency Access**: 10,000+ configuration requests with multiple threads
- **Cache Performance**: Cache hit rates and memory usage under sustained load
- **Event Bus Performance**: Multiple simultaneous configuration changes
- **Scalability Testing**: Performance at increasing load levels (10-1000 concurrent users)
- **Stress Testing**: Configuration change propagation under stress
- **Memory Usage**: Memory consumption patterns during sustained load

### Failure Scenario Tests (`test_configuration_failure_scenarios.py`)

Tests system behavior under failure conditions:
- **Database Unavailability**: Fallback to environment variables and schema defaults
- **Database Recovery**: System recovery after database outages
- **Cache Failures**: Direct database access when cache fails
- **Partial System Failures**: Data consistency during partial failures
- **Service Adapter Recovery**: Adapter behavior during service outages
- **Event Bus Failures**: Configuration updates continue despite event bus issues
- **Concurrent Failures**: System behavior under multiple simultaneous failures
- **Disaster Recovery**: Complete system recovery scenarios
- **Memory Pressure**: Cache behavior under memory constraints
- **Network Partitions**: Behavior during network connectivity issues
- **Data Corruption**: Detection and handling of corrupted configuration data

## Test Requirements Validation

These tests validate all requirements from the system configuration integration specification:

### Requirement 1: Configuration Service Layer ✅
- Configuration service initialization and cached access
- Environment variable override support
- Schema default fallback
- Restart requirement tracking
- Cache performance optimization

### Requirement 2: Dynamic Configuration Refresh ✅
- Cache invalidation on configuration updates
- Hot-reload configuration support
- Restart requirement warnings
- Configuration refresh signals
- Error handling for refresh failures

### Requirement 3: Task Queue Integration ✅
- Task queue manager configuration reading
- Concurrency limit enforcement
- Job timeout configuration
- Dynamic limit updates
- Queue size limit enforcement

### Requirement 4: Session Management Integration ✅
- Session timeout configuration
- Rate limiting configuration
- Security settings updates
- Audit log retention configuration

### Requirement 5: Alert System Integration ✅
- Alert threshold configuration
- Notification channel updates
- Real-time threshold updates
- Invalid threshold handling

### Requirement 6: Feature Flag Integration ✅
- Feature flag enforcement
- Real-time feature toggling
- Service notification within 30 seconds
- Graceful feature disabling

### Requirement 7: Maintenance Mode Integration ✅
- Maintenance mode control
- Job blocking during maintenance
- Running job completion
- Immediate operation resumption

### Requirement 8: Performance Optimization Integration ✅
- Memory limit enforcement
- Priority weight system
- Performance setting validation
- Resource limit enforcement

### Requirement 9: Configuration Validation and Safety ✅
- Schema rule validation
- Conflict detection
- Impact assessment
- Critical configuration confirmation

### Requirement 10: Monitoring and Observability ✅
- Usage metrics collection
- Cache performance metrics
- Change impact logging
- Error tracking and alerting

### Requirement 11: Backward Compatibility and Migration ✅
- Environment variable precedence
- Schema default fallback
- Service unavailability handling
- Hardcoded value migration

### Requirement 12: Admin Interface Enhancements ✅
- Restart requirement indicators
- Configuration impact warnings
- Dependency highlighting
- Dry-run mode testing

## Running the Tests

### Individual Test Files

```bash
# Run end-to-end integration tests
python -m unittest tests.integration.test_configuration_system_e2e -v

# Run load testing (requires more time)
python -m unittest tests.performance.test_configuration_system_load -v

# Run failure scenario tests
python -m unittest tests.integration.test_configuration_failure_scenarios -v
```

### Comprehensive Test Runner

Use the dedicated test runner for complete validation:

```bash
# Run all configuration integration tests
python tests/scripts/run_configuration_integration_tests.py

# Run specific test suites
python tests/scripts/run_configuration_integration_tests.py e2e load failure

# Run with verbose output
python tests/scripts/run_configuration_integration_tests.py --verbose

# List available test suites
python tests/scripts/run_configuration_integration_tests.py --list

# Exclude specific suites (e.g., skip load tests for faster execution)
python tests/scripts/run_configuration_integration_tests.py --exclude load

# Validate test environment
python tests/scripts/run_configuration_integration_tests.py --validate-env
```

## Test Performance Benchmarks

### Expected Performance Metrics

- **Configuration Access**: < 10ms average, < 100ms maximum
- **Cache Hit Rate**: > 80% under normal load
- **Throughput**: > 100 requests per second
- **Change Propagation**: < 50ms average
- **Memory Growth**: < 50MB during sustained load
- **Event Processing**: < 10ms average publish time

### Load Test Scenarios

1. **High-Frequency Access**: 10,000 requests across 10 threads
2. **Sustained Load**: 30-60 seconds of continuous access
3. **Scalability**: Load levels from 10 to 1,000 concurrent users
4. **Stress Testing**: 500 configuration changes with 20 subscribers per key
5. **Memory Pressure**: Cache eviction under memory constraints

## Failure Scenarios Tested

### Database Failures
- Complete database unavailability
- Intermittent connection failures
- Database recovery after outages
- Transaction commit failures

### Cache Failures
- Cache system corruption
- Cache lock failures
- Memory pressure eviction
- Cache clear failures

### Service Failures
- Configuration service unavailability
- Event bus failures
- Service adapter failures
- Partial system failures

### Network Issues
- Network partitions
- Connection timeouts
- Intermittent connectivity
- Slow network conditions

### Data Issues
- Configuration data corruption
- Invalid configuration values
- Schema validation failures
- Type conversion errors

## Test Environment Requirements

### Dependencies
- Python 3.8+
- unittest framework
- Mock/patch capabilities
- Threading support
- Memory monitoring (psutil)

### Mock Components
- Database manager with session context
- System configuration manager
- Service adapters (task queue, session, alert)
- Feature services (flags, maintenance mode)

### Environment Variables
Tests use environment variable overrides to validate precedence:
- `VEDFOLNIR_CONFIG_*` variables for testing overrides
- No actual database connection required (mocked)
- No Redis connection required (mocked)

## Test Data and Fixtures

### Mock Configurations
- `max_concurrent_jobs`: Integer configuration for task queue testing
- `session_timeout_minutes`: Integer configuration for session testing
- `alert_queue_backup_threshold`: Integer configuration for alert testing
- `enable_batch_processing`: Boolean configuration for feature flag testing
- `maintenance_mode`: Boolean configuration for maintenance mode testing

### Test Users
- Mock admin user with proper role and permissions
- User ID 1 with ADMIN role for authorization testing

### Performance Test Data
- 1,000 test configurations for load testing
- Configurable cache sizes and TTL values
- Adjustable thread counts and request volumes

## Continuous Integration

These tests are designed for CI/CD integration:

### Fast Tests (< 30 seconds)
- End-to-end integration tests
- Failure scenario tests
- Unit tests for individual components

### Extended Tests (30+ seconds)
- Load testing with high request volumes
- Sustained load testing
- Memory usage analysis
- Scalability testing

### Test Categories
- `e2e`: End-to-end integration (fast)
- `failure`: Failure scenarios (fast)
- `load`: Performance and load testing (slow)
- `unit`: Individual component tests (fast)
- `admin`: Admin interface tests (fast)

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure project root is in Python path
2. **Mock Failures**: Verify mock setup matches actual interfaces
3. **Timing Issues**: Adjust timeouts for slower systems
4. **Memory Issues**: Reduce load test parameters on constrained systems

### Debug Mode

Enable verbose output for detailed test information:
```bash
python tests/scripts/run_configuration_integration_tests.py --verbose
```

### Environment Validation

Validate test environment before running tests:
```bash
python tests/scripts/run_configuration_integration_tests.py --validate-env
```

## Contributing

When adding new configuration integration tests:

1. **Follow Naming Convention**: `test_configuration_*` for test files
2. **Use Proper Mocking**: Mock external dependencies consistently
3. **Include Performance Assertions**: Set reasonable performance expectations
4. **Test Error Conditions**: Include failure scenario coverage
5. **Document Requirements**: Map tests to specific requirements
6. **Update Test Runner**: Add new test suites to the runner script

## Test Coverage

These integration tests provide comprehensive coverage of:
- ✅ All 12 requirements from the specification
- ✅ Complete configuration flow (UI → DB → Service → App)
- ✅ Performance under high load (10,000+ requests)
- ✅ Failure scenarios and recovery
- ✅ Concurrent access and thread safety
- ✅ Memory usage and resource management
- ✅ Cache performance and optimization
- ✅ Event propagation and timing
- ✅ Error handling and graceful degradation
- ✅ Environment variable overrides
- ✅ Schema default fallbacks
- ✅ Service adapter integration
- ✅ Feature flag and maintenance mode integration
- ✅ Configuration validation and safety
- ✅ Admin interface integration

This comprehensive test suite ensures the configuration system integration meets all requirements and performs reliably under various conditions.