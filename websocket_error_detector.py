# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Error Detection and Categorization System

This module provides comprehensive error detection, categorization, and handling
for WebSocket connections, including CORS, authentication, and network issues.
"""

import re
import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json


class WebSocketErrorCategory(Enum):
    """Categories of WebSocket errors for systematic handling"""
    CORS = "cors"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    TRANSPORT = "transport"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CONFIGURATION = "configuration"
    SERVER = "server"
    CLIENT = "client"
    UNKNOWN = "unknown"


class WebSocketErrorSeverity(Enum):
    """Severity levels for WebSocket errors"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ErrorPattern:
    """Pattern for matching and categorizing errors"""
    pattern: str
    category: WebSocketErrorCategory
    severity: WebSocketErrorSeverity
    description: str
    suggested_fix: str
    user_message: str
    debug_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSocketErrorInfo:
    """Comprehensive error information"""
    category: WebSocketErrorCategory
    severity: WebSocketErrorSeverity
    error_code: str
    message: str
    user_message: str
    suggested_fix: str
    debug_info: Dict[str, Any]
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None


class WebSocketErrorDetector:
    """
    Comprehensive error detection and categorization system for WebSocket connections
    
    This class provides:
    - Pattern-based error detection
    - CORS-specific error recognition
    - Authentication failure detection
    - Network and transport error categorization
    - Detailed error logging with actionable information
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the error detector
        
        Args:
            logger: Optional logger instance for error reporting
        """
        self.logger = logger or logging.getLogger(__name__)
        self._error_patterns = self._initialize_error_patterns()
        self._error_stats = {
            'total_errors': 0,
            'by_category': {category.value: 0 for category in WebSocketErrorCategory},
            'by_severity': {severity.value: 0 for severity in WebSocketErrorSeverity}
        }
    
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize comprehensive error patterns for detection"""
        return [
            # CORS Error Patterns
            ErrorPattern(
                pattern=r"cors|cross.?origin|origin.*not.*allowed|access.?control",
                category=WebSocketErrorCategory.CORS,
                severity=WebSocketErrorSeverity.HIGH,
                description="Cross-Origin Resource Sharing (CORS) policy violation",
                suggested_fix="Check CORS configuration and allowed origins",
                user_message="Connection blocked by browser security policy. Please contact support if this persists.",
                debug_info={"check_origins": True, "verify_headers": True}
            ),
            ErrorPattern(
                pattern=r"preflight.*fail|options.*request.*fail",
                category=WebSocketErrorCategory.CORS,
                severity=WebSocketErrorSeverity.HIGH,
                description="CORS preflight request failed",
                suggested_fix="Ensure server handles OPTIONS requests properly",
                user_message="Browser security check failed. Please try refreshing the page.",
                debug_info={"check_preflight": True, "verify_options_handler": True}
            ),
            ErrorPattern(
                pattern=r"origin.*mismatch|invalid.*origin",
                category=WebSocketErrorCategory.CORS,
                severity=WebSocketErrorSeverity.HIGH,
                description="WebSocket origin validation failed",
                suggested_fix="Verify origin is in allowed origins list",
                user_message="Connection rejected due to security policy. Please ensure you're accessing from the correct URL.",
                debug_info={"validate_origin": True, "check_allowed_origins": True}
            ),
            
            # Authentication Error Patterns
            ErrorPattern(
                pattern=r"unauthorized|authentication.*fail|invalid.*token|token.*expired",
                category=WebSocketErrorCategory.AUTHENTICATION,
                severity=WebSocketErrorSeverity.HIGH,
                description="Authentication failed or token invalid",
                suggested_fix="Verify user credentials and session validity",
                user_message="Authentication failed. Please log in again.",
                debug_info={"check_session": True, "verify_token": True}
            ),
            ErrorPattern(
                pattern=r"session.*expired|session.*invalid|no.*session",
                category=WebSocketErrorCategory.AUTHENTICATION,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="User session expired or invalid",
                suggested_fix="Redirect user to login page",
                user_message="Your session has expired. Please log in again.",
                debug_info={"redirect_login": True, "clear_session": True}
            ),
            ErrorPattern(
                pattern=r"permission.*denied|access.*denied|forbidden",
                category=WebSocketErrorCategory.AUTHORIZATION,
                severity=WebSocketErrorSeverity.HIGH,
                description="User lacks required permissions",
                suggested_fix="Verify user role and permissions",
                user_message="You don't have permission to access this feature.",
                debug_info={"check_permissions": True, "verify_role": True}
            ),
            
            # Network Error Patterns
            ErrorPattern(
                pattern=r"connection.*refused|connection.*reset|network.*error",
                category=WebSocketErrorCategory.NETWORK,
                severity=WebSocketErrorSeverity.HIGH,
                description="Network connectivity issue",
                suggested_fix="Check network connectivity and server status",
                user_message="Network connection problem. Please check your internet connection.",
                debug_info={"check_connectivity": True, "verify_server": True}
            ),
            ErrorPattern(
                pattern=r"dns.*resolution.*fail|host.*not.*found|name.*resolution.*fail",
                category=WebSocketErrorCategory.NETWORK,
                severity=WebSocketErrorSeverity.HIGH,
                description="DNS resolution failed",
                suggested_fix="Verify hostname and DNS configuration",
                user_message="Cannot reach server. Please try again later.",
                debug_info={"check_dns": True, "verify_hostname": True}
            ),
            ErrorPattern(
                pattern=r"ssl.*error|tls.*error|certificate.*error",
                category=WebSocketErrorCategory.NETWORK,
                severity=WebSocketErrorSeverity.HIGH,
                description="SSL/TLS connection error",
                suggested_fix="Check SSL certificate and configuration",
                user_message="Secure connection failed. Please contact support.",
                debug_info={"check_ssl": True, "verify_certificate": True}
            ),
            
            # Transport Error Patterns
            ErrorPattern(
                pattern=r"websocket.*not.*supported|websocket.*fail",
                category=WebSocketErrorCategory.TRANSPORT,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="WebSocket transport not supported or failed",
                suggested_fix="Fall back to polling transport",
                user_message="WebSocket connection failed. Switching to alternative method.",
                debug_info={"fallback_polling": True, "check_browser_support": True}
            ),
            ErrorPattern(
                pattern=r"polling.*fail|xhr.*fail|long.*polling.*error",
                category=WebSocketErrorCategory.TRANSPORT,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="Polling transport failed",
                suggested_fix="Check HTTP connectivity and server configuration",
                user_message="Connection method failed. Trying alternative approach.",
                debug_info={"check_http": True, "verify_polling_endpoint": True}
            ),
            
            # Timeout Error Patterns
            ErrorPattern(
                pattern=r"timeout|timed.*out|connection.*timeout",
                category=WebSocketErrorCategory.TIMEOUT,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="Connection or operation timed out",
                suggested_fix="Increase timeout values or check network latency",
                user_message="Connection timed out. Please try again.",
                debug_info={"check_latency": True, "adjust_timeout": True}
            ),
            ErrorPattern(
                pattern=r"ping.*timeout|pong.*timeout|heartbeat.*fail",
                category=WebSocketErrorCategory.TIMEOUT,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="WebSocket heartbeat/ping timeout",
                suggested_fix="Check ping/pong configuration and network stability",
                user_message="Connection heartbeat failed. Reconnecting...",
                debug_info={"check_heartbeat": True, "verify_ping_config": True}
            ),
            
            # Rate Limiting Error Patterns
            ErrorPattern(
                pattern=r"rate.*limit|too.*many.*requests|throttle",
                category=WebSocketErrorCategory.RATE_LIMIT,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="Rate limit exceeded",
                suggested_fix="Implement exponential backoff and reduce request frequency",
                user_message="Too many requests. Please wait a moment before trying again.",
                debug_info={"implement_backoff": True, "reduce_frequency": True}
            ),
            
            # Configuration Error Patterns
            ErrorPattern(
                pattern=r"configuration.*error|config.*invalid|setting.*error",
                category=WebSocketErrorCategory.CONFIGURATION,
                severity=WebSocketErrorSeverity.HIGH,
                description="WebSocket configuration error",
                suggested_fix="Review and validate WebSocket configuration",
                user_message="System configuration error. Please contact support.",
                debug_info={"validate_config": True, "check_settings": True}
            ),
            
            # Server Error Patterns
            ErrorPattern(
                pattern=r"internal.*server.*error|server.*error|500|502|503|504",
                category=WebSocketErrorCategory.SERVER,
                severity=WebSocketErrorSeverity.HIGH,
                description="Server-side error",
                suggested_fix="Check server logs and system health",
                user_message="Server error occurred. Please try again later.",
                debug_info={"check_server_logs": True, "verify_health": True}
            ),
            ErrorPattern(
                pattern=r"service.*unavailable|server.*unavailable|maintenance",
                category=WebSocketErrorCategory.SERVER,
                severity=WebSocketErrorSeverity.HIGH,
                description="Server unavailable or in maintenance",
                suggested_fix="Wait for server to become available",
                user_message="Service temporarily unavailable. Please try again later.",
                debug_info={"check_maintenance": True, "wait_retry": True}
            ),
            
            # Client Error Patterns
            ErrorPattern(
                pattern=r"client.*error|browser.*error|400|404",
                category=WebSocketErrorCategory.CLIENT,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="Client-side error",
                suggested_fix="Check client configuration and browser compatibility",
                user_message="Browser compatibility issue. Please try refreshing or using a different browser.",
                debug_info={"check_browser": True, "verify_compatibility": True}
            )
        ]
    
    def detect_error(self, error: Union[Exception, str, Dict], context: Optional[Dict[str, Any]] = None) -> WebSocketErrorInfo:
        """
        Detect and categorize a WebSocket error
        
        Args:
            error: Error to analyze (Exception, string, or dict)
            context: Additional context information
            
        Returns:
            WebSocketErrorInfo: Comprehensive error information
        """
        # Convert error to string for pattern matching
        error_text = self._extract_error_text(error)
        error_lower = error_text.lower()
        
        # Find matching pattern
        matched_pattern = None
        for pattern in self._error_patterns:
            if re.search(pattern.pattern, error_lower, re.IGNORECASE):
                matched_pattern = pattern
                break
        
        # Use default pattern if no match found
        if not matched_pattern:
            matched_pattern = ErrorPattern(
                pattern=".*",
                category=WebSocketErrorCategory.UNKNOWN,
                severity=WebSocketErrorSeverity.MEDIUM,
                description="Unknown error occurred",
                suggested_fix="Check error details and logs for more information",
                user_message="An unexpected error occurred. Please try again.",
                debug_info={"review_logs": True}
            )
        
        # Generate error code
        error_code = self._generate_error_code(matched_pattern.category, error)
        
        # Extract stack trace if available
        stack_trace = None
        if isinstance(error, Exception):
            stack_trace = traceback.format_exc()
        
        # Create comprehensive error info
        error_info = WebSocketErrorInfo(
            category=matched_pattern.category,
            severity=matched_pattern.severity,
            error_code=error_code,
            message=matched_pattern.description,
            user_message=matched_pattern.user_message,
            suggested_fix=matched_pattern.suggested_fix,
            debug_info=matched_pattern.debug_info.copy(),
            timestamp=datetime.now(timezone.utc),
            context=context or {},
            stack_trace=stack_trace
        )
        
        # Add original error details to debug info
        error_info.debug_info.update({
            'original_error': error_text,
            'error_type': type(error).__name__ if isinstance(error, Exception) else 'string',
            'pattern_matched': matched_pattern.pattern
        })
        
        # Update statistics
        self._update_error_stats(error_info)
        
        # Log the error
        self._log_error(error_info)
        
        return error_info
    
    def detect_cors_error(self, origin: str, allowed_origins: List[str], error_details: Optional[Dict] = None) -> WebSocketErrorInfo:
        """
        Detect and analyze CORS-specific errors
        
        Args:
            origin: Request origin
            allowed_origins: List of allowed origins
            error_details: Additional error details
            
        Returns:
            WebSocketErrorInfo: CORS-specific error information
        """
        context = {
            'origin': origin,
            'allowed_origins': allowed_origins,
            'error_details': error_details or {}
        }
        
        # Determine specific CORS issue
        if not origin:
            error_text = "Missing origin header in WebSocket request"
        elif origin not in allowed_origins:
            error_text = f"Origin '{origin}' not in allowed origins list"
        else:
            error_text = "CORS validation failed for unknown reason"
        
        error_info = self.detect_error(error_text, context)
        
        # Add CORS-specific debug information
        error_info.debug_info.update({
            'cors_analysis': {
                'origin_provided': bool(origin),
                'origin_in_allowed_list': origin in allowed_origins if origin else False,
                'allowed_origins_count': len(allowed_origins),
                'origin_protocol': origin.split('://')[0] if origin and '://' in origin else 'unknown',
                'suggested_origins': self._suggest_cors_origins(origin, allowed_origins)
            }
        })
        
        return error_info
    
    def detect_authentication_error(self, user_id: Optional[int], session_data: Optional[Dict], error_details: Optional[Dict] = None) -> WebSocketErrorInfo:
        """
        Detect and analyze authentication-specific errors
        
        Args:
            user_id: User ID if available
            session_data: Session information
            error_details: Additional error details
            
        Returns:
            WebSocketErrorInfo: Authentication-specific error information
        """
        context = {
            'user_id': user_id,
            'session_data': session_data,
            'error_details': error_details or {}
        }
        
        # Determine specific authentication issue
        if not user_id:
            error_text = "No user ID found in WebSocket authentication"
        elif not session_data:
            error_text = "No session data found for WebSocket authentication"
        else:
            error_text = "WebSocket authentication validation failed"
        
        error_info = self.detect_error(error_text, context)
        
        # Add authentication-specific debug information
        error_info.debug_info.update({
            'auth_analysis': {
                'user_id_provided': bool(user_id),
                'session_data_available': bool(session_data),
                'session_keys': list(session_data.keys()) if session_data else [],
                'authentication_method': self._determine_auth_method(session_data),
                'session_age': self._calculate_session_age(session_data)
            }
        })
        
        return error_info
    
    def detect_network_error(self, connection_info: Dict, error_details: Optional[Dict] = None) -> WebSocketErrorInfo:
        """
        Detect and analyze network-specific errors
        
        Args:
            connection_info: Connection information (host, port, protocol, etc.)
            error_details: Additional error details
            
        Returns:
            WebSocketErrorInfo: Network-specific error information
        """
        context = {
            'connection_info': connection_info,
            'error_details': error_details or {}
        }
        
        # Determine specific network issue
        error_text = f"Network error connecting to {connection_info.get('host', 'unknown')}:{connection_info.get('port', 'unknown')}"
        
        error_info = self.detect_error(error_text, context)
        
        # Add network-specific debug information
        error_info.debug_info.update({
            'network_analysis': {
                'host': connection_info.get('host'),
                'port': connection_info.get('port'),
                'protocol': connection_info.get('protocol'),
                'transport': connection_info.get('transport'),
                'connection_attempts': connection_info.get('attempts', 0),
                'last_successful_connection': connection_info.get('last_success'),
                'network_diagnostics': self._perform_network_diagnostics(connection_info)
            }
        })
        
        return error_info
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive error statistics
        
        Returns:
            Dict containing error statistics and trends
        """
        return {
            'statistics': self._error_stats.copy(),
            'top_categories': self._get_top_error_categories(),
            'severity_distribution': self._get_severity_distribution(),
            'recent_trends': self._get_recent_error_trends()
        }
    
    def get_debugging_suggestions(self, error_info: WebSocketErrorInfo) -> List[str]:
        """
        Get specific debugging suggestions for an error
        
        Args:
            error_info: Error information
            
        Returns:
            List of debugging suggestions
        """
        suggestions = [error_info.suggested_fix]
        
        # Add category-specific suggestions
        if error_info.category == WebSocketErrorCategory.CORS:
            suggestions.extend([
                "Verify CORS_ORIGINS environment variable",
                "Check browser developer tools for CORS errors",
                "Ensure server handles OPTIONS requests",
                "Validate origin against allowed origins list"
            ])
        elif error_info.category == WebSocketErrorCategory.AUTHENTICATION:
            suggestions.extend([
                "Check user session validity",
                "Verify authentication tokens",
                "Ensure user has required permissions",
                "Check session expiration settings"
            ])
        elif error_info.category == WebSocketErrorCategory.NETWORK:
            suggestions.extend([
                "Test network connectivity",
                "Check firewall settings",
                "Verify server is running and accessible",
                "Test with different network connection"
            ])
        elif error_info.category == WebSocketErrorCategory.TRANSPORT:
            suggestions.extend([
                "Try different transport method (WebSocket vs polling)",
                "Check browser WebSocket support",
                "Verify proxy/firewall WebSocket support",
                "Test with different browser"
            ])
        
        return suggestions
    
    def _extract_error_text(self, error: Union[Exception, str, Dict]) -> str:
        """Extract text from various error types"""
        if isinstance(error, Exception):
            return str(error)
        elif isinstance(error, str):
            return error
        elif isinstance(error, dict):
            return json.dumps(error)
        else:
            return str(error)
    
    def _generate_error_code(self, category: WebSocketErrorCategory, error: Any) -> str:
        """Generate unique error code"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        category_code = category.value.upper()[:4]
        error_hash = abs(hash(str(error))) % 10000
        return f"WS_{category_code}_{timestamp}_{error_hash:04d}"
    
    def _update_error_stats(self, error_info: WebSocketErrorInfo) -> None:
        """Update error statistics"""
        self._error_stats['total_errors'] += 1
        self._error_stats['by_category'][error_info.category.value] += 1
        self._error_stats['by_severity'][error_info.severity.value] += 1
    
    def _log_error(self, error_info: WebSocketErrorInfo) -> None:
        """Log error with appropriate level"""
        log_message = f"WebSocket Error [{error_info.error_code}]: {error_info.message}"
        
        if error_info.severity in [WebSocketErrorSeverity.CRITICAL, WebSocketErrorSeverity.HIGH]:
            self.logger.error(log_message, extra={
                'error_code': error_info.error_code,
                'category': error_info.category.value,
                'severity': error_info.severity.value,
                'debug_info': error_info.debug_info,
                'context': error_info.context
            })
        elif error_info.severity == WebSocketErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra={
                'error_code': error_info.error_code,
                'category': error_info.category.value
            })
        else:
            self.logger.info(log_message, extra={
                'error_code': error_info.error_code,
                'category': error_info.category.value
            })
    
    def _suggest_cors_origins(self, origin: str, allowed_origins: List[str]) -> List[str]:
        """Suggest possible CORS origins based on the failed origin"""
        if not origin:
            return []
        
        suggestions = []
        
        # Try different protocols
        if origin.startswith('http://'):
            suggestions.append(origin.replace('http://', 'https://'))
        elif origin.startswith('https://'):
            suggestions.append(origin.replace('https://', 'http://'))
        
        # Try localhost variations
        if 'localhost' in origin:
            suggestions.append(origin.replace('localhost', '127.0.0.1'))
        elif '127.0.0.1' in origin:
            suggestions.append(origin.replace('127.0.0.1', 'localhost'))
        
        return suggestions[:3]  # Limit suggestions
    
    def _determine_auth_method(self, session_data: Optional[Dict]) -> str:
        """Determine authentication method from session data"""
        if not session_data:
            return "unknown"
        
        if 'user_id' in session_data:
            return "session_based"
        elif 'token' in session_data:
            return "token_based"
        else:
            return "unknown"
    
    def _calculate_session_age(self, session_data: Optional[Dict]) -> Optional[str]:
        """Calculate session age if timestamp available"""
        if not session_data or 'created_at' not in session_data:
            return None
        
        try:
            created_at = datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - created_at
            return str(age)
        except (ValueError, TypeError):
            return None
    
    def _perform_network_diagnostics(self, connection_info: Dict) -> Dict[str, Any]:
        """Perform basic network diagnostics"""
        return {
            'host_reachable': 'unknown',  # Would need actual network testing
            'port_open': 'unknown',
            'dns_resolution': 'unknown',
            'ssl_valid': 'unknown'
        }
    
    def _get_top_error_categories(self) -> List[Tuple[str, int]]:
        """Get top error categories by frequency"""
        categories = [(cat, count) for cat, count in self._error_stats['by_category'].items() if count > 0]
        return sorted(categories, key=lambda x: x[1], reverse=True)[:5]
    
    def _get_severity_distribution(self) -> Dict[str, float]:
        """Get error severity distribution as percentages"""
        total = self._error_stats['total_errors']
        if total == 0:
            return {severity.value: 0.0 for severity in WebSocketErrorSeverity}
        
        return {
            severity: (count / total) * 100
            for severity, count in self._error_stats['by_severity'].items()
        }
    
    def _get_recent_error_trends(self) -> Dict[str, Any]:
        """Get recent error trends (placeholder for future implementation)"""
        return {
            'trend': 'stable',
            'recent_increase': False,
            'most_common_recent': 'unknown'
        }