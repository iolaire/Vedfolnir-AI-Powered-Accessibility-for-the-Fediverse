#!/usr/bin/env python3
"""
MySQL Backup and Recovery Automation for Vedfolnir

This module provides comprehensive MySQL backup and recovery capabilities including:
- Automated scheduled backups with multiple strategies
- Point-in-time recovery support
- Backup validation and integrity checking
- Compression and encryption of backup files
- Cloud storage integration (S3, Google Cloud, Azure)
- Backup retention policy management
- Recovery testing and verification
- Monitoring and alerting for backup operations

Integrates with existing MySQL health monitoring and security systems.
"""

import logging
import subprocess
import gzip
import shutil
import hashlib
import json
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import sys
import tempfile
import tarfile

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pymysql
    from sqlalchemy import create_engine, text
    from cryptography.fernet import Fernet
    import redis
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    from config import Config
    from mysql_connection_validator import MySQLConnectionValidator
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required packages are installed")
    print("For cloud storage: pip install boto3 google-cloud-storage azure-storage-blob")
    sys.exit(1)

logger = logging.getLogger(__name__)

@dataclass
class BackupMetadata:
    """Container for backup metadata."""
    backup_id: str
    timestamp: datetime
    backup_type: str  # 'full', 'incremental', 'differential'
    database_name: str
    file_path: str
    file_size: int
    compressed: bool
    encrypted: bool
    checksum: str
    mysql_version: str
    binlog_position: Optional[str]
    backup_duration: float
    compression_ratio: Optional[float]
    validation_status: str  # 'pending', 'valid', 'invalid', 'error'
    retention_date: datetime
    storage_location: str  # 'local', 's3', 'gcs', 'azure'
    tags: Dict[str, str]

@dataclass
class RecoveryPlan:
    """Container for recovery plan details."""
    recovery_id: str
    target_timestamp: datetime
    recovery_type: str  # 'full', 'point_in_time', 'table_level'
    required_backups: List[str]
    estimated_duration: float
    recovery_steps: List[Dict[str, Any]]
    prerequisites: List[str]
    risks: List[str]
    rollback_plan: List[Dict[str, Any]]

@dataclass
class BackupJob:
    """Container for backup job configuration."""
    job_id: str
    name: str
    schedule: str  # Cron expression
    backup_type: str
    databases: List[str]
    retention_days: int
    compression_enabled: bool
    encryption_enabled: bool
    storage_locations: List[str]
    pre_backup_scripts: List[str]
    post_backup_scripts: List[str]
    notification_settings: Dict[str, Any]
    enabled: bool

class MySQLBackupRecovery:
    """
    Comprehensive MySQL backup and recovery automation system.
    
    Provides automated backups, point-in-time recovery, backup validation,
    and integration with cloud storage providers.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the MySQL Backup and Recovery system.
        
        Args:
            config: Optional Config instance, will create default if not provided
        """
        self.config = config or Config()
        self.validator = MySQLConnectionValidator()
        
        # Backup configuration
        self.backup_dir = Path(os.getenv('MYSQL_BACKUP_DIR', './backups'))
        self.backup_dir.mkdir(exist_ok=True)
        
        # Encryption for backup files
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Redis for backup metadata and job scheduling
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_redis()
        
        # Backup settings
        self.backup_settings = {
            'default_retention_days': int(os.getenv('MYSQL_BACKUP_RETENTION_DAYS', '30')),
            'compression_level': int(os.getenv('MYSQL_BACKUP_COMPRESSION_LEVEL', '6')),
            'max_backup_size_gb': int(os.getenv('MYSQL_MAX_BACKUP_SIZE_GB', '10')),
            'backup_timeout_minutes': int(os.getenv('MYSQL_BACKUP_TIMEOUT_MINUTES', '60')),
            'parallel_backup_jobs': int(os.getenv('MYSQL_PARALLEL_BACKUP_JOBS', '2'))
        }
        
        # Cloud storage clients
        self.cloud_clients = {}
        self._initialize_cloud_storage()
        
        # Backup scheduler
        self.scheduler_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # Active backup jobs
        self.backup_jobs: Dict[str, BackupJob] = {}
        self._load_backup_jobs()
        
        logger.info("MySQL Backup and Recovery system initialized")
    
    def _initialize_redis(self):
        """Initialize Redis connection for backup metadata."""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/4')  # Use DB 4 for backups
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for backup metadata")
        except Exception as e:
            logger.warning(f"Redis not available for backup metadata: {e}")
            self.redis_client = None
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for backup files."""
        key_file = Path(os.getenv('MYSQL_BACKUP_ENCRYPTION_KEY_FILE', '.mysql_backup_key'))
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Could not read existing backup encryption key: {e}")
        
        # Generate new key
        key = Fernet.generate_key()
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            logger.info("Generated new encryption key for backup files")
        except Exception as e:
            logger.warning(f"Could not save backup encryption key: {e}")
        
        return key
    
    def _initialize_cloud_storage(self):
        """Initialize cloud storage clients."""
        # AWS S3
        try:
            if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
                self.cloud_clients['s3'] = boto3.client('s3')
                logger.info("AWS S3 client initialized")
        except Exception as e:
            logger.debug(f"AWS S3 client not available: {e}")
        
        # Google Cloud Storage (would implement if needed)
        # Azure Blob Storage (would implement if needed)
    
    def _load_backup_jobs(self):
        """Load backup jobs from Redis or configuration."""
        try:
            if self.redis_client:
                # Load jobs from Redis
                job_keys = self.redis_client.keys("mysql_backup:jobs:*")
                for key in job_keys:
                    try:
                        job_data = self.redis_client.get(key)
                        if job_data:
                            job_dict = json.loads(job_data)
                            job = BackupJob(**job_dict)
                            self.backup_jobs[job.job_id] = job
                    except Exception as e:
                        logger.error(f"Could not load backup job from {key}: {e}")
            
            # If no jobs loaded, create default job
            if not self.backup_jobs:
                self._create_default_backup_job()
                
        except Exception as e:
            logger.error(f"Failed to load backup jobs: {e}")
            self._create_default_backup_job()
    
    def _create_default_backup_job(self):
        """Create a default backup job."""
        default_job = BackupJob(
            job_id='default_daily_backup',
            name='Daily Full Backup',
            schedule='0 2 * * *',  # Daily at 2 AM
            backup_type='full',
            databases=['all'],
            retention_days=self.backup_settings['default_retention_days'],
            compression_enabled=True,
            encryption_enabled=True,
            storage_locations=['local'],
            pre_backup_scripts=[],
            post_backup_scripts=[],
            notification_settings={},
            enabled=True
        )
        
        self.backup_jobs[default_job.job_id] = default_job
        self._save_backup_job(default_job)
    
    def _save_backup_job(self, job: BackupJob):
        """Save backup job to Redis."""
        try:
            if self.redis_client:
                job_key = f"mysql_backup:jobs:{job.job_id}"
                self.redis_client.set(job_key, json.dumps(asdict(job), default=str))
        except Exception as e:
            logger.error(f"Failed to save backup job: {e}")
    
    def create_backup(self, backup_type: str = 'full', databases: List[str] = None, 
                     options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a MySQL backup.
        
        Args:
            backup_type: Type of backup ('full', 'incremental', 'differential')
            databases: List of databases to backup (None for all)
            options: Additional backup options
            
        Returns:
            Dictionary containing backup results and metadata
        """
        try:
            backup_start = datetime.now()
            backup_id = f"backup_{backup_start.strftime('%Y%m%d_%H%M%S')}_{backup_type}"
            
            logger.info(f"Starting {backup_type} backup: {backup_id}")
            
            # Initialize options
            options = options or {}
            compress = options.get('compress', True)
            encrypt = options.get('encrypt', True)
            storage_locations = options.get('storage_locations', ['local'])
            
            # Determine databases to backup
            if databases is None or 'all' in databases:
                databases = self._get_all_databases()
            
            # Create backup for each database
            backup_files = []
            total_size = 0
            
            for database in databases:
                if database in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                    continue  # Skip system databases unless explicitly requested
                
                db_backup_result = self._create_database_backup(
                    database, backup_id, backup_type, compress, encrypt
                )
                
                if db_backup_result['success']:
                    backup_files.append(db_backup_result)
                    total_size += db_backup_result['file_size']
                else:
                    logger.error(f"Failed to backup database {database}: {db_backup_result.get('error')}")
            
            if not backup_files:
                return {
                    'success': False,
                    'error': 'No databases were successfully backed up',
                    'backup_id': backup_id
                }
            
            # Create combined backup archive if multiple databases
            if len(backup_files) > 1:
                archive_result = self._create_backup_archive(backup_files, backup_id)
                if archive_result['success']:
                    backup_files = [archive_result]
                    total_size = archive_result['file_size']
            
            # Get MySQL version and binlog position
            mysql_info = self._get_mysql_backup_info()
            
            # Create backup metadata
            backup_duration = (datetime.now() - backup_start).total_seconds()
            
            backup_metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=backup_start,
                backup_type=backup_type,
                database_name=','.join(databases),
                file_path=backup_files[0]['file_path'],
                file_size=total_size,
                compressed=compress,
                encrypted=encrypt,
                checksum=backup_files[0]['checksum'],
                mysql_version=mysql_info['version'],
                binlog_position=mysql_info.get('binlog_position'),
                backup_duration=backup_duration,
                compression_ratio=backup_files[0].get('compression_ratio'),
                validation_status='pending',
                retention_date=backup_start + timedelta(days=self.backup_settings['default_retention_days']),
                storage_location='local',
                tags=options.get('tags', {})
            )
            
            # Store backup metadata
            self._store_backup_metadata(backup_metadata)
            
            # Upload to cloud storage if requested
            cloud_upload_results = []
            for location in storage_locations:
                if location != 'local':
                    upload_result = self._upload_to_cloud_storage(backup_metadata, location)
                    cloud_upload_results.append(upload_result)
            
            # Validate backup
            validation_result = self._validate_backup(backup_metadata)
            backup_metadata.validation_status = 'valid' if validation_result['valid'] else 'invalid'
            self._update_backup_metadata(backup_metadata)
            
            logger.info(f"Backup completed: {backup_id} ({total_size} bytes, {backup_duration:.1f}s)")
            
            return {
                'success': True,
                'backup_id': backup_id,
                'backup_metadata': asdict(backup_metadata),
                'cloud_uploads': cloud_upload_results,
                'validation_result': validation_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'backup_id': backup_id if 'backup_id' in locals() else 'unknown',
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_all_databases(self) -> List[str]:
        """Get list of all databases."""
        try:
            engine = create_engine(self.config.DATABASE_URL, echo=False)
            
            with engine.connect() as conn:
                result = conn.execute(text("SHOW DATABASES")).fetchall()
                databases = [row[0] for row in result]
            
            engine.dispose()
            return databases
            
        except Exception as e:
            logger.error(f"Failed to get database list: {e}")
            return []
    
    def _create_database_backup(self, database: str, backup_id: str, backup_type: str, 
                              compress: bool, encrypt: bool) -> Dict[str, Any]:
        """Create backup for a single database."""
        try:
            # Parse database URL for mysqldump
            db_url_parts = self._parse_database_url(self.config.DATABASE_URL)
            
            # Create backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{database}_{backup_type}_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            # Build mysqldump command
            mysqldump_cmd = [
                'mysqldump',
                f"--host={db_url_parts['host']}",
                f"--port={db_url_parts['port']}",
                f"--user={db_url_parts['username']}",
                f"--password={db_url_parts['password']}",
                '--single-transaction',
                '--routines',
                '--triggers',
                '--events',
                '--add-drop-database',
                '--create-options',
                '--disable-keys',
                '--extended-insert',
                '--quick',
                '--lock-tables=false'
            ]
            
            # Add backup type specific options
            if backup_type == 'full':
                mysqldump_cmd.extend(['--complete-insert', '--hex-blob'])
            elif backup_type == 'incremental':
                # For incremental backups, we'd need binlog position tracking
                mysqldump_cmd.extend(['--master-data=2', '--flush-logs'])
            
            mysqldump_cmd.append(database)
            
            # Execute mysqldump
            original_size = 0
            with open(backup_path, 'w') as backup_file:
                process = subprocess.run(
                    mysqldump_cmd,
                    stdout=backup_file,
                    stderr=subprocess.PIPE,
                    timeout=self.backup_settings['backup_timeout_minutes'] * 60,
                    text=True
                )
                
                if process.returncode != 0:
                    raise Exception(f"mysqldump failed: {process.stderr}")
            
            original_size = backup_path.stat().st_size
            final_path = backup_path
            compression_ratio = None
            
            # Compress if requested
            if compress:
                compressed_path = backup_path.with_suffix('.sql.gz')
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb', compresslevel=self.backup_settings['compression_level']) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                compressed_size = compressed_path.stat().st_size
                compression_ratio = compressed_size / original_size
                
                # Remove uncompressed file
                backup_path.unlink()
                final_path = compressed_path
            
            # Encrypt if requested
            if encrypt:
                encrypted_path = final_path.with_suffix(final_path.suffix + '.enc')
                with open(final_path, 'rb') as f_in:
                    encrypted_data = self.cipher_suite.encrypt(f_in.read())
                    with open(encrypted_path, 'wb') as f_out:
                        f_out.write(encrypted_data)
                
                # Remove unencrypted file
                final_path.unlink()
                final_path = encrypted_path
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(final_path)
            
            return {
                'success': True,
                'database': database,
                'file_path': str(final_path),
                'file_size': final_path.stat().st_size,
                'original_size': original_size,
                'compression_ratio': compression_ratio,
                'checksum': checksum
            }
            
        except Exception as e:
            logger.error(f"Database backup failed for {database}: {e}")
            return {
                'success': False,
                'database': database,
                'error': str(e)
            }
    
    def _parse_database_url(self, database_url: str) -> Dict[str, str]:
        """Parse database URL into components."""
        # Simple URL parsing for MySQL URLs
        # Format: mysql+pymysql://username:password@host:port/database
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            
            return {
                'username': parsed.username or 'root',
                'password': parsed.password or '',
                'host': parsed.hostname or 'localhost',
                'port': str(parsed.port or 3306),
                'database': parsed.path.lstrip('/') if parsed.path else ''
            }
        except Exception as e:
            logger.error(f"Failed to parse database URL: {e}")
            return {
                'username': 'root',
                'password': '',
                'host': 'localhost',
                'port': '3306',
                'database': ''
            }
    
    def _create_backup_archive(self, backup_files: List[Dict[str, Any]], backup_id: str) -> Dict[str, Any]:
        """Create a tar archive of multiple backup files."""
        try:
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            
            with tarfile.open(archive_path, 'w:gz') as tar:
                for backup_file in backup_files:
                    file_path = Path(backup_file['file_path'])
                    tar.add(file_path, arcname=file_path.name)
            
            # Calculate checksum of archive
            checksum = self._calculate_file_checksum(archive_path)
            
            # Remove individual backup files
            for backup_file in backup_files:
                try:
                    Path(backup_file['file_path']).unlink()
                except:
                    pass
            
            return {
                'success': True,
                'file_path': str(archive_path),
                'file_size': archive_path.stat().st_size,
                'checksum': checksum
            }
            
        except Exception as e:
            logger.error(f"Failed to create backup archive: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_mysql_backup_info(self) -> Dict[str, Any]:
        """Get MySQL version and binlog information for backup metadata."""
        try:
            engine = create_engine(self.config.DATABASE_URL, echo=False)
            info = {}
            
            with engine.connect() as conn:
                # Get MySQL version
                version_result = conn.execute(text("SELECT VERSION()")).fetchone()
                info['version'] = version_result[0] if version_result else 'unknown'
                
                # Get binlog position (if binary logging is enabled)
                try:
                    binlog_result = conn.execute(text("SHOW MASTER STATUS")).fetchone()
                    if binlog_result:
                        info['binlog_position'] = f"{binlog_result[0]}:{binlog_result[1]}"
                except:
                    info['binlog_position'] = None
            
            engine.dispose()
            return info
            
        except Exception as e:
            logger.error(f"Failed to get MySQL backup info: {e}")
            return {'version': 'unknown', 'binlog_position': None}
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return 'unknown'
    
    def _store_backup_metadata(self, metadata: BackupMetadata):
        """Store backup metadata in Redis."""
        try:
            if self.redis_client:
                metadata_key = f"mysql_backup:metadata:{metadata.backup_id}"
                self.redis_client.setex(
                    metadata_key,
                    86400 * metadata.retention_date.day,  # TTL based on retention
                    json.dumps(asdict(metadata), default=str)
                )
        except Exception as e:
            logger.error(f"Failed to store backup metadata: {e}")
    
    def _update_backup_metadata(self, metadata: BackupMetadata):
        """Update existing backup metadata."""
        self._store_backup_metadata(metadata)  # Same as store for Redis
    
    def _validate_backup(self, metadata: BackupMetadata) -> Dict[str, Any]:
        """Validate backup file integrity."""
        try:
            backup_path = Path(metadata.file_path)
            
            # Check if file exists
            if not backup_path.exists():
                return {
                    'valid': False,
                    'error': 'Backup file does not exist'
                }
            
            # Verify file size
            actual_size = backup_path.stat().st_size
            if actual_size != metadata.file_size:
                return {
                    'valid': False,
                    'error': f'File size mismatch: expected {metadata.file_size}, got {actual_size}'
                }
            
            # Verify checksum
            actual_checksum = self._calculate_file_checksum(backup_path)
            if actual_checksum != metadata.checksum:
                return {
                    'valid': False,
                    'error': f'Checksum mismatch: expected {metadata.checksum}, got {actual_checksum}'
                }
            
            # Additional validation for SQL files
            if backup_path.suffix in ['.sql', '.gz']:
                sql_validation = self._validate_sql_backup(backup_path, metadata)
                if not sql_validation['valid']:
                    return sql_validation
            
            return {
                'valid': True,
                'validation_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _validate_sql_backup(self, backup_path: Path, metadata: BackupMetadata) -> Dict[str, Any]:
        """Validate SQL backup file content."""
        try:
            # Basic SQL file validation
            content_sample = ""
            
            if backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rt') as f:
                    content_sample = f.read(1024)  # Read first 1KB
            elif backup_path.suffix == '.enc':
                # Would need to decrypt first
                return {'valid': True, 'note': 'Encrypted file - content validation skipped'}
            else:
                with open(backup_path, 'r') as f:
                    content_sample = f.read(1024)
            
            # Check for SQL dump markers
            if not any(marker in content_sample for marker in [
                '-- MySQL dump', 'CREATE DATABASE', 'USE ', 'INSERT INTO'
            ]):
                return {
                    'valid': False,
                    'error': 'File does not appear to be a valid MySQL dump'
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"SQL backup validation failed: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _upload_to_cloud_storage(self, metadata: BackupMetadata, storage_location: str) -> Dict[str, Any]:
        """Upload backup to cloud storage."""
        try:
            if storage_location == 's3' and 's3' in self.cloud_clients:
                return self._upload_to_s3(metadata)
            elif storage_location == 'gcs':
                return self._upload_to_gcs(metadata)
            elif storage_location == 'azure':
                return self._upload_to_azure(metadata)
            else:
                return {
                    'success': False,
                    'storage_location': storage_location,
                    'error': f'Storage location {storage_location} not configured'
                }
                
        except Exception as e:
            logger.error(f"Cloud upload failed for {storage_location}: {e}")
            return {
                'success': False,
                'storage_location': storage_location,
                'error': str(e)
            }
    
    def _upload_to_s3(self, metadata: BackupMetadata) -> Dict[str, Any]:
        """Upload backup to AWS S3."""
        try:
            s3_client = self.cloud_clients['s3']
            bucket_name = os.getenv('MYSQL_BACKUP_S3_BUCKET')
            
            if not bucket_name:
                return {
                    'success': False,
                    'storage_location': 's3',
                    'error': 'S3 bucket name not configured (MYSQL_BACKUP_S3_BUCKET)'
                }
            
            # Create S3 key with organized structure
            s3_key = f"mysql-backups/{metadata.timestamp.strftime('%Y/%m/%d')}/{Path(metadata.file_path).name}"
            
            # Upload file
            s3_client.upload_file(
                metadata.file_path,
                bucket_name,
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'backup-id': metadata.backup_id,
                        'backup-type': metadata.backup_type,
                        'database': metadata.database_name,
                        'checksum': metadata.checksum,
                        'mysql-version': metadata.mysql_version
                    }
                }
            )
            
            # Update metadata
            metadata.storage_location = 's3'
            self._update_backup_metadata(metadata)
            
            logger.info(f"Backup uploaded to S3: s3://{bucket_name}/{s3_key}")
            return {
                'success': True,
                'storage_location': 's3',
                'bucket': bucket_name,
                'key': s3_key,
                'url': f's3://{bucket_name}/{s3_key}'
            }
            
        except ClientError as e:
            return {
                'success': False,
                'storage_location': 's3',
                'error': f'S3 client error: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'storage_location': 's3',
                'error': str(e)
            }
    
    def _upload_to_gcs(self, metadata: BackupMetadata) -> Dict[str, Any]:
        """Upload backup to Google Cloud Storage (placeholder)."""
        return {
            'success': False,
            'storage_location': 'gcs',
            'error': 'Google Cloud Storage integration not implemented'
        }
    
    def _upload_to_azure(self, metadata: BackupMetadata) -> Dict[str, Any]:
        """Upload backup to Azure Blob Storage (placeholder)."""
        return {
            'success': False,
            'storage_location': 'azure',
            'error': 'Azure Blob Storage integration not implemented'
        }
    
    def create_recovery_plan(self, target_timestamp: datetime, 
                           recovery_type: str = 'point_in_time',
                           databases: List[str] = None) -> Dict[str, Any]:
        """
        Create a recovery plan for point-in-time or full recovery.
        
        Args:
            target_timestamp: Target timestamp for recovery
            recovery_type: Type of recovery ('full', 'point_in_time', 'table_level')
            databases: List of databases to recover (None for all)
            
        Returns:
            Dictionary containing recovery plan details
        """
        try:
            recovery_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"Creating recovery plan: {recovery_id} for {target_timestamp}")
            
            # Find required backups
            required_backups = self._find_required_backups(target_timestamp, databases)
            
            if not required_backups:
                return {
                    'success': False,
                    'error': 'No suitable backups found for recovery',
                    'recovery_id': recovery_id
                }
            
            # Estimate recovery duration
            estimated_duration = self._estimate_recovery_duration(required_backups)
            
            # Create recovery steps
            recovery_steps = self._create_recovery_steps(
                required_backups, target_timestamp, recovery_type, databases
            )
            
            # Identify prerequisites
            prerequisites = self._identify_recovery_prerequisites(required_backups)
            
            # Assess risks
            risks = self._assess_recovery_risks(required_backups, recovery_type)
            
            # Create rollback plan
            rollback_plan = self._create_rollback_plan(recovery_type)
            
            # Create recovery plan
            recovery_plan = RecoveryPlan(
                recovery_id=recovery_id,
                target_timestamp=target_timestamp,
                recovery_type=recovery_type,
                required_backups=[backup['backup_id'] for backup in required_backups],
                estimated_duration=estimated_duration,
                recovery_steps=recovery_steps,
                prerequisites=prerequisites,
                risks=risks,
                rollback_plan=rollback_plan
            )
            
            # Store recovery plan
            self._store_recovery_plan(recovery_plan)
            
            logger.info(f"Recovery plan created: {recovery_id} ({len(required_backups)} backups, ~{estimated_duration:.1f}min)")
            
            return {
                'success': True,
                'recovery_plan': asdict(recovery_plan),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Recovery plan creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'recovery_id': recovery_id if 'recovery_id' in locals() else 'unknown',
                'timestamp': datetime.now().isoformat()
            }
    
    def _find_required_backups(self, target_timestamp: datetime, databases: List[str] = None) -> List[Dict[str, Any]]:
        """Find backups required for recovery to target timestamp."""
        try:
            if not self.redis_client:
                return []
            
            # Get all backup metadata
            backup_keys = self.redis_client.keys("mysql_backup:metadata:*")
            backups = []
            
            for key in backup_keys:
                try:
                    backup_data = self.redis_client.get(key)
                    if backup_data:
                        backup_dict = json.loads(backup_data)
                        backup_dict['timestamp'] = datetime.fromisoformat(backup_dict['timestamp'])
                        backup_dict['retention_date'] = datetime.fromisoformat(backup_dict['retention_date'])
                        backups.append(backup_dict)
                except Exception as e:
                    logger.debug(f"Could not parse backup metadata from {key}: {e}")
            
            # Filter backups by timestamp and databases
            suitable_backups = []
            for backup in backups:
                backup_time = backup['timestamp']
                
                # Must be before target timestamp
                if backup_time > target_timestamp:
                    continue
                
                # Check database filter
                if databases:
                    backup_databases = backup['database_name'].split(',')
                    if not any(db in backup_databases for db in databases):
                        continue
                
                # Must be valid
                if backup.get('validation_status') != 'valid':
                    continue
                
                suitable_backups.append(backup)
            
            # Sort by timestamp (newest first)
            suitable_backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # For point-in-time recovery, we need the most recent full backup
            # and any incremental backups after it
            required_backups = []
            
            # Find most recent full backup before target
            full_backup = None
            for backup in suitable_backups:
                if backup['backup_type'] == 'full':
                    full_backup = backup
                    break
            
            if full_backup:
                required_backups.append(full_backup)
                
                # Find incremental backups after the full backup
                for backup in suitable_backups:
                    if (backup['backup_type'] in ['incremental', 'differential'] and
                        backup['timestamp'] > full_backup['timestamp'] and
                        backup['timestamp'] <= target_timestamp):
                        required_backups.append(backup)
            
            # Sort required backups by timestamp (oldest first for restore order)
            required_backups.sort(key=lambda x: x['timestamp'])
            
            return required_backups
            
        except Exception as e:
            logger.error(f"Failed to find required backups: {e}")
            return []
    
    def _estimate_recovery_duration(self, required_backups: List[Dict[str, Any]]) -> float:
        """Estimate recovery duration in minutes."""
        try:
            total_size = sum(backup['file_size'] for backup in required_backups)
            
            # Rough estimation: 1GB takes about 5 minutes to restore
            size_gb = total_size / (1024 ** 3)
            base_duration = size_gb * 5
            
            # Add overhead for multiple backups
            overhead = len(required_backups) * 2  # 2 minutes per backup
            
            return base_duration + overhead
            
        except Exception as e:
            logger.error(f"Failed to estimate recovery duration: {e}")
            return 60.0  # Default to 1 hour
    
    def _create_recovery_steps(self, required_backups: List[Dict[str, Any]], 
                             target_timestamp: datetime, recovery_type: str,
                             databases: List[str] = None) -> List[Dict[str, Any]]:
        """Create detailed recovery steps."""
        steps = []
        
        # Step 1: Preparation
        steps.append({
            'step': 1,
            'title': 'Prepare for Recovery',
            'description': 'Stop applications and create current backup',
            'commands': [
                'systemctl stop vedfolnir',  # Stop application
                'mysqldump --all-databases > pre_recovery_backup.sql'  # Safety backup
            ],
            'estimated_duration': 5,
            'critical': True
        })
        
        # Step 2: Download backups if needed
        cloud_backups = [b for b in required_backups if b.get('storage_location') != 'local']
        if cloud_backups:
            steps.append({
                'step': 2,
                'title': 'Download Cloud Backups',
                'description': f'Download {len(cloud_backups)} backups from cloud storage',
                'commands': [f'# Download {b["backup_id"]} from {b.get("storage_location", "unknown")}' 
                           for b in cloud_backups],
                'estimated_duration': len(cloud_backups) * 3,
                'critical': True
            })
        
        # Step 3: Restore backups in order
        for i, backup in enumerate(required_backups):
            step_num = 3 + i
            steps.append({
                'step': step_num,
                'title': f'Restore Backup {backup["backup_id"]}',
                'description': f'Restore {backup["backup_type"]} backup from {backup["timestamp"]}',
                'commands': self._generate_restore_commands(backup),
                'estimated_duration': backup['file_size'] / (1024**3) * 5,  # 5 min per GB
                'critical': True
            })
        
        # Step 4: Apply point-in-time recovery if needed
        if recovery_type == 'point_in_time':
            steps.append({
                'step': len(steps) + 1,
                'title': 'Apply Point-in-Time Recovery',
                'description': f'Apply binary logs up to {target_timestamp}',
                'commands': [
                    f'mysqlbinlog --stop-datetime="{target_timestamp}" /var/log/mysql/mysql-bin.* | mysql'
                ],
                'estimated_duration': 10,
                'critical': True
            })
        
        # Step 5: Verify and restart
        steps.append({
            'step': len(steps) + 1,
            'title': 'Verify and Restart',
            'description': 'Verify data integrity and restart applications',
            'commands': [
                'mysql -e "SELECT COUNT(*) FROM information_schema.tables"',
                'systemctl start vedfolnir'
            ],
            'estimated_duration': 5,
            'critical': True
        })
        
        return steps
    
    def _generate_restore_commands(self, backup: Dict[str, Any]) -> List[str]:
        """Generate restore commands for a backup."""
        commands = []
        file_path = backup['file_path']
        
        # Handle different file types
        if file_path.endswith('.enc'):
            commands.append(f'# Decrypt backup file: {file_path}')
            commands.append(f'python -c "from cryptography.fernet import Fernet; ...; # Decrypt {file_path}"')
            file_path = file_path.replace('.enc', '')
        
        if file_path.endswith('.gz'):
            commands.append(f'gunzip -c {file_path} | mysql')
        elif file_path.endswith('.tar.gz'):
            commands.append(f'tar -xzf {file_path}')
            commands.append('mysql < extracted_backup.sql')
        else:
            commands.append(f'mysql < {file_path}')
        
        return commands
    
    def _identify_recovery_prerequisites(self, required_backups: List[Dict[str, Any]]) -> List[str]:
        """Identify prerequisites for recovery."""
        prerequisites = [
            'MySQL server must be running',
            'Sufficient disk space for backup restoration',
            'Application services should be stopped',
            'Database connections should be closed'
        ]
        
        # Add specific prerequisites based on backup types
        if any(b.get('encrypted') for b in required_backups):
            prerequisites.append('Backup encryption key must be available')
        
        if any(b.get('storage_location') != 'local' for b in required_backups):
            prerequisites.append('Cloud storage credentials must be configured')
        
        if any(b.get('compressed') for b in required_backups):
            prerequisites.append('Compression tools (gzip) must be installed')
        
        return prerequisites
    
    def _assess_recovery_risks(self, required_backups: List[Dict[str, Any]], recovery_type: str) -> List[str]:
        """Assess risks associated with recovery."""
        risks = [
            'Data loss: Any changes after backup timestamp will be lost',
            'Downtime: Application will be unavailable during recovery',
            'Disk space: Recovery requires significant temporary disk space'
        ]
        
        # Add specific risks
        if recovery_type == 'point_in_time':
            risks.append('Binary log availability: Point-in-time recovery requires binary logs')
        
        if len(required_backups) > 1:
            risks.append('Multiple backups: Failure in any backup can affect entire recovery')
        
        # Check backup ages
        oldest_backup = min(required_backups, key=lambda x: x['timestamp'])
        backup_age = datetime.now() - datetime.fromisoformat(oldest_backup['timestamp'])
        if backup_age.days > 7:
            risks.append(f'Old backup: Oldest backup is {backup_age.days} days old')
        
        return risks
    
    def _create_rollback_plan(self, recovery_type: str) -> List[Dict[str, Any]]:
        """Create rollback plan in case recovery fails."""
        rollback_steps = [
            {
                'step': 1,
                'title': 'Stop Recovery Process',
                'description': 'Immediately stop any ongoing recovery operations',
                'commands': ['killall mysql', 'killall mysqldump']
            },
            {
                'step': 2,
                'title': 'Restore Pre-Recovery Backup',
                'description': 'Restore the safety backup created before recovery',
                'commands': ['mysql < pre_recovery_backup.sql']
            },
            {
                'step': 3,
                'title': 'Restart Services',
                'description': 'Restart all services to previous state',
                'commands': ['systemctl start mysql', 'systemctl start vedfolnir']
            }
        ]
        
        return rollback_steps
    
    def _store_recovery_plan(self, recovery_plan: RecoveryPlan):
        """Store recovery plan in Redis."""
        try:
            if self.redis_client:
                plan_key = f"mysql_backup:recovery_plans:{recovery_plan.recovery_id}"
                self.redis_client.setex(
                    plan_key,
                    86400 * 7,  # Keep for 7 days
                    json.dumps(asdict(recovery_plan), default=str)
                )
        except Exception as e:
            logger.error(f"Failed to store recovery plan: {e}")
    
    def execute_recovery(self, recovery_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Execute a recovery plan.
        
        Args:
            recovery_id: ID of the recovery plan to execute
            confirm: Confirmation flag (required for safety)
            
        Returns:
            Dictionary containing recovery execution results
        """
        try:
            if not confirm:
                return {
                    'success': False,
                    'error': 'Recovery execution requires explicit confirmation (confirm=True)',
                    'recovery_id': recovery_id
                }
            
            # Load recovery plan
            recovery_plan = self._load_recovery_plan(recovery_id)
            if not recovery_plan:
                return {
                    'success': False,
                    'error': f'Recovery plan {recovery_id} not found',
                    'recovery_id': recovery_id
                }
            
            logger.info(f"Starting recovery execution: {recovery_id}")
            recovery_start = datetime.now()
            
            # Execute recovery steps
            execution_results = []
            for step in recovery_plan['recovery_steps']:
                step_result = self._execute_recovery_step(step)
                execution_results.append(step_result)
                
                if not step_result['success'] and step.get('critical', False):
                    logger.error(f"Critical recovery step failed: {step['title']}")
                    return {
                        'success': False,
                        'error': f"Critical step failed: {step['title']}",
                        'recovery_id': recovery_id,
                        'execution_results': execution_results,
                        'rollback_required': True
                    }
            
            recovery_duration = (datetime.now() - recovery_start).total_seconds()
            
            logger.info(f"Recovery completed: {recovery_id} ({recovery_duration:.1f}s)")
            
            return {
                'success': True,
                'recovery_id': recovery_id,
                'execution_results': execution_results,
                'recovery_duration': recovery_duration,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Recovery execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'recovery_id': recovery_id,
                'rollback_required': True,
                'timestamp': datetime.now().isoformat()
            }
    
    def _load_recovery_plan(self, recovery_id: str) -> Optional[Dict[str, Any]]:
        """Load recovery plan from Redis."""
        try:
            if not self.redis_client:
                return None
            
            plan_key = f"mysql_backup:recovery_plans:{recovery_id}"
            plan_data = self.redis_client.get(plan_key)
            
            if plan_data:
                return json.loads(plan_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load recovery plan: {e}")
            return None
    
    def _execute_recovery_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single recovery step."""
        try:
            step_start = datetime.now()
            
            logger.info(f"Executing recovery step {step['step']}: {step['title']}")
            
            # Execute commands
            command_results = []
            for command in step.get('commands', []):
                if command.startswith('#'):
                    # Comment/note - skip execution
                    command_results.append({
                        'command': command,
                        'success': True,
                        'note': 'Comment - not executed'
                    })
                    continue
                
                try:
                    # Execute command (simplified - would need more sophisticated execution)
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout per command
                    )
                    
                    command_results.append({
                        'command': command,
                        'success': result.returncode == 0,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'return_code': result.returncode
                    })
                    
                except subprocess.TimeoutExpired:
                    command_results.append({
                        'command': command,
                        'success': False,
                        'error': 'Command timed out'
                    })
                except Exception as e:
                    command_results.append({
                        'command': command,
                        'success': False,
                        'error': str(e)
                    })
            
            step_duration = (datetime.now() - step_start).total_seconds()
            
            # Determine overall step success
            step_success = all(cmd.get('success', False) for cmd in command_results)
            
            return {
                'step': step['step'],
                'title': step['title'],
                'success': step_success,
                'duration': step_duration,
                'command_results': command_results
            }
            
        except Exception as e:
            logger.error(f"Recovery step execution failed: {e}")
            return {
                'step': step.get('step', 'unknown'),
                'title': step.get('title', 'Unknown Step'),
                'success': False,
                'error': str(e)
            }
    
    def start_backup_scheduler(self) -> Dict[str, Any]:
        """Start the backup scheduler."""
        try:
            if self.scheduler_running:
                return {
                    'success': False,
                    'message': 'Backup scheduler is already running',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Schedule backup jobs
            for job in self.backup_jobs.values():
                if job.enabled:
                    schedule.every().day.at("02:00").do(self._execute_backup_job, job.job_id)
                    logger.info(f"Scheduled backup job: {job.name}")
            
            # Start scheduler thread
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("Backup scheduler started")
            return {
                'success': True,
                'message': f'Backup scheduler started with {len(self.backup_jobs)} jobs',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start backup scheduler: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def stop_backup_scheduler(self) -> Dict[str, Any]:
        """Stop the backup scheduler."""
        try:
            if not self.scheduler_running:
                return {
                    'success': False,
                    'message': 'Backup scheduler is not running',
                    'timestamp': datetime.now().isoformat()
                }
            
            self.scheduler_running = False
            schedule.clear()
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
            
            logger.info("Backup scheduler stopped")
            return {
                'success': True,
                'message': 'Backup scheduler stopped',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop backup scheduler: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.scheduler_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)
    
    def _execute_backup_job(self, job_id: str):
        """Execute a scheduled backup job."""
        try:
            job = self.backup_jobs.get(job_id)
            if not job:
                logger.error(f"Backup job not found: {job_id}")
                return
            
            logger.info(f"Executing scheduled backup job: {job.name}")
            
            # Execute pre-backup scripts
            for script in job.pre_backup_scripts:
                try:
                    subprocess.run(script, shell=True, check=True)
                except Exception as e:
                    logger.warning(f"Pre-backup script failed: {e}")
            
            # Create backup
            backup_result = self.create_backup(
                backup_type=job.backup_type,
                databases=job.databases,
                options={
                    'compress': job.compression_enabled,
                    'encrypt': job.encryption_enabled,
                    'storage_locations': job.storage_locations
                }
            )
            
            # Execute post-backup scripts
            for script in job.post_backup_scripts:
                try:
                    subprocess.run(script, shell=True, check=True)
                except Exception as e:
                    logger.warning(f"Post-backup script failed: {e}")
            
            # Send notifications if configured
            if job.notification_settings and backup_result.get('success'):
                self._send_backup_notification(job, backup_result)
            
        except Exception as e:
            logger.error(f"Backup job execution failed: {e}")
    
    def _send_backup_notification(self, job: BackupJob, backup_result: Dict[str, Any]):
        """Send backup completion notification."""
        try:
            # Placeholder for notification implementation
            # Could integrate with email, Slack, webhooks, etc.
            logger.info(f"Backup notification: {job.name} completed successfully")
        except Exception as e:
            logger.error(f"Failed to send backup notification: {e}")
    
    def list_backups(self, limit: int = 50, backup_type: str = None) -> Dict[str, Any]:
        """List available backups."""
        try:
            if not self.redis_client:
                return {
                    'success': False,
                    'error': 'Redis not available for backup metadata',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get all backup metadata
            backup_keys = self.redis_client.keys("mysql_backup:metadata:*")
            backups = []
            
            for key in backup_keys:
                try:
                    backup_data = self.redis_client.get(key)
                    if backup_data:
                        backup_dict = json.loads(backup_data)
                        
                        # Filter by backup type if specified
                        if backup_type and backup_dict.get('backup_type') != backup_type:
                            continue
                        
                        backups.append(backup_dict)
                except Exception as e:
                    logger.debug(f"Could not parse backup metadata from {key}: {e}")
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Limit results
            backups = backups[:limit]
            
            return {
                'success': True,
                'backups': backups,
                'total_count': len(backups),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def delete_backup(self, backup_id: str, force: bool = False) -> Dict[str, Any]:
        """Delete a backup and its metadata."""
        try:
            # Load backup metadata
            if not self.redis_client:
                return {
                    'success': False,
                    'error': 'Redis not available for backup metadata',
                    'backup_id': backup_id
                }
            
            metadata_key = f"mysql_backup:metadata:{backup_id}"
            backup_data = self.redis_client.get(metadata_key)
            
            if not backup_data:
                return {
                    'success': False,
                    'error': f'Backup {backup_id} not found',
                    'backup_id': backup_id
                }
            
            backup_metadata = json.loads(backup_data)
            
            # Check retention date unless forced
            if not force:
                retention_date = datetime.fromisoformat(backup_metadata['retention_date'])
                if datetime.now() < retention_date:
                    return {
                        'success': False,
                        'error': f'Backup {backup_id} has not reached retention date ({retention_date})',
                        'backup_id': backup_id
                    }
            
            # Delete local file
            file_path = Path(backup_metadata['file_path'])
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted backup file: {file_path}")
            
            # Delete from cloud storage if applicable
            storage_location = backup_metadata.get('storage_location', 'local')
            if storage_location != 'local':
                cloud_delete_result = self._delete_from_cloud_storage(backup_metadata, storage_location)
                if not cloud_delete_result.get('success'):
                    logger.warning(f"Failed to delete from cloud storage: {cloud_delete_result.get('error')}")
            
            # Delete metadata
            self.redis_client.delete(metadata_key)
            
            logger.info(f"Backup deleted: {backup_id}")
            return {
                'success': True,
                'backup_id': backup_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return {
                'success': False,
                'error': str(e),
                'backup_id': backup_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def _delete_from_cloud_storage(self, backup_metadata: Dict[str, Any], storage_location: str) -> Dict[str, Any]:
        """Delete backup from cloud storage."""
        try:
            if storage_location == 's3' and 's3' in self.cloud_clients:
                return self._delete_from_s3(backup_metadata)
            else:
                return {
                    'success': False,
                    'error': f'Cloud storage deletion not implemented for {storage_location}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _delete_from_s3(self, backup_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Delete backup from AWS S3."""
        try:
            s3_client = self.cloud_clients['s3']
            bucket_name = os.getenv('MYSQL_BACKUP_S3_BUCKET')
            
            if not bucket_name:
                return {
                    'success': False,
                    'error': 'S3 bucket name not configured'
                }
            
            # Reconstruct S3 key
            timestamp = datetime.fromisoformat(backup_metadata['timestamp'])
            s3_key = f"mysql-backups/{timestamp.strftime('%Y/%m/%d')}/{Path(backup_metadata['file_path']).name}"
            
            # Delete object
            s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            
            return {
                'success': True,
                'storage_location': 's3',
                'bucket': bucket_name,
                'key': s3_key
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_expired_backups(self) -> Dict[str, Any]:
        """Clean up expired backups based on retention policy."""
        try:
            if not self.redis_client:
                return {
                    'success': False,
                    'error': 'Redis not available for backup metadata',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get all backup metadata
            backup_keys = self.redis_client.keys("mysql_backup:metadata:*")
            expired_backups = []
            cleanup_results = []
            
            for key in backup_keys:
                try:
                    backup_data = self.redis_client.get(key)
                    if backup_data:
                        backup_dict = json.loads(backup_data)
                        retention_date = datetime.fromisoformat(backup_dict['retention_date'])
                        
                        if datetime.now() > retention_date:
                            expired_backups.append(backup_dict['backup_id'])
                except Exception as e:
                    logger.debug(f"Could not parse backup metadata from {key}: {e}")
            
            # Delete expired backups
            for backup_id in expired_backups:
                delete_result = self.delete_backup(backup_id, force=True)
                cleanup_results.append({
                    'backup_id': backup_id,
                    'deleted': delete_result.get('success', False),
                    'error': delete_result.get('error')
                })
            
            successful_deletions = len([r for r in cleanup_results if r['deleted']])
            
            logger.info(f"Cleanup completed: {successful_deletions}/{len(expired_backups)} expired backups deleted")
            
            return {
                'success': True,
                'expired_backups_found': len(expired_backups),
                'successful_deletions': successful_deletions,
                'cleanup_results': cleanup_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_backup_status_summary(self) -> Dict[str, Any]:
        """Get backup system status summary."""
        try:
            # Get backup statistics
            backup_list = self.list_backups(limit=1000)
            backups = backup_list.get('backups', [])
            
            # Calculate statistics
            total_backups = len(backups)
            total_size = sum(backup.get('file_size', 0) for backup in backups)
            
            # Group by type
            backup_types = {}
            for backup in backups:
                backup_type = backup.get('backup_type', 'unknown')
                backup_types[backup_type] = backup_types.get(backup_type, 0) + 1
            
            # Find latest backup
            latest_backup = backups[0] if backups else None
            
            # Check scheduler status
            scheduler_status = {
                'running': self.scheduler_running,
                'active_jobs': len([job for job in self.backup_jobs.values() if job.enabled]),
                'total_jobs': len(self.backup_jobs)
            }
            
            # Storage statistics
            storage_stats = {}
            for backup in backups:
                location = backup.get('storage_location', 'local')
                if location not in storage_stats:
                    storage_stats[location] = {'count': 0, 'size': 0}
                storage_stats[location]['count'] += 1
                storage_stats[location]['size'] += backup.get('file_size', 0)
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_backups': total_backups,
                'total_size_bytes': total_size,
                'total_size_gb': total_size / (1024**3),
                'backup_types': backup_types,
                'latest_backup': {
                    'backup_id': latest_backup.get('backup_id') if latest_backup else None,
                    'timestamp': latest_backup.get('timestamp') if latest_backup else None,
                    'type': latest_backup.get('backup_type') if latest_backup else None
                },
                'scheduler_status': scheduler_status,
                'storage_statistics': storage_stats,
                'cloud_storage_available': list(self.cloud_clients.keys()),
                'backup_directory': str(self.backup_dir)
            }
            
            return {
                'success': True,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup status summary: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def cleanup_resources(self):
        """Clean up resources."""
        try:
            # Stop scheduler
            self.stop_backup_scheduler()
            
            # Close cloud storage clients
            for client_name, client in self.cloud_clients.items():
                try:
                    if hasattr(client, 'close'):
                        client.close()
                except:
                    pass
            
            # Close Redis connection
            if self.redis_client:
                try:
                    self.redis_client.close()
                except:
                    pass
            
            logger.info("MySQL Backup and Recovery resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")


def main():
    """Command-line interface for MySQL Backup and Recovery."""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='MySQL Backup and Recovery for Vedfolnir')
    parser.add_argument('--action', choices=[
        'backup', 'list-backups', 'delete-backup', 'create-recovery-plan', 
        'execute-recovery', 'start-scheduler', 'stop-scheduler', 'cleanup', 'status'
    ], required=True, help='Action to perform')
    
    parser.add_argument('--backup-type', choices=['full', 'incremental', 'differential'], 
                       default='full', help='Type of backup (default: full)')
    parser.add_argument('--databases', nargs='+', help='Databases to backup (default: all)')
    parser.add_argument('--compress', action='store_true', help='Compress backup files')
    parser.add_argument('--encrypt', action='store_true', help='Encrypt backup files')
    parser.add_argument('--storage-locations', nargs='+', default=['local'], 
                       help='Storage locations (local, s3, gcs, azure)')
    
    parser.add_argument('--backup-id', help='Backup ID for operations')
    parser.add_argument('--recovery-id', help='Recovery ID for operations')
    parser.add_argument('--target-timestamp', help='Target timestamp for recovery (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--recovery-type', choices=['full', 'point_in_time', 'table_level'], 
                       default='point_in_time', help='Type of recovery')
    
    parser.add_argument('--force', action='store_true', help='Force operation (bypass safety checks)')
    parser.add_argument('--confirm', action='store_true', help='Confirm destructive operations')
    parser.add_argument('--limit', type=int, default=50, help='Limit for list operations')
    
    parser.add_argument('--output-format', choices=['json', 'table'], default='table',
                       help='Output format (default: table)')
    
    args = parser.parse_args()
    
    # Initialize backup and recovery system
    try:
        backup_recovery = MySQLBackupRecovery()
        
        if args.action == 'backup':
            options = {
                'compress': args.compress,
                'encrypt': args.encrypt,
                'storage_locations': args.storage_locations
            }
            result = backup_recovery.create_backup(args.backup_type, args.databases, options)
            print_result(result, args.output_format)
            
        elif args.action == 'list-backups':
            result = backup_recovery.list_backups(args.limit, args.backup_type)
            print_backup_list(result, args.output_format)
            
        elif args.action == 'delete-backup':
            if not args.backup_id:
                print("Error: --backup-id is required for delete operation")
                sys.exit(1)
            result = backup_recovery.delete_backup(args.backup_id, args.force)
            print_result(result, args.output_format)
            
        elif args.action == 'create-recovery-plan':
            if not args.target_timestamp:
                print("Error: --target-timestamp is required for recovery plan")
                sys.exit(1)
            
            target_dt = datetime.strptime(args.target_timestamp, '%Y-%m-%d %H:%M:%S')
            result = backup_recovery.create_recovery_plan(target_dt, args.recovery_type, args.databases)
            print_result(result, args.output_format)
            
        elif args.action == 'execute-recovery':
            if not args.recovery_id:
                print("Error: --recovery-id is required for recovery execution")
                sys.exit(1)
            if not args.confirm:
                print("Error: --confirm is required for recovery execution (destructive operation)")
                sys.exit(1)
            
            result = backup_recovery.execute_recovery(args.recovery_id, args.confirm)
            print_result(result, args.output_format)
            
        elif args.action == 'start-scheduler':
            result = backup_recovery.start_backup_scheduler()
            print_result(result, args.output_format)
            
            if result.get('success'):
                print("Scheduler started. Press Ctrl+C to stop...")
                try:
                    while backup_recovery.scheduler_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nStopping scheduler...")
                    backup_recovery.stop_backup_scheduler()
            
        elif args.action == 'stop-scheduler':
            result = backup_recovery.stop_backup_scheduler()
            print_result(result, args.output_format)
            
        elif args.action == 'cleanup':
            result = backup_recovery.cleanup_expired_backups()
            print_result(result, args.output_format)
            
        elif args.action == 'status':
            result = backup_recovery.get_backup_status_summary()
            print_result(result, args.output_format)
        
        # Cleanup
        backup_recovery.cleanup_resources()
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        print_result(error_result, args.output_format)
        sys.exit(1)


def print_backup_list(result: Dict[str, Any], output_format: str):
    """Print backup list in the specified format."""
    if output_format == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        # Table format
        print(f"\n{'='*100}")
        print(f"MySQL Backups - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}")
        
        if result.get('success'):
            backups = result.get('backups', [])
            if backups:
                print(f"Found {len(backups)} backups:\n")
                
                # Table header
                print(f"{'Backup ID':<25} {'Type':<12} {'Database':<20} {'Size':<10} {'Date':<20} {'Status':<10}")
                print("-" * 100)
                
                for backup in backups:
                    backup_id = backup.get('backup_id', 'unknown')[:24]
                    backup_type = backup.get('backup_type', 'unknown')
                    database = backup.get('database_name', 'unknown')[:19]
                    size_mb = backup.get('file_size', 0) / (1024*1024)
                    timestamp = backup.get('timestamp', 'unknown')[:19]
                    status = backup.get('validation_status', 'unknown')
                    
                    print(f"{backup_id:<25} {backup_type:<12} {database:<20} {size_mb:>8.1f}MB {timestamp:<20} {status:<10}")
            else:
                print("No backups found")
        else:
            print(f"❌ Failed to list backups: {result.get('error', 'Unknown error')}")
        
        print(f"{'='*100}\n")


def print_result(result: Dict[str, Any], output_format: str):
    """Print result in the specified format."""
    if output_format == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        # Table format
        print(f"\n{'='*60}")
        print(f"MySQL Backup & Recovery - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if result.get('success'):
            print("✅ Operation completed successfully")
            
            # Print specific result information
            if 'backup_id' in result:
                print(f"\n📦 Backup Information:")
                print(f"  Backup ID: {result['backup_id']}")
                
                if 'backup_metadata' in result:
                    metadata = result['backup_metadata']
                    print(f"  Type: {metadata.get('backup_type', 'unknown')}")
                    print(f"  Database: {metadata.get('database_name', 'unknown')}")
                    print(f"  Size: {metadata.get('file_size', 0) / (1024*1024):.1f} MB")
                    print(f"  Duration: {metadata.get('backup_duration', 0):.1f} seconds")
                    print(f"  Compressed: {'Yes' if metadata.get('compressed') else 'No'}")
                    print(f"  Encrypted: {'Yes' if metadata.get('encrypted') else 'No'}")
            
            if 'recovery_plan' in result:
                plan = result['recovery_plan']
                print(f"\n🔄 Recovery Plan:")
                print(f"  Recovery ID: {plan['recovery_id']}")
                print(f"  Target Time: {plan['target_timestamp']}")
                print(f"  Required Backups: {len(plan['required_backups'])}")
                print(f"  Estimated Duration: {plan['estimated_duration']:.1f} minutes")
                print(f"  Recovery Steps: {len(plan['recovery_steps'])}")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"\n📊 Backup Status:")
                print(f"  Total Backups: {summary.get('total_backups', 0)}")
                print(f"  Total Size: {summary.get('total_size_gb', 0):.2f} GB")
                print(f"  Scheduler Running: {'Yes' if summary.get('scheduler_status', {}).get('running') else 'No'}")
                print(f"  Active Jobs: {summary.get('scheduler_status', {}).get('active_jobs', 0)}")
                
                latest = summary.get('latest_backup', {})
                if latest.get('backup_id'):
                    print(f"  Latest Backup: {latest['backup_id']} ({latest.get('timestamp', 'unknown')})")
        
        else:
            print("❌ Operation failed")
            if 'error' in result:
                print(f"Error: {result['error']}")
        
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
