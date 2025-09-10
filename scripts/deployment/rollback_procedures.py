# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Rollback Procedures for Multi-Tenant Admin Deployment
Provides safe rollback mechanisms for deployment reversal
"""

import os
import sys
import json
import shutil
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from admin.feature_flags import FeatureFlagManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/rollback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RollbackManager:
    """Manages safe rollback procedures for admin deployment"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.feature_manager = FeatureFlagManager()
        self.rollback_state_file = "storage/rollback_state.json"
        
    def create_rollback_point(self, description: str = None) -> str:
        """Create a rollback point before deployment"""
        logger.info("Creating rollback point...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_id = f"rollback_{timestamp}"
        
        rollback_data = {
            'rollback_id': rollback_id,
            'timestamp': timestamp,
            'description': description or f"Rollback point created at {timestamp}",
            'database_backup': None,
            'feature_flags_backup': None,
            'config_backup': None,
            'application_state': self._capture_application_state()
        }
        
        try:
            # Create database backup
            rollback_data['database_backup'] = self._create_database_backup(rollback_id)
            
            # Backup feature flags
            rollback_data['feature_flags_backup'] = self._backup_feature_flags(rollback_id)
            
            # Backup configuration
            rollback_data['config_backup'] = self._backup_configuration(rollback_id)
            
            # Save rollback state
            self._save_rollback_state(rollback_data)
            
            logger.info(f"✅ Rollback point created: {rollback_id}")
            return rollback_id
            
        except Exception as e:
            logger.error(f"Failed to create rollback point: {e}")
            raise
    
    def _capture_application_state(self) -> Dict[str, Any]:
        """Capture current application state"""
        try:
            with self.db_manager.get_session() as session:
                # Count active jobs
                active_jobs = session.execute(
                    "SELECT COUNT(*) FROM caption_generation_tasks WHERE status IN ('pending', 'running')"
                ).scalar()
                
                # Count users
                user_count = session.execute("SELECT COUNT(*) FROM users").scalar()
                
                # Check for admin tables
                admin_tables = []
                tables_to_check = [
                    'system_configuration', 'job_audit_log', 'alert_configuration',
                    'system_alerts', 'performance_metrics'
                ]
                
                for table in tables_to_check:
                    try:
                        session.execute(f"SELECT 1 FROM {table} LIMIT 1")
                        admin_tables.append(table)
                    except:
                        pass
                
                return {
                    'active_jobs': active_jobs,
                    'user_count': user_count,
                    'admin_tables_present': admin_tables,
                    'feature_flags': self.feature_manager.list_flags()
                }
                
        except Exception as e:
            logger.warning(f"Could not capture full application state: {e}")
            return {'error': str(e)}
    
    def _create_database_backup(self, rollback_id: str) -> str:
        """Create database backup for rollback"""
        backup_dir = Path("storage/backups/rollback")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"{rollback_id}_database.sql"
        
        # MySQL backup command
        db_config = self.config.get_database_config()
        backup_cmd = f"""mysqldump -h {db_config.get('host', 'localhost')} \
                        -P {db_config.get('port', 3306)} \
                        -u {db_config.get('user')} \
                        -p{db_config.get('password')} \
                        --single-transaction --routines --triggers \
                        {db_config.get('database')} > {backup_file}"""
        
        result = os.system(backup_cmd)
        if result != 0:
            raise Exception(f"Database backup failed with exit code {result}")
        
        logger.info(f"Database backup created: {backup_file}")
        return str(backup_file)
    
    def _backup_feature_flags(self, rollback_id: str) -> str:
        """Backup current feature flags configuration"""
        backup_dir = Path("storage/backups/rollback")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"{rollback_id}_feature_flags.json"
        
        flags_data = {
            'flags': self.feature_manager.list_flags(),
            'backup_timestamp': datetime.now().isoformat()
        }
        
        with open(backup_file, 'w') as f:
            json.dump(flags_data, f, indent=2)
        
        logger.info(f"Feature flags backup created: {backup_file}")
        return str(backup_file)
    
    def _backup_configuration(self, rollback_id: str) -> str:
        """Backup current configuration files"""
        backup_dir = Path("storage/backups/rollback")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        config_backup_dir = backup_dir / f"{rollback_id}_config"
        config_backup_dir.mkdir(exist_ok=True)
        
        # Backup important config files
        config_files = [
            '.env',
            'config/feature_flags.json',
            'config/admin_settings.json'
        ]
        
        backed_up_files = []
        for config_file in config_files:
            if os.path.exists(config_file):
                dest = config_backup_dir / Path(config_file).name
                shutil.copy2(config_file, dest)
                backed_up_files.append(str(dest))
        
        logger.info(f"Configuration backup created: {config_backup_dir}")
        return str(config_backup_dir)
    
    def _save_rollback_state(self, rollback_data: Dict[str, Any]):
        """Save rollback state to file"""
        os.makedirs(os.path.dirname(self.rollback_state_file), exist_ok=True)
        
        # Load existing rollback states
        existing_states = []
        if os.path.exists(self.rollback_state_file):
            try:
                with open(self.rollback_state_file, 'r') as f:
                    existing_states = json.load(f)
            except:
                existing_states = []
        
        # Add new rollback state
        existing_states.append(rollback_data)
        
        # Keep only last 10 rollback points
        existing_states = existing_states[-10:]
        
        with open(self.rollback_state_file, 'w') as f:
            json.dump(existing_states, f, indent=2)
    
    def list_rollback_points(self) -> List[Dict[str, Any]]:
        """List available rollback points"""
        if not os.path.exists(self.rollback_state_file):
            return []
        
        try:
            with open(self.rollback_state_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def execute_rollback(self, rollback_id: str, confirm: bool = False) -> bool:
        """Execute rollback to a specific point"""
        if not confirm:
            logger.error("Rollback requires explicit confirmation")
            return False
        
        logger.info(f"🚨 EXECUTING ROLLBACK TO: {rollback_id}")
        
        # Find rollback point
        rollback_points = self.list_rollback_points()
        rollback_data = None
        
        for point in rollback_points:
            if point['rollback_id'] == rollback_id:
                rollback_data = point
                break
        
        if not rollback_data:
            logger.error(f"Rollback point not found: {rollback_id}")
            return False
        
        try:
            # Step 1: Disable all admin features immediately
            logger.info("Step 1: Disabling admin features...")
            self._emergency_disable_admin_features()
            
            # Step 2: Restore database
            logger.info("Step 2: Restoring database...")
            if rollback_data.get('database_backup'):
                self._restore_database(rollback_data['database_backup'])
            
            # Step 3: Restore feature flags
            logger.info("Step 3: Restoring feature flags...")
            if rollback_data.get('feature_flags_backup'):
                self._restore_feature_flags(rollback_data['feature_flags_backup'])
            
            # Step 4: Restore configuration
            logger.info("Step 4: Restoring configuration...")
            if rollback_data.get('config_backup'):
                self._restore_configuration(rollback_data['config_backup'])
            
            # Step 5: Verify rollback
            logger.info("Step 5: Verifying rollback...")
            self._verify_rollback(rollback_data)
            
            logger.info("✅ Rollback completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
    
    def _emergency_disable_admin_features(self):
        """Emergency disable all admin features"""
        admin_flags = [
            'multi_tenant_admin',
            'admin_dashboard',
            'admin_job_management', 
            'admin_user_management',
            'system_monitoring',
            'alert_system',
            'real_time_updates'
        ]
        
        for flag in admin_flags:
            try:
                self.feature_manager.disable_flag(flag)
            except Exception as e:
                logger.warning(f"Could not disable flag {flag}: {e}")
    
    def _restore_database(self, backup_file: str):
        """Restore database from backup"""
        if not os.path.exists(backup_file):
            raise Exception(f"Database backup file not found: {backup_file}")
        
        db_config = self.config.get_database_config()
        restore_cmd = f"""mysql -h {db_config.get('host', 'localhost')} \
                         -P {db_config.get('port', 3306)} \
                         -u {db_config.get('user')} \
                         -p{db_config.get('password')} \
                         {db_config.get('database')} < {backup_file}"""
        
        result = os.system(restore_cmd)
        if result != 0:
            raise Exception(f"Database restore failed with exit code {result}")
        
        logger.info("Database restored successfully")
    
    def _restore_feature_flags(self, backup_file: str):
        """Restore feature flags from backup"""
        if not os.path.exists(backup_file):
            logger.warning(f"Feature flags backup not found: {backup_file}")
            return
        
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Restore each flag
            for flag_name, flag_data in backup_data.get('flags', {}).items():
                if flag_data['state'] == 'enabled':
                    self.feature_manager.enable_flag(flag_name)
                else:
                    self.feature_manager.disable_flag(flag_name)
            
            logger.info("Feature flags restored successfully")
            
        except Exception as e:
            logger.warning(f"Could not restore feature flags: {e}")
    
    def _restore_configuration(self, backup_dir: str):
        """Restore configuration files from backup"""
        if not os.path.exists(backup_dir):
            logger.warning(f"Configuration backup not found: {backup_dir}")
            return
        
        try:
            backup_path = Path(backup_dir)
            
            # Restore .env file
            env_backup = backup_path / '.env'
            if env_backup.exists():
                shutil.copy2(env_backup, '.env')
            
            # Restore other config files
            for config_file in backup_path.glob('*.json'):
                dest_path = Path('config') / config_file.name
                dest_path.parent.mkdir(exist_ok=True)
                shutil.copy2(config_file, dest_path)
            
            logger.info("Configuration restored successfully")
            
        except Exception as e:
            logger.warning(f"Could not restore configuration: {e}")
    
    def _verify_rollback(self, rollback_data: Dict[str, Any]):
        """Verify rollback was successful"""
        try:
            # Check database connectivity
            with self.db_manager.get_session() as session:
                session.execute("SELECT 1")
            
            # Check application state
            current_state = self._capture_application_state()
            original_state = rollback_data.get('application_state', {})
            
            logger.info("Rollback verification:")
            logger.info(f"  Database: ✅ Connected")
            logger.info(f"  Users: {current_state.get('user_count', 'Unknown')}")
            logger.info(f"  Active jobs: {current_state.get('active_jobs', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"Rollback verification issues: {e}")
    
    def emergency_rollback(self) -> bool:
        """Emergency rollback to most recent point"""
        logger.info("🚨 EMERGENCY ROLLBACK INITIATED")
        
        rollback_points = self.list_rollback_points()
        if not rollback_points:
            logger.error("No rollback points available")
            return False
        
        # Use most recent rollback point
        latest_point = rollback_points[-1]
        logger.info(f"Using latest rollback point: {latest_point['rollback_id']}")
        
        return self.execute_rollback(latest_point['rollback_id'], confirm=True)
    
    def cleanup_old_rollback_points(self, keep_count: int = 5):
        """Clean up old rollback points"""
        rollback_points = self.list_rollback_points()
        
        if len(rollback_points) <= keep_count:
            logger.info("No old rollback points to clean up")
            return
        
        # Keep only the most recent points
        points_to_keep = rollback_points[-keep_count:]
        points_to_remove = rollback_points[:-keep_count]
        
        for point in points_to_remove:
            try:
                # Remove backup files
                if point.get('database_backup') and os.path.exists(point['database_backup']):
                    os.remove(point['database_backup'])
                
                if point.get('feature_flags_backup') and os.path.exists(point['feature_flags_backup']):
                    os.remove(point['feature_flags_backup'])
                
                if point.get('config_backup') and os.path.exists(point['config_backup']):
                    shutil.rmtree(point['config_backup'])
                
                logger.info(f"Cleaned up rollback point: {point['rollback_id']}")
                
            except Exception as e:
                logger.warning(f"Could not clean up {point['rollback_id']}: {e}")
        
        # Update rollback state file
        with open(self.rollback_state_file, 'w') as f:
            json.dump(points_to_keep, f, indent=2)
        
        logger.info(f"Cleanup completed: kept {len(points_to_keep)} rollback points")

def main():
    parser = argparse.ArgumentParser(description='Rollback Management')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create rollback point
    create_parser = subparsers.add_parser('create', help='Create rollback point')
    create_parser.add_argument('--description', help='Description for rollback point')
    
    # List rollback points
    list_parser = subparsers.add_parser('list', help='List rollback points')
    
    # Execute rollback
    rollback_parser = subparsers.add_parser('rollback', help='Execute rollback')
    rollback_parser.add_argument('rollback_id', help='Rollback point ID')
    rollback_parser.add_argument('--confirm', action='store_true', 
                                help='Confirm rollback execution')
    
    # Emergency rollback
    emergency_parser = subparsers.add_parser('emergency', help='Emergency rollback')
    emergency_parser.add_argument('--confirm', action='store_true',
                                 help='Confirm emergency rollback')
    
    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old rollback points')
    cleanup_parser.add_argument('--keep', type=int, default=5,
                               help='Number of rollback points to keep')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = RollbackManager()
    
    if args.command == 'create':
        rollback_id = manager.create_rollback_point(args.description)
        print(f"Created rollback point: {rollback_id}")
        
    elif args.command == 'list':
        points = manager.list_rollback_points()
        if not points:
            print("No rollback points available")
        else:
            print("Available rollback points:")
            for point in points:
                print(f"  {point['rollback_id']}: {point['description']}")
                
    elif args.command == 'rollback':
        if not args.confirm:
            print("❌ Rollback requires --confirm flag")
            sys.exit(1)
        
        success = manager.execute_rollback(args.rollback_id, confirm=True)
        sys.exit(0 if success else 1)
        
    elif args.command == 'emergency':
        if not args.confirm:
            print("❌ Emergency rollback requires --confirm flag")
            sys.exit(1)
        
        success = manager.emergency_rollback()
        sys.exit(0 if success else 1)
        
    elif args.command == 'cleanup':
        manager.cleanup_old_rollback_points(args.keep)

if __name__ == '__main__':
    main()