# WebSocket Client Factory Documentation

## Overview

The WebSocket Client Factory provides a standardized way to create and configure WebSocket clients in Vedfolnir. It automatically adapts client configuration based on server environment settings, client environment detection, and provides consistent connection initialization patterns.

## Features

- **Standardized Configuration**: Consistent WebSocket client configuration across the application
- **Environment Detection**: Automatic adaptation based on client environment (mobile, development, network quality)
- **Server Integration**: Fetches configuration from server-side WebSocket configuration managers
- **Error Handling**: Comprehensive error handling with intelligent recovery mechanisms
- **CORS Support**: Integrated CORS validation and origin management
- **Legacy Compatibility**: Maintains compatibility with existing WebSocket client code

## Usage

### Basic Client Creation

```javascript
// Create a basic WebSocket client
const client = window.createWebSocketClient({
    namespace: '/',
    autoConnect: true
});

// Listen for events
client.on('connect', () => {
    console.log('Connected to WebSocket server');
});

client.on('message', (data) => {
    console.log('Received message:', data);
});

// Emit events
client.emit('my_event', { data: 'Hello Server' });
```

### Advanced Configuration

```javascript
// Create client with custom configuration
const adminClient = window.WebSocketClientFactory.createClient({
    namespace: '/admin',
    autoConnect: false,
    customConfig: {
        timeout: 30000,
        reconnectionAttempts: 10,
        transports: ['websocket', 'polling']
    }
});

// Manual connection
adminClient.connect();
```

### Environment Adaptation

The factory automatically adapts configuration based on:

- **Mobile Detection**: Increases timeouts and ping intervals for mobile devices
- **Development Environment**: Enables more reconnection attempts and debugging features
- **Network Quality**: Adjusts transport methods and timeouts based on connection quality
- **Browser Compatibility**: Applies browser-specific optimizations

## Server Configuration API

The factory fetches configuration from the server via the `/api/websocket/client-config` endpoint:

```javascript
// Get server configuration
const config = await window.WebSocketClientFactory.getServerConfiguration();
console.log('Server config:', config);
```

### Configuration Response Format

```json
{
    "success": true,
    "config": {
        "url": "http://localhost:5000",
        "transports": ["websocket", "polling"],
        "reconnection": true,
        "reconnectionAttempts": 5,
        "reconnectionDelay": 1000,
        "reconnectionDelayMax": 5000,
        "timeout": 20000,
        "server_capabilities": {
            "namespaces": ["/", "/admin"],
            "features": ["reconnection", "rooms", "authentication"]
        }
    }
}
```

## Error Handling

The factory provides intelligent error handling:

### CORS Errors
```javascript
client.on('cors_error', (error) => {
    console.log('CORS error detected, switching to polling mode');
});
```

### Connection Timeouts
```javascript
client.on('timeout_error', (error) => {
    console.log('Timeout detected, increasing timeout values');
});
```

### Transport Issues
```javascript
client.on('transport_error', (error) => {
    console.log('Transport error, trying alternative method');
});
```

## Legacy Compatibility

The factory maintains compatibility with existing VedfolnirWebSocket code:

```javascript
// Legacy methods are automatically available
window.VedfolnirWS.joinAdminDashboard();
window.VedfolnirWS.joinTask('task_123');
window.VedfolnirWS.handleProgressUpdate(data);
```

## Client Metrics

Monitor client performance and connection quality:

```javascript
// Get connection metrics
const metrics = client.getMetrics();
console.log('Connection metrics:', {
    connected: metrics.connected,
    transport: metrics.transport,
    averageLatency: metrics.averageLatency,
    totalReconnects: metrics.totalReconnects
});

// Get client status
const status = client.getStatus();
console.log('Client status:', status);
```

## Configuration Validation

The factory validates configuration before creating clients:

```javascript
// Configuration is automatically validated
try {
    const client = window.WebSocketClientFactory.createClient(options);
} catch (error) {
    console.error('Configuration validation failed:', error.message);
}
```

## Environment Detection

The factory detects and adapts to various environments:

```javascript
// Get environment information
const summary = window.WebSocketClientFactory.getConfigurationSummary();
console.log('Environment:', summary.environment);
```

### Detected Environment Properties

- **Browser**: Name and version detection
- **Protocol**: HTTP/HTTPS detection
- **Development**: Development environment detection
- **Mobile**: Mobile device detection
- **Network Quality**: Connection quality estimation
- **WebSocket Support**: Native WebSocket support detection

## Best Practices

1. **Use Factory Methods**: Always use the factory to create clients for consistency
2. **Handle Errors**: Implement proper error handling for connection issues
3. **Monitor Metrics**: Use client metrics to monitor connection health
4. **Environment Awareness**: Let the factory handle environment-specific adaptations
5. **Cleanup Resources**: Properly destroy clients when no longer needed

```javascript
// Proper cleanup
client.destroy();
```

## Integration with Server

The client factory integrates with server-side components:

- **WebSocketConfigManager**: Provides server configuration
- **CORSManager**: Handles CORS validation and origin management
- **WebSocketFactory**: Creates standardized server instances

## Troubleshooting

### Common Issues

1. **Configuration Not Loading**: Check server endpoint availability
2. **CORS Errors**: Verify allowed origins in server configuration
3. **Connection Timeouts**: Check network connectivity and server status
4. **Transport Failures**: Ensure both WebSocket and polling are supported

### Debug Information

```javascript
// Get debug information
const debugInfo = window.WebSocketClientFactory.getConfigurationSummary();
console.log('Debug info:', debugInfo);

// Clear cache if needed
window.WebSocketClientFactory.clearCache();
```

## API Reference

### WebSocketClientFactory

- `createClient(options)`: Create a new WebSocket client
- `getServerConfiguration()`: Fetch server configuration
- `getConfigurationSummary()`: Get factory status and configuration
- `clearCache()`: Clear cached configuration

### StandardizedWebSocketClient

- `connect()`: Connect to server
- `disconnect()`: Disconnect from server
- `emit(event, data, callback)`: Emit event to server
- `on(event, handler)`: Listen for server events
- `off(event, handler)`: Remove event listener
- `isConnected()`: Check connection status
- `getMetrics()`: Get connection metrics
- `getStatus()`: Get client status
- `destroy()`: Clean up resources

This factory provides a robust, standardized foundation for WebSocket communication in Vedfolnir while maintaining backward compatibility and providing intelligent environment adaptation.