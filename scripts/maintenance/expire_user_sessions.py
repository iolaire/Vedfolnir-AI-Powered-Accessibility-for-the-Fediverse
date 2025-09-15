#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Quick Session Expiration Script

This script quickly expires all sessions for a user to force them to refresh
their browser and get updated platform context. Useful after platform changes.

Usage:
    python3 scripts/maintenance/expire_user_sessions.py --user-id 2
    python3 scripts/maintenance/expire_user_sessions.py --username admin
"""

import os
import sys
import argparse
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from scripts.maintenance.delete_user_data import UserDataDeleter
from config import Config
from models import User

def main():
    parser = argparse.ArgumentParser(description='Expire all sessions for a user')
    parser.add_argument('--user-id', type=int, help='User ID to expire sessions for')
    parser.add_argument('--username', help='Username to expire sessions for')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO', help='Set logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Validate arguments
    if not args.user_id and not args.username:
        print("❌ Error: Must specify either --user-id or --username")
        sys.exit(1)
    
    if args.user_id and args.username:
        print("❌ Error: Cannot specify both --user-id and --username")
        sys.exit(1)
    
    try:
        config = Config()
        deleter = UserDataDeleter(config)
        
        # Get user ID if username was provided
        user_id = args.user_id
        if args.username:
            with deleter.db_manager.get_session() as session:
                user = session.query(User).filter_by(username=args.username).first()
                if not user:
                    print(f"❌ Error: User '{args.username}' not found")
                    sys.exit(1)
                user_id = user.id
                print(f"Found user: {user.username} (ID: {user.id})")
        
        # Expire sessions
        print(f"🔄 Expiring all sessions for user ID {user_id}...")
        session_results = deleter.expire_user_sessions_only(user_id)
        
        total_expired = session_results['redis_sessions'] + session_results['database_sessions']
        print(f"✅ Expired/deleted {total_expired} total sessions:")
        print(f"   - Redis sessions: {session_results['redis_sessions']}")
        print(f"   - Database sessions: {session_results['database_sessions']}")
        print()
        print("💡 User will need to refresh their browser to see updated platform context")
        print("   This will force them to get fresh platform data from the database")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()