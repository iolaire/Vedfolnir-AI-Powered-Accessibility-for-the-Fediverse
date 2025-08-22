#!/usr/bin/env python3
"""
MySQL Test Database Cleanup Utility

Cleans up MySQL test databases created during testing.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MySQLTestDatabaseCleanup:
    """Cleanup utility for MySQL test databases"""
    
    def __init__(self, config_override: Dict[str, Any] = None):
        """Initialize cleanup utility"""
        self.config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'database_user_1d7b0d0696a20',
            'password': 'EQA&bok7',
            'base_database': 'vedfolnir_test',
            'charset': 'utf8mb4'
        }
        
        if config_override:
            self.config.update(config_override)
        
        # Load from environment
        self._load_from_environment()
        
        self.databases_found = []
        self.databases_cleaned = []
        self.cleanup_errors = []
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mapping = {
            'host': 'MYSQL_TEST_HOST',
            'port': 'MYSQL_TEST_PORT',
            'user': 'MYSQL_TEST_USER',
            'password': 'MYSQL_TEST_PASSWORD',
            'base_database': 'MYSQL_TEST_DATABASE',
        }
        
        for key, env_var in env_mapping.items():
            if os.getenv(env_var):
                if key == 'port':
                    self.config[key] = int(os.getenv(env_var))
                else:
                    self.config[key] = os.getenv(env_var)
    
    def find_test_databases(self) -> List[str]:
        """Find all test databases"""
        logger.info("Scanning for test databases...")
        
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                charset=self.config['charset']
            )
            
            with connection.cursor() as cursor:
                # Find databases matching test patterns
                patterns = [
                    f"{self.config['base_database']}_%",
                    "vedfolnir_test_%",
                    "%_test_%",
                ]
                
                all_test_dbs = set()
                
                for pattern in patterns:
                    cursor.execute(f"SHOW DATABASES LIKE '{pattern}'")
                    results = cursor.fetchall()
                    for (db_name,) in results:
                        all_test_dbs.add(db_name)
                
                self.databases_found = sorted(list(all_test_dbs))
            
            connection.close()
            
            logger.info(f"Found {len(self.databases_found)} test databases")
            for db_name in self.databases_found:
                logger.info(f"  - {db_name}")
            
            return self.databases_found
            
        except Exception as e:
            logger.error(f"Failed to find test databases: {e}")
            return []
    
    def cleanup_database(self, database_name: str) -> bool:
        """Clean up a single test database"""
        logger.info(f"Cleaning up database: {database_name}")
        
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                charset=self.config['charset']
            )
            
            with connection.cursor() as cursor:
                # Drop the database
                cursor.execute(f"DROP DATABASE IF EXISTS `{database_name}`")
                connection.commit()
            
            connection.close()
            
            logger.info(f"✅ Cleaned up database: {database_name}")
            self.databases_cleaned.append(database_name)
            return True
            
        except Exception as e:
            error_msg = f"Failed to cleanup database {database_name}: {e}"
            logger.error(f"❌ {error_msg}")
            self.cleanup_errors.append(error_msg)
            return False
    
    def cleanup_all_test_databases(self, dry_run: bool = False) -> bool:
        """Clean up all test databases"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Cleaning up all test databases...")
        
        # Find test databases
        test_databases = self.find_test_databases()
        
        if not test_databases:
            logger.info("No test databases found to clean up")
            return True
        
        if dry_run:
            logger.info("DRY RUN: Would clean up the following databases:")
            for db_name in test_databases:
                logger.info(f"  - {db_name}")
            return True
        
        # Clean up each database
        success_count = 0
        for db_name in test_databases:
            if self.cleanup_database(db_name):
                success_count += 1
        
        logger.info(f"Cleanup completed: {success_count}/{len(test_databases)} databases cleaned")
        
        return success_count == len(test_databases)
    
    def cleanup_old_test_databases(self, days_old: int = 1, dry_run: bool = False) -> bool:
        """Clean up test databases older than specified days"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Cleaning up test databases older than {days_old} days...")
        
        try:
            import pymysql
            from datetime import datetime, timedelta
            
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                charset=self.config['charset']
            )
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            old_databases = []
            
            with connection.cursor() as cursor:
                # Find test databases
                test_databases = self.find_test_databases()
                
                for db_name in test_databases:
                    # Get database creation time (approximation using information_schema)
                    cursor.execute(f"""
                        SELECT CREATE_TIME 
                        FROM information_schema.SCHEMATA 
                        WHERE SCHEMA_NAME = '{db_name}'
                    """)
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        create_time = result[0]
                        if create_time < cutoff_date:
                            old_databases.append(db_name)
                    else:
                        # If we can't determine age, assume it's old
                        old_databases.append(db_name)
            
            connection.close()
            
            if not old_databases:
                logger.info(f"No test databases older than {days_old} days found")
                return True
            
            if dry_run:
                logger.info(f"DRY RUN: Would clean up {len(old_databases)} old databases:")
                for db_name in old_databases:
                    logger.info(f"  - {db_name}")
                return True
            
            # Clean up old databases
            success_count = 0
            for db_name in old_databases:
                if self.cleanup_database(db_name):
                    success_count += 1
            
            logger.info(f"Old database cleanup completed: {success_count}/{len(old_databases)} databases cleaned")
            
            return success_count == len(old_databases)
            
        except Exception as e:
            logger.error(f"Failed to cleanup old test databases: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about test databases"""
        logger.info("Gathering test database information...")
        
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                charset=self.config['charset']
            )
            
            database_info = {}
            
            with connection.cursor() as cursor:
                test_databases = self.find_test_databases()
                
                for db_name in test_databases:
                    # Get database size and table count
                    cursor.execute(f"""
                        SELECT 
                            COUNT(*) as table_count,
                            COALESCE(SUM(data_length + index_length), 0) as size_bytes
                        FROM information_schema.TABLES 
                        WHERE table_schema = '{db_name}'
                    """)
                    
                    result = cursor.fetchone()
                    table_count = result[0] if result else 0
                    size_bytes = result[1] if result else 0
                    
                    # Get creation time
                    cursor.execute(f"""
                        SELECT CREATE_TIME 
                        FROM information_schema.SCHEMATA 
                        WHERE SCHEMA_NAME = '{db_name}'
                    """)
                    
                    create_result = cursor.fetchone()
                    create_time = create_result[0] if create_result and create_result[0] else "Unknown"
                    
                    database_info[db_name] = {
                        'table_count': table_count,
                        'size_bytes': size_bytes,
                        'size_mb': round(size_bytes / (1024 * 1024), 2),
                        'created': create_time
                    }
            
            connection.close()
            
            return database_info
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}
    
    def generate_cleanup_report(self) -> str:
        """Generate cleanup report"""
        database_info = self.get_database_info()
        
        report = [
            "=== MySQL Test Database Cleanup Report ===",
            "",
            f"MySQL Server: {self.config['host']}:{self.config['port']}",
            f"Test User: {self.config['user']}",
            f"Base Database Pattern: {self.config['base_database']}_%",
            "",
            "DATABASE INFORMATION:",
        ]
        
        if database_info:
            total_size_mb = sum(info['size_mb'] for info in database_info.values())
            total_tables = sum(info['table_count'] for info in database_info.values())
            
            report.extend([
                f"Total test databases: {len(database_info)}",
                f"Total size: {total_size_mb:.2f} MB",
                f"Total tables: {total_tables}",
                "",
                "DATABASE DETAILS:",
            ])
            
            for db_name, info in database_info.items():
                report.append(f"  {db_name}:")
                report.append(f"    Tables: {info['table_count']}")
                report.append(f"    Size: {info['size_mb']:.2f} MB")
                report.append(f"    Created: {info['created']}")
                report.append("")
        else:
            report.append("No test databases found")
            report.append("")
        
        if self.databases_cleaned:
            report.extend([
                "CLEANED UP DATABASES:",
                ""
            ])
            for db_name in self.databases_cleaned:
                report.append(f"  ✅ {db_name}")
            report.append("")
        
        if self.cleanup_errors:
            report.extend([
                "CLEANUP ERRORS:",
                ""
            ])
            for error in self.cleanup_errors:
                report.append(f"  ❌ {error}")
            report.append("")
        
        report.extend([
            "CLEANUP COMMANDS:",
            f"  All databases: python {__file__} --all",
            f"  Dry run: python {__file__} --all --dry-run",
            f"  Old databases: python {__file__} --old-days 7",
            f"  Database info: python {__file__} --info",
        ])
        
        return "\n".join(report)


def main():
    """Main cleanup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MySQL Test Database Cleanup Utility")
    parser.add_argument('--all', action='store_true', help='Clean up all test databases')
    parser.add_argument('--old-days', type=int, help='Clean up databases older than N days')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without actually doing it')
    parser.add_argument('--info', action='store_true', help='Show information about test databases')
    parser.add_argument('--database', type=str, help='Clean up specific database')
    
    args = parser.parse_args()
    
    if not any([args.all, args.old_days, args.info, args.database]):
        parser.print_help()
        return False
    
    # Initialize cleanup utility
    cleanup = MySQLTestDatabaseCleanup()
    
    success = True
    
    try:
        if args.info:
            # Show database information
            database_info = cleanup.get_database_info()
            if database_info:
                print("\nTest Database Information:")
                print("=" * 50)
                total_size = 0
                for db_name, info in database_info.items():
                    print(f"{db_name}:")
                    print(f"  Tables: {info['table_count']}")
                    print(f"  Size: {info['size_mb']:.2f} MB")
                    print(f"  Created: {info['created']}")
                    total_size += info['size_mb']
                print("=" * 50)
                print(f"Total: {len(database_info)} databases, {total_size:.2f} MB")
            else:
                print("No test databases found")
        
        elif args.database:
            # Clean up specific database
            success = cleanup.cleanup_database(args.database)
        
        elif args.all:
            # Clean up all test databases
            success = cleanup.cleanup_all_test_databases(dry_run=args.dry_run)
        
        elif args.old_days:
            # Clean up old test databases
            success = cleanup.cleanup_old_test_databases(days_old=args.old_days, dry_run=args.dry_run)
        
        # Generate and save report
        report = cleanup.generate_cleanup_report()
        
        project_root = Path(__file__).parent.parent.parent
        report_path = project_root / 'scripts' / 'mysql_migration' / 'mysql_test_cleanup_report.txt'
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Cleanup report saved to: {report_path}")
        
        if success:
            logger.info("✅ MySQL test database cleanup completed successfully")
        else:
            logger.error("❌ MySQL test database cleanup completed with errors")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
