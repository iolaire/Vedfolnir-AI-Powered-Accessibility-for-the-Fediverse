# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration Migration Tools
Migrates existing installations to support multi-tenant admin features
"""

import os
import sys
import json
import shutil
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/config_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConfigurationMigrator:
    """Handles configuration migration for existing installations"""
    
    def __init__(self):
        self.config = Config()
        self.backup_dir = Path("storage/backups/config_migration")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def analyze_current_configuration(self) -> Dict[str, Any]:
        """Analyze current configuration and identify migration needs"""
        logger.info("Analyzing current configuration...")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'environment_file': self._analyze_env_file(),
            'database_config': self._analyze_database_config(),
            'redis_config': self._analyze_redis_config(),
            'admin_config': self._analyze_admin_config(),
            'feature_flags': self._analyze_feature_flags(),
            'migration_needed': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Determine what migrations are needed
        self._determine_migration_needs(analysis)
        
        return analysis
    
    def _analyze_env_file(self) -> Dict[str, Any]:
        """Analyze .env file configuration"""
        env_file = Path('.env')
        
        if not env_file.exists():
            return {
                'exists': False,
                'error': '.env file not found'
            }
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Check for required variables
            required_vars = [
                'DATABASE_URL', 'FLASK_SECRET_KEY', 'REDIS_URL',
                'OLLAMA_URL', 'PLATFORM_ENCRYPTION_KEY'
            ]
            
            missing_vars = []
            present_vars = []
            
            for var in required_vars:
                if f'{var}=' in content:
                    present_vars.append(var)
                else:
                    missing_vars.append(var)
            
            # Check for new admin variables
            admin_vars = [
                'MULTI_TENANT_ADMIN_ENABLED',
                'ADMIN_DASHBOARD_ENABLED',
                'SYSTEM_MONITORING_ENABLED',
                'ALERT_SYSTEM_ENABLED'
            ]
            
            admin_vars_present = []
            for var in admin_vars:
                if f'{var}=' in content:
                    admin_vars_present.append(var)
            
            return {
                'exists': True,
                'size': len(content),
                'required_vars_present': present_vars,
                'required_vars_missing': missing_vars,
                'admin_vars_present': admin_vars_present,
                'needs_admin_vars': len(admin_vars_present) == 0
            }
            
        except Exception as e:
            return {
                'exists': True,
                'error': f'Could not read .env file: {e}'
            }
    
    def _analyze_database_config(self) -> Dict[str, Any]:
        """Analyze database configuration"""
        try:
            db_config = self.config.get_database_config()
            
            # Check if it's MySQL (required for admin features)
            is_mysql = 'mysql' in db_config.get('url', '').lower()
            
            return {
                'type': 'mysql' if is_mysql else 'other',
                'host': db_config.get('host', 'unknown'),
                'database': db_config.get('database', 'unknown'),
                'is_mysql': is_mysql,
                'connection_pool_configured': 'pool_size' in db_config
            }
            
        except Exception as e:
            return {
                'error': f'Could not analyze database config: {e}'
            }
    
    def _analyze_redis_config(self) -> Dict[str, Any]:
        """Analyze Redis configuration"""
        try:
            redis_url = os.getenv('REDIS_URL')
            
            if not redis_url:
                return {
                    'configured': False,
                    'error': 'REDIS_URL not configured'
                }
            
            # Test Redis connection
            import redis
            try:
                r = redis.from_url(redis_url)
                r.ping()
                redis_working = True
            except:
                redis_working = False
            
            return {
                'configured': True,
                'url': redis_url,
                'connection_working': redis_working,
                'session_config_present': bool(os.getenv('REDIS_SESSION_PREFIX'))
            }
            
        except Exception as e:
            return {
                'configured': False,
                'error': f'Could not analyze Redis config: {e}'
            }
    
    def _analyze_admin_config(self) -> Dict[str, Any]:
        """Analyze admin-specific configuration"""
        admin_config_file = Path('config/admin_settings.json')
        
        analysis = {
            'config_file_exists': admin_config_file.exists(),
            'admin_users_configured': False,
            'monitoring_configured': False,
            'alerts_configured': False
        }
        
        if admin_config_file.exists():
            try:
                with open(admin_config_file, 'r') as f:
                    config = json.load(f)
                
                analysis.update({
                    'admin_users_configured': bool(config.get('admin_users')),
                    'monitoring_configured': bool(config.get('monitoring')),
                    'alerts_configured': bool(config.get('alerts'))
                })
                
            except Exception as e:
                analysis['error'] = f'Could not read admin config: {e}'
        
        return analysis
    
    def _analyze_feature_flags(self) -> Dict[str, Any]:
        """Analyze feature flags configuration"""
        feature_flags_file = Path('config/feature_flags.json')
        
        if not feature_flags_file.exists():
            return {
                'configured': False,
                'file_exists': False
            }
        
        try:
            with open(feature_flags_file, 'r') as f:
                flags = json.load(f)
            
            admin_flags = [
                'multi_tenant_admin', 'admin_dashboard', 'admin_job_management',
                'admin_user_management', 'system_monitoring', 'alert_system'
            ]
            
            configured_admin_flags = []
            for flag in admin_flags:
                if flag in flags.get('flags', {}):
                    configured_admin_flags.append(flag)
            
            return {
                'configured': True,
                'file_exists': True,
                'total_flags': len(flags.get('flags', {})),
                'admin_flags_configured': configured_admin_flags,
                'needs_admin_flags': len(configured_admin_flags) == 0
            }
            
        except Exception as e:
            return {
                'configured': False,
                'file_exists': True,
                'error': f'Could not read feature flags: {e}'
            }
    
    def _determine_migration_needs(self, analysis: Dict[str, Any]):
        """Determine what migrations are needed"""
        needs = analysis['migration_needed']
        warnings = analysis['warnings']
        recommendations = analysis['recommendations']
        
        # Check environment file
        env_analysis = analysis['environment_file']
        if env_analysis.get('needs_admin_vars'):
            needs.append('env_admin_variables')
            recommendations.append('Add admin feature environment variables to .env file')
        
        if env_analysis.get('required_vars_missing'):
            warnings.append(f"Missing required variables: {', '.join(env_analysis['required_vars_missing'])}")
        
        # Check database
        db_analysis = analysis['database_config']
        if not db_analysis.get('is_mysql'):
            warnings.append('MySQL database required for admin features')
            needs.append('database_migration')
        
        # Check Redis
        redis_analysis = analysis['redis_config']
        if not redis_analysis.get('configured'):
            needs.append('redis_configuration')
            recommendations.append('Configure Redis for session management and caching')
        
        if not redis_analysis.get('connection_working'):
            warnings.append('Redis connection not working')
        
        # Check admin configuration
        admin_analysis = analysis['admin_config']
        if not admin_analysis.get('config_file_exists'):
            needs.append('admin_config_creation')
            recommendations.append('Create admin configuration file')
        
        # Check feature flags
        flags_analysis = analysis['feature_flags']
        if flags_analysis.get('needs_admin_flags'):
            needs.append('feature_flags_setup')
            recommendations.append('Initialize admin feature flags')
    
    def create_migration_backup(self) -> str:
        """Create backup of current configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"config_migration_{timestamp}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)
        
        logger.info(f"Creating configuration backup: {backup_id}")
        
        # Backup files
        files_to_backup = [
            '.env',
            'config/admin_settings.json',
            'config/feature_flags.json',
            'config/system_config.json'
        ]
        
        backed_up_files = []
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                dest = backup_path / Path(file_path).name
                shutil.copy2(file_path, dest)
                backed_up_files.append(file_path)
        
        # Create backup manifest
        manifest = {
            'backup_id': backup_id,
            'timestamp': timestamp,
            'backed_up_files': backed_up_files,
            'analysis': self.analyze_current_configuration()
        }
        
        with open(backup_path / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Configuration backup created: {backup_path}")
        return backup_id
    
    def migrate_environment_variables(self) -> bool:
        """Migrate environment variables for admin features"""
        logger.info("Migrating environment variables...")
        
        env_file = Path('.env')
        if not env_file.exists():
            logger.error(".env file not found")
            return False
        
        try:
            # Read current .env file
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Admin feature variables to add
            admin_vars = {
                'MULTI_TENANT_ADMIN_ENABLED': 'false',
                'ADMIN_DASHBOARD_ENABLED': 'false', 
                'ADMIN_JOB_MANAGEMENT_ENABLED': 'false',
                'ADMIN_USER_MANAGEMENT_ENABLED': 'false',
                'SYSTEM_MONITORING_ENABLED': 'false',
                'ALERT_SYSTEM_ENABLED': 'false',
                'PERFORMANCE_METRICS_ENABLED': 'false',
                'ENHANCED_ERROR_HANDLING_ENABLED': 'false',
                'AUDIT_LOGGING_ENABLED': 'false',
                'REAL_TIME_MONITORING_ENABLED': 'false',
                'EMAIL_ALERTS_ENABLED': 'false',
                'WEBHOOK_ALERTS_ENABLED': 'false'
            }
            
            # Add missing variables
            additions = []
            for var, default_value in admin_vars.items():
                if f'{var}=' not in content:
                    additions.append(f'{var}={default_value}')
            
            if additions:
                # Add admin section header
                content += '\n\n# Multi-Tenant Admin Configuration\n'
                content += '\n'.join(additions)
                
                # Write updated .env file
                with open(env_file, 'w') as f:
                    f.write(content)
                
                logger.info(f"Added {len(additions)} admin environment variables")
            else:
                logger.info("All admin environment variables already present")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate environment variables: {e}")
            return False
    
    def create_admin_configuration(self) -> bool:
        """Create admin configuration file"""
        logger.info("Creating admin configuration...")
        
        config_dir = Path('config')
        config_dir.mkdir(exist_ok=True)
        
        admin_config_file = config_dir / 'admin_settings.json'
        
        # Default admin configuration
        admin_config = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'admin_settings': {
                'dashboard': {
                    'refresh_interval': 30,
                    'max_jobs_display': 100,
                    'enable_real_time_updates': False
                },
                'job_management': {
                    'max_concurrent_jobs_per_user': 3,
                    'max_concurrent_jobs_system': 10,
                    'job_timeout_minutes': 60,
                    'auto_cleanup_completed_jobs_days': 7
                },
                'user_management': {
                    'allow_user_registration': True,
                    'require_email_verification': False,
                    'default_user_role': 'user',
                    'max_platform_connections_per_user': 5
                },
                'monitoring': {
                    'collect_performance_metrics': True,
                    'metrics_retention_days': 30,
                    'health_check_interval_seconds': 60
                },
                'alerts': {
                    'enable_email_alerts': False,
                    'enable_webhook_alerts': False,
                    'alert_thresholds': {
                        'high_error_rate_percentage': 10,
                        'queue_backup_threshold': 50,
                        'system_resource_threshold_percentage': 80
                    }
                }
            },
            'security': {
                'admin_session_timeout_minutes': 120,
                'require_admin_2fa': False,
                'audit_log_retention_days': 90,
                'rate_limit_admin_actions': True
            }
        }
        
        try:
            with open(admin_config_file, 'w') as f:
                json.dump(admin_config, f, indent=2)
            
            logger.info(f"Admin configuration created: {admin_config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create admin configuration: {e}")
            return False
    
    def initialize_feature_flags(self) -> bool:
        """Initialize feature flags for admin features"""
        logger.info("Initializing feature flags...")
        
        config_dir = Path('config')
        config_dir.mkdir(exist_ok=True)
        
        feature_flags_file = config_dir / 'feature_flags.json'
        
        # Initialize feature flag manager to create default flags
        try:
            from admin.feature_flags import FeatureFlagManager
            
            manager = FeatureFlagManager(str(feature_flags_file))
            # Manager will create default flags if file doesn't exist
            
            logger.info(f"Feature flags initialized: {feature_flags_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize feature flags: {e}")
            return False
    
    def migrate_database_configuration(self) -> bool:
        """Migrate database configuration for admin features"""
        logger.info("Migrating database configuration...")
        
        try:
            # Check if database migration is needed
            from database import DatabaseManager
            
            db_manager = DatabaseManager(self.config)
            
            # Test database connection
            with db_manager.get_session() as session:
                session.execute("SELECT 1")
            
            logger.info("Database configuration verified")
            return True
            
        except Exception as e:
            logger.error(f"Database configuration migration failed: {e}")
            return False
    
    def execute_full_migration(self) -> bool:
        """Execute complete configuration migration"""
        logger.info("🚀 Starting full configuration migration...")
        
        # Create backup first
        backup_id = self.create_migration_backup()
        
        success_count = 0
        total_steps = 4
        
        try:
            # Step 1: Migrate environment variables
            if self.migrate_environment_variables():
                success_count += 1
                logger.info("✅ Environment variables migrated")
            else:
                logger.error("❌ Environment variables migration failed")
            
            # Step 2: Create admin configuration
            if self.create_admin_configuration():
                success_count += 1
                logger.info("✅ Admin configuration created")
            else:
                logger.error("❌ Admin configuration creation failed")
            
            # Step 3: Initialize feature flags
            if self.initialize_feature_flags():
                success_count += 1
                logger.info("✅ Feature flags initialized")
            else:
                logger.error("❌ Feature flags initialization failed")
            
            # Step 4: Migrate database configuration
            if self.migrate_database_configuration():
                success_count += 1
                logger.info("✅ Database configuration verified")
            else:
                logger.error("❌ Database configuration migration failed")
            
            # Summary
            if success_count == total_steps:
                logger.info("🎉 Configuration migration completed successfully!")
                logger.info(f"Backup created: {backup_id}")
                return True
            else:
                logger.warning(f"⚠️  Partial migration: {success_count}/{total_steps} steps completed")
                logger.info(f"Backup available for rollback: {backup_id}")
                return False
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            logger.info(f"Backup available for rollback: {backup_id}")
            return False
    
    def validate_migration(self) -> Dict[str, Any]:
        """Validate migration results"""
        logger.info("Validating migration results...")
        
        validation = {
            'timestamp': datetime.now().isoformat(),
            'overall_success': True,
            'checks': {}
        }
        
        # Check environment variables
        env_check = self._validate_env_migration()
        validation['checks']['environment'] = env_check
        if not env_check['success']:
            validation['overall_success'] = False
        
        # Check admin configuration
        admin_check = self._validate_admin_config()
        validation['checks']['admin_config'] = admin_check
        if not admin_check['success']:
            validation['overall_success'] = False
        
        # Check feature flags
        flags_check = self._validate_feature_flags()
        validation['checks']['feature_flags'] = flags_check
        if not flags_check['success']:
            validation['overall_success'] = False
        
        # Check database
        db_check = self._validate_database_config()
        validation['checks']['database'] = db_check
        if not db_check['success']:
            validation['overall_success'] = False
        
        return validation
    
    def _validate_env_migration(self) -> Dict[str, Any]:
        """Validate environment variable migration"""
        try:
            required_admin_vars = [
                'MULTI_TENANT_ADMIN_ENABLED',
                'ADMIN_DASHBOARD_ENABLED',
                'SYSTEM_MONITORING_ENABLED'
            ]
            
            missing_vars = []
            for var in required_admin_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            return {
                'success': len(missing_vars) == 0,
                'missing_variables': missing_vars,
                'message': 'All admin environment variables present' if not missing_vars else f'Missing: {", ".join(missing_vars)}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_admin_config(self) -> Dict[str, Any]:
        """Validate admin configuration"""
        try:
            config_file = Path('config/admin_settings.json')
            
            if not config_file.exists():
                return {
                    'success': False,
                    'message': 'Admin configuration file not found'
                }
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            required_sections = ['admin_settings', 'security']
            missing_sections = []
            
            for section in required_sections:
                if section not in config:
                    missing_sections.append(section)
            
            return {
                'success': len(missing_sections) == 0,
                'missing_sections': missing_sections,
                'message': 'Admin configuration valid' if not missing_sections else f'Missing sections: {", ".join(missing_sections)}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_feature_flags(self) -> Dict[str, Any]:
        """Validate feature flags"""
        try:
            from admin.feature_flags import FeatureFlagManager
            
            manager = FeatureFlagManager()
            flags = manager.list_flags()
            
            required_flags = [
                'multi_tenant_admin',
                'admin_dashboard',
                'system_monitoring'
            ]
            
            missing_flags = []
            for flag in required_flags:
                if flag not in flags:
                    missing_flags.append(flag)
            
            return {
                'success': len(missing_flags) == 0,
                'total_flags': len(flags),
                'missing_flags': missing_flags,
                'message': 'Feature flags configured' if not missing_flags else f'Missing flags: {", ".join(missing_flags)}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_database_config(self) -> Dict[str, Any]:
        """Validate database configuration"""
        try:
            from database import DatabaseManager
            
            db_manager = DatabaseManager(self.config)
            
            with db_manager.get_session() as session:
                session.execute("SELECT 1")
            
            return {
                'success': True,
                'message': 'Database connection successful'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def main():
    parser = argparse.ArgumentParser(description='Configuration Migration Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze current configuration')
    analyze_parser.add_argument('--output', help='Output file for analysis results')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Execute configuration migration')
    migrate_parser.add_argument('--backup', action='store_true', default=True,
                               help='Create backup before migration')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate migration results')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create configuration backup')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    migrator = ConfigurationMigrator()
    
    if args.command == 'analyze':
        analysis = migrator.analyze_current_configuration()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"Analysis saved to: {args.output}")
        else:
            print(json.dumps(analysis, indent=2))
    
    elif args.command == 'migrate':
        success = migrator.execute_full_migration()
        sys.exit(0 if success else 1)
    
    elif args.command == 'validate':
        validation = migrator.validate_migration()
        print(json.dumps(validation, indent=2))
        sys.exit(0 if validation['overall_success'] else 1)
    
    elif args.command == 'backup':
        backup_id = migrator.create_migration_backup()
        print(f"Configuration backup created: {backup_id}")

if __name__ == '__main__':
    main()