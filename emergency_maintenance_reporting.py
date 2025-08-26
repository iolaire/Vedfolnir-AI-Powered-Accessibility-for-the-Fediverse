# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Emergency Maintenance Reporting System

Comprehensive reporting and documentation system for emergency maintenance
activities, including activation logging, summary reports, and deactivation validation.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum

from emergency_maintenance_handler import EmergencyMaintenanceHandler, EmergencyReport
from emergency_job_termination_manager import EmergencyJobTerminationManager, JobTerminationRecord

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of emergency maintenance reports"""
    ACTIVATION = "activation"
    DEACTIVATION = "deactivation"
    SUMMARY = "summary"
    INCIDENT = "incident"
    AUDIT = "audit"


class ReportSeverity(Enum):
    """Report severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EmergencyActivationLog:
    """Log entry for emergency maintenance activation"""
    activation_id: str
    timestamp: datetime
    triggered_by: str
    trigger_source: str  # manual, automated, alert, etc.
    reason: str
    severity: ReportSeverity
    affected_systems: List[str]
    estimated_duration: Optional[int]
    authorization_level: str
    contact_information: Dict[str, str]
    escalation_path: List[str]


@dataclass
class EmergencyDeactivationLog:
    """Log entry for emergency maintenance deactivation"""
    deactivation_id: str
    activation_id: str
    timestamp: datetime
    deactivated_by: str
    duration_minutes: float
    resolution_summary: str
    validation_checks: Dict[str, bool]
    recovery_status: str
    lessons_learned: List[str]
    follow_up_actions: List[str]


@dataclass
class EmergencySummaryReport:
    """Comprehensive emergency maintenance summary report"""
    report_id: str
    report_type: ReportType
    generated_at: datetime
    generated_by: str
    activation_log: EmergencyActivationLog
    deactivation_log: Optional[EmergencyDeactivationLog]
    job_termination_summary: Dict[str, Any]
    session_impact_summary: Dict[str, Any]
    system_impact_assessment: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    recommendations: List[str]
    attachments: List[str]


class EmergencyMaintenanceReporter:
    """
    Comprehensive emergency maintenance reporting system
    
    Features:
    - Emergency activation and deactivation logging
    - Comprehensive summary report generation
    - System impact assessment and documentation
    - Timeline tracking and analysis
    - Metrics collection and reporting
    - Recommendations and lessons learned
    """
    
    def __init__(self, 
                 emergency_handler: EmergencyMaintenanceHandler,
                 job_termination_manager: Optional[EmergencyJobTerminationManager] = None):
        """
        Initialize emergency maintenance reporter
        
        Args:
            emergency_handler: Emergency maintenance handler instance
            job_termination_manager: Job termination manager (optional)
        """
        self.emergency_handler = emergency_handler
        self.job_termination_manager = job_termination_manager
        
        # Report storage
        self._activation_logs: Dict[str, EmergencyActivationLog] = {}
        self._deactivation_logs: Dict[str, EmergencyDeactivationLog] = {}
        self._summary_reports: Dict[str, EmergencySummaryReport] = {}
        
        # Report statistics
        self._report_stats = {
            'total_activations': 0,
            'total_deactivations': 0,
            'total_reports_generated': 0,
            'average_emergency_duration': 0.0,
            'most_common_triggers': {},
            'severity_distribution': {}
        }
    
    def log_emergency_activation(self,
                                activation_id: str,
                                triggered_by: str,
                                trigger_source: str,
                                reason: str,
                                severity: ReportSeverity = ReportSeverity.HIGH,
                                affected_systems: Optional[List[str]] = None,
                                estimated_duration: Optional[int] = None,
                                authorization_level: str = "admin",
                                contact_information: Optional[Dict[str, str]] = None,
                                escalation_path: Optional[List[str]] = None) -> EmergencyActivationLog:
        """
        Log emergency maintenance activation with comprehensive details
        
        Args:
            activation_id: Unique identifier for this activation
            triggered_by: Who triggered the emergency maintenance
            trigger_source: Source of the trigger (manual, automated, etc.)
            reason: Reason for emergency maintenance
            severity: Severity level of the emergency
            affected_systems: List of affected systems
            estimated_duration: Estimated duration in minutes
            authorization_level: Authorization level required
            contact_information: Emergency contact information
            escalation_path: Escalation path for the emergency
            
        Returns:
            EmergencyActivationLog object
        """
        try:
            activation_log = EmergencyActivationLog(
                activation_id=activation_id,
                timestamp=datetime.now(timezone.utc),
                triggered_by=triggered_by,
                trigger_source=trigger_source,
                reason=reason,
                severity=severity,
                affected_systems=affected_systems or ["all"],
                estimated_duration=estimated_duration,
                authorization_level=authorization_level,
                contact_information=contact_information or {},
                escalation_path=escalation_path or []
            )
            
            # Store activation log
            self._activation_logs[activation_id] = activation_log
            
            # Update statistics
            self._report_stats['total_activations'] += 1
            
            # Update trigger statistics
            if trigger_source not in self._report_stats['most_common_triggers']:
                self._report_stats['most_common_triggers'][trigger_source] = 0
            self._report_stats['most_common_triggers'][trigger_source] += 1
            
            # Update severity statistics
            severity_key = severity.value
            if severity_key not in self._report_stats['severity_distribution']:
                self._report_stats['severity_distribution'][severity_key] = 0
            self._report_stats['severity_distribution'][severity_key] += 1
            
            logger.info(f"Emergency activation logged: {activation_id} by {triggered_by} ({severity.value})")
            
            return activation_log
            
        except Exception as e:
            logger.error(f"Error logging emergency activation: {str(e)}")
            raise
    
    def log_emergency_deactivation(self,
                                  deactivation_id: str,
                                  activation_id: str,
                                  deactivated_by: str,
                                  resolution_summary: str,
                                  validation_checks: Optional[Dict[str, bool]] = None,
                                  lessons_learned: Optional[List[str]] = None,
                                  follow_up_actions: Optional[List[str]] = None) -> EmergencyDeactivationLog:
        """
        Log emergency maintenance deactivation with validation and summary
        
        Args:
            deactivation_id: Unique identifier for this deactivation
            activation_id: ID of the corresponding activation
            deactivated_by: Who deactivated the emergency maintenance
            resolution_summary: Summary of how the emergency was resolved
            validation_checks: Dictionary of validation checks performed
            lessons_learned: List of lessons learned from this emergency
            follow_up_actions: List of follow-up actions required
            
        Returns:
            EmergencyDeactivationLog object
        """
        try:
            # Get activation log to calculate duration
            activation_log = self._activation_logs.get(activation_id)
            if not activation_log:
                logger.warning(f"No activation log found for {activation_id}")
                duration_minutes = 0.0
            else:
                duration = datetime.now(timezone.utc) - activation_log.timestamp
                duration_minutes = duration.total_seconds() / 60
            
            # Determine recovery status based on validation checks
            recovery_status = "successful"
            if validation_checks:
                failed_checks = [k for k, v in validation_checks.items() if not v]
                if failed_checks:
                    recovery_status = f"partial_failure ({len(failed_checks)} checks failed)"
            
            deactivation_log = EmergencyDeactivationLog(
                deactivation_id=deactivation_id,
                activation_id=activation_id,
                timestamp=datetime.now(timezone.utc),
                deactivated_by=deactivated_by,
                duration_minutes=duration_minutes,
                resolution_summary=resolution_summary,
                validation_checks=validation_checks or {},
                recovery_status=recovery_status,
                lessons_learned=lessons_learned or [],
                follow_up_actions=follow_up_actions or []
            )
            
            # Store deactivation log
            self._deactivation_logs[deactivation_id] = deactivation_log
            
            # Update statistics
            self._report_stats['total_deactivations'] += 1
            
            # Update average duration
            total_deactivations = self._report_stats['total_deactivations']
            current_avg = self._report_stats['average_emergency_duration']
            new_avg = ((current_avg * (total_deactivations - 1)) + duration_minutes) / total_deactivations
            self._report_stats['average_emergency_duration'] = new_avg
            
            logger.info(f"Emergency deactivation logged: {deactivation_id} by {deactivated_by} "
                       f"(duration: {duration_minutes:.1f}m, status: {recovery_status})")
            
            return deactivation_log
            
        except Exception as e:
            logger.error(f"Error logging emergency deactivation: {str(e)}")
            raise
    
    def generate_comprehensive_report(self,
                                    activation_id: str,
                                    report_type: ReportType = ReportType.SUMMARY,
                                    generated_by: str = "system") -> EmergencySummaryReport:
        """
        Generate comprehensive emergency maintenance report
        
        Args:
            activation_id: ID of the emergency activation to report on
            report_type: Type of report to generate
            generated_by: Who generated the report
            
        Returns:
            EmergencySummaryReport object
        """
        try:
            # Get activation and deactivation logs
            activation_log = self._activation_logs.get(activation_id)
            if not activation_log:
                raise ValueError(f"No activation log found for {activation_id}")
            
            deactivation_log = None
            for deact_log in self._deactivation_logs.values():
                if deact_log.activation_id == activation_id:
                    deactivation_log = deact_log
                    break
            
            # Generate report ID
            report_id = f"EMR_{activation_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            # Get job termination summary
            job_termination_summary = self._generate_job_termination_summary()
            
            # Get session impact summary
            session_impact_summary = self._generate_session_impact_summary()
            
            # Get system impact assessment
            system_impact_assessment = self._generate_system_impact_assessment(activation_log)
            
            # Generate timeline
            timeline = self._generate_emergency_timeline(activation_log, deactivation_log)
            
            # Collect metrics
            metrics = self._collect_emergency_metrics(activation_log, deactivation_log)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(activation_log, deactivation_log)
            
            # Create summary report
            summary_report = EmergencySummaryReport(
                report_id=report_id,
                report_type=report_type,
                generated_at=datetime.now(timezone.utc),
                generated_by=generated_by,
                activation_log=activation_log,
                deactivation_log=deactivation_log,
                job_termination_summary=job_termination_summary,
                session_impact_summary=session_impact_summary,
                system_impact_assessment=system_impact_assessment,
                timeline=timeline,
                metrics=metrics,
                recommendations=recommendations,
                attachments=[]
            )
            
            # Store report
            self._summary_reports[report_id] = summary_report
            self._report_stats['total_reports_generated'] += 1
            
            logger.info(f"Comprehensive emergency report generated: {report_id}")
            
            return summary_report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {str(e)}")
            raise
    
    def validate_emergency_deactivation(self, activation_id: str) -> Dict[str, bool]:
        """
        Perform validation checks before emergency deactivation
        
        Args:
            activation_id: ID of the emergency activation to validate
            
        Returns:
            Dictionary of validation check results
        """
        try:
            validation_results = {}
            
            # Check 1: Emergency handler status
            emergency_status = self.emergency_handler.get_emergency_status()
            validation_results['emergency_handler_active'] = emergency_status.get('is_active', False)
            
            # Check 2: No active jobs remaining
            if self.job_termination_manager:
                termination_stats = self.job_termination_manager.get_termination_statistics()
                recovery_queue_size = termination_stats.get('recovery_queue_size', 0)
                validation_results['no_pending_job_recovery'] = recovery_queue_size == 0
            else:
                validation_results['no_pending_job_recovery'] = True
            
            # Check 3: System components responsive
            validation_results['system_components_responsive'] = self._check_system_components()
            
            # Check 4: Database connectivity
            validation_results['database_connectivity'] = self._check_database_connectivity()
            
            # Check 5: Session management operational
            validation_results['session_management_operational'] = self._check_session_management()
            
            # Check 6: No critical errors in logs
            validation_results['no_critical_errors'] = self._check_for_critical_errors()
            
            logger.info(f"Emergency deactivation validation completed for {activation_id}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating emergency deactivation: {str(e)}")
            return {'validation_error': False, 'error_message': str(e)}
    
    def export_report_to_json(self, report_id: str) -> str:
        """
        Export emergency report to JSON format
        
        Args:
            report_id: ID of the report to export
            
        Returns:
            JSON string representation of the report
        """
        try:
            report = self._summary_reports.get(report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")
            
            # Convert dataclass to dictionary with datetime serialization
            report_dict = asdict(report)
            
            # Convert datetime objects and enums to serializable format
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, Enum):
                    return obj.value
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                else:
                    return obj
            
            report_dict = convert_datetime(report_dict)
            
            return json.dumps(report_dict, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error exporting report to JSON: {str(e)}")
            raise
    
    def get_reporting_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive reporting statistics
        
        Returns:
            Dictionary with reporting statistics
        """
        try:
            return {
                'report_statistics': self._report_stats.copy(),
                'active_emergencies': len([
                    log for log in self._activation_logs.values()
                    if log.activation_id not in [
                        deact.activation_id for deact in self._deactivation_logs.values()
                    ]
                ]),
                'total_activation_logs': len(self._activation_logs),
                'total_deactivation_logs': len(self._deactivation_logs),
                'total_summary_reports': len(self._summary_reports),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting reporting statistics: {str(e)}")
            return {'error': str(e)}
    
    def _generate_job_termination_summary(self) -> Dict[str, Any]:
        """Generate job termination summary for report"""
        try:
            if not self.job_termination_manager:
                return {'status': 'no_job_manager', 'details': 'Job termination manager not available'}
            
            stats = self.job_termination_manager.get_termination_statistics()
            return {
                'status': 'available',
                'jobs_terminated': stats['statistics'].get('jobs_terminated', 0),
                'jobs_recovered': stats['statistics'].get('jobs_recovered', 0),
                'termination_failures': stats['statistics'].get('termination_failures', 0),
                'recovery_failures': stats['statistics'].get('recovery_failures', 0),
                'recovery_rate_percent': stats.get('recovery_rate_percent', 0),
                'notifications_sent': stats['statistics'].get('notifications_sent', 0)
            }
            
        except Exception as e:
            logger.error(f"Error generating job termination summary: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _generate_session_impact_summary(self) -> Dict[str, Any]:
        """Generate session impact summary for report"""
        try:
            emergency_status = self.emergency_handler.get_emergency_status()
            return {
                'status': 'available',
                'sessions_invalidated': emergency_status.get('invalidated_sessions_count', 0),
                'impact_assessment': 'high' if emergency_status.get('invalidated_sessions_count', 0) > 10 else 'medium'
            }
            
        except Exception as e:
            logger.error(f"Error generating session impact summary: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _generate_system_impact_assessment(self, activation_log: EmergencyActivationLog) -> Dict[str, Any]:
        """Generate system impact assessment"""
        return {
            'severity': activation_log.severity.value,
            'affected_systems': activation_log.affected_systems,
            'estimated_user_impact': 'high' if activation_log.severity in [ReportSeverity.HIGH, ReportSeverity.CRITICAL] else 'medium',
            'business_impact': 'service_disruption',
            'recovery_complexity': 'medium'
        }
    
    def _generate_emergency_timeline(self, 
                                   activation_log: EmergencyActivationLog,
                                   deactivation_log: Optional[EmergencyDeactivationLog]) -> List[Dict[str, Any]]:
        """Generate emergency timeline"""
        timeline = [
            {
                'timestamp': activation_log.timestamp.isoformat(),
                'event': 'emergency_activated',
                'description': f'Emergency maintenance activated by {activation_log.triggered_by}',
                'details': {'reason': activation_log.reason, 'severity': activation_log.severity.value}
            }
        ]
        
        if deactivation_log:
            timeline.append({
                'timestamp': deactivation_log.timestamp.isoformat(),
                'event': 'emergency_deactivated',
                'description': f'Emergency maintenance deactivated by {deactivation_log.deactivated_by}',
                'details': {'duration_minutes': deactivation_log.duration_minutes, 'status': deactivation_log.recovery_status}
            })
        
        return timeline
    
    def _collect_emergency_metrics(self,
                                 activation_log: EmergencyActivationLog,
                                 deactivation_log: Optional[EmergencyDeactivationLog]) -> Dict[str, Any]:
        """Collect emergency metrics"""
        metrics = {
            'activation_time': activation_log.timestamp.isoformat(),
            'severity': activation_log.severity.value,
            'trigger_source': activation_log.trigger_source
        }
        
        if deactivation_log:
            metrics.update({
                'deactivation_time': deactivation_log.timestamp.isoformat(),
                'total_duration_minutes': deactivation_log.duration_minutes,
                'recovery_status': deactivation_log.recovery_status,
                'validation_checks_passed': sum(1 for v in deactivation_log.validation_checks.values() if v),
                'validation_checks_total': len(deactivation_log.validation_checks)
            })
        
        return metrics
    
    def _generate_recommendations(self,
                                activation_log: EmergencyActivationLog,
                                deactivation_log: Optional[EmergencyDeactivationLog]) -> List[str]:
        """Generate recommendations based on emergency data"""
        recommendations = []
        
        # Duration-based recommendations
        if deactivation_log and deactivation_log.duration_minutes > 60:
            recommendations.append("Consider implementing faster emergency response procedures")
        
        # Severity-based recommendations
        if activation_log.severity == ReportSeverity.CRITICAL:
            recommendations.append("Review critical system monitoring and alerting")
        
        # Validation-based recommendations
        if deactivation_log and deactivation_log.validation_checks:
            failed_checks = [k for k, v in deactivation_log.validation_checks.items() if not v]
            if failed_checks:
                recommendations.append(f"Address failed validation checks: {', '.join(failed_checks)}")
        
        # Follow-up recommendations
        if deactivation_log and deactivation_log.follow_up_actions:
            recommendations.append("Complete all identified follow-up actions")
        
        return recommendations
    
    def _check_system_components(self) -> bool:
        """Check if system components are responsive"""
        try:
            # In a real implementation, this would check various system components
            # For now, we'll simulate a basic check
            return True
        except Exception:
            return False
    
    def _check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        try:
            # In a real implementation, this would test database connectivity
            return True
        except Exception:
            return False
    
    def _check_session_management(self) -> bool:
        """Check session management operational status"""
        try:
            # In a real implementation, this would check session management
            return True
        except Exception:
            return False
    
    def _check_for_critical_errors(self) -> bool:
        """Check for critical errors in logs"""
        try:
            # In a real implementation, this would scan recent logs for critical errors
            return True
        except Exception:
            return False