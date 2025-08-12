#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Database Maintenance Utility

Provides database maintenance scripts for session table optimization,
index management, and performance tuning.
"""

import os
import sys
import argparse
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from logging import getLogger, basicConfig, INFO, DEBUG

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from database import DatabaseManager
from session_manager import SessionManager

logger = getLogger(__name__)

class SessionDatabaseMaintenance:
    """Database maintenance utilities for session management"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.session_manager = SessionManager(self.db_manager)
    
    def analyze_session_tables(self) -> Dict[str, Any]:
        """Analyze session tables for optimization opportunities"""
        logger.info("Analyzing session tables")
        
        try:
            with self.session_manager.get_db_session() as db_session:
                from sqlalchemy import text
                
                analysis = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'tables': {},
                    'indexes': {},
                    'recommendations': []
                }
                
                # Analyze user_sessions table
                session_stats = self._analyze_table(db_session, 'user_sessions')
                analysis['tables']['user_sessions'] = session_stats
                
                # Check existing indexes
                indexes = self._get_table_indexes(db_session, 'user_sessions')
                analysis['indexes']['user_sessions'] = indexes
                
                # Generate recommendations
                analysis['recommendations'] = self._generate_maintenance_recommendations(
                    session_stats, indexes
                )
                
                return analysis
                
        except Exception as e:
            logger.error(f"Error analyzing session tables: {e}")
            return {'error': str(e)}
    
    def _analyze_table(self, db_session, table_name: str) -> Dict[str, Any]:
        """Analyze a specific table"""
        try:
            from sqlalchemy import text
            
            # Get table statistics
            stats_query = text(f"""
                SELECT 
                    COUNT(*) as row_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    MIN(created_at) as oldest_record,
                    MAX(updated_at) as newest_record
                FROM {table_name}
            """)
            
            result = db_session.execute(stats_query).fetchone()
            
            # Get table size information (SQLite specific)
            size_query = text(f"SELECT COUNT(*) * 1024 as estimated_size FROM {table_name}")
            size_result = db_session.execute(size_query).fetchone()
            
            return {
                'row_count': result[0] if result else 0,
                'unique_users': result[1] if result else 0,
                'oldest_record': result[2].isoformat() if result and result[2] else None,
                'newest_record': result[3].isoformat() if result and result[3] else None,
                'estimated_size_bytes': size_result[0] if size_result else 0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing table {table_name}: {e}")
            return {'error': str(e)}
    
    def _get_table_indexes(self, db_session, table_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a table"""
        try:
            from sqlalchemy import text
            
            # SQLite specific query for indexes
            index_query = text(f"""
                SELECT name, sql, unique_flag
                FROM sqlite_master 
                WHERE type='index' AND tbl_name='{table_name}'
                AND name NOT LIKE 'sqlite_%'
            """)
            
            results = db_session.execute(index_query).fetchall()
            
            indexes = []
            for result in results:
                indexes.append({
                    'name': result[0],
                    'sql': result[1],
                    'unique': bool(result[2]) if result[2] is not None else False
                })
            
            return indexes
            
        except Exception as e:
            logger.error(f"Error getting indexes for {table_name}: {e}")
            return []
    
    def _generate_maintenance_recommendations(self, table_stats: Dict[str, Any], 
                                           indexes: List[Dict[str, Any]]) -> List[str]:
        """Generate maintenance recommendations"""
        recommendations = []
        
        try:
            # Check if we have basic required indexes
            index_names = [idx['name'] for idx in indexes]
            
            required_indexes = [
                'ix_user_sessions_session_id',
                'ix_user_sessions_user_id', 
                'ix_user_sessions_updated_at'
            ]
            
            for required_idx in required_indexes:
                if required_idx not in index_names:
                    recommendations.append(f"Missing recommended index: {required_idx}")
            
            # Check table size
            row_count = table_stats.get('row_count', 0)
            if row_count > 10000:
                recommendations.append("Consider implementing session cleanup policies - large table detected")
            
            # Check data age
            if table_stats.get('oldest_record'):
                from datetime import datetime
                oldest = datetime.fromisoformat(table_stats['oldest_record'].replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - oldest).days
                
                if age_days > 30:
                    recommendations.append(f"Old data detected ({age_days} days) - consider archiving")
            
            if not recommendations:
                recommendations.append("Database maintenance is up to date")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to analysis error")
        
        return recommendations
    
    def create_recommended_indexes(self, dry_run: bool = True) -> Dict[str, Any]:
        """Create recommended indexes for session tables"""
        logger.info(f"Creating recommended indexes (dry_run={dry_run})")
        
        try:
            with self.session_manager.get_db_session() as db_session:
                from sqlalchemy import text
                
                results = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'dry_run': dry_run,
                    'indexes_created': [],
                    'indexes_skipped': [],
                    'errors': []
                }
                
                # Define recommended indexes
                recommended_indexes = [
                    {
                        'name': 'ix_user_sessions_session_id',
                        'sql': 'CREATE INDEX IF NOT EXISTS ix_user_sessions_session_id ON user_sessions(session_id)'
                    },
                    {
                        'name': 'ix_user_sessions_user_id',
                        'sql': 'CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id)'
                    },
                    {
                        'name': 'ix_user_sessions_updated_at',
                        'sql': 'CREATE INDEX IF NOT EXISTS ix_user_sessions_updated_at ON user_sessions(updated_at)'
                    },
                    {
                        'name': 'ix_user_sessions_user_platform',
                        'sql': 'CREATE INDEX IF NOT EXISTS ix_user_sessions_user_platform ON user_sessions(user_id, active_platform_id)'
                    }
                ]
                
                # Check existing indexes
                existing_indexes = self._get_table_indexes(db_session, 'user_sessions')
                existing_names = [idx['name'] for idx in existing_indexes]
                
                for index_def in recommended_indexes:
                    index_name = index_def['name']
                    
                    if index_name in existing_names:
                        results['indexes_skipped'].append(f"{index_name} (already exists)")
                        continue
                    
                    try:
                        if not dry_run:
                            db_session.execute(text(index_def['sql']))
                            results['indexes_created'].append(index_name)
                            logger.info(f"Created index: {index_name}")
                        else:
                            results['indexes_created'].append(f"{index_name} (would create)")
                            logger.info(f"Would create index: {index_name}")
                    
                    except Exception as e:
                        error_msg = f"Error creating index {index_name}: {e}"
                        results['errors'].append(error_msg)
                        logger.error(error_msg)
                
                return results
                
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return {'error': str(e)}
    
    def optimize_session_tables(self, vacuum: bool = False) -> Dict[str, Any]:
        """Optimize session tables"""
        logger.info(f"Optimizing session tables (vacuum={vacuum})")
        
        try:
            start_time = time.time()
            
            with self.session_manager.get_db_session() as db_session:
                from sqlalchemy import text
                
                results = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'operations_performed': [],
                    'duration_seconds': 0,
                    'errors': []
                }
                
                try:
                    # Analyze tables for better query planning
                    db_session.execute(text("ANALYZE user_sessions"))
                    results['operations_performed'].append("ANALYZE user_sessions")
                    logger.info("Analyzed user_sessions table")
                    
                    # Update table statistics
                    db_session.execute(text("PRAGMA optimize"))
                    results['operations_performed'].append("PRAGMA optimize")
                    logger.info("Updated database statistics")
                    
                    if vacuum:
                        # Perform vacuum to reclaim space
                        db_session.execute(text("VACUUM"))
                        results['operations_performed'].append("VACUUM")
                        logger.info("Performed database vacuum")
                    else:
                        # Incremental vacuum for less impact
                        db_session.execute(text("PRAGMA incremental_vacuum"))
                        results['operations_performed'].append("PRAGMA incremental_vacuum")
                        logger.info("Performed incremental vacuum")
                
                except Exception as e:
                    error_msg = f"Error during optimization: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                
                results['duration_seconds'] = time.time() - start_time
                return results
                
        except Exception as e:
            logger.error(f"Error optimizing tables: {e}")
            return {'error': str(e)}
    
    def check_database_integrity(self) -> Dict[str, Any]:
        """Check database integrity"""
        logger.info("Checking database integrity")
        
        try:
            with self.session_manager.get_db_session() as db_session:
                from sqlalchemy import text
                
                results = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'integrity_check': 'unknown',
                    'foreign_key_check': 'unknown',
                    'issues_found': [],
                    'recommendations': []
                }
                
                # SQLite integrity check
                integrity_result = db_session.execute(text("PRAGMA integrity_check")).fetchone()
                if integrity_result and integrity_result[0] == 'ok':
                    results['integrity_check'] = 'passed'
                else:
                    results['integrity_check'] = 'failed'
                    results['issues_found'].append(f"Integrity check failed: {integrity_result[0] if integrity_result else 'unknown error'}")
                
                # Foreign key check
                fk_result = db_session.execute(text("PRAGMA foreign_key_check")).fetchall()
                if not fk_result:
                    results['foreign_key_check'] = 'passed'
                else:
                    results['foreign_key_check'] = 'failed'
                    for fk_error in fk_result:
                        results['issues_found'].append(f"Foreign key violation: {fk_error}")
                
                # Generate recommendations
                if results['integrity_check'] == 'failed':
                    results['recommendations'].append("Database corruption detected - consider backup and restore")
                
                if results['foreign_key_check'] == 'failed':
                    results['recommendations'].append("Foreign key violations found - review data consistency")
                
                if not results['issues_found']:
                    results['recommendations'].append("Database integrity is good")
                
                return results
                
        except Exception as e:
            logger.error(f"Error checking database integrity: {e}")
            return {'error': str(e)}
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            with self.session_manager.get_db_session() as db_session:
                from sqlalchemy import text
                
                # Get database file size
                db_size_result = db_session.execute(text("PRAGMA page_count")).fetchone()
                page_size_result = db_session.execute(text("PRAGMA page_size")).fetchone()
                
                db_size_bytes = (db_size_result[0] * page_size_result[0]) if db_size_result and page_size_result else 0
                
                # Get connection pool statistics
                pool_stats = self.session_manager.get_connection_pool_status()
                
                return {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'database_size_bytes': db_size_bytes,
                    'database_size_mb': round(db_size_bytes / (1024 * 1024), 2),
                    'connection_pool': pool_stats,
                    'table_analysis': self._analyze_table(db_session, 'user_sessions')
                }
                
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {'error': str(e)}

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Session Database Maintenance Utility')
    parser.add_argument('--analyze', action='store_true', help='Analyze session tables')
    parser.add_argument('--create-indexes', action='store_true', help='Create recommended indexes')
    parser.add_argument('--optimize', action='store_true', help='Optimize session tables')
    parser.add_argument('--vacuum', action='store_true', help='Perform full vacuum (use with --optimize)')
    parser.add_argument('--integrity-check', action='store_true', help='Check database integrity')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = DEBUG if args.verbose else INFO
    basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        config = Config()
        maintenance = SessionDatabaseMaintenance(config)
        
        if args.analyze:
            analysis = maintenance.analyze_session_tables()
            print("Session Table Analysis")
            print("=" * 40)
            
            if 'error' in analysis:
                print(f"Error: {analysis['error']}")
            else:
                # Table statistics
                table_stats = analysis.get('tables', {}).get('user_sessions', {})
                print(f"Row Count: {table_stats.get('row_count', 0)}")
                print(f"Unique Users: {table_stats.get('unique_users', 0)}")
                print(f"Size: {table_stats.get('estimated_size_bytes', 0)} bytes")
                
                # Indexes
                indexes = analysis.get('indexes', {}).get('user_sessions', [])
                print(f"\nIndexes ({len(indexes)}):")
                for idx in indexes:
                    print(f"  - {idx['name']}")
                
                # Recommendations
                recommendations = analysis.get('recommendations', [])
                print(f"\nRecommendations:")
                for rec in recommendations:
                    print(f"  - {rec}")
        
        elif args.create_indexes:
            results = maintenance.create_recommended_indexes(dry_run=args.dry_run)
            print("Index Creation Results")
            print("=" * 30)
            
            if 'error' in results:
                print(f"Error: {results['error']}")
            else:
                created = results.get('indexes_created', [])
                skipped = results.get('indexes_skipped', [])
                errors = results.get('errors', [])
                
                if created:
                    print("Created/Would Create:")
                    for idx in created:
                        print(f"  - {idx}")
                
                if skipped:
                    print("Skipped:")
                    for idx in skipped:
                        print(f"  - {idx}")
                
                if errors:
                    print("Errors:")
                    for error in errors:
                        print(f"  - {error}")
        
        elif args.optimize:
            results = maintenance.optimize_session_tables(vacuum=args.vacuum)
            print("Optimization Results")
            print("=" * 25)
            
            if 'error' in results:
                print(f"Error: {results['error']}")
            else:
                operations = results.get('operations_performed', [])
                duration = results.get('duration_seconds', 0)
                errors = results.get('errors', [])
                
                print(f"Duration: {duration:.2f} seconds")
                print("Operations:")
                for op in operations:
                    print(f"  - {op}")
                
                if errors:
                    print("Errors:")
                    for error in errors:
                        print(f"  - {error}")
        
        elif args.integrity_check:
            results = maintenance.check_database_integrity()
            print("Database Integrity Check")
            print("=" * 30)
            
            if 'error' in results:
                print(f"Error: {results['error']}")
            else:
                print(f"Integrity Check: {results.get('integrity_check', 'unknown')}")
                print(f"Foreign Key Check: {results.get('foreign_key_check', 'unknown')}")
                
                issues = results.get('issues_found', [])
                if issues:
                    print("Issues Found:")
                    for issue in issues:
                        print(f"  - {issue}")
                
                recommendations = results.get('recommendations', [])
                print("Recommendations:")
                for rec in recommendations:
                    print(f"  - {rec}")
        
        elif args.stats:
            stats = maintenance.get_database_statistics()
            print("Database Statistics")
            print("=" * 25)
            
            if 'error' in stats:
                print(f"Error: {stats['error']}")
            else:
                print(f"Database Size: {stats.get('database_size_mb', 0)} MB")
                
                table_stats = stats.get('table_analysis', {})
                print(f"Session Records: {table_stats.get('row_count', 0)}")
                print(f"Unique Users: {table_stats.get('unique_users', 0)}")
                
                pool_stats = stats.get('connection_pool', {})
                if 'error' not in pool_stats:
                    print(f"Pool Size: {pool_stats.get('pool_size', 0)}")
                    print(f"Available Connections: {pool_stats.get('available_connections', 0)}")
        
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()