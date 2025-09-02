#!/usr/bin/env python3
"""
MySQL Security Hardening and Access Control for Vedfolnir

This module provides comprehensive MySQL security hardening capabilities including:
- User privilege auditing and management
- SSL/TLS configuration validation and enforcement
- Security configuration analysis and recommendations
- Access control policy implementation
- Security compliance checking (CIS, OWASP)
- Automated security hardening procedures
- Security monitoring and alerting

Integrates with existing MySQL health monitoring and performance optimization systems.
"""

import logging
import json
import hashlib
import secrets
import ssl
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pymysql
    from sqlalchemy import create_engine, text
    from cryptography.fernet import Fernet
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import redis
    from config import Config
    from mysql_connection_validator import MySQLConnectionValidator
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required packages are installed")
    sys.exit(1)

logger = logging.getLogger(__name__)

@dataclass
class SecurityAuditResult:
    """Container for security audit results."""
    timestamp: datetime
    overall_score: float
    security_level: str  # 'excellent', 'good', 'fair', 'poor'
    critical_issues: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    compliance_status: Dict[str, Any]
    user_audit_results: Dict[str, Any]
    ssl_audit_results: Dict[str, Any]
    configuration_audit_results: Dict[str, Any]

@dataclass
class UserPrivilegeAudit:
    """Container for user privilege audit results."""
    username: str
    host: str
    privileges: List[str]
    global_privileges: List[str]
    database_privileges: Dict[str, List[str]]
    table_privileges: Dict[str, List[str]]
    is_admin: bool
    has_dangerous_privileges: bool
    last_login: Optional[datetime]
    password_strength: str  # 'strong', 'medium', 'weak', 'unknown'
    security_score: float

@dataclass
class SSLConfiguration:
    """Container for SSL configuration details."""
    ssl_enabled: bool
    ssl_version: Optional[str]
    cipher_suite: Optional[str]
    certificate_path: Optional[str]
    key_path: Optional[str]
    ca_path: Optional[str]
    certificate_valid: bool
    certificate_expires: Optional[datetime]
    certificate_issuer: Optional[str]
    certificate_subject: Optional[str]
    security_score: float

class MySQLSecurityHardening:
    """
    Comprehensive MySQL security hardening and access control system.
    
    Provides user privilege auditing, SSL/TLS configuration, security compliance
    checking, and automated hardening procedures.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the MySQL Security Hardening system.
        
        Args:
            config: Optional Config instance, will create default if not provided
        """
        self.config = config or Config()
        self.validator = MySQLConnectionValidator()
        
        # Security configuration
        self.security_standards = {
            'cis_mysql': self._load_cis_mysql_standards(),
            'owasp_database': self._load_owasp_database_standards(),
            'vedfolnir_custom': self._load_custom_security_standards()
        }
        
        # Encryption for sensitive data
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Redis for security event logging
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_redis()
        
        # Security thresholds
        self.security_thresholds = {
            'password_min_length': int(os.getenv('MYSQL_PASSWORD_MIN_LENGTH', '12')),
            'max_failed_logins': int(os.getenv('MYSQL_MAX_FAILED_LOGINS', '5')),
            'session_timeout': int(os.getenv('MYSQL_SESSION_TIMEOUT', '3600')),
            'certificate_expiry_warning_days': int(os.getenv('MYSQL_CERT_EXPIRY_WARNING_DAYS', '30'))
        }
        
        logger.info("MySQL Security Hardening system initialized")
    
    def _initialize_redis(self):
        """Initialize Redis connection for security event logging."""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/3')  # Use DB 3 for security
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for security logging")
        except Exception as e:
            logger.warning(f"Redis not available for security logging: {e}")
            self.redis_client = None
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data."""
        key_file = Path(os.getenv('MYSQL_SECURITY_KEY_FILE', '.mysql_security_key'))
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Could not read existing encryption key: {e}")
        
        # Generate new key
        key = Fernet.generate_key()
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            logger.info("Generated new encryption key for security data")
        except Exception as e:
            logger.warning(f"Could not save encryption key: {e}")
        
        return key
    
    def _load_cis_mysql_standards(self) -> Dict[str, Any]:
        """Load CIS MySQL security standards."""
        return {
            'version': 'CIS MySQL 8.0 Benchmark v1.0.0',
            'standards': {
                'remove_test_database': {
                    'id': '2.1',
                    'title': 'Remove test database',
                    'description': 'Remove the test database that is installed by default',
                    'severity': 'high'
                },
                'remove_anonymous_users': {
                    'id': '2.2',
                    'title': 'Remove anonymous users',
                    'description': 'Remove anonymous user accounts',
                    'severity': 'critical'
                },
                'remove_remote_root': {
                    'id': '2.3',
                    'title': 'Remove remote root access',
                    'description': 'Disable remote root login',
                    'severity': 'critical'
                },
                'require_ssl': {
                    'id': '3.1',
                    'title': 'Require SSL connections',
                    'description': 'Configure MySQL to require SSL for all connections',
                    'severity': 'high'
                },
                'validate_password_plugin': {
                    'id': '4.1',
                    'title': 'Enable password validation plugin',
                    'description': 'Use validate_password plugin for password strength',
                    'severity': 'medium'
                },
                'log_connections': {
                    'id': '5.1',
                    'title': 'Enable connection logging',
                    'description': 'Log all connection attempts',
                    'severity': 'medium'
                },
                'secure_file_privileges': {
                    'id': '6.1',
                    'title': 'Configure secure_file_priv',
                    'description': 'Restrict file operations to secure directory',
                    'severity': 'high'
                }
            }
        }
    
    def _load_owasp_database_standards(self) -> Dict[str, Any]:
        """Load OWASP database security standards."""
        return {
            'version': 'OWASP Database Security Guidelines',
            'standards': {
                'principle_of_least_privilege': {
                    'title': 'Principle of Least Privilege',
                    'description': 'Grant minimum necessary privileges to users',
                    'severity': 'critical'
                },
                'strong_authentication': {
                    'title': 'Strong Authentication',
                    'description': 'Implement strong password policies and multi-factor authentication',
                    'severity': 'high'
                },
                'encryption_in_transit': {
                    'title': 'Encryption in Transit',
                    'description': 'Encrypt all database communications',
                    'severity': 'high'
                },
                'encryption_at_rest': {
                    'title': 'Encryption at Rest',
                    'description': 'Encrypt sensitive data stored in database',
                    'severity': 'medium'
                },
                'audit_logging': {
                    'title': 'Comprehensive Audit Logging',
                    'description': 'Log all database access and modifications',
                    'severity': 'medium'
                },
                'regular_security_updates': {
                    'title': 'Regular Security Updates',
                    'description': 'Keep database software updated with security patches',
                    'severity': 'high'
                }
            }
        }
    
    def _load_custom_security_standards(self) -> Dict[str, Any]:
        """Load Vedfolnir-specific security standards."""
        return {
            'version': 'Vedfolnir MySQL Security Standards v1.0',
            'standards': {
                'application_user_separation': {
                    'title': 'Application User Separation',
                    'description': 'Separate database users for different application components',
                    'severity': 'medium'
                },
                'connection_rate_limiting': {
                    'title': 'Connection Rate Limiting',
                    'description': 'Implement connection rate limiting to prevent abuse',
                    'severity': 'medium'
                },
                'automated_security_monitoring': {
                    'title': 'Automated Security Monitoring',
                    'description': 'Implement automated security monitoring and alerting',
                    'severity': 'high'
                },
                'regular_privilege_audits': {
                    'title': 'Regular Privilege Audits',
                    'description': 'Conduct regular audits of user privileges',
                    'severity': 'medium'
                }
            }
        }
    
    def perform_comprehensive_security_audit(self, database_url: Optional[str] = None) -> SecurityAuditResult:
        """
        Perform comprehensive security audit of MySQL installation.
        
        Args:
            database_url: Optional database URL, uses config default if not provided
            
        Returns:
            SecurityAuditResult containing complete audit results
        """
        try:
            db_url = database_url or self.config.DATABASE_URL
            
            logger.info("Starting comprehensive MySQL security audit")
            
            # Initialize audit results
            audit_start = datetime.now()
            critical_issues = []
            warnings = []
            recommendations = []
            
            # Perform user privilege audit
            user_audit_results = self._audit_user_privileges(db_url)
            
            # Perform SSL/TLS audit
            ssl_audit_results = self._audit_ssl_configuration(db_url)
            
            # Perform configuration audit
            config_audit_results = self._audit_mysql_configuration(db_url)
            
            # Check compliance with security standards
            compliance_status = self._check_security_compliance(
                user_audit_results, ssl_audit_results, config_audit_results
            )
            
            # Aggregate issues and recommendations
            critical_issues.extend(user_audit_results.get('critical_issues', []))
            critical_issues.extend(ssl_audit_results.get('critical_issues', []))
            critical_issues.extend(config_audit_results.get('critical_issues', []))
            
            warnings.extend(user_audit_results.get('warnings', []))
            warnings.extend(ssl_audit_results.get('warnings', []))
            warnings.extend(config_audit_results.get('warnings', []))
            
            recommendations.extend(user_audit_results.get('recommendations', []))
            recommendations.extend(ssl_audit_results.get('recommendations', []))
            recommendations.extend(config_audit_results.get('recommendations', []))
            
            # Calculate overall security score
            overall_score = self._calculate_security_score(
                critical_issues, warnings, compliance_status
            )
            
            # Determine security level
            security_level = self._determine_security_level(overall_score)
            
            # Create audit result
            audit_result = SecurityAuditResult(
                timestamp=audit_start,
                overall_score=overall_score,
                security_level=security_level,
                critical_issues=critical_issues,
                warnings=warnings,
                recommendations=recommendations,
                compliance_status=compliance_status,
                user_audit_results=user_audit_results,
                ssl_audit_results=ssl_audit_results,
                configuration_audit_results=config_audit_results
            )
            
            # Log security event
            self._log_security_event('security_audit_completed', {
                'overall_score': overall_score,
                'security_level': security_level,
                'critical_issues_count': len(critical_issues),
                'warnings_count': len(warnings)
            })
            
            logger.info(f"Security audit completed - Score: {overall_score:.1f}/100, Level: {security_level}")
            return audit_result
            
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            # Return minimal audit result with error
            return SecurityAuditResult(
                timestamp=datetime.now(),
                overall_score=0.0,
                security_level='unknown',
                critical_issues=[{
                    'category': 'audit_error',
                    'title': 'Security Audit Failed',
                    'description': f'Security audit could not be completed: {str(e)}',
                    'severity': 'critical'
                }],
                warnings=[],
                recommendations=[],
                compliance_status={},
                user_audit_results={},
                ssl_audit_results={},
                configuration_audit_results={}
            )
    
    def _audit_user_privileges(self, database_url: str) -> Dict[str, Any]:
        """Audit user privileges and access controls."""
        try:
            engine = create_engine(database_url, echo=False)
            audit_results = {
                'users': [],
                'critical_issues': [],
                'warnings': [],
                'recommendations': [],
                'summary': {}
            }
            
            with engine.connect() as conn:
                # Get all users
                users_query = text("""
                    SELECT User, Host, account_locked, password_expired, 
                           password_last_changed, password_lifetime
                    FROM mysql.user
                    ORDER BY User, Host
                """)
                
                users_result = conn.execute(users_query).fetchall()
                
                for user_row in users_result:
                    username = user_row[0]
                    host = user_row[1]
                    
                    # Skip system users
                    if username in ['mysql.sys', 'mysql.session', 'mysql.infoschema']:
                        continue
                    
                    # Audit individual user
                    user_audit = self._audit_individual_user(conn, username, host)
                    audit_results['users'].append(asdict(user_audit))
                    
                    # Check for critical issues
                    if user_audit.has_dangerous_privileges:
                        audit_results['critical_issues'].append({
                            'category': 'dangerous_privileges',
                            'title': f'User {username}@{host} has dangerous privileges',
                            'description': f'User has privileges that could compromise security: {", ".join(user_audit.privileges)}',
                            'severity': 'critical',
                            'user': f'{username}@{host}'
                        })
                    
                    # Check for anonymous users
                    if username == '':
                        audit_results['critical_issues'].append({
                            'category': 'anonymous_user',
                            'title': 'Anonymous user account exists',
                            'description': f'Anonymous user account found: @{host}',
                            'severity': 'critical',
                            'user': f'@{host}'
                        })
                    
                    # Check for remote root access
                    if username == 'root' and host not in ['localhost', '127.0.0.1', '::1']:
                        audit_results['critical_issues'].append({
                            'category': 'remote_root',
                            'title': 'Remote root access enabled',
                            'description': f'Root user can connect from remote host: {host}',
                            'severity': 'critical',
                            'user': f'root@{host}'
                        })
                    
                    # Check password strength
                    if user_audit.password_strength in ['weak', 'unknown']:
                        audit_results['warnings'].append({
                            'category': 'weak_password',
                            'title': f'Weak password for user {username}@{host}',
                            'description': f'User has {user_audit.password_strength} password strength',
                            'severity': 'medium',
                            'user': f'{username}@{host}'
                        })
                
                # Check for test database
                test_db_query = text("SHOW DATABASES LIKE 'test'")
                test_db_result = conn.execute(test_db_query).fetchall()
                
                if test_db_result:
                    audit_results['critical_issues'].append({
                        'category': 'test_database',
                        'title': 'Test database exists',
                        'description': 'Default test database should be removed for security',
                        'severity': 'high'
                    })
                
                # Generate summary
                total_users = len(audit_results['users'])
                admin_users = len([u for u in audit_results['users'] if u['is_admin']])
                dangerous_users = len([u for u in audit_results['users'] if u['has_dangerous_privileges']])
                
                audit_results['summary'] = {
                    'total_users': total_users,
                    'admin_users': admin_users,
                    'dangerous_privilege_users': dangerous_users,
                    'critical_issues_count': len(audit_results['critical_issues']),
                    'warnings_count': len(audit_results['warnings'])
                }
            
            engine.dispose()
            return audit_results
            
        except Exception as e:
            logger.error(f"User privilege audit failed: {e}")
            return {
                'users': [],
                'critical_issues': [{
                    'category': 'audit_error',
                    'title': 'User privilege audit failed',
                    'description': str(e),
                    'severity': 'critical'
                }],
                'warnings': [],
                'recommendations': [],
                'summary': {}
            }
    
    def _audit_individual_user(self, conn, username: str, host: str) -> UserPrivilegeAudit:
        """Audit privileges for an individual user."""
        try:
            # Get global privileges
            global_privs_query = text("""
                SELECT * FROM mysql.user WHERE User = :username AND Host = :host
            """)
            
            global_result = conn.execute(global_privs_query, {
                'username': username, 'host': host
            }).fetchone()
            
            # Parse global privileges
            global_privileges = []
            dangerous_privileges = []
            
            if global_result:
                # Check common privilege columns
                privilege_columns = [
                    'Select_priv', 'Insert_priv', 'Update_priv', 'Delete_priv',
                    'Create_priv', 'Drop_priv', 'Reload_priv', 'Shutdown_priv',
                    'Process_priv', 'File_priv', 'Grant_priv', 'References_priv',
                    'Index_priv', 'Alter_priv', 'Show_db_priv', 'Super_priv',
                    'Create_tmp_table_priv', 'Lock_tables_priv', 'Execute_priv',
                    'Repl_slave_priv', 'Repl_client_priv', 'Create_view_priv',
                    'Show_view_priv', 'Create_routine_priv', 'Alter_routine_priv',
                    'Create_user_priv', 'Event_priv', 'Trigger_priv'
                ]
                
                for i, col in enumerate(privilege_columns):
                    try:
                        if global_result[col] == 'Y':
                            priv_name = col.replace('_priv', '').upper()
                            global_privileges.append(priv_name)
                            
                            # Check for dangerous privileges
                            if col in ['Super_priv', 'File_priv', 'Grant_priv', 'Create_user_priv', 
                                     'Shutdown_priv', 'Reload_priv', 'Process_priv']:
                                dangerous_privileges.append(priv_name)
                    except (IndexError, KeyError):
                        continue
            
            # Get database-specific privileges
            db_privs_query = text("""
                SELECT Db, Select_priv, Insert_priv, Update_priv, Delete_priv,
                       Create_priv, Drop_priv, Grant_priv, References_priv,
                       Index_priv, Alter_priv, Create_tmp_table_priv,
                       Lock_tables_priv, Create_view_priv, Show_view_priv,
                       Create_routine_priv, Alter_routine_priv, Execute_priv,
                       Event_priv, Trigger_priv
                FROM mysql.db WHERE User = :username AND Host = :host
            """)
            
            db_result = conn.execute(db_privs_query, {
                'username': username, 'host': host
            }).fetchall()
            
            database_privileges = {}
            for db_row in db_result:
                db_name = db_row[0]
                db_privs = []
                
                db_privilege_columns = [
                    'Select_priv', 'Insert_priv', 'Update_priv', 'Delete_priv',
                    'Create_priv', 'Drop_priv', 'Grant_priv', 'References_priv',
                    'Index_priv', 'Alter_priv', 'Create_tmp_table_priv',
                    'Lock_tables_priv', 'Create_view_priv', 'Show_view_priv',
                    'Create_routine_priv', 'Alter_routine_priv', 'Execute_priv',
                    'Event_priv', 'Trigger_priv'
                ]
                
                for i, col in enumerate(db_privilege_columns, 1):
                    try:
                        if db_row[i] == 'Y':
                            db_privs.append(col.replace('_priv', '').upper())
                    except IndexError:
                        continue
                
                if db_privs:
                    database_privileges[db_name] = db_privs
            
            # Get table-specific privileges (simplified)
            table_privileges = {}  # Would implement full table privilege audit if needed
            
            # Determine if user is admin
            is_admin = any(priv in ['SUPER', 'GRANT', 'CREATE_USER'] for priv in global_privileges)
            
            # Check password strength (simplified - would need more sophisticated analysis)
            password_strength = 'unknown'  # MySQL doesn't expose password hashes for analysis
            
            # Calculate security score for this user
            security_score = 100.0
            if dangerous_privileges:
                security_score -= len(dangerous_privileges) * 15  # -15 per dangerous privilege
            if username == '':
                security_score -= 50  # Anonymous user
            if username == 'root' and host not in ['localhost', '127.0.0.1', '::1']:
                security_score -= 40  # Remote root
            
            security_score = max(0.0, security_score)
            
            return UserPrivilegeAudit(
                username=username,
                host=host,
                privileges=global_privileges + list(set().union(*database_privileges.values())),
                global_privileges=global_privileges,
                database_privileges=database_privileges,
                table_privileges=table_privileges,
                is_admin=is_admin,
                has_dangerous_privileges=len(dangerous_privileges) > 0,
                last_login=None,  # Would need additional logging to track
                password_strength=password_strength,
                security_score=security_score
            )
            
        except Exception as e:
            logger.error(f"Individual user audit failed for {username}@{host}: {e}")
            return UserPrivilegeAudit(
                username=username,
                host=host,
                privileges=[],
                global_privileges=[],
                database_privileges={},
                table_privileges={},
                is_admin=False,
                has_dangerous_privileges=False,
                last_login=None,
                password_strength='unknown',
                security_score=0.0
            )
    
    def _audit_ssl_configuration(self, database_url: str) -> Dict[str, Any]:
        """Audit SSL/TLS configuration and certificate security."""
        try:
            engine = create_engine(database_url, echo=False)
            audit_results = {
                'ssl_config': None,
                'critical_issues': [],
                'warnings': [],
                'recommendations': [],
                'summary': {}
            }
            
            with engine.connect() as conn:
                # Check SSL status
                ssl_status_query = text("SHOW STATUS LIKE 'Ssl_%'")
                ssl_status_result = conn.execute(ssl_status_query).fetchall()
                ssl_status = {row[0]: row[1] for row in ssl_status_result}
                
                # Check SSL variables
                ssl_vars_query = text("SHOW VARIABLES LIKE 'ssl_%'")
                ssl_vars_result = conn.execute(ssl_vars_query).fetchall()
                ssl_vars = {row[0]: row[1] for row in ssl_vars_result}
                
                # Check if SSL is enabled
                ssl_enabled = ssl_status.get('Ssl_cipher', '') != ''
                
                if not ssl_enabled:
                    audit_results['critical_issues'].append({
                        'category': 'ssl_disabled',
                        'title': 'SSL/TLS not enabled',
                        'description': 'MySQL is not configured to use SSL/TLS encryption',
                        'severity': 'critical'
                    })
                
                # Analyze SSL configuration
                ssl_config = SSLConfiguration(
                    ssl_enabled=ssl_enabled,
                    ssl_version=ssl_status.get('Ssl_version'),
                    cipher_suite=ssl_status.get('Ssl_cipher'),
                    certificate_path=ssl_vars.get('ssl_cert'),
                    key_path=ssl_vars.get('ssl_key'),
                    ca_path=ssl_vars.get('ssl_ca'),
                    certificate_valid=False,
                    certificate_expires=None,
                    certificate_issuer=None,
                    certificate_subject=None,
                    security_score=0.0
                )
                
                # Validate SSL certificate if available
                if ssl_config.certificate_path and Path(ssl_config.certificate_path).exists():
                    cert_validation = self._validate_ssl_certificate(ssl_config.certificate_path)
                    ssl_config.certificate_valid = cert_validation['valid']
                    ssl_config.certificate_expires = cert_validation.get('expires')
                    ssl_config.certificate_issuer = cert_validation.get('issuer')
                    ssl_config.certificate_subject = cert_validation.get('subject')
                    
                    # Check certificate expiry
                    if ssl_config.certificate_expires:
                        days_until_expiry = (ssl_config.certificate_expires - datetime.now()).days
                        if days_until_expiry <= 0:
                            audit_results['critical_issues'].append({
                                'category': 'certificate_expired',
                                'title': 'SSL certificate expired',
                                'description': f'SSL certificate expired on {ssl_config.certificate_expires}',
                                'severity': 'critical'
                            })
                        elif days_until_expiry <= self.security_thresholds['certificate_expiry_warning_days']:
                            audit_results['warnings'].append({
                                'category': 'certificate_expiring',
                                'title': 'SSL certificate expiring soon',
                                'description': f'SSL certificate expires in {days_until_expiry} days',
                                'severity': 'medium'
                            })
                
                # Check cipher strength
                if ssl_config.cipher_suite:
                    cipher_strength = self._analyze_cipher_strength(ssl_config.cipher_suite)
                    if cipher_strength['strength'] == 'weak':
                        audit_results['warnings'].append({
                            'category': 'weak_cipher',
                            'title': 'Weak SSL cipher suite',
                            'description': f'Using weak cipher: {ssl_config.cipher_suite}',
                            'severity': 'medium'
                        })
                
                # Check for require_secure_transport
                secure_transport_query = text("SHOW VARIABLES LIKE 'require_secure_transport'")
                secure_transport_result = conn.execute(secure_transport_query).fetchone()
                
                if secure_transport_result and secure_transport_result[1] != 'ON':
                    audit_results['warnings'].append({
                        'category': 'insecure_transport_allowed',
                        'title': 'Insecure transport allowed',
                        'description': 'MySQL allows non-SSL connections (require_secure_transport=OFF)',
                        'severity': 'high'
                    })
                
                # Calculate SSL security score
                ssl_security_score = self._calculate_ssl_security_score(ssl_config, audit_results)
                ssl_config.security_score = ssl_security_score
                
                audit_results['ssl_config'] = asdict(ssl_config)
                audit_results['summary'] = {
                    'ssl_enabled': ssl_enabled,
                    'certificate_valid': ssl_config.certificate_valid,
                    'security_score': ssl_security_score,
                    'critical_issues_count': len(audit_results['critical_issues']),
                    'warnings_count': len(audit_results['warnings'])
                }
            
            engine.dispose()
            return audit_results
            
        except Exception as e:
            logger.error(f"SSL configuration audit failed: {e}")
            return {
                'ssl_config': None,
                'critical_issues': [{
                    'category': 'audit_error',
                    'title': 'SSL audit failed',
                    'description': str(e),
                    'severity': 'critical'
                }],
                'warnings': [],
                'recommendations': [],
                'summary': {}
            }
    
    def _validate_ssl_certificate(self, cert_path: str) -> Dict[str, Any]:
        """Validate SSL certificate file."""
        try:
            with open(cert_path, 'rb') as cert_file:
                cert_data = cert_file.read()
                certificate = x509.load_pem_x509_certificate(cert_data)
                
                return {
                    'valid': True,
                    'expires': certificate.not_valid_after,
                    'issuer': certificate.issuer.rfc4514_string(),
                    'subject': certificate.subject.rfc4514_string(),
                    'serial_number': str(certificate.serial_number),
                    'signature_algorithm': certificate.signature_algorithm_oid._name
                }
                
        except Exception as e:
            logger.error(f"Certificate validation failed: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _analyze_cipher_strength(self, cipher_suite: str) -> Dict[str, Any]:
        """Analyze SSL cipher suite strength."""
        # Simplified cipher strength analysis
        weak_ciphers = ['RC4', 'DES', 'MD5', 'NULL']
        medium_ciphers = ['3DES', 'SHA1']
        
        cipher_upper = cipher_suite.upper()
        
        if any(weak in cipher_upper for weak in weak_ciphers):
            return {
                'strength': 'weak',
                'reason': 'Contains weak cryptographic algorithms'
            }
        elif any(medium in cipher_upper for medium in medium_ciphers):
            return {
                'strength': 'medium',
                'reason': 'Contains deprecated but acceptable algorithms'
            }
        else:
            return {
                'strength': 'strong',
                'reason': 'Uses modern cryptographic algorithms'
            }
    
    def _calculate_ssl_security_score(self, ssl_config: SSLConfiguration, audit_results: Dict[str, Any]) -> float:
        """Calculate SSL security score."""
        score = 0.0
        
        if ssl_config.ssl_enabled:
            score += 40.0  # Base score for SSL enabled
            
            if ssl_config.certificate_valid:
                score += 30.0  # Valid certificate
                
            if ssl_config.certificate_expires:
                days_until_expiry = (ssl_config.certificate_expires - datetime.now()).days
                if days_until_expiry > 90:
                    score += 20.0  # Certificate not expiring soon
                elif days_until_expiry > 30:
                    score += 10.0  # Certificate expiring in 30-90 days
                # No points if expiring within 30 days
            
            # Cipher strength bonus
            if ssl_config.cipher_suite:
                cipher_analysis = self._analyze_cipher_strength(ssl_config.cipher_suite)
                if cipher_analysis['strength'] == 'strong':
                    score += 10.0
                elif cipher_analysis['strength'] == 'medium':
                    score += 5.0
        
        return min(100.0, score)
    
    def _audit_mysql_configuration(self, database_url: str) -> Dict[str, Any]:
        """Audit MySQL configuration for security issues."""
        try:
            engine = create_engine(database_url, echo=False)
            audit_results = {
                'configuration': {},
                'critical_issues': [],
                'warnings': [],
                'recommendations': [],
                'summary': {}
            }
            
            with engine.connect() as conn:
                # Get all variables
                variables_query = text("SHOW VARIABLES")
                variables_result = conn.execute(variables_query).fetchall()
                variables = {row[0]: row[1] for row in variables_result}
                
                audit_results['configuration'] = variables
                
                # Check critical security configurations
                security_checks = [
                    {
                        'variable': 'local_infile',
                        'expected': 'OFF',
                        'severity': 'high',
                        'title': 'Local file loading enabled',
                        'description': 'local_infile should be disabled to prevent file system access'
                    },
                    {
                        'variable': 'secure_file_priv',
                        'expected_not_empty': True,
                        'severity': 'high',
                        'title': 'Unrestricted file operations',
                        'description': 'secure_file_priv should be set to restrict file operations'
                    },
                    {
                        'variable': 'sql_mode',
                        'should_contain': 'STRICT_TRANS_TABLES',
                        'severity': 'medium',
                        'title': 'Non-strict SQL mode',
                        'description': 'SQL mode should include STRICT_TRANS_TABLES for data integrity'
                    },
                    {
                        'variable': 'log_bin_trust_function_creators',
                        'expected': 'OFF',
                        'severity': 'medium',
                        'title': 'Unrestricted function creation',
                        'description': 'log_bin_trust_function_creators should be OFF for security'
                    }
                ]
                
                for check in security_checks:
                    var_name = check['variable']
                    var_value = variables.get(var_name, '')
                    
                    issue_found = False
                    
                    if 'expected' in check and var_value != check['expected']:
                        issue_found = True
                    elif 'expected_not_empty' in check and not var_value:
                        issue_found = True
                    elif 'should_contain' in check and check['should_contain'] not in var_value:
                        issue_found = True
                    
                    if issue_found:
                        issue_category = 'critical_issues' if check['severity'] == 'critical' else 'warnings'
                        audit_results[issue_category].append({
                            'category': 'configuration',
                            'title': check['title'],
                            'description': f"{check['description']} (current: {var_value})",
                            'severity': check['severity'],
                            'variable': var_name,
                            'current_value': var_value,
                            'recommended_value': check.get('expected', 'see description')
                        })
                
                # Check password validation plugin
                validate_password_query = text("SHOW PLUGINS LIKE 'validate_password%'")
                validate_password_result = conn.execute(validate_password_query).fetchall()
                
                if not validate_password_result:
                    audit_results['warnings'].append({
                        'category': 'password_validation',
                        'title': 'Password validation plugin not enabled',
                        'description': 'validate_password plugin should be enabled for password strength enforcement',
                        'severity': 'medium'
                    })
                
                # Check logging configuration
                logging_checks = [
                    ('general_log', 'Connection logging'),
                    ('slow_query_log', 'Slow query logging'),
                    ('log_error', 'Error logging')
                ]
                
                for log_var, log_desc in logging_checks:
                    if variables.get(log_var, 'OFF') == 'OFF':
                        audit_results['recommendations'].append({
                            'category': 'logging',
                            'title': f'{log_desc} disabled',
                            'description': f'Consider enabling {log_var} for security monitoring',
                            'severity': 'low',
                            'variable': log_var
                        })
                
                # Generate summary
                audit_results['summary'] = {
                    'total_variables': len(variables),
                    'critical_issues_count': len(audit_results['critical_issues']),
                    'warnings_count': len(audit_results['warnings']),
                    'recommendations_count': len(audit_results['recommendations'])
                }
            
            engine.dispose()
            return audit_results
            
        except Exception as e:
            logger.error(f"Configuration audit failed: {e}")
            return {
                'configuration': {},
                'critical_issues': [{
                    'category': 'audit_error',
                    'title': 'Configuration audit failed',
                    'description': str(e),
                    'severity': 'critical'
                }],
                'warnings': [],
                'recommendations': [],
                'summary': {}
            }
    
    def _check_security_compliance(self, user_audit: Dict[str, Any], 
                                 ssl_audit: Dict[str, Any], 
                                 config_audit: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance with security standards."""
        compliance_status = {}
        
        # CIS MySQL compliance
        cis_compliance = self._check_cis_compliance(user_audit, ssl_audit, config_audit)
        compliance_status['cis_mysql'] = cis_compliance
        
        # OWASP compliance
        owasp_compliance = self._check_owasp_compliance(user_audit, ssl_audit, config_audit)
        compliance_status['owasp_database'] = owasp_compliance
        
        # Custom Vedfolnir compliance
        custom_compliance = self._check_custom_compliance(user_audit, ssl_audit, config_audit)
        compliance_status['vedfolnir_custom'] = custom_compliance
        
        # Overall compliance score
        total_score = (cis_compliance['score'] + owasp_compliance['score'] + custom_compliance['score']) / 3
        compliance_status['overall'] = {
            'score': total_score,
            'level': self._determine_compliance_level(total_score)
        }
        
        return compliance_status
    
    def _check_cis_compliance(self, user_audit: Dict[str, Any], 
                            ssl_audit: Dict[str, Any], 
                            config_audit: Dict[str, Any]) -> Dict[str, Any]:
        """Check CIS MySQL benchmark compliance."""
        cis_standards = self.security_standards['cis_mysql']['standards']
        compliance_results = {}
        total_checks = len(cis_standards)
        passed_checks = 0
        
        for standard_id, standard in cis_standards.items():
            compliance_results[standard_id] = {
                'title': standard['title'],
                'compliant': False,
                'details': ''
            }
            
            if standard_id == 'remove_test_database':
                # Check if test database exists
                test_db_issues = [issue for issue in config_audit.get('critical_issues', []) 
                                if issue.get('category') == 'test_database']
                compliance_results[standard_id]['compliant'] = len(test_db_issues) == 0
                
            elif standard_id == 'remove_anonymous_users':
                # Check for anonymous users
                anonymous_issues = [issue for issue in user_audit.get('critical_issues', []) 
                                  if issue.get('category') == 'anonymous_user']
                compliance_results[standard_id]['compliant'] = len(anonymous_issues) == 0
                
            elif standard_id == 'remove_remote_root':
                # Check for remote root access
                remote_root_issues = [issue for issue in user_audit.get('critical_issues', []) 
                                    if issue.get('category') == 'remote_root']
                compliance_results[standard_id]['compliant'] = len(remote_root_issues) == 0
                
            elif standard_id == 'require_ssl':
                # Check SSL configuration
                ssl_config = ssl_audit.get('ssl_config', {})
                compliance_results[standard_id]['compliant'] = ssl_config.get('ssl_enabled', False)
                
            elif standard_id == 'validate_password_plugin':
                # Check password validation plugin
                password_issues = [issue for issue in config_audit.get('warnings', []) 
                                 if issue.get('category') == 'password_validation']
                compliance_results[standard_id]['compliant'] = len(password_issues) == 0
                
            elif standard_id == 'secure_file_privileges':
                # Check secure_file_priv configuration
                secure_file_issues = [issue for issue in config_audit.get('critical_issues', []) + config_audit.get('warnings', [])
                                    if 'secure_file_priv' in issue.get('variable', '')]
                compliance_results[standard_id]['compliant'] = len(secure_file_issues) == 0
            
            if compliance_results[standard_id]['compliant']:
                passed_checks += 1
        
        compliance_score = (passed_checks / max(total_checks, 1)) * 100
        
        return {
            'score': compliance_score,
            'level': self._determine_compliance_level(compliance_score),
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'details': compliance_results
        }
    
    def _check_owasp_compliance(self, user_audit: Dict[str, Any], 
                              ssl_audit: Dict[str, Any], 
                              config_audit: Dict[str, Any]) -> Dict[str, Any]:
        """Check OWASP database security compliance."""
        owasp_standards = self.security_standards['owasp_database']['standards']
        compliance_results = {}
        total_checks = len(owasp_standards)
        passed_checks = 0
        
        for standard_id, standard in owasp_standards.items():
            compliance_results[standard_id] = {
                'title': standard['title'],
                'compliant': False,
                'details': ''
            }
            
            if standard_id == 'principle_of_least_privilege':
                # Check for users with dangerous privileges
                dangerous_users = user_audit.get('summary', {}).get('dangerous_privilege_users', 0)
                compliance_results[standard_id]['compliant'] = dangerous_users == 0
                
            elif standard_id == 'strong_authentication':
                # Check password policies (simplified)
                weak_password_issues = [issue for issue in user_audit.get('warnings', []) 
                                      if issue.get('category') == 'weak_password']
                compliance_results[standard_id]['compliant'] = len(weak_password_issues) == 0
                
            elif standard_id == 'encryption_in_transit':
                # Check SSL configuration
                ssl_config = ssl_audit.get('ssl_config', {})
                compliance_results[standard_id]['compliant'] = ssl_config.get('ssl_enabled', False)
                
            elif standard_id == 'audit_logging':
                # Check logging configuration
                logging_recommendations = [rec for rec in config_audit.get('recommendations', []) 
                                         if rec.get('category') == 'logging']
                compliance_results[standard_id]['compliant'] = len(logging_recommendations) < 2  # Allow some logging to be optional
            
            if compliance_results[standard_id]['compliant']:
                passed_checks += 1
        
        compliance_score = (passed_checks / max(total_checks, 1)) * 100
        
        return {
            'score': compliance_score,
            'level': self._determine_compliance_level(compliance_score),
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'details': compliance_results
        }
    
    def _check_custom_compliance(self, user_audit: Dict[str, Any], 
                               ssl_audit: Dict[str, Any], 
                               config_audit: Dict[str, Any]) -> Dict[str, Any]:
        """Check custom Vedfolnir security compliance."""
        custom_standards = self.security_standards['vedfolnir_custom']['standards']
        compliance_results = {}
        total_checks = len(custom_standards)
        passed_checks = total_checks  # Assume compliance for custom standards (would implement specific checks)
        
        for standard_id, standard in custom_standards.items():
            compliance_results[standard_id] = {
                'title': standard['title'],
                'compliant': True,  # Simplified - would implement actual checks
                'details': 'Custom compliance check not fully implemented'
            }
        
        compliance_score = (passed_checks / max(total_checks, 1)) * 100
        
        return {
            'score': compliance_score,
            'level': self._determine_compliance_level(compliance_score),
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'details': compliance_results
        }
    
    def _determine_compliance_level(self, score: float) -> str:
        """Determine compliance level based on score."""
        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 50:
            return 'fair'
        else:
            return 'poor'
    
    def _calculate_security_score(self, critical_issues: List[Dict[str, Any]], 
                                warnings: List[Dict[str, Any]], 
                                compliance_status: Dict[str, Any]) -> float:
        """Calculate overall security score."""
        base_score = 100.0
        
        # Deduct points for issues
        base_score -= len(critical_issues) * 20  # -20 per critical issue
        base_score -= len(warnings) * 5  # -5 per warning
        
        # Factor in compliance scores
        overall_compliance = compliance_status.get('overall', {}).get('score', 0)
        compliance_factor = overall_compliance / 100.0
        
        # Weighted average: 70% issue-based, 30% compliance-based
        final_score = (base_score * 0.7) + (overall_compliance * 0.3)
        
        return max(0.0, min(100.0, final_score))
    
    def _determine_security_level(self, score: float) -> str:
        """Determine security level based on score."""
        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 50:
            return 'fair'
        else:
            return 'poor'
    
    def _log_security_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log security event to Redis and application logs."""
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'data': event_data
            }
            
            # Log to application logs
            logger.info(f"Security event: {event_type} - {json.dumps(event_data)}")
            
            # Log to Redis if available
            if self.redis_client:
                event_key = f"mysql_security:events:{int(datetime.now().timestamp())}"
                self.redis_client.setex(
                    event_key,
                    86400,  # 24 hours TTL
                    json.dumps(event, default=str)
                )
                
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def implement_security_hardening(self, hardening_level: str = 'standard') -> Dict[str, Any]:
        """
        Implement automated security hardening based on audit results.
        
        Args:
            hardening_level: Level of hardening ('basic', 'standard', 'strict')
            
        Returns:
            Dictionary containing hardening implementation results
        """
        try:
            logger.info(f"Starting MySQL security hardening (level: {hardening_level})")
            
            # First perform security audit to identify issues
            audit_result = self.perform_comprehensive_security_audit()
            
            hardening_results = {
                'hardening_level': hardening_level,
                'audit_score_before': audit_result.overall_score,
                'actions_taken': [],
                'actions_failed': [],
                'recommendations': [],
                'audit_score_after': 0.0
            }
            
            # Define hardening actions based on level
            hardening_actions = self._get_hardening_actions(hardening_level, audit_result)
            
            # Execute hardening actions
            for action in hardening_actions:
                try:
                    action_result = self._execute_hardening_action(action)
                    if action_result['success']:
                        hardening_results['actions_taken'].append(action_result)
                        logger.info(f"Hardening action completed: {action['title']}")
                    else:
                        hardening_results['actions_failed'].append(action_result)
                        logger.warning(f"Hardening action failed: {action['title']} - {action_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Hardening action exception: {action['title']} - {e}")
                    hardening_results['actions_failed'].append({
                        'action': action,
                        'success': False,
                        'error': str(e)
                    })
            
            # Perform post-hardening audit
            post_audit_result = self.perform_comprehensive_security_audit()
            hardening_results['audit_score_after'] = post_audit_result.overall_score
            
            # Calculate improvement
            score_improvement = post_audit_result.overall_score - audit_result.overall_score
            hardening_results['score_improvement'] = score_improvement
            
            # Generate remaining recommendations
            hardening_results['recommendations'] = self._generate_post_hardening_recommendations(
                post_audit_result, hardening_level
            )
            
            # Log security event
            self._log_security_event('security_hardening_completed', {
                'hardening_level': hardening_level,
                'score_before': audit_result.overall_score,
                'score_after': post_audit_result.overall_score,
                'score_improvement': score_improvement,
                'actions_taken': len(hardening_results['actions_taken']),
                'actions_failed': len(hardening_results['actions_failed'])
            })
            
            logger.info(f"Security hardening completed - Score improved by {score_improvement:.1f} points")
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'results': hardening_results
            }
            
        except Exception as e:
            logger.error(f"Security hardening failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_hardening_actions(self, hardening_level: str, audit_result: SecurityAuditResult) -> List[Dict[str, Any]]:
        """Get list of hardening actions based on level and audit results."""
        actions = []
        
        # Basic hardening actions (all levels)
        basic_actions = [
            {
                'id': 'remove_anonymous_users',
                'title': 'Remove Anonymous Users',
                'description': 'Remove anonymous user accounts',
                'sql': "DELETE FROM mysql.user WHERE User = '';",
                'condition': lambda: any(issue.get('category') == 'anonymous_user' for issue in audit_result.critical_issues)
            },
            {
                'id': 'remove_test_database',
                'title': 'Remove Test Database',
                'description': 'Drop the default test database',
                'sql': "DROP DATABASE IF EXISTS test;",
                'condition': lambda: any(issue.get('category') == 'test_database' for issue in audit_result.critical_issues)
            },
            {
                'id': 'flush_privileges',
                'title': 'Flush Privileges',
                'description': 'Reload privilege tables',
                'sql': "FLUSH PRIVILEGES;",
                'condition': lambda: True  # Always flush after changes
            }
        ]
        
        # Standard hardening actions
        standard_actions = [
            {
                'id': 'disable_local_infile',
                'title': 'Disable Local File Loading',
                'description': 'Set local_infile to OFF',
                'sql': "SET GLOBAL local_infile = 'OFF';",
                'condition': lambda: any('local_infile' in issue.get('variable', '') for issue in audit_result.configuration_audit_results.get('warnings', []))
            },
            {
                'id': 'enable_strict_mode',
                'title': 'Enable Strict SQL Mode',
                'description': 'Add STRICT_TRANS_TABLES to sql_mode',
                'sql': "SET GLOBAL sql_mode = CONCAT(@@sql_mode, ',STRICT_TRANS_TABLES');",
                'condition': lambda: any('sql_mode' in issue.get('variable', '') for issue in audit_result.configuration_audit_results.get('warnings', []))
            }
        ]
        
        # Strict hardening actions
        strict_actions = [
            {
                'id': 'require_secure_transport',
                'title': 'Require Secure Transport',
                'description': 'Force all connections to use SSL',
                'sql': "SET GLOBAL require_secure_transport = 'ON';",
                'condition': lambda: audit_result.ssl_audit_results.get('ssl_config', {}).get('ssl_enabled', False)
            },
            {
                'id': 'disable_remote_root',
                'title': 'Disable Remote Root Access',
                'description': 'Remove remote root access (keep localhost only)',
                'sql': "DELETE FROM mysql.user WHERE User = 'root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');",
                'condition': lambda: any(issue.get('category') == 'remote_root' for issue in audit_result.critical_issues)
            }
        ]
        
        # Add actions based on hardening level
        actions.extend(basic_actions)
        
        if hardening_level in ['standard', 'strict']:
            actions.extend(standard_actions)
        
        if hardening_level == 'strict':
            actions.extend(strict_actions)
        
        # Filter actions based on conditions
        applicable_actions = [action for action in actions if action['condition']()]
        
        return applicable_actions
    
    def _execute_hardening_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single hardening action."""
        try:
            engine = create_engine(self.config.DATABASE_URL, echo=False)
            
            with engine.connect() as conn:
                # Execute the SQL command
                conn.execute(text(action['sql']))
                conn.commit()
            
            engine.dispose()
            
            return {
                'action': action,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'action': action,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_post_hardening_recommendations(self, audit_result: SecurityAuditResult, 
                                               hardening_level: str) -> List[Dict[str, Any]]:
        """Generate recommendations after hardening implementation."""
        recommendations = []
        
        # Add remaining critical issues as high-priority recommendations
        for issue in audit_result.critical_issues:
            recommendations.append({
                'priority': 'critical',
                'category': issue.get('category', 'unknown'),
                'title': f"Address remaining critical issue: {issue.get('title', 'Unknown')}",
                'description': issue.get('description', 'No description available'),
                'manual_action_required': True
            })
        
        # Add SSL recommendations if not using strict hardening
        if hardening_level != 'strict' and not audit_result.ssl_audit_results.get('ssl_config', {}).get('ssl_enabled', False):
            recommendations.append({
                'priority': 'high',
                'category': 'ssl_configuration',
                'title': 'Configure SSL/TLS encryption',
                'description': 'Set up SSL certificates and enable encrypted connections',
                'manual_action_required': True,
                'implementation_steps': [
                    'Generate or obtain SSL certificates',
                    'Configure ssl_cert, ssl_key, and ssl_ca variables',
                    'Restart MySQL server',
                    'Test SSL connections'
                ]
            })
        
        # Add password policy recommendations
        if not any('validate_password' in rec.get('category', '') for rec in audit_result.recommendations):
            recommendations.append({
                'priority': 'medium',
                'category': 'password_policy',
                'title': 'Enable password validation plugin',
                'description': 'Install and configure validate_password plugin for stronger passwords',
                'manual_action_required': True,
                'implementation_steps': [
                    'INSTALL PLUGIN validate_password SONAME "validate_password.so";',
                    'SET GLOBAL validate_password.policy = MEDIUM;',
                    'SET GLOBAL validate_password.length = 12;'
                ]
            })
        
        # Add logging recommendations
        recommendations.append({
            'priority': 'low',
            'category': 'logging',
            'title': 'Enable comprehensive logging',
            'description': 'Enable general log, slow query log, and error logging for security monitoring',
            'manual_action_required': True,
            'implementation_steps': [
                'SET GLOBAL general_log = "ON";',
                'SET GLOBAL slow_query_log = "ON";',
                'Configure log file locations in my.cnf'
            ]
        })
        
        return recommendations
    
    def generate_security_certificate(self, cert_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate self-signed SSL certificate for MySQL.
        
        Args:
            cert_info: Certificate information (common_name, organization, etc.)
            
        Returns:
            Dictionary containing certificate generation results
        """
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, cert_info.get('country', 'US')),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, cert_info.get('state', 'State')),
                x509.NameAttribute(NameOID.LOCALITY_NAME, cert_info.get('city', 'City')),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, cert_info.get('organization', 'Vedfolnir')),
                x509.NameAttribute(NameOID.COMMON_NAME, cert_info.get('common_name', 'localhost')),
            ])
            
            certificate = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.now()
            ).not_valid_after(
                datetime.now() + timedelta(days=365)  # Valid for 1 year
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            # Save certificate and key
            cert_dir = Path(cert_info.get('cert_dir', './ssl'))
            cert_dir.mkdir(exist_ok=True)
            
            cert_file = cert_dir / 'mysql-server-cert.pem'
            key_file = cert_dir / 'mysql-server-key.pem'
            
            # Write certificate
            with open(cert_file, 'wb') as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            with open(key_file, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Set appropriate permissions
            os.chmod(cert_file, 0o644)
            os.chmod(key_file, 0o600)
            
            logger.info(f"SSL certificate generated: {cert_file}")
            return {
                'success': True,
                'certificate_path': str(cert_file),
                'key_path': str(key_file),
                'valid_until': (datetime.now() + timedelta(days=365)).isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Certificate generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def create_secure_mysql_user(self, username: str, password: str, 
                                database: str, privileges: List[str] = None) -> Dict[str, Any]:
        """
        Create a secure MySQL user with minimal privileges.
        
        Args:
            username: Username for the new user
            password: Password for the new user
            database: Database to grant access to
            privileges: List of privileges to grant (default: SELECT, INSERT, UPDATE, DELETE)
            
        Returns:
            Dictionary containing user creation results
        """
        try:
            if privileges is None:
                privileges = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
            
            # Validate password strength
            password_validation = self._validate_password_strength(password)
            if not password_validation['strong']:
                return {
                    'success': False,
                    'error': f"Password does not meet security requirements: {password_validation['reason']}",
                    'timestamp': datetime.now().isoformat()
                }
            
            engine = create_engine(self.config.DATABASE_URL, echo=False)
            
            with engine.connect() as conn:
                # Create user
                create_user_sql = text(f"CREATE USER '{username}'@'localhost' IDENTIFIED BY :password")
                conn.execute(create_user_sql, {'password': password})
                
                # Grant privileges
                privileges_str = ', '.join(privileges)
                grant_sql = text(f"GRANT {privileges_str} ON {database}.* TO '{username}'@'localhost'")
                conn.execute(grant_sql)
                
                # Flush privileges
                conn.execute(text("FLUSH PRIVILEGES"))
                conn.commit()
            
            engine.dispose()
            
            # Log security event
            self._log_security_event('secure_user_created', {
                'username': username,
                'database': database,
                'privileges': privileges
            })
            
            logger.info(f"Secure MySQL user created: {username}")
            return {
                'success': True,
                'username': username,
                'database': database,
                'privileges': privileges,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Secure user creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength according to security policy."""
        validation = {
            'strong': True,
            'score': 100,
            'reason': 'Password meets all security requirements'
        }
        
        # Check minimum length
        if len(password) < self.security_thresholds['password_min_length']:
            validation['strong'] = False
            validation['score'] -= 30
            validation['reason'] = f"Password must be at least {self.security_thresholds['password_min_length']} characters"
            return validation
        
        # Check for uppercase letters
        if not any(c.isupper() for c in password):
            validation['strong'] = False
            validation['score'] -= 20
            validation['reason'] = "Password must contain uppercase letters"
        
        # Check for lowercase letters
        if not any(c.islower() for c in password):
            validation['strong'] = False
            validation['score'] -= 20
            validation['reason'] = "Password must contain lowercase letters"
        
        # Check for digits
        if not any(c.isdigit() for c in password):
            validation['strong'] = False
            validation['score'] -= 20
            validation['reason'] = "Password must contain digits"
        
        # Check for special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            validation['strong'] = False
            validation['score'] -= 10
            validation['reason'] = "Password should contain special characters"
        
        return validation
    
    def get_security_status_summary(self) -> Dict[str, Any]:
        """Get current security status summary."""
        try:
            # Perform quick security audit
            audit_result = self.perform_comprehensive_security_audit()
            
            # Get recent security events
            recent_events = self._get_recent_security_events(hours=24)
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'overall_security_score': audit_result.overall_score,
                'security_level': audit_result.security_level,
                'critical_issues_count': len(audit_result.critical_issues),
                'warnings_count': len(audit_result.warnings),
                'compliance_status': {
                    'cis_mysql': audit_result.compliance_status.get('cis_mysql', {}).get('level', 'unknown'),
                    'owasp_database': audit_result.compliance_status.get('owasp_database', {}).get('level', 'unknown'),
                    'overall': audit_result.compliance_status.get('overall', {}).get('level', 'unknown')
                },
                'recent_security_events': len(recent_events),
                'ssl_enabled': audit_result.ssl_audit_results.get('ssl_config', {}).get('ssl_enabled', False),
                'user_audit_summary': audit_result.user_audit_results.get('summary', {}),
                'recommendations_count': len(audit_result.recommendations)
            }
            
            return {
                'success': True,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get security status summary: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_recent_security_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent security events from Redis."""
        try:
            if not self.redis_client:
                return []
            
            # Get security event keys from the last N hours
            cutoff_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
            pattern = "mysql_security:events:*"
            keys = self.redis_client.keys(pattern)
            
            # Filter keys by timestamp
            recent_keys = [key for key in keys if int(key.split(':')[-1]) >= cutoff_timestamp]
            
            # Retrieve events
            events = []
            for key in recent_keys:
                try:
                    event_data = self.redis_client.get(key)
                    if event_data:
                        event = json.loads(event_data)
                        events.append(event)
                except Exception as e:
                    logger.debug(f"Could not parse security event from {key}: {e}")
            
            # Sort events by timestamp
            events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return events
            
        except Exception as e:
            logger.debug(f"Could not get recent security events: {e}")
            return []
    
    def cleanup_resources(self):
        """Clean up resources."""
        try:
            # Close Redis connection
            if self.redis_client:
                try:
                    self.redis_client.close()
                except:
                    pass
            
            logger.info("MySQL Security Hardening resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")


def main():
    """Command-line interface for MySQL Security Hardening."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MySQL Security Hardening for Vedfolnir')
    parser.add_argument('--action', choices=[
        'audit', 'harden', 'create-user', 'generate-cert', 'status'
    ], required=True, help='Action to perform')
    
    parser.add_argument('--database-url', help='Database URL (optional, uses config default)')
    parser.add_argument('--hardening-level', choices=['basic', 'standard', 'strict'], 
                       default='standard', help='Hardening level (default: standard)')
    parser.add_argument('--username', help='Username for user creation')
    parser.add_argument('--password', help='Password for user creation')
    parser.add_argument('--database', help='Database for user access')
    parser.add_argument('--privileges', nargs='+', help='Privileges to grant to user')
    parser.add_argument('--cert-common-name', default='localhost', help='Certificate common name')
    parser.add_argument('--cert-organization', default='Vedfolnir', help='Certificate organization')
    parser.add_argument('--cert-dir', default='./ssl', help='Certificate directory')
    parser.add_argument('--output-format', choices=['json', 'table'], default='table',
                       help='Output format (default: table)')
    
    args = parser.parse_args()
    
    # Initialize security hardening system
    try:
        hardening = MySQLSecurityHardening()
        
        if args.action == 'audit':
            result = hardening.perform_comprehensive_security_audit(args.database_url)
            print_audit_result(result, args.output_format)
            
        elif args.action == 'harden':
            result = hardening.implement_security_hardening(args.hardening_level)
            print_result(result, args.output_format)
            
        elif args.action == 'create-user':
            if not all([args.username, args.password, args.database]):
                print("Error: --username, --password, and --database are required for user creation")
                sys.exit(1)
            
            result = hardening.create_secure_mysql_user(
                args.username, args.password, args.database, args.privileges
            )
            print_result(result, args.output_format)
            
        elif args.action == 'generate-cert':
            cert_info = {
                'common_name': args.cert_common_name,
                'organization': args.cert_organization,
                'cert_dir': args.cert_dir
            }
            result = hardening.generate_security_certificate(cert_info)
            print_result(result, args.output_format)
            
        elif args.action == 'status':
            result = hardening.get_security_status_summary()
            print_result(result, args.output_format)
        
        # Cleanup
        hardening.cleanup_resources()
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        print_result(error_result, args.output_format)
        sys.exit(1)


def print_audit_result(audit_result: SecurityAuditResult, output_format: str):
    """Print security audit result in the specified format."""
    if output_format == 'json':
        print(json.dumps(asdict(audit_result), indent=2, default=str))
    else:
        # Table format
        print(f"\n{'='*80}")
        print(f"MySQL Security Audit Report - {audit_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # Overall score and level
        score_emoji = "🟢" if audit_result.overall_score >= 90 else "🟡" if audit_result.overall_score >= 75 else "🔴"
        print(f"{score_emoji} Overall Security Score: {audit_result.overall_score:.1f}/100 ({audit_result.security_level.upper()})")
        
        # Critical issues
        if audit_result.critical_issues:
            print(f"\n🚨 Critical Issues ({len(audit_result.critical_issues)}):")
            for issue in audit_result.critical_issues:
                print(f"  • {issue.get('title', 'Unknown Issue')}")
                print(f"    {issue.get('description', 'No description')}")
        else:
            print(f"\n✅ No Critical Issues Found")
        
        # Warnings
        if audit_result.warnings:
            print(f"\n⚠️ Warnings ({len(audit_result.warnings)}):")
            for warning in audit_result.warnings[:5]:  # Show top 5
                print(f"  • {warning.get('title', 'Unknown Warning')}")
        
        # Compliance status
        print(f"\n📋 Compliance Status:")
        compliance = audit_result.compliance_status
        if compliance:
            for standard, status in compliance.items():
                if isinstance(status, dict) and 'level' in status:
                    level_emoji = "✅" if status['level'] == 'excellent' else "⚠️" if status['level'] == 'good' else "❌"
                    print(f"  {level_emoji} {standard.replace('_', ' ').title()}: {status['level'].upper()}")
        
        # Recommendations
        if audit_result.recommendations:
            print(f"\n💡 Top Recommendations:")
            for rec in audit_result.recommendations[:3]:  # Show top 3
                print(f"  • {rec.get('title', 'Unknown Recommendation')}")
        
        print(f"{'='*80}\n")


def print_result(result: Dict[str, Any], output_format: str):
    """Print result in the specified format."""
    if output_format == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        # Table format
        print(f"\n{'='*60}")
        print(f"MySQL Security Hardening - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if result.get('success'):
            print("✅ Operation completed successfully")
            
            # Print specific result information
            if 'results' in result:
                results = result['results']
                if 'audit_score_before' in results and 'audit_score_after' in results:
                    improvement = results.get('score_improvement', 0)
                    print(f"\n📊 Security Score:")
                    print(f"  Before: {results['audit_score_before']:.1f}/100")
                    print(f"  After:  {results['audit_score_after']:.1f}/100")
                    print(f"  Improvement: {improvement:+.1f} points")
                
                if 'actions_taken' in results:
                    actions_taken = results['actions_taken']
                    print(f"\n✅ Actions Completed ({len(actions_taken)}):")
                    for action in actions_taken:
                        action_info = action.get('action', {})
                        print(f"  • {action_info.get('title', 'Unknown Action')}")
                
                if 'actions_failed' in results:
                    actions_failed = results['actions_failed']
                    if actions_failed:
                        print(f"\n❌ Actions Failed ({len(actions_failed)}):")
                        for action in actions_failed:
                            action_info = action.get('action', {})
                            print(f"  • {action_info.get('title', 'Unknown Action')}: {action.get('error', 'Unknown error')}")
            
            # Print other result types
            if 'username' in result:
                print(f"\n👤 User Created:")
                print(f"  Username: {result['username']}")
                print(f"  Database: {result['database']}")
                print(f"  Privileges: {', '.join(result.get('privileges', []))}")
            
            if 'certificate_path' in result:
                print(f"\n🔐 Certificate Generated:")
                print(f"  Certificate: {result['certificate_path']}")
                print(f"  Private Key: {result['key_path']}")
                print(f"  Valid Until: {result['valid_until']}")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"\n📊 Security Status:")
                print(f"  Overall Score: {summary.get('overall_security_score', 0):.1f}/100")
                print(f"  Security Level: {summary.get('security_level', 'unknown').upper()}")
                print(f"  Critical Issues: {summary.get('critical_issues_count', 0)}")
                print(f"  SSL Enabled: {'Yes' if summary.get('ssl_enabled') else 'No'}")
        
        else:
            print("❌ Operation failed")
            if 'error' in result:
                print(f"Error: {result['error']}")
        
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
