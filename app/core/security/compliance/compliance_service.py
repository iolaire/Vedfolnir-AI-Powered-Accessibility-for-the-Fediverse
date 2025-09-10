# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Compliance Service

Provides compliance calculation and tracking functionality for security audit systems.
Calculates compliance scores based on requirements, audits, and metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from models import ComplianceAudit, ComplianceRequirement, ComplianceMetric, ComplianceStandard, ComplianceStatus, ComplianceCategory
from unified_session_manager import unified_session_manager

logger = logging.getLogger(__name__)

class ComplianceService:
    """Service for calculating and managing compliance data"""
    
    def __init__(self, db_session=None):
        """Initialize compliance service"""
        self.db_session = db_session
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get current compliance status for all standards"""
        try:
            compliance_data = {}
            
            # Use context manager for database session
            with unified_session_manager.get_db_session() as session:
                # Calculate compliance for each standard
                for standard in ComplianceStandard:
                    compliance_data[standard.value] = self._calculate_standard_compliance(standard, session)
                
                # Get latest audit date
                latest_audit = session.query(
                    func.max(ComplianceAudit.audit_date)
                ).scalar()
            
            return {
                'owasp_compliance': compliance_data.get('owasp_asvs', {}).get('score', 0),
                'cwe_coverage': compliance_data.get('cwe_coverage', {}).get('score', 0),
                'last_audit': latest_audit.isoformat() if latest_audit else None,
                'standards': compliance_data,
                'calculated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating compliance status: {e}")
            # Return fallback data
            return {
                'owasp_compliance': 0,
                'cwe_coverage': 0,
                'last_audit': None,
                'standards': {},
                'calculated_at': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def _calculate_standard_compliance(self, standard: ComplianceStandard, session: Session) -> Dict[str, Any]:
        """Calculate compliance score for a specific standard"""
        try:
            # Get requirements for this standard
            requirements = session.query(ComplianceRequirement).filter(
                ComplianceRequirement.standard == standard
            ).all()
            
            if not requirements:
                return {
                    'score': 0,
                    'total_requirements': 0,
                    'met_requirements': 0,
                    'status': 'no_data'
                }
            
            total_requirements = len(requirements)
            met_requirements = 0
            
            # Check each requirement
            for requirement in requirements:
                if self._is_requirement_met(requirement, session):
                    met_requirements += 1
            
            # Calculate score
            score = (met_requirements / total_requirements) * 100 if total_requirements > 0 else 0
            
            # Determine status
            if score >= 90:
                status = 'excellent'
            elif score >= 70:
                status = 'good'
            elif score >= 50:
                status = 'fair'
            else:
                status = 'poor'
            
            return {
                'score': round(score, 1),
                'total_requirements': total_requirements,
                'met_requirements': met_requirements,
                'status': status,
                'last_assessed': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating compliance for {standard}: {e}")
            return {
                'score': 0,
                'total_requirements': 0,
                'met_requirements': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def _is_requirement_met(self, requirement: ComplianceRequirement, session: Session) -> bool:
        """Check if a compliance requirement is met"""
        try:
            # Get latest metric for this standard and category
            latest_metric = session.query(ComplianceMetric).filter(
                ComplianceMetric.standard == requirement.standard,
                ComplianceMetric.category == requirement.category
            ).order_by(ComplianceMetric.created_at.desc()).first()
            
            if not latest_metric:
                # Default to requirement status if no metrics exist
                return requirement.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT]
            
            # Check if metric indicates compliance based on score
            if latest_metric.metric_value >= (requirement.score or 80.0):
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"Error checking requirement {requirement.id}: {e}")
            # Default to requirement status
            return requirement.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT]
    
    def record_compliance_metric(self, requirement_id: int, value: Any, metric_type: str) -> bool:
        """Record a compliance metric"""
        try:
            with unified_session_manager.get_db_session() as session:
                metric = ComplianceMetric(
                    requirement_id=requirement_id,
                    timestamp=datetime.utcnow(),
                    metric_type=metric_type
                )
                
                # Set value based on type
                if metric_type == 'boolean':
                    metric.value_bool = bool(value)
                elif metric_type == 'percentage':
                    metric.value_float = float(value)
                elif metric_type == 'count':
                    metric.value_int = int(value)
                else:
                    metric.value_string = str(value)
                
                session.add(metric)
                session.commit()
                
                logger.info(f"Recorded compliance metric for requirement {requirement_id}")
                return True
            
        except Exception as e:
            logger.error(f"Error recording compliance metric: {e}")
            return False
    
    def create_compliance_audit(self, standard: ComplianceStandard, auditor_id: int, 
                              score: float, findings: List[Dict[str, Any]]) -> Optional[ComplianceAudit]:
        """Create a new compliance audit"""
        try:
            with unified_session_manager.get_db_session() as session:
                audit = ComplianceAudit(
                    standard=standard,
                    auditor_id=auditor_id,
                    overall_score=score,
                    status=ComplianceStatus.COMPLIANT if score >= 70 else ComplianceStatus.NON_COMPLIANT,
                    findings=findings,
                    next_audit_date=datetime.utcnow() + timedelta(days=90)  # Quarterly audits
                )
                
                session.add(audit)
                session.commit()
                
                logger.info(f"Created compliance audit for {standard.value} with score {score}")
                return audit
            
        except Exception as e:
            logger.error(f"Error creating compliance audit: {e}")
            return None
    
    def get_compliance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get compliance trends over time"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            with unified_session_manager.get_db_session() as session:
                # Get audit trends
                audits = session.query(ComplianceAudit).filter(
                    ComplianceAudit.audit_date >= start_date
                ).order_by(ComplianceAudit.audit_date.asc()).all()
                
                trends = {}
                for audit in audits:
                    standard = audit.standard.value
                    if standard not in trends:
                        trends[standard] = []
                    
                    trends[standard].append({
                        'date': audit.audit_date.isoformat(),
                        'score': audit.overall_score,
                        'status': audit.status.value
                    })
            
            return {
                'trends': trends,
                'period_days': days,
                'calculated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance trends: {e}")
            return {
                'trends': {},
                'period_days': days,
                'error': str(e)
            }
    
    def seed_initial_data(self) -> bool:
        """Seed initial compliance requirements and data"""
        try:
            with unified_session_manager.get_db_session() as session:
                # Check if data already exists
                existing_count = session.query(ComplianceRequirement).count()
                if existing_count > 0:
                    logger.info("Compliance data already exists, skipping seed")
                    return True
                
                # OWASP Top 10 requirements
                owasp_requirements = [
                    {
                        'name': 'A1: Injection Prevention',
                        'description': 'Prevent injection attacks through proper input validation',
                        'standard': ComplianceStandard.OWASP_ASVS,
                        'category': ComplianceCategory.APPLICATION_SECURITY,
                        'metric_type': 'boolean',
                        'threshold': 1.0,
                        'status': ComplianceStatus.COMPLIANT
                    },
                    {
                        'name': 'A2: Authentication',
                        'description': 'Implement strong authentication mechanisms',
                        'standard': ComplianceStandard.OWASP_ASVS,
                        'category': ComplianceCategory.ACCESS_CONTROL,
                        'metric_type': 'percentage',
                        'threshold': 80.0,
                        'status': ComplianceStatus.COMPLIANT
                    },
                    {
                        'name': 'A3: Data Protection',
                        'description': 'Protect sensitive data at rest and in transit',
                        'standard': ComplianceStandard.OWASP_ASVS,
                        'category': ComplianceCategory.DATA_PROTECTION,
                        'metric_type': 'percentage',
                        'threshold': 90.0,
                        'status': ComplianceStatus.COMPLIANT
                    }
                ]
                
                # CWE requirements
                cwe_requirements = [
                    {
                        'name': 'CWE-79: XSS Prevention',
                        'description': 'Prevent Cross-Site Scripting attacks',
                        'standard': ComplianceStandard.CWE_COVERAGE,
                        'category': ComplianceCategory.APPLICATION_SECURITY,
                        'metric_type': 'boolean',
                        'threshold': 1.0,
                        'status': ComplianceStatus.COMPLIANT
                    },
                    {
                        'name': 'CWE-89: SQL Injection',
                        'description': 'Prevent SQL injection attacks',
                        'standard': ComplianceStandard.CWE_COVERAGE,
                        'category': ComplianceCategory.APPLICATION_SECURITY,
                        'metric_type': 'boolean',
                        'threshold': 1.0,
                        'status': ComplianceStatus.COMPLIANT
                    },
                    {
                        'name': 'CWE-352: CSRF Protection',
                        'description': 'Implement CSRF protection',
                        'standard': ComplianceStandard.CWE_COVERAGE,
                        'category': ComplianceCategory.ACCESS_CONTROL,
                        'metric_type': 'boolean',
                        'threshold': 1.0,
                        'status': ComplianceStatus.COMPLIANT
                    }
                ]
                
                # Add all requirements
                all_requirements = owasp_requirements + cwe_requirements
                for req_data in all_requirements:
                    requirement = ComplianceRequirement(**req_data)
                    session.add(requirement)
                    session.flush()  # Flush to get the ID
                    
                    # Add initial metric
                    metric = ComplianceMetric(
                        requirement_id=requirement.id,
                        timestamp=datetime.utcnow(),
                        metric_type=requirement.metric_type
                    )
                    
                    if requirement.metric_type == 'boolean':
                        metric.value_bool = True
                    elif requirement.metric_type == 'percentage':
                        metric.value_float = 95.0
                    elif requirement.metric_type == 'count':
                        metric.value_int = 1
                    
                    session.add(metric)
                
                session.commit()
                logger.info(f"Seeded {len(all_requirements)} compliance requirements")
                return True
            
        except Exception as e:
            logger.error(f"Error seeding compliance data: {e}")
            return False
    
    def close(self):
        """Close database session"""
        if self.db_session:
            self.db_session.close()

# Global service instance
_compliance_service = None

def get_compliance_service() -> ComplianceService:
    """Get global compliance service instance"""
    global _compliance_service
    if _compliance_service is None:
        _compliance_service = ComplianceService()
    return _compliance_service