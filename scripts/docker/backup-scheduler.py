#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Automated Backup Scheduling System

Provides automated backup scheduling with:
- Configurable backup schedules (daily, weekly, monthly)
- Backup retention management
- Backup verification scheduling
- Disaster recovery testing scheduling
- Monitoring and alerting
- Backup health reporting
"""

import os
import sys
import json
import logging
import time
import subprocess
import schedule
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import argparse
import signal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BackupSchedule:
    """Backup schedule configuration."""
    schedule_id: str
    name: str
    schedule_type: str  # 'daily', 'weekly', 'monthly'
    schedule_time: str  # Time in HH:MM format
    schedule_day: Optional[str]  # Day of week for weekly, day of month for monthly
    backup_type: str  # 'full', 'incremental'
    retention_days: int
    enabled: bool
    compress: bool
    encrypt: bool
    verify: bool
    components: List[str]  # ['mysql', 'redis', 'app', 'vault']
    notification_settings: Dict[str, Any]

@dataclass
class ScheduledJob:
    """Scheduled job execution record."""
    job_id: str
    schedule_id: str
    job_type: str  # 'backup', 'verification', 'cleanup', 'dr_test'
    scheduled_time: datetime
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str  # 'scheduled', 'running', 'completed', 'failed', 'skipped'
    result_data: Dict[str, Any]
    error_message: Optional[str]

class BackupScheduler:
    """Automated backup scheduling system."""
    
    def __init__(self):
        """Initialize the backup scheduler."""
        self.schedules_dir = Path("storage/schedules")
        self.schedules_dir.mkdir(exist_ok=True)
        
        self.jobs_dir = Path("storage/scheduled_jobs")
        self.jobs_dir.mkdir(exist_ok=True)
        
        # Scheduler state
        self.running = False
        self.scheduler_thread = None
        
        # Load schedules
        self.backup_schedules = self._load_backup_schedules()
        
        # Default schedules if none exist
        if not self.backup_schedules:
            self._create_default_schedules()
        
        # Job execution tracking
        self.active_jobs = {}
        
        logger.info("Backup scheduler initialized")
    
    def _load_backup_schedules(self) -> List[BackupSchedule]:
        """Load backup schedules from configuration."""
        schedules = []
        
        schedules_file = self.schedules_dir / "backup_schedules.json"
        
        if schedules_file.exists():
            try:
                with open(schedules_file, 'r') as f:
                    schedules_data = json.load(f)
                
                for schedule_data in schedules_data:
                    schedule = BackupSchedule(**schedule_data)
                    schedules.append(schedule)
                
                logger.info(f"Loaded {len(schedules)} backup schedules")
            
            except Exception as e:
                logger.error(f"Failed to load backup schedules: {e}")
        
        return schedules
    
    def _save_backup_schedules(self):
        """Save backup schedules to configuration."""
        schedules_file = self.schedules_dir / "backup_schedules.json"
        
        try:
            schedules_data = [asdict(schedule) for schedule in self.backup_schedules]
            
            with open(schedules_file, 'w') as f:
                json.dump(schedules_data, f, indent=2)
            
            logger.info("Backup schedules saved")
        
        except Exception as e:
            logger.error(f"Failed to save backup schedules: {e}")
    
    def _create_default_schedules(self):
        """Create default backup schedules."""
        default_schedules = [
            BackupSchedule(
                schedule_id="daily_full_backup",
                name="Daily Full Backup",
                schedule_type="daily",
                schedule_time="02:00",
                schedule_day=None,
                backup_type="full",
                retention_days=7,
                enabled=True,
                compress=True,
                encrypt=True,
                verify=True,
                components=["mysql", "redis", "app", "vault"],
                notification_settings={"email": True, "webhook": False}
            ),
            BackupSchedule(
                schedule_id="weekly_verification",
                name="Weekly Backup Verification",
                schedule_type="weekly",
                schedule_time="03:00",
                schedule_day="sunday",
                backup_type="verification",
                retention_days=30,
                enabled=True,
                compress=False,
                encrypt=False,
                verify=True,
                components=["mysql", "redis", "app", "vault"],
                notification_settings={"email": True, "webhook": False}
            ),
            BackupSchedule(
                schedule_id="monthly_dr_test",
                name="Monthly Disaster Recovery Test",
                schedule_type="monthly",
                schedule_time="04:00",
                schedule_day="1",
                backup_type="dr_test",
                retention_days=90,
                enabled=True,
                compress=False,
                encrypt=False,
                verify=False,
                components=["mysql", "redis", "app"],
                notification_settings={"email": True, "webhook": True}
            )
        ]
        
        self.backup_schedules = default_schedules
        self._save_backup_schedules()
        
        logger.info("Created default backup schedules")
    
    def add_backup_schedule(self, schedule: BackupSchedule):
        """Add a new backup schedule."""
        # Check for duplicate schedule IDs
        existing_ids = [s.schedule_id for s in self.backup_schedules]
        if schedule.schedule_id in existing_ids:
            raise ValueError(f"Schedule ID already exists: {schedule.schedule_id}")
        
        self.backup_schedules.append(schedule)
        self._save_backup_schedules()
        
        # Register with scheduler if running
        if self.running:
            self._register_schedule(schedule)
        
        logger.info(f"Added backup schedule: {schedule.name}")
    
    def remove_backup_schedule(self, schedule_id: str):
        """Remove a backup schedule."""
        self.backup_schedules = [s for s in self.backup_schedules if s.schedule_id != schedule_id]
        self._save_backup_schedules()
        
        # Clear from scheduler if running
        if self.running:
            schedule.clear(schedule_id)
        
        logger.info(f"Removed backup schedule: {schedule_id}")
    
    def update_backup_schedule(self, schedule_id: str, updated_schedule: BackupSchedule):
        """Update an existing backup schedule."""
        for i, s in enumerate(self.backup_schedules):
            if s.schedule_id == schedule_id:
                self.backup_schedules[i] = updated_schedule
                break
        else:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        self._save_backup_schedules()
        
        # Re-register with scheduler if running
        if self.running:
            schedule.clear(schedule_id)
            self._register_schedule(updated_schedule)
        
        logger.info(f"Updated backup schedule: {schedule_id}")
    
    def start_scheduler(self):
        """Start the backup scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("Starting backup scheduler...")
        
        # Register all enabled schedules
        for backup_schedule in self.backup_schedules:
            if backup_schedule.enabled:
                self._register_schedule(backup_schedule)
        
        # Start scheduler thread
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Backup scheduler started")
    
    def stop_scheduler(self):
        """Stop the backup scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping backup scheduler...")
        
        self.running = False
        
        # Clear all scheduled jobs
        schedule.clear()
        
        # Wait for scheduler thread to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Backup scheduler stopped")
    
    def _register_schedule(self, backup_schedule: BackupSchedule):
        """Register a schedule with the scheduler."""
        if backup_schedule.backup_type == "full":
            job_func = lambda: self._execute_backup_job(backup_schedule)
        elif backup_schedule.backup_type == "verification":
            job_func = lambda: self._execute_verification_job(backup_schedule)
        elif backup_schedule.backup_type == "dr_test":
            job_func = lambda: self._execute_dr_test_job(backup_schedule)
        else:
            logger.warning(f"Unknown backup type: {backup_schedule.backup_type}")
            return
        
        # Schedule based on type
        if backup_schedule.schedule_type == "daily":
            schedule.every().day.at(backup_schedule.schedule_time).do(job_func).tag(backup_schedule.schedule_id)
        
        elif backup_schedule.schedule_type == "weekly":
            day_map = {
                'monday': schedule.every().monday,
                'tuesday': schedule.every().tuesday,
                'wednesday': schedule.every().wednesday,
                'thursday': schedule.every().thursday,
                'friday': schedule.every().friday,
                'saturday': schedule.every().saturday,
                'sunday': schedule.every().sunday
            }
            
            day_scheduler = day_map.get(backup_schedule.schedule_day.lower())
            if day_scheduler:
                day_scheduler.at(backup_schedule.schedule_time).do(job_func).tag(backup_schedule.schedule_id)
        
        elif backup_schedule.schedule_type == "monthly":
            # For monthly, we'll check on daily basis and execute on the right day
            def monthly_job():
                current_day = datetime.now().day
                target_day = int(backup_schedule.schedule_day)
                
                if current_day == target_day:
                    current_time = datetime.now().strftime("%H:%M")
                    if current_time == backup_schedule.schedule_time:
                        job_func()
            
            schedule.every().day.at(backup_schedule.schedule_time).do(monthly_job).tag(backup_schedule.schedule_id)
        
        logger.info(f"Registered schedule: {backup_schedule.name}")
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)
        
        logger.info("Scheduler loop stopped")
    
    def _execute_backup_job(self, backup_schedule: BackupSchedule):
        """Execute a backup job."""
        job_id = f"backup_{backup_schedule.schedule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Executing backup job: {job_id}")
        
        # Create job record
        job = ScheduledJob(
            job_id=job_id,
            schedule_id=backup_schedule.schedule_id,
            job_type="backup",
            scheduled_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            status="running",
            result_data={},
            error_message=None
        )
        
        self.active_jobs[job_id] = job
        
        try:
            # Build backup command
            backup_script = Path(__file__).parent / "backup-disaster-recovery.sh"
            
            cmd = [
                str(backup_script),
                "backup"
            ]
            
            if backup_schedule.compress:
                cmd.append("--compress")
            
            if backup_schedule.encrypt:
                cmd.append("--encrypt")
            
            if backup_schedule.verify:
                cmd.append("--verify")
            
            # Execute backup
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                job.status = "completed"
                job.result_data = {
                    "backup_successful": True,
                    "stdout": result.stdout,
                    "backup_command": " ".join(cmd)
                }
                logger.info(f"Backup job completed successfully: {job_id}")
            else:
                job.status = "failed"
                job.error_message = result.stderr
                job.result_data = {
                    "backup_successful": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                logger.error(f"Backup job failed: {job_id} - {result.stderr}")
        
        except subprocess.TimeoutExpired:
            job.status = "failed"
            job.error_message = "Backup job timed out"
            logger.error(f"Backup job timed out: {job_id}")
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            logger.error(f"Backup job error: {job_id} - {e}")
        
        finally:
            job.end_time = datetime.now()
            self._save_job_record(job)
            
            # Send notification
            self._send_notification(backup_schedule, job)
            
            # Cleanup old backups
            self._cleanup_old_backups(backup_schedule.retention_days)
            
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def _execute_verification_job(self, backup_schedule: BackupSchedule):
        """Execute a backup verification job."""
        job_id = f"verification_{backup_schedule.schedule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Executing verification job: {job_id}")
        
        # Create job record
        job = ScheduledJob(
            job_id=job_id,
            schedule_id=backup_schedule.schedule_id,
            job_type="verification",
            scheduled_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            status="running",
            result_data={},
            error_message=None
        )
        
        self.active_jobs[job_id] = job
        
        try:
            # Execute verification
            verification_script = Path(__file__).parent / "backup-verification.py"
            
            cmd = [
                "python3",
                str(verification_script),
                "verify-all",
                "--type", "quick"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                job.status = "completed"
                job.result_data = {
                    "verification_successful": True,
                    "stdout": result.stdout
                }
                logger.info(f"Verification job completed successfully: {job_id}")
            else:
                job.status = "failed"
                job.error_message = result.stderr
                job.result_data = {
                    "verification_successful": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                logger.error(f"Verification job failed: {job_id} - {result.stderr}")
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            logger.error(f"Verification job error: {job_id} - {e}")
        
        finally:
            job.end_time = datetime.now()
            self._save_job_record(job)
            
            # Send notification
            self._send_notification(backup_schedule, job)
            
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def _execute_dr_test_job(self, backup_schedule: BackupSchedule):
        """Execute a disaster recovery test job."""
        job_id = f"dr_test_{backup_schedule.schedule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Executing DR test job: {job_id}")
        
        # Create job record
        job = ScheduledJob(
            job_id=job_id,
            schedule_id=backup_schedule.schedule_id,
            job_type="dr_test",
            scheduled_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            status="running",
            result_data={},
            error_message=None
        )
        
        self.active_jobs[job_id] = job
        
        try:
            # Execute DR test
            dr_test_script = Path(__file__).parent / "disaster-recovery-test.py"
            
            cmd = [
                "python3",
                str(dr_test_script),
                "test",
                "mysql_data_corruption"  # Use a safe test scenario
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                job.status = "completed"
                job.result_data = {
                    "dr_test_successful": True,
                    "stdout": result.stdout
                }
                logger.info(f"DR test job completed successfully: {job_id}")
            else:
                job.status = "failed"
                job.error_message = result.stderr
                job.result_data = {
                    "dr_test_successful": False,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                logger.error(f"DR test job failed: {job_id} - {result.stderr}")
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            logger.error(f"DR test job error: {job_id} - {e}")
        
        finally:
            job.end_time = datetime.now()
            self._save_job_record(job)
            
            # Send notification
            self._send_notification(backup_schedule, job)
            
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def _save_job_record(self, job: ScheduledJob):
        """Save job execution record."""
        job_file = self.jobs_dir / f"{job.job_id}.json"
        
        try:
            with open(job_file, 'w') as f:
                json.dump(asdict(job), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save job record: {e}")
    
    def _send_notification(self, backup_schedule: BackupSchedule, job: ScheduledJob):
        """Send notification about job completion."""
        if not backup_schedule.notification_settings.get("email", False):
            return
        
        # Simple notification logging (could be extended to send actual emails/webhooks)
        status_emoji = "✅" if job.status == "completed" else "❌"
        
        notification_message = f"""
{status_emoji} Scheduled Job Notification

Job ID: {job.job_id}
Schedule: {backup_schedule.name}
Type: {job.job_type}
Status: {job.status}
Duration: {(job.end_time - job.start_time).total_seconds():.1f} seconds

{f"Error: {job.error_message}" if job.error_message else "Completed successfully"}
"""
        
        logger.info(f"Notification: {notification_message}")
        
        # Save notification to file
        notification_file = self.jobs_dir / f"{job.job_id}_notification.txt"
        try:
            with open(notification_file, 'w') as f:
                f.write(notification_message)
        except Exception as e:
            logger.error(f"Failed to save notification: {e}")
    
    def _cleanup_old_backups(self, retention_days: int):
        """Clean up old backup files based on retention policy."""
        try:
            backup_base_dir = Path("storage/backups")
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for backup_dir in backup_base_dir.glob("full_backup_*"):
                if backup_dir.is_dir():
                    # Check backup age
                    backup_time = datetime.fromtimestamp(backup_dir.stat().st_mtime)
                    
                    if backup_time < cutoff_date:
                        logger.info(f"Cleaning up old backup: {backup_dir.name}")
                        
                        # Remove backup directory
                        import shutil
                        shutil.rmtree(backup_dir)
        
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def get_job_history(self, limit: int = 50) -> List[ScheduledJob]:
        """Get job execution history."""
        jobs = []
        
        job_files = sorted(self.jobs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        for job_file in job_files[:limit]:
            try:
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                
                # Convert datetime strings back to datetime objects
                for field in ['scheduled_time', 'start_time', 'end_time']:
                    if job_data.get(field):
                        job_data[field] = datetime.fromisoformat(job_data[field])
                
                job = ScheduledJob(**job_data)
                jobs.append(job)
            
            except Exception as e:
                logger.warning(f"Failed to load job record {job_file}: {e}")
        
        return jobs
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            "running": self.running,
            "active_jobs": len(self.active_jobs),
            "total_schedules": len(self.backup_schedules),
            "enabled_schedules": len([s for s in self.backup_schedules if s.enabled]),
            "next_jobs": [
                {
                    "schedule_id": job.tags.pop() if job.tags else "unknown",
                    "next_run": job.next_run.isoformat() if job.next_run else None
                }
                for job in schedule.jobs
            ]
        }

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    global scheduler_instance
    if scheduler_instance:
        scheduler_instance.stop_scheduler()
    sys.exit(0)

# Global scheduler instance for signal handling
scheduler_instance = None

def main():
    """Main function for command-line interface."""
    global scheduler_instance
    
    parser = argparse.ArgumentParser(description='Backup Scheduler System')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the backup scheduler')
    start_parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop the backup scheduler')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show scheduler status')
    
    # List schedules command
    list_parser = subparsers.add_parser('list-schedules', help='List backup schedules')
    
    # Job history command
    history_parser = subparsers.add_parser('job-history', help='Show job execution history')
    history_parser.add_argument('--limit', type=int, default=20, help='Number of jobs to show')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        scheduler_instance = BackupScheduler()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if args.command == 'start':
            scheduler_instance.start_scheduler()
            
            if args.daemon:
                logger.info("Running as daemon...")
                try:
                    while scheduler_instance.running:
                        time.sleep(60)
                except KeyboardInterrupt:
                    logger.info("Received interrupt, shutting down...")
                finally:
                    scheduler_instance.stop_scheduler()
            else:
                print("Scheduler started. Press Ctrl+C to stop.")
                try:
                    while scheduler_instance.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    scheduler_instance.stop_scheduler()
        
        elif args.command == 'stop':
            scheduler_instance.stop_scheduler()
            print("Scheduler stopped")
        
        elif args.command == 'status':
            status = scheduler_instance.get_scheduler_status()
            print(f"Scheduler Status:")
            print(f"  Running: {status['running']}")
            print(f"  Active Jobs: {status['active_jobs']}")
            print(f"  Total Schedules: {status['total_schedules']}")
            print(f"  Enabled Schedules: {status['enabled_schedules']}")
            
            if status['next_jobs']:
                print("  Next Jobs:")
                for job in status['next_jobs']:
                    print(f"    {job['schedule_id']}: {job['next_run']}")
        
        elif args.command == 'list-schedules':
            print("Backup Schedules:")
            for schedule in scheduler_instance.backup_schedules:
                status = "Enabled" if schedule.enabled else "Disabled"
                print(f"  {schedule.schedule_id}: {schedule.name} ({status})")
                print(f"    Type: {schedule.backup_type}")
                print(f"    Schedule: {schedule.schedule_type} at {schedule.schedule_time}")
                print(f"    Retention: {schedule.retention_days} days")
                print()
        
        elif args.command == 'job-history':
            jobs = scheduler_instance.get_job_history(args.limit)
            
            print(f"Job History (last {len(jobs)} jobs):")
            for job in jobs:
                duration = (job.end_time - job.start_time).total_seconds() if job.end_time else 0
                print(f"  {job.job_id}")
                print(f"    Type: {job.job_type}")
                print(f"    Status: {job.status}")
                print(f"    Duration: {duration:.1f}s")
                print(f"    Time: {job.start_time}")
                if job.error_message:
                    print(f"    Error: {job.error_message}")
                print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())