# Website Improvements - Usage Examples

## Overview

This document provides practical usage examples for the Website Improvements implementation, demonstrating how to use the consolidated frameworks, admin interfaces, and enhanced functionality in real-world scenarios.

## Framework Usage Examples

### Security Framework Usage

#### CSP Middleware Implementation

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

from flask import Flask, render_template, g
from app.core.security.csp.middleware import CSPMiddleware
from app.core.security.access_control import require_admin_access

app = Flask(__name__)

# Initialize CSP middleware
csp_middleware = CSPMiddleware(app)

@app.before_request
def setup_security():
    """Set up security for each request."""
    # Generate CSP nonce
    nonce = csp_middleware.generate_nonce()
    g.csp_nonce = nonce
    
    # Set CSP header
    csp_header = csp_middleware.get_csp_header(nonce)
    g.csp_header = csp_header

@app.after_request
def apply_security_headers(response):
    """Apply security headers to response."""
    if hasattr(g, 'csp_header'):
        response.headers['Content-Security-Policy'] = g.csp_header
    return response

@app.route('/admin/dashboard')
@require_admin_access
def admin_dashboard():
    """Admin dashboard with CSP compliance."""
    return render_template('admin/dashboard.html', csp_nonce=g.csp_nonce)
```

#### Template Usage with CSP Nonces

```html
<!-- admin/dashboard.html -->
<!-- Copyright (C) 2025 iolaire mcfadden. -->
<!-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. -->

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csp-nonce" content="{{ csp_nonce }}">
    <title>Admin Dashboard - Vedfolnir</title>
    
    <!-- CSP-compliant inline styles -->
    <style nonce="{{ csp_nonce }}">
        .admin-dashboard {
            padding: 20px;
            background-color: #f8f9fa;
        }
        .metric-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="admin-dashboard">
        <h1>Admin Dashboard</h1>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>System Status</h3>
                <div id="system-status">Loading...</div>
            </div>
            
            <div class="metric-card">
                <h3>Performance Metrics</h3>
                <div id="performance-metrics">Loading...</div>
            </div>
        </div>
    </div>
    
    <!-- CSP-compliant inline scripts -->
    <script nonce="{{ csp_nonce }}">
        // Load system status
        fetch('/admin/api/system-status')
            .then(response => response.json())
            .then(data => {
                document.getElementById('system-status').innerHTML = 
                    `<span class="status-${data.status}">${data.status.toUpperCase()}</span>`;
            })
            .catch(error => {
                console.error('Error loading system status:', error);
                document.getElementById('system-status').innerHTML = 
                    '<span class="status-error">Error loading status</span>';
            });
        
        // Load performance metrics
        fetch('/admin/api/performance-metrics')
            .then(response => response.json())
            .then(data => {
                const metricsHtml = `
                    <p>Dashboard Load Time: ${data.response_times.admin_dashboard}ms</p>
                    <p>Requests/Second: ${data.throughput.requests_per_second}</p>
                    <p>Error Rate: ${data.error_rates['4xx_errors']}%</p>
                `;
                document.getElementById('performance-metrics').innerHTML = metricsHtml;
            })
            .catch(error => {
                console.error('Error loading performance metrics:', error);
                document.getElementById('performance-metrics').innerHTML = 
                    '<span class="status-error">Error loading metrics</span>';
            });
    </script>
</body>
</html>
```

### Session Management Usage

#### Creating and Managing Sessions

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

from flask import Flask, request, session, jsonify
from app.core.session.manager import SessionManager
from app.core.session.middleware.session_middleware import create_user_session, destroy_current_session
from app.core.database.manager import DatabaseManager
import redis

app = Flask(__name__)

# Initialize components
redis_client = redis.Redis.from_url('redis://localhost:6379/0')
db_manager = DatabaseManager(config)
session_manager = SessionManager(redis_client, db_manager)

@app.route('/login', methods=['POST'])
def login():
    """User login with session creation."""
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Authenticate user (implementation depends on your auth system)
    user = authenticate_user(username, password)
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Create session
    session_id = create_user_session(user.id, user.default_platform_id)
    
    # Set session data
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role.value
    session['platform_connection_id'] = user.default_platform_id
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role.value
        },
        'session_id': session_id
    })

@app.route('/logout', methods=['POST'])
def logout():
    """User logout with session cleanup."""
    # Destroy current session
    destroy_current_session()
    
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/session/status')
def session_status():
    """Get current session status."""
    if 'user_id' not in session:
        return jsonify({'authenticated': False})
    
    # Get detailed session data
    session_data = session_manager.get_session_data(session.sid)
    
    return jsonify({
        'authenticated': True,
        'user_id': session['user_id'],
        'username': session['username'],
        'role': session['role'],
        'platform_connection_id': session.get('platform_connection_id'),
        'session_created': session_data.get('created_at') if session_data else None,
        'last_activity': session_data.get('last_activity') if session_data else None
    })

@app.route('/session/update', methods=['POST'])
def update_session():
    """Update session data."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Update session with new data
    update_data = request.get_json()
    
    # Update Flask session
    if 'platform_connection_id' in update_data:
        session['platform_connection_id'] = update_data['platform_connection_id']
    
    # Update Redis session
    session_manager.update_session(session.sid, {
        'platform_connection_id': update_data.get('platform_connection_id'),
        'last_activity': datetime.utcnow().isoformat()
    })
    
    return jsonify({'success': True, 'message': 'Session updated'})
```

#### Cross-Tab Session Synchronization

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

// static/js/session-sync.js
class SessionSynchronizer {
    constructor() {
        this.lastSessionCheck = Date.now();
        this.sessionCheckInterval = 5000; // 5 seconds
        this.init();
    }
    
    init() {
        // Start session synchronization
        this.startSessionSync();
        
        // Listen for storage events (cross-tab communication)
        window.addEventListener('storage', (e) => {
            if (e.key === 'vedfolnir_session_update') {
                this.handleSessionUpdate(JSON.parse(e.newValue));
            }
        });
        
        // Listen for focus events to check session
        window.addEventListener('focus', () => {
            this.checkSessionStatus();
        });
    }
    
    startSessionSync() {
        setInterval(() => {
            this.checkSessionStatus();
        }, this.sessionCheckInterval);
    }
    
    async checkSessionStatus() {
        try {
            const response = await fetch('/session/status');
            const sessionData = await response.json();
            
            if (!sessionData.authenticated) {
                // Session expired, redirect to login
                this.handleSessionExpired();
                return;
            }
            
            // Update local session data
            this.updateLocalSession(sessionData);
            
            // Broadcast session update to other tabs
            localStorage.setItem('vedfolnir_session_update', JSON.stringify({
                timestamp: Date.now(),
                sessionData: sessionData
            }));
            
        } catch (error) {
            console.error('Session check failed:', error);
        }
    }
    
    handleSessionUpdate(updateData) {
        // Only process updates from other tabs
        if (updateData.timestamp > this.lastSessionCheck) {
            this.updateLocalSession(updateData.sessionData);
        }
    }
    
    updateLocalSession(sessionData) {
        // Update UI elements with session data
        const userInfo = document.querySelector('.user-info');
        if (userInfo && sessionData.authenticated) {
            userInfo.innerHTML = `
                <span class="username">${sessionData.username}</span>
                <span class="role">(${sessionData.role})</span>
            `;
        }
        
        // Update platform selector if present
        const platformSelector = document.querySelector('#platform-selector');
        if (platformSelector && sessionData.platform_connection_id) {
            platformSelector.value = sessionData.platform_connection_id;
        }
        
        this.lastSessionCheck = Date.now();
    }
    
    handleSessionExpired() {
        // Clear local storage
        localStorage.removeItem('vedfolnir_session_update');
        
        // Show session expired message
        alert('Your session has expired. Please log in again.');
        
        // Redirect to login
        window.location.href = '/login';
    }
    
    async switchPlatform(platformId) {
        try {
            const response = await fetch('/session/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    platform_connection_id: platformId
                })
            });
            
            if (response.ok) {
                // Trigger session sync to update other tabs
                this.checkSessionStatus();
                
                // Reload current page to reflect platform change
                window.location.reload();
            }
        } catch (error) {
            console.error('Platform switch failed:', error);
        }
    }
}

// Initialize session synchronizer when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.sessionSync = new SessionSynchronizer();
});
```

### Notification System Usage

#### Sending Admin Notifications

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

from flask import Flask, request, jsonify
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.core.database.manager import DatabaseManager
from app.websocket.core.websocket_manager import WebSocketManager

app = Flask(__name__)

# Initialize components
db_manager = DatabaseManager(config)
websocket_manager = WebSocketManager()
notification_manager = UnifiedNotificationManager(db_manager, websocket_manager)

@app.route('/admin/system/maintenance', methods=['POST'])
def system_maintenance():
    """System maintenance with notifications."""
    action = request.form.get('action')
    
    if action == 'pause_system':
        # Send notification to all admins
        notification_manager.send_admin_alert(
            "System maintenance initiated - system will be paused for maintenance",
            severity='warning'
        )
        
        # Send notification to all users
        notification_manager.broadcast_notification(
            "System maintenance in progress. Some features may be temporarily unavailable.",
            notification_type='maintenance'
        )
        
        # Perform maintenance action
        perform_system_pause()
        
        return jsonify({
            'success': True,
            'message': 'System maintenance initiated'
        })
    
    elif action == 'resume_system':
        # Resume system
        perform_system_resume()
        
        # Notify completion
        notification_manager.send_admin_alert(
            "System maintenance completed - system is now operational",
            severity='info'
        )
        
        notification_manager.broadcast_notification(
            "System maintenance completed. All features are now available.",
            notification_type='success'
        )
        
        return jsonify({
            'success': True,
            'message': 'System maintenance completed'
        })

@app.route('/admin/users/<int:user_id>/notify', methods=['POST'])
def notify_user(user_id):
    """Send notification to specific user."""
    data = request.get_json()
    message = data.get('message')
    notification_type = data.get('type', 'info')
    
    # Send notification
    notification_manager.send_user_notification(
        user_id=user_id,
        message=message,
        notification_type=notification_type
    )
    
    return jsonify({
        'success': True,
        'message': f'Notification sent to user {user_id}'
    })

@app.route('/notifications')
def get_notifications():
    """Get notifications for current user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get user notifications
    notifications = notification_manager.get_user_notifications(user_id, limit=20)
    
    return jsonify({
        'notifications': [
            {
                'id': notif['id'],
                'message': notif['message'],
                'type': notif['type'],
                'created_at': notif['created_at'].isoformat(),
                'read': notif['read']
            }
            for notif in notifications
        ]
    })
```

#### Real-Time Notifications with WebSocket

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

// static/js/notifications.js
class NotificationManager {
    constructor() {
        this.socket = null;
        this.notifications = [];
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupNotificationUI();
        this.loadExistingNotifications();
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected for notifications');
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'notification') {
                this.handleNewNotification(data.notification);
            }
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected, attempting reconnect...');
            setTimeout(() => this.connectWebSocket(), 5000);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    setupNotificationUI() {
        // Create notification container if it doesn't exist
        if (!document.querySelector('.notification-container')) {
            const container = document.createElement('div');
            container.className = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }
        
        // Create notification bell icon
        this.createNotificationBell();
    }
    
    createNotificationBell() {
        const bellContainer = document.querySelector('.notification-bell');
        if (bellContainer) {
            bellContainer.addEventListener('click', () => {
                this.toggleNotificationPanel();
            });
        }
    }
    
    async loadExistingNotifications() {
        try {
            const response = await fetch('/notifications');
            const data = await response.json();
            
            this.notifications = data.notifications || [];
            this.updateNotificationBadge();
        } catch (error) {
            console.error('Failed to load notifications:', error);
        }
    }
    
    handleNewNotification(notification) {
        // Add to notifications array
        this.notifications.unshift(notification);
        
        // Show toast notification
        this.showToastNotification(notification);
        
        // Update badge count
        this.updateNotificationBadge();
        
        // Play notification sound (optional)
        this.playNotificationSound(notification.type);
    }
    
    showToastNotification(notification) {
        const container = document.querySelector('.notification-container');
        
        const toast = document.createElement('div');
        toast.className = `notification-toast notification-${notification.type}`;
        toast.style.cssText = `
            background: white;
            border-left: 4px solid ${this.getTypeColor(notification.type)};
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease-out;
        `;
        
        toast.innerHTML = `
            <div class="notification-header">
                <span class="notification-type">${notification.type.toUpperCase()}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            <div class="notification-message">${notification.message}</div>
            <div class="notification-time">${new Date(notification.created_at).toLocaleTimeString()}</div>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }
    
    updateNotificationBadge() {
        const badge = document.querySelector('.notification-badge');
        const unreadCount = this.notifications.filter(n => !n.read).length;
        
        if (badge) {
            badge.textContent = unreadCount;
            badge.style.display = unreadCount > 0 ? 'block' : 'none';
        }
    }
    
    getTypeColor(type) {
        const colors = {
            'info': '#17a2b8',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545',
            'maintenance': '#6f42c1'
        };
        return colors[type] || colors.info;
    }
    
    playNotificationSound(type) {
        // Only play sound for important notifications
        if (type === 'error' || type === 'warning') {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Ignore audio play errors (user interaction required)
            });
        }
    }
    
    toggleNotificationPanel() {
        // Implementation for notification panel toggle
        console.log('Toggle notification panel');
    }
}

// Initialize notification manager
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});
```

### Monitoring System Usage

#### System Health Monitoring

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

from flask import Flask, jsonify
from app.services.monitoring.system.system_monitor import SystemMonitor
from app.services.monitoring.performance.monitors import PerformanceMonitor
from app.core.database.manager import DatabaseManager
import psutil
import time

app = Flask(__name__)

# Initialize components
db_manager = DatabaseManager(config)
system_monitor = SystemMonitor(db_manager)
performance_monitor = PerformanceMonitor(db_manager)

@app.route('/admin/api/system-status')
def get_system_status():
    """Get comprehensive system status."""
    try:
        # Get system health data
        health_data = system_monitor.get_system_health()
        
        # Get additional system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get database status
        db_status = system_monitor.check_database_health()
        
        # Get Redis status
        redis_status = system_monitor.check_redis_health()
        
        # Determine overall status
        overall_status = 'healthy'
        if cpu_percent > 80 or memory.percent > 85:
            overall_status = 'warning'
        if cpu_percent > 95 or memory.percent > 95 or not db_status['connected']:
            overall_status = 'critical'
        
        return jsonify({
            'status': overall_status,
            'timestamp': time.time(),
            'uptime': health_data.get('uptime', 0),
            'system_metrics': {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available': memory.available,
                'disk_usage': (disk.used / disk.total) * 100,
                'disk_free': disk.free
            },
            'database_status': db_status,
            'redis_status': redis_status,
            'active_sessions': health_data.get('active_sessions', 0),
            'recent_errors': health_data.get('recent_errors', [])
        })
        
    except Exception as e:
        system_monitor.log_error('system_status_api', str(e))
        return jsonify({
            'status': 'error',
            'error': 'Failed to retrieve system status'
        }), 500

@app.route('/admin/api/performance-metrics')
def get_performance_metrics():
    """Get performance metrics."""
    try:
        # Get performance data
        metrics = performance_monitor.get_performance_metrics()
        
        return jsonify({
            'response_times': {
                'admin_dashboard': metrics.get('admin_dashboard_load_time', 0),
                'user_dashboard': metrics.get('user_dashboard_load_time', 0),
                'api_endpoints': metrics.get('api_response_time', 0),
                'caption_generation': metrics.get('caption_generation_time', 0)
            },
            'throughput': {
                'requests_per_second': metrics.get('requests_per_second', 0),
                'captions_per_hour': metrics.get('captions_per_hour', 0),
                'concurrent_users': metrics.get('concurrent_users', 0)
            },
            'error_rates': {
                '4xx_errors': metrics.get('4xx_error_rate', 0),
                '5xx_errors': metrics.get('5xx_error_rate', 0),
                'timeout_errors': metrics.get('timeout_error_rate', 0)
            },
            'database_performance': {
                'query_time_avg': metrics.get('db_query_time_avg', 0),
                'connection_pool_usage': metrics.get('db_pool_usage', 0),
                'slow_queries': metrics.get('slow_query_count', 0)
            },
            'cache_performance': {
                'redis_hit_rate': metrics.get('redis_hit_rate', 0),
                'session_cache_hits': metrics.get('session_cache_hits', 0)
            }
        })
        
    except Exception as e:
        system_monitor.log_error('performance_metrics_api', str(e))
        return jsonify({
            'error': 'Failed to retrieve performance metrics'
        }), 500

# Performance monitoring middleware
@app.before_request
def before_request():
    """Record request start time."""
    g.start_time = time.time()

@app.after_request
def after_request(response):
    """Record request completion and metrics."""
    if hasattr(g, 'start_time'):
        response_time = (time.time() - g.start_time) * 1000  # Convert to ms
        
        # Log performance metric
        performance_monitor.log_performance_metric(
            metric_name=f"{request.endpoint}_response_time",
            value=response_time,
            unit='ms'
        )
        
        # Log slow requests
        if response_time > 1000:  # Slower than 1 second
            system_monitor.log_slow_request(
                endpoint=request.endpoint,
                response_time=response_time,
                method=request.method,
                user_id=session.get('user_id')
            )
    
    return response
```

#### Performance Dashboard

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

// static/js/performance-dashboard.js
class PerformanceDashboard {
    constructor() {
        this.updateInterval = 30000; // 30 seconds
        this.charts = {};
        this.init();
    }
    
    init() {
        this.setupDashboard();
        this.startAutoUpdate();
        this.loadInitialData();
    }
    
    setupDashboard() {
        // Create dashboard container
        const container = document.querySelector('.performance-dashboard');
        if (!container) return;
        
        container.innerHTML = `
            <div class="dashboard-header">
                <h2>Performance Dashboard</h2>
                <div class="last-updated">Last updated: <span id="last-updated">Never</span></div>
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>System Status</h3>
                    <div class="status-indicator" id="system-status">
                        <span class="status-dot"></span>
                        <span class="status-text">Loading...</span>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Response Times</h3>
                    <div class="response-times" id="response-times">
                        <div class="metric-item">
                            <span class="metric-label">Admin Dashboard:</span>
                            <span class="metric-value" id="admin-response-time">-</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">API Endpoints:</span>
                            <span class="metric-value" id="api-response-time">-</span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>System Resources</h3>
                    <div class="resource-meters" id="resource-meters">
                        <div class="meter">
                            <label>CPU Usage</label>
                            <div class="meter-bar">
                                <div class="meter-fill" id="cpu-meter"></div>
                            </div>
                            <span class="meter-value" id="cpu-value">0%</span>
                        </div>
                        <div class="meter">
                            <label>Memory Usage</label>
                            <div class="meter-bar">
                                <div class="meter-fill" id="memory-meter"></div>
                            </div>
                            <span class="meter-value" id="memory-value">0%</span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Error Rates</h3>
                    <div class="error-rates" id="error-rates">
                        <div class="metric-item">
                            <span class="metric-label">4xx Errors:</span>
                            <span class="metric-value" id="4xx-errors">0%</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">5xx Errors:</span>
                            <span class="metric-value" id="5xx-errors">0%</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="charts-section">
                <div class="chart-container">
                    <h3>Response Time Trend</h3>
                    <canvas id="response-time-chart"></canvas>
                </div>
                
                <div class="chart-container">
                    <h3>System Resources</h3>
                    <canvas id="resources-chart"></canvas>
                </div>
            </div>
        `;
    }
    
    async loadInitialData() {
        await this.updateSystemStatus();
        await this.updatePerformanceMetrics();
        this.updateTimestamp();
    }
    
    startAutoUpdate() {
        setInterval(async () => {
            await this.updateSystemStatus();
            await this.updatePerformanceMetrics();
            this.updateTimestamp();
        }, this.updateInterval);
    }
    
    async updateSystemStatus() {
        try {
            const response = await fetch('/admin/api/system-status');
            const data = await response.json();
            
            // Update status indicator
            const statusElement = document.querySelector('#system-status');
            const statusDot = statusElement.querySelector('.status-dot');
            const statusText = statusElement.querySelector('.status-text');
            
            statusDot.className = `status-dot status-${data.status}`;
            statusText.textContent = data.status.toUpperCase();
            
            // Update resource meters
            this.updateResourceMeter('cpu', data.system_metrics.cpu_usage);
            this.updateResourceMeter('memory', data.system_metrics.memory_usage);
            
        } catch (error) {
            console.error('Failed to update system status:', error);
            this.showError('Failed to load system status');
        }
    }
    
    async updatePerformanceMetrics() {
        try {
            const response = await fetch('/admin/api/performance-metrics');
            const data = await response.json();
            
            // Update response times
            document.getElementById('admin-response-time').textContent = 
                `${data.response_times.admin_dashboard.toFixed(1)}ms`;
            document.getElementById('api-response-time').textContent = 
                `${data.response_times.api_endpoints.toFixed(1)}ms`;
            
            // Update error rates
            document.getElementById('4xx-errors').textContent = 
                `${data.error_rates['4xx_errors'].toFixed(1)}%`;
            document.getElementById('5xx-errors').textContent = 
                `${data.error_rates['5xx_errors'].toFixed(1)}%`;
            
            // Update charts
            this.updateCharts(data);
            
        } catch (error) {
            console.error('Failed to update performance metrics:', error);
            this.showError('Failed to load performance metrics');
        }
    }
    
    updateResourceMeter(type, value) {
        const meter = document.getElementById(`${type}-meter`);
        const valueSpan = document.getElementById(`${type}-value`);
        
        if (meter && valueSpan) {
            meter.style.width = `${value}%`;
            meter.className = `meter-fill ${this.getMeterClass(value)}`;
            valueSpan.textContent = `${value.toFixed(1)}%`;
        }
    }
    
    getMeterClass(value) {
        if (value < 50) return 'meter-good';
        if (value < 80) return 'meter-warning';
        return 'meter-critical';
    }
    
    updateCharts(data) {
        // Implementation would use Chart.js or similar library
        // This is a simplified example
        console.log('Updating charts with data:', data);
    }
    
    updateTimestamp() {
        const timestampElement = document.getElementById('last-updated');
        if (timestampElement) {
            timestampElement.textContent = new Date().toLocaleTimeString();
        }
    }
    
    showError(message) {
        // Show error notification
        if (window.notificationManager) {
            window.notificationManager.handleNewNotification({
                type: 'error',
                message: message,
                created_at: new Date().toISOString()
            });
        }
    }
}

// Initialize performance dashboard
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.performance-dashboard')) {
        window.performanceDashboard = new PerformanceDashboard();
    }
});
```

## Admin Interface Usage Examples

### Complete Admin Route Implementation

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.core.security.access_control import require_admin_access
from app.core.session.manager import SessionManager
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.services.monitoring.system.system_monitor import SystemMonitor
from app.core.database.manager import DatabaseManager
from models import PlatformConnection, User

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, 
                    url_prefix='/admin',
                    template_folder='templates',
                    static_folder='static')

# Initialize services (would be done in app factory)
db_manager = DatabaseManager(config)
session_manager = SessionManager(redis_client, db_manager)
notification_manager = UnifiedNotificationManager(db_manager)
system_monitor = SystemMonitor(db_manager)

@admin_bp.route('/')
@require_admin_access
def dashboard():
    """Admin dashboard."""
    try:
        # Log admin access
        system_monitor.log_admin_access(
            current_user.id, 
            '/admin',
            request.remote_addr
        )
        
        # Get dashboard data
        with db_manager.get_session() as session:
            total_users = session.query(User).count()
            total_platforms = session.query(PlatformConnection).count()
            active_sessions = session_manager.get_active_session_count()
        
        # Get system health
        system_health = system_monitor.get_system_health()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_platforms=total_platforms,
                             active_sessions=active_sessions,
                             system_health=system_health)
                             
    except Exception as e:
        notification_manager.send_admin_alert(
            f"Error loading admin dashboard: {str(e)}", 
            severity='error'
        )
        flash('Error loading dashboard', 'error')
        return redirect(url_for('main.index'))

@admin_bp.route('/platforms')
@require_admin_access
def platform_management():
    """Platform management interface."""
    try:
        system_monitor.log_admin_access(
            current_user.id, 
            '/admin/platforms',
            request.remote_addr
        )
        
        with db_manager.get_session() as session:
            platforms = session.query(PlatformConnection).all()
        
        return render_template('admin/platform_management.html', 
                             platforms=platforms)
                             
    except Exception as e:
        notification_manager.send_admin_alert(
            f"Error in platform management: {str(e)}", 
            severity='error'
        )
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/platforms/create', methods=['GET', 'POST'])
@require_admin_access
def create_platform():
    """Create new platform connection."""
    if request.method == 'GET':
        return render_template('admin/create_platform.html')
    
    try:
        # Get form data
        platform_name = request.form.get('platform_name')
        platform_type = request.form.get('platform_type')
        base_url = request.form.get('base_url')
        
        # Validate input
        if not all([platform_name, platform_type, base_url]):
            flash('All fields are required', 'error')
            return render_template('admin/create_platform.html')
        
        # Create platform connection
        with db_manager.get_session() as session:
            platform = PlatformConnection(
                name=platform_name,
                platform_type=platform_type,
                base_url=base_url,
                created_by=current_user.id
            )
            session.add(platform)
            session.commit()
            
            platform_id = platform.id
        
        # Send success notification
        notification_manager.send_admin_alert(
            f"New platform connection created: {platform_name}",
            severity='info'
        )
        
        flash(f'Platform "{platform_name}" created successfully', 'success')
        return redirect(url_for('admin.platform_management'))
        
    except Exception as e:
        notification_manager.send_admin_alert(
            f"Error creating platform: {str(e)}", 
            severity='error'
        )
        flash('Error creating platform', 'error')
        return render_template('admin/create_platform.html')

@admin_bp.route('/system')
@require_admin_access
def system_administration():
    """System administration dashboard."""
    try:
        system_monitor.log_admin_access(
            current_user.id, 
            '/admin/system',
            request.remote_addr
        )
        
        # Get system metrics
        system_health = system_monitor.get_system_health()
        performance_metrics = system_monitor.get_performance_summary()
        
        return render_template('admin/system_administration.html',
                             system_health=system_health,
                             performance_metrics=performance_metrics)
                             
    except Exception as e:
        notification_manager.send_admin_alert(
            f"Error in system administration: {str(e)}", 
            severity='error'
        )
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/security')
@require_admin_access
def security_management():
    """Security management dashboard."""
    try:
        system_monitor.log_admin_access(
            current_user.id, 
            '/admin/security',
            request.remote_addr
        )
        
        # Get security metrics
        security_events = system_monitor.get_recent_security_events(limit=50)
        failed_logins = system_monitor.get_failed_login_attempts(limit=20)
        
        return render_template('admin/security_management.html',
                             security_events=security_events,
                             failed_logins=failed_logins)
                             
    except Exception as e:
        notification_manager.send_admin_alert(
            f"Error in security management: {str(e)}", 
            severity='error'
        )
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/security/audit')
@require_admin_access
def security_audit():
    """Security audit logs."""
    try:
        system_monitor.log_admin_access(
            current_user.id, 
            '/admin/security/audit',
            request.remote_addr
        )
        
        # Get audit logs
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        audit_logs = system_monitor.get_audit_logs(
            page=page, 
            per_page=per_page
        )
        
        return render_template('admin/security_audit.html',
                             audit_logs=audit_logs)
                             
    except Exception as e:
        notification_manager.send_admin_alert(
            f"Error loading security audit: {str(e)}", 
            severity='error'
        )
        return jsonify({'error': 'Internal server error'}), 500

# Register blueprint (would be done in app factory)
# app.register_blueprint(admin_bp)
```

### Admin Template Examples

```html
<!-- admin/dashboard.html -->
<!-- Copyright (C) 2025 iolaire mcfadden. -->
<!-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. -->

{% extends "admin/base_admin.html" %}

{% block title %}Admin Dashboard - Vedfolnir{% endblock %}

{% block content %}
<div class="admin-dashboard">
    <div class="dashboard-header">
        <h1>Admin Dashboard</h1>
        <div class="dashboard-actions">
            <button class="btn btn-primary" onclick="refreshDashboard()">
                <i class="fas fa-sync-alt"></i> Refresh
            </button>
        </div>
    </div>
    
    <div class="dashboard-stats">
        <div class="stat-card">
            <div class="stat-icon">
                <i class="fas fa-users"></i>
            </div>
            <div class="stat-content">
                <h3>{{ total_users }}</h3>
                <p>Total Users</p>
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-icon">
                <i class="fas fa-server"></i>
            </div>
            <div class="stat-content">
                <h3>{{ total_platforms }}</h3>
                <p>Platform Connections</p>
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-icon">
                <i class="fas fa-user-clock"></i>
            </div>
            <div class="stat-content">
                <h3>{{ active_sessions }}</h3>
                <p>Active Sessions</p>
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-icon">
                <i class="fas fa-heartbeat"></i>
            </div>
            <div class="stat-content">
                <h3 class="status-{{ system_health.status }}">
                    {{ system_health.status|title }}
                </h3>
                <p>System Status</p>
            </div>
        </div>
    </div>
    
    <div class="dashboard-grid">
        <div class="dashboard-card">
            <h3>System Health</h3>
            <div class="system-health">
                <div class="health-metric">
                    <span class="metric-label">CPU Usage:</span>
                    <div class="metric-bar">
                        <div class="metric-fill" style="width: {{ system_health.cpu_usage }}%"></div>
                    </div>
                    <span class="metric-value">{{ "%.1f"|format(system_health.cpu_usage) }}%</span>
                </div>
                
                <div class="health-metric">
                    <span class="metric-label">Memory Usage:</span>
                    <div class="metric-bar">
                        <div class="metric-fill" style="width: {{ system_health.memory_usage }}%"></div>
                    </div>
                    <span class="metric-value">{{ "%.1f"|format(system_health.memory_usage) }}%</span>
                </div>
                
                <div class="health-metric">
                    <span class="metric-label">Disk Usage:</span>
                    <div class="metric-bar">
                        <div class="metric-fill" style="width: {{ system_health.disk_usage }}%"></div>
                    </div>
                    <span class="metric-value">{{ "%.1f"|format(system_health.disk_usage) }}%</span>
                </div>
            </div>
        </div>
        
        <div class="dashboard-card">
            <h3>Quick Actions</h3>
            <div class="quick-actions">
                <a href="{{ url_for('admin.platform_management') }}" class="action-btn">
                    <i class="fas fa-server"></i>
                    Manage Platforms
                </a>
                <a href="{{ url_for('admin.system_administration') }}" class="action-btn">
                    <i class="fas fa-cogs"></i>
                    System Admin
                </a>
                <a href="{{ url_for('admin.security_management') }}" class="action-btn">
                    <i class="fas fa-shield-alt"></i>
                    Security
                </a>
                <a href="{{ url_for('admin.security_audit') }}" class="action-btn">
                    <i class="fas fa-clipboard-list"></i>
                    Audit Logs
                </a>
            </div>
        </div>
        
        <div class="dashboard-card">
            <h3>Recent Activity</h3>
            <div class="recent-activity">
                {% if system_health.recent_events %}
                    {% for event in system_health.recent_events[:5] %}
                    <div class="activity-item">
                        <div class="activity-icon">
                            <i class="fas fa-{{ event.icon }}"></i>
                        </div>
                        <div class="activity-content">
                            <p>{{ event.message }}</p>
                            <small>{{ event.timestamp|datetime }}</small>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <p class="no-activity">No recent activity</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<script nonce="{{ csp_nonce }}">
function refreshDashboard() {
    window.location.reload();
}

// Auto-refresh dashboard every 5 minutes
setInterval(refreshDashboard, 300000);
</script>
{% endblock %}
```

This comprehensive usage examples document demonstrates practical implementation of all the consolidated frameworks and enhanced functionality in the Website Improvements specification. Each example includes proper error handling, security considerations, and integration with the unified notification and monitoring systems.