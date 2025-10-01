# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Compliance Service Integration

Main service that coordinates all compliance and audit framework components:
- Audit logging
- GDPR compliance
- Data lifecycle management
- Compliance reporting
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .audit_logger import AuditLogger, AuditEventType
from .gdpr_compliance import GDPRComplianceService, GDPRRequestType
from .compliance_reporter import ComplianceReporter, ReportType, ReportFormat
from .data_lifecycle_manager import DataLifecycleManager

class ComplianceService:
    """
    Main Compliance Service
    
    Coordinates all compliance and audit framework components and provides
    a unified interface for compliance operations.
    """
    
    def __init__(self, db_manager, config_path: str = None):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.audit_logger = None
        self.gdpr_service = None
        self.reporter = None
        self.lifecycle_manager = None
        
        self._initialize_components()
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load compliance configuration"""
        if not config_path:
            config_path = "/app/config/compliance/audit_config.yml"
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Loaded compliance configuration from {config_path}")
            return config
        except Exception as e:
            self.logger.warning(f"Failed to load compliance config from {config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default compliance configuration"""
        return {
            'audit_logging': {
                'enabled': True,
                'log_level': 'INFO',
                'destinations': [
                    {
                        'type': 'file',
                        'path': '/app/logs/audit/audit.log'
                    }
                ],
                'events': [],
                'async_logging': True
            },
            'gdpr_compliance': {
                'enabled': True,
                'export_path': '/app/storage/gdpr_exports'
            },
            'data_lifecycle': {
                'enabled': True,
                'auto_execution': True
            },
            'compliance_reporting': {
                'enabled': True,
                'reports_path': '/app/storage/compliance_reports'
            }
        }
    
    def _initialize_components(self):
        """Initialize all compliance components"""
        try:
            # Initialize audit logger
            audit_config = self.config.get('audit_logging', {})
            if audit_config.get('enabled', True):
                self.audit_logger = AuditLogger(audit_config)
                self.logger.info("Audit logger initialized")
            
            # Initialize GDPR compliance service
            gdpr_config = self.config.get('gdpr_compliance', {})
            if gdpr_config.get('enabled', True) and self.audit_logger:
                self.gdpr_service = GDPRComplianceService(
                    self.db_manager, 
                    self.audit_logger, 
                    gdpr_config
                )
                self.logger.info("GDPR compliance service initialized")
            
            # Initialize compliance reporter
            reporting_config = self.config.get('compliance_reporting', {})
            if reporting_config.get('enabled', True) and self.audit_logger:
                self.reporter = ComplianceReporter(
                    self.db_manager,
                    self.audit_logger,
                    reporting_config
                )
                self.logger.info("Compliance reporter initialized")
            
            # Initialize data lifecycle manager
            lifecycle_config = self.config.get('data_lifecycle', {})
            if lifecycle_config.get('enabled', True) and self.audit_logger:
                self.lifecycle_manager = DataLifecycleManager(
                    self.db_manager,
                    self.audit_logger,
                    lifecycle_config
                )
                self.logger.info("Data lifecycle manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize compliance components: {e}")
            raise
    
    # Audit Logging Methods
    def log_user_authentication(self, username: str, success: bool, 
                              ip_address: str = None, details: Dict = None):
        """Log user authentication event"""
        if self.audit_logger:
            outcome = "SUCCESS" if success else "FAILURE"
            self.audit_logger.log_user_authentication(
                username=username,
                outcome=outcome,
                ip_address=ip_address,
                details=details
            )
    
    def log_data_access(self, user_id: int, username: str, resource: str,
                       action: str, success: bool = True, details: Dict = None):
        """Log data access event"""
        if self.audit_logger:
            outcome = "SUCCESS" if success else "FAILURE"
            self.audit_logger.log_data_access(
                user_id=user_id,
                username=username,
                resource=resource,
                action=action,
                outcome=outcome,
                details=details
            )
    
    def log_data_modification(self, user_id: int, username: str, resource: str,
                            action: str, success: bool = True, details: Dict = None):
        """Log data modification event"""
        if self.audit_logger:
            outcome = "SUCCESS" if success else "FAILURE"
            self.audit_logger.log_data_modification(
                user_id=user_id,
                username=username,
                resource=resource,
                action=action,
                outcome=outcome,
                details=details
            )
    
    def log_security_event(self, description: str, severity: str = "HIGH",
                          user_id: int = None, username: str = None,
                          ip_address: str = None, details: Dict = None):
        """Log security event"""
        if self.audit_logger:
            self.audit_logger.log_security_event(
                event_description=description,
                severity=severity,
                user_id=user_id,
                username=username,
                ip_address=ip_address,
                details=details
            )
    
    def log_container_event(self, container_id: str, service_name: str,
                           action: str, success: bool = True, details: Dict = None):
        """Log container-related event"""
        if self.audit_logger:
            outcome = "SUCCESS" if success else "FAILURE"
            self.audit_logger.log_container_event(
                container_id=container_id,
                service_name=service_name,
                action=action,
                outcome=outcome,
                details=details
            )
    
    # GDPR Compliance Methods
    def create_gdpr_data_export_request(self, user_id: int, details: Dict = None) -> Optional[str]:
        """Create GDPR data export request"""
        if self.gdpr_service:
            return self.gdpr_service.create_gdpr_request(
                user_id=user_id,
                request_type=GDPRRequestType.DATA_EXPORT,
                details=details
            )
        return None
    
    def create_gdpr_data_deletion_request(self, user_id: int, details: Dict = None) -> Optional[str]:
        """Create GDPR data deletion request"""
        if self.gdpr_service:
            return self.gdpr_service.create_gdpr_request(
                user_id=user_id,
                request_type=GDPRRequestType.DATA_DELETION,
                details=details
            )
        return None
    
    def process_gdpr_request(self, request_id: str) -> tuple[bool, Optional[str]]:
        """Process a GDPR request"""
        if not self.gdpr_service:
            return False, "GDPR service not available"
        
        # Get request details
        request = self.gdpr_service._get_request(request_id)
        if not request:
            return False, "Request not found"
        
        # Process based on request type
        if request.request_type == GDPRRequestType.DATA_EXPORT:
            return self.gdpr_service.process_data_export_request(request_id)
        elif request.request_type == GDPRRequestType.DATA_DELETION:
            return self.gdpr_service.process_data_deletion_request(request_id)
        elif request.request_type == GDPRRequestType.DATA_ANONYMIZATION:
            return self.gdpr_service.process_data_anonymization_request(request_id)
        else:
            return False, f"Unsupported request type: {request.request_type}"
    
    def get_gdpr_requests(self, user_id: int = None):
        """Get GDPR requests"""
        if self.gdpr_service:
            return self.gdpr_service.get_gdpr_requests(user_id=user_id)
        return []
    
    # Compliance Reporting Methods
    def generate_gdpr_compliance_report(self, start_date: datetime = None,
                                      end_date: datetime = None,
                                      format: str = "html"):
        """Generate GDPR compliance report"""
        if self.reporter:
            report_format = ReportFormat(format.lower())
            return self.reporter.generate_gdpr_compliance_report(
                start_date=start_date,
                end_date=end_date,
                format=report_format
            )
        return None
    
    def generate_audit_summary_report(self, start_date: datetime = None,
                                    end_date: datetime = None,
                                    format: str = "html"):
        """Generate audit summary report"""
        if self.reporter:
            report_format = ReportFormat(format.lower())
            return self.reporter.generate_audit_summary_report(
                start_date=start_date,
                end_date=end_date,
                format=report_format
            )
        return None
    
    def generate_comprehensive_report(self, start_date: datetime = None,
                                    end_date: datetime = None,
                                    format: str = "html"):
        """Generate comprehensive compliance report"""
        if self.reporter:
            report_format = ReportFormat(format.lower())
            return self.reporter.generate_comprehensive_report(
                start_date=start_date,
                end_date=end_date,
                format=report_format
            )
        return None
    
    # Data Lifecycle Management Methods
    def execute_data_lifecycle_policies(self):
        """Execute all data lifecycle policies"""
        if self.lifecycle_manager:
            return self.lifecycle_manager.execute_lifecycle_policies()
        return []
    
    def get_retention_status(self):
        """Get data retention policy status"""
        if self.lifecycle_manager:
            return self.lifecycle_manager.get_retention_status()
        return {}
    
    # Health and Status Methods
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get overall compliance framework status"""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'audit_logger': self.audit_logger is not None,
                'gdpr_service': self.gdpr_service is not None,
                'reporter': self.reporter is not None,
                'lifecycle_manager': self.lifecycle_manager is not None
            },
            'configuration': {
                'audit_logging_enabled': self.config.get('audit_logging', {}).get('enabled', False),
                'gdpr_compliance_enabled': self.config.get('gdpr_compliance', {}).get('enabled', False),
                'reporting_enabled': self.config.get('compliance_reporting', {}).get('enabled', False),
                'lifecycle_management_enabled': self.config.get('data_lifecycle', {}).get('enabled', False)
            }
        }
        
        # Add component-specific status
        if self.gdpr_service:
            status['gdpr_requests'] = {
                'pending': len(self.gdpr_service.get_gdpr_requests()),
                'total': len(self.gdpr_service.get_gdpr_requests())
            }
        
        if self.lifecycle_manager:
            status['data_lifecycle'] = self.lifecycle_manager.get_retention_status()
        
        return status
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """Verify audit log integrity"""
        if self.audit_logger:
            return self.audit_logger.verify_audit_chain()
        return {'verified': False, 'error': 'Audit logger not available'}
    
    def shutdown(self):
        """Shutdown compliance service gracefully"""
        if self.audit_logger:
            self.audit_logger.shutdown()
        
        self.logger.info("Compliance service shutdown complete")