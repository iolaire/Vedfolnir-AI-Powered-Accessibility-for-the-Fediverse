#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unified Session Maintenance CLI

Provides a unified interface for all session cleanup and maintenance utilities.
Combines automated cleanup, analytics, and database maintenance in one tool.
"""

import os
import sys
import argparse
import json
from datetime import datetime
from logging import getLogger, basicConfig, INFO, DEBUG

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from scripts.maintenance.session_cleanup import SessionCleanupService
from scripts.maintenance.session_analytics import SessionAnalytics
from scripts.maintenance.session_db_maintenance import SessionDatabaseMaintenance

logger = getLogger(__name__)

class UnifiedSessionMaintenance:
    """Unified session maintenance interface"""
    
    def __init__(self, config: Config):
        self.config = config
        self.cleanup_service = SessionCleanupService(config)
        self.analytics = SessionAnalytics(config)
        self.db_maintenance = SessionDatabaseMaintenance(config)
    
    def run_full_maintenance(self, dry_run: bool = False) -> dict:
        """Run complete maintenance cycle"""
        logger.info(f"Starting full maintenance cycle (dry_run={dry_run})")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'cleanup': {},
            'analytics': {},
            'database': {},
            'summary': {}
        }
        
        try:
            # 1. Run cleanup
            if not dry_run:
                cleanup_results = self.cleanup_service.run_cleanup_cycle()
            else:
                cleanup_results = self.cleanup_service.get_cleanup_statistics()
                cleanup_results['dry_run'] = True
            
            results['cleanup'] = cleanup_results
            
            # 2. Generate analytics
            analytics_results = self.analytics.generate_health_report()
            results['analytics'] = analytics_results
            
            # 3. Database maintenance
            if not dry_run:
                # Create indexes if needed
                index_results = self.db_maintenance.create_recommended_indexes(dry_run=False)
                
                # Optimize tables
                optimize_results = self.db_maintenance.optimize_session_tables()
                
                results['database'] = {
                    'indexes': index_results,
                    'optimization': optimize_results
                }
            else:
                # Just analyze
                analysis_results = self.db_maintenance.analyze_session_tables()
                results['database'] = {'analysis': analysis_results}
            
            # 4. Generate summary
            results['summary'] = self._generate_maintenance_summary(results)
            
            logger.info("Full maintenance cycle completed")
            return results
            
        except Exception as e:
            logger.error(f"Error in full maintenance cycle: {e}")
            results['error'] = str(e)
            return results
    
    def _generate_maintenance_summary(self, results: dict) -> dict:
        """Generate maintenance summary"""
        summary = {
            'status': 'completed',
            'actions_taken': [],
            'issues_found': [],
            'recommendations': []
        }
        
        try:
            # Cleanup summary
            cleanup = results.get('cleanup', {})
            if cleanup.get('expired_sessions_cleaned', 0) > 0:
                summary['actions_taken'].append(
                    f"Cleaned {cleanup['expired_sessions_cleaned']} expired sessions"
                )
            
            # Analytics summary
            analytics = results.get('analytics', {})
            health_status = analytics.get('health_status', {})
            
            if health_status.get('overall_health') != 'good':
                summary['issues_found'].append(
                    f"Health status: {health_status.get('overall_health', 'unknown')}"
                )
            
            # Add analytics recommendations
            analytics_recs = results.get('recommendations', [])
            summary['recommendations'].extend(analytics_recs)
            
            # Database summary
            database = results.get('database', {})
            if 'indexes' in database:
                indexes_created = len(database['indexes'].get('indexes_created', []))
                if indexes_created > 0:
                    summary['actions_taken'].append(f"Created {indexes_created} database indexes")
            
            if not summary['actions_taken'] and not summary['issues_found']:
                summary['actions_taken'].append("No maintenance actions required")
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            summary['error'] = str(e)
        
        return summary

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Unified Session Maintenance CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --full-maintenance          # Run complete maintenance
  %(prog)s --cleanup --once            # Run cleanup once
  %(prog)s --analytics --health        # Generate health report
  %(prog)s --database --analyze        # Analyze database
  %(prog)s --status                    # Show system status
        """
    )
    
    # Main operation modes
    parser.add_argument('--full-maintenance', action='store_true', 
                       help='Run complete maintenance cycle')
    parser.add_argument('--cleanup', action='store_true', 
                       help='Session cleanup operations')
    parser.add_argument('--analytics', action='store_true', 
                       help='Analytics and monitoring')
    parser.add_argument('--database', action='store_true', 
                       help='Database maintenance')
    parser.add_argument('--status', action='store_true', 
                       help='Show system status')
    
    # Cleanup options
    parser.add_argument('--once', action='store_true', 
                       help='Run cleanup once (with --cleanup)')
    parser.add_argument('--daemon', action='store_true', 
                       help='Run as daemon (with --cleanup)')
    parser.add_argument('--force', action='store_true', 
                       help='Force cleanup (with --cleanup)')
    parser.add_argument('--max-age', type=int, metavar='HOURS',
                       help='Maximum session age in hours (with --force)')
    
    # Analytics options
    parser.add_argument('--health', action='store_true', 
                       help='Generate health report (with --analytics)')
    parser.add_argument('--trends', type=int, metavar='DAYS', default=7,
                       help='Show trends for N days (with --analytics)')
    parser.add_argument('--export', metavar='FILE',
                       help='Export report to file (with --analytics)')
    
    # Database options
    parser.add_argument('--analyze', action='store_true', 
                       help='Analyze tables (with --database)')
    parser.add_argument('--create-indexes', action='store_true', 
                       help='Create indexes (with --database)')
    parser.add_argument('--optimize', action='store_true', 
                       help='Optimize tables (with --database)')
    parser.add_argument('--vacuum', action='store_true', 
                       help='Full vacuum (with --optimize)')
    parser.add_argument('--integrity-check', action='store_true', 
                       help='Check integrity (with --database)')
    
    # General options
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--json', action='store_true', 
                       help='Output in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = DEBUG if args.verbose else INFO
    basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        config = Config()
        maintenance = UnifiedSessionMaintenance(config)
        
        if args.full_maintenance:
            # Run complete maintenance cycle
            results = maintenance.run_full_maintenance(dry_run=args.dry_run)
            
            if args.json:
                print(json.dumps(results, indent=2, default=str))
            else:
                print("Session Maintenance Results")
                print("=" * 40)
                
                summary = results.get('summary', {})
                print(f"Status: {summary.get('status', 'unknown')}")
                
                actions = summary.get('actions_taken', [])
                if actions:
                    print("\nActions Taken:")
                    for action in actions:
                        print(f"  - {action}")
                
                issues = summary.get('issues_found', [])
                if issues:
                    print("\nIssues Found:")
                    for issue in issues:
                        print(f"  - {issue}")
                
                recommendations = summary.get('recommendations', [])
                if recommendations:
                    print("\nRecommendations:")
                    for rec in recommendations:
                        print(f"  - {rec}")
        
        elif args.cleanup:
            # Cleanup operations
            if args.daemon:
                maintenance.cleanup_service.start_daemon()
            elif args.once or args.force:
                if args.force:
                    results = maintenance.cleanup_service.force_cleanup(args.max_age)
                else:
                    results = maintenance.cleanup_service.run_cleanup_cycle()
                
                if args.json:
                    print(json.dumps(results, indent=2, default=str))
                else:
                    print("Cleanup Results:")
                    expired = results.get('expired_sessions_cleaned', 0)
                    orphaned = results.get('orphaned_sessions_cleaned', 0)
                    print(f"  Expired sessions: {expired}")
                    print(f"  Orphaned sessions: {orphaned}")
                    print(f"  Duration: {results.get('duration_seconds', 0):.2f}s")
            else:
                # Show cleanup statistics
                stats = maintenance.cleanup_service.get_cleanup_statistics()
                if args.json:
                    print(json.dumps(stats, indent=2, default=str))
                else:
                    print("Cleanup Statistics:")
                    print(f"  Total sessions: {stats.get('total_sessions', 0)}")
                    print(f"  Recent (24h): {stats.get('recent_sessions_24h', 0)}")
                    print(f"  Old (48h+): {stats.get('old_sessions_48h', 0)}")
        
        elif args.analytics:
            # Analytics operations
            if args.health:
                report = maintenance.analytics.generate_health_report()
                
                if args.export:
                    maintenance.analytics.export_analytics_report(args.export)
                    print(f"Health report exported to {args.export}")
                elif args.json:
                    print(json.dumps(report, indent=2, default=str))
                else:
                    print("Session Health Report")
                    print("=" * 30)
                    
                    health_status = report.get('health_status', {})
                    print(f"Overall Health: {health_status.get('overall_health', 'unknown')}")
                    
                    issues = health_status.get('issues', [])
                    if issues:
                        print("\nIssues:")
                        for issue in issues:
                            print(f"  - {issue}")
                    
                    recommendations = report.get('recommendations', [])
                    if recommendations:
                        print("\nRecommendations:")
                        for rec in recommendations:
                            print(f"  - {rec}")
            else:
                # Show trends
                trends = maintenance.analytics.get_session_trends(args.trends)
                
                if args.json:
                    print(json.dumps(trends, indent=2, default=str))
                else:
                    print(f"Session Trends ({args.trends} days)")
                    print("=" * 30)
                    
                    daily_trends = trends.get('daily_session_creation', {})
                    for date, count in daily_trends.items():
                        print(f"{date}: {count} sessions")
                    
                    print(f"\nTotal: {trends.get('total_sessions_created', 0)} sessions")
                    print(f"Average: {trends.get('average_daily_sessions', 0):.1f} sessions/day")
        
        elif args.database:
            # Database operations
            if args.analyze:
                analysis = maintenance.db_maintenance.analyze_session_tables()
                
                if args.json:
                    print(json.dumps(analysis, indent=2, default=str))
                else:
                    print("Database Analysis")
                    print("=" * 20)
                    
                    table_stats = analysis.get('tables', {}).get('user_sessions', {})
                    print(f"Row Count: {table_stats.get('row_count', 0)}")
                    print(f"Unique Users: {table_stats.get('unique_users', 0)}")
                    
                    recommendations = analysis.get('recommendations', [])
                    if recommendations:
                        print("\nRecommendations:")
                        for rec in recommendations:
                            print(f"  - {rec}")
            
            elif args.create_indexes:
                results = maintenance.db_maintenance.create_recommended_indexes(dry_run=args.dry_run)
                
                if args.json:
                    print(json.dumps(results, indent=2, default=str))
                else:
                    print("Index Creation Results")
                    created = results.get('indexes_created', [])
                    if created:
                        print("Created:")
                        for idx in created:
                            print(f"  - {idx}")
            
            elif args.optimize:
                results = maintenance.db_maintenance.optimize_session_tables(vacuum=args.vacuum)
                
                if args.json:
                    print(json.dumps(results, indent=2, default=str))
                else:
                    print("Optimization Results")
                    operations = results.get('operations_performed', [])
                    print(f"Duration: {results.get('duration_seconds', 0):.2f}s")
                    print("Operations:")
                    for op in operations:
                        print(f"  - {op}")
            
            elif args.integrity_check:
                results = maintenance.db_maintenance.check_database_integrity()
                
                if args.json:
                    print(json.dumps(results, indent=2, default=str))
                else:
                    print("Integrity Check Results")
                    print(f"Integrity: {results.get('integrity_check', 'unknown')}")
                    print(f"Foreign Keys: {results.get('foreign_key_check', 'unknown')}")
            
            else:
                # Show database statistics
                stats = maintenance.db_maintenance.get_database_statistics()
                
                if args.json:
                    print(json.dumps(stats, indent=2, default=str))
                else:
                    print("Database Statistics")
                    print("=" * 25)
                    print(f"Size: {stats.get('database_size_mb', 0)} MB")
                    
                    table_stats = stats.get('table_analysis', {})
                    print(f"Sessions: {table_stats.get('row_count', 0)}")
                    print(f"Users: {table_stats.get('unique_users', 0)}")
        
        elif args.status:
            # Show system status
            cleanup_stats = maintenance.cleanup_service.get_cleanup_statistics()
            health_report = maintenance.analytics.generate_health_report()
            db_stats = maintenance.db_maintenance.get_database_statistics()
            
            if args.json:
                status = {
                    'cleanup': cleanup_stats,
                    'health': health_report.get('health_status', {}),
                    'database': db_stats
                }
                print(json.dumps(status, indent=2, default=str))
            else:
                print("Session System Status")
                print("=" * 30)
                
                # Health status
                health_status = health_report.get('health_status', {})
                print(f"Overall Health: {health_status.get('overall_health', 'unknown')}")
                
                # Session counts
                print(f"Total Sessions: {cleanup_stats.get('total_sessions', 0)}")
                print(f"Recent (24h): {cleanup_stats.get('recent_sessions_24h', 0)}")
                
                # Database size
                print(f"Database Size: {db_stats.get('database_size_mb', 0)} MB")
                
                # Issues
                issues = health_status.get('issues', [])
                if issues:
                    print("\nIssues:")
                    for issue in issues:
                        print(f"  - {issue}")
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()