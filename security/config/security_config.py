# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Security Configuration for User Management System

Centralizes security configuration and initialization for all security components.
"""

import os
import logging
from typing import Dict, Any, Optional
from flask import Flask
from sqlalchemy.orm import Session
from security.core.security_middleware import SecurityMiddleware
from security.core.enhanced_rate_limiter import EnhancedRateLimiter
from security.core.enhanced_csrf_protection import EnhancedCSRFProtection
from security.monitoring.security_event_logger import SecurityEventLogger
from security.error_handling.user_management_error_handler import UserManagementErrorHandler
from security.error_handling.system_recovery import HealthMonitor, health_monitor

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Centralized security configuration"""
    
    def __init__(self):
        # Rate limiting configuration
        self.rate_limiting_enabled = os.getenv('SECURITY_RATE_LIMITING_ENABLED', 'true').lower() == 'true'
        self.rate_limit_storage_type = os.getenv('RATE_LIMIT_STORAGE_TYPE', 'memory')  # memory, redis, database
        
        # CSRF protection configuration
        self.csrf_enabled = os.getenv('SECURITY_CSRF_ENABLED', 'true').lower() == 'true'
        self.csrf_time_limit = int(os.getenv('WTF_CSRF_TIME_LIMIT', '3600'))
        self.csrf_ssl_strict = os.getenv('WTF_CSRF_SSL_STRICT', 'true').lower() == 'true'
        
        # Input validation configuration
        self.input_validation_enabled = os.getenv('SECURITY_INPUT_VALIDATION_ENABLED', 'true').lower() == 'true'
        self.max_input_length = int(os.getenv('SECURITY_MAX_INPUT_LENGTH', '10000'))
        self.strict_validation = os.getenv('SECURITY_STRICT_VALIDATION', 'true').lower() == 'true'
        
        # Security monitoring configuration
        self.security_logging_enabled = os.getenv('SECURITY_LOGGING_ENABLED', 'true').lower() == 'true'
        self.security_log_file = os.getenv('SECURITY_LOG_FILE', 'logs/security_events.log')
        self.audit_trail_enabled = os.getenv('AUDIT_TRAIL_ENABLED', 'true').lower() == 'true'
        
        # Error handling configuration
        self.error_handling_enabled = os.getenv('ERROR_HANDLING_ENABLED', 'true').lower() == 'true'
        self.graceful_degradation = os.getenv('GRACEFUL_DEGRADATION_ENABLED', 'true').lower() == 'true'
        self.system_recovery_enabled = os.getenv('SYSTEM_RECOVERY_ENABLED', 'true').lower() == 'true'
        
        # Health monitoring configuration
        self.health_monitoring_enabled = os.getenv('HEALTH_MONITORING_ENABLED', 'true').lower() == 'true'
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))  # 5 minutes
        
        # Security headers configuration
        self.security_headers_enabled = os.getenv('SECURITY_HEADERS_ENABLED', 'true').lower() == 'true'
        self.hsts_enabled = os.getenv('HSTS_ENABLED', 'true').lower() == 'true'
        self.csp_enabled = os.getenv('CSP_ENABLED', 'true').lower() == 'true'
        
        # Session security configuration
        self.secure_sessions = os.getenv('SECURE_SESSIONS', 'true').lower() == 'true'
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT', '7200'))  # 2 hours
        self.session_regeneration = os.getenv('SESSION_REGENERATION', 'true').lower() == 'true'
        
        # Password security configuration
        self.password_min_length = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
        self.password_complexity_required = os.getenv('PASSWORD_COMPLEXITY_REQUIRED', 'true').lower() == 'true'
        self.password_history_check = os.getenv('PASSWORD_HISTORY_CHECK', 'false').lower() == 'true'
        
        # Account security configuration
        self.account_lockout_enabled = os.getenv('ACCOUNT_LOCKOUT_ENABLED', 'true').lower() == 'true'
        self.max_login_attempts = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
        self.lockout_duration = int(os.getenv('LOCKOUT_DURATION', '900'))  # 15 minutes
        
        # Email verification configuration
        self.email_verification_required = os.getenv('EMAIL_VERIFICATION_REQUIRED', 'true').lower() == 'true'
        self.email_verification_timeout = int(os.getenv('EMAIL_VERIFICATION_TIMEOUT', '86400'))  # 24 hours
        
        # Admin security configuration
        self.admin_2fa_required = os.getenv('ADMIN_2FA_REQUIRED', 'false').lower() == 'true'
        self.admin_session_timeout = int(os.getenv('ADMIN_SESSION_TIMEOUT', '3600'))  # 1 hour
        self.admin_ip_whitelist = os.getenv('ADMIN_IP_WHITELIST', '').split(',') if os.getenv('ADMIN_IP_WHITELIST') else []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'rate_limiting_enabled': self.rate_limiting_enabled,
            'csrf_enabled': self.csrf_enabled,
            'input_validation_enabled': self.input_validation_enabled,
            'security_logging_enabled': self.security_logging_enabled,
            'error_handling_enabled': self.error_handling_enabled,
            'health_monitoring_enabled': self.health_monitoring_enabled,
            'security_headers_enabled': self.security_headers_enabled,
            'secure_sessions': self.secure_sessions,
            'password_min_length': self.password_min_length,
            'account_lockout_enabled': self.account_lockout_enabled,
            'email_verification_required': self.email_verification_required,
        }
    
    def validate_config(self) -> bool:
        """Validate security configuration"""
        try:
            # Check required directories
            required_dirs = ['logs', 'storage']
            for dir_path in required_dirs:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                    logger.info(f"Created required directory: {dir_path}")
            
            # Validate numeric values
            if self.password_min_length < 6:
                logger.warning("Password minimum length is less than 6 characters")
                return False
            
            if self.session_timeout < 300:  # 5 minutes
                logger.warning("Session timeout is less than 5 minutes")
                return False
            
            if self.max_login_attempts < 3:
                logger.warning("Max login attempts is less than 3")
                return False
            
            logger.info("Security configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Security configuration validation failed: {e}")
            return False


class SecurityManager:
    """Manages all security components for the user management system"""
    
    def __init__(self, app: Optional[Flask] = None, db_session: Optional[Session] = None):
        self.app = app
        self.db_session = db_session
        self.config = SecurityConfig()
        
        # Security components
        self.security_middleware = None
        self.rate_limiter = None
        self.csrf_protection = None
        self.security_logger = None
        self.error_handler = None
        self.health_monitor = None
        
        if app:
            self.init_app(app, db_session)
    
    def init_app(self, app: Flask, db_session: Optional[Session] = None):
        """Initialize security manager with Flask app"""
        self.app = app
        self.db_session = db_session
        
        # Validate configuration
        if not self.config.validate_config():
            logger.error("Security configuration validation failed")
            return False
        
        try:
            # Initialize security components
            self._init_security_middleware(app)
            self._init_rate_limiter(db_session)
            self._init_csrf_protection(app, db_session)
            self._init_security_logger(db_session)
            self._init_error_handler(app, db_session)
            self._init_health_monitor()
            
            # Store security manager in app
            app.security_manager = self
            
            logger.info("Security manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize security manager: {e}")
            return False
    
    def _init_security_middleware(self, app: Flask):
        """Initialize security middleware"""
        if self.config.security_headers_enabled:
            self.security_middleware = SecurityMiddleware(app)
            logger.info("Security middleware initialized")
    
    def _init_rate_limiter(self, db_session: Optional[Session]):
        """Initialize rate limiter"""
        if self.config.rate_limiting_enabled and db_session:
            self.rate_limiter = EnhancedRateLimiter(db_session)
            logger.info("Enhanced rate limiter initialized")
    
    def _init_csrf_protection(self, app: Flask, db_session: Optional[Session]):
        """Initialize CSRF protection"""
        if self.config.csrf_enabled:
            self.csrf_protection = EnhancedCSRFProtection(app, db_session)
            
            # Configure CSRF settings
            app.config['WTF_CSRF_TIME_LIMIT'] = self.config.csrf_time_limit
            app.config['WTF_CSRF_SSL_STRICT'] = self.config.csrf_ssl_strict
            
            logger.info("Enhanced CSRF protection initialized")
    
    def _init_security_logger(self, db_session: Optional[Session]):
        """Initialize security event logger"""
        if self.config.security_logging_enabled and db_session:
            self.security_logger = SecurityEventLogger(db_session)
            logger.info("Security event logger initialized")
    
    def _init_error_handler(self, app: Flask, db_session: Optional[Session]):
        """Initialize error handler"""
        if self.config.error_handling_enabled:
            self.error_handler = UserManagementErrorHandler(app, db_session)
            logger.info("User management error handler initialized")
    
    def _init_health_monitor(self):
        """Initialize health monitor"""
        if self.config.health_monitoring_enabled:
            self.health_monitor = health_monitor
            self.health_monitor.check_interval = self.config.health_check_interval
            self.health_monitor.start_monitoring()
            logger.info("Health monitor initialized and started")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        return {
            'config': self.config.to_dict(),
            'components': {
                'security_middleware': self.security_middleware is not None,
                'rate_limiter': self.rate_limiter is not None,
                'csrf_protection': self.csrf_protection is not None,
                'security_logger': self.security_logger is not None,
                'error_handler': self.error_handler is not None,
                'health_monitor': self.health_monitor is not None and self.health_monitor.monitoring,
            },
            'timestamp': os.time.time()
        }
    
    def shutdown(self):
        """Shutdown security manager and cleanup resources"""
        try:
            if self.health_monitor and self.health_monitor.monitoring:
                self.health_monitor.stop_monitoring()
                logger.info("Health monitor stopped")
            
            logger.info("Security manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during security manager shutdown: {e}")


# Global security manager instance
security_manager = SecurityManager()


def init_security(app: Flask, db_session: Optional[Session] = None) -> bool:
    """
    Initialize security for the Flask application
    
    Args:
        app: Flask application instance
        db_session: Database session for security components
        
    Returns:
        True if initialization was successful, False otherwise
    """
    return security_manager.init_app(app, db_session)


def get_security_manager() -> SecurityManager:
    """Get the global security manager instance"""
    return security_manager