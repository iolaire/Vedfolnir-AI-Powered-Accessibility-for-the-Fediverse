# Maintenance Status API Documentation

## Overview

The Maintenance Status API provides real-time information about the system's maintenance mode status. This API enables frontend applications, monitoring systems, and external integrations to query maintenance status and respond appropriately to maintenance events.

## Base URL

```
http://your-domain.com/api/maintenance
```

## Authentication

Most maintenance status endpoints are publicly accessible to allow systems to check maintenance status even when other operations are blocked. Administrative endpoints require authentication and admin privileges.

### Public Endpoints
- `GET /status` - No authentication required
- `GET /blocked-operations` - No authentication required
- `GET /message` - No authentication required

### Admin Endpoints
- `POST /enable` - Requires admin authentication
- `POST /disable` - Requires admin authentication
- `POST /emergency` - Requires admin authentication

## Endpoints

### GET /api/maintenance/status

Returns the current maintenance mode status and related information.

#### Request
```http
GET /api/maintenance/status HTTP/1.1
Host: your-domain.com
Accept: application/json
```

#### Response

**Success Response (200 OK)**
```json
{
  "is_active": true,
  "mode": "normal",
  "reason": "Database optimization and security updates",
  "estimated_duration": 3600,
  "started_at": "2025-01-15T10:00:00Z",
  "estimated_completion": "2025-01-15T11:00:00Z",
  "blocked_operations": [
    "caption_generation",
    "job_creation",
    "platform_operations",
    "batch_operations",
    "user_data_modification",
    "image_processing"
  ],
  "active_jobs_count": 3,
  "message": "System maintenance in progress. Most operations will resume at 11:00 AM UTC.",
  "enabled_by": "admin",
  "invalidated_sessions": 15,
  "test_mode": false
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `is_active` | boolean | Whether maintenance mode is currently active |
| `mode` | string | Maintenance mode type: "normal", "emergency", or "test" |
| `reason` | string | Reason for maintenance (null if not active) |
| `estimated_duration` | integer | Estimated duration in seconds (null if unknown) |
| `started_at` | string | ISO 8601 timestamp when maintenance started |
| `estimated_completion` | string | ISO 8601 timestamp of estimated completion |
| `blocked_operations` | array | List of currently blocked operation types |
| `active_jobs_count` | integer | Number of jobs still running/completing |
| `message` | string | User-friendly maintenance message |
| `enabled_by` | string | Username who enabled maintenance mode |
| `invalidated_sessions` | integer | Number of user sessions invalidated |
| `test_mode` | boolean | Whether this is test mode (simulation only) |

**Inactive Maintenance Response**
```json
{
  "is_active": false,
  "mode": "normal",
  "reason": null,
  "estimated_duration": null,
  "started_at": null,
  "estimated_completion": null,
  "blocked_operations": [],
  "active_jobs_count": 0,
  "message": "All systems operational",
  "enabled_by": null,
  "invalidated_sessions": 0,
  "test_mode": false
}
```

#### Error Responses

**Service Unavailable (503)**
```json
{
  "error": "maintenance_service_unavailable",
  "message": "Maintenance status service is temporarily unavailable",
  "retry_after": 30
}
```

### GET /api/maintenance/blocked-operations

Returns detailed information about currently blocked operations.

#### Request
```http
GET /api/maintenance/blocked-operations HTTP/1.1
Host: your-domain.com
Accept: application/json
```

#### Response

**Success Response (200 OK)**
```json
{
  "blocked_operations": [
    {
      "operation_type": "caption_generation",
      "endpoint_pattern": "/start_caption_generation",
      "description": "AI caption generation operations",
      "blocked_since": "2025-01-15T10:00:00Z",
      "attempt_count": 47,
      "last_attempt": "2025-01-15T10:15:23Z",
      "user_message": "Caption generation is temporarily unavailable due to system maintenance. Please try again after 11:00 AM UTC."
    },
    {
      "operation_type": "job_creation",
      "endpoint_pattern": "/api/jobs/*",
      "description": "Background job creation",
      "blocked_since": "2025-01-15T10:00:00Z",
      "attempt_count": 23,
      "last_attempt": "2025-01-15T10:12:45Z",
      "user_message": "Job creation is temporarily disabled during maintenance. Please try again after maintenance completion."
    }
  ],
  "total_blocked_operations": 6,
  "total_blocked_attempts": 156,
  "maintenance_active_since": "2025-01-15T10:00:00Z"
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `operation_type` | string | Type of blocked operation |
| `endpoint_pattern` | string | URL pattern that is blocked |
| `description` | string | Human-readable description of the operation |
| `blocked_since` | string | ISO 8601 timestamp when blocking started |
| `attempt_count` | integer | Number of blocked attempts for this operation |
| `last_attempt` | string | ISO 8601 timestamp of last blocked attempt |
| `user_message` | string | User-friendly message for this operation type |

### GET /api/maintenance/message

Returns a user-friendly maintenance message for a specific operation type.

#### Request
```http
GET /api/maintenance/message?operation=caption_generation HTTP/1.1
Host: your-domain.com
Accept: application/json
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `operation` | string | No | Specific operation type to get message for |

#### Response

**Success Response (200 OK)**
```json
{
  "message": "Caption generation is temporarily unavailable due to system maintenance. Expected completion: 11:00 AM UTC.",
  "operation_type": "caption_generation",
  "maintenance_active": true,
  "estimated_completion": "2025-01-15T11:00:00Z",
  "alternative_actions": [
    "Review existing captions",
    "Prepare images for processing after maintenance",
    "Check system status for updates"
  ]
}
```

**No Maintenance Response**
```json
{
  "message": "All systems operational",
  "operation_type": null,
  "maintenance_active": false,
  "estimated_completion": null,
  "alternative_actions": []
}
```

### POST /api/maintenance/enable

Enables maintenance mode. Requires admin authentication.

#### Request
```http
POST /api/maintenance/enable HTTP/1.1
Host: your-domain.com
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "reason": "Database optimization and security updates",
  "duration": 3600,
  "mode": "normal",
  "notify_users": true
}
```

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | Reason for maintenance |
| `duration` | integer | No | Estimated duration in seconds |
| `mode` | string | No | Maintenance mode: "normal", "emergency", "test" (default: "normal") |
| `notify_users` | boolean | No | Whether to notify users (default: true) |

#### Response

**Success Response (200 OK)**
```json
{
  "success": true,
  "message": "Maintenance mode enabled successfully",
  "maintenance_status": {
    "is_active": true,
    "mode": "normal",
    "reason": "Database optimization and security updates",
    "estimated_duration": 3600,
    "started_at": "2025-01-15T10:00:00Z",
    "estimated_completion": "2025-01-15T11:00:00Z",
    "enabled_by": "admin"
  },
  "invalidated_sessions": 15,
  "blocked_operations": [
    "caption_generation",
    "job_creation",
    "platform_operations",
    "batch_operations",
    "user_data_modification",
    "image_processing"
  ]
}
```

#### Error Responses

**Unauthorized (401)**
```json
{
  "error": "unauthorized",
  "message": "Admin authentication required"
}
```

**Forbidden (403)**
```json
{
  "error": "insufficient_privileges",
  "message": "Admin privileges required to enable maintenance mode"
}
```

**Conflict (409)**
```json
{
  "error": "maintenance_already_active",
  "message": "Maintenance mode is already active",
  "current_status": {
    "is_active": true,
    "mode": "normal",
    "reason": "Existing maintenance operation",
    "started_at": "2025-01-15T09:30:00Z"
  }
}
```

**Bad Request (400)**
```json
{
  "error": "invalid_request",
  "message": "Invalid maintenance mode parameters",
  "details": {
    "reason": "Reason is required",
    "mode": "Mode must be one of: normal, emergency, test"
  }
}
```

### POST /api/maintenance/disable

Disables maintenance mode. Requires admin authentication.

#### Request
```http
POST /api/maintenance/disable HTTP/1.1
Host: your-domain.com
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "notify_users": true
}
```

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notify_users` | boolean | No | Whether to notify users of completion (default: true) |

#### Response

**Success Response (200 OK)**
```json
{
  "success": true,
  "message": "Maintenance mode disabled successfully",
  "maintenance_duration": 3847,
  "operations_resumed": [
    "caption_generation",
    "job_creation",
    "platform_operations",
    "batch_operations",
    "user_data_modification",
    "image_processing"
  ],
  "disabled_by": "admin",
  "disabled_at": "2025-01-15T11:04:07Z"
}
```

#### Error Responses

**Conflict (409)**
```json
{
  "error": "maintenance_not_active",
  "message": "Maintenance mode is not currently active"
}
```

### POST /api/maintenance/emergency

Activates emergency maintenance mode. Requires admin authentication.

#### Request
```http
POST /api/maintenance/emergency HTTP/1.1
Host: your-domain.com
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "reason": "Critical security incident - immediate system protection required",
  "terminate_jobs": true,
  "grace_period": 30
}
```

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | Emergency reason (required for audit trail) |
| `terminate_jobs` | boolean | No | Whether to terminate running jobs (default: true) |
| `grace_period` | integer | No | Grace period for job termination in seconds (default: 30) |

#### Response

**Success Response (200 OK)**
```json
{
  "success": true,
  "message": "Emergency maintenance mode activated",
  "emergency_status": {
    "is_active": true,
    "mode": "emergency",
    "reason": "Critical security incident - immediate system protection required",
    "started_at": "2025-01-15T14:30:00Z",
    "enabled_by": "admin"
  },
  "terminated_jobs": 5,
  "invalidated_sessions": 23,
  "blocked_operations": [
    "caption_generation",
    "job_creation",
    "platform_operations",
    "batch_operations",
    "user_data_modification",
    "image_processing",
    "read_operations"
  ]
}
```

## WebSocket API (Real-time Updates)

For real-time maintenance status updates, the API supports WebSocket connections.

### WebSocket Endpoint

```
ws://your-domain.com/api/maintenance/ws
```

### Connection

```javascript
const ws = new WebSocket('ws://your-domain.com/api/maintenance/ws');

ws.onopen = function(event) {
    console.log('Connected to maintenance status WebSocket');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Maintenance status update:', data);
};
```

### Message Types

#### Status Update
```json
{
  "type": "status_update",
  "timestamp": "2025-01-15T10:00:00Z",
  "data": {
    "is_active": true,
    "mode": "normal",
    "reason": "Database optimization",
    "estimated_completion": "2025-01-15T11:00:00Z"
  }
}
```

#### Operation Blocked
```json
{
  "type": "operation_blocked",
  "timestamp": "2025-01-15T10:05:23Z",
  "data": {
    "operation_type": "caption_generation",
    "endpoint": "/start_caption_generation",
    "user": "user123",
    "attempt_count": 1
  }
}
```

#### Emergency Activation
```json
{
  "type": "emergency_activated",
  "timestamp": "2025-01-15T14:30:00Z",
  "data": {
    "reason": "Critical security incident",
    "enabled_by": "admin",
    "terminated_jobs": 5,
    "invalidated_sessions": 23
  }
}
```

## Client Libraries

### JavaScript/TypeScript

```javascript
class MaintenanceStatusClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }

    async getStatus() {
        const response = await fetch(`${this.baseUrl}/api/maintenance/status`);
        return await response.json();
    }

    async getBlockedOperations() {
        const response = await fetch(`${this.baseUrl}/api/maintenance/blocked-operations`);
        return await response.json();
    }

    async getMessage(operationType = null) {
        const url = operationType 
            ? `${this.baseUrl}/api/maintenance/message?operation=${operationType}`
            : `${this.baseUrl}/api/maintenance/message`;
        const response = await fetch(url);
        return await response.json();
    }

    connectWebSocket(onMessage) {
        const ws = new WebSocket(`${this.baseUrl.replace('http', 'ws')}/api/maintenance/ws`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            onMessage(data);
        };
        return ws;
    }
}

// Usage
const client = new MaintenanceStatusClient('http://localhost:5000');
const status = await client.getStatus();
console.log('Maintenance active:', status.is_active);
```

### Python

```python
import requests
import json

class MaintenanceStatusClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_status(self):
        response = requests.get(f"{self.base_url}/api/maintenance/status")
        return response.json()

    def get_blocked_operations(self):
        response = requests.get(f"{self.base_url}/api/maintenance/blocked-operations")
        return response.json()

    def get_message(self, operation_type=None):
        url = f"{self.base_url}/api/maintenance/message"
        if operation_type:
            url += f"?operation={operation_type}"
        response = requests.get(url)
        return response.json()

    def enable_maintenance(self, reason, duration=None, mode="normal", token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        data = {
            "reason": reason,
            "mode": mode
        }
        if duration:
            data["duration"] = duration
        
        response = requests.post(
            f"{self.base_url}/api/maintenance/enable",
            json=data,
            headers=headers
        )
        return response.json()

# Usage
client = MaintenanceStatusClient("http://localhost:5000")
status = client.get_status()
print(f"Maintenance active: {status['is_active']}")
```

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient privileges |
| 404 | Not Found - Endpoint not found |
| 409 | Conflict - Operation not allowed in current state |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Maintenance service unavailable |

### Error Response Format

All error responses follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional error details"
  },
  "timestamp": "2025-01-15T10:00:00Z",
  "request_id": "req_123456789"
}
```

## Rate Limiting

The maintenance status API implements rate limiting to prevent abuse:

- **Public endpoints**: 100 requests per minute per IP
- **Admin endpoints**: 20 requests per minute per authenticated user
- **WebSocket connections**: 5 connections per IP

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

## Caching

### Response Caching

- **Status endpoint**: Cached for 30 seconds
- **Blocked operations**: Cached for 60 seconds
- **Message endpoint**: Cached for 60 seconds

### Cache Headers

```http
Cache-Control: public, max-age=30
ETag: "abc123def456"
Last-Modified: Wed, 15 Jan 2025 10:00:00 GMT
```

## Monitoring and Metrics

The API provides metrics for monitoring:

- **Request count**: Number of API requests per endpoint
- **Response time**: Average response time per endpoint
- **Error rate**: Percentage of requests resulting in errors
- **Active connections**: Number of active WebSocket connections

Metrics are available at `/api/maintenance/metrics` (admin only).

## Security Considerations

### Authentication
- Admin endpoints require valid authentication tokens
- WebSocket connections support optional authentication
- Rate limiting prevents abuse of public endpoints

### Data Privacy
- User-specific information is not exposed in public endpoints
- Audit logs maintain user privacy while tracking actions
- Session invalidation data is aggregated, not detailed

### CORS Support
The API supports CORS for browser-based applications:

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

## Conclusion

The Maintenance Status API provides comprehensive access to maintenance mode information and controls. It supports both polling and real-time updates, making it suitable for various integration scenarios from simple status checks to complex monitoring systems.

For additional support or questions about the API, refer to the troubleshooting guide or contact the development team.