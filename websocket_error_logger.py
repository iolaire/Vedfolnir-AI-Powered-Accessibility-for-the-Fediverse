# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Error Logging System

This module provides comprehensive error logging with actionable debugging information
for WebSocket connections, including structured logging, error aggregation, and
debugging assistance.
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any, TextIO
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict, deque
import threading
from dataclasses import asdict

from websocket_error_detector import WebSocketErrorInfo, WebSocketErrorCategory, WebSocketErrorSeverity


class WebSocketErrorLogger:
    """
    Comprehensive error logging system for WebSocket connections
    
    This class provides:
    - Structured error logging with JSON format
    - Error aggregation and pattern detection
    - Debugging assistance and suggestions
    - Error trend analysis
    - Actionable error reports
    """
    
    def __init__(self, log_dir: str = "logs", max_log_size: int = 10 * 1024 * 1024, max_recent_errors: int = 1000):
        """
        Initialize the error logger
        
        Args:
            log_dir: Directory for log files
            max_log_size: Maximum size for individual log files (bytes)
            max_recent_errors: Maximum number of recent errors to keep in memory
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.max_log_size = max_log_size
        self.max_recent_errors = max_recent_errors
        
        # Thread-safe collections for error tracking
        self._lock = threading.Lock()
        self._recent_errors = deque(maxlen=max_recent_errors)
        self._error_patterns = defaultdict(int)
        self._error_trends = defaultdict(list)
        
        # Setup loggers
        self._setup_loggers()
        
        # Error aggregation counters
        self._error_counters = {
            'total': 0,
            'by_category': defaultdict(int),
            'by_severity': defaultdict(int),
            'by_hour': defaultdict(int),
            'by_client': defaultdict(int)
        }
    
    def _setup_loggers(self) -> None:
        """Setup structured loggers for different error types"""
        
        # Main error logger
        self.error_logger = logging.getLogger('websocket.errors')
        self.error_logger.setLevel(logging.DEBUG)
        
        # CORS error logger
        self.cors_logger = logging.getLogger('websocket.cors')
        self.cors_logger.setLevel(logging.DEBUG)
        
        # Authentication error logger
        self.auth_logger = logging.getLogger('websocket.auth')
        self.auth_logger.setLevel(logging.DEBUG)
        
        # Network error logger
        self.network_logger = logging.getLogger('websocket.network')
        self.network_logger.setLevel(logging.DEBUG)
        
        # Setup file handlers
        self._setup_file_handlers()
        
        # Setup formatters
        self._setup_formatters()
    
    def _setup_file_handlers(self) -> None:
        """Setup rotating file handlers for different log types"""
        from logging.handlers import RotatingFileHandler
        
        # Main error log
        error_handler = RotatingFileHandler(
            self.log_dir / 'websocket_errors.log',
            maxBytes=self.max_log_size,
            backupCount=5
        )
        self.error_logger.addHandler(error_handler)
        
        # CORS error log
        cors_handler = RotatingFileHandler(
            self.log_dir / 'websocket_cors_errors.log',
            maxBytes=self.max_log_size,
            backupCount=3
        )
        self.cors_logger.addHandler(cors_handler)
        
        # Authentication error log
        auth_handler = RotatingFileHandler(
            self.log_dir / 'websocket_auth_errors.log',
            maxBytes=self.max_log_size,
            backupCount=3
        )
        self.auth_logger.addHandler(auth_handler)
        
        # Network error log
        network_handler = RotatingFileHandler(
            self.log_dir / 'websocket_network_errors.log',
            maxBytes=self.max_log_size,
            backupCount=3
        )
        self.network_logger.addHandler(network_handler)
        
        # JSON structured log for monitoring
        json_handler = RotatingFileHandler(
            self.log_dir / 'websocket_errors.json',
            maxBytes=self.max_log_size,
            backupCount=5
        )
        json_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Add JSON handler to main logger
        json_logger = logging.getLogger('websocket.json')
        json_logger.setLevel(logging.INFO)
        json_logger.addHandler(json_handler)
        self.json_logger = json_logger
    
    def _setup_formatters(self) -> None:
        """Setup log formatters"""
        
        # Detailed formatter for main logs
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
            'Context: %(context)s\n'
            'Debug Info: %(debug_info)s\n'
            '---'
        )
        
        # Simple formatter for category-specific logs
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Apply formatters
        for handler in self.error_logger.handlers:
            handler.setFormatter(detailed_formatter)
        
        for logger in [self.cors_logger, self.auth_logger, self.network_logger]:
            for handler in logger.handlers:
                handler.setFormatter(simple_formatter)
    
    def log_error(self, error_info: WebSocketErrorInfo) -> None:
        """
        Log a WebSocket error with comprehensive information
        
        Args:
            error_info: Comprehensive error information
        """
        with self._lock:
            # Add to recent errors
            self._recent_errors.append(error_info)
            
            # Update counters
            self._update_counters(error_info)
            
            # Update patterns and trends
            self._update_patterns(error_info)
        
        # Log to appropriate loggers
        self._log_to_category_logger(error_info)
        self._log_to_json(error_info)
        self._log_to_main_logger(error_info)
    
    def log_cors_error(self, error_info: WebSocketErrorInfo, origin: str, allowed_origins: List[str]) -> None:
        """
        Log CORS-specific error with detailed information
        
        Args:
            error_info: Error information
            origin: Failed origin
            allowed_origins: List of allowed origins
        """
        cors_details = {
            'failed_origin': origin,
            'allowed_origins': allowed_origins,
            'origin_analysis': error_info.debug_info.get('cors_analysis', {}),
            'suggested_fixes': [
                f"Add '{origin}' to CORS_ORIGINS environment variable",
                "Check if origin protocol (http/https) matches server configuration",
                "Verify origin format includes protocol and port if non-standard",
                "Review CORS middleware configuration"
            ]
        }
        
        # Add CORS-specific context
        error_info.context.update({'cors_details': cors_details})
        
        # Log with CORS-specific information
        self.cors_logger.error(
            f"CORS Error [{error_info.error_code}]: Origin '{origin}' not allowed",
            extra={
                'error_code': error_info.error_code,
                'origin': origin,
                'allowed_origins': allowed_origins,
                'cors_analysis': error_info.debug_info.get('cors_analysis', {}),
                'suggested_fixes': cors_details['suggested_fixes']
            }
        )
        
        # Log to main system
        self.log_error(error_info)
    
    def log_authentication_error(self, error_info: WebSocketErrorInfo, user_id: Optional[int], session_data: Optional[Dict]) -> None:
        """
        Log authentication-specific error with detailed information
        
        Args:
            error_info: Error information
            user_id: User ID if available
            session_data: Session information
        """
        auth_details = {
            'user_id': user_id,
            'session_available': bool(session_data),
            'session_keys': list(session_data.keys()) if session_data else [],
            'auth_analysis': error_info.debug_info.get('auth_analysis', {}),
            'suggested_fixes': [
                "Verify user session is valid and not expired",
                "Check authentication token integrity",
                "Ensure user has required permissions",
                "Review session configuration and timeout settings",
                "Check Redis session storage connectivity"
            ]
        }
        
        # Add auth-specific context
        error_info.context.update({'auth_details': auth_details})
        
        # Log with authentication-specific information
        self.auth_logger.error(
            f"Auth Error [{error_info.error_code}]: Authentication failed for user {user_id}",
            extra={
                'error_code': error_info.error_code,
                'user_id': user_id,
                'session_available': bool(session_data),
                'auth_analysis': error_info.debug_info.get('auth_analysis', {}),
                'suggested_fixes': auth_details['suggested_fixes']
            }
        )
        
        # Log to main system
        self.log_error(error_info)
    
    def log_network_error(self, error_info: WebSocketErrorInfo, connection_info: Dict) -> None:
        """
        Log network-specific error with detailed information
        
        Args:
            error_info: Error information
            connection_info: Connection details
        """
        network_details = {
            'connection_info': connection_info,
            'network_analysis': error_info.debug_info.get('network_analysis', {}),
            'suggested_fixes': [
                "Check network connectivity to server",
                "Verify firewall settings allow WebSocket connections",
                "Test with different network connection",
                "Check proxy settings and WebSocket support",
                "Verify server is running and accessible"
            ]
        }
        
        # Add network-specific context
        error_info.context.update({'network_details': network_details})
        
        # Log with network-specific information
        self.network_logger.error(
            f"Network Error [{error_info.error_code}]: Connection failed to {connection_info.get('host', 'unknown')}",
            extra={
                'error_code': error_info.error_code,
                'connection_info': connection_info,
                'network_analysis': error_info.debug_info.get('network_analysis', {}),
                'suggested_fixes': network_details['suggested_fixes']
            }
        )
        
        # Log to main system
        self.log_error(error_info)
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive error summary for specified time period
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dict containing error summary and analysis
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [
                error for error in self._recent_errors
                if error.timestamp >= cutoff_time
            ]
        
        if not recent_errors:
            return {
                'period_hours': hours,
                'total_errors': 0,
                'summary': 'No errors in specified period'
            }
        
        # Analyze errors
        category_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        error_codes = []
        top_patterns = defaultdict(int)
        
        for error in recent_errors:
            category_counts[error.category.value] += 1
            severity_counts[error.severity.value] += 1
            error_codes.append(error.error_code)
            
            # Extract patterns
            if 'original_error' in error.debug_info:
                pattern = error.debug_info['original_error'][:50]  # First 50 chars
                top_patterns[pattern] += 1
        
        return {
            'period_hours': hours,
            'total_errors': len(recent_errors),
            'by_category': dict(category_counts),
            'by_severity': dict(severity_counts),
            'top_error_patterns': dict(sorted(top_patterns.items(), key=lambda x: x[1], reverse=True)[:5]),
            'recent_error_codes': error_codes[-10:],  # Last 10 error codes
            'trends': self._analyze_trends(recent_errors),
            'actionable_insights': self._generate_actionable_insights(recent_errors)
        }
    
    def get_debugging_report(self, error_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed debugging report for specific error
        
        Args:
            error_code: Error code to analyze
            
        Returns:
            Detailed debugging information or None if not found
        """
        with self._lock:
            for error in reversed(self._recent_errors):
                if error.error_code == error_code:
                    return self._generate_debugging_report(error)
        
        return None
    
    def export_error_logs(self, output_file: str, hours: int = 24, format: str = 'json') -> bool:
        """
        Export error logs to file
        
        Args:
            output_file: Output file path
            hours: Number of hours to export
            format: Export format ('json' or 'csv')
            
        Returns:
            Success status
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            with self._lock:
                recent_errors = [
                    error for error in self._recent_errors
                    if error.timestamp >= cutoff_time
                ]
            
            if format.lower() == 'json':
                return self._export_json(recent_errors, output_file)
            elif format.lower() == 'csv':
                return self._export_csv(recent_errors, output_file)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            self.error_logger.error(f"Failed to export error logs: {e}")
            return False
    
    def _update_counters(self, error_info: WebSocketErrorInfo) -> None:
        """Update error counters"""
        self._error_counters['total'] += 1
        self._error_counters['by_category'][error_info.category.value] += 1
        self._error_counters['by_severity'][error_info.severity.value] += 1
        
        # Hour-based counting
        hour_key = error_info.timestamp.strftime('%Y-%m-%d-%H')
        self._error_counters['by_hour'][hour_key] += 1
        
        # Client-based counting
        client_id = error_info.context.get('client_id', 'unknown')
        self._error_counters['by_client'][client_id] += 1
    
    def _update_patterns(self, error_info: WebSocketErrorInfo) -> None:
        """Update error patterns for trend analysis"""
        pattern_key = f"{error_info.category.value}:{error_info.severity.value}"
        self._error_patterns[pattern_key] += 1
        
        # Add to trends
        hour_key = error_info.timestamp.strftime('%Y-%m-%d-%H')
        self._error_trends[pattern_key].append(hour_key)
    
    def _log_to_category_logger(self, error_info: WebSocketErrorInfo) -> None:
        """Log to category-specific logger"""
        message = f"[{error_info.error_code}] {error_info.message}"
        
        if error_info.category == WebSocketErrorCategory.CORS:
            self.cors_logger.error(message)
        elif error_info.category in [WebSocketErrorCategory.AUTHENTICATION, WebSocketErrorCategory.AUTHORIZATION]:
            self.auth_logger.error(message)
        elif error_info.category == WebSocketErrorCategory.NETWORK:
            self.network_logger.error(message)
    
    def _log_to_json(self, error_info: WebSocketErrorInfo) -> None:
        """Log to JSON format for monitoring"""
        json_data = {
            'timestamp': error_info.timestamp.isoformat(),
            'error_code': error_info.error_code,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'message': error_info.message,
            'user_message': error_info.user_message,
            'context': error_info.context,
            'debug_info': error_info.debug_info
        }
        
        self.json_logger.info(json.dumps(json_data))
    
    def _log_to_main_logger(self, error_info: WebSocketErrorInfo) -> None:
        """Log to main error logger"""
        self.error_logger.error(
            f"WebSocket Error [{error_info.error_code}]: {error_info.message}",
            extra={
                'context': error_info.context,
                'debug_info': error_info.debug_info,
                'error_code': error_info.error_code,
                'category': error_info.category.value,
                'severity': error_info.severity.value
            }
        )
    
    def _analyze_trends(self, errors: List[WebSocketErrorInfo]) -> Dict[str, Any]:
        """Analyze error trends"""
        if len(errors) < 2:
            return {'trend': 'insufficient_data'}
        
        # Group by hour
        hourly_counts = defaultdict(int)
        for error in errors:
            hour_key = error.timestamp.strftime('%H')
            hourly_counts[hour_key] += 1
        
        # Simple trend analysis
        hours = sorted(hourly_counts.keys())
        if len(hours) >= 2:
            recent_avg = sum(hourly_counts[h] for h in hours[-2:]) / 2
            earlier_avg = sum(hourly_counts[h] for h in hours[:-2]) / max(1, len(hours) - 2)
            
            if recent_avg > earlier_avg * 1.5:
                trend = 'increasing'
            elif recent_avg < earlier_avg * 0.5:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'hourly_distribution': dict(hourly_counts),
            'peak_hour': max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else None
        }
    
    def _generate_actionable_insights(self, errors: List[WebSocketErrorInfo]) -> List[str]:
        """Generate actionable insights from error patterns"""
        insights = []
        
        # Category analysis
        category_counts = defaultdict(int)
        for error in errors:
            category_counts[error.category.value] += 1
        
        if category_counts:
            top_category = max(category_counts.items(), key=lambda x: x[1])
            
            if top_category[0] == 'cors':
                insights.append("High CORS error rate detected. Review CORS configuration and allowed origins.")
            elif top_category[0] == 'authentication':
                insights.append("Authentication errors are common. Check session management and token validation.")
            elif top_category[0] == 'network':
                insights.append("Network connectivity issues detected. Verify server accessibility and network configuration.")
            elif top_category[0] == 'transport':
                insights.append("Transport failures occurring. Consider implementing transport fallback mechanisms.")
        
        # Severity analysis
        severity_counts = defaultdict(int)
        for error in errors:
            severity_counts[error.severity.value] += 1
        
        critical_count = severity_counts.get('critical', 0)
        high_count = severity_counts.get('high', 0)
        
        if critical_count > 0:
            insights.append(f"{critical_count} critical errors require immediate attention.")
        if high_count > len(errors) * 0.5:
            insights.append("High severity errors are prevalent. Review system stability.")
        
        return insights
    
    def _generate_debugging_report(self, error_info: WebSocketErrorInfo) -> Dict[str, Any]:
        """Generate detailed debugging report for specific error"""
        return {
            'error_code': error_info.error_code,
            'timestamp': error_info.timestamp.isoformat(),
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'description': error_info.message,
            'user_message': error_info.user_message,
            'suggested_fix': error_info.suggested_fix,
            'context': error_info.context,
            'debug_info': error_info.debug_info,
            'stack_trace': error_info.stack_trace,
            'debugging_steps': self._get_debugging_steps(error_info),
            'related_documentation': self._get_related_documentation(error_info)
        }
    
    def _get_debugging_steps(self, error_info: WebSocketErrorInfo) -> List[str]:
        """Get step-by-step debugging instructions"""
        steps = []
        
        if error_info.category == WebSocketErrorCategory.CORS:
            steps.extend([
                "1. Check browser developer tools for CORS error details",
                "2. Verify CORS_ORIGINS environment variable includes the failing origin",
                "3. Ensure server handles OPTIONS preflight requests",
                "4. Test with curl to verify server CORS headers",
                "5. Check if origin includes correct protocol (http/https)"
            ])
        elif error_info.category == WebSocketErrorCategory.AUTHENTICATION:
            steps.extend([
                "1. Verify user is logged in and session is valid",
                "2. Check Redis session storage connectivity",
                "3. Validate authentication token integrity",
                "4. Review user permissions and roles",
                "5. Check session timeout configuration"
            ])
        elif error_info.category == WebSocketErrorCategory.NETWORK:
            steps.extend([
                "1. Test basic network connectivity to server",
                "2. Check firewall rules for WebSocket ports",
                "3. Verify DNS resolution for server hostname",
                "4. Test with different network connection",
                "5. Check proxy settings and WebSocket support"
            ])
        
        return steps
    
    def _get_related_documentation(self, error_info: WebSocketErrorInfo) -> List[str]:
        """Get related documentation links"""
        docs = []
        
        if error_info.category == WebSocketErrorCategory.CORS:
            docs.extend([
                "WebSocket CORS Configuration Guide",
                "Browser CORS Policy Documentation",
                "Troubleshooting CORS Issues"
            ])
        elif error_info.category == WebSocketErrorCategory.AUTHENTICATION:
            docs.extend([
                "WebSocket Authentication Setup",
                "Session Management Documentation",
                "Redis Session Configuration"
            ])
        elif error_info.category == WebSocketErrorCategory.NETWORK:
            docs.extend([
                "Network Connectivity Troubleshooting",
                "WebSocket Firewall Configuration",
                "Proxy and Load Balancer Setup"
            ])
        
        return docs
    
    def _export_json(self, errors: List[WebSocketErrorInfo], output_file: str) -> bool:
        """Export errors to JSON format"""
        try:
            export_data = []
            for error in errors:
                export_data.append({
                    'timestamp': error.timestamp.isoformat(),
                    'error_code': error.error_code,
                    'category': error.category.value,
                    'severity': error.severity.value,
                    'message': error.message,
                    'user_message': error.user_message,
                    'suggested_fix': error.suggested_fix,
                    'context': error.context,
                    'debug_info': error.debug_info
                })
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def _export_csv(self, errors: List[WebSocketErrorInfo], output_file: str) -> bool:
        """Export errors to CSV format"""
        try:
            import csv
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'Timestamp', 'Error Code', 'Category', 'Severity',
                    'Message', 'User Message', 'Suggested Fix', 'Context'
                ])
                
                # Data
                for error in errors:
                    writer.writerow([
                        error.timestamp.isoformat(),
                        error.error_code,
                        error.category.value,
                        error.severity.value,
                        error.message,
                        error.user_message,
                        error.suggested_fix,
                        json.dumps(error.context)
                    ])
            
            return True
        except Exception:
            return False