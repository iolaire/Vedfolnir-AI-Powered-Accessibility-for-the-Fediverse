# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Compliance Framework Integration

Integrates the compliance and audit framework with the main application,
providing middleware and decorators for automatic compliance logging.
"""

import functools
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
from flask import request, session, g

from app.services.compliance.compliance_service import ComplianceService

class ComplianceIntegration:
    """
    Compliance Framework Integration
    
    Provides integration between the main application and the compliance framework,
    including automatic audit logging and GDPR compliance features.
    """
    
    def __init__(self, app=None, db_manager=None):
        self.app = app
        self.db_manager = db_manager
        self.compliance_service: Optional[ComplianceService] = None
        self.logger = logging.getLogger(__name__)
        
        if app is not None:
            self.init_app(app, db_manager)
    
    def init_app(self, app, db_manager):
        """Initialize compliance integration with Flask app"""
        self.app = app
        self.db_manager = db_manager
        
        # Initialize compliance service
        try:
            self.compliance_service = ComplianceService(db_manager)
            self.logger.info("Compliance service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize compliance service: {e}")
            self.compliance_service = None
        
        # Register middleware
        self._register_middleware()
        
        # Register CLI commands
        self._register_cli_commands()
    
    def _register_middleware(self):
        """Register Flask middleware for automatic audit logging"""
        if not self.app or not self.compliance_service:
            return
        
        @self.app.before_request
        def before_request():
            """Log request start and setup compliance context"""
            g.compliance_start_time = datetime.now(timezone.utc)
            g.compliance_request_id = request.headers.get('X-Request-ID', 'unknown')
        
        @self.app.after_request
        def after_request(response):
            """Log request completion and audit events"""
            if not self.compliance_service:
                return response
            
            try:
                # Get user information
                user_id = session.get('user_id')
                username = session.get('username')
                
                # Log data access for API endpoints
                if request.endpoint and request.endpoint.startswith('api.'):
                    self.compliance_service.log_data_access(
                        user_id=user_id,
                        username=username,
                        resource=request.endpoint,
                        action=request.method,
                        success=response.status_code < 400,
                        details={
                            'status_code': response.status_code,
                            'ip_address': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent'),
                            'request_id': g.get('compliance_request_id')
                        }
                    )
                
                # Log security events for failed requests
                if response.status_code in [401, 403, 429]:
                    severity = "HIGH" if response.status_code in [401, 403] else "MEDIUM"
                    self.compliance_service.log_security_event(
                        description=f"HTTP {response.status_code} response",
                        severity=severity,
                        user_id=user_id,
                        username=username,
                        ip_address=request.remote_addr,
                        details={
                            'endpoint': request.endpoint,
                            'method': request.method,
                            'status_code': response.status_code,
                            'user_agent': request.headers.get('User-Agent')
                        }
                    )
                
            except Exception as e:
                self.logger.error(f"Error in compliance after_request middleware: {e}")
            
            return response
    
    def _register_cli_commands(self):
        """Register CLI commands for compliance management"""
        if not self.app:
            return
        
        @self.app.cli.command('compliance-status')
        def compliance_status():
            """Show compliance framework status"""
            if not self.compliance_service:
                print("Compliance service not available")
                return
            
            status = self.compliance_service.get_compliance_status()
            print("Compliance Framework Status:")
            print(f"  Timestamp: {status['timestamp']}")
            print("  Components:")
            for component, enabled in status['components'].items():
                status_text = "✓ Enabled" if enabled else "✗ Disabled"
                print(f"    {component}: {status_text}")
            print("  Configuration:")
            for config, enabled in status['configuration'].items():
                status_text = "✓ Enabled" if enabled else "✗ Disabled"
                print(f"    {config}: {status_text}")
        
        @self.app.cli.command('generate-compliance-report')
        @self.app.cli.option('--type', default='comprehensive', help='Report type (gdpr, audit, comprehensive)')
        @self.app.cli.option('--format', default='html', help='Report format (html, json, csv)')
        def generate_compliance_report(type, format):
            """Generate compliance report"""
            if not self.compliance_service:
                print("Compliance service not available")
                return
            
            print(f"Generating {type} compliance report in {format} format...")
            
            try:
                if type == 'gdpr':
                    report = self.compliance_service.generate_gdpr_compliance_report(format=format)
                elif type == 'audit':
                    report = self.compliance_service.generate_audit_summary_report(format=format)
                elif type == 'comprehensive':
                    report = self.compliance_service.generate_comprehensive_report(format=format)
                else:
                    print(f"Unknown report type: {type}")
                    return
                
                if report:
                    print(f"Report generated successfully: {report.file_path}")
                else:
                    print("Failed to generate report")
            except Exception as e:
                print(f"Error generating report: {e}")
        
        @self.app.cli.command('execute-lifecycle-policies')
        def execute_lifecycle_policies():
            """Execute data lifecycle policies"""
            if not self.compliance_service:
                print("Compliance service not available")
                return
            
            print("Executing data lifecycle policies...")
            
            try:
                events = self.compliance_service.execute_data_lifecycle_policies()
                print(f"Executed {len(events)} lifecycle policies:")
                for event in events:
                    status = "✓" if event.success else "✗"
                    print(f"  {status} {event.category.value}: {event.affected_records} records")
            except Exception as e:
                print(f"Error executing lifecycle policies: {e}")
        
        @self.app.cli.command('verify-audit-integrity')
        def verify_audit_integrity():
            """Verify audit log integrity"""
            if not self.compliance_service:
                print("Compliance service not available")
                return
            
            print("Verifying audit log integrity...")
            
            try:
                result = self.compliance_service.verify_audit_integrity()
                if result['verified']:
                    print("✓ Audit log integrity verified")
                    print(f"  Total events: {result.get('total_events', 'Unknown')}")
                else:
                    print("✗ Audit log integrity verification failed")
                    if 'error' in result:
                        print(f"  Error: {result['error']}")
            except Exception as e:
                print(f"Error verifying audit integrity: {e}")

# Decorators for compliance logging
def audit_data_access(resource: str, action: str = None):
    """Decorator to automatically log data access events"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get compliance service from app context
            compliance_service = getattr(g, 'compliance_service', None)
            if not compliance_service:
                return func(*args, **kwargs)
            
            # Get user information
            user_id = session.get('user_id')
            username = session.get('username')
            
            # Determine action if not provided
            actual_action = action or getattr(func, '__name__', 'unknown')
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log successful data access
                compliance_service.log_data_access(
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    action=actual_action,
                    success=True,
                    details={
                        'function': func.__name__,
                        'ip_address': request.remote_addr if request else None,
                        'user_agent': request.headers.get('User-Agent') if request else None
                    }
                )
                
                return result
                
            except Exception as e:
                # Log failed data access
                compliance_service.log_data_access(
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    action=actual_action,
                    success=False,
                    details={
                        'function': func.__name__,
                        'error': str(e),
                        'ip_address': request.remote_addr if request else None,
                        'user_agent': request.headers.get('User-Agent') if request else None
                    }
                )
                raise
        
        return wrapper
    return decorator

def audit_data_modification(resource: str, action: str = None):
    """Decorator to automatically log data modification events"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get compliance service from app context
            compliance_service = getattr(g, 'compliance_service', None)
            if not compliance_service:
                return func(*args, **kwargs)
            
            # Get user information
            user_id = session.get('user_id')
            username = session.get('username')
            
            # Determine action if not provided
            actual_action = action or getattr(func, '__name__', 'unknown')
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log successful data modification
                compliance_service.log_data_modification(
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    action=actual_action,
                    success=True,
                    details={
                        'function': func.__name__,
                        'ip_address': request.remote_addr if request else None,
                        'user_agent': request.headers.get('User-Agent') if request else None
                    }
                )
                
                return result
                
            except Exception as e:
                # Log failed data modification
                compliance_service.log_data_modification(
                    user_id=user_id,
                    username=username,
                    resource=resource,
                    action=actual_action,
                    success=False,
                    details={
                        'function': func.__name__,
                        'error': str(e),
                        'ip_address': request.remote_addr if request else None,
                        'user_agent': request.headers.get('User-Agent') if request else None
                    }
                )
                raise
        
        return wrapper
    return decorator

def audit_security_event(description: str, severity: str = "MEDIUM"):
    """Decorator to automatically log security events"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get compliance service from app context
            compliance_service = getattr(g, 'compliance_service', None)
            if not compliance_service:
                return func(*args, **kwargs)
            
            # Get user information
            user_id = session.get('user_id')
            username = session.get('username')
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log security event (assuming success means event occurred)
                compliance_service.log_security_event(
                    description=description,
                    severity=severity,
                    user_id=user_id,
                    username=username,
                    ip_address=request.remote_addr if request else None,
                    details={
                        'function': func.__name__,
                        'user_agent': request.headers.get('User-Agent') if request else None
                    }
                )
                
                return result
                
            except Exception as e:
                # Log security event with error details
                compliance_service.log_security_event(
                    description=f"{description} (Failed)",
                    severity="HIGH",  # Escalate severity on failure
                    user_id=user_id,
                    username=username,
                    ip_address=request.remote_addr if request else None,
                    details={
                        'function': func.__name__,
                        'error': str(e),
                        'user_agent': request.headers.get('User-Agent') if request else None
                    }
                )
                raise
        
        return wrapper
    return decorator

# Global compliance integration instance
compliance_integration = ComplianceIntegration()