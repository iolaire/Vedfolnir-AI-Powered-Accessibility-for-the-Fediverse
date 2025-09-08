#!/usr/bin/env python3
"""
MySQL Connection Parameter Validation

Provides comprehensive validation and troubleshooting for MySQL connection parameters.
"""

import re
import logging
import socket
import pymysql
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check operation"""
    healthy: bool
    status: str
    timestamp: datetime
    details: Dict[str, Any]
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class ServerInfo:
    """MySQL server information"""
    version: str
    version_comment: str
    character_set: str
    collation: str
    ssl_support: bool
    max_connections: int
    innodb_version: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of connection validation"""
    success: bool
    error_message: Optional[str] = None
    server_info: Optional[ServerInfo] = None
    connection_time_ms: Optional[float] = None
    validation_details: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


@dataclass
class MySQLConnectionParams:
    """MySQL connection parameters extracted from DATABASE_URL"""
    scheme: str
    username: str
    password: str
    host: str
    port: int
    database: str
    charset: str
    unix_socket: Optional[str] = None
    ssl_mode: Optional[str] = None
    connect_timeout: Optional[int] = None
    read_timeout: Optional[int] = None
    write_timeout: Optional[int] = None


class MySQLConnectionValidator:
    """Validates MySQL connection parameters and provides troubleshooting guidance"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        self.troubleshooting_tips: List[str] = []
        self.database_url = database_url
        
        # Set default database URL from environment if not provided
        if not self.database_url:
            import os
            self.database_url = os.getenv('DATABASE_URL')
    
    def _get_connection(self):
        """Get a MySQL connection using the configured database URL"""
        if not self.database_url:
            raise ValueError("No database URL configured")
        
        # Parse the database URL
        parsed = urlparse(self.database_url)
        
        # Extract connection parameters
        host = parsed.hostname or 'localhost'
        port = parsed.port or 3306
        user = parsed.username or 'root'
        password = parsed.password or ''
        database = parsed.path.lstrip('/') if parsed.path else ''
        
        # Parse query parameters
        query_params = parse_qs(parsed.query)
        charset = query_params.get('charset', ['utf8mb4'])[0]
        
        # Create connection
        return pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset=charset,
            autocommit=False,
            connect_timeout=10
        )
    
    def validate_connection(self) -> ValidationResult:
        """
        Validate MySQL connection and gather server information.
        
        Returns:
            ValidationResult with connection status and server info
        """
        start_time = datetime.now()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get server version
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                
                cursor.execute("SELECT @@version_comment")
                version_comment = cursor.fetchone()[0]
                
                # Get character set info
                cursor.execute("SELECT @@character_set_server")
                character_set = cursor.fetchone()[0]
                
                cursor.execute("SELECT @@collation_server")
                collation = cursor.fetchone()[0]
                
                # Check SSL support
                cursor.execute("SHOW VARIABLES LIKE 'have_ssl'")
                ssl_result = cursor.fetchone()
                ssl_support = ssl_result[1].upper() == 'YES' if ssl_result else False
                
                # Get max connections
                cursor.execute("SELECT @@max_connections")
                max_connections = int(cursor.fetchone()[0])
                
                # Get InnoDB version if available
                innodb_version = None
                try:
                    cursor.execute("SELECT @@innodb_version")
                    innodb_version = cursor.fetchone()[0]
                except:
                    pass
                
                cursor.close()
                
                # Calculate connection time
                connection_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                server_info = ServerInfo(
                    version=version,
                    version_comment=version_comment,
                    character_set=character_set,
                    collation=collation,
                    ssl_support=ssl_support,
                    max_connections=max_connections,
                    innodb_version=innodb_version
                )
                
                return ValidationResult(
                    success=True,
                    server_info=server_info,
                    connection_time_ms=connection_time_ms,
                    validation_details={
                        'connection_successful': True,
                        'server_accessible': True
                    },
                    recommendations=[],
                    warnings=[]
                )
                
        except Exception as e:
            connection_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return ValidationResult(
                success=False,
                error_message=str(e),
                connection_time_ms=connection_time_ms,
                validation_details={
                    'connection_successful': False,
                    'error_type': type(e).__name__
                },
                recommendations=[
                    'Check database server is running',
                    'Verify connection parameters',
                    'Check network connectivity'
                ],
                warnings=[]
            )
    
    def validate_database_url(self, database_url: str) -> Tuple[bool, MySQLConnectionParams, Dict[str, Any]]:
        """
        Validate MySQL DATABASE_URL and extract connection parameters
        
        Returns:
            Tuple of (is_valid, connection_params, validation_report)
        """
        validation_report = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'troubleshooting_tips': [],
            'connection_params': None
        }
        
        try:
            # Parse the database URL
            parsed = urlparse(database_url)
            
            # Validate scheme
            if not parsed.scheme or not parsed.scheme.startswith('mysql'):
                validation_report['errors'].append(f"Invalid scheme: {parsed.scheme}. Expected mysql:// or mysql+pymysql://")
                return False, None, validation_report
            
            # Extract connection parameters
            host = parsed.hostname or 'localhost'
            port = parsed.port or 3306
            username = parsed.username or 'root'
            password = parsed.password or ''
            database = parsed.path.lstrip('/') if parsed.path else ''
            
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            charset = query_params.get('charset', ['utf8mb4'])[0]
            ssl_mode = query_params.get('ssl_mode', [None])[0]
            unix_socket = query_params.get('unix_socket', [None])[0]
            
            # Create connection params object
            connection_params = MySQLConnectionParams(
                scheme=parsed.scheme,
                username=username,
                password=password,
                host=host,
                port=port,
                database=database,
                charset=charset,
                unix_socket=unix_socket,
                ssl_mode=ssl_mode,
                connect_timeout=query_params.get('connect_timeout', [10])[0],
                read_timeout=query_params.get('read_timeout', [None])[0],
                write_timeout=query_params.get('write_timeout', [None])[0]
            )
            
            # Validate connection parameters
            self._validate_connection_params(connection_params)
            
            # If we get here, validation passed
            validation_report['is_valid'] = True
            validation_report['connection_params'] = connection_params
            validation_report['errors'] = self.validation_errors.copy()
            validation_report['warnings'] = self.validation_warnings.copy()
            validation_report['troubleshooting_tips'] = self.troubleshooting_tips.copy()
            
            return True, connection_params, validation_report
            
        except Exception as e:
            validation_report['errors'].append(f"Failed to parse database URL: {str(e)}")
            return False, None, validation_report
    def perform_health_check(self) -> HealthCheckResult:
        """
        Perform comprehensive MySQL health check.
        
        Returns:
            HealthCheckResult with health status and metrics
        """
        start_time = datetime.now()
        details = {}
        metrics = {}
        healthy = True
        status = "healthy"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Basic connectivity test
                cursor.execute("SELECT 1")
                if cursor.fetchone()[0] != 1:
                    healthy = False
                    status = "unhealthy"
                    details['connectivity'] = "Basic connectivity test failed"
                else:
                    details['connectivity'] = "OK"
                
                # Connection pool metrics
                try:
                    cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                    threads_connected = int(cursor.fetchone()[1])
                    cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                    max_connections = int(cursor.fetchone()[1])
                    
                    connection_usage = (threads_connected / max_connections) * 100
                    metrics['connection_usage_percent'] = connection_usage
                    metrics['threads_connected'] = threads_connected
                    metrics['max_connections'] = max_connections
                    
                    if connection_usage > 80:
                        healthy = False
                        status = "warning"
                        details['connection_pool'] = f"High connection usage: {connection_usage:.1f}%"
                    else:
                        details['connection_pool'] = "OK"
                        
                except Exception as e:
                    details['connection_pool'] = f"Failed to check: {e}"
                
                # Performance metrics
                try:
                    # Query performance
                    cursor.execute("SHOW STATUS LIKE 'Slow_queries'")
                    slow_queries = int(cursor.fetchone()[1])
                    cursor.execute("SHOW STATUS LIKE 'Questions'")
                    total_queries = int(cursor.fetchone()[1])
                    
                    if total_queries > 0:
                        slow_query_ratio = (slow_queries / total_queries) * 100
                        metrics['slow_query_ratio_percent'] = slow_query_ratio
                        
                        if slow_query_ratio > 5:  # More than 5% slow queries
                            healthy = False
                            status = "warning"
                            details['query_performance'] = f"High slow query ratio: {slow_query_ratio:.2f}%"
                        else:
                            details['query_performance'] = "OK"
                    
                    metrics['slow_queries'] = slow_queries
                    metrics['total_queries'] = total_queries
                    
                except Exception as e:
                    details['query_performance'] = f"Failed to check: {e}"
                
                # InnoDB metrics
                try:
                    cursor.execute("SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'")
                    read_requests = int(cursor.fetchone()[1])
                    cursor.execute("SHOW STATUS LIKE 'Innodb_buffer_pool_reads'")
                    disk_reads = int(cursor.fetchone()[1])
                    
                    if read_requests > 0:
                        buffer_pool_hit_ratio = ((read_requests - disk_reads) / read_requests) * 100
                        metrics['buffer_pool_hit_ratio_percent'] = buffer_pool_hit_ratio
                        
                        if buffer_pool_hit_ratio < 95:  # Less than 95% hit ratio
                            details['buffer_pool'] = f"Low hit ratio: {buffer_pool_hit_ratio:.2f}%"
                        else:
                            details['buffer_pool'] = "OK"
                    
                except Exception as e:
                    details['buffer_pool'] = f"Failed to check: {e}"
                
                # Replication status (if applicable)
                try:
                    cursor.execute("SHOW SLAVE STATUS")
                    slave_status = cursor.fetchone()
                    if slave_status:
                        # This is a slave server
                        details['replication'] = "Slave server detected"
                        # Add more replication-specific checks here
                    else:
                        details['replication'] = "Not a slave server"
                except Exception:
                    details['replication'] = "Not applicable"
                
                cursor.close()
                
        except Exception as e:
            healthy = False
            status = "unhealthy"
            details['error'] = str(e)
            logger.error(f"Health check failed: {e}")
        
        # Calculate response time
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        metrics['response_time_ms'] = response_time_ms
        
        return HealthCheckResult(
            healthy=healthy,
            status=status,
            details=details,
            metrics=metrics,
            timestamp=datetime.now()
        )
    
    def get_server_compatibility_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive MySQL server compatibility report.
        
        Returns:
            Dictionary containing compatibility analysis
        """
        validation_result = self.validate_connection()
        
        if not validation_result.success:
            return {
                'compatible': False,
                'error': validation_result.error_message,
                'recommendations': ['Fix connection issues before proceeding']
            }
        
        server_info = validation_result.server_info
        compatibility_report = {
            'compatible': True,
            'server_info': server_info.__dict__ if server_info else {},
            'compatibility_checks': {},
            'recommendations': validation_result.recommendations,
            'warnings': validation_result.warnings
        }
        
        # Version compatibility
        version_compatible = server_info.version_major >= 8 or (
            server_info.version_major == 5 and server_info.version_minor >= 7
        )
        compatibility_report['compatibility_checks']['version'] = {
            'compatible': version_compatible,
            'current': server_info.version,
            'minimum_required': '5.7.0',
            'recommended': '8.0.0'
        }
        
        # Feature compatibility
        feature_checks = {}
        feature_checks['innodb'] = {
            'available': server_info.engine_support.get('innodb', False),
            'required': True,
            'description': 'InnoDB storage engine for ACID compliance'
        }
        feature_checks['utf8mb4'] = {
            'available': server_info.character_set == 'utf8mb4',
            'required': True,
            'description': 'UTF8MB4 character set for full Unicode support'
        }
        feature_checks['ssl'] = {
            'available': server_info.ssl_support,
            'required': False,
            'description': 'SSL support for encrypted connections'
        }
        
        compatibility_report['compatibility_checks']['features'] = feature_checks
        
        # Performance compatibility
        performance_checks = {}
        performance_checks['buffer_pool_size'] = {
            'current': server_info.innodb_buffer_pool_size,
            'recommended_minimum': 134217728,  # 128MB
            'adequate': server_info.innodb_buffer_pool_size >= 134217728
        }
        performance_checks['max_connections'] = {
            'current': server_info.max_connections,
            'recommended_minimum': 50,
            'adequate': server_info.max_connections >= 50
        }
        
        compatibility_report['compatibility_checks']['performance'] = performance_checks
        
        # Overall compatibility assessment
        critical_issues = []
        if not version_compatible:
            critical_issues.append("MySQL version is below minimum requirements")
        if not server_info.engine_support.get('innodb', False):
            critical_issues.append("InnoDB storage engine is not available")
        if server_info.character_set != 'utf8mb4':
            critical_issues.append("UTF8MB4 character set is not configured")
        
        compatibility_report['compatible'] = len(critical_issues) == 0
        compatibility_report['critical_issues'] = critical_issues
        
        return compatibility_report
    
    def diagnose_connection_issues(self, database_url: str) -> Dict[str, Any]:
        """
        Diagnose MySQL connection issues and provide troubleshooting guidance.
        
        Args:
            database_url: MySQL database URL to diagnose
            
        Returns:
            Dictionary containing diagnostic information and recommendations
        """
        diagnostic_report = {
            'url_analysis': {},
            'connectivity_tests': {},
            'recommendations': [],
            'troubleshooting_steps': []
        }
        
        try:
            # Parse and validate URL
            parsed = urlparse(database_url)
            diagnostic_report['url_analysis'] = {
                'scheme': parsed.scheme,
                'hostname': parsed.hostname,
                'port': parsed.port or 3306,
                'database': parsed.path.lstrip('/'),
                'username': parsed.username,
                'password_provided': bool(parsed.password)
            }
            
            # Test network connectivity
            host = parsed.hostname or 'localhost'
            port = parsed.port or 3306
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    diagnostic_report['connectivity_tests']['network'] = {
                        'status': 'success',
                        'message': f"Network connection to {host}:{port} successful"
                    }
                else:
                    diagnostic_report['connectivity_tests']['network'] = {
                        'status': 'failed',
                        'message': f"Cannot connect to {host}:{port}",
                        'error_code': result
                    }
                    diagnostic_report['recommendations'].append(
                        f"Check if MySQL server is running on {host}:{port}"
                    )
                    diagnostic_report['troubleshooting_steps'].extend([
                        "Verify MySQL server is installed and running",
                        "Check firewall settings",
                        "Verify the hostname and port are correct"
                    ])
                    
            except Exception as e:
                diagnostic_report['connectivity_tests']['network'] = {
                    'status': 'error',
                    'message': f"Network connectivity test failed: {e}"
                }
            
            # Test MySQL authentication
            try:
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=parsed.username,
                    password=parsed.password,
                    database=parsed.path.lstrip('/'),
                    charset='utf8mb4',
                    connect_timeout=10
                )
                conn.close()
                
                diagnostic_report['connectivity_tests']['authentication'] = {
                    'status': 'success',
                    'message': "MySQL authentication successful"
                }
                
            except pymysql.Error as e:
                error_code = e.args[0] if e.args else 0
                error_message = e.args[1] if len(e.args) > 1 else str(e)
                
                diagnostic_report['connectivity_tests']['authentication'] = {
                    'status': 'failed',
                    'error_code': error_code,
                    'message': error_message
                }
                
                # Provide specific troubleshooting based on error code
                if error_code == 1045:  # Access denied
                    diagnostic_report['recommendations'].extend([
                        "Check username and password",
                        "Verify user exists and has proper privileges",
                        "Check if user is allowed to connect from this host"
                    ])
                elif error_code == 1049:  # Unknown database
                    diagnostic_report['recommendations'].append(
                        f"Create database '{parsed.path.lstrip('/')}' or check database name"
                    )
                elif error_code == 2003:  # Can't connect
                    diagnostic_report['recommendations'].extend([
                        "Check if MySQL server is running",
                        "Verify hostname and port",
                        "Check firewall settings"
                    ])
                
        except Exception as e:
            diagnostic_report['url_analysis']['error'] = str(e)
            diagnostic_report['recommendations'].append("Fix database URL format")
        
        return diagnostic_report
        self.validation_warnings.clear()
        self.troubleshooting_tips.clear()
        
        try:
            # Parse the URL
            parsed = urlparse(database_url)
            
            # Validate scheme
            if not parsed.scheme.startswith('mysql'):
                self.validation_errors.append(f"Invalid scheme '{parsed.scheme}'. Expected 'mysql+pymysql'")
                self.troubleshooting_tips.append("Use 'mysql+pymysql://' as the URL scheme for PyMySQL driver")
            
            if parsed.scheme != 'mysql+pymysql':
                self.validation_warnings.append(f"Scheme '{parsed.scheme}' may not be optimal. Recommended: 'mysql+pymysql'")
            
            # Extract basic connection parameters
            username = parsed.username or ''
            password = parsed.password or ''
            host = parsed.hostname or 'localhost'
            port = parsed.port or 3306
            database = parsed.path.lstrip('/') if parsed.path else ''
            
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            charset = query_params.get('charset', ['utf8mb4'])[0]
            unix_socket = query_params.get('unix_socket', [None])[0]
            ssl_mode = query_params.get('ssl_mode', [None])[0]
            
            # Extract timeout parameters
            connect_timeout = None
            read_timeout = None
            write_timeout = None
            
            if 'connect_timeout' in query_params:
                try:
                    connect_timeout = int(query_params['connect_timeout'][0])
                except ValueError:
                    self.validation_errors.append("Invalid connect_timeout value - must be integer")
            
            if 'read_timeout' in query_params:
                try:
                    read_timeout = int(query_params['read_timeout'][0])
                except ValueError:
                    self.validation_errors.append("Invalid read_timeout value - must be integer")
            
            if 'write_timeout' in query_params:
                try:
                    write_timeout = int(query_params['write_timeout'][0])
                except ValueError:
                    self.validation_errors.append("Invalid write_timeout value - must be integer")
            
            # Create connection params object
            connection_params = MySQLConnectionParams(
                scheme=parsed.scheme,
                username=username,
                password=password,
                host=host,
                port=port,
                database=database,
                charset=charset,
                unix_socket=unix_socket,
                ssl_mode=ssl_mode,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                write_timeout=write_timeout
            )
            
            # Validate individual parameters
            self._validate_connection_params(connection_params)
            
            # Create validation report
            validation_report = {
                'is_valid': len(self.validation_errors) == 0,
                'errors': self.validation_errors.copy(),
                'warnings': self.validation_warnings.copy(),
                'troubleshooting_tips': self.troubleshooting_tips.copy(),
                'connection_params': connection_params
            }
            
            return len(self.validation_errors) == 0, connection_params, validation_report
            
        except Exception as e:
            self.validation_errors.append(f"Failed to parse DATABASE_URL: {e}")
            validation_report = {
                'is_valid': False,
                'errors': self.validation_errors.copy(),
                'warnings': self.validation_warnings.copy(),
                'troubleshooting_tips': self.troubleshooting_tips.copy(),
                'connection_params': None
            }
            return False, None, validation_report
    
    def _validate_connection_params(self, params: MySQLConnectionParams):
        """Validate individual MySQL connection parameters"""
        
        # Validate username
        if not params.username:
            self.validation_errors.append("MySQL username is required")
            self.troubleshooting_tips.append("Set MySQL username in DATABASE_URL: mysql+pymysql://USERNAME:password@host/database")
        elif len(params.username) > 32:
            self.validation_errors.append("MySQL username cannot exceed 32 characters")
        
        # Validate password
        if not params.password:
            self.validation_warnings.append("MySQL password is empty - ensure this is intentional")
            self.troubleshooting_tips.append("Set MySQL password in DATABASE_URL: mysql+pymysql://username:PASSWORD@host/database")
        
        # Validate host
        if not params.host:
            self.validation_errors.append("MySQL host is required")
        elif params.host == 'localhost' and not params.unix_socket:
            self.validation_warnings.append("Using 'localhost' without unix_socket may cause connection issues")
            self.troubleshooting_tips.append("Consider using '127.0.0.1' or specify unix_socket parameter")
        
        # Validate port
        if params.port < 1 or params.port > 65535:
            self.validation_errors.append(f"Invalid MySQL port {params.port}. Must be between 1-65535")
        elif params.port != 3306:
            self.validation_warnings.append(f"Non-standard MySQL port {params.port}. Standard port is 3306")
        
        # Validate database name
        if not params.database:
            self.validation_errors.append("MySQL database name is required")
            self.troubleshooting_tips.append("Specify database name in DATABASE_URL: mysql+pymysql://user:pass@host/DATABASE_NAME")
        elif not re.match(r'^[a-zA-Z0-9_]+$', params.database):
            self.validation_warnings.append("Database name contains special characters - ensure it's properly escaped")
        
        # Validate charset
        if params.charset not in ['utf8mb4', 'utf8', 'latin1']:
            self.validation_warnings.append(f"Charset '{params.charset}' may not be optimal. Recommended: 'utf8mb4'")
        elif params.charset != 'utf8mb4':
            self.validation_warnings.append("Consider using 'utf8mb4' charset for full Unicode support including emojis")
        
        # Validate timeouts
        if params.connect_timeout and params.connect_timeout < 5:
            self.validation_warnings.append("Connect timeout < 5 seconds may cause connection failures")
        
        if params.read_timeout and params.read_timeout < 30:
            self.validation_warnings.append("Read timeout < 30 seconds may cause query failures for large results")
        
        if params.write_timeout and params.write_timeout < 30:
            self.validation_warnings.append("Write timeout < 30 seconds may cause failures for large inserts/updates")
    
    def test_network_connectivity(self, host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
        """Test network connectivity to MySQL server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True, f"Network connectivity to {host}:{port} successful"
            else:
                return False, f"Cannot connect to {host}:{port} - connection refused or host unreachable"
                
        except socket.gaierror as e:
            return False, f"DNS resolution failed for {host}: {e}"
        except Exception as e:
            return False, f"Network connectivity test failed: {e}"
    
    def generate_troubleshooting_guide(self, validation_report: Dict[str, Any]) -> str:
        """Generate comprehensive troubleshooting guide based on validation results"""
        
        guide = ["=== MySQL Connection Troubleshooting Guide ===\n"]
        
        if validation_report['errors']:
            guide.append("🚨 ERRORS (Must be fixed):")
            for error in validation_report['errors']:
                guide.append(f"  ❌ {error}")
            guide.append("")
        
        if validation_report['warnings']:
            guide.append("⚠️  WARNINGS (Recommended fixes):")
            for warning in validation_report['warnings']:
                guide.append(f"  ⚠️  {warning}")
            guide.append("")
        
        if validation_report['troubleshooting_tips']:
            guide.append("💡 TROUBLESHOOTING TIPS:")
            for tip in validation_report['troubleshooting_tips']:
                guide.append(f"  💡 {tip}")
            guide.append("")
        
        # Add general troubleshooting steps
        guide.extend([
            "🔧 GENERAL TROUBLESHOOTING STEPS:",
            "  1. Verify MySQL server is running: sudo systemctl status mysql",
            "  2. Check MySQL server logs: sudo tail -f /var/log/mysql/error.log",
            "  3. Test connection manually: mysql -u username -p -h host database",
            "  4. Verify user permissions: SHOW GRANTS FOR 'username'@'host';",
            "  5. Check firewall settings for MySQL port (default 3306)",
            "  6. Verify DATABASE_URL format: mysql+pymysql://user:pass@host:port/database?charset=utf8mb4",
            "",
            "📋 EXAMPLE VALID DATABASE_URL:",
            "  DATABASE_URL=mysql+pymysql://vedfolnir_user:secure_password@localhost:3306/vedfolnir?charset=utf8mb4",
            "",
            "🔗 For more help, see: https://dev.mysql.com/doc/refman/8.0/en/problems-connecting.html"
        ])
        
        return "\n".join(guide)


def validate_mysql_connection(database_url: str) -> Dict[str, Any]:
    """
    Convenience function to validate MySQL connection parameters
    
    Args:
        database_url: MySQL DATABASE_URL string
        
    Returns:
        Dictionary containing validation results and troubleshooting information
    """
    validator = MySQLConnectionValidator()
    is_valid, connection_params, validation_report = validator.validate_database_url(database_url)
    
    # Add network connectivity test if we have valid connection params
    if connection_params and not connection_params.unix_socket:
        network_ok, network_message = validator.test_network_connectivity(
            connection_params.host, 
            connection_params.port
        )
        validation_report['network_connectivity'] = {
            'success': network_ok,
            'message': network_message
        }
    
    # Generate troubleshooting guide
    validation_report['troubleshooting_guide'] = validator.generate_troubleshooting_guide(validation_report)
    
    return validation_report


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    else:
        database_url = "mysql+pymysql://user:password@localhost:3306/database?charset=utf8mb4"
    
    print(f"Validating DATABASE_URL: {database_url}")
    print()
    
    result = validate_mysql_connection(database_url)
    
    if result['is_valid']:
        print("✅ DATABASE_URL is valid!")
    else:
        print("❌ DATABASE_URL validation failed!")
    
    print()
    print(result['troubleshooting_guide'])
