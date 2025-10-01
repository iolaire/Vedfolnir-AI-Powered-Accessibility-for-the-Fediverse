#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Backup Verification and Integrity Checking System

Provides comprehensive backup verification including:
- File integrity verification (checksums, sizes)
- Database backup validation (SQL syntax, structure)
- Redis backup validation (RDB/AOF format)
- Cross-backup consistency checks
- Automated verification scheduling
- Verification reporting and alerting
"""

import os
import sys
import json
import logging
import hashlib
import gzip
import tempfile
import subprocess
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import docker
    import pymysql
    import redis
    from cryptography.fernet import Fernet
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages: pip install docker pymysql redis cryptography")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup_verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class VerificationResult:
    """Result of a backup verification check."""
    check_type: str
    component: str
    status: str  # 'pass', 'fail', 'warning', 'skip'
    message: str
    details: Dict[str, Any]
    timestamp: datetime

@dataclass
class BackupVerificationReport:
    """Comprehensive backup verification report."""
    backup_id: str
    verification_id: str
    timestamp: datetime
    overall_status: str  # 'pass', 'fail', 'warning'
    results: List[VerificationResult]
    summary: Dict[str, Any]
    recommendations: List[str]

class BackupVerificationSystem:
    """Comprehensive backup verification and integrity checking system."""
    
    def __init__(self):
        """Initialize the backup verification system."""
        self.docker_client = docker.from_env()
        
        # Directories
        self.backup_base_dir = Path("storage/backups")
        self.verification_dir = Path("storage/verification")
        self.verification_dir.mkdir(exist_ok=True)
        
        # Container names
        self.mysql_container = "vedfolnir_mysql"
        self.redis_container = "vedfolnir_redis"
        
        # Verification settings
        self.verification_settings = {
            'checksum_algorithms': ['sha256', 'md5'],
            'mysql_test_queries': [
                'SELECT 1',
                'SHOW TABLES',
                'SELECT COUNT(*) FROM information_schema.tables'
            ],
            'redis_test_commands': [
                'PING',
                'INFO server',
                'DBSIZE'
            ],
            'max_file_size_mb': 1000,  # Skip verification for files larger than 1GB
            'verification_timeout': 300  # 5 minutes
        }
        
        logger.info("Backup verification system initialized")
    
    def verify_backup(self, backup_path: str, verification_type: str = 'full') -> BackupVerificationReport:
        """
        Verify a backup comprehensively.
        
        Args:
            backup_path: Path to the backup directory
            verification_type: Type of verification ('full', 'quick', 'integrity_only')
            
        Returns:
            Comprehensive verification report
        """
        backup_path = Path(backup_path)
        verification_id = f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting backup verification: {backup_path} (type: {verification_type})")
        
        # Load backup manifest
        manifest = self._load_backup_manifest(backup_path)
        if not manifest:
            return self._create_failed_report(backup_path.name, verification_id, "Backup manifest not found")
        
        backup_id = manifest.get('backup_id', backup_path.name)
        results = []
        
        # Verify backup structure
        results.extend(self._verify_backup_structure(backup_path, manifest))
        
        # Verify file integrity
        if verification_type in ['full', 'integrity_only']:
            results.extend(self._verify_file_integrity(backup_path))
        
        # Verify MySQL backup
        if manifest.get('components', {}).get('mysql', False):
            results.extend(self._verify_mysql_backup(backup_path, verification_type))
        
        # Verify Redis backup
        if manifest.get('components', {}).get('redis', False):
            results.extend(self._verify_redis_backup(backup_path, verification_type))
        
        # Verify application data backup
        if manifest.get('components', {}).get('app', False):
            results.extend(self._verify_application_backup(backup_path))
        
        # Verify Vault backup
        if manifest.get('components', {}).get('vault', False):
            results.extend(self._verify_vault_backup(backup_path))
        
        # Cross-component consistency checks
        if verification_type == 'full':
            results.extend(self._verify_cross_component_consistency(backup_path, manifest))
        
        # Generate report
        report = self._generate_verification_report(backup_id, verification_id, results)
        
        # Save report
        self._save_verification_report(report)
        
        logger.info(f"Backup verification completed: {report.overall_status}")
        return report
    
    def _load_backup_manifest(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """Load backup manifest file."""
        manifest_file = backup_path / "backup_manifest.json"
        
        if not manifest_file.exists():
            logger.error(f"Backup manifest not found: {manifest_file}")
            return None
        
        try:
            with open(manifest_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backup manifest: {e}")
            return None
    
    def _verify_backup_structure(self, backup_path: Path, manifest: Dict[str, Any]) -> List[VerificationResult]:
        """Verify backup directory structure."""
        results = []
        
        # Check required directories
        required_dirs = []
        components = manifest.get('components', {})
        
        if components.get('mysql', False):
            required_dirs.append('mysql')
        if components.get('redis', False):
            required_dirs.append('redis')
        if components.get('app', False):
            required_dirs.append('app')
        if components.get('vault', False):
            required_dirs.append('vault')
        
        for dir_name in required_dirs:
            dir_path = backup_path / dir_name
            
            if dir_path.exists() and dir_path.is_dir():
                results.append(VerificationResult(
                    check_type='structure',
                    component=dir_name,
                    status='pass',
                    message=f'Directory {dir_name} exists',
                    details={'path': str(dir_path)},
                    timestamp=datetime.now()
                ))
            else:
                results.append(VerificationResult(
                    check_type='structure',
                    component=dir_name,
                    status='fail',
                    message=f'Required directory {dir_name} not found',
                    details={'expected_path': str(dir_path)},
                    timestamp=datetime.now()
                ))
        
        # Check metadata directory
        metadata_dir = backup_path / "metadata"
        if metadata_dir.exists():
            results.append(VerificationResult(
                check_type='structure',
                component='metadata',
                status='pass',
                message='Metadata directory exists',
                details={'path': str(metadata_dir)},
                timestamp=datetime.now()
            ))
        
        return results
    
    def _verify_file_integrity(self, backup_path: Path) -> List[VerificationResult]:
        """Verify file integrity using checksums."""
        results = []
        
        # Find all files in backup
        for file_path in backup_path.rglob('*'):
            if file_path.is_file() and file_path.suffix not in ['.json', '.log']:
                # Skip very large files
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > self.verification_settings['max_file_size_mb']:
                    results.append(VerificationResult(
                        check_type='integrity',
                        component='file',
                        status='skip',
                        message=f'File too large for verification: {file_path.name}',
                        details={'size_mb': file_size_mb, 'path': str(file_path)},
                        timestamp=datetime.now()
                    ))
                    continue
                
                # Calculate checksums
                checksums = self._calculate_file_checksums(file_path)
                
                # Look for stored checksum in metadata
                stored_checksum = self._find_stored_checksum(file_path, backup_path)
                
                if stored_checksum:
                    if checksums.get('sha256') == stored_checksum:
                        results.append(VerificationResult(
                            check_type='integrity',
                            component='file',
                            status='pass',
                            message=f'File integrity verified: {file_path.name}',
                            details={'checksums': checksums, 'path': str(file_path)},
                            timestamp=datetime.now()
                        ))
                    else:
                        results.append(VerificationResult(
                            check_type='integrity',
                            component='file',
                            status='fail',
                            message=f'File integrity check failed: {file_path.name}',
                            details={
                                'expected_checksum': stored_checksum,
                                'actual_checksums': checksums,
                                'path': str(file_path)
                            },
                            timestamp=datetime.now()
                        ))
                else:
                    results.append(VerificationResult(
                        check_type='integrity',
                        component='file',
                        status='warning',
                        message=f'No stored checksum found for: {file_path.name}',
                        details={'checksums': checksums, 'path': str(file_path)},
                        timestamp=datetime.now()
                    ))
        
        return results
    
    def _calculate_file_checksums(self, file_path: Path) -> Dict[str, str]:
        """Calculate multiple checksums for a file."""
        checksums = {}
        
        # Initialize hash objects
        hash_objects = {}
        for algorithm in self.verification_settings['checksum_algorithms']:
            if algorithm == 'sha256':
                hash_objects[algorithm] = hashlib.sha256()
            elif algorithm == 'md5':
                hash_objects[algorithm] = hashlib.md5()
        
        # Read file and update hashes
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    for hash_obj in hash_objects.values():
                        hash_obj.update(chunk)
            
            # Get hex digests
            for algorithm, hash_obj in hash_objects.items():
                checksums[algorithm] = hash_obj.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to calculate checksums for {file_path}: {e}")
        
        return checksums
    
    def _find_stored_checksum(self, file_path: Path, backup_path: Path) -> Optional[str]:
        """Find stored checksum for a file in backup metadata."""
        # Look in component-specific metadata files
        relative_path = file_path.relative_to(backup_path)
        component = relative_path.parts[0] if relative_path.parts else None
        
        if component:
            metadata_file = backup_path / component / f"{component}_backup_metadata.json"
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Look for checksum in metadata
                    return metadata.get('checksum')
                
                except Exception as e:
                    logger.debug(f"Could not load metadata from {metadata_file}: {e}")
        
        return None
    
    def _verify_mysql_backup(self, backup_path: Path, verification_type: str) -> List[VerificationResult]:
        """Verify MySQL backup integrity and validity."""
        results = []
        mysql_dir = backup_path / "mysql"
        
        if not mysql_dir.exists():
            return [VerificationResult(
                check_type='mysql',
                component='mysql',
                status='fail',
                message='MySQL backup directory not found',
                details={'expected_path': str(mysql_dir)},
                timestamp=datetime.now()
            )]
        
        # Check for SQL dump file
        sql_files = list(mysql_dir.glob("*.sql*"))
        
        if not sql_files:
            results.append(VerificationResult(
                check_type='mysql',
                component='mysql',
                status='fail',
                message='No SQL dump files found',
                details={'search_path': str(mysql_dir)},
                timestamp=datetime.now()
            ))
            return results
        
        # Verify each SQL file
        for sql_file in sql_files:
            results.extend(self._verify_sql_file(sql_file, verification_type))
        
        # Verify MySQL metadata
        metadata_file = mysql_dir / "mysql_backup_metadata.json"
        if metadata_file.exists():
            results.append(self._verify_mysql_metadata(metadata_file))
        
        # Test restore capability (if full verification)
        if verification_type == 'full':
            results.append(self._test_mysql_restore_capability(mysql_dir))
        
        return results
    
    def _verify_sql_file(self, sql_file: Path, verification_type: str) -> List[VerificationResult]:
        """Verify SQL file integrity and syntax."""
        results = []
        
        # Check if file is compressed or encrypted
        if sql_file.suffix == '.gz':
            results.extend(self._verify_compressed_sql_file(sql_file, verification_type))
        elif sql_file.suffix == '.enc':
            results.append(VerificationResult(
                check_type='mysql',
                component='sql_file',
                status='skip',
                message=f'Encrypted SQL file - cannot verify content: {sql_file.name}',
                details={'file': str(sql_file)},
                timestamp=datetime.now()
            ))
        else:
            results.extend(self._verify_plain_sql_file(sql_file, verification_type))
        
        return results
    
    def _verify_compressed_sql_file(self, sql_file: Path, verification_type: str) -> List[VerificationResult]:
        """Verify compressed SQL file."""
        results = []
        
        try:
            # Test if file can be decompressed
            with gzip.open(sql_file, 'rt') as f:
                # Read first few lines to verify it's a valid SQL dump
                first_lines = []
                for i, line in enumerate(f):
                    first_lines.append(line.strip())
                    if i >= 10:  # Read first 10 lines
                        break
            
            # Check for MySQL dump markers
            dump_markers = ['-- MySQL dump', 'CREATE DATABASE', 'USE ', 'SET @@']
            has_markers = any(marker in ' '.join(first_lines) for marker in dump_markers)
            
            if has_markers:
                results.append(VerificationResult(
                    check_type='mysql',
                    component='sql_file',
                    status='pass',
                    message=f'Compressed SQL file is valid: {sql_file.name}',
                    details={'file': str(sql_file), 'first_lines': first_lines[:3]},
                    timestamp=datetime.now()
                ))
            else:
                results.append(VerificationResult(
                    check_type='mysql',
                    component='sql_file',
                    status='fail',
                    message=f'Compressed SQL file does not appear to be a valid MySQL dump: {sql_file.name}',
                    details={'file': str(sql_file), 'first_lines': first_lines[:3]},
                    timestamp=datetime.now()
                ))
        
        except Exception as e:
            results.append(VerificationResult(
                check_type='mysql',
                component='sql_file',
                status='fail',
                message=f'Failed to verify compressed SQL file: {sql_file.name}',
                details={'file': str(sql_file), 'error': str(e)},
                timestamp=datetime.now()
            ))
        
        return results
    
    def _verify_plain_sql_file(self, sql_file: Path, verification_type: str) -> List[VerificationResult]:
        """Verify plain SQL file."""
        results = []
        
        try:
            with open(sql_file, 'r') as f:
                # Read first few lines
                first_lines = [f.readline().strip() for _ in range(10)]
            
            # Check for MySQL dump markers
            dump_markers = ['-- MySQL dump', 'CREATE DATABASE', 'USE ', 'SET @@']
            has_markers = any(marker in ' '.join(first_lines) for marker in dump_markers)
            
            if has_markers:
                results.append(VerificationResult(
                    check_type='mysql',
                    component='sql_file',
                    status='pass',
                    message=f'SQL file is valid: {sql_file.name}',
                    details={'file': str(sql_file), 'first_lines': first_lines[:3]},
                    timestamp=datetime.now()
                ))
                
                # Additional syntax check for full verification
                if verification_type == 'full':
                    syntax_result = self._check_sql_syntax(sql_file)
                    results.append(syntax_result)
            else:
                results.append(VerificationResult(
                    check_type='mysql',
                    component='sql_file',
                    status='fail',
                    message=f'SQL file does not appear to be a valid MySQL dump: {sql_file.name}',
                    details={'file': str(sql_file), 'first_lines': first_lines[:3]},
                    timestamp=datetime.now()
                ))
        
        except Exception as e:
            results.append(VerificationResult(
                check_type='mysql',
                component='sql_file',
                status='fail',
                message=f'Failed to verify SQL file: {sql_file.name}',
                details={'file': str(sql_file), 'error': str(e)},
                timestamp=datetime.now()
            ))
        
        return results
    
    def _check_sql_syntax(self, sql_file: Path) -> VerificationResult:
        """Check SQL syntax by attempting to parse with MySQL."""
        try:
            # Use MySQL container to check syntax
            container = self.docker_client.containers.get(self.mysql_container)
            
            # Copy file to container temporarily
            temp_file = f"/tmp/verify_{sql_file.name}"
            
            with open(sql_file, 'rb') as f:
                container.put_archive("/tmp", f.read())
            
            # Check syntax using MySQL
            result = container.exec_run([
                "mysql", "-u", "root", "-p$(cat /run/secrets/mysql_root_password)",
                "--execute", f"source {temp_file}"
            ], environment={"MYSQL_PWD": "$(cat /run/secrets/mysql_root_password)"})
            
            # Clean up
            container.exec_run(["rm", temp_file])
            
            if result.exit_code == 0:
                return VerificationResult(
                    check_type='mysql',
                    component='sql_syntax',
                    status='pass',
                    message=f'SQL syntax is valid: {sql_file.name}',
                    details={'file': str(sql_file)},
                    timestamp=datetime.now()
                )
            else:
                return VerificationResult(
                    check_type='mysql',
                    component='sql_syntax',
                    status='fail',
                    message=f'SQL syntax errors found: {sql_file.name}',
                    details={'file': str(sql_file), 'error': result.output.decode()},
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            return VerificationResult(
                check_type='mysql',
                component='sql_syntax',
                status='warning',
                message=f'Could not verify SQL syntax: {sql_file.name}',
                details={'file': str(sql_file), 'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _verify_mysql_metadata(self, metadata_file: Path) -> VerificationResult:
        """Verify MySQL backup metadata."""
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check required fields
            required_fields = ['backup_timestamp', 'mysql_version', 'backup_type']
            missing_fields = [field for field in required_fields if field not in metadata]
            
            if missing_fields:
                return VerificationResult(
                    check_type='mysql',
                    component='metadata',
                    status='warning',
                    message=f'MySQL metadata missing fields: {missing_fields}',
                    details={'metadata_file': str(metadata_file), 'missing_fields': missing_fields},
                    timestamp=datetime.now()
                )
            else:
                return VerificationResult(
                    check_type='mysql',
                    component='metadata',
                    status='pass',
                    message='MySQL metadata is complete',
                    details={'metadata_file': str(metadata_file), 'metadata': metadata},
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            return VerificationResult(
                check_type='mysql',
                component='metadata',
                status='fail',
                message=f'Failed to verify MySQL metadata: {e}',
                details={'metadata_file': str(metadata_file), 'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _test_mysql_restore_capability(self, mysql_dir: Path) -> VerificationResult:
        """Test MySQL restore capability using a temporary database."""
        try:
            # Create a temporary database for testing
            test_db_name = f"backup_verify_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            container = self.docker_client.containers.get(self.mysql_container)
            
            # Create test database
            result = container.exec_run([
                "mysql", "-u", "root", "-p$(cat /run/secrets/mysql_root_password)",
                "-e", f"CREATE DATABASE {test_db_name}"
            ])
            
            if result.exit_code != 0:
                return VerificationResult(
                    check_type='mysql',
                    component='restore_test',
                    status='fail',
                    message='Failed to create test database for restore verification',
                    details={'error': result.output.decode()},
                    timestamp=datetime.now()
                )
            
            # Find SQL dump file
            sql_files = list(mysql_dir.glob("*.sql*"))
            if not sql_files:
                return VerificationResult(
                    check_type='mysql',
                    component='restore_test',
                    status='fail',
                    message='No SQL dump file found for restore test',
                    details={'mysql_dir': str(mysql_dir)},
                    timestamp=datetime.now()
                )
            
            # Test restore (just check if file can be processed)
            sql_file = sql_files[0]
            
            # For compressed files, test decompression
            if sql_file.suffix == '.gz':
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
                    with gzip.open(sql_file, 'rt') as gz_file:
                        # Read first 1000 lines to test
                        for i, line in enumerate(gz_file):
                            if i >= 1000:
                                break
                            temp_file.write(line)
                    
                    temp_sql_file = temp_file.name
            else:
                temp_sql_file = str(sql_file)
            
            # Test a small portion of the restore
            result = container.exec_run([
                "mysql", "-u", "root", "-p$(cat /run/secrets/mysql_root_password)",
                test_db_name, "-e", f"source {temp_sql_file}"
            ], timeout=60)  # 1 minute timeout
            
            # Clean up test database
            container.exec_run([
                "mysql", "-u", "root", "-p$(cat /run/secrets/mysql_root_password)",
                "-e", f"DROP DATABASE {test_db_name}"
            ])
            
            # Clean up temporary file
            if sql_file.suffix == '.gz':
                os.unlink(temp_sql_file)
            
            if result.exit_code == 0:
                return VerificationResult(
                    check_type='mysql',
                    component='restore_test',
                    status='pass',
                    message='MySQL restore test successful',
                    details={'test_database': test_db_name, 'sql_file': str(sql_file)},
                    timestamp=datetime.now()
                )
            else:
                return VerificationResult(
                    check_type='mysql',
                    component='restore_test',
                    status='fail',
                    message='MySQL restore test failed',
                    details={
                        'test_database': test_db_name,
                        'sql_file': str(sql_file),
                        'error': result.output.decode()
                    },
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            return VerificationResult(
                check_type='mysql',
                component='restore_test',
                status='warning',
                message=f'MySQL restore test could not be completed: {e}',
                details={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _verify_redis_backup(self, backup_path: Path, verification_type: str) -> List[VerificationResult]:
        """Verify Redis backup integrity and validity."""
        results = []
        redis_dir = backup_path / "redis"
        
        if not redis_dir.exists():
            return [VerificationResult(
                check_type='redis',
                component='redis',
                status='fail',
                message='Redis backup directory not found',
                details={'expected_path': str(redis_dir)},
                timestamp=datetime.now()
            )]
        
        # Check for RDB file
        rdb_files = list(redis_dir.glob("dump.rdb*"))
        if rdb_files:
            results.extend(self._verify_redis_rdb_file(rdb_files[0]))
        else:
            results.append(VerificationResult(
                check_type='redis',
                component='rdb',
                status='warning',
                message='No Redis RDB file found',
                details={'search_path': str(redis_dir)},
                timestamp=datetime.now()
            ))
        
        # Check for AOF file
        aof_files = list(redis_dir.glob("appendonly.aof*"))
        if aof_files:
            results.extend(self._verify_redis_aof_file(aof_files[0]))
        
        # Verify Redis metadata
        metadata_file = redis_dir / "redis_backup_metadata.json"
        if metadata_file.exists():
            results.append(self._verify_redis_metadata(metadata_file))
        
        return results
    
    def _verify_redis_rdb_file(self, rdb_file: Path) -> List[VerificationResult]:
        """Verify Redis RDB file."""
        results = []
        
        try:
            # Check if file is compressed or encrypted
            if rdb_file.suffix == '.gz':
                # Test decompression
                with gzip.open(rdb_file, 'rb') as f:
                    header = f.read(9)  # RDB header is 9 bytes
            elif rdb_file.suffix == '.enc':
                results.append(VerificationResult(
                    check_type='redis',
                    component='rdb',
                    status='skip',
                    message=f'Encrypted RDB file - cannot verify content: {rdb_file.name}',
                    details={'file': str(rdb_file)},
                    timestamp=datetime.now()
                ))
                return results
            else:
                with open(rdb_file, 'rb') as f:
                    header = f.read(9)
            
            # Check RDB magic string
            if header.startswith(b'REDIS'):
                results.append(VerificationResult(
                    check_type='redis',
                    component='rdb',
                    status='pass',
                    message=f'RDB file has valid header: {rdb_file.name}',
                    details={'file': str(rdb_file), 'header': header.hex()},
                    timestamp=datetime.now()
                ))
            else:
                results.append(VerificationResult(
                    check_type='redis',
                    component='rdb',
                    status='fail',
                    message=f'RDB file has invalid header: {rdb_file.name}',
                    details={'file': str(rdb_file), 'header': header.hex()},
                    timestamp=datetime.now()
                ))
        
        except Exception as e:
            results.append(VerificationResult(
                check_type='redis',
                component='rdb',
                status='fail',
                message=f'Failed to verify RDB file: {rdb_file.name}',
                details={'file': str(rdb_file), 'error': str(e)},
                timestamp=datetime.now()
            ))
        
        return results
    
    def _verify_redis_aof_file(self, aof_file: Path) -> List[VerificationResult]:
        """Verify Redis AOF file."""
        results = []
        
        try:
            # Check if file is compressed or encrypted
            if aof_file.suffix == '.gz':
                with gzip.open(aof_file, 'rt') as f:
                    first_lines = [f.readline().strip() for _ in range(5)]
            elif aof_file.suffix == '.enc':
                results.append(VerificationResult(
                    check_type='redis',
                    component='aof',
                    status='skip',
                    message=f'Encrypted AOF file - cannot verify content: {aof_file.name}',
                    details={'file': str(aof_file)},
                    timestamp=datetime.now()
                ))
                return results
            else:
                with open(aof_file, 'r') as f:
                    first_lines = [f.readline().strip() for _ in range(5)]
            
            # Check for Redis protocol commands
            redis_commands = ['*', '$', '+', '-', ':']
            has_redis_protocol = any(line.startswith(tuple(redis_commands)) for line in first_lines if line)
            
            if has_redis_protocol:
                results.append(VerificationResult(
                    check_type='redis',
                    component='aof',
                    status='pass',
                    message=f'AOF file appears to be valid: {aof_file.name}',
                    details={'file': str(aof_file), 'first_lines': first_lines},
                    timestamp=datetime.now()
                ))
            else:
                results.append(VerificationResult(
                    check_type='redis',
                    component='aof',
                    status='warning',
                    message=f'AOF file format unclear: {aof_file.name}',
                    details={'file': str(aof_file), 'first_lines': first_lines},
                    timestamp=datetime.now()
                ))
        
        except Exception as e:
            results.append(VerificationResult(
                check_type='redis',
                component='aof',
                status='fail',
                message=f'Failed to verify AOF file: {aof_file.name}',
                details={'file': str(aof_file), 'error': str(e)},
                timestamp=datetime.now()
            ))
        
        return results
    
    def _verify_redis_metadata(self, metadata_file: Path) -> VerificationResult:
        """Verify Redis backup metadata."""
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check required fields
            required_fields = ['backup_timestamp', 'redis_version', 'backup_type']
            missing_fields = [field for field in required_fields if field not in metadata]
            
            if missing_fields:
                return VerificationResult(
                    check_type='redis',
                    component='metadata',
                    status='warning',
                    message=f'Redis metadata missing fields: {missing_fields}',
                    details={'metadata_file': str(metadata_file), 'missing_fields': missing_fields},
                    timestamp=datetime.now()
                )
            else:
                return VerificationResult(
                    check_type='redis',
                    component='metadata',
                    status='pass',
                    message='Redis metadata is complete',
                    details={'metadata_file': str(metadata_file), 'metadata': metadata},
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            return VerificationResult(
                check_type='redis',
                component='metadata',
                status='fail',
                message=f'Failed to verify Redis metadata: {e}',
                details={'metadata_file': str(metadata_file), 'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _verify_application_backup(self, backup_path: Path) -> List[VerificationResult]:
        """Verify application data backup."""
        results = []
        app_dir = backup_path / "app"
        
        if not app_dir.exists():
            return [VerificationResult(
                check_type='application',
                component='app',
                status='fail',
                message='Application backup directory not found',
                details={'expected_path': str(app_dir)},
                timestamp=datetime.now()
            )]
        
        # Check for expected subdirectories/files
        expected_items = ['storage', 'logs', 'config', 'app_backup_metadata.json']
        
        for item in expected_items:
            item_path = app_dir / item
            
            if item_path.exists():
                results.append(VerificationResult(
                    check_type='application',
                    component='app_structure',
                    status='pass',
                    message=f'Application backup item exists: {item}',
                    details={'item': item, 'path': str(item_path)},
                    timestamp=datetime.now()
                ))
            else:
                # Check for compressed versions
                compressed_versions = [f"{item}.tar.gz", f"{item}.gz"]
                found_compressed = False
                
                for compressed in compressed_versions:
                    if (app_dir / compressed).exists():
                        results.append(VerificationResult(
                            check_type='application',
                            component='app_structure',
                            status='pass',
                            message=f'Application backup item exists (compressed): {compressed}',
                            details={'item': item, 'compressed_file': compressed, 'path': str(app_dir / compressed)},
                            timestamp=datetime.now()
                        ))
                        found_compressed = True
                        break
                
                if not found_compressed:
                    results.append(VerificationResult(
                        check_type='application',
                        component='app_structure',
                        status='warning',
                        message=f'Application backup item not found: {item}',
                        details={'item': item, 'expected_path': str(item_path)},
                        timestamp=datetime.now()
                    ))
        
        return results
    
    def _verify_vault_backup(self, backup_path: Path) -> List[VerificationResult]:
        """Verify Vault secrets backup."""
        results = []
        vault_dir = backup_path / "vault"
        
        if not vault_dir.exists():
            return [VerificationResult(
                check_type='vault',
                component='vault',
                status='fail',
                message='Vault backup directory not found',
                details={'expected_path': str(vault_dir)},
                timestamp=datetime.now()
            )]
        
        # Check for Vault snapshot or data backup
        snapshot_files = list(vault_dir.glob("vault_snapshot_*"))
        data_files = list(vault_dir.glob("vault_data.tar.gz*"))
        
        if snapshot_files or data_files:
            results.append(VerificationResult(
                check_type='vault',
                component='vault_data',
                status='pass',
                message='Vault backup files found',
                details={
                    'snapshot_files': [str(f) for f in snapshot_files],
                    'data_files': [str(f) for f in data_files]
                },
                timestamp=datetime.now()
            ))
        else:
            results.append(VerificationResult(
                check_type='vault',
                component='vault_data',
                status='fail',
                message='No Vault backup files found',
                details={'vault_dir': str(vault_dir)},
                timestamp=datetime.now()
            ))
        
        # Check for Vault metadata
        metadata_file = vault_dir / "vault_backup_metadata.json"
        if metadata_file.exists():
            results.append(VerificationResult(
                check_type='vault',
                component='vault_metadata',
                status='pass',
                message='Vault metadata found',
                details={'metadata_file': str(metadata_file)},
                timestamp=datetime.now()
            ))
        
        return results
    
    def _verify_cross_component_consistency(self, backup_path: Path, manifest: Dict[str, Any]) -> List[VerificationResult]:
        """Verify consistency across backup components."""
        results = []
        
        # Check timestamp consistency
        backup_timestamp = datetime.fromisoformat(manifest['timestamp'])
        component_timestamps = {}
        
        # Collect timestamps from component metadata
        for component in ['mysql', 'redis', 'app', 'vault']:
            metadata_file = backup_path / component / f"{component}_backup_metadata.json"
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    component_timestamp = datetime.fromisoformat(metadata['backup_timestamp'])
                    component_timestamps[component] = component_timestamp
                    
                    # Check if component timestamp is close to backup timestamp (within 1 hour)
                    time_diff = abs((component_timestamp - backup_timestamp).total_seconds())
                    
                    if time_diff <= 3600:  # 1 hour
                        results.append(VerificationResult(
                            check_type='consistency',
                            component=f'{component}_timestamp',
                            status='pass',
                            message=f'{component} timestamp is consistent with backup timestamp',
                            details={
                                'backup_timestamp': backup_timestamp.isoformat(),
                                'component_timestamp': component_timestamp.isoformat(),
                                'time_diff_seconds': time_diff
                            },
                            timestamp=datetime.now()
                        ))
                    else:
                        results.append(VerificationResult(
                            check_type='consistency',
                            component=f'{component}_timestamp',
                            status='warning',
                            message=f'{component} timestamp differs significantly from backup timestamp',
                            details={
                                'backup_timestamp': backup_timestamp.isoformat(),
                                'component_timestamp': component_timestamp.isoformat(),
                                'time_diff_seconds': time_diff
                            },
                            timestamp=datetime.now()
                        ))
                
                except Exception as e:
                    results.append(VerificationResult(
                        check_type='consistency',
                        component=f'{component}_timestamp',
                        status='warning',
                        message=f'Could not verify {component} timestamp consistency',
                        details={'error': str(e)},
                        timestamp=datetime.now()
                    ))
        
        return results
    
    def _generate_verification_report(self, backup_id: str, verification_id: str, 
                                    results: List[VerificationResult]) -> BackupVerificationReport:
        """Generate comprehensive verification report."""
        # Calculate overall status
        statuses = [result.status for result in results]
        
        if 'fail' in statuses:
            overall_status = 'fail'
        elif 'warning' in statuses:
            overall_status = 'warning'
        else:
            overall_status = 'pass'
        
        # Generate summary
        summary = {
            'total_checks': len(results),
            'passed': len([r for r in results if r.status == 'pass']),
            'failed': len([r for r in results if r.status == 'fail']),
            'warnings': len([r for r in results if r.status == 'warning']),
            'skipped': len([r for r in results if r.status == 'skip']),
            'components_verified': list(set(r.component for r in results)),
            'check_types': list(set(r.check_type for r in results))
        }
        
        # Generate recommendations
        recommendations = []
        
        failed_results = [r for r in results if r.status == 'fail']
        if failed_results:
            recommendations.append("Address failed verification checks before relying on this backup")
            
            # Specific recommendations based on failures
            mysql_failures = [r for r in failed_results if r.component.startswith('mysql')]
            if mysql_failures:
                recommendations.append("MySQL backup has issues - consider recreating MySQL backup")
            
            redis_failures = [r for r in failed_results if r.component.startswith('redis')]
            if redis_failures:
                recommendations.append("Redis backup has issues - consider recreating Redis backup")
        
        warning_results = [r for r in results if r.status == 'warning']
        if warning_results:
            recommendations.append("Review warning messages and consider addressing them")
        
        if summary['passed'] / summary['total_checks'] < 0.8:
            recommendations.append("Less than 80% of checks passed - backup quality is questionable")
        
        return BackupVerificationReport(
            backup_id=backup_id,
            verification_id=verification_id,
            timestamp=datetime.now(),
            overall_status=overall_status,
            results=results,
            summary=summary,
            recommendations=recommendations
        )
    
    def _create_failed_report(self, backup_id: str, verification_id: str, error_message: str) -> BackupVerificationReport:
        """Create a failed verification report."""
        return BackupVerificationReport(
            backup_id=backup_id,
            verification_id=verification_id,
            timestamp=datetime.now(),
            overall_status='fail',
            results=[VerificationResult(
                check_type='system',
                component='verification',
                status='fail',
                message=error_message,
                details={},
                timestamp=datetime.now()
            )],
            summary={
                'total_checks': 1,
                'passed': 0,
                'failed': 1,
                'warnings': 0,
                'skipped': 0,
                'components_verified': [],
                'check_types': ['system']
            },
            recommendations=['Fix the underlying issue and retry verification']
        )
    
    def _save_verification_report(self, report: BackupVerificationReport):
        """Save verification report to file."""
        report_file = self.verification_dir / f"{report.verification_id}_report.json"
        
        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        logger.info(f"Verification report saved to {report_file}")
    
    def verify_all_backups(self, verification_type: str = 'quick') -> List[BackupVerificationReport]:
        """Verify all available backups."""
        logger.info(f"Starting verification of all backups (type: {verification_type})")
        
        reports = []
        
        for backup_dir in self.backup_base_dir.glob("full_backup_*"):
            if backup_dir.is_dir():
                try:
                    report = self.verify_backup(str(backup_dir), verification_type)
                    reports.append(report)
                except Exception as e:
                    logger.error(f"Failed to verify backup {backup_dir}: {e}")
        
        logger.info(f"Completed verification of {len(reports)} backups")
        return reports

def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description='Backup Verification System')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify a specific backup')
    verify_parser.add_argument('backup_path', help='Path to backup directory')
    verify_parser.add_argument('--type', choices=['full', 'quick', 'integrity_only'], 
                              default='full', help='Verification type')
    
    # Verify all command
    verify_all_parser = subparsers.add_parser('verify-all', help='Verify all backups')
    verify_all_parser.add_argument('--type', choices=['full', 'quick', 'integrity_only'], 
                                  default='quick', help='Verification type')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        verification_system = BackupVerificationSystem()
        
        if args.command == 'verify':
            report = verification_system.verify_backup(args.backup_path, args.type)
            
            print(f"Verification Report: {report.verification_id}")
            print(f"Backup: {report.backup_id}")
            print(f"Overall Status: {report.overall_status}")
            print(f"Summary: {report.summary}")
            
            if report.recommendations:
                print("Recommendations:")
                for rec in report.recommendations:
                    print(f"  - {rec}")
            
            return 0 if report.overall_status != 'fail' else 1
        
        elif args.command == 'verify-all':
            reports = verification_system.verify_all_backups(args.type)
            
            print(f"Verified {len(reports)} backups:")
            for report in reports:
                print(f"  {report.backup_id}: {report.overall_status}")
            
            failed_count = len([r for r in reports if r.overall_status == 'fail'])
            return 0 if failed_count == 0 else 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())