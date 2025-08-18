#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Security Monitor CLI

Command-line utility for monitoring and managing session security.
"""

import sys
import os
import argparse
import json
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from database import DatabaseManager
from unified_session_manager import UnifiedSessionManager as SessionManager
from security.features.session_security import SessionSecurityHardening


def setup_database():
    """Set up database connection"""
    try:
        config = Config()
        db_manager = DatabaseManager(config)
        session_manager = UnifiedSessionManager(db_manager)
        return session_manager
    except Exception as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)


def get_security_status(session_manager):
    """Get overall security status"""
    try:
        security = SessionSecurityHardening(session_manager)
        
        # Get active sessions
        with session_manager.get_db_session() as db_session:
            from models import UserSession
            active_sessions = db_session.query(UserSession).all()
        
        print("=== Session Security Status ===")
        print(f"Total active sessions: {len(active_sessions)}")
        print(f"Fingerprint cache size: {len(security.fingerprint_cache)}")
        print(f"Activity logs tracked: {len(security.activity_log)}")
        
        # Check for suspicious sessions
        suspicious_count = 0
        for session_id in security.activity_log:
            activities = security.activity_log[session_id]
            suspicious_activities = [
                a for a in activities
                if a.get('details', {}).get('suspicious', False)
            ]
            if suspicious_activities:
                suspicious_count += 1
        
        print(f"Sessions with suspicious activity: {suspicious_count}")
        
        if suspicious_count > 0:
            print("\n⚠️  WARNING: Suspicious activity detected!")
        else:
            print("\n✅ No suspicious activity detected")
        
        return True
        
    except Exception as e:
        print(f"Error getting security status: {e}")
        return False


def list_session_metrics(session_manager, session_id=None):
    """List session security metrics"""
    try:
        security = SessionSecurityHardening(session_manager)
        
        if session_id:
            # Show metrics for specific session
            metrics = security.get_session_security_metrics(session_id)
            print(f"=== Security Metrics for Session {session_id} ===")
            print(json.dumps(metrics, indent=2, default=str))
        else:
            # Show metrics for all sessions
            print("=== All Session Security Metrics ===")
            for sid in security.activity_log:
                metrics = security.get_session_security_metrics(sid)
                print(f"\nSession {sid}:")
                print(f"  Activity count (24h): {metrics.get('activity_count_24h', 0)}")
                print(f"  Suspicious events: {metrics.get('suspicious_events', 0)}")
                print(f"  Has fingerprint: {metrics.get('has_fingerprint', False)}")
                
                if metrics.get('last_activity'):
                    print(f"  Last activity: {metrics['last_activity']}")
        
        return True
        
    except Exception as e:
        print(f"Error listing session metrics: {e}")
        return False


def cleanup_expired_data(session_manager, max_age_hours=24):
    """Clean up expired security data"""
    try:
        security = SessionSecurityHardening(session_manager)
        
        print(f"Cleaning up security data older than {max_age_hours} hours...")
        stats = security.cleanup_expired_data(max_age_hours)
        
        print("=== Cleanup Results ===")
        print(f"Expired fingerprints removed: {stats.get('expired_fingerprints', 0)}")
        print(f"Expired activity logs removed: {stats.get('expired_activity_logs', 0)}")
        print(f"Remaining fingerprints: {stats.get('remaining_fingerprints', 0)}")
        print(f"Remaining activity logs: {stats.get('remaining_activity_logs', 0)}")
        
        return True
        
    except Exception as e:
        print(f"Error cleaning up expired data: {e}")
        return False


def validate_session_security(session_manager, session_id, user_id):
    """Validate security for a specific session"""
    try:
        security = SessionSecurityHardening(session_manager)
        
        print(f"Validating security for session {session_id} (user {user_id})...")
        
        is_valid, issues = security.validate_session_security(session_id, int(user_id))
        
        print("=== Security Validation Results ===")
        print(f"Session valid: {is_valid}")
        
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("No security issues found")
        
        return is_valid
        
    except Exception as e:
        print(f"Error validating session security: {e}")
        return False


def invalidate_suspicious_sessions(session_manager, user_id, reason):
    """Invalidate all sessions for a user due to suspicious activity"""
    try:
        security = SessionSecurityHardening(session_manager)
        
        print(f"Invalidating suspicious sessions for user {user_id}...")
        print(f"Reason: {reason}")
        
        count = security.invalidate_suspicious_sessions(int(user_id), reason)
        
        print(f"Invalidated {count} sessions")
        
        return count > 0
        
    except Exception as e:
        print(f"Error invalidating suspicious sessions: {e}")
        return False


def show_suspicious_activity(session_manager):
    """Show sessions with suspicious activity"""
    try:
        security = SessionSecurityHardening(session_manager)
        
        print("=== Sessions with Suspicious Activity ===")
        
        found_suspicious = False
        for session_id, activities in security.activity_log.items():
            suspicious_activities = [
                a for a in activities
                if a.get('details', {}).get('suspicious', False)
            ]
            
            if suspicious_activities:
                found_suspicious = True
                print(f"\nSession {session_id}:")
                print(f"  Total activities: {len(activities)}")
                print(f"  Suspicious activities: {len(suspicious_activities)}")
                
                for activity in suspicious_activities[-3:]:  # Show last 3
                    print(f"    - {activity['timestamp']}: {activity.get('details', {}).get('type', 'unknown')}")
        
        if not found_suspicious:
            print("No suspicious activity found")
        
        return True
        
    except Exception as e:
        print(f"Error showing suspicious activity: {e}")
        return False


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Session Security Monitor')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show overall security status')
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Show session security metrics')
    metrics_parser.add_argument('--session-id', help='Show metrics for specific session')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up expired security data')
    cleanup_parser.add_argument('--max-age-hours', type=int, default=24, 
                               help='Maximum age in hours for data to keep (default: 24)')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate session security')
    validate_parser.add_argument('session_id', help='Session ID to validate')
    validate_parser.add_argument('user_id', help='User ID for the session')
    
    # Invalidate command
    invalidate_parser = subparsers.add_parser('invalidate', help='Invalidate suspicious sessions')
    invalidate_parser.add_argument('user_id', help='User ID to invalidate sessions for')
    invalidate_parser.add_argument('reason', help='Reason for invalidation')
    
    # Suspicious command
    subparsers.add_parser('suspicious', help='Show sessions with suspicious activity')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Set up database
    session_manager = setup_database()
    
    # Execute command
    success = False
    
    if args.command == 'status':
        success = get_security_status(session_manager)
    
    elif args.command == 'metrics':
        success = list_session_metrics(session_manager, args.session_id)
    
    elif args.command == 'cleanup':
        success = cleanup_expired_data(session_manager, args.max_age_hours)
    
    elif args.command == 'validate':
        success = validate_session_security(session_manager, args.session_id, args.user_id)
    
    elif args.command == 'invalidate':
        success = invalidate_suspicious_sessions(session_manager, args.user_id, args.reason)
    
    elif args.command == 'suspicious':
        success = show_suspicious_activity(session_manager)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()