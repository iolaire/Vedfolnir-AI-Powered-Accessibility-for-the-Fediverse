#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Compliance Data Seeding Script

Populates the compliance tracking system with realistic requirements and metrics
to demonstrate the compliance calculation functionality.
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_session_manager import unified_session_manager
from models import ComplianceAudit, ComplianceRequirement, ComplianceMetric, ComplianceStandard, ComplianceStatus, ComplianceCategory, User

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_or_create_admin_user(session):
    """Get or create an admin user for audits"""
    # Try to find an existing admin user
    admin_user = session.query(User).filter(User.role.in_(['admin', 'administrator'])).first()
    
    if not admin_user:
        # Create a default admin user
        admin_user = User(
            username='admin',
            email='admin@vedfolnir.local',
            role='admin',
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(admin_user)
        session.flush()
        logger.info("Created default admin user for compliance audits")
    
    return admin_user

def create_compliance_requirements(session, audit_id, standard, requirements_data):
    """Create compliance requirements for a given standard"""
    created_requirements = []
    
    for req_data in requirements_data:
        requirement = ComplianceRequirement(
            audit_id=audit_id,
            standard=standard,
            category=req_data['category'],
            requirement_id=req_data['requirement_id'],
            title=req_data['title'],
            description=req_data['description'],
            status=req_data['status'],
            score=req_data['score'],
            is_critical=req_data.get('is_critical', False),
            implementation_details=req_data.get('implementation_details', ''),
            test_methodology=req_data.get('test_methodology', '')
        )
        session.add(requirement)
        session.flush()
        
        # Create corresponding metric
        metric = ComplianceMetric(
            standard=standard,
            category=req_data['category'],
            metric_name=req_data['title'],
            metric_value=req_data['score'],
            target_value=100.0,
            unit='percentage',
            data_source='compliance_audit',
            confidence_score=0.9,
            metric_metadata=f'Requirement ID: {req_data["requirement_id"]}'
        )
        
        session.add(metric)
        created_requirements.append(requirement)
    
    return created_requirements

def seed_owasp_asvs_data(session, admin_user):
    """Seed OWASP ASVS compliance data"""
    logger.info("Seeding OWASP ASVS compliance data...")
    
    # Create OWASP ASVS audit
    audit = ComplianceAudit(
        standard=ComplianceStandard.OWASP_ASVS,
        auditor_id=admin_user.id,
        overall_score=92.5,
        status=ComplianceStatus.COMPLIANT,
        findings_count=3,
        critical_findings=0,
        high_findings=1,
        medium_findings=1,
        low_findings=1,
        scope='Application Security Verification',
        methodology='OWASP Application Security Verification Standard',
        next_audit_date=datetime.utcnow() + timedelta(days=90)
    )
    session.add(audit)
    session.flush()
    
    # OWASP ASVS requirements
    requirements_data = [
        {
            'category': ComplianceCategory.ACCESS_CONTROL,
            'requirement_id': 'OWASP-ASVS-1.1.1',
            'title': 'User Authentication',
            'description': 'Verify that the application enforces strong authentication mechanisms',
            'status': ComplianceStatus.COMPLIANT,
            'score': 95.0,
            'is_critical': True,
            'implementation_details': 'Multi-factor authentication implemented with rate limiting',
            'test_methodology': 'Manual verification and automated testing'
        },
        {
            'category': ComplianceCategory.ACCESS_CONTROL,
            'requirement_id': 'OWASP-ASVS-1.2.1',
            'title': 'Session Management',
            'description': 'Verify that session management is secure against common attacks',
            'status': ComplianceStatus.COMPLIANT,
            'score': 90.0,
            'is_critical': True,
            'implementation_details': 'Secure session tokens with proper timeout handling',
            'test_methodology': 'Session token analysis and timeout testing'
        },
        {
            'category': ComplianceCategory.APPLICATION_SECURITY,
            'requirement_id': 'OWASP-ASVS-4.1.1',
            'title': 'Input Validation',
            'description': 'Verify that all user input is properly validated',
            'status': ComplianceStatus.COMPLIANT,
            'score': 100.0,
            'is_critical': True,
            'implementation_details': 'Comprehensive input validation with parameterized queries',
            'test_methodology': 'Injection testing and input fuzzing'
        },
        {
            'category': ComplianceCategory.APPLICATION_SECURITY,
            'requirement_id': 'OWASP-ASVS-4.2.1',
            'title': 'Output Encoding',
            'description': 'Verify that output encoding prevents XSS attacks',
            'status': ComplianceStatus.COMPLIANT,
            'score': 100.0,
            'is_critical': True,
            'implementation_details': 'Context-aware output encoding',
            'test_methodology': 'XSS payload testing'
        },
        {
            'category': ComplianceCategory.DATA_PROTECTION,
            'requirement_id': 'OWASP-ASVS-6.2.1',
            'title': 'Data Protection at Rest',
            'description': 'Verify that sensitive data is encrypted at rest',
            'status': ComplianceStatus.PARTIALLY_COMPLIANT,
            'score': 80.0,
            'is_critical': True,
            'implementation_details': 'Encryption implemented but key management needs improvement',
            'test_methodology': 'Data encryption verification'
        }
    ]
    
    created_reqs = create_compliance_requirements(session, audit.id, ComplianceStandard.OWASP_ASVS, requirements_data)
    logger.info(f"Created {len(created_reqs)} OWASP ASVS requirements")
    
    return audit

def seed_cwe_coverage_data(session, admin_user):
    """Seed CWE coverage compliance data"""
    logger.info("Seeding CWE coverage compliance data...")
    
    # Create CWE audit
    audit = ComplianceAudit(
        standard=ComplianceStandard.CWE_COVERAGE,
        auditor_id=admin_user.id,
        overall_score=88.0,
        status=ComplianceStatus.COMPLIANT,
        findings_count=4,
        critical_findings=0,
        high_findings=2,
        medium_findings=1,
        low_findings=1,
        scope='Common Weakness Enumeration Coverage',
        methodology='CWE Top 25 Coverage Analysis',
        next_audit_date=datetime.utcnow() + timedelta(days=60)
    )
    session.add(audit)
    session.flush()
    
    # CWE requirements
    requirements_data = [
        {
            'category': ComplianceCategory.APPLICATION_SECURITY,
            'requirement_id': 'CWE-79',
            'title': 'Cross-site Scripting (XSS)',
            'description': 'Prevent cross-site scripting vulnerabilities',
            'status': ComplianceStatus.COMPLIANT,
            'score': 100.0,
            'is_critical': True,
            'implementation_details': 'Comprehensive XSS prevention implemented',
            'test_methodology': 'XSS payload testing and code review'
        },
        {
            'category': ComplianceCategory.APPLICATION_SECURITY,
            'requirement_id': 'CWE-89',
            'title': 'SQL Injection',
            'description': 'Prevent SQL injection attacks',
            'status': ComplianceStatus.COMPLIANT,
            'score': 100.0,
            'is_critical': True,
            'implementation_details': 'Parameterized queries and ORM usage',
            'test_methodology': 'SQL injection testing'
        },
        {
            'category': ComplianceCategory.APPLICATION_SECURITY,
            'requirement_id': 'CWE-352',
            'title': 'CSRF Protection',
            'description': 'Implement Cross-Site Request Forgery protection',
            'status': ComplianceStatus.COMPLIANT,
            'score': 100.0,
            'is_critical': True,
            'implementation_details': 'CSRF tokens implemented on all state-changing operations',
            'test_methodology': 'CSRF token verification testing'
        },
        {
            'category': ComplianceCategory.ACCESS_CONTROL,
            'requirement_id': 'CWE-287',
            'title': 'Authentication Issues',
            'description': 'Implement proper authentication mechanisms',
            'status': ComplianceStatus.PARTIALLY_COMPLIANT,
            'score': 75.0,
            'is_critical': True,
            'implementation_details': 'Authentication implemented but missing some security headers',
            'test_methodology': 'Authentication bypass testing'
        },
        {
            'category': ComplianceCategory.DATA_PROTECTION,
            'requirement_id': 'CWE-311',
            'title': 'Missing Encryption',
            'description': 'Ensure sensitive data is properly encrypted',
            'status': ComplianceStatus.PARTIALLY_COMPLIANT,
            'score': 65.0,
            'is_critical': True,
            'implementation_details': 'Encryption partially implemented',
            'test_methodology': 'Data encryption verification'
        }
    ]
    
    created_reqs = create_compliance_requirements(session, audit.id, ComplianceStandard.CWE_COVERAGE, requirements_data)
    logger.info(f"Created {len(created_reqs)} CWE coverage requirements")
    
    return audit

def seed_iso27001_data(session, admin_user):
    """Seed ISO 27001 compliance data"""
    logger.info("Seeding ISO 27001 compliance data...")
    
    # Create ISO 27001 audit
    audit = ComplianceAudit(
        standard=ComplianceStandard.ISO_27001,
        auditor_id=admin_user.id,
        overall_score=85.0,
        status=ComplianceStatus.COMPLIANT,
        findings_count=6,
        critical_findings=1,
        high_findings=2,
        medium_findings=2,
        low_findings=1,
        scope='Information Security Management System',
        methodology='ISO 27001:2022 Standard Audit',
        next_audit_date=datetime.utcnow() + timedelta(days=180)
    )
    session.add(audit)
    session.flush()
    
    # ISO 27001 requirements
    requirements_data = [
        {
            'category': ComplianceCategory.ACCESS_CONTROL,
            'requirement_id': 'ISO-27001-A.9',
            'title': 'Access Control',
            'description': 'Logical access control to information systems',
            'status': ComplianceStatus.COMPLIANT,
            'score': 90.0,
            'is_critical': True,
            'implementation_details': 'Role-based access control implemented',
            'test_methodology': 'Access control review and testing'
        },
        {
            'category': ComplianceCategory.DATA_PROTECTION,
            'requirement_id': 'ISO-27001-A.8',
            'title': 'Asset Management',
            'description': 'Inventory of information assets',
            'status': ComplianceStatus.PARTIALLY_COMPLIANT,
            'score': 80.0,
            'is_critical': True,
            'implementation_details': 'Asset inventory partially implemented',
            'test_methodology': 'Asset inventory verification'
        },
        {
            'category': ComplianceCategory.AUDIT_LOGGING,
            'requirement_id': 'ISO-27001-A.12',
            'title': 'Logging and Monitoring',
            'description': 'Event logging and monitoring',
            'status': ComplianceStatus.COMPLIANT,
            'score': 95.0,
            'is_critical': True,
            'implementation_details': 'Comprehensive logging and monitoring system',
            'test_methodology': 'Log review and monitoring verification'
        },
        {
            'category': ComplianceCategory.INCIDENT_RESPONSE,
            'requirement_id': 'ISO-27001-A.16',
            'title': 'Incident Management',
            'description': 'Information security incident management',
            'status': ComplianceStatus.PARTIALLY_COMPLIANT,
            'score': 70.0,
            'is_critical': True,
            'implementation_details': 'Basic incident response procedures in place',
            'test_methodology': 'Incident response procedure review'
        }
    ]
    
    created_reqs = create_compliance_requirements(session, audit.id, ComplianceStandard.ISO_27001, requirements_data)
    logger.info(f"Created {len(created_reqs)} ISO 27001 requirements")
    
    return audit

def seed_all_compliance_data():
    """Seed all compliance data"""
    try:
        logger.info("Starting compliance data seeding...")
        
        with unified_session_manager.get_db_session() as session:
            # Get or create admin user
            admin_user = get_or_create_admin_user(session)
            
            # Check if data already exists
            existing_audits = session.query(ComplianceAudit).count()
            if existing_audits > 0:
                logger.info(f"Compliance data already exists ({existing_audits} audits found). Skipping seed.")
                return True
            
            # Seed data for different standards
            owasp_audit = seed_owasp_asvs_data(session, admin_user)
            cwe_audit = seed_cwe_coverage_data(session, admin_user)
            iso_audit = seed_iso27001_data(session, admin_user)
            
            # Create minimal audits for other standards
            other_standards = [
                (ComplianceStandard.SOC2, 80.0, "SOC Type 2 Compliance"),
                (ComplianceStandard.GDPR, 75.0, "GDPR Compliance"),
                (ComplianceStandard.HIPAA, 70.0, "HIPAA Compliance"),
                (ComplianceStandard.PCI_DSS, 85.0, "PCI DSS Compliance"),
                (ComplianceStandard.NIST_800_53, 82.0, "NIST SP 800-53 Compliance")
            ]
            
            for standard, score, scope in other_standards:
                audit = ComplianceAudit(
                    standard=standard,
                    auditor_id=admin_user.id,
                    overall_score=score,
                    status=ComplianceStatus.COMPLIANT if score >= 70 else ComplianceStatus.PARTIALLY_COMPLIANT,
                    findings_count=max(1, int((100 - score) / 10)),
                    critical_findings=0,
                    high_findings=max(0, int((100 - score) / 20)),
                    medium_findings=max(0, int((100 - score) / 25)),
                    low_findings=max(0, int((100 - score) / 30)),
                    scope=scope,
                    methodology='Automated compliance assessment',
                    next_audit_date=datetime.utcnow() + timedelta(days=120)
                )
                session.add(audit)
                session.flush()  # Flush to get the audit ID
                
                # Add at least one requirement per standard
                requirement = ComplianceRequirement(
                    audit_id=audit.id,
                    standard=standard,
                    category=ComplianceCategory.APPLICATION_SECURITY,
                    requirement_id=f'{standard.value}-1',
                    title=f'{standard.value} Requirement 1',
                    description=f'Primary requirement for {standard.value}',
                    status=ComplianceStatus.COMPLIANT if score >= 70 else ComplianceStatus.PARTIALLY_COMPLIANT,
                    score=score,
                    is_critical=True
                )
                session.add(requirement)
                session.flush()
                
                # Add metric
                metric = ComplianceMetric(
                    standard=standard,
                    category=ComplianceCategory.APPLICATION_SECURITY,
                    metric_name=f'{standard.value} Compliance Score',
                    metric_value=score,
                    target_value=100.0,
                    unit='percentage',
                    data_source='automated_assessment',
                    confidence_score=0.8,
                    metric_metadata=f'Auto-generated metric for {standard.value}'
                )
                session.add(metric)
            
            session.commit()
            logger.info("Compliance data seeding completed successfully!")
            logger.info(f"Created {session.query(ComplianceAudit).count()} audits")
            logger.info(f"Created {session.query(ComplianceRequirement).count()} requirements")
            logger.info(f"Created {session.query(ComplianceMetric).count()} metrics")
            
            return True
            
    except Exception as e:
        logger.error(f"Error seeding compliance data: {e}")
        return False

def verify_seeded_data():
    """Verify that the compliance data was seeded correctly"""
    try:
        logger.info("Verifying seeded compliance data...")
        
        with unified_session_manager.get_db_session() as session:
            # Check audits
            audit_count = session.query(ComplianceAudit).count()
            logger.info(f"Total audits: {audit_count}")
            
            # Check requirements
            requirement_count = session.query(ComplianceRequirement).count()
            logger.info(f"Total requirements: {requirement_count}")
            
            # Check metrics
            metric_count = session.query(ComplianceMetric).count()
            logger.info(f"Total metrics: {metric_count}")
            
            # Show audit summary
            audits = session.query(ComplianceAudit).all()
            logger.info("Audit Summary:")
            for audit in audits:
                logger.info(f"  {audit.standard.value}: {audit.overall_score}% ({audit.status.value})")
        
        logger.info("Compliance data verification completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying compliance data: {e}")
        return False

if __name__ == "__main__":
    print("Compliance Data Seeding Script")
    print("=" * 50)
    
    if seed_all_compliance_data():
        print("\n✓ Compliance data seeded successfully")
        
        if verify_seeded_data():
            print("✓ Data verification passed")
        else:
            print("✗ Data verification failed")
            sys.exit(1)
    else:
        print("\n✗ Failed to seed compliance data")
        sys.exit(1)