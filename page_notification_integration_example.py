# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Page Notification Integration Example

This module demonstrates how to integrate the Page Notification Manager with a Flask
application, including setup, configuration, and usage examples.
"""

import logging
from flask import Flask, render_template, session, request
from dotenv import load_dotenv

from config import Config
from database import DatabaseManager
from session_manager_v2 import SessionManagerV2
from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager
from unified_notification_manager import UnifiedNotificationManager
from page_notification_integrator import PageNotificationIntegrator, PageType
from routes.page_notification_routes import register_page_notification_routes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app_with_page_notifications():
    """
    Create Flask app with page notification integration
    
    Returns:
        Configured Flask app with page notification system
    """
    # Load environment
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    config = Config()
    app.config.from_object(config)
    
    # Initialize core components
    db_manager = DatabaseManager(config)
    session_manager = SessionManagerV2(config, db_manager)
    
    # Initialize WebSocket components
    websocket_config_manager = WebSocketConfigManager(config)
    cors_manager = CORSManager(websocket_config_manager)
    websocket_factory = WebSocketFactory(websocket_config_manager, cors_manager, db_manager, session_manager)
    auth_handler = WebSocketAuthHandler(db_manager, session_manager)
    
    # Create SocketIO instance
    socketio = websocket_factory.create_socketio_instance(app)
    
    # Initialize namespace manager
    namespace_manager = WebSocketNamespaceManager(socketio, auth_handler)
    
    # Initialize unified notification manager
    notification_manager = UnifiedNotificationManager(
        websocket_factory, auth_handler, namespace_manager, db_manager
    )
    
    # Initialize page notification integrator
    page_integrator = PageNotificationIntegrator(
        websocket_factory, auth_handler, namespace_manager, notification_manager
    )
    
    # Store components in app context
    app.db_manager = db_manager
    app.session_manager = session_manager
    app.socketio = socketio
    app.notification_manager = notification_manager
    app.page_notification_integrator = page_integrator
    
    # Register routes
    register_page_notification_routes(app)
    
    # Setup example routes
    setup_example_routes(app)
    
    logger.info("Flask app with page notifications created successfully")
    return app, socketio


def setup_example_routes(app):
    """
    Setup example routes demonstrating page notification integration
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/')
    def user_dashboard():
        """User dashboard with notification integration"""
        return render_template('examples/user_dashboard.html',
                             page_id='user-dashboard-main',
                             page_type='user_dashboard')
    
    @app.route('/caption-processing')
    def caption_processing():
        """Caption processing page with progress notifications"""
        return render_template('examples/caption_processing.html',
                             page_id='caption-processing-main',
                             page_type='caption_processing')
    
    @app.route('/platform-management')
    def platform_management():
        """Platform management page with status notifications"""
        return render_template('examples/platform_management.html',
                             page_id='platform-management-main',
                             page_type='platform_management')
    
    @app.route('/admin')
    def admin_dashboard():
        """Admin dashboard with system notifications"""
        # Check admin access
        if not session.get('role') == 'admin':
            return "Access denied", 403
        
        return render_template('examples/admin_dashboard.html',
                             page_id='admin-dashboard-main',
                             page_type='admin_dashboard')
    
    @app.route('/admin/users')
    def user_management():
        """User management page with admin notifications"""
        # Check admin access
        if not session.get('role') == 'admin':
            return "Access denied", 403
        
        return render_template('examples/user_management.html',
                             page_id='user-management-main',
                             page_type='user_management')
    
    @app.route('/test-notifications')
    def test_notifications():
        """Test page for notification functionality"""
        return render_template('examples/test_notifications.html',
                             page_id='test-notifications-main',
                             page_type='user_dashboard')
    
    @app.route('/api/test/send-notification', methods=['POST'])
    def send_test_notification():
        """Send test notification"""
        try:
            data = request.get_json()
            notification_type = data.get('type', 'info')
            title = data.get('title', 'Test Notification')
            message = data.get('message', 'This is a test notification')
            
            # Send notification through unified notification manager
            from unified_notification_manager import NotificationMessage, NotificationType, NotificationPriority
            
            notification = NotificationMessage(
                id=f"test-{int(time.time())}",
                type=NotificationType(notification_type.upper()),
                title=title,
                message=message,
                user_id=session.get('user_id'),
                priority=NotificationPriority.NORMAL
            )
            
            success = app.notification_manager.send_user_notification(
                session.get('user_id'), notification
            )
            
            return {'success': success, 'message': 'Test notification sent'}
            
        except Exception as e:
            logger.error(f"Failed to send test notification: {e}")
            return {'success': False, 'error': str(e)}, 500


def create_example_templates():
    """
    Create example templates for testing page notification integration
    """
    import os
    
    # Create templates directory if it doesn't exist
    templates_dir = 'templates/examples'
    os.makedirs(templates_dir, exist_ok=True)
    
    # User Dashboard Template
    user_dashboard_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Dashboard - Vedfolnir</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
</head>
<body>
    <div class="container">
        <h1>User Dashboard</h1>
        <p>Welcome to your dashboard. Real-time notifications are enabled.</p>
        
        <div class="dashboard-content">
            <div class="card">
                <h3>Caption Processing</h3>
                <p>Monitor your caption generation progress here.</p>
                <button onclick="testCaptionProgress()">Test Caption Progress</button>
            </div>
            
            <div class="card">
                <h3>Platform Status</h3>
                <p>Check your platform connections and status.</p>
                <button onclick="testPlatformStatus()">Test Platform Status</button>
            </div>
        </div>
    </div>
    
    <!-- Include page notification integration -->
    {% include 'components/page_notification_integration.html' %}
    
    <script>
        function testCaptionProgress() {
            // Simulate caption progress notification
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'progress',
                    title: 'Caption Generation',
                    message: 'Processing image 3 of 10...',
                    progress: 30,
                    auto_hide: false
                });
            }
        }
        
        function testPlatformStatus() {
            // Simulate platform status notification
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'success',
                    title: 'Platform Connected',
                    message: 'Successfully connected to Pixelfed instance',
                    auto_hide: true,
                    duration: 3000
                });
            }
        }
    </script>
    
    <style>
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .dashboard-content { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        button { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</body>
</html>
    '''
    
    # Caption Processing Template
    caption_processing_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Caption Processing - Vedfolnir</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
</head>
<body>
    <div class="container">
        <h1>Caption Processing</h1>
        <p>Generate and review image captions with real-time progress updates.</p>
        
        <div class="processing-controls">
            <button onclick="startCaptionGeneration()">Start Caption Generation</button>
            <button onclick="simulateProgress()">Simulate Progress</button>
            <button onclick="simulateCompletion()">Simulate Completion</button>
            <button onclick="simulateError()">Simulate Error</button>
        </div>
        
        <div class="progress-display">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill" style="width: 0%"></div>
            </div>
            <div class="progress-text" id="progressText">Ready to start</div>
        </div>
    </div>
    
    <!-- Include page notification integration with custom config -->
    {% set notification_config = {
        'enabled_types': ['caption', 'system', 'maintenance'],
        'auto_hide': true,
        'max_notifications': 3,
        'position': 'bottom-center',
        'show_progress': true
    } %}
    {% set websocket_events = ['caption_progress', 'caption_status', 'caption_complete', 'caption_error'] %}
    {% include 'components/page_notification_integration.html' %}
    
    <script>
        let currentProgress = 0;
        
        function startCaptionGeneration() {
            currentProgress = 0;
            updateProgress(0, 'Starting caption generation...');
            
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'info',
                    title: 'Caption Generation Started',
                    message: 'Processing your images...',
                    auto_hide: true,
                    duration: 3000
                });
            }
        }
        
        function simulateProgress() {
            currentProgress = Math.min(currentProgress + 20, 90);
            updateProgress(currentProgress, `Processing image ${Math.floor(currentProgress/20) + 1} of 5...`);
            
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'progress',
                    title: 'Caption Generation Progress',
                    message: `Processing image ${Math.floor(currentProgress/20) + 1} of 5...`,
                    progress: currentProgress,
                    auto_hide: false
                });
            }
        }
        
        function simulateCompletion() {
            currentProgress = 100;
            updateProgress(100, 'Caption generation complete!');
            
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'success',
                    title: 'Caption Generation Complete',
                    message: 'All captions have been generated successfully',
                    auto_hide: true,
                    duration: 5000
                });
            }
        }
        
        function simulateError() {
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'error',
                    title: 'Caption Generation Error',
                    message: 'Failed to process image. Please try again.',
                    auto_hide: false,
                    actions: [
                        { text: 'Retry', type: 'primary', handler: () => startCaptionGeneration() },
                        { text: 'Skip', handler: () => simulateProgress() }
                    ]
                });
            }
        }
        
        function updateProgress(percent, text) {
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('progressText').textContent = text;
        }
        
        // Custom event handlers for caption processing
        window.handleCaptionProgress = function(data) {
            console.log('Caption progress received:', data);
            updateProgress(data.progress || 0, data.message || 'Processing...');
        };
        
        window.handleCaptionComplete = function(data) {
            console.log('Caption generation complete:', data);
            updateProgress(100, 'Complete!');
        };
        
        window.handleCaptionError = function(data) {
            console.error('Caption generation error:', data);
            updateProgress(currentProgress, 'Error occurred');
        };
    </script>
    
    <style>
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .processing-controls { margin: 20px 0; }
        .processing-controls button { margin-right: 10px; margin-bottom: 10px; }
        .progress-display { margin: 30px 0; }
        .progress-bar { width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: #007bff; transition: width 0.3s ease; }
        .progress-text { margin-top: 10px; text-align: center; font-weight: 500; }
        button { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</body>
</html>
    '''
    
    # Admin Dashboard Template
    admin_dashboard_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Vedfolnir</title>
    <meta name="csrf-token" content="{{ csrf_token() }}">
</head>
<body>
    <div class="container">
        <h1>Admin Dashboard</h1>
        <p>System administration and monitoring with real-time notifications.</p>
        
        <div class="admin-controls">
            <button onclick="testSystemStatus()">Test System Status</button>
            <button onclick="testSecurityAlert()">Test Security Alert</button>
            <button onclick="testMaintenanceNotification()">Test Maintenance</button>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3>System Health</h3>
                <div class="status-indicator green">Online</div>
            </div>
            
            <div class="card">
                <h3>Active Users</h3>
                <div class="metric">42</div>
            </div>
            
            <div class="card">
                <h3>Processing Queue</h3>
                <div class="metric">7 jobs</div>
            </div>
        </div>
    </div>
    
    <!-- Include page notification integration for admin -->
    {% set notification_config = {
        'enabled_types': ['system', 'admin', 'security', 'maintenance'],
        'auto_hide': false,
        'max_notifications': 10,
        'position': 'top-center',
        'show_progress': false
    } %}
    {% set websocket_events = ['system_status', 'admin_notification', 'security_alert', 'maintenance_status'] %}
    {% include 'components/page_notification_integration.html' %}
    
    <script>
        function testSystemStatus() {
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'info',
                    title: 'System Status Update',
                    message: 'All systems operating normally. CPU: 45%, Memory: 62%',
                    auto_hide: true,
                    duration: 5000
                });
            }
        }
        
        function testSecurityAlert() {
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'error',
                    title: 'Security Alert',
                    message: 'Multiple failed login attempts detected from IP 192.168.1.100',
                    auto_hide: false,
                    actions: [
                        { text: 'Block IP', type: 'primary', handler: () => alert('IP blocked') },
                        { text: 'View Details', handler: () => alert('Viewing details') }
                    ]
                });
            }
        }
        
        function testMaintenanceNotification() {
            if (window.pageNotificationIntegrator) {
                window.pageNotificationIntegrator.showNotification({
                    type: 'warning',
                    title: 'Scheduled Maintenance',
                    message: 'System maintenance scheduled for tonight at 2:00 AM EST',
                    auto_hide: false,
                    actions: [
                        { text: 'Reschedule', handler: () => alert('Rescheduling') },
                        { text: 'Notify Users', handler: () => alert('Users notified') }
                    ]
                });
            }
        }
    </script>
    
    <style>
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .admin-controls { margin: 20px 0; }
        .admin-controls button { margin-right: 10px; margin-bottom: 10px; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .status-indicator { padding: 8px 16px; border-radius: 20px; color: white; font-weight: 500; }
        .status-indicator.green { background: #28a745; }
        .metric { font-size: 2em; font-weight: bold; color: #007bff; }
        button { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</body>
</html>
    '''
    
    # Write template files
    with open(f'{templates_dir}/user_dashboard.html', 'w') as f:
        f.write(user_dashboard_template)
    
    with open(f'{templates_dir}/caption_processing.html', 'w') as f:
        f.write(caption_processing_template)
    
    with open(f'{templates_dir}/admin_dashboard.html', 'w') as f:
        f.write(admin_dashboard_template)
    
    logger.info("Example templates created successfully")


def run_integration_example():
    """
    Run the page notification integration example
    """
    try:
        # Create example templates
        create_example_templates()
        
        # Create Flask app with page notifications
        app, socketio = create_app_with_page_notifications()
        
        # Set up mock session for testing
        @app.before_request
        def setup_mock_session():
            if not session.get('user_id'):
                session['user_id'] = 1
                session['username'] = 'test_user'
                session['role'] = 'admin'  # For admin page access
                session['permissions'] = ['system_management', 'user_management']
        
        logger.info("Starting page notification integration example...")
        logger.info("Available routes:")
        logger.info("  - http://localhost:5000/ (User Dashboard)")
        logger.info("  - http://localhost:5000/caption-processing (Caption Processing)")
        logger.info("  - http://localhost:5000/admin (Admin Dashboard)")
        logger.info("  - http://localhost:5000/test-notifications (Test Page)")
        
        # Run the app
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        logger.error(f"Failed to run integration example: {e}")
        raise


if __name__ == '__main__':
    import time
    run_integration_example()