# WebSocket API Reference

## Overview

This document provides comprehensive API documentation for WebSocket events and message formats in the Vedfolnir WebSocket CORS standardization system. It covers all available events, message structures, authentication requirements, and usage examples.

## Connection Endpoints

### Base WebSocket Endpoint
```
ws://localhost:5000/socket.io/
wss://app.example.com/socket.io/
```

### Namespaces

#### User Namespace (`/`)
- **Purpose**: General user functionality and real-time updates
- **Authentication**: Required (user session)
- **Access**: All authenticated users

#### Admin Namespace (`/admin`)
- **Purpose**: Administrative functionality and system monitoring
- **Authentication**: Required (admin session)
- **Access**: Admin users only

## Authentication

### Session-Based Authentication

WebSocket connections use the existing Flask session system for authentication:

```javascript
// Authentication is automatic if user is logged in
const socket = io();

// Check authentication status
socket.on('connect', () => {
    console.log('Connected and authenticated');
});

socket.on('auth_error', (data) => {
    console.error('Authentication failed:', data.message);
    // Redirect to login page
    window.location.href = '/login';
});
```

### Authentication Events

#### `auth_required`
**Direction**: Server → Client  
**Namespace**: All  
**Description**: Sent when authentication is required but not provided

**Message Format**:
```json
{
    "event": "auth_required",
    "data": {
        "message": "Authentication required for WebSocket connection",
        "redirect_url": "/login",
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

#### `auth_error`
**Direction**: Server → Client  
**Namespace**: All  
**Description**: Sent when authentication fails

**Message Format**:
```json
{
    "event": "auth_error",
    "data": {
        "message": "Invalid session or expired credentials",
        "error_code": "AUTH_INVALID_SESSION",
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

## User Namespace Events (`/`)

### Caption Generation Events

#### `caption_generation_started`
**Direction**: Server → Client  
**Description**: Indicates that caption generation has begun for a user

**Message Format**:
```json
{
    "event": "caption_generation_started",
    "data": {
        "user_id": 123,
        "total_posts": 25,
        "estimated_duration": 300,
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

**Client Usage**:
```javascript
socket.on('caption_generation_started', (data) => {
    console.log(`Caption generation started for ${data.total_posts} posts`);
    showProgressBar(data.estimated_duration);
});
```

#### `caption_progress`
**Direction**: Server → Client  
**Description**: Real-time progress updates during caption generation

**Message Format**:
```json
{
    "event": "caption_progress",
    "data": {
        "user_id": 123,
        "current_post": 5,
        "total_posts": 25,
        "progress_percentage": 20,
        "current_post_id": "post_abc123",
        "current_post_url": "https://pixelfed.example.com/p/abc123",
        "status": "processing",
        "estimated_time_remaining": 240,
        "timestamp": "2025-01-15T10:30:15Z"
    }
}
```

**Client Usage**:
```javascript
socket.on('caption_progress', (data) => {
    updateProgressBar(data.progress_percentage);
    updateCurrentPost(data.current_post_id, data.current_post_url);
    updateTimeRemaining(data.estimated_time_remaining);
});
```

#### `caption_generated`
**Direction**: Server → Client  
**Description**: Sent when a caption is successfully generated for a post

**Message Format**:
```json
{
    "event": "caption_generated",
    "data": {
        "user_id": 123,
        "post_id": "post_abc123",
        "post_url": "https://pixelfed.example.com/p/abc123",
        "caption": "A beautiful sunset over the ocean with vibrant orange and pink colors reflecting on the water.",
        "confidence_score": 0.92,
        "processing_time": 2.3,
        "timestamp": "2025-01-15T10:30:17Z"
    }
}
```

**Client Usage**:
```javascript
socket.on('caption_generated', (data) => {
    addCaptionToReviewQueue(data.post_id, data.caption, data.confidence_score);
    showNotification(`Caption generated for post ${data.post_id}`);
});
```

#### `caption_generation_completed`
**Direction**: Server → Client  
**Description**: Indicates that caption generation process has completed

**Message Format**:
```json
{
    "event": "caption_generation_completed",
    "data": {
        "user_id": 123,
        "total_posts_processed": 25,
        "successful_captions": 23,
        "failed_captions": 2,
        "total_processing_time": 298,
        "average_processing_time": 11.9,
        "timestamp": "2025-01-15T10:35:00Z"
    }
}
```

**Client Usage**:
```javascript
socket.on('caption_generation_completed', (data) => {
    hideProgressBar();
    showCompletionSummary(data);
    refreshCaptionReviewPage();
});
```

#### `caption_generation_error`
**Direction**: Server → Client  
**Description**: Sent when an error occurs during caption generation

**Message Format**:
```json
{
    "event": "caption_generation_error",
    "data": {
        "user_id": 123,
        "post_id": "post_abc123",
        "error_type": "OLLAMA_CONNECTION_ERROR",
        "error_message": "Failed to connect to Ollama service",
        "retry_possible": true,
        "timestamp": "2025-01-15T10:30:20Z"
    }
}
```

**Client Usage**:
```javascript
socket.on('caption_generation_error', (data) => {
    showErrorNotification(data.error_message);
    if (data.retry_possible) {
        showRetryOption(data.post_id);
    }
});
```

### Platform Management Events

#### `platform_connection_status`
**Direction**: Server → Client  
**Description**: Updates on platform connection status changes

**Message Format**:
```json
{
    "event": "platform_connection_status",
    "data": {
        "user_id": 123,
        "platform_id": 456,
        "platform_name": "My Pixelfed Instance",
        "platform_type": "pixelfed",
        "status": "connected",
        "last_sync": "2025-01-15T10:30:00Z",
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

**Status Values**:
- `connected`: Platform is connected and accessible
- `disconnected`: Platform connection lost
- `error`: Connection error occurred
- `syncing`: Currently synchronizing data

#### `platform_sync_progress`
**Direction**: Server → Client  
**Description**: Progress updates during platform data synchronization

**Message Format**:
```json
{
    "event": "platform_sync_progress",
    "data": {
        "user_id": 123,
        "platform_id": 456,
        "sync_type": "posts",
        "current_item": 150,
        "total_items": 500,
        "progress_percentage": 30,
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

### User Notification Events

#### `user_notification`
**Direction**: Server → Client  
**Description**: General notifications for the user

**Message Format**:
```json
{
    "event": "user_notification",
    "data": {
        "user_id": 123,
        "notification_id": "notif_xyz789",
        "type": "info",
        "title": "Caption Review Available",
        "message": "5 new captions are ready for review",
        "action_url": "/captions/review",
        "action_text": "Review Now",
        "auto_dismiss": true,
        "dismiss_timeout": 10000,
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

**Notification Types**:
- `info`: Informational message
- `success`: Success confirmation
- `warning`: Warning message
- `error`: Error notification

## Admin Namespace Events (`/admin`)

### System Status Events

#### `system_status_update`
**Direction**: Server → Client  
**Description**: Real-time system status updates for administrators

**Message Format**:
```json
{
    "event": "system_status_update",
    "data": {
        "component": "websocket_server",
        "status": "healthy",
        "metrics": {
            "active_connections": 45,
            "total_connections": 1250,
            "memory_usage": "256MB",
            "cpu_usage": "15%"
        },
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

**Component Types**:
- `websocket_server`: WebSocket server status
- `database`: Database connection status
- `redis`: Redis server status
- `ollama`: AI service status
- `platform_apis`: External platform API status

#### `admin_alert`
**Direction**: Server → Client  
**Description**: Critical alerts for system administrators

**Message Format**:
```json
{
    "event": "admin_alert",
    "data": {
        "alert_id": "alert_critical_001",
        "severity": "critical",
        "component": "database",
        "title": "Database Connection Pool Exhausted",
        "message": "All database connections are in use. New requests are being queued.",
        "recommended_action": "Increase connection pool size or investigate slow queries",
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

**Severity Levels**:
- `info`: Informational alert
- `warning`: Warning condition
- `error`: Error condition
- `critical`: Critical system issue

### User Management Events

#### `user_activity_update`
**Direction**: Server → Client  
**Description**: Real-time user activity updates for admin monitoring

**Message Format**:
```json
{
    "event": "user_activity_update",
    "data": {
        "user_id": 123,
        "username": "john_doe",
        "activity_type": "caption_generation_started",
        "details": {
            "posts_count": 25,
            "platform": "pixelfed"
        },
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

#### `admin_notification`
**Direction**: Server → Client  
**Description**: Administrative notifications and system messages

**Message Format**:
```json
{
    "event": "admin_notification",
    "data": {
        "notification_id": "admin_notif_001",
        "type": "system_maintenance",
        "priority": "high",
        "title": "Scheduled Maintenance Window",
        "message": "System maintenance scheduled for tonight at 2:00 AM UTC",
        "action_required": false,
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

## Client-to-Server Events

### Connection Management

#### `join_room`
**Direction**: Client → Server  
**Description**: Join a specific room for targeted messaging

**Message Format**:
```json
{
    "event": "join_room",
    "data": {
        "room_name": "user_123_captions",
        "room_type": "user_specific"
    }
}
```

**Response**:
```json
{
    "event": "room_joined",
    "data": {
        "room_name": "user_123_captions",
        "success": true,
        "message": "Successfully joined room"
    }
}
```

#### `leave_room`
**Direction**: Client → Server  
**Description**: Leave a specific room

**Message Format**:
```json
{
    "event": "leave_room",
    "data": {
        "room_name": "user_123_captions"
    }
}
```

### Caption Management

#### `request_caption_status`
**Direction**: Client → Server  
**Description**: Request current status of caption generation

**Message Format**:
```json
{
    "event": "request_caption_status",
    "data": {
        "user_id": 123
    }
}
```

**Response**:
```json
{
    "event": "caption_status_response",
    "data": {
        "user_id": 123,
        "is_active": true,
        "current_progress": {
            "current_post": 5,
            "total_posts": 25,
            "progress_percentage": 20
        }
    }
}
```

#### `pause_caption_generation`
**Direction**: Client → Server  
**Description**: Request to pause ongoing caption generation

**Message Format**:
```json
{
    "event": "pause_caption_generation",
    "data": {
        "user_id": 123,
        "reason": "user_requested"
    }
}
```

#### `resume_caption_generation`
**Direction**: Client → Server  
**Description**: Request to resume paused caption generation

**Message Format**:
```json
{
    "event": "resume_caption_generation",
    "data": {
        "user_id": 123
    }
}
```

## Error Handling

### Standard Error Response Format

All error responses follow this standard format:

```json
{
    "event": "error",
    "data": {
        "error_code": "WEBSOCKET_ERROR_CODE",
        "error_message": "Human-readable error description",
        "error_details": {
            "original_event": "caption_progress",
            "user_id": 123,
            "additional_info": "Any relevant details"
        },
        "retry_possible": true,
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

### Common Error Codes

#### Authentication Errors
- `AUTH_REQUIRED`: Authentication required but not provided
- `AUTH_INVALID_SESSION`: Invalid or expired session
- `AUTH_INSUFFICIENT_PRIVILEGES`: User lacks required permissions

#### Connection Errors
- `CONNECTION_TIMEOUT`: Connection attempt timed out
- `CONNECTION_REFUSED`: Server refused connection
- `TRANSPORT_ERROR`: Transport-level error occurred

#### CORS Errors
- `CORS_ORIGIN_NOT_ALLOWED`: Origin not in allowed CORS origins
- `CORS_PREFLIGHT_FAILED`: CORS preflight request failed
- `CORS_CREDENTIALS_ERROR`: CORS credentials handling error

#### Rate Limiting Errors
- `RATE_LIMIT_EXCEEDED`: Too many requests from client
- `CONNECTION_LIMIT_EXCEEDED`: Too many concurrent connections

#### Application Errors
- `CAPTION_GENERATION_FAILED`: Caption generation process failed
- `PLATFORM_CONNECTION_ERROR`: Platform API connection error
- `DATABASE_ERROR`: Database operation failed

## Message Validation

### Required Fields

All WebSocket messages must include:
- `event`: String identifying the event type
- `data`: Object containing event-specific data
- `timestamp`: ISO 8601 timestamp (server-generated)

### Optional Fields

- `message_id`: Unique identifier for message tracking
- `correlation_id`: ID for correlating request/response pairs
- `user_id`: User ID (automatically added by server)
- `session_id`: Session ID (automatically added by server)

### Data Validation Rules

#### String Fields
- Maximum length: 1000 characters
- Must be valid UTF-8
- HTML tags are escaped for security

#### Numeric Fields
- Must be valid numbers
- Range validation applied where appropriate

#### Timestamp Fields
- Must be valid ISO 8601 format
- Server timestamps are in UTC

## Rate Limiting

### Connection Limits
- Maximum 5 concurrent connections per user
- Maximum 100 connection attempts per hour per IP

### Message Limits
- Maximum 100 messages per minute per user
- Maximum message size: 10KB

### Rate Limit Headers
Rate limit information is included in error responses:

```json
{
    "event": "rate_limit_exceeded",
    "data": {
        "error_code": "RATE_LIMIT_EXCEEDED",
        "limit": 100,
        "remaining": 0,
        "reset_time": "2025-01-15T10:31:00Z"
    }
}
```

## Security Considerations

### CSRF Protection
- All WebSocket events include CSRF token validation
- Tokens must match the user's session CSRF token

### Input Sanitization
- All user input is sanitized and validated
- HTML content is escaped to prevent XSS

### Session Security
- Sessions are validated on every WebSocket message
- Expired sessions are automatically disconnected

## Client Implementation Examples

### JavaScript Client Setup

```javascript
// Basic client setup with error handling
const socket = io('/', {
    transports: ['websocket', 'polling'],
    timeout: 20000,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
});

// Connection event handlers
socket.on('connect', () => {
    console.log('WebSocket connected');
    joinUserRoom();
});

socket.on('disconnect', (reason) => {
    console.log('WebSocket disconnected:', reason);
    if (reason === 'io server disconnect') {
        // Server disconnected, manual reconnection needed
        socket.connect();
    }
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    handleConnectionError(error);
});

// Join user-specific room
function joinUserRoom() {
    socket.emit('join_room', {
        room_name: `user_${currentUserId}_captions`,
        room_type: 'user_specific'
    });
}

// Handle caption progress updates
socket.on('caption_progress', (data) => {
    updateProgressBar(data.progress_percentage);
    updateCurrentPost(data.current_post_id);
    updateTimeRemaining(data.estimated_time_remaining);
});

// Handle errors
socket.on('error', (error) => {
    console.error('WebSocket error:', error);
    showErrorNotification(error.error_message);
    
    if (error.retry_possible) {
        setTimeout(() => {
            socket.connect();
        }, 5000);
    }
});
```

### Admin Client Setup

```javascript
// Admin client with additional event handlers
const adminSocket = io('/admin', {
    transports: ['websocket', 'polling']
});

// System status monitoring
adminSocket.on('system_status_update', (data) => {
    updateSystemStatusDashboard(data);
});

// Critical alerts
adminSocket.on('admin_alert', (data) => {
    if (data.severity === 'critical') {
        showCriticalAlert(data);
        playAlertSound();
    }
});

// User activity monitoring
adminSocket.on('user_activity_update', (data) => {
    updateUserActivityLog(data);
});
```

## Testing and Development

### WebSocket Testing Tools

```javascript
// Test WebSocket connection
function testWebSocketConnection() {
    const testSocket = io('/', { forceNew: true });
    
    testSocket.on('connect', () => {
        console.log('✅ WebSocket connection successful');
        testSocket.disconnect();
    });
    
    testSocket.on('connect_error', (error) => {
        console.error('❌ WebSocket connection failed:', error);
    });
}

// Test authentication
function testWebSocketAuth() {
    const authSocket = io('/', { forceNew: true });
    
    authSocket.on('auth_required', () => {
        console.log('✅ Authentication required (expected)');
    });
    
    authSocket.on('connect', () => {
        console.log('✅ Authenticated connection successful');
    });
}
```

### Development Utilities

```bash
# Test WebSocket connectivity
python scripts/test_websocket_connection.py

# Monitor WebSocket events
python scripts/monitor_websocket_events.py

# Test CORS configuration
python scripts/test_websocket_cors.py
```

This comprehensive API reference provides all the information needed to integrate with the Vedfolnir WebSocket system effectively and securely.