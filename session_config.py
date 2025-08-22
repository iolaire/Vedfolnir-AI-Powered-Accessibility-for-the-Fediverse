# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Management Configuration System

Provides comprehensive configuration management for session timeouts, cleanup intervals,
feature flags, and environment-specific settings for the session management system.
"""

import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from dotenv import load_dotenv

class SessionEnvironment(Enum):
    """Session management environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class SessionTimeoutConfig:
    """Configuration for session timeout behavior"""
    # Basic timeout settings
    session_lifetime: timedelta = field(default_factory=lambda: timedelta(hours=48))
    idle_timeout: timedelta = field(default_factory=lambda: timedelta(hours=24))
    absolute_timeout: timedelta = field(default_factory=lambda: timedelta(days=7))
    
    # Grace periods
    expiration_grace_period: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    cleanup_grace_period: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    
    # Warning thresholds
    expiration_warning_threshold: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    
    @classmethod
    def from_env(cls):
        """Create SessionTimeoutConfig from environment variables"""
        return cls(
            session_lifetime=timedelta(seconds=int(os.getenv("SESSION_LIFETIME_SECONDS", str(48 * 3600)))),
            idle_timeout=timedelta(seconds=int(os.getenv("SESSION_IDLE_TIMEOUT_SECONDS", str(24 * 3600)))),
            absolute_timeout=timedelta(seconds=int(os.getenv("SESSION_ABSOLUTE_TIMEOUT_SECONDS", str(7 * 24 * 3600)))),
            expiration_grace_period=timedelta(seconds=int(os.getenv("SESSION_EXPIRATION_GRACE_SECONDS", "300"))),
            cleanup_grace_period=timedelta(seconds=int(os.getenv("SESSION_CLEANUP_GRACE_SECONDS", "600"))),
            expiration_warning_threshold=timedelta(seconds=int(os.getenv("SESSION_WARNING_THRESHOLD_SECONDS", "900")))
        )

@dataclass
class SessionCleanupConfig:
    """Configuration for session cleanup behavior"""
    # Cleanup intervals
    cleanup_interval: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    batch_cleanup_interval: timedelta = field(default_factory=lambda: timedelta(hours=6))
    deep_cleanup_interval: timedelta = field(default_factory=lambda: timedelta(days=1))
    
    # Cleanup batch sizes
    cleanup_batch_size: int = 100
    max_cleanup_batches_per_run: int = 10
    
    # Cleanup thresholds
    max_expired_sessions_threshold: int = 1000
    cleanup_trigger_threshold: int = 500
    
    # Retention settings
    expired_session_retention_days: int = 7
    audit_log_retention_days: int = 30
    
    @classmethod
    def from_env(cls):
        """Create SessionCleanupConfig from environment variables"""
        return cls(
            cleanup_interval=timedelta(seconds=int(os.getenv("SESSION_CLEANUP_INTERVAL_SECONDS", str(30 * 60)))),
            batch_cleanup_interval=timedelta(seconds=int(os.getenv("SESSION_BATCH_CLEANUP_INTERVAL_SECONDS", str(6 * 3600)))),
            deep_cleanup_interval=timedelta(seconds=int(os.getenv("SESSION_DEEP_CLEANUP_INTERVAL_SECONDS", str(24 * 3600)))),
            cleanup_batch_size=int(os.getenv("SESSION_CLEANUP_BATCH_SIZE", "100")),
            max_cleanup_batches_per_run=int(os.getenv("SESSION_MAX_CLEANUP_BATCHES", "10")),
            max_expired_sessions_threshold=int(os.getenv("SESSION_MAX_EXPIRED_THRESHOLD", "1000")),
            cleanup_trigger_threshold=int(os.getenv("SESSION_CLEANUP_TRIGGER_THRESHOLD", "500")),
            expired_session_retention_days=int(os.getenv("SESSION_EXPIRED_RETENTION_DAYS", "7")),
            audit_log_retention_days=int(os.getenv("SESSION_AUDIT_RETENTION_DAYS", "30"))
        )

@dataclass
class SessionSyncConfig:
    """Configuration for cross-tab session synchronization"""
    # Synchronization intervals
    sync_check_interval: timedelta = field(default_factory=lambda: timedelta(seconds=2))
    heartbeat_interval: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    
    # Synchronization timeouts
    sync_timeout: timedelta = field(default_factory=lambda: timedelta(seconds=5))
    tab_response_timeout: timedelta = field(default_factory=lambda: timedelta(seconds=3))
    
    # Storage settings
    localStorage_key_prefix: str = "vedfolnir_session_"
    max_sync_data_size: int = 1024  # bytes
    
    @classmethod
    def from_env(cls):
        """Create SessionSyncConfig from environment variables"""
        return cls(
            sync_check_interval=timedelta(seconds=int(os.getenv("SESSION_SYNC_CHECK_INTERVAL_SECONDS", "2"))),
            heartbeat_interval=timedelta(seconds=int(os.getenv("SESSION_HEARTBEAT_INTERVAL_SECONDS", "30"))),
            sync_timeout=timedelta(seconds=int(os.getenv("SESSION_SYNC_TIMEOUT_SECONDS", "5"))),
            tab_response_timeout=timedelta(seconds=int(os.getenv("SESSION_TAB_RESPONSE_TIMEOUT_SECONDS", "3"))),
            localStorage_key_prefix=os.getenv("SESSION_LOCALSTORAGE_PREFIX", "vedfolnir_session_"),
            max_sync_data_size=int(os.getenv("SESSION_MAX_SYNC_DATA_SIZE", "1024"))
        )

@dataclass
class SessionSecurityConfig:
    """Configuration for session security features"""
    # Security validation
    enable_fingerprinting: bool = True
    enable_suspicious_activity_detection: bool = True
    enable_audit_logging: bool = True
    
    # Security thresholds
    max_concurrent_sessions_per_user: int = 5
    suspicious_activity_threshold: int = 10
    max_platform_switches_per_hour: int = 50
    
    # Security timeouts
    security_check_interval: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    
    @classmethod
    def from_env(cls):
        """Create SessionSecurityConfig from environment variables"""
        return cls(
            enable_fingerprinting=os.getenv("SESSION_ENABLE_FINGERPRINTING", "true").lower() == "true",
            enable_suspicious_activity_detection=os.getenv("SESSION_ENABLE_SUSPICIOUS_DETECTION", "true").lower() == "true",
            enable_audit_logging=os.getenv("SESSION_ENABLE_AUDIT_LOGGING", "true").lower() == "true",
            max_concurrent_sessions_per_user=int(os.getenv("SESSION_MAX_CONCURRENT_PER_USER", "5")),
            suspicious_activity_threshold=int(os.getenv("SESSION_SUSPICIOUS_ACTIVITY_THRESHOLD", "10")),
            max_platform_switches_per_hour=int(os.getenv("SESSION_MAX_PLATFORM_SWITCHES_PER_HOUR", "50")),
            security_check_interval=timedelta(seconds=int(os.getenv("SESSION_SECURITY_CHECK_INTERVAL_SECONDS", str(5 * 60))))
        )

@dataclass
class SessionMonitoringConfig:
    """Configuration for session monitoring and metrics"""
    # Monitoring features
    enable_performance_monitoring: bool = True
    enable_metrics_collection: bool = True
    enable_health_checks: bool = True
    enable_alerting: bool = True
    enable_console_alerts: bool = False
    
    # Monitoring intervals
    metrics_collection_interval: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    health_check_interval: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    
    # Buffer sizes
    metrics_buffer_size: int = 1000
    events_buffer_size: int = 500
    
    # Alert thresholds
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'session_creation_rate': 100.0,
        'session_failure_rate': 10.0,
        'avg_session_duration': 3600.0,
        'concurrent_sessions': 1000.0,
        'suspicious_activity_rate': 5.0
    })
    
    @classmethod
    def from_env(cls):
        """Create SessionMonitoringConfig from environment variables"""
        # Parse alert thresholds from environment
        alert_thresholds = {}
        threshold_prefix = "SESSION_ALERT_THRESHOLD_"
        for key, value in os.environ.items():
            if key.startswith(threshold_prefix):
                threshold_name = key[len(threshold_prefix):].lower()
                try:
                    alert_thresholds[threshold_name] = float(value)
                except ValueError:
                    pass
        
        # Use defaults if no custom thresholds provided
        if not alert_thresholds:
            alert_thresholds = {
                'session_creation_rate': float(os.getenv("SESSION_ALERT_CREATION_RATE", "100.0")),
                'session_failure_rate': float(os.getenv("SESSION_ALERT_FAILURE_RATE", "10.0")),
                'avg_session_duration': float(os.getenv("SESSION_ALERT_AVG_DURATION", "3600.0")),
                'concurrent_sessions': float(os.getenv("SESSION_ALERT_CONCURRENT_SESSIONS", "1000.0")),
                'suspicious_activity_rate': float(os.getenv("SESSION_ALERT_SUSPICIOUS_RATE", "5.0"))
            }
        
        return cls(
            enable_performance_monitoring=os.getenv("SESSION_ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true",
            enable_metrics_collection=os.getenv("SESSION_ENABLE_METRICS_COLLECTION", "true").lower() == "true",
            enable_health_checks=os.getenv("SESSION_ENABLE_HEALTH_CHECKS", "true").lower() == "true",
            enable_alerting=os.getenv("SESSION_ENABLE_ALERTING", "true").lower() == "true",
            enable_console_alerts=os.getenv("SESSION_ENABLE_CONSOLE_ALERTS", "false").lower() == "true",
            metrics_collection_interval=timedelta(seconds=int(os.getenv("SESSION_METRICS_INTERVAL_SECONDS", "60"))),
            health_check_interval=timedelta(seconds=int(os.getenv("SESSION_HEALTH_CHECK_INTERVAL_SECONDS", "300"))),
            metrics_buffer_size=int(os.getenv("SESSION_METRICS_BUFFER_SIZE", "1000")),
            events_buffer_size=int(os.getenv("SESSION_EVENTS_BUFFER_SIZE", "500")),
            alert_thresholds=alert_thresholds
        )

@dataclass
class SessionFeatureFlags:
    """Feature flags for session management components"""
    # Core features
    enable_cross_tab_sync: bool = True
    enable_platform_switching: bool = True
    enable_session_persistence: bool = True
    
    # Advanced features
    enable_optimistic_ui_updates: bool = True
    enable_background_cleanup: bool = True
    enable_session_analytics: bool = True
    
    # Experimental features
    enable_session_clustering: bool = False
    enable_distributed_sessions: bool = False
    enable_session_caching: bool = False
    
    @classmethod
    def from_env(cls):
        """Create SessionFeatureFlags from environment variables"""
        return cls(
            enable_cross_tab_sync=os.getenv("SESSION_FEATURE_CROSS_TAB_SYNC", "true").lower() == "true",
            enable_platform_switching=os.getenv("SESSION_FEATURE_PLATFORM_SWITCHING", "true").lower() == "true",
            enable_session_persistence=os.getenv("SESSION_FEATURE_PERSISTENCE", "true").lower() == "true",
            enable_optimistic_ui_updates=os.getenv("SESSION_FEATURE_OPTIMISTIC_UI", "true").lower() == "true",
            enable_background_cleanup=os.getenv("SESSION_FEATURE_BACKGROUND_CLEANUP", "true").lower() == "true",
            enable_session_analytics=os.getenv("SESSION_FEATURE_ANALYTICS", "true").lower() == "true",
            enable_session_clustering=os.getenv("SESSION_FEATURE_CLUSTERING", "false").lower() == "true",
            enable_distributed_sessions=os.getenv("SESSION_FEATURE_DISTRIBUTED", "false").lower() == "true",
            enable_session_caching=os.getenv("SESSION_FEATURE_CACHING", "false").lower() == "true"
        )

@dataclass
class SessionConfig:
    """Comprehensive session management configuration"""
    # Environment settings
    environment: SessionEnvironment = SessionEnvironment.DEVELOPMENT
    debug_mode: bool = False
    
    # Component configurations
    timeout: SessionTimeoutConfig = field(default_factory=SessionTimeoutConfig)
    cleanup: SessionCleanupConfig = field(default_factory=SessionCleanupConfig)
    sync: SessionSyncConfig = field(default_factory=SessionSyncConfig)
    security: SessionSecurityConfig = field(default_factory=SessionSecurityConfig)
    monitoring: SessionMonitoringConfig = field(default_factory=SessionMonitoringConfig)
    features: SessionFeatureFlags = field(default_factory=SessionFeatureFlags)
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls):
        """Create SessionConfig from environment variables"""
        # Determine environment
        env_name = os.getenv("SESSION_ENVIRONMENT", "development").lower()
        try:
            environment = SessionEnvironment(env_name)
        except ValueError:
            environment = SessionEnvironment.DEVELOPMENT
        
        # Parse custom settings
        custom_settings = {}
        custom_prefix = "SESSION_CUSTOM_"
        for key, value in os.environ.items():
            if key.startswith(custom_prefix):
                setting_name = key[len(custom_prefix):].lower()
                custom_settings[setting_name] = value
        
        return cls(
            environment=environment,
            debug_mode=os.getenv("SESSION_DEBUG_MODE", "false").lower() == "true",
            timeout=SessionTimeoutConfig.from_env(),
            cleanup=SessionCleanupConfig.from_env(),
            sync=SessionSyncConfig.from_env(),
            security=SessionSecurityConfig.from_env(),
            monitoring=SessionMonitoringConfig.from_env(),
            features=SessionFeatureFlags.from_env(),
            custom_settings=custom_settings
        )
    
    def get_environment_specific_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration overrides"""
        env_configs = {
            SessionEnvironment.DEVELOPMENT: {
                'timeout.session_lifetime': timedelta(hours=24),
                'cleanup.cleanup_interval': timedelta(minutes=15),
                'monitoring.enable_performance_monitoring': True,
                'features.enable_session_analytics': True,
                'debug_mode': True
            },
            SessionEnvironment.TESTING: {
                'timeout.session_lifetime': timedelta(minutes=30),
                'cleanup.cleanup_interval': timedelta(minutes=5),
                'monitoring.enable_performance_monitoring': False,
                'features.enable_session_analytics': False,
                'debug_mode': True
            },
            SessionEnvironment.STAGING: {
                'timeout.session_lifetime': timedelta(hours=48),
                'cleanup.cleanup_interval': timedelta(minutes=30),
                'monitoring.enable_performance_monitoring': True,
                'features.enable_session_analytics': True,
                'debug_mode': False
            },
            SessionEnvironment.PRODUCTION: {
                'timeout.session_lifetime': timedelta(hours=48),
                'cleanup.cleanup_interval': timedelta(hours=1),
                'monitoring.enable_performance_monitoring': True,
                'features.enable_session_analytics': True,
                'debug_mode': False
            }
        }
        
        return env_configs.get(self.environment, {})
    
    def apply_environment_overrides(self):
        """Apply environment-specific configuration overrides"""
        overrides = self.get_environment_specific_config()
        
        for key, value in overrides.items():
            if '.' in key:
                # Handle nested configuration
                parts = key.split('.')
                obj = self
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
            else:
                # Handle top-level configuration
                setattr(self, key, value)
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate timeout settings
        if self.timeout.idle_timeout > self.timeout.session_lifetime:
            issues.append("Idle timeout should be less than session lifetime")
        
        if self.timeout.expiration_grace_period >= self.timeout.idle_timeout:
            issues.append("Expiration grace period should be less than idle timeout")
        
        # Validate cleanup settings
        if self.cleanup.cleanup_batch_size <= 0:
            issues.append("Cleanup batch size must be positive")
        
        if self.cleanup.cleanup_interval >= self.cleanup.batch_cleanup_interval:
            issues.append("Cleanup interval should be less than batch cleanup interval")
        
        # Validate sync settings
        if self.sync.sync_timeout >= self.sync.heartbeat_interval:
            issues.append("Sync timeout should be less than heartbeat interval")
        
        # Validate security settings
        if self.security.max_concurrent_sessions_per_user <= 0:
            issues.append("Max concurrent sessions per user must be positive")
        
        # Validate monitoring settings
        if self.monitoring.metrics_buffer_size <= 0:
            issues.append("Metrics buffer size must be positive")
        
        return issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        return {
            'environment': self.environment.value,
            'debug_mode': self.debug_mode,
            'session_lifetime_hours': self.timeout.session_lifetime.total_seconds() / 3600,
            'cleanup_interval_minutes': self.cleanup.cleanup_interval.total_seconds() / 60,
            'features_enabled': {
                'cross_tab_sync': self.features.enable_cross_tab_sync,
                'platform_switching': self.features.enable_platform_switching,
                'monitoring': self.monitoring.enable_performance_monitoring,
                'security': self.security.enable_fingerprinting
            },
            'custom_settings_count': len(self.custom_settings)
        }

# Global session configuration instance
_session_config = None

def get_session_config() -> SessionConfig:
    """Get or create global session configuration instance"""
    global _session_config
    if _session_config is None:
        _session_config = SessionConfig.from_env()
        _session_config.apply_environment_overrides()
        
        # Validate configuration
        issues = _session_config.validate_configuration()
        if issues:
            from logging import getLogger
            logger = getLogger(__name__)
            logger.warning(f"Session configuration issues detected: {issues}")
    
    return _session_config

def reload_session_config():
    """Reload session configuration from environment"""
    global _session_config
    _session_config = None
    return get_session_config()