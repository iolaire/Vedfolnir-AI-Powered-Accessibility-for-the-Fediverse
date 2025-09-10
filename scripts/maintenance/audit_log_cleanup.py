# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Audit log cleanup script for maintaining audit log retention policies.

This script provides automated cleanup of old audit log entries based on
configurable retention periods and compliance requirements.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from audit_logger import AuditLogger
from app.core.database.core.database_manager import DatabaseManager
from config import Config


def main():
    """Main function for audit log cleanup."""
    
    parser = argparse.ArgumentParser(
        description='Clean up old audit log entries based on retention policy'
    )
    parser.add_argument(
        '--retention-days',
        type=int,
        default=365,
        help='Number of days to retain audit logs (default: 365)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of records to delete in each batch (default: 1000)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show audit log statistics before cleanup'
    )
    parser.add_argument(
        '--export-before-cleanup',
        type=str,
        help='Export logs to file before cleanup (specify filename)'
    )
    
    args = parser.parse_args()
    
    print("=== Audit Log Cleanup Script ===\n")
    
    # Initialize components
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        audit_logger = AuditLogger(db_manager)
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Failed to initialize database connection: {e}")
        return 1
    
    # Show statistics if requested
    if args.stats:
        print("\n--- Current Audit Log Statistics ---")
        try:
            stats = audit_logger.get_audit_statistics()
            print(f"Total audit log entries: {stats['total_entries']}")
            print(f"Admin interventions: {stats['admin_interventions']}")
            print(f"Action breakdown: {stats['action_counts']}")
            print(f"Top users by activity: {dict(list(stats['user_activity'].items())[:5])}")
        except Exception as e:
            print(f"✗ Failed to get statistics: {e}")
    
    # Calculate cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=args.retention_days)
    print(f"\nRetention policy: {args.retention_days} days")
    print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Count logs that would be affected
    try:
        old_logs = audit_logger.query_audit_logs(
            end_date=cutoff_date,
            limit=10000  # Get a sample to estimate
        )
        
        if not old_logs:
            print("✓ No audit logs found older than retention period")
            return 0
        
        print(f"Found {len(old_logs)} audit log entries to process")
        
        if len(old_logs) == 10000:
            print("  (Note: This is a sample - actual count may be higher)")
        
    except Exception as e:
        print(f"✗ Failed to query old logs: {e}")
        return 1
    
    # Export logs before cleanup if requested
    if args.export_before_cleanup:
        print(f"\n--- Exporting logs to {args.export_before_cleanup} ---")
        try:
            export_data = audit_logger.export_audit_logs(
                format_type='json',
                end_date=cutoff_date
            )
            
            with open(args.export_before_cleanup, 'w') as f:
                f.write(export_data)
            
            print(f"✓ Exported {len(export_data)} characters to {args.export_before_cleanup}")
        except Exception as e:
            print(f"✗ Failed to export logs: {e}")
            return 1
    
    # Perform cleanup
    if args.dry_run:
        print(f"\n--- Dry Run Mode ---")
        print(f"Would delete audit logs older than {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Batch size: {args.batch_size}")
        print("No actual deletion performed.")
    else:
        print(f"\n--- Performing Cleanup ---")
        try:
            deleted_count = audit_logger.cleanup_old_logs(
                retention_days=args.retention_days,
                batch_size=args.batch_size
            )
            
            print(f"✓ Cleanup completed successfully")
            print(f"  Deleted {deleted_count} audit log entries")
            
            if deleted_count > 0:
                # Show updated statistics
                print("\n--- Updated Statistics ---")
                stats = audit_logger.get_audit_statistics()
                print(f"Remaining audit log entries: {stats['total_entries']}")
            
        except Exception as e:
            print(f"✗ Cleanup failed: {e}")
            return 1
    
    print("\n=== Cleanup Complete ===")
    return 0


if __name__ == '__main__':
    sys.exit(main())