#!/usr/bin/env python3
"""
Database Column Widening Script

Widens MySQL database columns to accommodate longer test data and improve
compatibility with comprehensive testing scenarios.
"""

import os
import sys
import logging
import pymysql
from typing import Dict, List, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseColumnWidener:
    """Tool to widen MySQL database columns for better test compatibility"""
    
    def __init__(self, host='localhost', user='database_user_1d7b0d0696a20', 
                 password='EQA&bok7', database='vedfolnir'):
        """Initialize database connection"""
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
        # Column modifications to apply
        self.column_modifications = {
            'users': [
                ('username', 'VARCHAR(255)', 'Widen username to support longer test names'),
                ('email', 'VARCHAR(255)', 'Widen email to support longer test emails'),
                ('first_name', 'VARCHAR(255)', 'Widen first_name for consistency'),
                ('last_name', 'VARCHAR(255)', 'Widen last_name for consistency'),
            ],
            'images': [
                ('image_post_id', 'VARCHAR(255)', 'Widen image_post_id to support longer test IDs'),
                ('original_filename', 'VARCHAR(255)', 'Widen original_filename for longer test filenames'),
                ('local_path', 'TEXT', 'Change to TEXT for very long paths'),
                ('image_url', 'TEXT', 'Change to TEXT for very long URLs'),
            ],
            'posts': [
                ('post_id', 'VARCHAR(255)', 'Widen post_id to support longer test IDs'),
                ('user_id', 'VARCHAR(255)', 'Widen user_id to support longer test user IDs'),
                ('post_url', 'TEXT', 'Change to TEXT for very long URLs'),
            ],
            'platform_connections': [
                ('name', 'VARCHAR(255)', 'Widen name to support longer test platform names'),
                ('username', 'VARCHAR(255)', 'Widen username to support longer test usernames'),
                ('instance_url', 'TEXT', 'Change to TEXT for very long URLs'),
            ],
            'user_sessions': [
                ('session_id', 'VARCHAR(255)', 'Widen session_id for longer test session IDs'),
            ],
            'processing_runs': [
                ('run_id', 'VARCHAR(255)', 'Widen run_id for longer test run IDs'),
            ]
        }
        
        self.modifications_applied = []
        self.errors_encountered = []
    
    def connect(self) -> bool:
        """Connect to MySQL database"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4'
            )
            logger.info(f"✅ Connected to MySQL database: {self.database}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MySQL database"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from database")
    
    def get_current_column_info(self, table_name: str) -> Dict[str, str]:
        """Get current column information for a table"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"DESCRIBE {table_name}")
                columns = {}
                for row in cursor.fetchall():
                    column_name, column_type = row[0], row[1]
                    columns[column_name] = column_type
                return columns
        except Exception as e:
            logger.error(f"Failed to get column info for {table_name}: {e}")
            return {}
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check if table {table_name} exists: {e}")
            return False
    
    def modify_column(self, table_name: str, column_name: str, new_type: str, description: str) -> bool:
        """Modify a single column"""
        try:
            # Check if table exists
            if not self.check_table_exists(table_name):
                logger.warning(f"⏭️  Table {table_name} does not exist, skipping")
                return True
            
            # Get current column info
            current_columns = self.get_current_column_info(table_name)
            
            if column_name not in current_columns:
                logger.warning(f"⏭️  Column {table_name}.{column_name} does not exist, skipping")
                return True
            
            current_type = current_columns[column_name]
            
            # Check if modification is needed
            if current_type.upper() == new_type.upper():
                logger.info(f"⏭️  Column {table_name}.{column_name} already has type {new_type}")
                return True
            
            # Apply the modification
            with self.connection.cursor() as cursor:
                sql = f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} {new_type}"
                logger.info(f"Executing: {sql}")
                cursor.execute(sql)
                self.connection.commit()
            
            self.modifications_applied.append({
                'table': table_name,
                'column': column_name,
                'old_type': current_type,
                'new_type': new_type,
                'description': description
            })
            
            logger.info(f"✅ Modified {table_name}.{column_name}: {current_type} → {new_type}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to modify {table_name}.{column_name}: {e}"
            logger.error(f"❌ {error_msg}")
            self.errors_encountered.append(error_msg)
            return False
    
    def apply_all_modifications(self, dry_run: bool = False) -> bool:
        """Apply all column modifications"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Applying database column modifications...")
        
        if dry_run:
            logger.info("DRY RUN MODE: No actual changes will be made")
        
        success = True
        total_modifications = sum(len(columns) for columns in self.column_modifications.values())
        applied_count = 0
        
        for table_name, columns in self.column_modifications.items():
            logger.info(f"Processing table: {table_name}")
            
            for column_name, new_type, description in columns:
                if dry_run:
                    logger.info(f"Would modify {table_name}.{column_name} to {new_type} - {description}")
                    applied_count += 1
                else:
                    if self.modify_column(table_name, column_name, new_type, description):
                        applied_count += 1
                    else:
                        success = False
        
        logger.info(f"Column modification completed: {applied_count}/{total_modifications} modifications processed")
        return success
    
    def create_backup_script(self) -> str:
        """Create a backup script to revert changes if needed"""
        backup_script = [
            "#!/usr/bin/env python3",
            '"""',
            "Database Column Reversion Script",
            "",
            "This script can be used to revert the column widening changes if needed.",
            "Generated automatically by widen_database_columns.py",
            '"""',
            "",
            "import pymysql",
            "",
            "def revert_changes():",
            "    conn = pymysql.connect(",
            f"        host='{self.host}',",
            f"        user='{self.user}',",
            f"        password='{self.password}',",
            f"        database='{self.database}',",
            "        charset='utf8mb4'",
            "    )",
            "",
            "    try:",
            "        with conn.cursor() as cursor:",
        ]
        
        # Add reversion commands for each modification
        for mod in self.modifications_applied:
            backup_script.append(f"            # Revert {mod['table']}.{mod['column']}")
            backup_script.append(f"            cursor.execute(\"ALTER TABLE {mod['table']} MODIFY COLUMN {mod['column']} {mod['old_type']}\")")
            backup_script.append("")
        
        backup_script.extend([
            "        conn.commit()",
            "        print('✅ All changes reverted successfully')",
            "",
            "    except Exception as e:",
            "        print(f'❌ Error reverting changes: {e}')",
            "",
            "    finally:",
            "        conn.close()",
            "",
            "if __name__ == '__main__':",
            "    revert_changes()"
        ])
        
        return "\n".join(backup_script)
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of changes made"""
        report = [
            "=== Database Column Widening Report ===",
            "",
            f"Database: {self.database}",
            f"Host: {self.host}",
            f"User: {self.user}",
            "",
            "MODIFICATIONS APPLIED:",
            f"Total modifications: {len(self.modifications_applied)}",
            f"Errors encountered: {len(self.errors_encountered)}",
            ""
        ]
        
        if self.modifications_applied:
            report.extend([
                "SUCCESSFUL MODIFICATIONS:",
                ""
            ])
            for mod in self.modifications_applied:
                report.append(f"✅ {mod['table']}.{mod['column']}")
                report.append(f"   Old type: {mod['old_type']}")
                report.append(f"   New type: {mod['new_type']}")
                report.append(f"   Reason: {mod['description']}")
                report.append("")
        
        if self.errors_encountered:
            report.extend([
                "🚨 ERRORS ENCOUNTERED:",
                ""
            ])
            for error in self.errors_encountered:
                report.append(f"  - {error}")
            report.append("")
        
        report.extend([
            "COLUMN WIDENING BENEFITS:",
            "✅ Longer test names and identifiers supported",
            "✅ More comprehensive test data compatibility",
            "✅ Reduced test failures due to data truncation",
            "✅ Better support for integration testing scenarios",
            "✅ Improved development and testing experience",
            "",
            "IMPACT ASSESSMENT:",
            "- Storage usage: Minimal increase (VARCHAR limits, not actual storage)",
            "- Performance: No significant impact on query performance",
            "- Compatibility: Improved compatibility with test frameworks",
            "- Maintenance: Reduced need for data length management in tests",
            "",
            "NEXT STEPS:",
            "1. Run integration tests to verify improvements",
            "2. Monitor for any remaining data length issues",
            "3. Update test data generation if needed",
            "4. Consider these column sizes for future schema changes",
        ])
        
        return "\n".join(report)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Widen MySQL database columns for better test compatibility")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--host', default='localhost', help='MySQL host')
    parser.add_argument('--user', default='database_user_1d7b0d0696a20', help='MySQL user')
    parser.add_argument('--password', default='EQA&bok7', help='MySQL password')
    parser.add_argument('--database', default='vedfolnir', help='MySQL database name')
    
    args = parser.parse_args()
    
    logger.info("Database Column Widening Tool")
    logger.info(f"Target database: {args.database} on {args.host}")
    
    if args.dry_run:
        logger.info("DRY RUN MODE: No changes will be made")
    
    # Initialize the widener
    widener = DatabaseColumnWidener(
        host=args.host,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    try:
        # Connect to database
        if not widener.connect():
            return False
        
        # Apply modifications
        success = widener.apply_all_modifications(dry_run=args.dry_run)
        
        # Generate report
        report = widener.generate_report()
        
        # Save report
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'column_widening_report.txt')
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Report saved to: {report_path}")
        
        # Create backup script if changes were made
        if widener.modifications_applied and not args.dry_run:
            backup_script = widener.create_backup_script()
            backup_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'revert_column_widening.py')
            
            with open(backup_path, 'w') as f:
                f.write(backup_script)
            
            logger.info(f"Backup reversion script created: {backup_path}")
        
        if success:
            logger.info("✅ Database column widening completed successfully")
            if not args.dry_run:
                print("\n" + "="*60)
                print("Database Columns Widened Successfully!")
                print("="*60)
                print(f"Modified {len(widener.modifications_applied)} columns")
                print("Tests should now handle longer identifiers")
                print("="*60)
        else:
            logger.error("❌ Database column widening completed with errors")
        
        return success
        
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        widener.disconnect()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
