# API Documentation - Web Caption Generation

## Overview
This document describes the REST API endpoints and WebSocket events for the web-based caption generation system.

## Authentication
All API endpoints require user authentication via session cookies or API tokens.

```http
Cookie: session=<session_token>
```

## REST API Endpoints

### Caption Generation

#### Start Caption Generation
Start a new caption generation task for the current user and platform.

```http
POST /api/caption-generation/start
Content-Type: application/json

{
  "max_posts_per_run": 50,
  "caption_max_length": 500,
  "include_hashtags": true
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Caption generation started successfully"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "User already has an active task",
  "error_code": "ACTIVE_TASK_EXISTS"
}
```

#### Get Task Status
Retrieve the current status of a caption generation task.

```http
GET /api/caption-generation/status/{task_id}
```

**Response:**
```json
{
  "success": true,
  "status": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "progress_percent": 45,
    "current_step": "Processing images",
    "created_at": "2024-01-15T14:30:00Z",
    "started_at": "2024-01-15T14:30:05Z",
    "estimated_completion": "2024-01-15T14:40:00Z",
    "progress_details": {
      "posts_processed": 15,
      "total_posts": 33,
      "captions_generated": 12,
      "errors": 1
    }
  }
}
```

#### Cancel Task
Cancel an active caption generation task.

```http
POST /api/caption-generation/cancel/{task_id}
```

**Response:**
```json
{
  "success": true,
  "cancelled": true,
  "message": "Task cancelled successfully"
}
```

#### Get Task Results
Retrieve the results of a completed caption generation task.

```http
GET /api/caption-generation/results/{task_id}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "total_posts_processed": 33,
    "captions_generated": 28,
    "captions_updated": 25,
    "errors": 3,
    "completion_time": 420,
    "error_details": [
      {
        "post_id": "post123",
        "error": "Image could not be processed",
        "error_code": "IMAGE_PROCESSING_FAILED"
      }
    ]
  }
}
```

#### Get Task History
Retrieve the user's caption generation task history.

```http
GET /api/caption-generation/history?limit=10&offset=0
```

**Response:**
```json
{
  "success": true,
  "history": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "created_at": "2024-01-15T14:30:00Z",
      "completed_at": "2024-01-15T14:37:00Z",
      "posts_processed": 33,
      "captions_generated": 28
    }
  ],
  "total_count": 25,
  "has_more": true
}
```

### Settings Management

#### Get User Settings
Retrieve the user's caption generation settings for the current platform.

```http
GET /api/caption-generation/settings
```

**Response:**
```json
{
  "success": true,
  "settings": {
    "max_posts_per_run": 50,
    "caption_max_length": 500,
    "caption_optimal_min_length": 80,
    "caption_optimal_max_length": 200,
    "include_hashtags": true,
    "auto_approve_simple": false,
    "use_enhanced_classification": true
  }
}
```

#### Save User Settings
Save the user's caption generation settings for the current platform.

```http
POST /api/caption-generation/settings
Content-Type: application/json

{
  "max_posts_per_run": 25,
  "caption_max_length": 400,
  "include_hashtags": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings saved successfully"
}
```

### Admin Endpoints

#### Get System Overview
Retrieve system-wide statistics and health information (admin only).

```http
GET /api/admin/system-overview
```

**Response:**
```json
{
  "success": true,
  "overview": {
    "users": {
      "total": 150,
      "active": 45,
      "active_last_24h": 23
    },
    "platforms": {
      "total": 200,
      "active": 180
    },
    "tasks": {
      "total": 1250,
      "active": 5,
      "completed": 1200,
      "failed": 45
    },
    "system_health": "healthy"
  }
}
```

#### Get Active Tasks
Retrieve all currently active caption generation tasks (admin only).

```http
GET /api/admin/active-tasks
```

**Response:**
```json
{
  "success": true,
  "active_tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": 123,
      "username": "john_doe",
      "platform_name": "Mastodon",
      "status": "running",
      "progress_percent": 45,
      "started_at": "2024-01-15T14:30:00Z",
      "current_step": "Processing images"
    }
  ]
}
```

#### Cancel Task (Admin)
Cancel any user's caption generation task (admin only).

```http
POST /api/admin/cancel-task/{task_id}
```

**Response:**
```json
{
  "success": true,
  "cancelled": true,
  "message": "Task cancelled by administrator"
}
```

## WebSocket Events

### Connection
Connect to the WebSocket endpoint for real-time updates:

```javascript
const socket = io('/caption-generation');
```

### Authentication
Authenticate the WebSocket connection:

```javascript
socket.emit('authenticate', {
  task_id: '550e8400-e29b-41d4-a716-446655440000'
});
```

### Events

#### Progress Update
Receive real-time progress updates for a task:

```javascript
socket.on('progress_update', (data) => {
  console.log('Progress:', data);
  // {
  //   task_id: '550e8400-e29b-41d4-a716-446655440000',
  //   progress_percent: 45,
  //   current_step: 'Processing images',
  //   details: {
  //     posts_processed: 15,
  //     total_posts: 33
  //   }
  // }
});
```

#### Task Completed
Receive notification when a task completes:

```javascript
socket.on('task_completed', (data) => {
  console.log('Task completed:', data);
  // {
  //   task_id: '550e8400-e29b-41d4-a716-446655440000',
  //   status: 'completed',
  //   results: {
  //     total_posts_processed: 33,
  //     captions_generated: 28
  //   }
  // }
});
```

#### Task Failed
Receive notification when a task fails:

```javascript
socket.on('task_failed', (data) => {
  console.log('Task failed:', data);
  // {
  //   task_id: '550e8400-e29b-41d4-a716-446655440000',
  //   status: 'failed',
  //   error_message: 'Platform connection failed',
  //   error_code: 'PLATFORM_ERROR'
  // }
});
```

#### Error
Receive error notifications:

```javascript
socket.on('error', (data) => {
  console.error('WebSocket error:', data);
  // {
  //   error: 'Authentication failed',
  //   error_code: 'AUTH_FAILED'
  // }
});
```

## Error Codes

### Task Management Errors
- `ACTIVE_TASK_EXISTS`: User already has an active task
- `TASK_NOT_FOUND`: Specified task does not exist
- `TASK_NOT_AUTHORIZED`: User not authorized to access task
- `TASK_CANNOT_BE_CANCELLED`: Task is in a state that cannot be cancelled

### Platform Errors
- `PLATFORM_CONNECTION_FAILED`: Cannot connect to platform
- `PLATFORM_AUTH_FAILED`: Platform authentication failed
- `PLATFORM_RATE_LIMITED`: Platform API rate limit exceeded
- `PLATFORM_UNAVAILABLE`: Platform service is unavailable

### Validation Errors
- `INVALID_SETTINGS`: Invalid settings provided
- `INVALID_TASK_ID`: Task ID format is invalid
- `MISSING_REQUIRED_FIELD`: Required field is missing
- `VALUE_OUT_OF_RANGE`: Setting value is outside allowed range

### System Errors
- `SYSTEM_OVERLOADED`: System is at capacity
- `DATABASE_ERROR`: Database operation failed
- `AI_SERVICE_UNAVAILABLE`: AI caption generation service unavailable
- `INTERNAL_ERROR`: Unexpected system error

## Rate Limits

### API Rate Limits
- **General API**: 100 requests per minute per user
- **Start Generation**: 5 requests per hour per user
- **Status Checks**: 60 requests per minute per user
- **Settings Updates**: 10 requests per minute per user

### WebSocket Limits
- **Connections**: 5 concurrent connections per user
- **Messages**: 100 messages per minute per connection

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "details": {
    "field": "Additional error context"
  }
}
```

## SDK Examples

### JavaScript/Node.js
```javascript
class CaptionGenerationAPI {
  constructor(baseUrl, sessionToken) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Content-Type': 'application/json',
      'Cookie': `session=${sessionToken}`
    };
  }

  async startGeneration(settings) {
    const response = await fetch(`${this.baseUrl}/api/caption-generation/start`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(settings)
    });
    return response.json();
  }

  async getStatus(taskId) {
    const response = await fetch(`${this.baseUrl}/api/caption-generation/status/${taskId}`, {
      headers: this.headers
    });
    return response.json();
  }
}
```

### Python
```python
import requests

class CaptionGenerationAPI:
    def __init__(self, base_url, session_token):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.cookies.set('session', session_token)
    
    def start_generation(self, settings):
        response = self.session.post(
            f"{self.base_url}/api/caption-generation/start",
            json=settings
        )
        return response.json()
    
    def get_status(self, task_id):
        response = self.session.get(
            f"{self.base_url}/api/caption-generation/status/{task_id}"
        )
        return response.json()
```