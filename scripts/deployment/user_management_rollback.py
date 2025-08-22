# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Management Rollback Procedures

This module provides comprehensive rollback procedures for user management deployments,
including database rollback, configuration restoration, service rollback, and
validation procedures to ensure system integrity after rollback operations.
"""

import os
import sys
import json
import shutil
import logging
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from database import DatabaseManager
from migrations.user_management_migration import UserManagementMigration

@dataclass
class RollbackPoint:
    """Information about a rollback point"""
    timestamp: datetime
    version: str
    description: str
    database_backup: str
    config_backup: str
    application_backup: str
    validation_data: Dict[str, Any]

@dataclass
class RollbackResult:
    """Result of rollback operation"""
    success: bool
    rollback_point: RollbackPoint
    steps_completed: List[str]
    steps_failed: List[str]
    validation_results: Dict[str, Any]
    error_message: Optional[str] = None

class UserManagementRollback:
    """
    Comprehensive rollback system for user management deployments.
    
    Provides:
    - Database rollback with integrity verification
    - Configuration restoration
    - Application code rollback
    - Service restart and validation
    - Post-rollback health checks
    - Rollback point management
    """
    
    def __init__(self, config: Config):
        """
        Initialize rollback system.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.db_manager = DatabaseManager(config)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Rollback configuration
        self.backup_base_dir = Path("backups")
        self.rollback_points_file = self.backup_base_dir / "rollback_points.json"
        
        # Ensure backup directory exists
        self.backup_base_dir.mkdir(exist_ok=True)
        
        # Load existing rollback points
        self.rollback_points = self._load_rollback_points()
    
    def _load_rollback_points(self) -> List[RollbackPoint]:
        """Load rollback points from storage"""
        if not self.rollback_points_file.exists():
            return []
        
        try:
            with open(self.rollback_points_file, 'r') as f:
                data = json.load(f)
            
            rollback_points = []
            for item in data:
                rollback_points.append(RollbackPoint(
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    version=item['version'],
                    description=item['description'],
                    database_backup=item['database_backup'],
                    config_backup=item['config_backup'],
                    application_backup=item['application_backup'],
                    validation_data=item['validation_data']
                ))
            
            return rollback_points
            
        except Exception as e:
            self.logger.error(f"Error loading rollback points: {e}")
            return []
    
    def _save_rollback_points(self) -> None:
        """Save rollback points to storage"""
        try:
            data = []
            for rp in self.rollback_points:
                data.append({
                    'timestamp': rp.timestamp.isoformat(),
                    'version': rp.version,
                    'description': rp.description,
                    'database_backup': rp.database_backup,
                    'config_backup': rp.config_backup,
                    'application_backup': rp.application_backup,
                    'validation_data': rp.validation_data
                })
            
            with open(self.rollback_points_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving rollback points: {e}")
    
    def create_rollback_point(self, version: str, description: str) -> RollbackPoint:
        """
        Create a new rollback point with complete system backup.
        
        Args:
            version: Version identifier for this rollback point
            description: Human-readable description
        
        Returns:
            Created rollback point
        """
        self.logger.info(f"Creating rollback point: {version} - {description}")
        
        timestamp = datetime.utcnow()
        backup_dir = self.backup_base_dir / f"rollback_{version}_{int(timestamp.timestamp())}"
        backup_dir.mkdir(exist_ok=True)
        
        try:
            # Create database backup
            database_backup = self._create_database_backup(backup_dir)
            
            # Create configuration backup
            config_backup = self._create_config_backup(backup_dir)
            
            # Create application backup
            application_backup = self._create_application_backup(backup_dir)
            
            # Collect validation data
            validation_data = self._collect_validation_data()
            
            # Create rollback point
            rollback_point = RollbackPoint(
                timestamp=timestamp,
                version=version,
                description=description,
                database_backup=database_backup,
                config_backup=config_backup,
                application_backup=application_backup,
                validation_data=validation_data
            )
            
            # Add to rollback points and save
            self.rollback_points.append(rollback_point)
            self._save_rollback_points()
            
            self.logger.info(f"Rollback point created successfully: {version}")
            return rollback_point
            
        except Exception as e:
            self.logger.error(f"Error creating rollback point: {e}")
            # Clean up partial backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            raise
    
    def _create_database_backup(self, backup_dir: Path) -> str:
        """Create database backup"""
        self.logger.info("Creating database backup")
        
        db_path = Path(self.config.storage.database_path)
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        backup_path = backup_dir / "MySQL database"
        shutil.copy2(db_path, backup_path)
        
        # Verify backup integrity
        try:
            from sqlalchemy import create_engine
            engine = create_engine(f"mysql+pymysql://{backup_path}")
            with engine.connect() as conn:
                conn.execute("PRAGMA integrity_check").fetchone()
            self.logger.info("Database backup integrity verified")
        except Exception as e:
            raise Exception(f"Database backup integrity check failed: {e}")
        
        return str(backup_path)
    
    def _create_config_backup(self, backup_dir: Path) -> str:
        """Create configuration backup"""
        self.logger.info("Creating configuration backup")
        
        config_backup_dir = backup_dir / "config"
        config_backup_dir.mkdir(exist_ok=True)
        
        # Backup .env file
        env_file = Path(".env")
        if env_file.exists():
            shutil.copy2(env_file, config_backup_dir / ".env")
        
        # Backup other configuration files
        config_files = [
            "config.py",
            "alembic.ini"
        ]
        
        for config_file in config_files:
            file_path = Path(config_file)
            if file_path.exists():
                shutil.copy2(file_path, config_backup_dir / config_file)
        
        return str(config_backup_dir)
    
    def _create_application_backup(self, backup_dir: Path) -> str:
        """Create application code backup"""
        self.logger.info("Creating application backup")
        
        app_backup_path = backup_dir / "application_backup.tar.gz"
        
        # Create tar archive of application code
        cmd = [
            "tar", "-czf", str(app_backup_path),
            "--exclude=storage",
            "--exclude=__pycache__",
            "--exclude=.git",
            "--exclude=backups",
            "--exclude=logs",
            "--exclude=*.pyc",
            "."
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Application backup failed: {result.stderr}")
        
        return str(app_backup_path)
    
    def _collect_validation_data(self) -> Dict[str, Any]:
        """Collect validation data for rollback verification"""
        self.logger.info("Collecting validation data")
        
        validation_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'database_stats': {},
            'system_stats': {},
            'configuration': {}
        }
        
        try:
            # Database statistics
            session = self.db_manager.get_session()
            
            from models import User, UserSession, UserAuditLog
            
            validation_data['database_stats'] = {
                'user_count': session.query(User).count(),
                'active_session_count': session.query(UserSession).filter_by(is_active=True).count(),
                'audit_log_count': session.query(UserAuditLog).count(),
                'admin_user_count': session.query(User).filter_by(role='admin').count(),
                'verified_user_count': session.query(User).filter_by(email_verified=True).count()
            }
            
            session.close()
            
            # System statistics
            try:
                import psutil
                validation_data['system_stats'] = {
                    'memory_percent': psutil.virtual_memory().percent,
                    'cpu_percent': psutil.cpu_percent(),
                    'disk_percent': psutil.disk_usage('/').percent
                }
            except ImportError:
                pass
            
            # Configuration snapshot
            validation_data['configuration'] = {
                'database_url': self.config.storage.database_url,
                'session_timeout': getattr(self.config, 'session_timeout', None),
                'email_configured': bool(os.getenv('MAIL_SERVER'))
            }
            
        except Exception as e:
            self.logger.warning(f"Error collecting validation data: {e}")
        
        return validation_data
    
    def list_rollback_points(self) -> List[RollbackPoint]:
        """
        List available rollback points.
        
        Returns:
            List of available rollback points
        """
        return sorted(self.rollback_points, key=lambda rp: rp.timestamp, reverse=True)
    
    def get_rollback_point(self, version: str) -> Optional[RollbackPoint]:
        """
        Get specific rollback point by version.
        
        Args:
            version: Version identifier
        
        Returns:
            Rollback point if found, None otherwise
        """
        return next((rp for rp in self.rollback_points if rp.version == version), None)
    
    def execute_rollback(self, rollback_point: RollbackPoint, force: bool = False) -> RollbackResult:
        """
        Execute rollback to specified point.
        
        Args:
            rollback_point: Rollback point to restore to
            force: Force rollback even if validation fails
        
        Returns:
            Rollback result with success status and details
        """
        self.logger.info(f"Starting rollback to version {rollback_point.version}")
        
        steps_completed = []
        steps_failed = []
        
        try:
            # Pre-rollback validation
            if not force:
                self.logger.info("Performing pre-rollback validation")
                validation_result = self._validate_rollback_point(rollback_point)
                if not validation_result['valid']:
                    return RollbackResult(
                        success=False,
                        rollback_point=rollback_point,
                        steps_completed=steps_completed,
                        steps_failed=['pre_rollback_validation'],
                        validation_results=validation_result,
                        error_message=f"Pre-rollback validation failed: {validation_result['errors']}"
                    )
            
            # Stop services
            self.logger.info("Stopping application services")
            if self._stop_services():
                steps_completed.append('stop_services')
            else:
                steps_failed.append('stop_services')
                self.logger.warning("Failed to stop services, continuing with rollback")
            
            # Rollback database
            self.logger.info("Rolling back database")
            if self._rollback_database(rollback_point):
                steps_completed.append('rollback_database')
            else:
                steps_failed.append('rollback_database')
                raise Exception("Database rollback failed")
            
            # Rollback configuration
            self.logger.info("Rolling back configuration")
            if self._rollback_configuration(rollback_point):
                steps_completed.append('rollback_configuration')
            else:
                steps_failed.append('rollback_configuration')
                raise Exception("Configuration rollback failed")
            
            # Rollback application code
            self.logger.info("Rolling back application code")
            if self._rollback_application(rollback_point):
                steps_completed.append('rollback_application')
            else:
                steps_failed.append('rollback_application')
                raise Exception("Application rollback failed")
            
            # Start services
            self.logger.info("Starting application services")
            if self._start_services():
                steps_completed.append('start_services')
            else:
                steps_failed.append('start_services')
                raise Exception("Failed to start services after rollback")
            
            # Post-rollback validation
            self.logger.info("Performing post-rollback validation")
            validation_results = self._validate_post_rollback(rollback_point)
            
            if validation_results['valid']:
                steps_completed.append('post_rollback_validation')
                self.logger.info(f"Rollback to version {rollback_point.version} completed successfully")
                
                return RollbackResult(
                    success=True,
                    rollback_point=rollback_point,
                    steps_completed=steps_completed,
                    steps_failed=steps_failed,
                    validation_results=validation_results
                )
            else:
                steps_failed.append('post_rollback_validation')
                error_msg = f"Post-rollback validation failed: {validation_results['errors']}"
                
                if not force:
                    raise Exception(error_msg)
                else:
                    self.logger.warning(f"Rollback completed with validation warnings: {error_msg}")
                    return RollbackResult(
                        success=True,
                        rollback_point=rollback_point,
                        steps_completed=steps_completed,
                        steps_failed=steps_failed,
                        validation_results=validation_results,
                        error_message=error_msg
                    )
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            
            # Attempt to restart services even if rollback failed
            try:
                self._start_services()
            except:
                pass
            
            return RollbackResult(
                success=False,
                rollback_point=rollback_point,
                steps_completed=steps_completed,
                steps_failed=steps_failed,
                validation_results={},
                error_message=str(e)
            )
    
    def _validate_rollback_point(self, rollback_point: RollbackPoint) -> Dict[str, Any]:
        """Validate rollback point before execution"""
        errors = []
        warnings = []
        
        # Check if backup files exist
        if not Path(rollback_point.database_backup).exists():
            errors.append(f"Database backup not found: {rollback_point.database_backup}")
        
        if not Path(rollback_point.config_backup).exists():
            errors.append(f"Configuration backup not found: {rollback_point.config_backup}")
        
        if not Path(rollback_point.application_backup).exists():
            errors.append(f"Application backup not found: {rollback_point.application_backup}")
        
        # Check backup age
        backup_age = datetime.utcnow() - rollback_point.timestamp
        if backup_age > timedelta(days=30):
            warnings.append(f"Rollback point is {backup_age.days} days old")
        
        # Validate database backup integrity
        try:
            from sqlalchemy import create_engine
            engine = create_engine(f"mysql+pymysql://{rollback_point.database_backup}")
            with engine.connect() as conn:
                conn.execute("PRAGMA integrity_check").fetchone()
        except Exception as e:
            errors.append(f"Database backup integrity check failed: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _stop_services(self) -> bool:
        """Stop application services"""
        try:
            # Find and stop web application processes
            result = subprocess.run(
                ["pkill", "-f", "web_app.py"],
                capture_output=True,
                text=True
            )
            
            # Wait for processes to stop
            time.sleep(5)
            
            # Check if processes are still running
            result = subprocess.run(
                ["pgrep", "-f", "web_app.py"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.warning("Some processes may still be running")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
            return False
    
    def _start_services(self) -> bool:
        """Start application services"""
        try:
            # Start web application
            subprocess.Popen(
                [sys.executable, "web_app.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for service to start
            time.sleep(10)
            
            # Check if service is running
            result = subprocess.run(
                ["pgrep", "-f", "web_app.py"],
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            return False
    
    def _rollback_database(self, rollback_point: RollbackPoint) -> bool:
        """Rollback database to backup"""
        try:
            db_path = Path(self.config.storage.database_path)
            backup_path = Path(rollback_point.database_backup)
            
            # Create backup of current database
            current_backup = db_path.with_suffix('.db.pre_rollback')
            if db_path.exists():
                shutil.copy2(db_path, current_backup)
            
            # Restore database from backup
            shutil.copy2(backup_path, db_path)
            
            # Verify restored database
            try:
                from sqlalchemy import create_engine
                engine = create_engine(f"mysql+pymysql://{db_path}")
                with engine.connect() as conn:
                    conn.execute("PRAGMA integrity_check").fetchone()
                return True
            except Exception as e:
                # Restore current database if verification fails
                if current_backup.exists():
                    shutil.copy2(current_backup, db_path)
                raise Exception(f"Database verification failed after rollback: {e}")
            
        except Exception as e:
            self.logger.error(f"Database rollback failed: {e}")
            return False
    
    def _rollback_configuration(self, rollback_point: RollbackPoint) -> bool:
        """Rollback configuration files"""
        try:
            config_backup_dir = Path(rollback_point.config_backup)
            
            # Backup current configuration
            current_env = Path(".env")
            if current_env.exists():
                shutil.copy2(current_env, current_env.with_suffix('.env.pre_rollback'))
            
            # Restore configuration files
            for config_file in config_backup_dir.iterdir():
                if config_file.is_file():
                    target_path = Path(config_file.name)
                    shutil.copy2(config_file, target_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration rollback failed: {e}")
            return False
    
    def _rollback_application(self, rollback_point: RollbackPoint) -> bool:
        """Rollback application code"""
        try:
            app_backup_path = Path(rollback_point.application_backup)
            
            # Create backup of current application
            current_backup = Path(f"application_backup_pre_rollback_{int(time.time())}.tar.gz")
            subprocess.run([
                "tar", "-czf", str(current_backup),
                "--exclude=storage",
                "--exclude=backups",
                "--exclude=logs",
                "."
            ], check=True)
            
            # Extract application backup
            subprocess.run([
                "tar", "-xzf", str(app_backup_path)
            ], check=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Application rollback failed: {e}")
            return False
    
    def _validate_post_rollback(self, rollback_point: RollbackPoint) -> Dict[str, Any]:
        """Validate system after rollback"""
        errors = []
        warnings = []
        
        try:
            # Test database connectivity
            session = self.db_manager.get_session()
            session.execute("SELECT 1").scalar()
            session.close()
        except Exception as e:
            errors.append(f"Database connectivity test failed: {e}")
        
        # Test web service
        try:
            import requests
            response = requests.get("http://localhost:5000/health", timeout=10)
            if response.status_code != 200:
                warnings.append(f"Web service health check returned status {response.status_code}")
        except Exception as e:
            warnings.append(f"Web service health check failed: {e}")
        
        # Compare validation data
        try:
            current_validation = self._collect_validation_data()
            original_validation = rollback_point.validation_data
            
            # Compare database stats
            current_db_stats = current_validation.get('database_stats', {})
            original_db_stats = original_validation.get('database_stats', {})
            
            for key, original_value in original_db_stats.items():
                current_value = current_db_stats.get(key, 0)
                if abs(current_value - original_value) > original_value * 0.1:  # 10% tolerance
                    warnings.append(f"Database stat {key} differs significantly: {current_value} vs {original_value}")
            
        except Exception as e:
            warnings.append(f"Validation data comparison failed: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def cleanup_old_rollback_points(self, keep_days: int = 30) -> int:
        """
        Clean up old rollback points.
        
        Args:
            keep_days: Number of days to keep rollback points
        
        Returns:
            Number of rollback points cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        cleaned_count = 0
        
        rollback_points_to_keep = []
        
        for rp in self.rollback_points:
            if rp.timestamp < cutoff_date:
                try:
                    # Remove backup files
                    for backup_path in [rp.database_backup, rp.config_backup, rp.application_backup]:
                        path = Path(backup_path)
                        if path.exists():
                            if path.is_dir():
                                shutil.rmtree(path)
                            else:
                                path.unlink()
                    
                    cleaned_count += 1
                    self.logger.info(f"Cleaned up rollback point: {rp.version}")
                    
                except Exception as e:
                    self.logger.error(f"Error cleaning up rollback point {rp.version}: {e}")
                    rollback_points_to_keep.append(rp)
            else:
                rollback_points_to_keep.append(rp)
        
        self.rollback_points = rollback_points_to_keep
        self._save_rollback_points()
        
        return cleaned_count

def main():
    """Main rollback script entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='User Management Rollback System')
    parser.add_argument('action', choices=['create', 'list', 'rollback', 'cleanup'], help='Action to perform')
    parser.add_argument('--version', help='Version identifier for rollback point')
    parser.add_argument('--description', help='Description for rollback point')
    parser.add_argument('--force', action='store_true', help='Force rollback even if validation fails')
    parser.add_argument('--keep-days', type=int, default=30, help='Days to keep rollback points (for cleanup)')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        config = Config()
        rollback_system = UserManagementRollback(config)
        
        if args.action == 'create':
            if not args.version:
                print("Error: --version required for create action")
                return 1
            
            description = args.description or f"Rollback point created at {datetime.utcnow()}"
            rollback_point = rollback_system.create_rollback_point(args.version, description)
            print(f"Rollback point created: {rollback_point.version}")
            print(f"Timestamp: {rollback_point.timestamp}")
            print(f"Description: {rollback_point.description}")
            
        elif args.action == 'list':
            rollback_points = rollback_system.list_rollback_points()
            if not rollback_points:
                print("No rollback points found")
            else:
                print(f"{'Version':<20} {'Timestamp':<20} {'Description'}")
                print("-" * 80)
                for rp in rollback_points:
                    print(f"{rp.version:<20} {rp.timestamp.strftime('%Y-%m-%d %H:%M'):<20} {rp.description}")
        
        elif args.action == 'rollback':
            if not args.version:
                print("Error: --version required for rollback action")
                return 1
            
            rollback_point = rollback_system.get_rollback_point(args.version)
            if not rollback_point:
                print(f"Error: Rollback point not found: {args.version}")
                return 1
            
            print(f"Rolling back to version: {rollback_point.version}")
            print(f"Description: {rollback_point.description}")
            print(f"Timestamp: {rollback_point.timestamp}")
            
            if not args.force:
                confirm = input("Are you sure you want to proceed? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("Rollback cancelled")
                    return 0
            
            result = rollback_system.execute_rollback(rollback_point, args.force)
            
            if result.success:
                print("Rollback completed successfully!")
                print(f"Steps completed: {', '.join(result.steps_completed)}")
                if result.steps_failed:
                    print(f"Steps with issues: {', '.join(result.steps_failed)}")
                if result.error_message:
                    print(f"Warnings: {result.error_message}")
            else:
                print("Rollback failed!")
                print(f"Error: {result.error_message}")
                print(f"Steps completed: {', '.join(result.steps_completed)}")
                print(f"Steps failed: {', '.join(result.steps_failed)}")
                return 1
        
        elif args.action == 'cleanup':
            cleaned_count = rollback_system.cleanup_old_rollback_points(args.keep_days)
            print(f"Cleaned up {cleaned_count} old rollback points")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())