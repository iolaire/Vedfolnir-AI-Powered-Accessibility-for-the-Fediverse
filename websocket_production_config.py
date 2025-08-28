# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Production Configuration

This module provides production-grade configuration for WebSocket connections,
including SSL/TLS support, load balancer compatibility, session affinity,
and production-ready error handling and logging.
"""

import os
import ssl
import logging
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from urllib.parse import urlparse

from websocket_config_manager import WebSocketConfig, WebSocketConfigManager
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class SSLConfig:
    """SSL/TLS configuration for WebSocket connections"""
    
    # SSL Certificate Configuration
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ca_file: Optional[str] = None
    cert_chain_file: Optional[str] = None
    
    # SSL Protocol Configuration
    ssl_version: str = "TLSv1_2"  # Minimum TLS version
    ciphers: Optional[str] = None
    verify_mode: str = "CERT_NONE"  # CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED
    check_hostname: bool = False
    
    # SSL Context Options
    ssl_context: Optional[ssl.SSLContext] = None
    
    # Certificate Validation
    validate_certificates: bool = True
    allow_self_signed: bool = False
    
    # HTTPS Enforcement
    force_https: bool = True
    https_redirect: bool = True
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True


@dataclass
class LoadBalancerConfig:
    """Load balancer compatibility configuration"""
    
    # Session Affinity
    session_affinity_enabled: bool = True
    session_affinity_cookie: str = "WEBSOCKET_SERVER"
    session_affinity_timeout: int = 3600  # 1 hour
    
    # Health Check Configuration
    health_check_path: str = "/websocket/health"
    health_check_interval: int = 30
    health_check_timeout: int = 5
    health_check_retries: int = 3
    
    # Load Balancer Headers
    trust_proxy_headers: bool = True
    proxy_headers: List[str] = field(default_factory=lambda: [
        "X-Forwarded-For",
        "X-Forwarded-Proto",
        "X-Forwarded-Host",
        "X-Real-IP"
    ])
    
    # Connection Limits
    max_connections_per_server: int = 1000
    connection_timeout: int = 30
    
    # Sticky Sessions
    sticky_sessions: bool = True
    sticky_session_key: str = "websocket_server_id"


@dataclass
class ProductionLoggingConfig:
    """Production-grade logging configuration"""
    
    # Log Levels
    websocket_log_level: str = "INFO"
    security_log_level: str = "WARNING"
    performance_log_level: str = "INFO"
    error_log_level: str = "ERROR"
    
    # Log Formats
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    json_logging: bool = True
    structured_logging: bool = True
    
    # Log Files
    websocket_log_file: Optional[str] = None
    security_log_file: Optional[str] = None
    performance_log_file: Optional[str] = None
    error_log_file: Optional[str] = None
    
    # Log Rotation
    log_rotation_enabled: bool = True
    max_log_size: str = "100MB"
    backup_count: int = 10
    
    # Remote Logging
    remote_logging_enabled: bool = False
    syslog_server: Optional[str] = None
    log_aggregation_service: Optional[str] = None


@dataclass
class ProductionMonitoringConfig:
    """Production monitoring configuration"""
    
    # Metrics Collection
    metrics_enabled: bool = True
    metrics_endpoint: str = "/websocket/metrics"
    metrics_format: str = "prometheus"  # prometheus, json, custom
    
    # Performance Monitoring
    performance_monitoring: bool = True
    connection_metrics: bool = True
    message_metrics: bool = True
    error_metrics: bool = True
    
    # Health Checks
    health_checks_enabled: bool = True
    health_check_endpoint: str = "/websocket/health"
    detailed_health_info: bool = True
    
    # Alerting
    alerting_enabled: bool = False
    alert_webhook_url: Optional[str] = None
    alert_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        "connection_errors": 10,
        "message_errors": 50,
        "response_time_ms": 1000,
        "memory_usage_mb": 500
    })


@dataclass
class BackupRecoveryConfig:
    """Backup and recovery configuration for WebSocket state"""
    
    # State Backup
    state_backup_enabled: bool = True
    backup_interval: int = 300  # 5 minutes
    backup_location: str = "storage/websocket_backups"
    max_backup_files: int = 24  # Keep 24 backups (2 hours worth)
    
    # Recovery Configuration
    auto_recovery_enabled: bool = True
    recovery_timeout: int = 30
    recovery_retries: int = 3
    
    # State Persistence
    persist_connections: bool = True
    persist_subscriptions: bool = True
    persist_session_data: bool = True
    
    # Backup Compression
    compress_backups: bool = True
    compression_level: int = 6


@dataclass
class ProductionWebSocketConfig(WebSocketConfig):
    """Extended WebSocket configuration for production environments"""
    
    # SSL/TLS Configuration
    ssl_config: SSLConfig = field(default_factory=SSLConfig)
    
    # Load Balancer Configuration
    load_balancer_config: LoadBalancerConfig = field(default_factory=LoadBalancerConfig)
    
    # Production Logging
    logging_config: ProductionLoggingConfig = field(default_factory=ProductionLoggingConfig)
    
    # Monitoring Configuration
    monitoring_config: ProductionMonitoringConfig = field(default_factory=ProductionMonitoringConfig)
    
    # Backup and Recovery
    backup_config: BackupRecoveryConfig = field(default_factory=BackupRecoveryConfig)
    
    # Production-specific settings
    production_mode: bool = True
    debug_mode: bool = False
    
    # Enhanced Security
    enhanced_security: bool = True
    security_headers: bool = True
    
    # Performance Optimization
    connection_pooling: bool = True
    message_compression: bool = True
    keep_alive_enabled: bool = True


class ProductionWebSocketConfigManager(WebSocketConfigManager):
    """
    Production-grade WebSocket configuration manager
    
    Extends the base configuration manager with production-specific features
    including SSL/TLS support, load balancer compatibility, enhanced logging,
    monitoring integration, and backup/recovery capabilities.
    """
    
    def __init__(self, config: Config):
        """
        Initialize production WebSocket configuration manager
        
        Args:
            config: Application configuration instance
        """
        super().__init__(config)
        self._production_config = None
        self._ssl_context = None
        self._load_production_configuration()
    
    def _load_production_configuration(self) -> None:
        """Load production-specific configuration"""
        try:
            # Create base configuration
            base_config = super().get_websocket_config()
            
            # Create production configuration
            self._production_config = ProductionWebSocketConfig(
                # Copy base configuration
                cors_origins=base_config.cors_origins,
                cors_credentials=base_config.cors_credentials,
                cors_methods=base_config.cors_methods,
                cors_headers=base_config.cors_headers,
                async_mode=base_config.async_mode,
                transports=base_config.transports,
                ping_timeout=base_config.ping_timeout,
                ping_interval=base_config.ping_interval,
                max_http_buffer_size=base_config.max_http_buffer_size,
                reconnection=base_config.reconnection,
                reconnection_attempts=base_config.reconnection_attempts,
                reconnection_delay=base_config.reconnection_delay,
                reconnection_delay_max=base_config.reconnection_delay_max,
                timeout=base_config.timeout,
                require_auth=base_config.require_auth,
                
                # Add production-specific configuration
                ssl_config=self._create_ssl_config(),
                load_balancer_config=self._create_load_balancer_config(),
                logging_config=self._create_logging_config(),
                monitoring_config=self._create_monitoring_config(),
                backup_config=self._create_backup_config(),
                
                # Production settings
                production_mode=self._get_bool_env("WEBSOCKET_PRODUCTION_MODE", True),
                debug_mode=self._get_bool_env("WEBSOCKET_DEBUG_MODE", False),
                enhanced_security=self._get_bool_env("WEBSOCKET_ENHANCED_SECURITY", True),
                security_headers=self._get_bool_env("WEBSOCKET_SECURITY_HEADERS", True),
                connection_pooling=self._get_bool_env("WEBSOCKET_CONNECTION_POOLING", True),
                message_compression=self._get_bool_env("WEBSOCKET_MESSAGE_COMPRESSION", True),
                keep_alive_enabled=self._get_bool_env("WEBSOCKET_KEEP_ALIVE", True)
            )
            
            # Create SSL context if SSL is configured
            if self._production_config.ssl_config.cert_file:
                self._ssl_context = self._create_ssl_context()
            
            self.logger.info("Production WebSocket configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load production WebSocket configuration: {e}")
            # Fall back to base configuration
            self._production_config = None
    
    def _create_ssl_config(self) -> SSLConfig:
        """Create SSL configuration from environment variables"""
        return SSLConfig(
            cert_file=os.getenv("WEBSOCKET_SSL_CERT_FILE"),
            key_file=os.getenv("WEBSOCKET_SSL_KEY_FILE"),
            ca_file=os.getenv("WEBSOCKET_SSL_CA_FILE"),
            cert_chain_file=os.getenv("WEBSOCKET_SSL_CERT_CHAIN_FILE"),
            ssl_version=os.getenv("WEBSOCKET_SSL_VERSION", "TLSv1_2"),
            ciphers=os.getenv("WEBSOCKET_SSL_CIPHERS"),
            verify_mode=os.getenv("WEBSOCKET_SSL_VERIFY_MODE", "CERT_NONE"),
            check_hostname=self._get_bool_env("WEBSOCKET_SSL_CHECK_HOSTNAME", False),
            validate_certificates=self._get_bool_env("WEBSOCKET_SSL_VALIDATE_CERTS", True),
            allow_self_signed=self._get_bool_env("WEBSOCKET_SSL_ALLOW_SELF_SIGNED", False),
            force_https=self._get_bool_env("WEBSOCKET_FORCE_HTTPS", True),
            https_redirect=self._get_bool_env("WEBSOCKET_HTTPS_REDIRECT", True),
            hsts_enabled=self._get_bool_env("WEBSOCKET_HSTS_ENABLED", True),
            hsts_max_age=int(os.getenv("WEBSOCKET_HSTS_MAX_AGE", "31536000")),
            hsts_include_subdomains=self._get_bool_env("WEBSOCKET_HSTS_INCLUDE_SUBDOMAINS", True)
        )
    
    def _create_load_balancer_config(self) -> LoadBalancerConfig:
        """Create load balancer configuration from environment variables"""
        return LoadBalancerConfig(
            session_affinity_enabled=self._get_bool_env("WEBSOCKET_SESSION_AFFINITY", True),
            session_affinity_cookie=os.getenv("WEBSOCKET_SESSION_AFFINITY_COOKIE", "WEBSOCKET_SERVER"),
            session_affinity_timeout=int(os.getenv("WEBSOCKET_SESSION_AFFINITY_TIMEOUT", "3600")),
            health_check_path=os.getenv("WEBSOCKET_HEALTH_CHECK_PATH", "/websocket/health"),
            health_check_interval=int(os.getenv("WEBSOCKET_HEALTH_CHECK_INTERVAL", "30")),
            health_check_timeout=int(os.getenv("WEBSOCKET_HEALTH_CHECK_TIMEOUT", "5")),
            health_check_retries=int(os.getenv("WEBSOCKET_HEALTH_CHECK_RETRIES", "3")),
            trust_proxy_headers=self._get_bool_env("WEBSOCKET_TRUST_PROXY_HEADERS", True),
            proxy_headers=self._parse_list("WEBSOCKET_PROXY_HEADERS", [
                "X-Forwarded-For", "X-Forwarded-Proto", "X-Forwarded-Host", "X-Real-IP"
            ]),
            max_connections_per_server=int(os.getenv("WEBSOCKET_MAX_CONNECTIONS_PER_SERVER", "1000")),
            connection_timeout=int(os.getenv("WEBSOCKET_CONNECTION_TIMEOUT", "30")),
            sticky_sessions=self._get_bool_env("WEBSOCKET_STICKY_SESSIONS", True),
            sticky_session_key=os.getenv("WEBSOCKET_STICKY_SESSION_KEY", "websocket_server_id")
        )
    
    def _create_logging_config(self) -> ProductionLoggingConfig:
        """Create production logging configuration from environment variables"""
        return ProductionLoggingConfig(
            websocket_log_level=os.getenv("WEBSOCKET_LOG_LEVEL", "INFO"),
            security_log_level=os.getenv("WEBSOCKET_SECURITY_LOG_LEVEL", "WARNING"),
            performance_log_level=os.getenv("WEBSOCKET_PERFORMANCE_LOG_LEVEL", "INFO"),
            error_log_level=os.getenv("WEBSOCKET_ERROR_LOG_LEVEL", "ERROR"),
            log_format=os.getenv("WEBSOCKET_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            json_logging=self._get_bool_env("WEBSOCKET_JSON_LOGGING", True),
            structured_logging=self._get_bool_env("WEBSOCKET_STRUCTURED_LOGGING", True),
            websocket_log_file=os.getenv("WEBSOCKET_LOG_FILE"),
            security_log_file=os.getenv("WEBSOCKET_SECURITY_LOG_FILE"),
            performance_log_file=os.getenv("WEBSOCKET_PERFORMANCE_LOG_FILE"),
            error_log_file=os.getenv("WEBSOCKET_ERROR_LOG_FILE"),
            log_rotation_enabled=self._get_bool_env("WEBSOCKET_LOG_ROTATION", True),
            max_log_size=os.getenv("WEBSOCKET_MAX_LOG_SIZE", "100MB"),
            backup_count=int(os.getenv("WEBSOCKET_LOG_BACKUP_COUNT", "10")),
            remote_logging_enabled=self._get_bool_env("WEBSOCKET_REMOTE_LOGGING", False),
            syslog_server=os.getenv("WEBSOCKET_SYSLOG_SERVER"),
            log_aggregation_service=os.getenv("WEBSOCKET_LOG_AGGREGATION_SERVICE")
        )
    
    def _create_monitoring_config(self) -> ProductionMonitoringConfig:
        """Create monitoring configuration from environment variables"""
        alert_thresholds = {}
        try:
            thresholds_str = os.getenv("WEBSOCKET_ALERT_THRESHOLDS")
            if thresholds_str:
                alert_thresholds = json.loads(thresholds_str)
        except (json.JSONDecodeError, TypeError):
            alert_thresholds = {
                "connection_errors": 10,
                "message_errors": 50,
                "response_time_ms": 1000,
                "memory_usage_mb": 500
            }
        
        return ProductionMonitoringConfig(
            metrics_enabled=self._get_bool_env("WEBSOCKET_METRICS_ENABLED", True),
            metrics_endpoint=os.getenv("WEBSOCKET_METRICS_ENDPOINT", "/websocket/metrics"),
            metrics_format=os.getenv("WEBSOCKET_METRICS_FORMAT", "prometheus"),
            performance_monitoring=self._get_bool_env("WEBSOCKET_PERFORMANCE_MONITORING", True),
            connection_metrics=self._get_bool_env("WEBSOCKET_CONNECTION_METRICS", True),
            message_metrics=self._get_bool_env("WEBSOCKET_MESSAGE_METRICS", True),
            error_metrics=self._get_bool_env("WEBSOCKET_ERROR_METRICS", True),
            health_checks_enabled=self._get_bool_env("WEBSOCKET_HEALTH_CHECKS", True),
            health_check_endpoint=os.getenv("WEBSOCKET_HEALTH_ENDPOINT", "/websocket/health"),
            detailed_health_info=self._get_bool_env("WEBSOCKET_DETAILED_HEALTH", True),
            alerting_enabled=self._get_bool_env("WEBSOCKET_ALERTING_ENABLED", False),
            alert_webhook_url=os.getenv("WEBSOCKET_ALERT_WEBHOOK_URL"),
            alert_thresholds=alert_thresholds
        )
    
    def _create_backup_config(self) -> BackupRecoveryConfig:
        """Create backup and recovery configuration from environment variables"""
        return BackupRecoveryConfig(
            state_backup_enabled=self._get_bool_env("WEBSOCKET_STATE_BACKUP", True),
            backup_interval=int(os.getenv("WEBSOCKET_BACKUP_INTERVAL", "300")),
            backup_location=os.getenv("WEBSOCKET_BACKUP_LOCATION", "storage/websocket_backups"),
            max_backup_files=int(os.getenv("WEBSOCKET_MAX_BACKUP_FILES", "24")),
            auto_recovery_enabled=self._get_bool_env("WEBSOCKET_AUTO_RECOVERY", True),
            recovery_timeout=int(os.getenv("WEBSOCKET_RECOVERY_TIMEOUT", "30")),
            recovery_retries=int(os.getenv("WEBSOCKET_RECOVERY_RETRIES", "3")),
            persist_connections=self._get_bool_env("WEBSOCKET_PERSIST_CONNECTIONS", True),
            persist_subscriptions=self._get_bool_env("WEBSOCKET_PERSIST_SUBSCRIPTIONS", True),
            persist_session_data=self._get_bool_env("WEBSOCKET_PERSIST_SESSION_DATA", True),
            compress_backups=self._get_bool_env("WEBSOCKET_COMPRESS_BACKUPS", True),
            compression_level=int(os.getenv("WEBSOCKET_COMPRESSION_LEVEL", "6"))
        )
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context from configuration"""
        try:
            ssl_config = self._production_config.ssl_config
            
            # Create SSL context
            if ssl_config.ssl_version == "TLSv1_2":
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            elif ssl_config.ssl_version == "TLSv1_3":
                context = ssl.SSLContext(ssl.PROTOCOL_TLS)
                context.minimum_version = ssl.TLSVersion.TLSv1_3
            else:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            
            # Configure certificate files
            if ssl_config.cert_file and ssl_config.key_file:
                if not Path(ssl_config.cert_file).exists():
                    raise FileNotFoundError(f"SSL certificate file not found: {ssl_config.cert_file}")
                if not Path(ssl_config.key_file).exists():
                    raise FileNotFoundError(f"SSL key file not found: {ssl_config.key_file}")
                
                context.load_cert_chain(ssl_config.cert_file, ssl_config.key_file)
                self.logger.info(f"Loaded SSL certificate: {ssl_config.cert_file}")
            
            # Configure CA file
            if ssl_config.ca_file:
                if Path(ssl_config.ca_file).exists():
                    context.load_verify_locations(ssl_config.ca_file)
                    self.logger.info(f"Loaded SSL CA file: {ssl_config.ca_file}")
                else:
                    self.logger.warning(f"SSL CA file not found: {ssl_config.ca_file}")
            
            # Configure verification mode
            if ssl_config.verify_mode == "CERT_REQUIRED":
                context.verify_mode = ssl.CERT_REQUIRED
            elif ssl_config.verify_mode == "CERT_OPTIONAL":
                context.verify_mode = ssl.CERT_OPTIONAL
            else:
                context.verify_mode = ssl.CERT_NONE
            
            # Configure hostname checking
            context.check_hostname = ssl_config.check_hostname
            
            # Configure ciphers
            if ssl_config.ciphers:
                context.set_ciphers(ssl_config.ciphers)
            
            # Security options
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            context.options |= ssl.OP_SINGLE_DH_USE
            context.options |= ssl.OP_SINGLE_ECDH_USE
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            return None
    
    def get_production_config(self) -> Optional[ProductionWebSocketConfig]:
        """
        Get production WebSocket configuration
        
        Returns:
            Production WebSocket configuration or None if not available
        """
        return self._production_config
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        Get SSL context for secure WebSocket connections
        
        Returns:
            SSL context or None if SSL is not configured
        """
        return self._ssl_context
    
    def is_production_mode(self) -> bool:
        """
        Check if running in production mode
        
        Returns:
            True if production mode is enabled
        """
        return self._production_config and self._production_config.production_mode
    
    def is_ssl_enabled(self) -> bool:
        """
        Check if SSL/TLS is enabled
        
        Returns:
            True if SSL is configured and enabled
        """
        return (self._production_config and 
                self._production_config.ssl_config.cert_file and 
                self._ssl_context is not None)
    
    def get_socketio_production_config(self) -> Dict[str, Any]:
        """
        Get SocketIO configuration optimized for production
        
        Returns:
            Dictionary of SocketIO configuration parameters
        """
        if not self._production_config:
            return super().get_socketio_config()
        
        config = super().get_socketio_config()
        
        # Add production-specific settings
        if self._ssl_context:
            config['ssl_context'] = self._ssl_context
        
        # Enhanced settings for production
        config.update({
            'logger': self._production_config.debug_mode,
            'engineio_logger': self._production_config.debug_mode,
            'manage_session': False,  # We handle sessions ourselves
            'monitor_clients': self._production_config.monitoring_config.connection_metrics,
            'compression_threshold': 1024 if self._production_config.message_compression else 0,
        })
        
        return config
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _parse_list(self, key: str, default: List[str]) -> List[str]:
        """Parse comma-separated list from environment variable"""
        value = os.getenv(key)
        if not value:
            return default
        return [item.strip() for item in value.split(',') if item.strip()]