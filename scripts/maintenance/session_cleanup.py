#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Cleanup and Maintenance Utility

Provides automated cleanup of expired sessions with configurable intervals,
comprehensive logging, and health monitoring capabilities.
"""

import os
import sys
import argparse
import time
import signal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from logging import getLogger, basicConfig, INFO, DEBUG

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from database import DatabaseManager
from session_manager import SessionManager
from session_monitoring import get_session_monitor
from models import UserSession

logger = getLogger(__name__)

class SessionCleanupService:
    """Automated session cleanup service with configurable intervals"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.session_manager = SessionManager(self.db_manager)
        self.monitor = get_session_monitor(self.db_manager)
        self.running = False
        self.cleanup_interval = int(os.getenv('SESSION_CLEANUP_INTERVAL', '3600'))  # 1 hour default
        self.batch_size = int(os.getenv('SESSION_CLEANUP_BATCH_SIZE', '100'))
        self.max_session_age = int(os.getenv('SESSION_MAX_AGE', '172800'))  # 48 hours default
        
    def start_daemon(self):
        """Start the cleanup daemon"""
        logger.info(f"Starting session cleanup daemon (interval: {self.cleanup_interval}s)")
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            while self.running:
                self.run_cleanup_cycle()
                time.sleep(self.cleanup_interval)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.stop()
    
    def run_cleanup_cycle(self) -> Dict[str, Any]:
        """Run a single cleanup cycle"""
        start_time = time.time()
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'expired_sessions_cleaned': 0,
            'orphaned_sessions_cleaned': 0,
            'database_optimizations': 0,
            'errors': [],
            'duration_seconds': 0
        }
        
        try:
            logger.info("Starting session cleanup cycle")
            
            # Clean up expired sessions
            expired_count = self.session_manager.cleanup_expired_sessions()
            results['expired_sessions_cleaned'] = expired_count
            
            # Clean up orphaned sessions (sessions without valid users)
            orphaned_count = self._cleanup_orphaned_sessions()
            results['orphaned_sessions_cleaned'] = orphaned_count
            
            # Optimize database if needed
            if expired_count > 0 or orphaned_count > 0:
                optimization_count = self._optimize_session_tables()
                results['database_optimizations'] = optimization_count
            
            # Log cleanup results
            total_cleaned = expired_count + orphaned_count
            if total_cleaned > 0:
                logger.info(f"Cleanup cycle completed: {total_cleaned} sessions cleaned")
                self.monitor.record_metric('cleanup_sessions_removed', 'system', 0, total_cleaned)
            else:
                logger.debug("Cleanup cycle completed: no sessions to clean")
            
        except Exception as e:
            error_msg = f"Error in cleanup cycle: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            self.monitor.log_session_error('system', 0, 'cleanup_error', str(e))
        
        results['duration_seconds'] = time.time() - start_time
        return results
    
    def _cleanup_orphaned_sessions(self) -> int:
        """Clean up sessions that reference non-existent users"""
        try:
            with self.session_manager.get_db_session() as db_session:
                # Find sessions with invalid user references
                from sqlalchemy import text
                orphaned_sessions = db_session.execute(text("""
                    SELECT us.id, us.session_id 
                    FROM user_sessions us 
                    LEFT JOIN users u ON us.user_id = u.id 
                    WHERE u.id IS NULL OR u.is_active = 0
                """)).fetchall()
                
                count = 0
                for session_row in orphaned_sessions:
                    session_obj = db_session.query(UserSession).get(session_row[0])
                    if session_obj:
                        db_session.delete(session_obj)
                        count += 1
                
                if count > 0:
                    logger.info(f"Cleaned up {count} orphaned sessions")
                
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning orphaned sessions: {e}")
            return 0
    
    def _optimize_session_tables(self) -> int:
        """Optimize session-related database tables"""
        try:
            with self.session_manager.get_db_session() as db_session:
                # SQLite-specific optimizations
                from sqlalchemy import text
                
                optimizations = 0
                
                # Analyze tables for better query planning
                db_session.execute(text("ANALYZE user_sessions"))
                optimizations += 1
                
                # Vacuum if significant cleanup occurred
                db_session.execute(text("PRAGMA incremental_vacuum"))
                optimizations += 1
                
                logger.debug(f"Performed {optimizations} database optimizations")
                return optimizations
                
        except Exception as e:
            logger.error(f"Error optimizing session tables: {e}")
            return 0
    
    def get_cleanup_statistics(self) -> Dict[str, Any]:
        """Get cleanup service statistics"""
        try:
            with self.session_manager.get_db_session() as db_session:
                total_sessions = db_session.query(UserSession).count()
                
                # Count sessions by age
                now = datetime.now(timezone.utc)
                cutoff_24h = now - timedelta(hours=24)
                cutoff_48h = now - timedelta(hours=48)
                cutoff_week = now - timedelta(days=7)
                
                recent_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at >= cutoff_24h
                ).count()
                
                old_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at < cutoff_48h
                ).count()
                
                very_old_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at < cutoff_week
                ).count()
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_sessions': total_sessions,
                'recent_sessions_24h': recent_sessions,
                'old_sessions_48h': old_sessions,
                'very_old_sessions_week': very_old_sessions,
                'cleanup_interval': self.cleanup_interval,
                'batch_size': self.batch_size,
                'max_session_age': self.max_session_age,
                'service_running': self.running
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup statistics: {e}")
            return {'error': str(e)}
    
    def force_cleanup(self, max_age_hours: Optional[int] = None) -> Dict[str, Any]:
        """Force immediate cleanup with optional custom age limit"""
        logger.info("Starting forced session cleanup")
        
        if max_age_hours:
            # Temporarily override session timeout
            original_timeout = self.session_manager.session_timeout
            self.session_manager.session_timeout = timedelta(hours=max_age_hours)
            
            try:
                results = self.run_cleanup_cycle()
                results['forced_cleanup'] = True
                results['custom_max_age_hours'] = max_age_hours
                return results
            finally:
                # Restore original timeout
                self.session_manager.session_timeout = original_timeout
        else:
            results = self.run_cleanup_cycle()
            results['forced_cleanup'] = True
            return results
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def stop(self):
        """Stop the cleanup service"""
        self.running = False
        logger.info("Session cleanup service stopped")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Session Cleanup and Maintenance Utility')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--once', action='store_true', help='Run cleanup once and exit')
    parser.add_argument('--force', action='store_true', help='Force cleanup regardless of age')
    parser.add_argument('--max-age', type=int, help='Maximum session age in hours')
    parser.add_argument('--stats', action='store_true', help='Show cleanup statistics')
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
        service = SessionCleanupService(config)
        
        if args.stats:
            # Show statistics
            stats = service.get_cleanup_statistics()
            print("Session Cleanup Statistics:")
            print("=" * 40)
            for key, value in stats.items():
                print(f"{key}: {value}")
            
        elif args.daemon:
            # Run as daemon
            service.start_daemon()
            
        elif args.once or args.force:
            # Run once
            if args.force:
                results = service.force_cleanup(args.max_age)
            else:
                results = service.run_cleanup_cycle()
            
            print("Cleanup Results:")
            print("=" * 20)
            for key, value in results.items():
                print(f"{key}: {value}")
        
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