# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Emergency Monitoring Dashboard

Provides a web-based dashboard for monitoring notification system emergency status,
recovery operations, and system health during critical incidents.
"""

import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from app.services.notification.components.notification_emergency_recovery import NotificationEmergencyRecovery
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from websocket_factory import WebSocketFactory
from websocket_auth_handler import WebSocketAuthHandler
from websocket_namespace_manager import WebSocketNamespaceManager

# Load environment
load_dotenv()

# Create Flask app for emergency dashboard
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'emergency-dashboard-key')

# Initialize emergency system
config = Config()
db_manager = DatabaseManager(config)

try:
    websocket_factory = WebSocketFactory(config)
    auth_handler = WebSocketAuthHandler(config)
    namespace_manager = WebSocketNamespaceManager()
    notification_manager = UnifiedNotificationManager(websocket_factory, auth_handler)
    
    emergency_recovery = NotificationEmergencyRecovery(
        notification_manager,
        websocket_factory,
        auth_handler,
        namespace_manager,
        db_manager
    )
except Exception as e:
    print(f"Warning: Could not initialize emergency recovery system: {e}")
    emergency_recovery = None

# Dashboard HTML template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emergency Monitoring Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #dc3545, #c82333);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .status-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #007bff;
        }
        .status-card.emergency {
            border-left-color: #dc3545;
        }
        .status-card.warning {
            border-left-color: #ffc107;
        }
        .status-card.success {
            border-left-color: #28a745;
        }
        .status-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .status-label {
            color: #666;
            font-size: 0.9em;
        }
        .events-section {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .event-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .event-item:last-child {
            border-bottom: none;
        }
        .event-level {
            padding: 4px 8px;
            border-radius: 4px;
            color: white;
            font-size: 0.8em;
            font-weight: bold;
        }
        .event-level.critical { background-color: #dc3545; }
        .event-level.high { background-color: #fd7e14; }
        .event-level.medium { background-color: #ffc107; color: #000; }
        .event-level.low { background-color: #6c757d; }
        .controls {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
            font-weight: bold;
        }
        .btn-danger { background-color: #dc3545; color: white; }
        .btn-success { background-color: #28a745; color: white; }
        .btn-warning { background-color: #ffc107; color: #000; }
        .btn-info { background-color: #17a2b8; color: white; }
        .auto-refresh {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .timestamp {
            color: #666;
            font-size: 0.8em;
        }
        .health-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .health-healthy { background-color: #28a745; }
        .health-degraded { background-color: #ffc107; }
        .health-critical { background-color: #dc3545; }
        .health-unknown { background-color: #6c757d; }
    </style>
</head>
<body>
    <div class="auto-refresh">
        Auto-refresh: <span id="countdown">30</span>s
    </div>
    
    <div class="container">
        <div class="header">
            <h1>🚨 Emergency Monitoring Dashboard</h1>
            <p>Notification System Emergency Status & Recovery</p>
            <div class="timestamp">Last Updated: <span id="last-updated">{{ timestamp }}</span></div>
        </div>
        
        <div class="status-grid">
            <div class="status-card {{ 'emergency' if emergency_active else 'success' }}">
                <div class="status-label">Emergency Status</div>
                <div class="status-value">
                    {{ '🚨 ACTIVE' if emergency_active else '✅ NORMAL' }}
                </div>
            </div>
            
            <div class="status-card {{ health_status_class }}">
                <div class="status-label">System Health</div>
                <div class="status-value">
                    <span class="health-indicator health-{{ health_status }}"></span>
                    {{ health_status.upper() }}
                </div>
            </div>
            
            <div class="status-card">
                <div class="status-label">Emergency Events (24h)</div>
                <div class="status-value">{{ emergency_events_24h }}</div>
            </div>
            
            <div class="status-card">
                <div class="status-label">Recovery Success Rate</div>
                <div class="status-value">{{ "%.1f"|format(recovery_success_rate * 100) }}%</div>
            </div>
        </div>
        
        <div class="controls">
            <h3>Emergency Controls</h3>
            <button class="btn btn-danger" onclick="activateEmergency()">Activate Emergency Mode</button>
            <button class="btn btn-success" onclick="deactivateEmergency()">Deactivate Emergency Mode</button>
            <button class="btn btn-warning" onclick="runHealthCheck()">Run Health Check</button>
            <button class="btn btn-info" onclick="attemptRecovery()">Attempt Recovery</button>
        </div>
        
        <div class="events-section">
            <h3>Recent Emergency Events</h3>
            {% if recent_events %}
                {% for event in recent_events %}
                <div class="event-item">
                    <div>
                        <strong>{{ event.failure_type }}</strong><br>
                        <small class="timestamp">{{ event.timestamp }}</small>
                    </div>
                    <div>
                        <span class="event-level {{ event.emergency_level }}">{{ event.emergency_level.upper() }}</span>
                        {% if event.recovery_success %}
                            <span style="color: #28a745;">✅ Recovered</span>
                        {% else %}
                            <span style="color: #dc3545;">❌ Failed</span>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p>No recent emergency events</p>
            {% endif %}
        </div>
        
        <div class="events-section">
            <h3>System Components</h3>
            {% for component, status in components.items() %}
            <div class="event-item">
                <div>
                    <strong>{{ component.replace('_', ' ').title() }}</strong>
                </div>
                <div>
                    <span class="health-indicator health-{{ status.status }}"></span>
                    {{ status.status.upper() }}
                    {% if status.error %}
                        <br><small style="color: #dc3545;">{{ status.error }}</small>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <script>
        let countdown = 30;
        
        function updateCountdown() {
            document.getElementById('countdown').textContent = countdown;
            countdown--;
            
            if (countdown < 0) {
                location.reload();
            }
        }
        
        setInterval(updateCountdown, 1000);
        
        function activateEmergency() {
            const reason = prompt('Enter reason for emergency activation:');
            if (reason) {
                fetch('/api/activate-emergency', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        reason: reason,
                        triggered_by: 'dashboard_user'
                    })
                }).then(() => location.reload());
            }
        }
        
        function deactivateEmergency() {
            if (confirm('Are you sure you want to deactivate emergency mode?')) {
                fetch('/api/deactivate-emergency', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        resolved_by: 'dashboard_user'
                    })
                }).then(() => location.reload());
            }
        }
        
        function runHealthCheck() {
            fetch('/api/health-check', {method: 'POST'})
                .then(() => {
                    alert('Health check initiated');
                    setTimeout(() => location.reload(), 2000);
                });
        }
        
        function attemptRecovery() {
            if (confirm('Attempt automatic recovery?')) {
                fetch('/api/attempt-recovery', {method: 'POST'})
                    .then(() => {
                        alert('Recovery attempt initiated');
                        setTimeout(() => location.reload(), 5000);
                    });
            }
        }
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """Main emergency dashboard"""
    try:
        if not emergency_recovery:
            return render_template_string("""
            <h1>Emergency Dashboard Unavailable</h1>
            <p>The emergency recovery system could not be initialized.</p>
            <p>This may indicate a critical system failure.</p>
            <p>Please check system logs and contact administrators immediately.</p>
            """)
        
        # Get emergency status
        status = emergency_recovery.get_emergency_status()
        health = emergency_recovery.run_health_check()
        
        # Calculate 24h emergency events
        recent_events = status.get('recent_events', [])
        now = datetime.now(timezone.utc)
        events_24h = [
            event for event in recent_events
            if (now - datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))).days < 1
        ]
        
        # Determine health status class
        health_status = health.get('overall_status', 'unknown')
        health_status_class = {
            'healthy': 'success',
            'degraded': 'warning',
            'critical': 'emergency',
            'error': 'emergency'
        }.get(health_status, 'warning')
        
        return render_template_string(
            DASHBOARD_TEMPLATE,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            emergency_active=status.get('emergency_active', False),
            health_status=health_status,
            health_status_class=health_status_class,
            emergency_events_24h=len(events_24h),
            recovery_success_rate=status.get('statistics', {}).get('recovery_success_rate', 0),
            recent_events=recent_events[-10:],  # Last 10 events
            components=health.get('components', {})
        )
        
    except Exception as e:
        return f"Dashboard error: {e}", 500


@app.route('/api/status')
def api_status():
    """API endpoint for emergency status"""
    try:
        if not emergency_recovery:
            return jsonify({'error': 'Emergency recovery system unavailable'}), 503
        
        status = emergency_recovery.get_emergency_status()
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health-check', methods=['POST'])
def api_health_check():
    """API endpoint to trigger health check"""
    try:
        if not emergency_recovery:
            return jsonify({'error': 'Emergency recovery system unavailable'}), 503
        
        health = emergency_recovery.run_health_check()
        return jsonify(health)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/activate-emergency', methods=['POST'])
def api_activate_emergency():
    """API endpoint to activate emergency mode"""
    try:
        if not emergency_recovery:
            return jsonify({'error': 'Emergency recovery system unavailable'}), 503
        
        data = request.get_json()
        reason = data.get('reason', 'Manual activation via dashboard')
        triggered_by = data.get('triggered_by', 'dashboard')
        
        success = emergency_recovery.activate_emergency_mode(reason, triggered_by)
        
        return jsonify({
            'success': success,
            'message': 'Emergency mode activated' if success else 'Failed to activate emergency mode'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/deactivate-emergency', methods=['POST'])
def api_deactivate_emergency():
    """API endpoint to deactivate emergency mode"""
    try:
        if not emergency_recovery:
            return jsonify({'error': 'Emergency recovery system unavailable'}), 503
        
        data = request.get_json()
        resolved_by = data.get('resolved_by', 'dashboard')
        
        success = emergency_recovery.deactivate_emergency_mode(resolved_by)
        
        return jsonify({
            'success': success,
            'message': 'Emergency mode deactivated' if success else 'Failed to deactivate emergency mode'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/attempt-recovery', methods=['POST'])
def api_attempt_recovery():
    """API endpoint to attempt automatic recovery"""
    try:
        if not emergency_recovery:
            return jsonify({'error': 'Emergency recovery system unavailable'}), 503
        
        # Simulate recovery attempt
        test_error = Exception("Manual recovery test via dashboard")
        context = {
            'affected_users': [],
            'component': 'dashboard_test',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        success = emergency_recovery.detect_and_recover(test_error, context)
        
        return jsonify({
            'success': success,
            'message': 'Recovery attempt completed' if success else 'Recovery attempt failed'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def main():
    """Main entry point for emergency dashboard"""
    print("Starting Emergency Monitoring Dashboard...")
    print("Dashboard will be available at: http://127.0.0.1:5001/")
    print("Press Ctrl+C to stop")
    
    try:
        app.run(
            host='127.0.0.1',
            port=5001,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
    except Exception as e:
        print(f"Dashboard error: {e}")


if __name__ == '__main__':
    main()