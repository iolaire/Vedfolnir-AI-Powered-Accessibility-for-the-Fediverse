# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Configuration Management System

This module provides centralized configuration management for WebSocket settings,
including dynamic CORS origin generation, environment variable parsing, and
configuration validation with fallback mechanisms.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from config import Config
from websocket_config_validator import WebSocketConfigValidator
from websocket_config_health_checker import WebSocketConfigHealthChecker

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConfig:
    """Configuration schema for WebSocket settings"""
    
    # CORS Configuration
    cors_origins: List[str] = field(default_factory=list)
    cors_credentials: bool = True
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "POST"])
    cors_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])
    
    # SocketIO Configuration
    async_mode: str = "threading"
    transports: List[str] = field(default_factory=lambda: ["websocket", "polling"])
    ping_timeout: int = 60
    ping_interval: int = 25
    max_http_buffer_size: int = 1000000
    
    # Client Configuration
    reconnection: bool = True
    reconnection_attempts: int = 5
    reconnection_delay: int = 1000
    reconnection_delay_max: int = 5000
    timeout: int = 20000
    
    # Security Configuration
    require_auth: bool = True
    session_validation: bool = True
    rate_limiting: bool = True
    csrf_protection: bool = True


class WebSocketConfigManager:
    """
    Centralized configuration manager for WebSocket settings
    
    Handles environment variable parsing, dynamic CORS origin generation,
    configuration validation, and fallback mechanisms.
    """
    
    def __init__(self, config: Config):
        """
        Initialize WebSocket configuration manager
        
        Args:
            config: Main application configuration instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._websocket_config = None
        self._validation_errors = []
        
        # Initialize validator and health checker
        self._validator = WebSocketConfigValidator()
        self._health_checker = WebSocketConfigHealthChecker()
        
        # Load configuration on initialization
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load WebSocket configuration from environment variables"""
        try:
            self._websocket_config = self._create_websocket_config()
            self._validation_errors = self._validate_configuration()
            
            if self._validation_errors:
                self.logger.warning(f"WebSocket configuration validation warnings: {'; '.join(self._validation_errors)}")
            else:
                self.logger.info("WebSocket configuration loaded successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to load WebSocket configuration: {e}")
            # Create fallback configuration
            self._websocket_config = self._create_fallback_config()
            self._validation_errors = [f"Using fallback configuration due to error: {e}"]
    
    def _create_websocket_config(self) -> WebSocketConfig:
        """Create WebSocket configuration from environment variables"""
        
        # Generate CORS origins
        cors_origins = self._generate_cors_origins()
        
        # Parse transport configuration
        transports = self._parse_transports()
        
        # Create configuration object
        return WebSocketConfig(
            # CORS Configuration
            cors_origins=cors_origins,
            cors_credentials=self._parse_bool("SOCKETIO_CORS_CREDENTIALS", True),
            cors_methods=self._parse_list("SOCKETIO_CORS_METHODS", ["GET", "POST"]),
            cors_headers=self._parse_list("SOCKETIO_CORS_HEADERS", ["Content-Type", "Authorization"]),
            
            # SocketIO Configuration
            async_mode=os.getenv("SOCKETIO_ASYNC_MODE", "threading"),
            transports=transports,
            ping_timeout=int(os.getenv("SOCKETIO_PING_TIMEOUT", "60")),
            ping_interval=int(os.getenv("SOCKETIO_PING_INTERVAL", "25")),
            max_http_buffer_size=int(os.getenv("SOCKETIO_MAX_HTTP_BUFFER_SIZE", "1000000")),
            
            # Client Configuration
            reconnection=self._parse_bool("SOCKETIO_RECONNECTION", True),
            reconnection_attempts=int(os.getenv("SOCKETIO_RECONNECTION_ATTEMPTS", "5")),
            reconnection_delay=int(os.getenv("SOCKETIO_RECONNECTION_DELAY", "1000")),
            reconnection_delay_max=int(os.getenv("SOCKETIO_RECONNECTION_DELAY_MAX", "5000")),
            timeout=int(os.getenv("SOCKETIO_TIMEOUT", "20000")),
            
            # Security Configuration
            require_auth=self._parse_bool("SOCKETIO_REQUIRE_AUTH", True),
            session_validation=self._parse_bool("SOCKETIO_SESSION_VALIDATION", True),
            rate_limiting=self._parse_bool("SOCKETIO_RATE_LIMITING", True),
            csrf_protection=self._parse_bool("SOCKETIO_CSRF_PROTECTION", True),
        )
    
    def _generate_cors_origins(self) -> List[str]:
        """
        Generate dynamic CORS origins based on environment variables
        
        Returns:
            List of allowed CORS origins
        """
        origins = []
        
        # Check for explicit CORS origins configuration
        explicit_origins = os.getenv("SOCKETIO_CORS_ORIGINS")
        if explicit_origins:
            if explicit_origins == "*":
                return ["*"]
            else:
                # Parse comma-separated origins
                origins.extend([origin.strip() for origin in explicit_origins.split(",")])
                return origins
        
        # Generate origins from FLASK_HOST and FLASK_PORT
        flask_host = os.getenv("FLASK_HOST", "127.0.0.1")
        flask_port = int(os.getenv("FLASK_PORT", "5000"))
        
        # Handle localhost/127.0.0.1 variants
        hosts_to_check = [flask_host]
        if flask_host in ["localhost", "127.0.0.1"]:
            hosts_to_check = ["localhost", "127.0.0.1"]
        
        # Generate HTTP and HTTPS origins for each host
        for host in hosts_to_check:
            # HTTP origin
            origins.append(f"http://{host}:{flask_port}")
            
            # HTTPS origin (for production environments)
            if flask_port != 443:
                origins.append(f"https://{host}:{flask_port}")
            else:
                origins.append(f"https://{host}")
        
        # Add common development origins if not already included
        dev_origins = [
            "http://localhost:3000",  # Common React dev server
            "http://127.0.0.1:3000",
            "http://localhost:8080",  # Common Vue/webpack dev server
            "http://127.0.0.1:8080",
        ]
        
        for dev_origin in dev_origins:
            if dev_origin not in origins:
                origins.append(dev_origin)
        
        # Remove duplicates while preserving order
        unique_origins = []
        for origin in origins:
            if origin not in unique_origins:
                unique_origins.append(origin)
        
        self.logger.info(f"Generated CORS origins: {unique_origins}")
        return unique_origins
    
    def _parse_transports(self) -> List[str]:
        """
        Parse transport configuration from environment variables
        
        Returns:
            List of allowed transports
        """
        transports_env = os.getenv("SOCKETIO_TRANSPORTS", "websocket,polling")
        transports = [transport.strip() for transport in transports_env.split(",")]
        
        # Validate transports
        valid_transports = ["websocket", "polling"]
        validated_transports = []
        
        for transport in transports:
            if transport in valid_transports:
                validated_transports.append(transport)
            else:
                self.logger.warning(f"Invalid transport '{transport}' ignored. Valid transports: {valid_transports}")
        
        # Ensure at least one transport is available
        if not validated_transports:
            self.logger.warning("No valid transports configured, using default: ['websocket', 'polling']")
            validated_transports = ["websocket", "polling"]
        
        return validated_transports
    
    def _parse_bool(self, env_var: str, default: bool) -> bool:
        """Parse boolean environment variable with fallback"""
        value = os.getenv(env_var, str(default)).lower()
        return value in ["true", "1", "yes", "on"]
    
    def _parse_list(self, env_var: str, default: List[str]) -> List[str]:
        """Parse comma-separated list environment variable with fallback"""
        value = os.getenv(env_var)
        if value:
            return [item.strip() for item in value.split(",")]
        return default
    
    def _create_fallback_config(self) -> WebSocketConfig:
        """Create safe fallback configuration"""
        self.logger.info("Creating fallback WebSocket configuration")
        
        return WebSocketConfig(
            cors_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
            cors_credentials=True,
            cors_methods=["GET", "POST"],
            cors_headers=["Content-Type", "Authorization"],
            async_mode="threading",
            transports=["websocket", "polling"],
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=1000000,
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1000,
            reconnection_delay_max=5000,
            timeout=20000,
            require_auth=True,
            session_validation=True,
            rate_limiting=True,
            csrf_protection=True,
        )
    
    def _validate_configuration(self) -> List[str]:
        """
        Validate WebSocket configuration
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not self._websocket_config:
            errors.append("WebSocket configuration not loaded")
            return errors
        
        # Validate CORS origins
        if not self._websocket_config.cors_origins:
            errors.append("No CORS origins configured")
        else:
            for origin in self._websocket_config.cors_origins:
                if origin != "*" and not self._is_valid_origin(origin):
                    errors.append(f"Invalid CORS origin: {origin}")
        
        # Validate transports
        if not self._websocket_config.transports:
            errors.append("No transports configured")
        
        # Validate timeout values
        if self._websocket_config.ping_timeout <= 0:
            errors.append("ping_timeout must be positive")
        
        if self._websocket_config.ping_interval <= 0:
            errors.append("ping_interval must be positive")
        
        if self._websocket_config.ping_interval >= self._websocket_config.ping_timeout:
            errors.append("ping_interval should be less than ping_timeout")
        
        # Validate reconnection settings
        if self._websocket_config.reconnection_attempts < 0:
            errors.append("reconnection_attempts must be non-negative")
        
        if self._websocket_config.reconnection_delay <= 0:
            errors.append("reconnection_delay must be positive")
        
        if self._websocket_config.reconnection_delay_max < self._websocket_config.reconnection_delay:
            errors.append("reconnection_delay_max must be >= reconnection_delay")
        
        return errors
    
    def _is_valid_origin(self, origin: str) -> bool:
        """
        Validate CORS origin format
        
        Args:
            origin: Origin URL to validate
            
        Returns:
            True if origin is valid, False otherwise
        """
        try:
            parsed = urlparse(origin)
            return (
                parsed.scheme in ["http", "https"] and
                parsed.netloc and
                not parsed.path or parsed.path == "/"
            )
        except Exception:
            return False
    
    def get_cors_origins(self) -> List[str]:
        """
        Get allowed CORS origins
        
        Returns:
            List of allowed CORS origins
        """
        if not self._websocket_config:
            return ["http://127.0.0.1:5000", "http://localhost:5000"]
        
        return self._websocket_config.cors_origins
    
    def get_websocket_config(self) -> WebSocketConfig:
        """
        Get WebSocket configuration object
        
        Returns:
            WebSocket configuration object
        """
        if not self._websocket_config:
            return self._create_fallback_config()
        
        return self._websocket_config
    
    def get_socketio_config(self) -> Dict[str, Any]:
        """
        Get Flask-SocketIO configuration dictionary
        
        Returns:
            Configuration dictionary for Flask-SocketIO initialization
        """
        if not self._websocket_config:
            return self._get_fallback_socketio_config()
        
        config = {
            "cors_allowed_origins": self._websocket_config.cors_origins,
            "cors_credentials": self._websocket_config.cors_credentials,
            "async_mode": self._websocket_config.async_mode,
            "ping_timeout": self._websocket_config.ping_timeout,
            "ping_interval": self._websocket_config.ping_interval,
            "max_http_buffer_size": self._websocket_config.max_http_buffer_size,
            "allow_upgrades": self._parse_bool("SOCKETIO_ALLOW_UPGRADES", True),
            "transports": self._websocket_config.transports,
        }
        
        self.logger.debug(f"Generated SocketIO config: {config}")
        return config
    
    def get_client_config(self) -> Dict[str, Any]:
        """
        Get client-side WebSocket configuration
        
        Returns:
            Configuration dictionary for client-side WebSocket initialization
        """
        if not self._websocket_config:
            return self._get_fallback_client_config()
        
        # Determine server URL from CORS origins
        server_url = self._get_server_url()
        
        # Determine if WebSocket upgrades should be allowed
        allow_upgrades = "websocket" in self._websocket_config.transports
        
        config = {
            "url": server_url,
            "transports": self._websocket_config.transports,
            "reconnection": self._websocket_config.reconnection,
            "reconnectionAttempts": self._websocket_config.reconnection_attempts,
            "reconnectionDelay": self._websocket_config.reconnection_delay,
            "reconnectionDelayMax": self._websocket_config.reconnection_delay_max,
            "timeout": self._websocket_config.timeout,
            "forceNew": True,  # Force new connection to ensure transport settings are respected
            "upgrade": allow_upgrades,
            "rememberUpgrade": allow_upgrades,
        }
        
        self.logger.debug(f"Generated client config: {config}")
        return config
    
    def _get_server_url(self) -> str:
        """
        Determine server URL for client connections
        
        Returns:
            Server URL for WebSocket connections
        """
        if not self._websocket_config or not self._websocket_config.cors_origins:
            return "http://127.0.0.1:5000"
        
        # Use the first non-wildcard origin as the server URL
        for origin in self._websocket_config.cors_origins:
            if origin != "*":
                return origin
        
        # Fallback to localhost
        return "http://127.0.0.1:5000"
    
    def _get_fallback_socketio_config(self) -> Dict[str, Any]:
        """Get fallback SocketIO configuration"""
        return {
            "cors_allowed_origins": ["http://127.0.0.1:5000", "http://localhost:5000"],
            "cors_credentials": True,
            "async_mode": "threading",
            "ping_timeout": 60,
            "ping_interval": 25,
            "max_http_buffer_size": 1000000,
            "allow_upgrades": True,
            "transports": ["websocket", "polling"],
        }
    
    def _get_fallback_client_config(self) -> Dict[str, Any]:
        """Get fallback client configuration"""
        return {
            "url": "http://127.0.0.1:5000",
            "transports": ["websocket", "polling"],
            "reconnection": True,
            "reconnectionAttempts": 5,
            "reconnectionDelay": 1000,
            "reconnectionDelayMax": 5000,
            "timeout": 20000,
            "forceNew": False,
            "upgrade": True,
            "rememberUpgrade": True,
        }
    
    def validate_configuration(self) -> bool:
        """
        Validate current configuration
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not self._websocket_config:
            return False
        
        errors = self._validate_configuration()
        return len(errors) == 0
    
    def get_validation_errors(self) -> List[str]:
        """
        Get configuration validation errors
        
        Returns:
            List of validation error messages
        """
        return self._validation_errors.copy()
    
    def reload_configuration(self) -> None:
        """Reload configuration from environment variables"""
        self.logger.info("Reloading WebSocket configuration")
        self._load_configuration()
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary for debugging and monitoring
        
        Returns:
            Dictionary containing configuration summary
        """
        if not self._websocket_config:
            return {
                "status": "error",
                "message": "Configuration not loaded",
                "using_fallback": True
            }
        
        return {
            "status": "loaded" if not self._validation_errors else "loaded_with_warnings",
            "validation_errors": self._validation_errors,
            "cors_origins_count": len(self._websocket_config.cors_origins),
            "cors_origins": self._websocket_config.cors_origins,
            "transports": self._websocket_config.transports,
            "async_mode": self._websocket_config.async_mode,
            "security": {
                "require_auth": self._websocket_config.require_auth,
                "session_validation": self._websocket_config.session_validation,
                "rate_limiting": self._websocket_config.rate_limiting,
                "csrf_protection": self._websocket_config.csrf_protection,
            },
            "timeouts": {
                "ping_timeout": self._websocket_config.ping_timeout,
                "ping_interval": self._websocket_config.ping_interval,
                "client_timeout": self._websocket_config.timeout,
            },
            "reconnection": {
                "enabled": self._websocket_config.reconnection,
                "attempts": self._websocket_config.reconnection_attempts,
                "delay": self._websocket_config.reconnection_delay,
                "delay_max": self._websocket_config.reconnection_delay_max,
            }
        }
    
    def perform_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Perform comprehensive configuration validation using the validator
        
        Returns:
            Detailed validation report
        """
        report = self._validator.validate_configuration()
        
        return {
            "timestamp": report.timestamp.isoformat(),
            "health_score": report.health_score,
            "is_valid": report.is_valid,
            "has_warnings": report.has_warnings,
            "summary": {
                "total_fields": report.total_fields,
                "validated_fields": report.validated_fields,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "missing_required": len(report.missing_required),
                "deprecated_used": len(report.deprecated_used)
            },
            "issues": {
                "errors": [
                    {
                        "field": error.field_name,
                        "message": error.message,
                        "current_value": error.current_value,
                        "suggested_value": error.suggested_value
                    }
                    for error in report.errors
                ],
                "warnings": [
                    {
                        "field": warning.field_name,
                        "message": warning.message,
                        "current_value": warning.current_value
                    }
                    for warning in report.warnings
                ]
            }
        }
    
    def check_configuration_health(self) -> Dict[str, Any]:
        """
        Perform configuration health check
        
        Returns:
            Health check results
        """
        return self._health_checker.check_configuration_health()
    
    def start_health_monitoring(self, interval: int = 300) -> None:
        """
        Start continuous health monitoring
        
        Args:
            interval: Health check interval in seconds (default: 5 minutes)
        """
        self._health_checker.check_interval = interval
        self._health_checker.start_monitoring()
        self.logger.info(f"Started WebSocket configuration health monitoring (interval: {interval}s)")
    
    def stop_health_monitoring(self) -> None:
        """Stop continuous health monitoring"""
        self._health_checker.stop_monitoring()
        self.logger.info("Stopped WebSocket configuration health monitoring")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health monitoring summary"""
        return self._health_checker.get_health_summary()