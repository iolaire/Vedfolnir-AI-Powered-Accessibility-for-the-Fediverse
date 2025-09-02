# WebSocket Debugging Tools

## Overview

This comprehensive suite of debugging tools provides developers with everything needed to diagnose, monitor, and troubleshoot WebSocket connections in the Vedfolnir application. The tools include diagnostic utilities, debug logging, health monitoring, connection monitoring dashboard, and automated testing capabilities.

## Tools Overview

### 1. WebSocket Diagnostic Tools (`websocket_diagnostic_tools.py`)
Comprehensive diagnostic capabilities for WebSocket connections, CORS validation, and performance testing.

### 2. Debug Logger (`websocket_debug_logger.py`)
Advanced debug logging system with configurable verbosity levels and structured output.

### 3. Connection Monitoring Dashboard (`websocket_monitoring_dashboard.py`)
Real-time web-based dashboard for monitoring WebSocket connections and metrics.

### 4. Health Checker (`websocket_health_checker.py`)
Automated health monitoring system with configurable alerts and continuous monitoring.

### 5. Debug CLI (`websocket_debug_cli.py`)
Command-line interface providing easy access to all debugging features.

## Quick Start

### Install Dependencies
```bash
pip install flask socketio requests
```

### Basic Usage

#### Run Comprehensive Diagnostics
```python
from websocket_diagnostic_tools import WebSocketDiagnosticTools
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

# Initialize tools
config_manager = WebSocketConfigManager()
cors_manager = CORSManager(config_manager)
diagnostics = WebSocketDiagnosticTools(config_manager, cors_manager)

# Run diagnostics
results = diagnostics.run_comprehensive_diagnostics("http://localhost:5000")
print(f"Overall status: {results['summary']['overall_status']}")
```

#### Start Monitoring Dashboard
```python
from websocket_monitoring_dashboard import start_monitoring_dashboard

# Start dashboard on port 5001
start_monitoring_dashboard(port=5001)
# Access at http://localhost:5001
```

#### Enable Debug Logging
```python
from websocket_debug_logger import set_debug_level, DebugLevel, get_debug_logger

# Set verbose logging
set_debug_level(DebugLevel.VERBOSE)

# Get logger
logger = get_debug_logger('my_component')
logger.info("Debug logging enabled")
```

#### Run Health Checks
```python
from websocket_health_checker import create_health_checker

# Create health checker
health_checker = create_health_checker()

# Run health check
overall_health = health_checker.get_overall_health()
print(f"System health: {overall_health['status']}")
```

### Command Line Interface

#### Run Diagnostics
```bash
# Comprehensive diagnostics
python websocket_debug_cli.py diagnose

# Check specific component
python websocket_debug_cli.py diagnose --component cors

# Export diagnostic report
python websocket_debug_cli.py diagnose --export diagnostic_report.json
```

#### Health Monitoring
```bash
# One-time health check
python websocket_debug_cli.py health

# Continuous monitoring
python websocket_debug_cli.py health --monitor --interval 30

# Check specific component
python websocket_debug_cli.py health --component configuration
```

#### Start Monitoring Dashboard
```bash
# Default port 5001
python websocket_debug_cli.py monitor

# Custom port and host
python websocket_debug_cli.py monitor --port 8080 --host 0.0.0.0
```

#### Connection Testing
```bash
# Test connection
python websocket_debug_cli.py test --type connection

# Test transport fallback
python websocket_debug_cli.py test --type transport

# Performance testing
python websocket_debug_cli.py test --type performance
```

#### Configuration Management
```bash
# Show configuration
python websocket_debug_cli.py config

# Export configuration
python websocket_debug_cli.py config --export config.json
```

#### Debug Logging
```bash
# Set debug level
python websocket_debug_cli.py debug --level verbose

# Export debug log
python websocket_debug_cli.py debug --export debug_log.json
```

## Detailed Tool Documentation

### WebSocket Diagnostic Tools

#### Features
- **Configuration Validation**: Check WebSocket and CORS configuration
- **Connection Testing**: Test WebSocket connection establishment
- **Transport Fallback**: Verify transport fallback mechanisms
- **Performance Testing**: Measure connection performance
- **CORS Validation**: Validate CORS configuration against server
- **Authentication Testing**: Test authentication flows
- **Error Scenario Testing**: Test error handling capabilities

#### Usage Examples
```python
# Check configuration only
config_check = diagnostics.check_configuration()
if config_check['status'] != 'pass':
    print("Configuration issues:")
    for issue in config_check['issues']:
        print(f"  - {issue}")

# Test connection performance
performance = diagnostics.test_connection_performance("http://localhost:5000")
avg_time = performance['metrics']['avg_connection_time']
print(f"Average connection time: {avg_time:.2f}s")

# Validate CORS
cors_validation = diagnostics.validate_cors_configuration("http://localhost:5000")
print(f"CORS status: {cors_validation['status']}")
```

### Debug Logger

#### Debug Levels
- **SILENT**: No debug output
- **ERROR**: Errors only
- **WARNING**: Warnings and errors
- **INFO**: Info, warnings, and errors
- **DEBUG**: Debug, info, warnings, and errors
- **VERBOSE**: All messages including trace information

#### Features
- **Structured Logging**: JSON-formatted log entries with context
- **Session Tracking**: Track debug sessions with unique IDs
- **Context Management**: Add contextual information to log entries
- **Performance Timing**: Built-in operation timing
- **File and Console Output**: Dual output with configurable formatting
- **WebSocket-Specific Logging**: Specialized logging for WebSocket events

#### Usage Examples
```python
from websocket_debug_logger import get_debug_logger, DebugLevel

# Create logger with specific level
logger = get_debug_logger('my_component', DebugLevel.DEBUG)

# Set session and context
logger.set_session_id('session_123')
logger.set_context(user_id='user_456', operation='connection_test')

# Log WebSocket events
logger.log_connection_attempt('http://localhost:5000', 'websocket')
logger.log_cors_check('http://localhost:5000', True)
logger.log_performance_metric('connection_time', 1.23, 'seconds')

# Use context managers
with logger.debug_context(component='auth'):
    logger.info("Authentication started")
    
with logger.timed_operation('database_query'):
    # Simulate database operation
    time.sleep(0.1)
```

### Connection Monitoring Dashboard

#### Features
- **Real-Time Monitoring**: Live connection status and metrics
- **Connection Tracking**: Track individual WebSocket connections
- **Message Monitoring**: Monitor message send/receive rates
- **Error Tracking**: Track and categorize connection errors
- **Performance Metrics**: Connection times and throughput
- **Namespace Monitoring**: Monitor different WebSocket namespaces
- **Transport Monitoring**: Track transport usage (WebSocket vs polling)

#### Dashboard Sections
- **Connection Status**: Active connections and overall statistics
- **Performance Metrics**: Message rates, connection times, error rates
- **Recent Events**: Real-time event log
- **Connection Details**: Individual connection information

#### API Endpoints
- `GET /api/status` - Connection status
- `GET /api/metrics` - Performance metrics
- `GET /api/events` - Recent events
- `GET /api/connections/<id>` - Connection details
- `GET /api/export` - Export monitoring data

### Health Checker

#### Health Check Components
- **Configuration**: WebSocket configuration validation
- **CORS Setup**: CORS configuration health
- **Server Availability**: Server reachability
- **WebSocket Endpoint**: WebSocket endpoint availability
- **Connection Establishment**: Connection establishment testing
- **Transport Fallback**: Transport fallback functionality
- **Authentication Flow**: Authentication system health
- **Message Handling**: Message processing capability
- **Error Recovery**: Error handling mechanisms
- **Performance Metrics**: System performance health

#### Health Status Levels
- **HEALTHY**: Component is functioning normally
- **WARNING**: Component has minor issues
- **CRITICAL**: Component has serious issues
- **UNKNOWN**: Component status cannot be determined

#### Usage Examples
```python
from websocket_health_checker import create_health_checker, setup_basic_alerts

# Create health checker
health_checker = create_health_checker()

# Set up basic alerts
setup_basic_alerts(health_checker)

# Run specific health checks
results = health_checker.run_health_check(['configuration', 'cors_setup'])
for component, result in results.items():
    print(f"{component}: {result.status.value} - {result.message}")

# Start continuous monitoring
health_checker.start_monitoring(interval=60)

# Get overall health
overall_health = health_checker.get_overall_health()
print(f"System health: {overall_health['status']}")

# Get health history
history = health_checker.get_health_history(hours=24)
```

## Environment Configuration

### Environment Variables
```bash
# Debug logging level
export WEBSOCKET_DEBUG_LEVEL=VERBOSE

# WebSocket configuration
export FLASK_HOST=localhost
export FLASK_PORT=5000
export SOCKETIO_CORS_ORIGINS="http://localhost:5000,https://localhost:5000"

# Health check configuration
export WEBSOCKET_HEALTH_CHECK_INTERVAL=60
export WEBSOCKET_HEALTH_ALERT_THRESHOLD=5.0

# Monitoring configuration
export WEBSOCKET_MONITOR_PORT=5001
export WEBSOCKET_MONITOR_HOST=127.0.0.1
```

### Configuration Files
Create a `.env` file in your project root:
```bash
# WebSocket Debug Configuration
WEBSOCKET_DEBUG_LEVEL=INFO
FLASK_HOST=localhost
FLASK_PORT=5000
SOCKETIO_CORS_ORIGINS=http://localhost:5000,https://localhost:5000
SOCKETIO_TRANSPORTS=websocket,polling
SOCKETIO_PING_TIMEOUT=60
SOCKETIO_PING_INTERVAL=25
```

## Integration with Existing Code

### Flask Application Integration
```python
from flask import Flask
from websocket_monitoring_dashboard import get_connection_monitor
from websocket_debug_logger import get_debug_logger, DebugLevel

app = Flask(__name__)

# Set up debug logging
logger = get_debug_logger('webapp', DebugLevel.INFO)

# Get connection monitor
monitor = get_connection_monitor()

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    # Register connection with monitor
    monitor.register_connection(
        connection_id=request.sid,
        namespace=request.namespace,
        transport='websocket',  # or detect actual transport
        user_id=current_user.id if current_user.is_authenticated else None
    )
    
    # Log connection
    logger.log_connection_success(request.url, 'websocket')

@socketio.on('disconnect')
def handle_disconnect():
    # Unregister connection
    monitor.unregister_connection(request.sid, 'client_disconnect')
    
    # Log disconnection
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('message')
def handle_message(data):
    # Record message
    monitor.record_message_received(request.sid, 'message', len(str(data)))
    
    # Log message
    logger.log_message_received('message', data, request.namespace)
```

### Error Handling Integration
```python
from websocket_debug_logger import get_debug_logger

logger = get_debug_logger('error_handler')

@socketio.on_error()
def error_handler(e):
    # Log error
    logger.error(f"WebSocket error: {str(e)}", e)
    
    # Record error in monitor
    monitor.record_error(request.sid, 'websocket_error', str(e))

@socketio.on_error_default
def default_error_handler(e):
    # Log default errors
    logger.error(f"Unhandled WebSocket error: {str(e)}", e)
```

## Testing and Validation

### Run Test Suite
```bash
# Run comprehensive test suite
python tests/scripts/test_websocket_debugging_tools.py

# Run specific tests
python -c "
from tests.scripts.test_websocket_debugging_tools import WebSocketDebuggingToolsTest
test = WebSocketDebuggingToolsTest()
test.test_debug_logger()
"
```

### Manual Testing
```python
# Test diagnostic tools
from websocket_diagnostic_tools import WebSocketDiagnosticTools
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

config_manager = WebSocketConfigManager()
cors_manager = CORSManager(config_manager)
diagnostics = WebSocketDiagnosticTools(config_manager, cors_manager)

# Test configuration
config_result = diagnostics.check_configuration()
print(f"Configuration: {config_result['status']}")

# Test CORS
cors_result = diagnostics.validate_cors_configuration("http://localhost:5000")
print(f"CORS: {cors_result['status']}")
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Ensure all dependencies are installed
pip install flask socketio requests

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 2. Connection Failures
```bash
# Check if server is running
curl http://localhost:5000

# Test WebSocket endpoint
curl http://localhost:5000/socket.io/
```

#### 3. Permission Errors
```bash
# Ensure log directory is writable
mkdir -p logs
chmod 755 logs
```

#### 4. Port Conflicts
```bash
# Check if port is in use
netstat -an | grep 5001

# Use different port
python websocket_debug_cli.py monitor --port 5002
```

### Debug Steps

1. **Check Configuration**:
   ```bash
   python websocket_debug_cli.py config
   ```

2. **Run Diagnostics**:
   ```bash
   python websocket_debug_cli.py diagnose
   ```

3. **Check Health**:
   ```bash
   python websocket_debug_cli.py health --verbose
   ```

4. **Enable Verbose Logging**:
   ```bash
   export WEBSOCKET_DEBUG_LEVEL=VERBOSE
   python websocket_debug_cli.py debug --level verbose
   ```

5. **Monitor Connections**:
   ```bash
   python websocket_debug_cli.py monitor
   ```

## Performance Considerations

### Resource Usage
- **Memory**: Debug logging and monitoring use minimal memory
- **CPU**: Health checks run in background threads
- **Network**: Diagnostic tools make minimal network requests
- **Storage**: Log files are rotated and size-limited

### Production Recommendations
- Set debug level to INFO or WARNING in production
- Use health monitoring with reasonable intervals (60s+)
- Enable monitoring dashboard only in development
- Export diagnostic reports for offline analysis

## Security Considerations

### Debug Information
- Debug logs may contain sensitive information
- Restrict access to monitoring dashboard
- Use secure connections (HTTPS/WSS) in production
- Sanitize debug output in production environments

### Network Security
- Monitoring dashboard binds to localhost by default
- Use firewall rules to restrict access
- Consider authentication for monitoring dashboard
- Encrypt exported diagnostic reports if needed

## API Reference

### WebSocketDiagnosticTools
```python
class WebSocketDiagnosticTools:
    def run_comprehensive_diagnostics(server_url: str) -> Dict[str, Any]
    def check_configuration() -> Dict[str, Any]
    def validate_cors_configuration(server_url: str) -> Dict[str, Any]
    def test_websocket_connection(server_url: str) -> Dict[str, Any]
    def test_transport_fallback(server_url: str) -> Dict[str, Any]
    def test_authentication_flow(server_url: str) -> Dict[str, Any]
    def test_connection_performance(server_url: str) -> Dict[str, Any]
    def export_diagnostic_report(results: Dict, filename: str) -> str
```

### WebSocketDebugLogger
```python
class WebSocketDebugLogger:
    def error(message: str, exception: Exception = None, extra_data: Dict = None)
    def warning(message: str, extra_data: Dict = None)
    def info(message: str, extra_data: Dict = None)
    def debug(message: str, extra_data: Dict = None)
    def verbose(message: str, extra_data: Dict = None)
    def log_connection_attempt(server_url: str, transport: str, namespace: str)
    def log_cors_check(origin: str, allowed: bool, reason: str)
    def log_performance_metric(metric_name: str, value: float, unit: str)
    def export_debug_log(filename: str) -> str
```

### WebSocketHealthChecker
```python
class WebSocketHealthChecker:
    def start_monitoring(interval: int = 60)
    def stop_monitoring()
    def run_health_check(components: List[str] = None) -> Dict[str, HealthCheckResult]
    def get_overall_health() -> Dict[str, Any]
    def get_health_history(component: str = None, hours: int = 24) -> Dict[str, List]
    def add_alert_callback(callback: Callable)
```

### WebSocketConnectionMonitor
```python
class WebSocketConnectionMonitor:
    def register_connection(connection_id: str, namespace: str, transport: str, user_id: str)
    def unregister_connection(connection_id: str, reason: str)
    def record_message_sent(connection_id: str, event: str, data_size: int)
    def record_message_received(connection_id: str, event: str, data_size: int)
    def record_error(connection_id: str, error_type: str, error_message: str)
    def get_connection_status() -> Dict[str, Any]
    def get_metrics_summary() -> Dict[str, Any]
```

## Contributing

### Adding New Diagnostic Tests
1. Add test method to `WebSocketDiagnosticTools`
2. Update CLI command options
3. Add documentation
4. Include in test suite

### Adding New Health Checks
1. Add checker method to `WebSocketHealthChecker`
2. Update component list
3. Add alert conditions
4. Test with different scenarios

### Extending Monitoring
1. Add new metrics to `WebSocketConnectionMonitor`
2. Update dashboard display
3. Add API endpoints
4. Update documentation

## License

This debugging tools suite is part of the Vedfolnir project and is licensed under the GNU Affero General Public License v3.0.