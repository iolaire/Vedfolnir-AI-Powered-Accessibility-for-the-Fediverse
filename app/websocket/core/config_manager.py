# Copyright (C) 2025 iolaire mcfadden.
# Consolidated WebSocket Configuration Management

import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from urllib.parse import urlparse
from enum import Enum
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

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

@dataclass
class ValidationResult:
    """Configuration validation result"""
    field_name: str
    level: ConfigValidationLevel
    message: str
    current_value: Any = None
    suggested_value: Any = None
    is_valid: bool = True

@dataclass
class ConfigSchemaField:
    """Configuration schema field definition"""
    name: str
    data_type: ConfigDataType
    default_value: Any
    description: str
    required: bool = False
    validation_rules: List[Callable] = field(default_factory=list)
    env_var: Optional[str] = None

@dataclass
class WebSocketConfig:
    """Consolidated WebSocket configuration schema"""
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
    
    # Performance Configuration
    max_connections: int = 1000
    connection_timeout: int = 30
    heartbeat_interval: int = 30
    
    # Logging Configuration
    log_level: str = "INFO"
    enable_debug: bool = False

class ConsolidatedWebSocketConfigManager:
    """Consolidated WebSocket configuration management with validation and health checking"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._websocket_config = None
        self._schema_fields = self._build_schema()
        self._validation_results = []
    
    def _build_schema(self) -> Dict[str, ConfigSchemaField]:
        """Build configuration schema with validation rules"""
        return {
            'cors_origins': ConfigSchemaField(
                name='cors_origins',
                data_type=ConfigDataType.LIST,
                default_value=['http://localhost:5000'],
                description='Allowed CORS origins for WebSocket connections',
                env_var='WEBSOCKET_CORS_ORIGINS',
                validation_rules=[self._validate_cors_origins]
            ),
            'ping_timeout': ConfigSchemaField(
                name='ping_timeout',
                data_type=ConfigDataType.INTEGER,
                default_value=60,
                description='WebSocket ping timeout in seconds',
                env_var='WEBSOCKET_PING_TIMEOUT',
                validation_rules=[self._validate_positive_integer]
            ),
            'ping_interval': ConfigSchemaField(
                name='ping_interval',
                data_type=ConfigDataType.INTEGER,
                default_value=25,
                description='WebSocket ping interval in seconds',
                env_var='WEBSOCKET_PING_INTERVAL',
                validation_rules=[self._validate_positive_integer]
            ),
            'max_connections': ConfigSchemaField(
                name='max_connections',
                data_type=ConfigDataType.INTEGER,
                default_value=1000,
                description='Maximum concurrent WebSocket connections',
                env_var='WEBSOCKET_MAX_CONNECTIONS',
                validation_rules=[self._validate_positive_integer]
            ),
            'require_auth': ConfigSchemaField(
                name='require_auth',
                data_type=ConfigDataType.BOOLEAN,
                default_value=True,
                description='Require authentication for WebSocket connections',
                env_var='WEBSOCKET_REQUIRE_AUTH',
                validation_rules=[self._validate_boolean]
            )
        }
    
    def get_websocket_config(self) -> WebSocketConfig:
        """Get validated WebSocket configuration"""
        if self._websocket_config is None:
            self._websocket_config = self._build_config()
        return self._websocket_config
    
    def _build_config(self) -> WebSocketConfig:
        """Build WebSocket configuration from environment and defaults"""
        config_data = {}
        
        # Process each schema field
        for field_name, schema_field in self._schema_fields.items():
            value = self._get_config_value(schema_field)
            config_data[field_name] = value
        
        # Add additional configuration from environment
        config_data.update({
            'cors_credentials': self._get_bool_env('WEBSOCKET_CORS_CREDENTIALS', True),
            'cors_methods': self._get_list_env('WEBSOCKET_CORS_METHODS', ['GET', 'POST']),
            'cors_headers': self._get_list_env('WEBSOCKET_CORS_HEADERS', ['Content-Type', 'Authorization']),
            'async_mode': os.getenv('WEBSOCKET_ASYNC_MODE', 'threading'),
            'transports': self._get_list_env('WEBSOCKET_TRANSPORTS', ['websocket', 'polling']),
            'max_http_buffer_size': int(os.getenv('WEBSOCKET_MAX_HTTP_BUFFER_SIZE', '1000000')),
            'reconnection': self._get_bool_env('WEBSOCKET_RECONNECTION', True),
            'reconnection_attempts': int(os.getenv('WEBSOCKET_RECONNECTION_ATTEMPTS', '5')),
            'reconnection_delay': int(os.getenv('WEBSOCKET_RECONNECTION_DELAY', '1000')),
            'reconnection_delay_max': int(os.getenv('WEBSOCKET_RECONNECTION_DELAY_MAX', '5000')),
            'timeout': int(os.getenv('WEBSOCKET_TIMEOUT', '20000')),
            'connection_timeout': int(os.getenv('WEBSOCKET_CONNECTION_TIMEOUT', '30')),
            'heartbeat_interval': int(os.getenv('WEBSOCKET_HEARTBEAT_INTERVAL', '30')),
            'log_level': os.getenv('WEBSOCKET_LOG_LEVEL', 'INFO'),
            'enable_debug': self._get_bool_env('WEBSOCKET_ENABLE_DEBUG', False)
        })
        
        return WebSocketConfig(**config_data)
    
    def _get_config_value(self, schema_field: ConfigSchemaField) -> Any:
        """Get configuration value with validation"""
        # Get value from environment or use default
        if schema_field.env_var:
            env_value = os.getenv(schema_field.env_var)
            if env_value is not None:
                value = self._convert_value(env_value, schema_field.data_type)
            else:
                value = schema_field.default_value
        else:
            value = schema_field.default_value
        
        # Validate the value
        for validation_rule in schema_field.validation_rules:
            result = validation_rule(schema_field.name, value)
            if result:
                self._validation_results.append(result)
                if result.level == ConfigValidationLevel.ERROR:
                    value = schema_field.default_value
        
        return value
    
    def _convert_value(self, value: str, data_type: ConfigDataType) -> Any:
        """Convert string value to appropriate type"""
        if data_type == ConfigDataType.INTEGER:
            return int(value)
        elif data_type == ConfigDataType.BOOLEAN:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif data_type == ConfigDataType.LIST:
            return [item.strip() for item in value.split(',') if item.strip()]
        else:
            return value
    
    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _get_list_env(self, key: str, default: List[str]) -> List[str]:
        """Get list environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        return [item.strip() for item in value.split(',') if item.strip()]
    
    # Validation Rules
    def _validate_cors_origins(self, field_name: str, value: List[str]) -> Optional[ValidationResult]:
        """Validate CORS origins"""
        if not isinstance(value, list):
            return ValidationResult(
                field_name=field_name,
                level=ConfigValidationLevel.ERROR,
                message="CORS origins must be a list",
                current_value=value,
                is_valid=False
            )
        
        for origin in value:
            if not self._is_valid_url(origin) and origin != '*':
                return ValidationResult(
                    field_name=field_name,
                    level=ConfigValidationLevel.WARNING,
                    message=f"Invalid CORS origin format: {origin}",
                    current_value=value,
                    is_valid=True
                )
        
        return None
    
    def _validate_positive_integer(self, field_name: str, value: int) -> Optional[ValidationResult]:
        """Validate positive integer"""
        if not isinstance(value, int) or value <= 0:
            return ValidationResult(
                field_name=field_name,
                level=ConfigValidationLevel.ERROR,
                message=f"{field_name} must be a positive integer",
                current_value=value,
                is_valid=False
            )
        return None
    
    def _validate_boolean(self, field_name: str, value: bool) -> Optional[ValidationResult]:
        """Validate boolean value"""
        if not isinstance(value, bool):
            return ValidationResult(
                field_name=field_name,
                level=ConfigValidationLevel.ERROR,
                message=f"{field_name} must be a boolean",
                current_value=value,
                is_valid=False
            )
        return None
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def validate_configuration(self) -> List[ValidationResult]:
        """Validate current configuration and return results"""
        self._validation_results = []
        config = self.get_websocket_config()
        
        # Run validation on current config
        for field_name, schema_field in self._schema_fields.items():
            value = getattr(config, field_name, None)
            for validation_rule in schema_field.validation_rules:
                result = validation_rule(field_name, value)
                if result:
                    self._validation_results.append(result)
        
        return self._validation_results
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get configuration health status"""
        validation_results = self.validate_configuration()
        
        errors = [r for r in validation_results if r.level == ConfigValidationLevel.ERROR]
        warnings = [r for r in validation_results if r.level == ConfigValidationLevel.WARNING]
        
        return {
            'status': 'healthy' if not errors else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'errors': len(errors),
            'warnings': len(warnings),
            'error_details': [{'field': r.field_name, 'message': r.message} for r in errors],
            'warning_details': [{'field': r.field_name, 'message': r.message} for r in warnings],
            'configuration_loaded': self._websocket_config is not None
        }
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        config = self.get_websocket_config()
        return {
            'cors_origins': config.cors_origins,
            'ping_timeout': config.ping_timeout,
            'ping_interval': config.ping_interval,
            'max_connections': config.max_connections,
            'require_auth': config.require_auth,
            'async_mode': config.async_mode,
            'transports': config.transports,
            'log_level': config.log_level,
            'enable_debug': config.enable_debug
        }
        self._validate_config(self._websocket_config)
        return self._websocket_config
    
    def _build_config(self) -> WebSocketConfig:
        """Build configuration from environment and defaults"""
        return WebSocketConfig(
            cors_origins=self._get_cors_origins(),
            async_mode=os.getenv('WEBSOCKET_ASYNC_MODE', 'threading'),
            transports=os.getenv('WEBSOCKET_TRANSPORTS', 'websocket,polling').split(','),
            ping_timeout=int(os.getenv('WEBSOCKET_PING_TIMEOUT', '60')),
            ping_interval=int(os.getenv('WEBSOCKET_PING_INTERVAL', '25')),
            require_auth=os.getenv('WEBSOCKET_REQUIRE_AUTH', 'true').lower() == 'true'
        )
    
    def _get_cors_origins(self) -> List[str]:
        """Generate CORS origins dynamically"""
        # For development, allow all origins
        return ["*"]
        
        # Production code (commented out for development):
        # origins = []
        # 
        # # Add configured origins
        # env_origins = os.getenv('WEBSOCKET_CORS_ORIGINS', '')
        # if env_origins:
        #     origins.extend(env_origins.split(','))
        # 
        # # Add default local origins
        # host = self.config.webapp.host
        # port = self.config.webapp.port
        # origins.extend([
        #     f"http://{host}:{port}",
        #     f"https://{host}:{port}",
        #     "http://localhost:5000",
        #     "https://localhost:5000",
        #     "http://127.0.0.1:5000",
        #     "https://127.0.0.1:5000"
        # ])
        # 
        # return list(set(origins))  # Remove duplicates
    
    def _validate_config(self, config: WebSocketConfig) -> bool:
        """Validate WebSocket configuration"""
        try:
            # Validate transports
            valid_transports = ['websocket', 'polling']
            for transport in config.transports:
                if transport not in valid_transports:
                    raise ValueError(f"Invalid transport: {transport}")
            
            # Validate timeouts
            if config.ping_timeout <= 0 or config.ping_interval <= 0:
                raise ValueError("Ping timeout and interval must be positive")
            
            # Validate CORS origins
            for origin in config.cors_origins:
                try:
                    parsed = urlparse(origin)
                    if not parsed.scheme or not parsed.netloc:
                        raise ValueError(f"Invalid CORS origin: {origin}")
                except Exception:
                    raise ValueError(f"Invalid CORS origin format: {origin}")
            
            self.logger.info("WebSocket configuration validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket configuration validation failed: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on WebSocket configuration"""
        try:
            config = self.get_websocket_config()
            
            return {
                'status': 'healthy',
                'cors_origins_count': len(config.cors_origins),
                'transports': config.transports,
                'auth_required': config.require_auth,
                'ping_timeout': config.ping_timeout
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def get_client_config(self) -> Dict[str, Any]:
        """
        Get client-side WebSocket configuration
        
        Returns:
            Dictionary containing client configuration
        """
        try:
            config = self.get_websocket_config()
            
            return {
                'websocket_url': f"ws://localhost:5000",
                'transports': config.transports,
                'ping_timeout': config.ping_timeout,
                'ping_interval': config.ping_interval,
                'cors_origins': config.cors_origins,
                'namespaces': {
                    'user': '/',
                    'admin': '/admin'
                },
                'reconnection': True,
                'reconnection_attempts': 5,
                'reconnection_delay': 1000
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get client config: {e}")
            return {
                'websocket_url': f"ws://localhost:5000",
                'transports': ['websocket', 'polling'],
                'namespaces': {'user': '/', 'admin': '/admin'}
            }
