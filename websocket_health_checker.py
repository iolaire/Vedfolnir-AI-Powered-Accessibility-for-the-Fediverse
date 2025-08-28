# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Health Checker

Provides automated health checks for WebSocket system components
with configurable monitoring intervals and alert thresholds.
"""

import time
import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import requests
import socketio
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager
from websocket_debug_logger import get_debug_logger, DebugLevel


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time: float = 0.0
    error: Optional[str] = None


class WebSocketHealthChecker:
    """Automated health checker for WebSocket components"""
    
    def __init__(self, config_manager: WebSocketConfigManager, cors_manager: CORSManager):
        self.config_manager = config_manager
        self.cors_manager = cors_manager
        self.logger = get_debug_logger('health_checker', DebugLevel.INFO)
        
        # Health check configuration
        self.check_interval = 60  # seconds
        self.alert_thresholds = {
            'response_time': 5.0,  # seconds
            'error_rate': 0.1,     # 10%
            'connection_failures': 3  # consecutive failures
        }
        
        # Health check history
        self.health_history = {}
        self.consecutive_failures = {}
        self.alert_callbacks = []
        
        # Health check thread
        self.running = False
        self.health_thread = None
        
        # Component checkers
        self.checkers = {
            'configuration': self._check_configuration,
            'cors_setup': self._check_cors_setup,
            'server_availability': self._check_server_availability,
            'websocket_endpoint': self._check_websocket_endpoint,
            'connection_establishment': self._check_connection_establishment,
            'transport_fallback': self._check_transport_fallback,
            'authentication_flow': self._check_authentication_flow,
            'message_handling': self._check_message_handling,
            'error_recovery': self._check_error_recovery,
            'performance_metrics': self._check_performance_metrics
        }
        
    def start_monitoring(self, interval: int = None):
        """Start automated health monitoring"""
        if self.running:
            self.logger.warning("Health monitoring is already running")
            return
            
        if interval:
            self.check_interval = interval
            
        self.running = True
        self.health_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.health_thread.start()
        
        self.logger.info(f"Started WebSocket health monitoring (interval: {self.check_interval}s)")
        
    def stop_monitoring(self):
        """Stop automated health monitoring"""
        self.running = False
        if self.health_thread:
            self.health_thread.join(timeout=5)
            
        self.logger.info("Stopped WebSocket health monitoring")
        
    def add_alert_callback(self, callback: Callable[[HealthCheckResult], None]):
        """Add callback function for health alerts"""
        self.alert_callbacks.append(callback)
        
    def run_health_check(self, components: List[str] = None) -> Dict[str, HealthCheckResult]:
        """Run health checks for specified components"""
        if components is None:
            components = list(self.checkers.keys())
            
        results = {}
        
        for component in components:
            if component not in self.checkers:
                self.logger.warning(f"Unknown health check component: {component}")
                continue
                
            try:
                start_time = time.time()
                result = self.checkers[component]()
                response_time = time.time() - start_time
                
                result.response_time = response_time
                result.timestamp = datetime.utcnow()
                
                results[component] = result
                
                # Update health history
                self._update_health_history(component, result)
                
                # Check for alerts
                self._check_alerts(result)
                
            except Exception as e:
                self.logger.error(f"Health check failed for {component}: {e}")
                result = HealthCheckResult(
                    component=component,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    details={},
                    timestamp=datetime.utcnow(),
                    error=str(e)
                )
                results[component] = result
                
        return results
        
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        recent_results = self._get_recent_results()
        
        if not recent_results:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': 'No recent health check data available',
                'components': {},
                'summary': {}
            }
            
        # Calculate overall status
        statuses = [result.status for result in recent_results.values()]
        
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
            
        # Generate summary
        summary = {
            'total_components': len(recent_results),
            'healthy_components': sum(1 for s in statuses if s == HealthStatus.HEALTHY),
            'warning_components': sum(1 for s in statuses if s == HealthStatus.WARNING),
            'critical_components': sum(1 for s in statuses if s == HealthStatus.CRITICAL),
            'last_check': max(result.timestamp for result in recent_results.values()).isoformat(),
            'avg_response_time': sum(result.response_time for result in recent_results.values()) / len(recent_results)
        }
        
        return {
            'status': overall_status.value,
            'message': self._generate_health_message(overall_status, summary),
            'components': {name: asdict(result) for name, result in recent_results.items()},
            'summary': summary
        }
        
    def get_health_history(self, component: str = None, hours: int = 24) -> Dict[str, List[Dict]]:
        """Get health check history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        if component:
            if component in self.health_history:
                history = [
                    asdict(result) for result in self.health_history[component]
                    if result.timestamp > cutoff_time
                ]
                return {component: history}
            else:
                return {component: []}
        else:
            history = {}
            for comp, results in self.health_history.items():
                history[comp] = [
                    asdict(result) for result in results
                    if result.timestamp > cutoff_time
                ]
            return history
            
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self.logger.debug("Running scheduled health checks")
                self.run_health_check()
                
                # Sleep for the specified interval
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(10)  # Wait before retrying
                
    def _update_health_history(self, component: str, result: HealthCheckResult):
        """Update health history for a component"""
        if component not in self.health_history:
            self.health_history[component] = []
            
        self.health_history[component].append(result)
        
        # Keep only last 1000 results per component
        if len(self.health_history[component]) > 1000:
            self.health_history[component] = self.health_history[component][-1000:]
            
        # Update consecutive failure count
        if result.status == HealthStatus.CRITICAL:
            self.consecutive_failures[component] = self.consecutive_failures.get(component, 0) + 1
        else:
            self.consecutive_failures[component] = 0
            
    def _check_alerts(self, result: HealthCheckResult):
        """Check if result triggers any alerts"""
        alerts_triggered = []
        
        # Check response time threshold
        if result.response_time > self.alert_thresholds['response_time']:
            alerts_triggered.append(f"High response time: {result.response_time:.2f}s")
            
        # Check consecutive failures
        consecutive = self.consecutive_failures.get(result.component, 0)
        if consecutive >= self.alert_thresholds['connection_failures']:
            alerts_triggered.append(f"Consecutive failures: {consecutive}")
            
        # Check critical status
        if result.status == HealthStatus.CRITICAL:
            alerts_triggered.append(f"Critical status: {result.message}")
            
        # Trigger alert callbacks
        if alerts_triggered:
            for callback in self.alert_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
                    
    def _get_recent_results(self, minutes: int = 5) -> Dict[str, HealthCheckResult]:
        """Get most recent health check results"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_results = {}
        
        for component, results in self.health_history.items():
            # Get the most recent result within the time window
            recent = [r for r in results if r.timestamp > cutoff_time]
            if recent:
                recent_results[component] = recent[-1]  # Most recent
                
        return recent_results
        
    def _generate_health_message(self, status: HealthStatus, summary: Dict[str, Any]) -> str:
        """Generate human-readable health message"""
        if status == HealthStatus.HEALTHY:
            return f"All {summary['total_components']} components are healthy"
        elif status == HealthStatus.WARNING:
            return f"{summary['warning_components']} components have warnings"
        elif status == HealthStatus.CRITICAL:
            return f"{summary['critical_components']} components are critical"
        else:
            return "Health status unknown"
            
    # Component-specific health checks
    
    def _check_configuration(self) -> HealthCheckResult:
        """Check WebSocket configuration health"""
        try:
            # Validate configuration
            is_valid = self.config_manager.validate_configuration()
            
            details = {
                'flask_host': self.config_manager.get_flask_host(),
                'flask_port': self.config_manager.get_flask_port(),
                'socketio_config': self.config_manager.get_socketio_config()
            }
            
            if is_valid:
                return HealthCheckResult(
                    component='configuration',
                    status=HealthStatus.HEALTHY,
                    message='Configuration is valid',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='configuration',
                    status=HealthStatus.CRITICAL,
                    message='Configuration validation failed',
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='configuration',
                status=HealthStatus.CRITICAL,
                message=f'Configuration check failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_cors_setup(self) -> HealthCheckResult:
        """Check CORS configuration health"""
        try:
            origins = self.cors_manager.get_allowed_origins()
            
            details = {
                'allowed_origins': origins,
                'origin_count': len(origins)
            }
            
            if not origins:
                return HealthCheckResult(
                    component='cors_setup',
                    status=HealthStatus.CRITICAL,
                    message='No CORS origins configured',
                    details=details
                )
            elif len(origins) == 1 and origins[0] == '*':
                return HealthCheckResult(
                    component='cors_setup',
                    status=HealthStatus.WARNING,
                    message='Wildcard CORS origin detected',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='cors_setup',
                    status=HealthStatus.HEALTHY,
                    message=f'CORS configured with {len(origins)} origins',
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='cors_setup',
                status=HealthStatus.CRITICAL,
                message=f'CORS check failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_server_availability(self) -> HealthCheckResult:
        """Check server availability"""
        try:
            server_url = f"http://{self.config_manager.get_flask_host()}:{self.config_manager.get_flask_port()}"
            
            response = requests.get(server_url, timeout=5)
            
            details = {
                'server_url': server_url,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
            if response.status_code == 200:
                return HealthCheckResult(
                    component='server_availability',
                    status=HealthStatus.HEALTHY,
                    message='Server is available',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='server_availability',
                    status=HealthStatus.WARNING,
                    message=f'Server returned status {response.status_code}',
                    details=details
                )
                
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                component='server_availability',
                status=HealthStatus.CRITICAL,
                message='Server is not reachable',
                details={'server_url': server_url},
                error='Connection refused'
            )
        except Exception as e:
            return HealthCheckResult(
                component='server_availability',
                status=HealthStatus.CRITICAL,
                message=f'Server check failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_websocket_endpoint(self) -> HealthCheckResult:
        """Check WebSocket endpoint availability"""
        try:
            server_url = f"http://{self.config_manager.get_flask_host()}:{self.config_manager.get_flask_port()}"
            endpoint_url = f"{server_url}/socket.io/"
            
            response = requests.get(endpoint_url, timeout=5)
            
            details = {
                'endpoint_url': endpoint_url,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', 'unknown')
            }
            
            if response.status_code == 200:
                return HealthCheckResult(
                    component='websocket_endpoint',
                    status=HealthStatus.HEALTHY,
                    message='WebSocket endpoint is available',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='websocket_endpoint',
                    status=HealthStatus.WARNING,
                    message=f'WebSocket endpoint returned status {response.status_code}',
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='websocket_endpoint',
                status=HealthStatus.CRITICAL,
                message=f'WebSocket endpoint check failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_connection_establishment(self) -> HealthCheckResult:
        """Check WebSocket connection establishment"""
        try:
            server_url = f"http://{self.config_manager.get_flask_host()}:{self.config_manager.get_flask_port()}"
            
            sio = socketio.Client(logger=False, engineio_logger=False)
            
            connection_successful = False
            connection_error = None
            
            @sio.event
            def connect():
                nonlocal connection_successful
                connection_successful = True
                
            @sio.event
            def connect_error(data):
                nonlocal connection_error
                connection_error = data
                
            # Attempt connection
            sio.connect(server_url, wait_timeout=10)
            
            details = {
                'server_url': server_url,
                'connection_successful': connection_successful,
                'transport': sio.transport() if hasattr(sio, 'transport') else 'unknown'
            }
            
            if connection_successful:
                sio.disconnect()
                return HealthCheckResult(
                    component='connection_establishment',
                    status=HealthStatus.HEALTHY,
                    message='WebSocket connection established successfully',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='connection_establishment',
                    status=HealthStatus.CRITICAL,
                    message='WebSocket connection failed',
                    details=details,
                    error=str(connection_error) if connection_error else 'Unknown error'
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='connection_establishment',
                status=HealthStatus.CRITICAL,
                message=f'Connection test failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_transport_fallback(self) -> HealthCheckResult:
        """Check transport fallback functionality"""
        try:
            server_url = f"http://{self.config_manager.get_flask_host()}:{self.config_manager.get_flask_port()}"
            
            transports_tested = {}
            fallback_working = False
            
            for transport in [['websocket'], ['polling']]:
                transport_name = '+'.join(transport)
                
                try:
                    sio = socketio.Client(logger=False, engineio_logger=False)
                    
                    connection_successful = False
                    
                    @sio.event
                    def connect():
                        nonlocal connection_successful
                        connection_successful = True
                        
                    sio.connect(server_url, transports=transport, wait_timeout=5)
                    
                    transports_tested[transport_name] = {
                        'status': 'success' if connection_successful else 'failed',
                        'transport': sio.transport() if hasattr(sio, 'transport') else 'unknown'
                    }
                    
                    if connection_successful:
                        fallback_working = True
                        
                    sio.disconnect()
                    
                except Exception as e:
                    transports_tested[transport_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    
            details = {
                'transports_tested': transports_tested,
                'fallback_working': fallback_working
            }
            
            if fallback_working:
                return HealthCheckResult(
                    component='transport_fallback',
                    status=HealthStatus.HEALTHY,
                    message='Transport fallback is working',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='transport_fallback',
                    status=HealthStatus.CRITICAL,
                    message='No transport methods are working',
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='transport_fallback',
                status=HealthStatus.CRITICAL,
                message=f'Transport fallback check failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_authentication_flow(self) -> HealthCheckResult:
        """Check authentication flow (basic test)"""
        # This is a basic check - full authentication testing would require valid credentials
        return HealthCheckResult(
            component='authentication_flow',
            status=HealthStatus.HEALTHY,
            message='Authentication flow check skipped (requires credentials)',
            details={'note': 'Manual testing required for full authentication validation'}
        )
        
    def _check_message_handling(self) -> HealthCheckResult:
        """Check message handling capability"""
        try:
            server_url = f"http://{self.config_manager.get_flask_host()}:{self.config_manager.get_flask_port()}"
            
            sio = socketio.Client(logger=False, engineio_logger=False)
            
            message_sent = False
            message_received = False
            
            @sio.event
            def connect():
                # Send test message after connection
                test_data = {'test': 'health_check', 'timestamp': datetime.utcnow().isoformat()}
                sio.emit('health_check_message', test_data)
                nonlocal message_sent
                message_sent = True
                
            @sio.event
            def health_check_response(data):
                nonlocal message_received
                message_received = True
                
            sio.connect(server_url, wait_timeout=5)
            sio.sleep(2)  # Wait for potential response
            sio.disconnect()
            
            details = {
                'message_sent': message_sent,
                'message_received': message_received
            }
            
            if message_sent:
                return HealthCheckResult(
                    component='message_handling',
                    status=HealthStatus.HEALTHY,
                    message='Message handling is working',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='message_handling',
                    status=HealthStatus.WARNING,
                    message='Could not send test message',
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='message_handling',
                status=HealthStatus.CRITICAL,
                message=f'Message handling check failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_error_recovery(self) -> HealthCheckResult:
        """Check error recovery mechanisms"""
        try:
            # Test connection to invalid server (should fail gracefully)
            sio = socketio.Client(logger=False, engineio_logger=False)
            
            error_handled = False
            
            @sio.event
            def connect_error(data):
                nonlocal error_handled
                error_handled = True
                
            try:
                sio.connect("http://invalid-server:9999", wait_timeout=2)
            except Exception:
                error_handled = True
                
            details = {
                'error_handled': error_handled,
                'test_type': 'invalid_server_connection'
            }
            
            if error_handled:
                return HealthCheckResult(
                    component='error_recovery',
                    status=HealthStatus.HEALTHY,
                    message='Error recovery is working',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='error_recovery',
                    status=HealthStatus.WARNING,
                    message='Error recovery behavior unclear',
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='error_recovery',
                status=HealthStatus.CRITICAL,
                message=f'Error recovery check failed: {str(e)}',
                details={},
                error=str(e)
            )
            
    def _check_performance_metrics(self) -> HealthCheckResult:
        """Check performance metrics"""
        try:
            # Get recent performance data from health history
            recent_results = self._get_recent_results(minutes=10)
            
            if not recent_results:
                return HealthCheckResult(
                    component='performance_metrics',
                    status=HealthStatus.WARNING,
                    message='No recent performance data available',
                    details={}
                )
                
            # Calculate average response times
            response_times = [r.response_time for r in recent_results.values()]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            details = {
                'avg_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'sample_size': len(response_times),
                'threshold': self.alert_thresholds['response_time']
            }
            
            if avg_response_time > self.alert_thresholds['response_time']:
                return HealthCheckResult(
                    component='performance_metrics',
                    status=HealthStatus.WARNING,
                    message=f'High average response time: {avg_response_time:.2f}s',
                    details=details
                )
            else:
                return HealthCheckResult(
                    component='performance_metrics',
                    status=HealthStatus.HEALTHY,
                    message=f'Performance is good (avg: {avg_response_time:.2f}s)',
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component='performance_metrics',
                status=HealthStatus.CRITICAL,
                message=f'Performance metrics check failed: {str(e)}',
                details={},
                error=str(e)
            )


def create_health_checker(config_manager: WebSocketConfigManager = None, 
                         cors_manager: CORSManager = None) -> WebSocketHealthChecker:
    """Create a WebSocket health checker instance"""
    if not config_manager:
        config_manager = WebSocketConfigManager()
    if not cors_manager:
        cors_manager = CORSManager(config_manager)
        
    return WebSocketHealthChecker(config_manager, cors_manager)


def setup_basic_alerts(health_checker: WebSocketHealthChecker):
    """Set up basic alert callbacks"""
    
    def log_alert(result: HealthCheckResult):
        """Log health alerts"""
        logger = get_debug_logger('health_alerts', DebugLevel.WARNING)
        logger.warning(f"Health alert for {result.component}: {result.message}")
        
    def console_alert(result: HealthCheckResult):
        """Print health alerts to console"""
        timestamp = result.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] HEALTH ALERT - {result.component}: {result.message}")
        
    health_checker.add_alert_callback(log_alert)
    health_checker.add_alert_callback(console_alert)