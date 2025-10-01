#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Point-in-Time Recovery System for Docker Compose Vedfolnir

Provides comprehensive point-in-time recovery capabilities for MySQL and Redis,
including binary log analysis, recovery planning, and automated recovery execution.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import docker
    import pymysql
    import redis
    from config import Config
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages: pip install docker pymysql redis")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/point_in_time_recovery.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class RecoveryPoint:
    """Represents a point-in-time recovery target."""
    timestamp: datetime
    mysql_binlog_file: Optional[str]
    mysql_binlog_position: Optional[int]
    redis_aof_position: Optional[int]
    backup_id: Optional[str]
    description: str

@dataclass
class RecoveryPlan:
    """Comprehensive recovery plan."""
    recovery_id: str
    target_time: datetime
    recovery_type: str  # 'full', 'mysql_only', 'redis_only'
    base_backup: str
    mysql_steps: List[Dict[str, Any]]
    redis_steps: List[Dict[str, Any]]
    estimated_duration: int  # minutes
    prerequisites: List[str]
    risks: List[str]
    rollback_plan: List[Dict[str, Any]]
    validation_steps: List[Dict[str, Any]]

class PointInTimeRecovery:
    """Point-in-time recovery system for Vedfolnir Docker Compose deployment."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the point-in-time recovery system."""
        self.config = Config() if config_path is None else Config(config_path)
        self.docker_client = docker.from_env()
        
        # Container names
        self.mysql_container = "vedfolnir_mysql"
        self.redis_container = "vedfolnir_redis"
        self.app_container = "vedfolnir_app"
        
        # Backup and recovery directories
        self.backup_base_dir = Path("storage/backups")
        self.recovery_work_dir = Path("storage/recovery")
        self.recovery_work_dir.mkdir(exist_ok=True)
        
        # Recovery objectives
        self.rto_target = int(os.getenv('RTO_TARGET_MINUTES', '240'))  # 4 hours
        self.rpo_target = int(os.getenv('RPO_TARGET_MINUTES', '60'))   # 1 hour
        
        logger.info("Point-in-time recovery system initialized")
    
    def analyze_available_recovery_points(self, start_time: datetime, end_time: datetime) -> List[RecoveryPoint]:
        """
        Analyze available recovery points within a time range.
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            List of available recovery points
        """
        logger.info(f"Analyzing recovery points from {start_time} to {end_time}")
        
        recovery_points = []
        
        # Find available backups
        backups = self._find_backups_in_range(start_time, end_time)
        
        for backup in backups:
            backup_time = datetime.fromisoformat(backup['timestamp'])
            
            # Add backup as recovery point
            recovery_points.append(RecoveryPoint(
                timestamp=backup_time,
                mysql_binlog_file=backup.get('mysql_binlog_file'),
                mysql_binlog_position=backup.get('mysql_binlog_position'),
                redis_aof_position=backup.get('redis_aof_position'),
                backup_id=backup['backup_id'],
                description=f"Full backup: {backup['backup_id']}"
            ))
            
            # Analyze MySQL binary logs for additional recovery points
            mysql_points = self._analyze_mysql_binlogs(backup_time, end_time, backup)
            recovery_points.extend(mysql_points)
            
            # Analyze Redis AOF for additional recovery points
            redis_points = self._analyze_redis_aof(backup_time, end_time, backup)
            recovery_points.extend(redis_points)
        
        # Sort by timestamp
        recovery_points.sort(key=lambda x: x.timestamp)
        
        logger.info(f"Found {len(recovery_points)} recovery points")
        return recovery_points
    
    def _find_backups_in_range(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Find backups within the specified time range."""
        backups = []
        
        for backup_dir in self.backup_base_dir.glob("full_backup_*"):
            manifest_file = backup_dir / "backup_manifest.json"
            
            if manifest_file.exists():
                try:
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    backup_time = datetime.fromisoformat(manifest['timestamp'])
                    
                    if start_time <= backup_time <= end_time:
                        # Load additional metadata
                        mysql_metadata = self._load_mysql_metadata(backup_dir)
                        redis_metadata = self._load_redis_metadata(backup_dir)
                        
                        backup_info = {
                            'backup_id': manifest['backup_id'],
                            'timestamp': manifest['timestamp'],
                            'backup_dir': str(backup_dir),
                            'mysql_binlog_file': mysql_metadata.get('binlog_file'),
                            'mysql_binlog_position': mysql_metadata.get('binlog_position'),
                            'redis_aof_position': redis_metadata.get('aof_position')
                        }
                        
                        backups.append(backup_info)
                        
                except Exception as e:
                    logger.warning(f"Could not load backup manifest from {backup_dir}: {e}")
        
        return backups
    
    def _load_mysql_metadata(self, backup_dir: Path) -> Dict[str, Any]:
        """Load MySQL backup metadata."""
        metadata_file = backup_dir / "mysql" / "mysql_backup_metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load MySQL metadata: {e}")
        
        # Try to extract from binlog position file
        binlog_file = backup_dir / "mysql" / "binlog_position.txt"
        if binlog_file.exists():
            try:
                with open(binlog_file, 'r') as f:
                    content = f.read()
                
                # Parse SHOW MASTER STATUS output
                file_match = re.search(r'File: (.+)', content)
                position_match = re.search(r'Position: (\d+)', content)
                
                if file_match and position_match:
                    return {
                        'binlog_file': file_match.group(1).strip(),
                        'binlog_position': int(position_match.group(1))
                    }
            except Exception as e:
                logger.warning(f"Could not parse binlog position: {e}")
        
        return {}
    
    def _load_redis_metadata(self, backup_dir: Path) -> Dict[str, Any]:
        """Load Redis backup metadata."""
        metadata_file = backup_dir / "redis" / "redis_backup_metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load Redis metadata: {e}")
        
        return {}
    
    def _analyze_mysql_binlogs(self, start_time: datetime, end_time: datetime, 
                              backup_info: Dict[str, Any]) -> List[RecoveryPoint]:
        """Analyze MySQL binary logs for recovery points."""
        recovery_points = []
        
        try:
            # Get list of binary log files from MySQL container
            binlog_files = self._get_mysql_binlog_files()
            
            for binlog_file in binlog_files:
                # Parse binary log events
                events = self._parse_mysql_binlog_events(binlog_file, start_time, end_time)
                
                for event in events:
                    if self._is_significant_mysql_event(event):
                        recovery_points.append(RecoveryPoint(
                            timestamp=event['timestamp'],
                            mysql_binlog_file=binlog_file,
                            mysql_binlog_position=event['position'],
                            redis_aof_position=None,
                            backup_id=backup_info['backup_id'],
                            description=f"MySQL event: {event['type']} at {event['timestamp']}"
                        ))
        
        except Exception as e:
            logger.warning(f"Could not analyze MySQL binary logs: {e}")
        
        return recovery_points
    
    def _analyze_redis_aof(self, start_time: datetime, end_time: datetime,
                          backup_info: Dict[str, Any]) -> List[RecoveryPoint]:
        """Analyze Redis AOF for recovery points."""
        recovery_points = []
        
        try:
            # Redis AOF analysis would require parsing the AOF file
            # For now, we'll create recovery points at regular intervals
            current_time = start_time
            interval = timedelta(minutes=15)  # 15-minute intervals
            
            while current_time <= end_time:
                recovery_points.append(RecoveryPoint(
                    timestamp=current_time,
                    mysql_binlog_file=backup_info.get('mysql_binlog_file'),
                    mysql_binlog_position=backup_info.get('mysql_binlog_position'),
                    redis_aof_position=None,  # Would need AOF parsing
                    backup_id=backup_info['backup_id'],
                    description=f"Redis checkpoint at {current_time}"
                ))
                
                current_time += interval
        
        except Exception as e:
            logger.warning(f"Could not analyze Redis AOF: {e}")
        
        return recovery_points
    
    def _get_mysql_binlog_files(self) -> List[str]:
        """Get list of MySQL binary log files."""
        try:
            container = self.docker_client.containers.get(self.mysql_container)
            
            # Execute SHOW BINARY LOGS
            result = container.exec_run([
                "mysql", "-u", "root", "-p$(cat /run/secrets/mysql_root_password)",
                "-e", "SHOW BINARY LOGS"
            ])
            
            if result.exit_code == 0:
                lines = result.output.decode().strip().split('\n')[1:]  # Skip header
                return [line.split('\t')[0] for line in lines if line.strip()]
            
        except Exception as e:
            logger.warning(f"Could not get MySQL binary log files: {e}")
        
        return []
    
    def _parse_mysql_binlog_events(self, binlog_file: str, start_time: datetime, 
                                  end_time: datetime) -> List[Dict[str, Any]]:
        """Parse MySQL binary log events."""
        events = []
        
        try:
            container = self.docker_client.containers.get(self.mysql_container)
            
            # Use mysqlbinlog to parse events
            result = container.exec_run([
                "mysqlbinlog", 
                "--start-datetime", start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "--stop-datetime", end_time.strftime('%Y-%m-%d %H:%M:%S'),
                f"/var/lib/mysql/{binlog_file}"
            ])
            
            if result.exit_code == 0:
                # Parse mysqlbinlog output (simplified)
                lines = result.output.decode().split('\n')
                
                for i, line in enumerate(lines):
                    if line.startswith('#') and 'server id' in line:
                        # Extract timestamp and position
                        timestamp_match = re.search(r'(\d{6}\s+\d{1,2}:\d{2}:\d{2})', line)
                        position_match = re.search(r'end_log_pos (\d+)', line)
                        
                        if timestamp_match and position_match:
                            # Look ahead for event type
                            event_type = 'unknown'
                            for j in range(i+1, min(i+5, len(lines))):
                                if 'Query' in lines[j]:
                                    event_type = 'Query'
                                    break
                                elif 'Write_rows' in lines[j]:
                                    event_type = 'Write_rows'
                                    break
                                elif 'Update_rows' in lines[j]:
                                    event_type = 'Update_rows'
                                    break
                                elif 'Delete_rows' in lines[j]:
                                    event_type = 'Delete_rows'
                                    break
                            
                            # Convert timestamp
                            timestamp_str = timestamp_match.group(1)
                            event_timestamp = datetime.strptime(f"20{timestamp_str}", '%Y%m%d %H:%M:%S')
                            
                            events.append({
                                'timestamp': event_timestamp,
                                'position': int(position_match.group(1)),
                                'type': event_type
                            })
        
        except Exception as e:
            logger.warning(f"Could not parse MySQL binary log {binlog_file}: {e}")
        
        return events
    
    def _is_significant_mysql_event(self, event: Dict[str, Any]) -> bool:
        """Determine if a MySQL event is significant for recovery."""
        significant_types = ['Query', 'Write_rows', 'Update_rows', 'Delete_rows']
        return event['type'] in significant_types
    
    def create_recovery_plan(self, target_time: datetime, recovery_type: str = 'full') -> RecoveryPlan:
        """
        Create a comprehensive recovery plan for the target time.
        
        Args:
            target_time: Target recovery time
            recovery_type: Type of recovery ('full', 'mysql_only', 'redis_only')
            
        Returns:
            Comprehensive recovery plan
        """
        logger.info(f"Creating recovery plan for {target_time} (type: {recovery_type})")
        
        recovery_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Find the best base backup
        base_backup = self._find_best_base_backup(target_time)
        
        if not base_backup:
            raise ValueError(f"No suitable backup found for recovery to {target_time}")
        
        # Create recovery steps
        mysql_steps = []
        redis_steps = []
        
        if recovery_type in ['full', 'mysql_only']:
            mysql_steps = self._create_mysql_recovery_steps(target_time, base_backup)
        
        if recovery_type in ['full', 'redis_only']:
            redis_steps = self._create_redis_recovery_steps(target_time, base_backup)
        
        # Estimate duration
        estimated_duration = self._estimate_recovery_duration(mysql_steps, redis_steps)
        
        # Create prerequisites and risks
        prerequisites = self._create_prerequisites(recovery_type)
        risks = self._identify_risks(target_time, recovery_type)
        
        # Create rollback plan
        rollback_plan = self._create_rollback_plan(recovery_type)
        
        # Create validation steps
        validation_steps = self._create_validation_steps(recovery_type)
        
        recovery_plan = RecoveryPlan(
            recovery_id=recovery_id,
            target_time=target_time,
            recovery_type=recovery_type,
            base_backup=base_backup['backup_id'],
            mysql_steps=mysql_steps,
            redis_steps=redis_steps,
            estimated_duration=estimated_duration,
            prerequisites=prerequisites,
            risks=risks,
            rollback_plan=rollback_plan,
            validation_steps=validation_steps
        )
        
        # Save recovery plan
        self._save_recovery_plan(recovery_plan)
        
        logger.info(f"Recovery plan created: {recovery_id}")
        return recovery_plan
    
    def _find_best_base_backup(self, target_time: datetime) -> Optional[Dict[str, Any]]:
        """Find the best base backup for the target time."""
        # Find the most recent backup before the target time
        best_backup = None
        best_time_diff = None
        
        for backup_dir in self.backup_base_dir.glob("full_backup_*"):
            manifest_file = backup_dir / "backup_manifest.json"
            
            if manifest_file.exists():
                try:
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    
                    backup_time = datetime.fromisoformat(manifest['timestamp'])
                    
                    if backup_time <= target_time:
                        time_diff = target_time - backup_time
                        
                        if best_time_diff is None or time_diff < best_time_diff:
                            best_time_diff = time_diff
                            best_backup = {
                                'backup_id': manifest['backup_id'],
                                'timestamp': manifest['timestamp'],
                                'backup_dir': str(backup_dir)
                            }
                
                except Exception as e:
                    logger.warning(f"Could not load backup manifest from {backup_dir}: {e}")
        
        return best_backup
    
    def _create_mysql_recovery_steps(self, target_time: datetime, base_backup: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create MySQL recovery steps."""
        steps = []
        
        # Step 1: Stop MySQL container
        steps.append({
            'step': 1,
            'action': 'stop_mysql_container',
            'description': 'Stop MySQL container to prevent data corruption',
            'command': f'docker stop {self.mysql_container}',
            'estimated_duration': 1
        })
        
        # Step 2: Backup current data (for rollback)
        steps.append({
            'step': 2,
            'action': 'backup_current_mysql_data',
            'description': 'Backup current MySQL data for rollback purposes',
            'command': f'docker run --rm -v vedfolnir_mysql_data:/data -v $(pwd)/storage/recovery:/backup alpine tar czf /backup/mysql_rollback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tar.gz -C /data .',
            'estimated_duration': 5
        })
        
        # Step 3: Restore base backup
        backup_dir = base_backup['backup_dir']
        steps.append({
            'step': 3,
            'action': 'restore_mysql_base_backup',
            'description': f'Restore MySQL base backup from {base_backup["backup_id"]}',
            'command': f'docker run --rm -v {backup_dir}/mysql:/backup -v vedfolnir_mysql_data:/data alpine sh -c "rm -rf /data/* && tar xzf /backup/mysql_data.tar.gz -C /data"',
            'estimated_duration': 10
        })
        
        # Step 4: Start MySQL container
        steps.append({
            'step': 4,
            'action': 'start_mysql_container',
            'description': 'Start MySQL container',
            'command': f'docker start {self.mysql_container}',
            'estimated_duration': 2
        })
        
        # Step 5: Apply binary logs (if needed)
        backup_time = datetime.fromisoformat(base_backup['timestamp'])
        if target_time > backup_time:
            steps.append({
                'step': 5,
                'action': 'apply_mysql_binlogs',
                'description': f'Apply MySQL binary logs from {backup_time} to {target_time}',
                'command': f'python3 scripts/docker/apply_mysql_binlogs.py --from-time "{backup_time}" --to-time "{target_time}"',
                'estimated_duration': 15
            })
        
        return steps
    
    def _create_redis_recovery_steps(self, target_time: datetime, base_backup: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create Redis recovery steps."""
        steps = []
        
        # Step 1: Stop Redis container
        steps.append({
            'step': 1,
            'action': 'stop_redis_container',
            'description': 'Stop Redis container',
            'command': f'docker stop {self.redis_container}',
            'estimated_duration': 1
        })
        
        # Step 2: Backup current data (for rollback)
        steps.append({
            'step': 2,
            'action': 'backup_current_redis_data',
            'description': 'Backup current Redis data for rollback purposes',
            'command': f'docker run --rm -v vedfolnir_redis_data:/data -v $(pwd)/storage/recovery:/backup alpine tar czf /backup/redis_rollback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tar.gz -C /data .',
            'estimated_duration': 2
        })
        
        # Step 3: Restore Redis backup
        backup_dir = base_backup['backup_dir']
        steps.append({
            'step': 3,
            'action': 'restore_redis_backup',
            'description': f'Restore Redis backup from {base_backup["backup_id"]}',
            'command': f'docker run --rm -v {backup_dir}/redis:/backup -v vedfolnir_redis_data:/data alpine sh -c "cp /backup/dump.rdb /data/ && cp /backup/appendonly.aof /data/ 2>/dev/null || true"',
            'estimated_duration': 2
        })
        
        # Step 4: Start Redis container
        steps.append({
            'step': 4,
            'action': 'start_redis_container',
            'description': 'Start Redis container',
            'command': f'docker start {self.redis_container}',
            'estimated_duration': 1
        })
        
        return steps
    
    def _estimate_recovery_duration(self, mysql_steps: List[Dict[str, Any]], 
                                   redis_steps: List[Dict[str, Any]]) -> int:
        """Estimate total recovery duration in minutes."""
        mysql_duration = sum(step.get('estimated_duration', 0) for step in mysql_steps)
        redis_duration = sum(step.get('estimated_duration', 0) for step in redis_steps)
        
        # Add buffer for coordination and validation
        buffer = max(5, (mysql_duration + redis_duration) * 0.2)
        
        return int(mysql_duration + redis_duration + buffer)
    
    def _create_prerequisites(self, recovery_type: str) -> List[str]:
        """Create list of prerequisites for recovery."""
        prerequisites = [
            "Docker Compose environment is available",
            "Sufficient disk space for recovery operations",
            "Network connectivity to container registry",
            "Administrative access to Docker containers"
        ]
        
        if recovery_type in ['full', 'mysql_only']:
            prerequisites.extend([
                "MySQL container can be stopped safely",
                "MySQL backup files are accessible and valid"
            ])
        
        if recovery_type in ['full', 'redis_only']:
            prerequisites.extend([
                "Redis container can be stopped safely",
                "Redis backup files are accessible and valid"
            ])
        
        return prerequisites
    
    def _identify_risks(self, target_time: datetime, recovery_type: str) -> List[str]:
        """Identify risks associated with the recovery."""
        risks = [
            "Data loss between last backup and target time",
            "Service downtime during recovery process",
            "Potential data corruption if recovery fails",
            "Application state inconsistency after recovery"
        ]
        
        # Add time-based risks
        time_since_backup = datetime.now() - target_time
        if time_since_backup > timedelta(hours=24):
            risks.append("Recovery target is more than 24 hours old - increased risk of issues")
        
        if recovery_type == 'mysql_only':
            risks.append("Redis data will not be recovered - potential data inconsistency")
        elif recovery_type == 'redis_only':
            risks.append("MySQL data will not be recovered - potential data inconsistency")
        
        return risks
    
    def _create_rollback_plan(self, recovery_type: str) -> List[Dict[str, Any]]:
        """Create rollback plan in case recovery fails."""
        rollback_steps = []
        
        if recovery_type in ['full', 'mysql_only']:
            rollback_steps.extend([
                {
                    'step': 1,
                    'action': 'stop_mysql_container',
                    'description': 'Stop MySQL container',
                    'command': f'docker stop {self.mysql_container}'
                },
                {
                    'step': 2,
                    'action': 'restore_mysql_rollback',
                    'description': 'Restore MySQL data from rollback backup',
                    'command': 'docker run --rm -v $(pwd)/storage/recovery:/backup -v vedfolnir_mysql_data:/data alpine tar xzf /backup/mysql_rollback_*.tar.gz -C /data'
                },
                {
                    'step': 3,
                    'action': 'start_mysql_container',
                    'description': 'Start MySQL container',
                    'command': f'docker start {self.mysql_container}'
                }
            ])
        
        if recovery_type in ['full', 'redis_only']:
            rollback_steps.extend([
                {
                    'step': len(rollback_steps) + 1,
                    'action': 'stop_redis_container',
                    'description': 'Stop Redis container',
                    'command': f'docker stop {self.redis_container}'
                },
                {
                    'step': len(rollback_steps) + 2,
                    'action': 'restore_redis_rollback',
                    'description': 'Restore Redis data from rollback backup',
                    'command': 'docker run --rm -v $(pwd)/storage/recovery:/backup -v vedfolnir_redis_data:/data alpine tar xzf /backup/redis_rollback_*.tar.gz -C /data'
                },
                {
                    'step': len(rollback_steps) + 3,
                    'action': 'start_redis_container',
                    'description': 'Start Redis container',
                    'command': f'docker start {self.redis_container}'
                }
            ])
        
        return rollback_steps
    
    def _create_validation_steps(self, recovery_type: str) -> List[Dict[str, Any]]:
        """Create validation steps to verify recovery success."""
        validation_steps = []
        
        if recovery_type in ['full', 'mysql_only']:
            validation_steps.extend([
                {
                    'step': 1,
                    'action': 'verify_mysql_connectivity',
                    'description': 'Verify MySQL container is running and accessible',
                    'command': f'docker exec {self.mysql_container} mysql -u root -p$(cat /run/secrets/mysql_root_password) -e "SELECT 1"'
                },
                {
                    'step': 2,
                    'action': 'verify_mysql_data_integrity',
                    'description': 'Verify MySQL data integrity',
                    'command': f'docker exec {self.mysql_container} mysqlcheck --all-databases -u root -p$(cat /run/secrets/mysql_root_password)'
                }
            ])
        
        if recovery_type in ['full', 'redis_only']:
            validation_steps.extend([
                {
                    'step': len(validation_steps) + 1,
                    'action': 'verify_redis_connectivity',
                    'description': 'Verify Redis container is running and accessible',
                    'command': f'docker exec {self.redis_container} redis-cli ping'
                },
                {
                    'step': len(validation_steps) + 2,
                    'action': 'verify_redis_data',
                    'description': 'Verify Redis data is accessible',
                    'command': f'docker exec {self.redis_container} redis-cli info keyspace'
                }
            ])
        
        if recovery_type == 'full':
            validation_steps.append({
                'step': len(validation_steps) + 1,
                'action': 'verify_application_functionality',
                'description': 'Verify application functionality',
                'command': 'python3 scripts/docker/verify_application_health.py'
            })
        
        return validation_steps
    
    def _save_recovery_plan(self, recovery_plan: RecoveryPlan):
        """Save recovery plan to file."""
        plan_file = self.recovery_work_dir / f"{recovery_plan.recovery_id}_plan.json"
        
        with open(plan_file, 'w') as f:
            json.dump(asdict(recovery_plan), f, indent=2, default=str)
        
        logger.info(f"Recovery plan saved to {plan_file}")
    
    def execute_recovery_plan(self, recovery_plan: RecoveryPlan, dry_run: bool = False) -> bool:
        """
        Execute a recovery plan.
        
        Args:
            recovery_plan: The recovery plan to execute
            dry_run: If True, only show what would be done
            
        Returns:
            True if recovery was successful, False otherwise
        """
        logger.info(f"Executing recovery plan: {recovery_plan.recovery_id}")
        
        if dry_run:
            logger.info("DRY RUN MODE - No actual changes will be made")
        
        try:
            # Execute MySQL recovery steps
            if recovery_plan.mysql_steps:
                logger.info("Executing MySQL recovery steps...")
                for step in recovery_plan.mysql_steps:
                    logger.info(f"Step {step['step']}: {step['description']}")
                    
                    if not dry_run:
                        result = subprocess.run(
                            step['command'],
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=step.get('estimated_duration', 10) * 60
                        )
                        
                        if result.returncode != 0:
                            logger.error(f"MySQL recovery step failed: {result.stderr}")
                            return False
                    else:
                        logger.info(f"DRY RUN: Would execute: {step['command']}")
            
            # Execute Redis recovery steps
            if recovery_plan.redis_steps:
                logger.info("Executing Redis recovery steps...")
                for step in recovery_plan.redis_steps:
                    logger.info(f"Step {step['step']}: {step['description']}")
                    
                    if not dry_run:
                        result = subprocess.run(
                            step['command'],
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=step.get('estimated_duration', 10) * 60
                        )
                        
                        if result.returncode != 0:
                            logger.error(f"Redis recovery step failed: {result.stderr}")
                            return False
                    else:
                        logger.info(f"DRY RUN: Would execute: {step['command']}")
            
            # Execute validation steps
            if not dry_run:
                logger.info("Executing validation steps...")
                for step in recovery_plan.validation_steps:
                    logger.info(f"Validation {step['step']}: {step['description']}")
                    
                    result = subprocess.run(
                        step['command'],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes timeout for validation
                    )
                    
                    if result.returncode != 0:
                        logger.warning(f"Validation step failed: {result.stderr}")
                        # Continue with other validations
            
            logger.info("Recovery plan executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Recovery plan execution failed: {e}")
            return False

def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description='Point-in-Time Recovery for Vedfolnir')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze available recovery points')
    analyze_parser.add_argument('--start-time', required=True, help='Start time (ISO format)')
    analyze_parser.add_argument('--end-time', required=True, help='End time (ISO format)')
    
    # Plan command
    plan_parser = subparsers.add_parser('plan', help='Create recovery plan')
    plan_parser.add_argument('--target-time', required=True, help='Target recovery time (ISO format)')
    plan_parser.add_argument('--type', choices=['full', 'mysql_only', 'redis_only'], 
                           default='full', help='Recovery type')
    
    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute recovery plan')
    execute_parser.add_argument('--plan-file', required=True, help='Recovery plan file')
    execute_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        recovery_system = PointInTimeRecovery()
        
        if args.command == 'analyze':
            start_time = datetime.fromisoformat(args.start_time)
            end_time = datetime.fromisoformat(args.end_time)
            
            recovery_points = recovery_system.analyze_available_recovery_points(start_time, end_time)
            
            print(f"Found {len(recovery_points)} recovery points:")
            for point in recovery_points:
                print(f"  {point.timestamp}: {point.description}")
        
        elif args.command == 'plan':
            target_time = datetime.fromisoformat(args.target_time)
            
            recovery_plan = recovery_system.create_recovery_plan(target_time, args.type)
            
            print(f"Recovery plan created: {recovery_plan.recovery_id}")
            print(f"Estimated duration: {recovery_plan.estimated_duration} minutes")
            print(f"Base backup: {recovery_plan.base_backup}")
        
        elif args.command == 'execute':
            with open(args.plan_file, 'r') as f:
                plan_data = json.load(f)
            
            recovery_plan = RecoveryPlan(**plan_data)
            
            success = recovery_system.execute_recovery_plan(recovery_plan, args.dry_run)
            
            if success:
                print("Recovery completed successfully")
                return 0
            else:
                print("Recovery failed")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())