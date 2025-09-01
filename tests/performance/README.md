# Notification System Performance Testing Suite

This directory contains comprehensive performance and load testing for the notification system, including high-volume notification delivery, concurrent user handling, WebSocket connection scaling, queue management, and graceful degradation testing.

## Test Suites

### 1. Notification Performance Tests (`test_notification_performance.py`)

Tests the core notification system performance under various load conditions:

- **High-Volume Notification Delivery**: Tests delivery of 1000+ notifications in batches
- **Concurrent User Notification Handling**: Tests 20+ concurrent users with 25+ notifications each
- **WebSocket Connection Scaling**: Tests scaling up to 100+ WebSocket connections
- **Notification Queue Management Under Load**: Tests offline queue handling with 200+ messages per user
- **Graceful Degradation Under High Load**: Tests system behavior under extreme load conditions
- **Statistics Collection Performance**: Tests performance of system statistics gathering

**Key Metrics Measured**:
- Notification throughput (notifications/second)
- Average operation time
- Success rates under load
- Memory usage growth
- CPU utilization
- Queue management efficiency

### 2. WebSocket Load Tests (`test_websocket_load.py`)

Tests WebSocket connection performance and scalability:

- **WebSocket Connection Scaling**: Tests creating and managing 50+ concurrent connections
- **Message Throughput**: Tests sending 50+ messages per client across 10+ clients
- **Concurrent User Simulation**: Simulates 15+ users with realistic activity patterns
- **Resource Usage Monitoring**: Monitors memory and CPU usage during WebSocket operations

**Key Metrics Measured**:
- Connection establishment time
- Message send/receive throughput
- Connection success rates
- Memory usage per connection
- Broadcast performance
- Resource utilization

### 3. Memory Usage Tests (`test_memory_usage.py`)

Tests memory efficiency and leak detection:

- **Notification Creation Memory Usage**: Tests memory usage during notification creation
- **Offline Queue Memory Efficiency**: Tests memory efficiency of offline message queues
- **Concurrent Operations Memory Impact**: Tests memory usage during concurrent operations
- **Long-Running Memory Stability**: Tests memory stability over extended periods
- **Garbage Collection Effectiveness**: Tests GC effectiveness with notification objects

**Key Metrics Measured**:
- Memory growth patterns
- Memory per notification/operation
- Memory leak detection
- Garbage collection effectiveness
- Peak memory usage
- Memory stability over time

## Running the Tests

### Prerequisites

1. **Environment Setup**: Ensure your `.env` file is properly configured
2. **Database**: MySQL database should be running and accessible
3. **Dependencies**: Install required packages:
   ```bash
   pip install psutil websocket-client tracemalloc
   ```

### Running Individual Test Suites

```bash
# Run notification performance tests
python -m unittest tests.performance.test_notification_performance -v

# Run WebSocket load tests
python -m unittest tests.performance.test_websocket_load -v

# Run memory usage tests
python -m unittest tests.performance.test_memory_usage -v
```

### Running All Performance Tests

Use the performance test runner for comprehensive testing:

```bash
# Run all performance tests
python tests/performance/run_performance_tests.py

# Run specific test suites
python tests/performance/run_performance_tests.py --suites notification websocket

# Generate detailed JSON report
python tests/performance/run_performance_tests.py --output performance_report.json

# Run with verbose output
python tests/performance/run_performance_tests.py --verbose
```

### Test Runner Options

- `--suites`: Specify which test suites to run (`notification`, `websocket`, `memory`, `all`)
- `--output`: Generate detailed JSON report to specified file
- `--verbose`: Enable verbose output for debugging

## Performance Benchmarks

### Expected Performance Targets

#### Notification System
- **Throughput**: > 100 notifications/second
- **Operation Time**: < 100ms average per notification
- **Success Rate**: > 95% under normal load, > 70% under extreme load
- **Memory Usage**: < 10KB per notification
- **Concurrent Users**: Support 20+ concurrent users

#### WebSocket Connections
- **Connection Time**: < 2 seconds average
- **Connection Success Rate**: > 80%
- **Message Throughput**: > 100 messages/second
- **Memory per Connection**: < 1MB
- **Broadcast Time**: < 1 second for 50+ connections

#### Memory Efficiency
- **Memory Growth Rate**: < 0.5MB/second for long-running operations
- **Memory per Queued Message**: < 15KB
- **GC Effectiveness**: > 5% memory recovery
- **Memory Leak Detection**: No significant leaks detected

## Test Configuration

### Adjusting Test Parameters

Test parameters can be modified in each test file:

```python
# In test_notification_performance.py
notification_count = 1000  # Number of notifications to test
concurrent_users = 20      # Number of concurrent users
batch_size = 50           # Batch size for operations

# In test_websocket_load.py
max_connections = 50      # Maximum WebSocket connections
messages_per_client = 50  # Messages per client for throughput testing
concurrent_users = 15     # Concurrent users for simulation

# In test_memory_usage.py
stress_notifications = 500  # Notifications for stress testing
test_duration = 30         # Duration for long-running tests (seconds)
offline_users = 10         # Users for offline queue testing
```

### Environment Variables

Performance tests respect these environment variables:

```bash
# Database configuration
DATABASE_URL=mysql+pymysql://user:password@localhost/vedfolnir_test

# WebSocket configuration
SOCKETIO_REQUIRE_AUTH=false  # Disable auth for testing
CORS_ALLOWED_ORIGINS=*       # Allow all origins for testing

# Performance tuning
DB_POOL_SIZE=20             # Database connection pool size
DB_MAX_OVERFLOW=30          # Maximum overflow connections
```

## Interpreting Results

### Success Criteria

Tests are considered successful when:

1. **All assertions pass**: Performance targets are met
2. **No memory leaks detected**: Memory growth is within acceptable limits
3. **High success rates**: > 95% success rate for normal operations
4. **Stable performance**: Consistent performance across test runs

### Common Issues and Solutions

#### High Memory Usage
- **Cause**: Memory leaks or inefficient object management
- **Solution**: Review object lifecycle, ensure proper cleanup, force garbage collection

#### Low Throughput
- **Cause**: Database bottlenecks, inefficient algorithms, or resource contention
- **Solution**: Optimize database queries, increase connection pool size, review algorithms

#### WebSocket Connection Failures
- **Cause**: CORS issues, authentication problems, or server overload
- **Solution**: Check CORS configuration, verify authentication setup, increase server resources

#### Test Timeouts
- **Cause**: Slow operations or deadlocks
- **Solution**: Increase test timeouts, optimize slow operations, check for deadlocks

## Continuous Integration

### Running in CI/CD

For automated testing in CI/CD pipelines:

```bash
# Run performance tests with timeout and report generation
timeout 300 python tests/performance/run_performance_tests.py \
  --output ci_performance_report.json \
  --suites notification memory

# Check exit code for pass/fail status
if [ $? -eq 0 ]; then
  echo "Performance tests passed"
else
  echo "Performance tests failed"
  exit 1
fi
```

### Performance Regression Detection

Monitor key metrics across builds:
- Notification throughput trends
- Memory usage patterns
- WebSocket connection success rates
- Test execution times

## Troubleshooting

### Common Test Failures

1. **Database Connection Issues**
   ```
   Error: Failed to connect to database
   Solution: Verify DATABASE_URL and ensure MySQL is running
   ```

2. **WebSocket Connection Failures**
   ```
   Error: WebSocket connection timeout
   Solution: Ensure web application is running on http://127.0.0.1:5000
   ```

3. **Memory Test Failures**
   ```
   Error: Memory leak detected
   Solution: Review object lifecycle and garbage collection
   ```

4. **Permission Errors**
   ```
   Error: Access denied for user
   Solution: Verify database user permissions and test user creation
   ```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run specific test with debug output
python -m unittest tests.performance.test_notification_performance.NotificationPerformanceTestSuite.test_high_volume_notification_delivery -v
```

## Contributing

When adding new performance tests:

1. **Follow naming conventions**: `test_*_performance.py`
2. **Include comprehensive metrics**: Throughput, latency, memory usage, success rates
3. **Add proper assertions**: Define clear performance targets
4. **Document test parameters**: Make test parameters configurable
5. **Handle cleanup**: Ensure proper resource cleanup after tests
6. **Update this README**: Document new tests and their purpose

## Performance Monitoring

### Continuous Monitoring

For production monitoring, consider:
- Regular performance test execution
- Automated performance regression detection
- Performance metrics dashboards
- Alerting on performance degradation

### Profiling Tools

Additional profiling tools for deep analysis:
- `cProfile` for CPU profiling
- `memory_profiler` for detailed memory analysis
- `py-spy` for production profiling
- `tracemalloc` for memory allocation tracking

## References

- [Python unittest documentation](https://docs.python.org/3/library/unittest.html)
- [psutil documentation](https://psutil.readthedocs.io/)
- [WebSocket testing best practices](https://websockets.readthedocs.io/en/stable/howto/test.html)
- [Memory profiling in Python](https://docs.python.org/3/library/tracemalloc.html)