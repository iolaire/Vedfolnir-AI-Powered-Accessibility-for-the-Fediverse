# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Performance Dashboard

Provides a comprehensive web-based dashboard for monitoring and managing
WebSocket performance, including real-time metrics, optimization controls,
and scalability testing.
"""

import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from websocket_debug_logger import get_debug_logger, DebugLevel
from websocket_performance_monitor import WebSocketPerformanceMonitor, LoadLevel, PerformanceLevel
from websocket_performance_optimizer import WebSocketPerformanceOptimizer, OptimizationStrategy
from websocket_scalability_tester import WebSocketScalabilityTester, create_load_test_config


class WebSocketPerformanceDashboard:
    """Comprehensive WebSocket performance dashboard"""
    
    def __init__(self, performance_monitor: WebSocketPerformanceMonitor,
                 performance_optimizer: WebSocketPerformanceOptimizer = None,
                 scalability_tester: WebSocketScalabilityTester = None,
                 port: int = 5002):
        self.performance_monitor = performance_monitor
        self.performance_optimizer = performance_optimizer
        self.scalability_tester = scalability_tester or WebSocketScalabilityTester()
        self.port = port
        
        self.app = Flask(__name__)
        self.app.secret_key = 'websocket_performance_dashboard_key'
        
        self.logger = get_debug_logger('performance_dashboard', DebugLevel.INFO)
        
        # Dashboard state
        self.active_tests = {}
        self.dashboard_config = {
            'refresh_interval': 5000,  # milliseconds
            'chart_history_points': 100,
            'alert_thresholds': {
                'cpu_usage': 80,
                'memory_usage': 85,
                'error_rate': 0.05,
                'latency': 200
            }
        }
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Flask routes for the dashboard"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template_string(self._get_dashboard_template())
            
        @self.app.route('/api/performance/current')
        def api_current_performance():
            """Get current performance metrics"""
            return jsonify(self.performance_monitor.get_current_performance_summary())
            
        @self.app.route('/api/performance/history')
        def api_performance_history():
            """Get performance history"""
            hours = request.args.get('hours', 24, type=int)
            return jsonify(self.performance_monitor.get_performance_history(hours))
            
        @self.app.route('/api/performance/scalability')
        def api_scalability_metrics():
            """Get scalability metrics"""
            return jsonify(self.performance_monitor.get_scalability_metrics())
            
        @self.app.route('/api/optimization/recommendations')
        def api_optimization_recommendations():
            """Get optimization recommendations"""
            if self.performance_optimizer:
                return jsonify(self.performance_optimizer.get_optimization_recommendations())
            return jsonify([])
            
        @self.app.route('/api/optimization/history')
        def api_optimization_history():
            """Get optimization history"""
            if self.performance_optimizer:
                hours = request.args.get('hours', 24, type=int)
                return jsonify(self.performance_optimizer.get_optimization_history(hours))
            return jsonify([])
            
        @self.app.route('/api/optimization/apply', methods=['POST'])
        def api_apply_optimization():
            """Apply optimization now"""
            if not self.performance_optimizer:
                return jsonify({'error': 'Optimizer not available'}), 400
                
            try:
                results = self.performance_optimizer.optimize_now()
                return jsonify({
                    'success': True,
                    'optimizations_applied': len(results),
                    'results': [
                        {
                            'rule_name': r.rule_name,
                            'action': r.action.value,
                            'success': r.success,
                            'error_message': r.error_message
                        } for r in results
                    ]
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/api/optimization/rollback', methods=['POST'])
        def api_rollback_optimization():
            """Rollback last optimization"""
            if not self.performance_optimizer:
                return jsonify({'error': 'Optimizer not available'}), 400
                
            try:
                success = self.performance_optimizer.rollback_last_optimization()
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/api/optimization/settings', methods=['GET', 'POST'])
        def api_optimization_settings():
            """Get or update optimization settings"""
            if not self.performance_optimizer:
                return jsonify({'error': 'Optimizer not available'}), 400
                
            if request.method == 'GET':
                return jsonify({
                    'auto_optimization_enabled': self.performance_optimizer.auto_optimization_enabled,
                    'strategy': self.performance_optimizer.strategy.value,
                    'current_settings': self.performance_optimizer.current_settings,
                    'performance_baselines': self.performance_optimizer.performance_baselines
                })
            else:
                data = request.get_json()
                
                if 'auto_optimization_enabled' in data:
                    if data['auto_optimization_enabled']:
                        self.performance_optimizer.start_auto_optimization()
                    else:
                        self.performance_optimizer.stop_auto_optimization()
                        
                if 'performance_baselines' in data:
                    self.performance_optimizer.set_performance_baselines(data['performance_baselines'])
                    
                return jsonify({'success': True})
                
        @self.app.route('/api/testing/quick', methods=['POST'])
        def api_quick_test():
            """Run a quick scalability test"""
            data = request.get_json()
            target_url = data.get('target_url', 'http://localhost:5000')
            max_connections = data.get('max_connections', 50)
            
            # Start test in background
            test_id = f"quick_test_{int(time.time())}"
            
            async def run_test():
                config = create_load_test_config(target_url, max_connections, 30)
                result = await self.scalability_tester.run_load_test(config)
                self.active_tests[test_id] = result
                
            # Schedule the test
            asyncio.create_task(run_test())
            
            return jsonify({
                'test_id': test_id,
                'status': 'started',
                'message': f'Quick test started with {max_connections} connections'
            })
            
        @self.app.route('/api/testing/stress', methods=['POST'])
        def api_stress_test():
            """Run a stress test"""
            data = request.get_json()
            target_url = data.get('target_url', 'http://localhost:5000')
            connection_counts = data.get('connection_counts', [50, 100, 200])
            
            test_id = f"stress_test_{int(time.time())}"
            
            async def run_test():
                base_config = create_load_test_config(target_url, 100, 60)
                results = await self.scalability_tester.run_stress_test(base_config, connection_counts)
                self.active_tests[test_id] = results
                
            asyncio.create_task(run_test())
            
            return jsonify({
                'test_id': test_id,
                'status': 'started',
                'message': f'Stress test started with connection counts: {connection_counts}'
            })
            
        @self.app.route('/api/testing/status/<test_id>')
        def api_test_status(test_id):
            """Get test status"""
            if test_id in self.active_tests:
                result = self.active_tests[test_id]
                if isinstance(result, list):
                    # Stress test results
                    return jsonify({
                        'status': 'completed',
                        'test_count': len(result),
                        'results': [
                            {
                                'max_connections': r.config.max_connections,
                                'result': r.result.value,
                                'performance_level': r.performance_summary.get('performance_level'),
                                'connection_success_rate': r.aggregate_metrics.get('connection_success_rate', 0),
                                'avg_latency': r.aggregate_metrics.get('latency_avg', 0),
                                'error_rate': r.aggregate_metrics.get('error_rate', 0)
                            } for r in result
                        ]
                    })
                else:
                    # Single test result
                    return jsonify({
                        'status': 'completed',
                        'result': result.result.value,
                        'performance_level': result.performance_summary.get('performance_level'),
                        'connection_success_rate': result.aggregate_metrics.get('connection_success_rate', 0),
                        'avg_latency': result.aggregate_metrics.get('latency_avg', 0),
                        'error_rate': result.aggregate_metrics.get('error_rate', 0),
                        'total_duration': result.total_duration,
                        'issues': result.issues,
                        'recommendations': result.recommendations
                    })
            else:
                return jsonify({
                    'status': 'running',
                    'message': 'Test is still in progress'
                })
                
        @self.app.route('/api/dashboard/config', methods=['GET', 'POST'])
        def api_dashboard_config():
            """Get or update dashboard configuration"""
            if request.method == 'GET':
                return jsonify(self.dashboard_config)
            else:
                data = request.get_json()
                self.dashboard_config.update(data)
                return jsonify({'success': True})
                
        @self.app.route('/api/alerts/current')
        def api_current_alerts():
            """Get current performance alerts"""
            current_performance = self.performance_monitor.get_current_performance_summary()
            alerts = []
            
            # Check CPU usage
            cpu_usage = current_performance.get('resource_usage', {}).get('cpu_usage', 0)
            if cpu_usage > self.dashboard_config['alert_thresholds']['cpu_usage']:
                alerts.append({
                    'type': 'warning' if cpu_usage < 90 else 'critical',
                    'metric': 'CPU Usage',
                    'value': f"{cpu_usage:.1f}%",
                    'threshold': f"{self.dashboard_config['alert_thresholds']['cpu_usage']}%",
                    'message': f"CPU usage is {cpu_usage:.1f}%"
                })
                
            # Check memory usage
            memory_usage = current_performance.get('resource_usage', {}).get('memory_usage', 0)
            if memory_usage > self.dashboard_config['alert_thresholds']['memory_usage']:
                alerts.append({
                    'type': 'warning' if memory_usage < 95 else 'critical',
                    'metric': 'Memory Usage',
                    'value': f"{memory_usage:.1f}%",
                    'threshold': f"{self.dashboard_config['alert_thresholds']['memory_usage']}%",
                    'message': f"Memory usage is {memory_usage:.1f}%"
                })
                
            # Check error rate
            error_rate = current_performance.get('connection_quality', {}).get('error_rate', 0)
            if error_rate > self.dashboard_config['alert_thresholds']['error_rate']:
                alerts.append({
                    'type': 'warning' if error_rate < 0.1 else 'critical',
                    'metric': 'Error Rate',
                    'value': f"{error_rate:.2%}",
                    'threshold': f"{self.dashboard_config['alert_thresholds']['error_rate']:.2%}",
                    'message': f"Error rate is {error_rate:.2%}"
                })
                
            # Check latency
            avg_latency = current_performance.get('connection_quality', {}).get('avg_latency', 0)
            if avg_latency > self.dashboard_config['alert_thresholds']['latency']:
                alerts.append({
                    'type': 'warning' if avg_latency < 500 else 'critical',
                    'metric': 'Average Latency',
                    'value': f"{avg_latency:.1f}ms",
                    'threshold': f"{self.dashboard_config['alert_thresholds']['latency']}ms",
                    'message': f"Average latency is {avg_latency:.1f}ms"
                })
                
            return jsonify(alerts)
            
    def _get_dashboard_template(self) -> str:
        """Get the HTML template for the performance dashboard"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f7fa;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
        }
        
        .card h3 {
            margin-bottom: 15px;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }
        
        .metric {
            text-align: center;
            padding: 15px;
            background: #f8f9ff;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .metric-label {
            color: #666;
            margin-top: 5px;
            font-size: 0.9em;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5a6fd8;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background: #218838;
        }
        
        .btn-warning {
            background: #ffc107;
            color: #212529;
        }
        
        .btn-warning:hover {
            background: #e0a800;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .alert {
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
            border-left: 4px solid;
        }
        
        .alert-warning {
            background: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }
        
        .alert-critical {
            background: #f8d7da;
            border-color: #dc3545;
            color: #721c24;
        }
        
        .alert-info {
            background: #d1ecf1;
            border-color: #17a2b8;
            color: #0c5460;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-excellent { background: #28a745; }
        .status-good { background: #17a2b8; }
        .status-fair { background: #ffc107; }
        .status-poor { background: #fd7e14; }
        .status-critical { background: #dc3545; }
        
        .optimization-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .optimization-item {
            padding: 10px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            margin-bottom: 10px;
            background: #f8f9fa;
        }
        
        .optimization-item h5 {
            margin-bottom: 5px;
            color: #495057;
        }
        
        .optimization-item p {
            margin-bottom: 5px;
            font-size: 0.9em;
            color: #6c757d;
        }
        
        .test-results {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .test-result {
            padding: 15px;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            margin-bottom: 15px;
            background: #f8f9fa;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        
        .form-group input, .form-group select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ced4da;
            border-radius: 4px;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #6c757d;
        }
        
        .tabs {
            display: flex;
            border-bottom: 2px solid #dee2e6;
            margin-bottom: 20px;
        }
        
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }
        
        .tab.active {
            border-bottom-color: #667eea;
            color: #667eea;
            font-weight: bold;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>WebSocket Performance Dashboard</h1>
        <p>Real-time monitoring, optimization, and scalability testing</p>
    </div>
    
    <div class="container">
        <!-- Controls -->
        <div class="controls">
            <button class="btn btn-primary" onclick="refreshData()">Refresh Data</button>
            <button class="btn btn-success" onclick="optimizeNow()">Optimize Now</button>
            <button class="btn btn-warning" onclick="rollbackOptimization()">Rollback Last</button>
            <label style="margin-left: 20px;">
                <input type="checkbox" id="autoRefresh" checked> Auto-refresh (5s)
            </label>
        </div>
        
        <!-- Alerts -->
        <div id="alertsContainer"></div>
        
        <!-- Main Dashboard Grid -->
        <div class="dashboard-grid">
            <!-- Current Performance -->
            <div class="card">
                <h3>Current Performance</h3>
                <div class="metric-grid" id="currentMetrics">
                    <div class="loading">Loading...</div>
                </div>
            </div>
            
            <!-- Resource Usage -->
            <div class="card">
                <h3>Resource Usage</h3>
                <div class="metric-grid" id="resourceMetrics">
                    <div class="loading">Loading...</div>
                </div>
            </div>
            
            <!-- Connection Quality -->
            <div class="card">
                <h3>Connection Quality</h3>
                <div class="metric-grid" id="qualityMetrics">
                    <div class="loading">Loading...</div>
                </div>
            </div>
            
            <!-- Scalability Status -->
            <div class="card">
                <h3>Scalability Status</h3>
                <div id="scalabilityStatus">
                    <div class="loading">Loading...</div>
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="card">
            <h3>Performance Trends</h3>
            <div class="chart-container">
                <canvas id="performanceChart"></canvas>
            </div>
        </div>
        
        <!-- Tabs for detailed views -->
        <div class="card">
            <div class="tabs">
                <div class="tab active" onclick="showTab('optimization')">Optimization</div>
                <div class="tab" onclick="showTab('testing')">Testing</div>
                <div class="tab" onclick="showTab('history')">History</div>
            </div>
            
            <!-- Optimization Tab -->
            <div id="optimization" class="tab-content active">
                <h3>Optimization Recommendations</h3>
                <div id="optimizationRecommendations">
                    <div class="loading">Loading...</div>
                </div>
            </div>
            
            <!-- Testing Tab -->
            <div id="testing" class="tab-content">
                <h3>Scalability Testing</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4>Quick Test</h4>
                        <div class="form-group">
                            <label>Target URL:</label>
                            <input type="text" id="quickTestUrl" value="http://localhost:5000">
                        </div>
                        <div class="form-group">
                            <label>Max Connections:</label>
                            <input type="number" id="quickTestConnections" value="50">
                        </div>
                        <button class="btn btn-primary" onclick="runQuickTest()">Run Quick Test</button>
                    </div>
                    <div>
                        <h4>Stress Test</h4>
                        <div class="form-group">
                            <label>Target URL:</label>
                            <input type="text" id="stressTestUrl" value="http://localhost:5000">
                        </div>
                        <div class="form-group">
                            <label>Connection Counts (comma-separated):</label>
                            <input type="text" id="stressTestCounts" value="50,100,200">
                        </div>
                        <button class="btn btn-primary" onclick="runStressTest()">Run Stress Test</button>
                    </div>
                </div>
                <div id="testResults" class="test-results">
                    <!-- Test results will be populated here -->
                </div>
            </div>
            
            <!-- History Tab -->
            <div id="history" class="tab-content">
                <h3>Optimization History</h3>
                <div id="optimizationHistory">
                    <div class="loading">Loading...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let autoRefreshInterval;
        let performanceChart;
        let chartData = {
            labels: [],
            datasets: [
                {
                    label: 'CPU Usage (%)',
                    data: [],
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Memory Usage (%)',
                    data: [],
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Avg Latency (ms)',
                    data: [],
                    borderColor: '#17a2b8',
                    backgroundColor: 'rgba(23, 162, 184, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        };
        
        function initializeChart() {
            const ctx = document.getElementById('performanceChart').getContext('2d');
            performanceChart = new Chart(ctx, {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Percentage (%)'
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Latency (ms)'
                            },
                            grid: {
                                drawOnChartArea: false,
                            },
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }
        
        function updateChart(performance) {
            const now = new Date().toLocaleTimeString();
            
            chartData.labels.push(now);
            chartData.datasets[0].data.push(performance.resource_usage?.cpu_usage || 0);
            chartData.datasets[1].data.push(performance.resource_usage?.memory_usage || 0);
            chartData.datasets[2].data.push(performance.connection_quality?.avg_latency || 0);
            
            // Keep only last 20 data points
            if (chartData.labels.length > 20) {
                chartData.labels.shift();
                chartData.datasets.forEach(dataset => dataset.data.shift());
            }
            
            performanceChart.update('none');
        }
        
        function refreshData() {
            Promise.all([
                fetch('/api/performance/current').then(r => r.json()),
                fetch('/api/performance/scalability').then(r => r.json()),
                fetch('/api/optimization/recommendations').then(r => r.json()),
                fetch('/api/alerts/current').then(r => r.json())
            ]).then(([performance, scalability, recommendations, alerts]) => {
                updateCurrentMetrics(performance);
                updateScalabilityStatus(scalability);
                updateOptimizationRecommendations(recommendations);
                updateAlerts(alerts);
                updateChart(performance);
            }).catch(error => {
                console.error('Error fetching data:', error);
            });
        }
        
        function updateCurrentMetrics(performance) {
            const container = document.getElementById('currentMetrics');
            container.innerHTML = `
                <div class="metric">
                    <div class="metric-value">
                        <span class="status-indicator status-${performance.performance_level}"></span>
                        ${performance.performance_level}
                    </div>
                    <div class="metric-label">Performance Level</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${performance.connection_pool?.total_connections || 0}</div>
                    <div class="metric-label">Total Connections</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${performance.connection_pool?.active_connections || 0}</div>
                    <div class="metric-label">Active Connections</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${(performance.message_delivery?.messages_per_second || 0).toFixed(1)}</div>
                    <div class="metric-label">Messages/sec</div>
                </div>
            `;
            
            const resourceContainer = document.getElementById('resourceMetrics');
            resourceContainer.innerHTML = `
                <div class="metric">
                    <div class="metric-value">${(performance.resource_usage?.cpu_usage || 0).toFixed(1)}%</div>
                    <div class="metric-label">CPU Usage</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${(performance.resource_usage?.memory_usage || 0).toFixed(1)}%</div>
                    <div class="metric-label">Memory Usage</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${(performance.resource_usage?.memory_available / 1024 / 1024 / 1024 || 0).toFixed(1)}GB</div>
                    <div class="metric-label">Available Memory</div>
                </div>
            `;
            
            const qualityContainer = document.getElementById('qualityMetrics');
            qualityContainer.innerHTML = `
                <div class="metric">
                    <div class="metric-value">${(performance.connection_quality?.avg_latency || 0).toFixed(1)}ms</div>
                    <div class="metric-label">Avg Latency</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${((performance.connection_quality?.error_rate || 0) * 100).toFixed(2)}%</div>
                    <div class="metric-label">Error Rate</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${performance.connection_quality?.total_errors || 0}</div>
                    <div class="metric-label">Total Errors</div>
                </div>
            `;
        }
        
        function updateScalabilityStatus(scalability) {
            const container = document.getElementById('scalabilityStatus');
            container.innerHTML = `
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">${scalability.current_connections || 0}</div>
                        <div class="metric-label">Current Connections</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${scalability.estimated_max_connections || 0}</div>
                        <div class="metric-label">Estimated Max</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${scalability.current_load_level || 'unknown'}</div>
                        <div class="metric-label">Load Level</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${((scalability.scaling_factor || 0) * 100).toFixed(0)}%</div>
                        <div class="metric-label">Scaling Headroom</div>
                    </div>
                </div>
                ${scalability.bottlenecks && scalability.bottlenecks.length > 0 ? `
                    <div style="margin-top: 15px;">
                        <strong>Bottlenecks:</strong>
                        <ul>
                            ${scalability.bottlenecks.map(b => `<li>${b}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            `;
        }
        
        function updateOptimizationRecommendations(recommendations) {
            const container = document.getElementById('optimizationRecommendations');
            
            if (recommendations.length === 0) {
                container.innerHTML = '<p>No optimization recommendations at this time.</p>';
                return;
            }
            
            container.innerHTML = recommendations.map(rec => `
                <div class="optimization-item">
                    <h5>${rec.rule_name}</h5>
                    <p><strong>Action:</strong> ${rec.action}</p>
                    <p><strong>Description:</strong> ${rec.description}</p>
                    <p><strong>Priority:</strong> ${rec.priority}</p>
                </div>
            `).join('');
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alertsContainer');
            
            if (alerts.length === 0) {
                container.innerHTML = '';
                return;
            }
            
            container.innerHTML = alerts.map(alert => `
                <div class="alert alert-${alert.type}">
                    <strong>${alert.metric}:</strong> ${alert.message}
                    (Threshold: ${alert.threshold})
                </div>
            `).join('');
        }
        
        function optimizeNow() {
            fetch('/api/optimization/apply', { method: 'POST' })
                .then(r => r.json())
                .then(result => {
                    if (result.success) {
                        alert(`Applied ${result.optimizations_applied} optimizations`);
                        refreshData();
                    } else {
                        alert(`Optimization failed: ${result.error}`);
                    }
                })
                .catch(error => {
                    alert(`Error: ${error.message}`);
                });
        }
        
        function rollbackOptimization() {
            if (confirm('Are you sure you want to rollback the last optimization?')) {
                fetch('/api/optimization/rollback', { method: 'POST' })
                    .then(r => r.json())
                    .then(result => {
                        if (result.success) {
                            alert('Optimization rolled back successfully');
                            refreshData();
                        } else {
                            alert(`Rollback failed: ${result.error}`);
                        }
                    })
                    .catch(error => {
                        alert(`Error: ${error.message}`);
                    });
            }
        }
        
        function runQuickTest() {
            const url = document.getElementById('quickTestUrl').value;
            const connections = parseInt(document.getElementById('quickTestConnections').value);
            
            fetch('/api/testing/quick', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_url: url, max_connections: connections })
            })
            .then(r => r.json())
            .then(result => {
                alert(`Test started: ${result.message}`);
                monitorTest(result.test_id);
            })
            .catch(error => {
                alert(`Error: ${error.message}`);
            });
        }
        
        function runStressTest() {
            const url = document.getElementById('stressTestUrl').value;
            const counts = document.getElementById('stressTestCounts').value
                .split(',').map(s => parseInt(s.trim()));
            
            fetch('/api/testing/stress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_url: url, connection_counts: counts })
            })
            .then(r => r.json())
            .then(result => {
                alert(`Stress test started: ${result.message}`);
                monitorTest(result.test_id);
            })
            .catch(error => {
                alert(`Error: ${error.message}`);
            });
        }
        
        function monitorTest(testId) {
            const checkStatus = () => {
                fetch(`/api/testing/status/${testId}`)
                    .then(r => r.json())
                    .then(status => {
                        if (status.status === 'completed') {
                            displayTestResults(testId, status);
                        } else {
                            setTimeout(checkStatus, 5000); // Check again in 5 seconds
                        }
                    });
            };
            
            checkStatus();
        }
        
        function displayTestResults(testId, results) {
            const container = document.getElementById('testResults');
            
            let html = `<div class="test-result">
                <h4>Test Results: ${testId}</h4>`;
            
            if (results.test_count) {
                // Stress test results
                html += `<p><strong>Stress Test Completed</strong> - ${results.test_count} phases</p>`;
                results.results.forEach((result, index) => {
                    html += `
                        <div style="margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 5px;">
                            <strong>Phase ${index + 1}: ${result.max_connections} connections</strong><br>
                            Result: ${result.result}<br>
                            Performance: ${result.performance_level}<br>
                            Success Rate: ${(result.connection_success_rate * 100).toFixed(1)}%<br>
                            Avg Latency: ${result.avg_latency.toFixed(1)}ms<br>
                            Error Rate: ${(result.error_rate * 100).toFixed(2)}%
                        </div>
                    `;
                });
            } else {
                // Single test results
                html += `
                    <p><strong>Result:</strong> ${results.result}</p>
                    <p><strong>Performance Level:</strong> ${results.performance_level}</p>
                    <p><strong>Connection Success Rate:</strong> ${(results.connection_success_rate * 100).toFixed(1)}%</p>
                    <p><strong>Average Latency:</strong> ${results.avg_latency.toFixed(1)}ms</p>
                    <p><strong>Error Rate:</strong> ${(results.error_rate * 100).toFixed(2)}%</p>
                    <p><strong>Duration:</strong> ${results.total_duration.toFixed(1)}s</p>
                `;
                
                if (results.issues && results.issues.length > 0) {
                    html += `<p><strong>Issues:</strong></p><ul>`;
                    results.issues.forEach(issue => {
                        html += `<li>${issue}</li>`;
                    });
                    html += `</ul>`;
                }
                
                if (results.recommendations && results.recommendations.length > 0) {
                    html += `<p><strong>Recommendations:</strong></p><ul>`;
                    results.recommendations.forEach(rec => {
                        html += `<li>${rec}</li>`;
                    });
                    html += `</ul>`;
                }
            }
            
            html += `</div>`;
            container.innerHTML = html + container.innerHTML;
        }
        
        function showTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to selected tab
            event.target.classList.add('active');
            
            // Load data for the selected tab
            if (tabName === 'history') {
                loadOptimizationHistory();
            }
        }
        
        function loadOptimizationHistory() {
            fetch('/api/optimization/history')
                .then(r => r.json())
                .then(history => {
                    const container = document.getElementById('optimizationHistory');
                    
                    if (history.length === 0) {
                        container.innerHTML = '<p>No optimization history available.</p>';
                        return;
                    }
                    
                    container.innerHTML = history.map(item => `
                        <div class="optimization-item">
                            <h5>${item.rule_name}</h5>
                            <p><strong>Timestamp:</strong> ${new Date(item.timestamp).toLocaleString()}</p>
                            <p><strong>Action:</strong> ${item.action}</p>
                            <p><strong>Success:</strong> ${item.success ? 'Yes' : 'No'}</p>
                            <p><strong>Expected Impact:</strong> ${item.expected_impact}</p>
                            ${item.error_message ? `<p><strong>Error:</strong> ${item.error_message}</p>` : ''}
                        </div>
                    `).join('');
                })
                .catch(error => {
                    console.error('Error loading optimization history:', error);
                });
        }
        
        function setupAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            
            function toggleAutoRefresh() {
                if (checkbox.checked) {
                    autoRefreshInterval = setInterval(refreshData, 5000);
                } else {
                    clearInterval(autoRefreshInterval);
                }
            }
            
            checkbox.addEventListener('change', toggleAutoRefresh);
            toggleAutoRefresh(); // Start auto-refresh if checked
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeChart();
            refreshData();
            setupAutoRefresh();
        });
    </script>
</body>
</html>
        '''
        
    def run(self, debug: bool = True, host: str = '127.0.0.1'):
        """Run the performance dashboard"""
        self.logger.info(f"Starting WebSocket performance dashboard on {host}:{self.port}")
        self.app.run(host=host, port=self.port, debug=debug, threaded=True)


def create_performance_dashboard(performance_monitor: WebSocketPerformanceMonitor,
                               performance_optimizer: WebSocketPerformanceOptimizer = None,
                               scalability_tester: WebSocketScalabilityTester = None,
                               port: int = 5002) -> WebSocketPerformanceDashboard:
    """Create a WebSocket performance dashboard"""
    return WebSocketPerformanceDashboard(
        performance_monitor=performance_monitor,
        performance_optimizer=performance_optimizer,
        scalability_tester=scalability_tester,
        port=port
    )


def start_performance_dashboard(performance_monitor: WebSocketPerformanceMonitor,
                              performance_optimizer: WebSocketPerformanceOptimizer = None,
                              port: int = 5002, host: str = '127.0.0.1'):
    """Start the performance dashboard server"""
    dashboard = create_performance_dashboard(performance_monitor, performance_optimizer, port=port)
    dashboard.run(debug=True, host=host)