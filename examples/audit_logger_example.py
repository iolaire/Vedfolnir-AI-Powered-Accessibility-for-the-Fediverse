# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Example usage of the AuditLogger class for comprehensive job audit logging.

This example demonstrates how to use the AuditLogger to track job-related actions,
administrative interventions, and system events with full context tracking.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audit_logger import AuditLogger
from app.core.database.core.database_manager import DatabaseManager
from config import Config


def demonstrate_audit_logging():
    """Demonstrate comprehensive audit logging functionality."""
    
    print("=== Audit Logger Example ===\n")
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config)
    audit_logger = AuditLogger(db_manager)
    
    # Example data
    task_id = "example-task-12345"
    user_id = 1
    admin_user_id = 2
    platform_connection_id = 1
    
    print("1. Logging job creation...")
    try:
        # Log job creation
        settings = {
            'max_posts': 10,
            'platform': 'pixelfed',
            'caption_style': 'descriptive'
        }
        
        audit_entry = audit_logger.log_job_creation(
            task_id=task_id,
            user_id=user_id,
            platform_connection_id=platform_connection_id,
            settings=settings,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (Example Browser)'
        )
        print(f"   ✓ Job creation logged: {audit_entry.id}")
    except Exception as e:
        print(f"   ✗ Error logging job creation: {e}")
    
    print("\n2. Logging job completion...")
    try:
        # Log successful job completion
        results = {
            'images_processed': 8,
            'captions_generated': 8,
            'errors': 0,
            'success_rate': 100.0
        }
        
        audit_entry = audit_logger.log_job_completion(
            task_id=task_id,
            user_id=user_id,
            success=True,
            results=results,
            processing_time_ms=45000,  # 45 seconds
            ip_address='192.168.1.100'
        )
        print(f"   ✓ Job completion logged: {audit_entry.id}")
    except Exception as e:
        print(f"   ✗ Error logging job completion: {e}")
    
    print("\n3. Logging admin intervention...")
    try:
        # Log admin intervention
        intervention_details = {
            'old_priority': 'normal',
            'new_priority': 'high',
            'reason': 'User requested priority increase'
        }
        
        audit_entry = audit_logger.log_admin_intervention(
            task_id=task_id,
            user_id=user_id,
            admin_user_id=admin_user_id,
            intervention_type='priority_change',
            details=intervention_details,
            ip_address='192.168.1.200',
            user_agent='Admin Dashboard v1.0'
        )
        print(f"   ✓ Admin intervention logged: {audit_entry.id}")
    except Exception as e:
        print(f"   ✗ Error logging admin intervention: {e}")
    
    print("\n4. Querying audit logs...")
    try:
        # Query audit logs for this task
        logs = audit_logger.query_audit_logs(
            task_id=task_id,
            limit=10
        )
        print(f"   ✓ Found {len(logs)} audit log entries for task {task_id}")
        
        for log in logs:
            print(f"      - {log.timestamp}: {log.action} by user {log.user_id}")
            if log.admin_user_id:
                print(f"        (Admin intervention by user {log.admin_user_id})")
    except Exception as e:
        print(f"   ✗ Error querying audit logs: {e}")
    
    print("\n5. Getting audit statistics...")
    try:
        # Get audit statistics for the last 30 days
        start_date = datetime.utcnow() - timedelta(days=30)
        stats = audit_logger.get_audit_statistics(
            start_date=start_date,
            user_id=user_id
        )
        
        print(f"   ✓ Audit statistics for user {user_id}:")
        print(f"      - Total entries: {stats['total_entries']}")
        print(f"      - Admin interventions: {stats['admin_interventions']}")
        print(f"      - Action counts: {stats['action_counts']}")
    except Exception as e:
        print(f"   ✗ Error getting audit statistics: {e}")
    
    print("\n6. Exporting audit logs...")
    try:
        # Export audit logs in JSON format
        export_data = audit_logger.export_audit_logs(
            format_type='json',
            task_id=task_id
        )
        
        print(f"   ✓ Exported audit logs ({len(export_data)} characters)")
        print(f"      First 200 characters: {export_data[:200]}...")
    except Exception as e:
        print(f"   ✗ Error exporting audit logs: {e}")
    
    print("\n7. Demonstrating cleanup (dry run)...")
    try:
        # Note: This would normally clean up old logs, but we'll use a very high retention
        # period to avoid actually deleting anything in this example
        deleted_count = audit_logger.cleanup_old_logs(
            retention_days=36500,  # 100 years - won't delete anything
            batch_size=100
        )
        print(f"   ✓ Cleanup completed: {deleted_count} entries would be deleted")
    except Exception as e:
        print(f"   ✗ Error during cleanup: {e}")
    
    print("\n=== Audit Logger Example Complete ===")


if __name__ == '__main__':
    demonstrate_audit_logging()