# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Configuration Schema and Validation System

This module provides comprehensive environment variable schema definitions,
validation rules, and configuration documentation for WebSocket settings.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Callable
from enum import Enum


class ConfigValidationLevel(Enum):
    """Configuration validation levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ConfigDataType(Enum):
    """Configuration data types"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    LIST = "list"
    URL = "url"
    HOST = "host"
    PORT = "port"


@dataclass
class ConfigValidationRule:
    """Configuration validation rule"""
    name: str
    validator: Callable[[Any], bool]
    message: str
    level: ConfigValidationLevel = ConfigValidationLevel.ERROR


@dataclass
class ConfigSchemaField:
    """Configuration schema field definition"""
    name: str
    data_type: ConfigDataType
    default_value: Any
    description: str
    required: bool = False
    validation_rules: List[ConfigValidationRule] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    deprecated: bool = False
    migration_note: Optional[str] = None
    category: str = "general"


class WebSocketConfigSchema:
    """
    Comprehensive WebSocket configuration schema
    
    Defines all environment variables, their types, validation rules,
    and documentation for WebSocket configuration.
    """
    
    def __init__(self):
        """Initialize configuration schema"""
        self._schema_fields = self._define_schema_fields()
        self._validation_rules = self._define_validation_rules()
    
    def _define_schema_fields(self) -> Dict[str, ConfigSchemaField]:
        """Define all configuration schema fields"""
        return {
            # CORS Configuration
            "SOCKETIO_CORS_ORIGINS": ConfigSchemaField(
                name="SOCKETIO_CORS_ORIGINS",
                data_type=ConfigDataType.LIST,
                default_value=None,
                description="Comma-separated list of allowed CORS origins. Use '*' for all origins (not recommended for production).",
                required=False,
                examples=[
                    "http://localhost:3000,https://example.com",
                    "http://127.0.0.1:5000,http://localhost:5000",
                    "*"
                ],
                category="cors"
            ),
            
            "SOCKETIO_CORS_CREDENTIALS": ConfigSchemaField(
                name="SOCKETIO_CORS_CREDENTIALS",
                data_type=ConfigDataType.BOOLEAN,
                default_value=True,
                description="Whether to allow credentials in CORS requests",
                required=False,
                examples=["true", "false"],
                category="cors"
            ),
            
            "SOCKETIO_CORS_METHODS": ConfigSchemaField(
                name="SOCKETIO_CORS_METHODS",
                data_type=ConfigDataType.LIST,
                default_value=["GET", "POST"],
                description="Comma-separated list of allowed HTTP methods for CORS",
                required=False,
                examples=["GET,POST", "GET,POST,PUT,DELETE"],
                category="cors"
            ),
            
            "SOCKETIO_CORS_HEADERS": ConfigSchemaField(
                name="SOCKETIO_CORS_HEADERS",
                data_type=ConfigDataType.LIST,
                default_value=["Content-Type", "Authorization"],
                description="Comma-separated list of allowed headers for CORS",
                required=False,
                examples=["Content-Type,Authorization", "Content-Type,Authorization,X-Custom-Header"],
                category="cors"
            ),
            
            # Server Configuration
            "FLASK_HOST": ConfigSchemaField(
                name="FLASK_HOST",
                data_type=ConfigDataType.HOST,
                default_value="127.0.0.1",
                description="Host address for the Flask application",
                required=False,
                examples=["127.0.0.1", "localhost", "0.0.0.0", "example.com"],
                category="server"
            ),
            
            "FLASK_PORT": ConfigSchemaField(
                name="FLASK_PORT",
                data_type=ConfigDataType.PORT,
                default_value=5000,
                description="Port number for the Flask application",
                required=False,
                examples=["5000", "8080", "3000"],
                category="server"
            ),
            
            # SocketIO Configuration
            "SOCKETIO_ASYNC_MODE": ConfigSchemaField(
                name="SOCKETIO_ASYNC_MODE",
                data_type=ConfigDataType.STRING,
                default_value="threading",
                description="Async mode for SocketIO server",
                required=False,
                examples=["threading", "eventlet", "gevent"],
                category="socketio"
            ),
            
            "SOCKETIO_TRANSPORTS": ConfigSchemaField(
                name="SOCKETIO_TRANSPORTS",
                data_type=ConfigDataType.LIST,
                default_value=["websocket", "polling"],
                description="Comma-separated list of allowed transport methods",
                required=False,
                examples=["websocket,polling", "websocket", "polling"],
                category="socketio"
            ),
            
            "SOCKETIO_PING_TIMEOUT": ConfigSchemaField(
                name="SOCKETIO_PING_TIMEOUT",
                data_type=ConfigDataType.INTEGER,
                default_value=60,
                description="Ping timeout in seconds",
                required=False,
                examples=["60", "120", "30"],
                category="socketio"
            ),
            
            "SOCKETIO_PING_INTERVAL": ConfigSchemaField(
                name="SOCKETIO_PING_INTERVAL",
                data_type=ConfigDataType.INTEGER,
                default_value=25,
                description="Ping interval in seconds",
                required=False,
                examples=["25", "30", "15"],
                category="socketio"
            ),
            
            "SOCKETIO_MAX_HTTP_BUFFER_SIZE": ConfigSchemaField(
                name="SOCKETIO_MAX_HTTP_BUFFER_SIZE",
                data_type=ConfigDataType.INTEGER,
                default_value=1000000,
                description="Maximum HTTP buffer size in bytes",
                required=False,
                examples=["1000000", "2000000", "500000"],
                category="socketio"
            ),
            
            # Client Configuration
            "SOCKETIO_RECONNECTION": ConfigSchemaField(
                name="SOCKETIO_RECONNECTION",
                data_type=ConfigDataType.BOOLEAN,
                default_value=True,
                description="Whether to enable automatic reconnection on the client",
                required=False,
                examples=["true", "false"],
                category="client"
            ),
            
            "SOCKETIO_RECONNECTION_ATTEMPTS": ConfigSchemaField(
                name="SOCKETIO_RECONNECTION_ATTEMPTS",
                data_type=ConfigDataType.INTEGER,
                default_value=5,
                description="Maximum number of reconnection attempts",
                required=False,
                examples=["5", "10", "3"],
                category="client"
            ),
            
            "SOCKETIO_RECONNECTION_DELAY": ConfigSchemaField(
                name="SOCKETIO_RECONNECTION_DELAY",
                data_type=ConfigDataType.INTEGER,
                default_value=1000,
                description="Initial reconnection delay in milliseconds",
                required=False,
                examples=["1000", "2000", "500"],
                category="client"
            ),
            
            "SOCKETIO_RECONNECTION_DELAY_MAX": ConfigSchemaField(
                name="SOCKETIO_RECONNECTION_DELAY_MAX",
                data_type=ConfigDataType.INTEGER,
                default_value=5000,
                description="Maximum reconnection delay in milliseconds",
                required=False,
                examples=["5000", "10000", "3000"],
                category="client"
            ),
            
            "SOCKETIO_TIMEOUT": ConfigSchemaField(
                name="SOCKETIO_TIMEOUT",
                data_type=ConfigDataType.INTEGER,
                default_value=20000,
                description="Connection timeout in milliseconds",
                required=False,
                examples=["20000", "30000", "10000"],
                category="client"
            ),
            
            # Security Configuration
            "SOCKETIO_REQUIRE_AUTH": ConfigSchemaField(
                name="SOCKETIO_REQUIRE_AUTH",
                data_type=ConfigDataType.BOOLEAN,
                default_value=True,
                description="Whether to require authentication for WebSocket connections",
                required=False,
                examples=["true", "false"],
                category="security"
            ),
            
            "SOCKETIO_SESSION_VALIDATION": ConfigSchemaField(
                name="SOCKETIO_SESSION_VALIDATION",
                data_type=ConfigDataType.BOOLEAN,
                default_value=True,
                description="Whether to validate user sessions for WebSocket connections",
                required=False,
                examples=["true", "false"],
                category="security"
            ),
            
            "SOCKETIO_RATE_LIMITING": ConfigSchemaField(
                name="SOCKETIO_RATE_LIMITING",
                data_type=ConfigDataType.BOOLEAN,
                default_value=True,
                description="Whether to enable rate limiting for WebSocket connections",
                required=False,
                examples=["true", "false"],
                category="security"
            ),
            
            "SOCKETIO_CSRF_PROTECTION": ConfigSchemaField(
                name="SOCKETIO_CSRF_PROTECTION",
                data_type=ConfigDataType.BOOLEAN,
                default_value=True,
                description="Whether to enable CSRF protection for WebSocket events",
                required=False,
                examples=["true", "false"],
                category="security"
            ),
            
            # Performance Configuration
            "SOCKETIO_MAX_CONNECTIONS": ConfigSchemaField(
                name="SOCKETIO_MAX_CONNECTIONS",
                data_type=ConfigDataType.INTEGER,
                default_value=1000,
                description="Maximum number of concurrent WebSocket connections",
                required=False,
                examples=["1000", "5000", "100"],
                category="performance"
            ),
            
            "SOCKETIO_CONNECTION_POOL_SIZE": ConfigSchemaField(
                name="SOCKETIO_CONNECTION_POOL_SIZE",
                data_type=ConfigDataType.INTEGER,
                default_value=10,
                description="Size of the connection pool for WebSocket connections",
                required=False,
                examples=["10", "20", "5"],
                category="performance"
            ),
            
            # Logging Configuration
            "SOCKETIO_LOG_LEVEL": ConfigSchemaField(
                name="SOCKETIO_LOG_LEVEL",
                data_type=ConfigDataType.STRING,
                default_value="INFO",
                description="Log level for WebSocket operations",
                required=False,
                examples=["DEBUG", "INFO", "WARNING", "ERROR"],
                category="logging"
            ),
            
            "SOCKETIO_LOG_CONNECTIONS": ConfigSchemaField(
                name="SOCKETIO_LOG_CONNECTIONS",
                data_type=ConfigDataType.BOOLEAN,
                default_value=False,
                description="Whether to log WebSocket connection events",
                required=False,
                examples=["true", "false"],
                category="logging"
            ),
            
            # Development Configuration
            "SOCKETIO_DEBUG": ConfigSchemaField(
                name="SOCKETIO_DEBUG",
                data_type=ConfigDataType.BOOLEAN,
                default_value=False,
                description="Enable debug mode for WebSocket operations",
                required=False,
                examples=["true", "false"],
                category="development"
            ),
            
            "SOCKETIO_ENGINEIO_LOGGER": ConfigSchemaField(
                name="SOCKETIO_ENGINEIO_LOGGER",
                data_type=ConfigDataType.BOOLEAN,
                default_value=False,
                description="Enable Engine.IO logger for detailed debugging",
                required=False,
                examples=["true", "false"],
                category="development"
            ),
        }
    
    def _define_validation_rules(self) -> Dict[str, List[ConfigValidationRule]]:
        """Define validation rules for configuration fields"""
        return {
            "SOCKETIO_CORS_ORIGINS": [
                ConfigValidationRule(
                    name="valid_origins",
                    validator=self._validate_cors_origins,
                    message="CORS origins must be valid URLs or '*'",
                    level=ConfigValidationLevel.ERROR
                ),
                ConfigValidationRule(
                    name="production_wildcard",
                    validator=self._validate_production_wildcard,
                    message="Using '*' for CORS origins is not recommended in production",
                    level=ConfigValidationLevel.WARNING
                )
            ],
            
            "FLASK_HOST": [
                ConfigValidationRule(
                    name="valid_host",
                    validator=self._validate_host,
                    message="Host must be a valid hostname or IP address",
                    level=ConfigValidationLevel.ERROR
                )
            ],
            
            "FLASK_PORT": [
                ConfigValidationRule(
                    name="valid_port",
                    validator=self._validate_port,
                    message="Port must be between 1 and 65535",
                    level=ConfigValidationLevel.ERROR
                )
            ],
            
            "SOCKETIO_TRANSPORTS": [
                ConfigValidationRule(
                    name="valid_transports",
                    validator=self._validate_transports,
                    message="Transports must be 'websocket' and/or 'polling'",
                    level=ConfigValidationLevel.ERROR
                )
            ],
            
            "SOCKETIO_PING_TIMEOUT": [
                ConfigValidationRule(
                    name="positive_timeout",
                    validator=lambda x: x > 0,
                    message="Ping timeout must be positive",
                    level=ConfigValidationLevel.ERROR
                )
            ],
            
            "SOCKETIO_PING_INTERVAL": [
                ConfigValidationRule(
                    name="positive_interval",
                    validator=lambda x: x > 0,
                    message="Ping interval must be positive",
                    level=ConfigValidationLevel.ERROR
                )
            ],
            
            "SOCKETIO_RECONNECTION_ATTEMPTS": [
                ConfigValidationRule(
                    name="non_negative_attempts",
                    validator=lambda x: x >= 0,
                    message="Reconnection attempts must be non-negative",
                    level=ConfigValidationLevel.ERROR
                )
            ],
            
            "SOCKETIO_LOG_LEVEL": [
                ConfigValidationRule(
                    name="valid_log_level",
                    validator=self._validate_log_level,
                    message="Log level must be DEBUG, INFO, WARNING, or ERROR",
                    level=ConfigValidationLevel.ERROR
                )
            ]
        }
    
    def _validate_cors_origins(self, value: str) -> bool:
        """Validate CORS origins format"""
        if not value:
            return True  # Optional field
        
        if value == "*":
            return True
        
        origins = [origin.strip() for origin in value.split(",")]
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        for origin in origins:
            if not url_pattern.match(origin):
                return False
        
        return True
    
    def _validate_production_wildcard(self, value: str) -> bool:
        """Check for wildcard CORS in production"""
        if not value:
            return True
        
        # This is a warning, not an error
        # In production, we should warn about using '*'
        env = os.getenv("FLASK_ENV", "production").lower()
        if env == "production" and value.strip() == "*":
            return False
        
        return True
    
    def _validate_host(self, value: str) -> bool:
        """Validate host format"""
        if not value:
            return False
        
        # Check for valid hostname or IP address
        hostname_pattern = re.compile(
            r'^(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$'
        )
        
        return bool(hostname_pattern.match(value))
    
    def _validate_port(self, value: int) -> bool:
        """Validate port number"""
        return 1 <= value <= 65535
    
    def _validate_transports(self, value: str) -> bool:
        """Validate transport methods"""
        if not value:
            return False
        
        valid_transports = {"websocket", "polling"}
        transports = {transport.strip() for transport in value.split(",")}
        
        return transports.issubset(valid_transports) and len(transports) > 0
    
    def _validate_log_level(self, value: str) -> bool:
        """Validate log level"""
        if not value:
            return False
        
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        return value.upper() in valid_levels
    
    def get_schema_fields(self) -> Dict[str, ConfigSchemaField]:
        """Get all schema fields"""
        return self._schema_fields.copy()
    
    def get_field_by_name(self, name: str) -> Optional[ConfigSchemaField]:
        """Get schema field by name"""
        return self._schema_fields.get(name)
    
    def get_fields_by_category(self, category: str) -> Dict[str, ConfigSchemaField]:
        """Get schema fields by category"""
        return {
            name: field for name, field in self._schema_fields.items()
            if field.category == category
        }
    
    def get_categories(self) -> List[str]:
        """Get all configuration categories"""
        categories = set()
        for field in self._schema_fields.values():
            categories.add(field.category)
        return sorted(list(categories))
    
    def get_validation_rules(self, field_name: str) -> List[ConfigValidationRule]:
        """Get validation rules for a field"""
        return self._validation_rules.get(field_name, [])
    
    def get_required_fields(self) -> Dict[str, ConfigSchemaField]:
        """Get all required fields"""
        return {
            name: field for name, field in self._schema_fields.items()
            if field.required
        }
    
    def get_deprecated_fields(self) -> Dict[str, ConfigSchemaField]:
        """Get all deprecated fields"""
        return {
            name: field for name, field in self._schema_fields.items()
            if field.deprecated
        }