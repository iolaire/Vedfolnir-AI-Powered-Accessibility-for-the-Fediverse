# Session Management API Reference

This document provides a complete API reference for the unified session management system endpoints and functions.

## Table of Contents

1. [REST API Endpoints](#rest-api-endpoints)
2. [Python API Reference](#python-api-reference)
3. [JavaScript API Reference](#javascript-api-reference)
4. [Session Context Schema](#session-context-schema)
5. [Error Codes](#error-codes)
6. [Authentication](#authentication)

## REST API Endpoints

### Session State API

#### GET /api/session_state

Returns the current session state for cross-tab synchronization and client-side session management.

**Authentication:** Required (session cookie)

**Request Headers:**
```
Cookie: session_id=<session-id>
X-Requested-With: XMLHttpRequest
```

**Response (Success - 200):**
```json
{
  "success": true,
  "user": {
    "id": 123,
    "username": "user@example.com",
    "email": "user@example.com",
    "is_active": true
  },
  "platform": {
    "id": 456,
    "name": "My Platform",
    "type": "pixelfed",
    "instance_url": "https://pixelfed.social",
    "username": "myuser",
    "is_default": true
  },
  "session": {
    "session_id": "abc123...",
    "created_at": "2025-01-11T10:00:00Z",
    "last_activity": "2025-01-11T10:30:00Z",
    "expires_at": "2025-01-13T10:00:00Z"
  },
  "timestamp": "2025-01-11T10:30:00Z"
}
```

**Response (No Session - 401):**
```json
{
  "success": false,
  "error": "No active session",
  "error_code": "SESSION_REQUIRED"
}
```

**Response (Session Expired - 401):**
```json
{
  "success": false,
  "error": "Session expired",
  "error_code": "SESSION_EXPIRED",
  "redirect_url": "/login"
}
```

#### POST /api/session/validate

Validates the current session and returns validation status.

**Authentication:** Required (session cookie)
**CSRF Protection:** Required

**Request Headers:**
```
Cookie: session_id=<session-id>
X-CSRFToken: <csrf-token>
Content-Type: application/json
```

**Response (Valid Session - 200):**
```json
{
  "success": true,
  "valid": true,
  "session_id": "abc123...",
  "user_id": 123,
  "platform_id": 456,
  "expires_at": "2025-01-13T10:00:00Z",
  "timestamp": "2025-01-11T10:30:00Z"
}
```

**Response (Invalid Session - 401):**
```json
{
  "success": false,
  "valid": false,
  "error": "Session invalid or expired",
  "error_code": "SESSION_INVALID"
}
```

### Platform Management API

#### POST /api/switch_platform/<int:platform_id>

Switches the current session to a different platform context.

**Authentication:** Required (session cookie)
**CSRF Protection:** Required

**Parameters:**
- `platform_id` (int): ID of the platform to switch to

**Request Headers:**
```
Cookie: session_id=<session-id>
X-CSRFToken: <csrf-token>
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Successfully switched to My Platform (Pixelfed)",
  "platform": {
    "id": 456,
    "name": "My Platform",
    "platform_type": "pixelfed",
    "instance_url": "https://pixelfed.social",
    "username": "myuser",
    "is_default": false
  },
  "timestamp": "2025-01-11T10:30:00Z"
}
```

**Response (Platform Not Found - 404):**
```json
{
  "success": false,
  "error": "Platform not found or not accessible",
  "error_code": "PLATFORM_NOT_FOUND"
}
```

**Response (No Session - 401):**
```json
{
  "success": false,
  "error": "Authentication required",
  "error_code": "SESSION_REQUIRED"
}
```

#### GET /api/user_platforms

Returns all active platforms for the current user.

**Authentication:** Required (session cookie)

**Request Headers:**
```
Cookie: session_id=<session-id>
X-Requested-With: XMLHttpRequest
```

**Response (Success - 200):**
```json
{
  "success": true,
  "platforms": [
    {
      "id": 456,
      "name": "My Pixelfed",
      "platform_type": "pixelfed",
      "instance_url": "https://pixelfed.social",
      "username": "myuser",
      "is_default": true,
      "is_active": true,
      "last_used": "2025-01-11T10:00:00Z"
    },
    {
      "id": 789,
      "name": "My Mastodon",
      "platform_type": "mastodon",
      "instance_url": "https://mastodon.social",
      "username": "myuser",
      "is_default": false,
      "is_active": true,
      "last_used": "2025-01-10T15:30:00Z"
    }
  ],
  "current_platform": {
    "id": 456,
    "name": "My Pixelfed"
  },
  "timestamp": "2025-01-11T10:30:00Z"
}
```

### Session Management API

#### POST /api/session/cleanup

Cleans up expired sessions for the current user.

**Authentication:** Required (session cookie)
**CSRF Protection:** Required

**Request Headers:**
```
Cookie: session_id=<session-id>
X-CSRFToken: <csrf-token>
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
  "success": true,
  "cleaned_sessions": 3,
  "message": "Cleaned up 3 expired sessions",
  "timestamp": "2025-01-11T10:30:00Z"
}
```

#### POST /api/session/refresh

Refreshes the current session, extending its expiration time.

**Authentication:** Required (session cookie)
**CSRF Protection:** Required

**Request Headers:**
```
Cookie: session_id=<session-id>
X-CSRFToken: <csrf-token>
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Session refreshed successfully",
  "expires_at": "2025-01-13T12:30:00Z",
  "timestamp": "2025-01-11T10:30:00Z"
}
```

### Authentication API

#### POST /login

Authenticates user and creates a new session.

**Authentication:** Not required
**CSRF Protection:** Required

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "userpassword",
  "platform_id": 456  // Optional: specific platform to activate
}
```

**Request Headers:**
```
X-CSRFToken: <csrf-token>
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": 123,
    "username": "user@example.com",
    "email": "user@example.com"
  },
  "platform": {
    "id": 456,
    "name": "My Platform",
    "type": "pixelfed"
  },
  "session": {
    "created_at": "2025-01-11T10:30:00Z",
    "expires_at": "2025-01-13T10:30:00Z"
  }
}
```

**Response Headers:**
```
Set-Cookie: session_id=<session-id>; Max-Age=172800; Secure; HttpOnly; SameSite=Lax; Path=/
```

**Response (Invalid Credentials - 401):**
```json
{
  "success": false,
  "error": "Invalid username or password",
  "error_code": "INVALID_CREDENTIALS"
}
```

#### POST /logout

Destroys the current session and logs out the user.

**Authentication:** Required (session cookie)
**CSRF Protection:** Required

**Request Headers:**
```
Cookie: session_id=<session-id>
X-CSRFToken: <csrf-token>
Content-Type: application/json
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Logout successful",
  "timestamp": "2025-01-11T10:30:00Z"
}
```

**Response Headers:**
```
Set-Cookie: session_id=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; HttpOnly; SameSite=Lax; Path=/
```

## Python API Reference

### UnifiedSessionManager

#### Class: UnifiedSessionManager

Main session management class using database as single source of truth.

```python
from unified_session_manager import UnifiedSessionManager
from app.core.database.core.database_manager import DatabaseManager

session_manager = UnifiedSessionManager(db_manager)
```

##### Methods

###### create_session(user_id, platform_connection_id=None)

Creates a new database session.

**Parameters:**
- `user_id` (int): User ID
- `platform_connection_id` (int, optional): Platform connection ID

**Returns:** `str` - Session ID

**Raises:**
- `SessionValidationError`: Invalid user or platform
- `SessionDatabaseError`: Database operation failed

**Example:**
```python
session_id = session_manager.create_session(123, 456)
```

###### get_session_context(session_id)

Retrieves complete session context from database.

**Parameters:**
- `session_id` (str): Session ID

**Returns:** `Dict[str, Any]` or `None` - Session context dictionary

**Example:**
```python
context = session_manager.get_session_context(session_id)
if context:
    user_id = context['user_id']
    platform_id = context['platform_connection_id']
```

###### validate_session(session_id)

Validates session exists and is not expired.

**Parameters:**
- `session_id` (str): Session ID

**Returns:** `bool` - True if valid, False otherwise

**Example:**
```python
if session_manager.validate_session(session_id):
    # Session is valid
    process_request()
```

###### update_platform_context(session_id, platform_connection_id)

Updates active platform for session.

**Parameters:**
- `session_id` (str): Session ID
- `platform_connection_id` (int): New platform ID

**Returns:** `bool` - True if successful, False otherwise

**Example:**
```python
success = session_manager.update_platform_context(session_id, new_platform_id)
```

###### destroy_session(session_id)

Removes session from database.

**Parameters:**
- `session_id` (str): Session ID

**Returns:** `bool` - True if successful, False otherwise

**Example:**
```python
session_manager.destroy_session(session_id)
```

###### cleanup_expired_sessions()

Removes expired sessions.

**Returns:** `int` - Number of sessions cleaned up

**Example:**
```python
count = session_manager.cleanup_expired_sessions()
print(f"Cleaned up {count} expired sessions")
```

### SessionCookieManager

#### Class: SessionCookieManager

Manages secure session cookies containing only session IDs.

```python
from session_cookie_manager import SessionCookieManager

cookie_manager = SessionCookieManager(
    cookie_name='session_id',
    max_age=86400,
    secure=True
)
```

##### Methods

###### set_session_cookie(response, session_id)

Sets secure session cookie.

**Parameters:**
- `response` (Flask Response): Flask response object
- `session_id` (str): Session ID

**Example:**
```python
from flask import make_response
response = make_response(jsonify({'success': True}))
cookie_manager.set_session_cookie(response, session_id)
```

###### get_session_id_from_cookie()

Extracts session ID from request cookie.

**Returns:** `str` or `None` - Session ID if found

**Example:**
```python
session_id = cookie_manager.get_session_id_from_cookie()
```

###### clear_session_cookie(response)

Clears session cookie.

**Parameters:**
- `response` (Flask Response): Flask response object

**Example:**
```python
response = make_response(redirect('/login'))
cookie_manager.clear_session_cookie(response)
```

### Database Session Middleware Functions

#### get_current_session_context()

Gets current session context from Flask g object.

**Returns:** `Dict[str, Any]` or `None` - Session context

**Example:**
```python
from database_session_middleware import get_current_session_context

context = get_current_session_context()
if context:
    user_id = context['user_id']
```

#### get_current_user_id()

Gets current user ID from session context.

**Returns:** `int` or `None` - User ID

**Example:**
```python
from database_session_middleware import get_current_user_id

user_id = get_current_user_id()
if user_id:
    # User is authenticated
    load_user_data(user_id)
```

#### get_current_platform_id()

Gets current platform ID from session context.

**Returns:** `int` or `None` - Platform connection ID

**Example:**
```python
from database_session_middleware import get_current_platform_id

platform_id = get_current_platform_id()
if platform_id:
    # Platform context available
    load_platform_data(platform_id)
```

#### is_session_authenticated()

Checks if current session is authenticated.

**Returns:** `bool` - True if authenticated

**Example:**
```python
from database_session_middleware import is_session_authenticated

if is_session_authenticated():
    # User is logged in
    show_authenticated_content()
else:
    return redirect('/login')
```

#### update_session_platform(platform_id)

Updates current session's platform context.

**Parameters:**
- `platform_id` (int): New platform connection ID

**Returns:** `bool` - True if successful

**Example:**
```python
from database_session_middleware import update_session_platform

success = update_session_platform(new_platform_id)
if success:
    # Platform switched successfully
    reload_platform_data()
```

## JavaScript API Reference

### SessionSync Class

Handles cross-tab session synchronization.

#### Methods

##### syncSessionState()

Manually triggers session state synchronization.

**Example:**
```javascript
if (window.sessionSync) {
    window.sessionSync.syncSessionState();
}
```

##### notifyPlatformSwitch(platformId, platformName)

Notifies other tabs of platform switch.

**Parameters:**
- `platformId` (number): Platform ID
- `platformName` (string): Platform name

**Example:**
```javascript
window.sessionSync.notifyPlatformSwitch(456, 'My Platform');
```

##### getTabId()

Gets unique tab identifier.

**Returns:** `string` - Tab ID

**Example:**
```javascript
const tabId = window.sessionSync.getTabId();
```

##### getPerformanceMetrics()

Gets session sync performance metrics.

**Returns:** `Object` - Performance metrics

**Example:**
```javascript
const metrics = window.sessionSync.getPerformanceMetrics();
console.log('Sync count:', metrics.syncCount);
console.log('Error rate:', metrics.errorRate);
```

### Session Events

#### sessionStateChanged

Fired when session state changes.

**Event Detail:**
```javascript
{
  user: { id: 123, username: "user@example.com" },
  platform: { id: 456, name: "My Platform" },
  session: { session_id: "abc123...", created_at: "..." },
  timestamp: "2025-01-11T10:30:00Z"
}
```

**Example:**
```javascript
window.addEventListener('sessionStateChanged', function(event) {
    const sessionState = event.detail;
    updateUI(sessionState);
});
```

#### platformSwitched

Fired when platform is switched.

**Event Detail:**
```javascript
{
  platformId: 456,
  platformName: "My Platform",
  platformType: "pixelfed",
  timestamp: "2025-01-11T10:30:00Z"
}
```

**Example:**
```javascript
window.addEventListener('platformSwitched', function(event) {
    const switchEvent = event.detail;
    console.log('Switched to:', switchEvent.platformName);
});
```

#### sessionExpired

Fired when session expires.

**Event Detail:**
```javascript
{
  reason: "expired",
  timestamp: "2025-01-11T10:30:00Z"
}
```

**Example:**
```javascript
window.addEventListener('sessionExpired', function(event) {
    // Redirect to login
    window.location.href = '/login';
});
```

## Session Context Schema

### Complete Session Context

```typescript
interface SessionContext {
  session_id: string;
  user_id: number;
  user_info: {
    username: string;
    email: string;
    is_active: boolean;
  };
  platform_connection_id?: number;
  platform_info?: {
    name: string;
    platform_type: 'pixelfed' | 'mastodon';
    instance_url: string;
    username: string;
    is_default: boolean;
  };
  created_at: string;  // ISO 8601 timestamp
  updated_at: string;  // ISO 8601 timestamp
  last_activity: string;  // ISO 8601 timestamp
  expires_at: string;  // ISO 8601 timestamp
}
```

### User Info Schema

```typescript
interface UserInfo {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
}
```

### Platform Info Schema

```typescript
interface PlatformInfo {
  id: number;
  name: string;
  platform_type: 'pixelfed' | 'mastodon';
  instance_url: string;
  username: string;
  is_default: boolean;
  is_active: boolean;
  last_used?: string;  // ISO 8601 timestamp
}
```

## Error Codes

### Session Errors

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `SESSION_REQUIRED` | No session cookie present | 401 |
| `SESSION_EXPIRED` | Session has expired | 401 |
| `SESSION_INVALID` | Session ID is invalid or not found | 401 |
| `SESSION_DATABASE_ERROR` | Database error during session operation | 500 |

### Platform Errors

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `PLATFORM_NOT_FOUND` | Platform ID not found or not accessible | 404 |
| `PLATFORM_INACTIVE` | Platform is deactivated | 400 |
| `PLATFORM_REQUIRED` | Platform context required for operation | 400 |

### Authentication Errors

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | Username or password incorrect | 401 |
| `USER_INACTIVE` | User account is deactivated | 401 |
| `CSRF_TOKEN_MISSING` | CSRF token not provided | 403 |
| `CSRF_TOKEN_INVALID` | CSRF token is invalid | 403 |

### General Errors

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `VALIDATION_ERROR` | Request validation failed | 400 |
| `DATABASE_ERROR` | Database operation failed | 500 |
| `INTERNAL_ERROR` | Unexpected server error | 500 |

## Authentication

### Session Cookie Authentication

All authenticated endpoints require a valid session cookie:

```
Cookie: session_id=<session-id>
```

The session cookie is:
- **HttpOnly**: Cannot be accessed by JavaScript
- **Secure**: Only sent over HTTPS (in production)
- **SameSite=Lax**: CSRF protection while allowing normal navigation
- **Path=/**: Available for entire application

### CSRF Protection

State-changing operations require CSRF token:

```
X-CSRFToken: <csrf-token>
```

Get CSRF token from meta tag:
```javascript
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
```

### Request Examples

#### Authenticated GET Request

```javascript
fetch('/api/session_state', {
    method: 'GET',
    headers: {
        'X-Requested-With': 'XMLHttpRequest'
    },
    credentials: 'same-origin'
});
```

#### Authenticated POST Request

```javascript
fetch('/api/switch_platform/456', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
    },
    credentials: 'same-origin',
    body: JSON.stringify({})
});
```

This comprehensive API reference provides all the information needed to work with the unified session management system.