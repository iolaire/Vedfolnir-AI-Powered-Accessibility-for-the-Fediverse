# API Documentation: Platform-Aware Vedfolnir

This document provides comprehensive API documentation for the platform-aware Vedfolnir, including endpoints for platform management, caption review, and system monitoring.

## Overview

The Vedfolnir provides a RESTful API that supports:

- **Platform Connection Management:** CRUD operations for platform connections
- **Caption Review Operations:** Programmatic caption review and approval
- **Processing Management:** Trigger and monitor processing jobs
- **Statistics and Analytics:** Access to system metrics and reports
- **User Management:** User account and session management

## Authentication

### API Token Authentication

All API requests require authentication using Bearer tokens.

#### Obtaining an API Token

1. **Web Interface Method:**
   - Log in to the web interface
   - Go to Profile Settings
   - Click "Generate API Token"
   - Copy the generated token

2. **Programmatic Method:**
   ```bash
   curl -X POST http://localhost:5000/api/auth/token \
        -H "Content-Type: application/json" \
        -d '{"username": "your_username", "password": "your_password"}'
   ```

#### Using API Tokens

Include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     http://localhost:5000/api/platforms
```

### Session-Based Authentication

For web interface integration, session-based authentication is also supported:

```bash
# Login to create session
curl -X POST http://localhost:5000/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=your_username&password=your_password" \
     -c cookies.txt

# Use session for subsequent requests
curl -b cookies.txt http://localhost:5000/api/platforms
```

## Base URL and Versioning

- **Base URL:** `http://localhost:5000/api`
- **API Version:** v1 (current)
- **Content Type:** `application/json`

## Platform Management API

### List Platform Connections

Get all platform connections for the authenticated user.

```http
GET /api/platforms
```

**Response:**
```json
{
  "platforms": [
    {
      "id": 1,
      "name": "My Pixelfed",
      "platform_type": "pixelfed",
      "instance_url": "https://pixelfed.social",
      "username": "myusername",
      "is_active": true,
      "is_default": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_used": "2024-01-20T14:22:00Z"
    }
  ]
}
```

### Get Platform Connection

Get details for a specific platform connection.

```http
GET /api/platforms/{platform_id}
```

**Response:**
```json
{
  "id": 1,
  "name": "My Pixelfed",
  "platform_type": "pixelfed",
  "instance_url": "https://pixelfed.social",
  "username": "myusername",
  "is_active": true,
  "is_default": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:22:00Z",
  "last_used": "2024-01-20T14:22:00Z"
}
```

### Create Platform Connection

Create a new platform connection.

```http
POST /api/platforms
```

**Request Body:**
```json
{
  "name": "My Mastodon",
  "platform_type": "mastodon",
  "instance_url": "https://mastodon.social",
  "username": "myusername",
  "access_token": "your_access_token",
  "client_key": "your_client_key",
  "client_secret": "your_client_secret",
  "test_connection": true
}
```

**Response:**
```json
{
  "id": 2,
  "name": "My Mastodon",
  "platform_type": "mastodon",
  "instance_url": "https://mastodon.social",
  "username": "myusername",
  "is_active": true,
  "is_default": false,
  "created_at": "2024-01-20T15:30:00Z",
  "connection_test": {
    "success": true,
    "message": "Connection successful"
  }
}
```

### Update Platform Connection

Update an existing platform connection.

```http
PUT /api/platforms/{platform_id}
```

**Request Body:**
```json
{
  "name": "Updated Platform Name",
  "access_token": "new_access_token",
  "is_default": true
}
```

### Delete Platform Connection

Delete a platform connection.

```http
DELETE /api/platforms/{platform_id}
```

**Response:**
```json
{
  "message": "Platform connection deleted successfully"
}
```

### Test Platform Connection

Test connectivity for a platform connection.

```http
POST /api/platforms/{platform_id}/test
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "details": {
    "response_time": 245,
    "api_version": "v1",
    "account_verified": true
  }
}
```

### Set Default Platform

Set a platform as the user's default.

```http
POST /api/platforms/{platform_id}/set-default
```

**Response:**
```json
{
  "message": "Default platform updated successfully"
}
```

## Platform Context API

### Get Current Platform Context

Get the user's current platform context.

```http
GET /api/context/platform
```

**Response:**
```json
{
  "platform_id": 1,
  "platform_name": "My Pixelfed",
  "platform_type": "pixelfed",
  "instance_url": "https://pixelfed.social",
  "username": "myusername"
}
```

### Switch Platform Context

Switch the user's active platform context.

```http
POST /api/context/platform
```

**Request Body:**
```json
{
  "platform_id": 2
}
```

**Response:**
```json
{
  "message": "Platform context switched successfully",
  "platform": {
    "id": 2,
    "name": "My Mastodon",
    "platform_type": "mastodon",
    "instance_url": "https://mastodon.social"
  }
}
```

## Caption Review API

### List Images for Review

Get images pending review for the current platform.

```http
GET /api/review/images
```

**Query Parameters:**
- `status` (optional): Filter by status (pending, approved, rejected)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `quality_min` (optional): Minimum quality score
- `date_from` (optional): Filter from date (ISO format)
- `date_to` (optional): Filter to date (ISO format)

**Response:**
```json
{
  "images": [
    {
      "id": 123,
      "post_id": "456789",
      "image_url": "https://example.com/image.jpg",
      "generated_caption": "A beautiful sunset over the ocean",
      "quality_score": 0.85,
      "status": "pending",
      "platform_type": "pixelfed",
      "instance_url": "https://pixelfed.social",
      "created_at": "2024-01-20T10:30:00Z",
      "original_post": {
        "url": "https://pixelfed.social/p/username/456789",
        "author": "username",
        "created_at": "2024-01-19T15:22:00Z"
      }
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_next": true
  }
}
```

### Get Image Details

Get detailed information for a specific image.

```http
GET /api/review/images/{image_id}
```

**Response:**
```json
{
  "id": 123,
  "post_id": "456789",
  "image_url": "https://example.com/image.jpg",
  "local_path": "storage/images/123.jpg",
  "generated_caption": "A beautiful sunset over the ocean",
  "edited_caption": null,
  "quality_score": 0.85,
  "status": "pending",
  "platform_type": "pixelfed",
  "instance_url": "https://pixelfed.social",
  "processing_details": {
    "model_used": "llava:7b",
    "processing_time": 2.3,
    "classification": "landscape"
  },
  "original_post": {
    "url": "https://pixelfed.social/p/username/456789",
    "author": "username",
    "content": "Check out this amazing sunset!",
    "created_at": "2024-01-19T15:22:00Z"
  }
}
```

### Approve Caption

Approve a generated caption.

```http
POST /api/review/images/{image_id}/approve
```

**Request Body (optional):**
```json
{
  "edited_caption": "A stunning sunset over the ocean with vibrant orange and pink colors"
}
```

**Response:**
```json
{
  "message": "Caption approved successfully",
  "image": {
    "id": 123,
    "status": "approved",
    "final_caption": "A stunning sunset over the ocean with vibrant orange and pink colors",
    "approved_at": "2024-01-20T16:45:00Z"
  }
}
```

### Reject Caption

Reject a generated caption.

```http
POST /api/review/images/{image_id}/reject
```

**Request Body (optional):**
```json
{
  "reason": "Caption is inaccurate - this is actually a sunrise, not a sunset"
}
```

**Response:**
```json
{
  "message": "Caption rejected successfully",
  "image": {
    "id": 123,
    "status": "rejected",
    "rejection_reason": "Caption is inaccurate - this is actually a sunrise, not a sunset",
    "rejected_at": "2024-01-20T16:45:00Z"
  }
}
```

### Batch Review Operations

Perform batch operations on multiple images.

```http
POST /api/review/batch
```

**Request Body:**
```json
{
  "action": "approve",
  "image_ids": [123, 124, 125],
  "filters": {
    "quality_min": 0.8,
    "status": "pending"
  }
}
```

**Response:**
```json
{
  "message": "Batch operation completed",
  "results": {
    "processed": 3,
    "successful": 2,
    "failed": 1,
    "errors": [
      {
        "image_id": 125,
        "error": "Image already processed"
      }
    ]
  }
}
```

## Processing Management API

### Trigger Processing

Start a processing job for specified users.

```http
POST /api/processing/start
```

**Request Body:**
```json
{
  "users": ["username1", "username2"],
  "platform_id": 1,
  "options": {
    "max_posts": 50,
    "force_reprocess": false,
    "dry_run": false
  }
}
```

**Response:**
```json
{
  "job_id": "proc_20240120_164500_abc123",
  "message": "Processing job started",
  "status": "running",
  "users": ["username1", "username2"],
  "platform": {
    "id": 1,
    "name": "My Pixelfed",
    "platform_type": "pixelfed"
  }
}
```

### Get Processing Status

Check the status of a processing job.

```http
GET /api/processing/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "proc_20240120_164500_abc123",
  "status": "completed",
  "started_at": "2024-01-20T16:45:00Z",
  "completed_at": "2024-01-20T16:52:30Z",
  "progress": {
    "users_processed": 2,
    "users_total": 2,
    "posts_processed": 45,
    "images_processed": 23,
    "captions_generated": 18
  },
  "results": {
    "successful_users": ["username1", "username2"],
    "failed_users": [],
    "total_images": 23,
    "captions_generated": 18,
    "errors": []
  }
}
```

### List Processing Jobs

Get a list of processing jobs.

```http
GET /api/processing/jobs
```

**Query Parameters:**
- `status` (optional): Filter by status (running, completed, failed)
- `platform_id` (optional): Filter by platform
- `limit` (optional): Number of results (default: 20)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "proc_20240120_164500_abc123",
      "status": "completed",
      "platform_name": "My Pixelfed",
      "users": ["username1", "username2"],
      "started_at": "2024-01-20T16:45:00Z",
      "completed_at": "2024-01-20T16:52:30Z",
      "images_processed": 23
    }
  ],
  "pagination": {
    "total": 15,
    "limit": 20,
    "offset": 0
  }
}
```

### Cancel Processing Job

Cancel a running processing job.

```http
POST /api/processing/jobs/{job_id}/cancel
```

**Response:**
```json
{
  "message": "Processing job cancelled successfully",
  "job_id": "proc_20240120_164500_abc123",
  "status": "cancelled"
}
```

## Statistics API

### Platform Statistics

Get statistics for a specific platform.

```http
GET /api/statistics/platform/{platform_id}
```

**Response:**
```json
{
  "platform": {
    "id": 1,
    "name": "My Pixelfed",
    "platform_type": "pixelfed"
  },
  "statistics": {
    "total_posts": 1250,
    "total_images": 890,
    "images_pending": 45,
    "images_approved": 623,
    "images_rejected": 87,
    "images_posted": 598,
    "processing_runs": 25,
    "last_processing": "2024-01-20T16:52:30Z",
    "quality_metrics": {
      "average_quality_score": 0.82,
      "high_quality_count": 456,
      "medium_quality_count": 234,
      "low_quality_count": 89
    }
  }
}
```

### User Statistics

Get statistics for the current user across all platforms.

```http
GET /api/statistics/user
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "username": "myusername"
  },
  "statistics": {
    "total_platforms": 3,
    "active_platforms": 2,
    "total_posts": 2100,
    "total_images": 1456,
    "review_activity": {
      "images_reviewed": 1200,
      "images_approved": 980,
      "images_rejected": 220,
      "approval_rate": 0.817
    },
    "platform_breakdown": [
      {
        "platform_name": "My Pixelfed",
        "platform_type": "pixelfed",
        "posts": 1250,
        "images": 890
      },
      {
        "platform_name": "My Mastodon",
        "platform_type": "mastodon",
        "posts": 850,
        "images": 566
      }
    ]
  }
}
```

### System Statistics

Get overall system statistics (admin only).

```http
GET /api/statistics/system
```

**Response:**
```json
{
  "system": {
    "total_users": 15,
    "active_users": 12,
    "total_platforms": 28,
    "active_platforms": 24,
    "total_posts": 45000,
    "total_images": 32000,
    "processing_statistics": {
      "total_processing_runs": 450,
      "successful_runs": 432,
      "failed_runs": 18,
      "average_processing_time": 125.5
    },
    "quality_statistics": {
      "average_quality_score": 0.79,
      "quality_distribution": {
        "high": 18500,
        "medium": 10200,
        "low": 3300
      }
    }
  }
}
```

## User Management API

### Get Current User

Get information about the current authenticated user.

```http
GET /api/user/profile
```

**Response:**
```json
{
  "id": 1,
  "username": "myusername",
  "email": "user@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-10T09:15:00Z",
  "last_login": "2024-01-20T14:30:00Z",
  "platform_count": 3,
  "preferences": {
    "email_notifications": true,
    "default_platform_id": 1,
    "review_batch_size": 20
  }
}
```

### Update User Profile

Update user profile information.

```http
PUT /api/user/profile
```

**Request Body:**
```json
{
  "email": "newemail@example.com",
  "preferences": {
    "email_notifications": false,
    "review_batch_size": 50
  }
}
```

### Change Password

Change the user's password.

```http
POST /api/user/change-password
```

**Request Body:**
```json
{
  "current_password": "current_password",
  "new_password": "new_secure_password"
}
```

## Health and Monitoring API

### System Health Check

Check overall system health.

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T17:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 12
    },
    "ollama": {
      "status": "healthy",
      "model": "llava:7b",
      "response_time": 245
    },
    "storage": {
      "status": "healthy",
      "disk_usage": "45%",
      "available_space": "15.2GB"
    }
  }
}
```

### Platform Health Check

Check health of all platform connections.

```http
GET /api/health/platforms
```

**Response:**
```json
{
  "platforms": [
    {
      "id": 1,
      "name": "My Pixelfed",
      "status": "healthy",
      "response_time": 156,
      "last_check": "2024-01-20T17:25:00Z"
    },
    {
      "id": 2,
      "name": "My Mastodon",
      "status": "error",
      "error": "Authentication failed",
      "last_check": "2024-01-20T17:25:00Z"
    }
  ]
}
```

## Error Handling

### HTTP Status Codes

The API uses standard HTTP status codes:

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate name)
- `422 Unprocessable Entity` - Validation errors
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Error Response Format

All error responses follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request data is invalid",
    "details": {
      "field": "platform_type",
      "issue": "Must be either 'pixelfed' or 'mastodon'"
    },
    "timestamp": "2024-01-20T17:30:00Z"
  }
}
```

### Common Error Codes

- `AUTHENTICATION_REQUIRED` - No valid authentication provided
- `INSUFFICIENT_PERMISSIONS` - User lacks required permissions
- `VALIDATION_ERROR` - Request data validation failed
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `PLATFORM_CONNECTION_FAILED` - Platform connection test failed
- `PROCESSING_ERROR` - Error during processing operation
- `RATE_LIMIT_EXCEEDED` - Too many requests

## Rate Limiting

### Rate Limit Headers

All API responses include rate limiting headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
```

### Rate Limits

- **General API:** 1000 requests per hour per user
- **Processing API:** 10 processing jobs per hour per user
- **Platform Testing:** 60 tests per hour per platform
- **Batch Operations:** 5 batch operations per hour per user

## SDK and Examples

### Python SDK Example

```python
import requests

class VedfolnirAPI:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    def get_platforms(self):
        response = requests.get(
            f'{self.base_url}/api/platforms',
            headers=self.headers
        )
        return response.json()
    
    def approve_caption(self, image_id, edited_caption=None):
        data = {}
        if edited_caption:
            data['edited_caption'] = edited_caption
        
        response = requests.post(
            f'{self.base_url}/api/review/images/{image_id}/approve',
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
api = VedfolnirAPI('http://localhost:5000', 'your_api_token')
platforms = api.get_platforms()
print(f"Found {len(platforms['platforms'])} platforms")
```

### JavaScript/Node.js Example

```javascript
class VedfolnirAPI {
    constructor(baseUrl, apiToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async getPlatforms() {
        const response = await fetch(`${this.baseUrl}/api/platforms`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async getImagesForReview(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(
            `${this.baseUrl}/api/review/images?${params}`,
            { headers: this.headers }
        );
        return response.json();
    }
}

// Usage
const api = new VedfolnirAPI('http://localhost:5000', 'your_api_token');
const images = await api.getImagesForReview({ status: 'pending', limit: 10 });
console.log(`Found ${images.images.length} images for review`);
```

### cURL Examples

```bash
# Get all platforms
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/platforms

# Create new platform
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"My Platform","platform_type":"pixelfed","instance_url":"https://pixelfed.social","access_token":"token"}' \
     http://localhost:5000/api/platforms

# Approve caption with edit
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"edited_caption":"Improved caption text"}' \
     http://localhost:5000/api/review/images/123/approve

# Start processing job
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"users":["username1"],"platform_id":1}' \
     http://localhost:5000/api/processing/start
```

This API documentation provides comprehensive coverage of all available endpoints in the platform-aware Vedfolnir system. For additional examples and integration guides, refer to the other documentation files.