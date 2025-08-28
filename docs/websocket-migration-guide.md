# WebSocket Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from existing WebSocket implementations to the new standardized WebSocket CORS system in Vedfolnir. It covers configuration changes, code updates, and testing procedures to ensure a smooth transition.

## Migration Scenarios

### Scenario 1: Legacy Flask-SocketIO Implementation

**From**: Basic Flask-SocketIO setup with hardcoded CORS
**To**: Dynamic CORS configuration with unified management

### Scenario 2: Custom WebSocket Implementation

**From**: Custom WebSocket handling with manual CORS management
**To**: Standardized Socket.IO with automated CORS handling

### Scenario 3: Multiple WebSocket Instances

**From**: Separate WebSocket configurations for user and admin
**To**: Unified configuration with namespace separation

## Pre-Migration Assessment

### 1. Current Implementation Analysis

Run the assessment script to analyze your current WebSocket setup:

```bash
# Analyze current WebSocket implementation
python scripts/migration/analyze_websocket_implementation.py

# Check for deprecated patterns
python scripts/migration/check_deprecated_patterns.py
```

**Assessment Report Example**:
```
WebSocket Implementation Analysis
================================
Current Setup: Flask-SocketIO 5.1.0
CORS Configuration: Hardcoded origins
Authentication: Session-based (compatible)
Namespaces: Single namespace (needs update)
Transport: WebSocket only (needs polling fallback)

Migration Complexity: MEDIUM
Estimated Time: 2-4 hours
Breaking Changes: 3 identified
```

### 2. Backup Current Implementation

```bash
# Create backup of current WebSocket files
mkdir -p backups/websocket_migration_$(date +%Y%m%d_%H%M%S)
cp web_app.py backups/websocket_migration_*/
cp -r static/js/websocket* backups/websocket_migration_*/
cp .env backups/websocket_migration_*/

# Backup database (if WebSocket data is stored)
python scripts/backup/backup_websocket_data.py
```

### 3. Dependency Check

```bash
# Check current dependencies
pip list | grep -E "(flask|socketio|eventlet|gevent)"

# Check for conflicting packages
python scripts/migration/check_dependency_conflicts.py
```

## Step-by-Step Migration

### Step 1: Update Dependencies

```bash
# Update to compatible versions
pip install --upgrade flask-socketio==5.3.0
pip install --upgrade python-socketio==5.8.0
pip install --upgrade eventlet==0.33.0

# Install new dependencies
pip install redis>=4.0.0
pip install cryptography>=3.4.0

# Verify installation
python -c "import socketio; print(f'Socket.IO version: {socketio.__version__}')"
```

### Step 2: Environment Configuration Migration

#### Legacy Configuration (.env.old)
```bash
# Old hardcoded CORS configuration
SOCKETIO_CORS_ALLOWED_ORIGINS=http://localhost:5000,https://localhost:5000
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=5000
```

#### New Configuration (.env)
```bash
# New dynamic CORS configuration
FLASK_HOST=localhost
FLASK_PORT=5000

# WebSocket configuration (new)
SOCKETIO_CORS_CREDENTIALS=true
SOCKETIO_TRANSPORTS=websocket,polling
SOCKETIO_CSRF_PROTECTION=true
SOCKETIO_RATE_LIMITING=true
SOCKETIO_MAX_CONNECTIONS_PER_USER=5

# Remove old variables
# SOCKETIO_CORS_ALLOWED_ORIGINS (deprecated)
# WEBSOCKET_HOST (deprecated)
# WEBSOCKET_PORT (deprecated)
```

**Migration Script**:
```bash
# Run configuration migration
python scripts/migration/migrate_websocket_config.py --backup --validate
```

### Step 3: Server-Side Code Migration

#### Legacy Implementation (web_app.py)
```python
# OLD: Hardcoded CORS configuration
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=[
    "http://localhost:5000",
    "https://localhost:5000"
])

@socketio.on('connect')
def handle_connect():
    # Basic connection handling
    pass

@socketio.on('caption_progress')
def handle_caption_progress(data):
    # Manual event handling
    pass
```

#### New Implementation (web_app.py)
```python
# NEW: Dynamic CORS with unified configuration
from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

app = Flask(__name__)

# Initialize WebSocket system
config_manager = WebSocketConfigManager(app.config)
cors_manager = CORSManager(config_manager)
websocket_factory = WebSocketFactory(config_manager, cors_manager)

# Create SocketIO instance with standardized configuration
socketio = websocket_factory.create_socketio_instance(app)

# Namespace management is handled automatically
# Event handlers are registered through the namespace manager
```

**Migration Steps**:

1. **Replace WebSocket initialization**:
   ```bash
   # Run server-side migration
   python scripts/migration/migrate_server_websocket.py --input web_app.py --output web_app_new.py
   ```

2. **Update event handlers**:
   ```python
   # OLD: Direct event handlers
   @socketio.on('caption_progress')
   def handle_caption_progress(data):
       emit('progress_update', data)
   
   # NEW: Namespace-aware handlers (automatically handled)
   # Event handlers are registered through the namespace manager
   ```

3. **Update authentication**:
   ```python
   # OLD: Manual authentication
   @socketio.on('connect')
   def handle_connect():
       if not session.get('user_id'):
           return False
   
   # NEW: Automatic authentication (handled by auth handler)
   # Authentication is managed by WebSocketAuthHandler
   ```

### Step 4: Client-Side Code Migration

#### Legacy Client Implementation (static/js/websocket-client.js)
```javascript
// OLD: Hardcoded configuration
const socket = io('http://localhost:5000', {
    transports: ['websocket']
});

socket.on('connect', function() {
    console.log('Connected');
});

socket.on('caption_progress', function(data) {
    updateProgress(data.percentage);
});
```

#### New Client Implementation
```javascript
// NEW: Dynamic configuration with error handling
import { WebSocketClientFactory } from './websocket-client-factory.js';

// Create client with automatic configuration
const clientFactory = new WebSocketClientFactory();
const socket = clientFactory.createUserClient({
    namespace: '/',
    autoReconnect: true,
    fallbackTransport: true
});

// Enhanced event handling
socket.on('connect', () => {
    console.log('WebSocket connected with enhanced features');
});

socket.on('caption_progress', (data) => {
    updateProgress(data.progress_percentage);
    updateTimeRemaining(data.estimated_time_remaining);
});

// Automatic error recovery
socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    // Error recovery is handled automatically
});
```

**Client Migration Steps**:

1. **Update client files**:
   ```bash
   # Run client-side migration
   python scripts/migration/migrate_client_websocket.py --input static/js/ --output static/js/migrated/
   ```

2. **Update HTML templates**:
   ```html
   <!-- OLD: Direct Socket.IO inclusion -->
   <script src="/static/js/socket.io.min.js"></script>
   <script src="/static/js/websocket-client.js"></script>
   
   <!-- NEW: Modular client factory -->
   <script type="module" src="/static/js/websocket-client-factory.js"></script>
   <script type="module" src="/static/js/websocket-client-enhanced.js"></script>
   ```

### Step 5: Database Migration (if applicable)

If your current implementation stores WebSocket-related data:

```bash
# Check for WebSocket-related database tables
python scripts/migration/check_websocket_database.py

# Migrate WebSocket session data (if needed)
python scripts/migration/migrate_websocket_sessions.py

# Update database schema for new features
python scripts/migration/update_websocket_schema.py
```

### Step 6: Configuration Validation

```bash
# Validate new configuration
python scripts/migration/validate_websocket_config.py

# Test CORS configuration
python scripts/migration/test_cors_migration.py

# Verify authentication integration
python scripts/migration/test_auth_migration.py
```

## Testing Migration

### 1. Unit Testing

```bash
# Test individual components
python -m unittest tests.websocket.test_config_manager -v
python -m unittest tests.websocket.test_cors_manager -v
python -m unittest tests.websocket.test_websocket_factory -v
```

### 2. Integration Testing

```bash
# Test complete WebSocket system
python scripts/test/test_websocket_integration.py

# Test CORS functionality
python scripts/test/test_cors_integration.py

# Test authentication flow
python scripts/test/test_auth_integration.py
```

### 3. Browser Testing

```javascript
// Browser console testing
// Test connection
const testSocket = io();
testSocket.on('connect', () => console.log('✅ Connection successful'));
testSocket.on('connect_error', (error) => console.error('❌ Connection failed:', error));

// Test CORS
fetch('/socket.io/?transport=polling', {
    method: 'GET',
    credentials: 'include'
}).then(response => {
    console.log('✅ CORS test successful:', response.status);
}).catch(error => {
    console.error('❌ CORS test failed:', error);
});
```

### 4. Load Testing

```bash
# Test connection load
python scripts/test/websocket_load_test.py --connections 100 --duration 60

# Test message throughput
python scripts/test/websocket_message_load_test.py --messages 1000 --concurrent 10
```

## Common Migration Issues

### Issue 1: CORS Origin Mismatch

**Symptoms**:
- Connection fails with CORS errors
- Browser console shows origin not allowed

**Solution**:
```bash
# Check current origins
python -c "
from websocket_config_manager import WebSocketConfigManager
from config import Config
config = Config()
ws_config = WebSocketConfigManager(config)
print('Generated origins:', ws_config.get_cors_origins())
"

# Update FLASK_HOST and FLASK_PORT if needed
echo "FLASK_HOST=your-actual-host" >> .env
echo "FLASK_PORT=your-actual-port" >> .env
```

### Issue 2: Authentication Failures

**Symptoms**:
- WebSocket connects but user context is missing
- Authentication errors in logs

**Solution**:
```python
# Verify session configuration
from flask import Flask, session
app = Flask(__name__)
with app.app_context():
    print('Session interface:', app.session_interface.__class__.__name__)
    print('Session cookie name:', app.config.get('SESSION_COOKIE_NAME'))
```

### Issue 3: Transport Fallback Issues

**Symptoms**:
- WebSocket connection fails in some browsers
- Connection stuck in connecting state

**Solution**:
```bash
# Enable transport fallback
echo "SOCKETIO_TRANSPORTS=websocket,polling" >> .env

# Test both transports
python scripts/test/test_transport_fallback.py
```

### Issue 4: Namespace Conflicts

**Symptoms**:
- Events not received in correct namespace
- Admin events visible to regular users

**Solution**:
```python
# Verify namespace configuration
from websocket_namespace_manager import WebSocketNamespaceManager
# Namespace separation is handled automatically
# Check logs for namespace registration
```

## Rollback Procedures

### Emergency Rollback

If migration fails and immediate rollback is needed:

```bash
# Stop new WebSocket server
pkill -f "python web_app.py"

# Restore backup files
cp backups/websocket_migration_*/web_app.py ./
cp backups/websocket_migration_*/.env ./

# Restore client files
cp -r backups/websocket_migration_*/static/js/* static/js/

# Start old implementation
python web_app.py & sleep 10

# Verify rollback
python scripts/test/test_websocket_basic.py
```

### Gradual Rollback

For controlled rollback with user notification:

```bash
# Enable maintenance mode
python scripts/maintenance/enable_maintenance_mode.py --message "WebSocket system maintenance in progress"

# Perform rollback steps
python scripts/migration/rollback_websocket_migration.py --step-by-step

# Disable maintenance mode
python scripts/maintenance/disable_maintenance_mode.py
```

## Post-Migration Verification

### 1. Functionality Checklist

- [ ] WebSocket connections establish successfully
- [ ] CORS configuration works across all environments
- [ ] Authentication integrates properly
- [ ] Real-time events are delivered correctly
- [ ] Error handling and recovery work as expected
- [ ] Performance meets or exceeds previous implementation

### 2. Performance Verification

```bash
# Compare performance metrics
python scripts/migration/compare_performance.py --before backups/performance_baseline.json --after current

# Monitor resource usage
python scripts/monitoring/monitor_websocket_resources.py --duration 300
```

### 3. Security Verification

```bash
# Security audit
python scripts/security/audit_websocket_security.py

# CORS security test
python scripts/security/test_cors_security.py

# Authentication security test
python scripts/security/test_websocket_auth_security.py
```

## Migration Best Practices

### Planning Phase
1. **Schedule maintenance window** for migration
2. **Notify users** of potential service interruption
3. **Prepare rollback plan** in case of issues
4. **Test migration** in staging environment first

### Execution Phase
1. **Follow migration steps** in exact order
2. **Validate each step** before proceeding
3. **Monitor logs** for errors during migration
4. **Test functionality** after each major step

### Post-Migration Phase
1. **Monitor system performance** for 24-48 hours
2. **Collect user feedback** on WebSocket functionality
3. **Document any issues** and resolutions
4. **Update monitoring** and alerting systems

### Communication
1. **Inform stakeholders** of migration timeline
2. **Provide status updates** during migration
3. **Document changes** for future reference
4. **Train team members** on new WebSocket system

## Troubleshooting Migration Issues

### Debug Mode Migration

```bash
# Enable debug logging during migration
export SOCKETIO_DEBUG=true
export SOCKETIO_LOG_LEVEL=DEBUG

# Run migration with verbose output
python scripts/migration/migrate_websocket_full.py --verbose --debug
```

### Common Error Patterns

#### Configuration Errors
```
ERROR: Invalid CORS origin format
SOLUTION: Check FLASK_HOST and FLASK_PORT values
```

#### Import Errors
```
ERROR: Cannot import WebSocketFactory
SOLUTION: Ensure all new dependencies are installed
```

#### Authentication Errors
```
ERROR: Session validation failed
SOLUTION: Verify session configuration and Redis connectivity
```

### Getting Help

If you encounter issues during migration:

1. **Check migration logs**: `logs/websocket_migration.log`
2. **Run diagnostic script**: `python scripts/migration/diagnose_migration_issues.py`
3. **Consult troubleshooting guide**: `docs/websocket-troubleshooting-guide.md`
4. **Contact support** with diagnostic information

## Migration Completion

### Final Steps

1. **Clean up backup files** (after successful migration)
2. **Update documentation** with any custom changes
3. **Schedule regular maintenance** for WebSocket system
4. **Plan future upgrades** and improvements

### Success Criteria

Migration is considered successful when:
- [ ] All WebSocket functionality works as expected
- [ ] Performance meets or exceeds baseline
- [ ] No security vulnerabilities introduced
- [ ] User experience is maintained or improved
- [ ] System monitoring shows healthy metrics

### Post-Migration Monitoring

```bash
# Set up continuous monitoring
python scripts/monitoring/setup_websocket_monitoring.py

# Configure alerts for WebSocket issues
python scripts/monitoring/configure_websocket_alerts.py

# Schedule regular health checks
crontab -e
# Add: */5 * * * * /path/to/scripts/monitoring/websocket_health_check.py
```

This comprehensive migration guide ensures a smooth transition to the new WebSocket CORS standardization system while minimizing downtime and maintaining system reliability.