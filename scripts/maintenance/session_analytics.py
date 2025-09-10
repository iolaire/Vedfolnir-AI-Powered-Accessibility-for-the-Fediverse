#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Analytics and Health Monitoring Utility

Provides comprehensive analytics, health monitoring, and diagnostic
capabilities for the session management system.
"""

import os
import sys
import argparse
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from logging import getLogger, basicConfig, INFO, DEBUG

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from unified_session_manager import UnifiedSessionManager as SessionManager
from session_monitoring import get_session_monitor
from models import UserSession, User, PlatformConnection

logger = getLogger(__name__)

class SessionAnalytics:
    """Session analytics and health monitoring service"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        self.monitor = get_session_monitor(self.db_manager)
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive session health report"""
        logger.info("Generating session health report")
        
        try:
            # Get basic monitoring report
            health_report = self.monitor.get_session_health_report()
            
            # Add detailed analytics
            health_report['detailed_analytics'] = self._get_detailed_analytics()
            health_report['performance_metrics'] = self._get_performance_metrics()
            health_report['security_analysis'] = self._get_security_analysis()
            health_report['recommendations'] = self._generate_recommendations(health_report)
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return {'error': str(e)}
    
    def _get_detailed_analytics(self) -> Dict[str, Any]:
        """Get detailed session analytics"""
        try:
            with self.session_manager.get_db_session() as db_session:
                now = datetime.now(timezone.utc)
                
                # Session age distribution
                age_buckets = {
                    'last_hour': now - timedelta(hours=1),
                    'last_24h': now - timedelta(hours=24),
                    'last_week': now - timedelta(days=7),
                    'last_month': now - timedelta(days=30)
                }
                
                age_distribution = {}
                for bucket_name, cutoff_time in age_buckets.items():
                    count = db_session.query(UserSession).filter(
                        UserSession.updated_at >= cutoff_time
                    ).count()
                    age_distribution[bucket_name] = count
                
                # Platform distribution
                platform_stats = db_session.query(
                    PlatformConnection.platform_type,
                    db_session.query(UserSession).filter(
                        UserSession.active_platform_id == PlatformConnection.id
                    ).count().label('session_count')
                ).join(UserSession, UserSession.active_platform_id == PlatformConnection.id).all()
                
                platform_distribution = {stat[0]: stat[1] for stat in platform_stats}
                
                # User activity patterns
                user_activity = db_session.query(
                    UserSession.user_id,
                    db_session.query(UserSession).filter(
                        UserSession.user_id == UserSession.user_id
                    ).count().label('session_count')
                ).group_by(UserSession.user_id).all()
                
                # Calculate session duration statistics
                session_durations = []
                for session in db_session.query(UserSession).all():
                    if session.created_at and session.updated_at:
                        duration = (session.updated_at - session.created_at).total_seconds()
                        session_durations.append(duration)
                
                duration_stats = {}
                if session_durations:
                    duration_stats = {
                        'avg_duration_seconds': sum(session_durations) / len(session_durations),
                        'min_duration_seconds': min(session_durations),
                        'max_duration_seconds': max(session_durations),
                        'total_sessions_analyzed': len(session_durations)
                    }
                
                return {
                    'age_distribution': age_distribution,
                    'platform_distribution': platform_distribution,
                    'active_users': len(user_activity),
                    'multi_session_users': len([u for u in user_activity if u[1] > 1]),
                    'session_duration_stats': duration_stats
                }
                
        except Exception as e:
            logger.error(f"Error getting detailed analytics: {e}")
            return {'error': str(e)}
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get session performance metrics"""
        try:
            # Get connection pool status
            pool_status = self.session_manager.get_connection_pool_status()
            
            # Get monitoring statistics
            monitor_stats = self.monitor.get_session_statistics()
            
            # Calculate performance indicators
            performance_indicators = {
                'connection_pool_efficiency': self._calculate_pool_efficiency(pool_status),
                'session_operation_success_rate': self._calculate_success_rate(monitor_stats),
                'average_response_time': self._calculate_avg_response_time(monitor_stats)
            }
            
            return {
                'connection_pool': pool_status,
                'monitoring_stats': monitor_stats.get('performance_stats', {}),
                'performance_indicators': performance_indicators
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def _get_security_analysis(self) -> Dict[str, Any]:
        """Get security analysis of sessions"""
        try:
            with self.session_manager.get_db_session() as db_session:
                now = datetime.now(timezone.utc)
                
                # Find potentially suspicious sessions
                suspicious_sessions = []
                
                # Sessions with rapid updates (potential session hijacking)
                rapid_update_sessions = db_session.query(UserSession).filter(
                    UserSession.updated_at > now - timedelta(minutes=5),
                    UserSession.created_at > now - timedelta(minutes=5)
                ).all()
                
                for session in rapid_update_sessions:
                    if session.created_at and session.updated_at:
                        update_frequency = (session.updated_at - session.created_at).total_seconds()
                        if update_frequency < 10:  # Updated within 10 seconds of creation
                            suspicious_sessions.append({
                                'session_id': session.session_id[:8] + '...',
                                'user_id': session.user_id,
                                'reason': 'rapid_updates',
                                'update_frequency_seconds': update_frequency
                            })
                
                # Very old sessions that are still active
                old_active_sessions = db_session.query(UserSession).filter(
                    UserSession.created_at < now - timedelta(days=7),
                    UserSession.updated_at > now - timedelta(hours=1)
                ).count()
                
                # Sessions without platform context
                orphaned_platform_sessions = db_session.query(UserSession).filter(
                    UserSession.active_platform_id.is_(None)
                ).count()
                
                return {
                    'suspicious_sessions': suspicious_sessions,
                    'old_active_sessions': old_active_sessions,
                    'orphaned_platform_sessions': orphaned_platform_sessions,
                    'security_score': self._calculate_security_score(
                        len(suspicious_sessions), old_active_sessions, orphaned_platform_sessions
                    )
                }
                
        except Exception as e:
            logger.error(f"Error getting security analysis: {e}")
            return {'error': str(e)}
    
    def _calculate_pool_efficiency(self, pool_status: Dict[str, Any]) -> float:
        """Calculate connection pool efficiency"""
        try:
            if 'error' in pool_status:
                return 0.0
            
            total_connections = pool_status.get('total_connections', 1)
            available_connections = pool_status.get('available_connections', 0)
            
            if total_connections == 0:
                return 0.0
            
            return (available_connections / total_connections) * 100
            
        except Exception:
            return 0.0
    
    def _calculate_success_rate(self, monitor_stats: Dict[str, Any]) -> float:
        """Calculate session operation success rate"""
        try:
            performance_stats = monitor_stats.get('performance_stats', {})
            
            creation_rate = performance_stats.get('session_creation_rate', {})
            error_rate = performance_stats.get('session_error_rate', {})
            
            if not creation_rate or not error_rate:
                return 100.0
            
            total_operations = creation_rate.get('count', 0)
            total_errors = error_rate.get('count', 0)
            
            if total_operations == 0:
                return 100.0
            
            return ((total_operations - total_errors) / total_operations) * 100
            
        except Exception:
            return 100.0
    
    def _calculate_avg_response_time(self, monitor_stats: Dict[str, Any]) -> float:
        """Calculate average response time"""
        try:
            performance_stats = monitor_stats.get('performance_stats', {})
            platform_switch_stats = performance_stats.get('platform_switch_duration', {})
            
            if platform_switch_stats:
                return platform_switch_stats.get('avg', 0.0)
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_security_score(self, suspicious_count: int, old_active_count: int, 
                                 orphaned_count: int) -> int:
        """Calculate security score (0-100)"""
        try:
            # Start with perfect score
            score = 100
            
            # Deduct points for security issues
            score -= min(suspicious_count * 10, 30)  # Max 30 points for suspicious sessions
            score -= min(old_active_count * 2, 20)   # Max 20 points for old active sessions
            score -= min(orphaned_count * 1, 10)     # Max 10 points for orphaned sessions
            
            return max(score, 0)
            
        except Exception:
            return 50  # Default moderate score on error
    
    def _generate_recommendations(self, health_report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on health report"""
        recommendations = []
        
        try:
            # Check connection pool efficiency
            performance = health_report.get('performance_metrics', {})
            pool_efficiency = performance.get('performance_indicators', {}).get('connection_pool_efficiency', 100)
            
            if pool_efficiency < 50:
                recommendations.append("Consider increasing database connection pool size")
            
            # Check security score
            security = health_report.get('security_analysis', {})
            security_score = security.get('security_score', 100)
            
            if security_score < 80:
                recommendations.append("Review session security - suspicious activity detected")
            
            # Check session age distribution
            analytics = health_report.get('detailed_analytics', {})
            age_dist = analytics.get('age_distribution', {})
            
            old_sessions = age_dist.get('last_month', 0) - age_dist.get('last_week', 0)
            if old_sessions > 100:
                recommendations.append("Consider more aggressive session cleanup policies")
            
            # Check error rates
            success_rate = performance.get('performance_indicators', {}).get('session_operation_success_rate', 100)
            if success_rate < 95:
                recommendations.append("Investigate session operation failures")
            
            if not recommendations:
                recommendations.append("Session system is operating optimally")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to analysis error")
        
        return recommendations
    
    def export_analytics_report(self, output_file: Optional[str] = None) -> str:
        """Export analytics report to file"""
        try:
            report = self.generate_health_report()
            
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"session_analytics_report_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Analytics report exported to {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error exporting analytics report: {e}")
            raise
    
    def get_session_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get session trends over specified period"""
        try:
            with self.session_manager.get_db_session() as db_session:
                now = datetime.now(timezone.utc)
                start_date = now - timedelta(days=days)
                
                # Daily session creation trends
                daily_trends = {}
                for i in range(days):
                    day_start = start_date + timedelta(days=i)
                    day_end = day_start + timedelta(days=1)
                    
                    daily_count = db_session.query(UserSession).filter(
                        UserSession.created_at >= day_start,
                        UserSession.created_at < day_end
                    ).count()
                    
                    daily_trends[day_start.strftime('%Y-%m-%d')] = daily_count
                
                return {
                    'period_days': days,
                    'daily_session_creation': daily_trends,
                    'total_sessions_created': sum(daily_trends.values()),
                    'average_daily_sessions': sum(daily_trends.values()) / days if days > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting session trends: {e}")
            return {'error': str(e)}

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Session Analytics and Health Monitoring')
    parser.add_argument('--health-report', action='store_true', help='Generate health report')
    parser.add_argument('--export', metavar='FILE', help='Export report to file')
    parser.add_argument('--trends', type=int, metavar='DAYS', default=7, help='Show trends for N days')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
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
        analytics = SessionAnalytics(config)
        
        if args.health_report:
            report = analytics.generate_health_report()
            
            if args.export:
                analytics.export_analytics_report(args.export)
                print(f"Health report exported to {args.export}")
            elif args.json:
                print(json.dumps(report, indent=2, default=str))
            else:
                # Pretty print report
                print("Session Health Report")
                print("=" * 50)
                
                # Health status
                health_status = report.get('health_status', {})
                print(f"Overall Health: {health_status.get('overall_health', 'unknown')}")
                
                # Issues
                issues = health_status.get('issues', [])
                if issues:
                    print("\nIssues:")
                    for issue in issues:
                        print(f"  - {issue}")
                
                # Recommendations
                recommendations = report.get('recommendations', [])
                if recommendations:
                    print("\nRecommendations:")
                    for rec in recommendations:
                        print(f"  - {rec}")
                
                # Key metrics
                analytics_data = report.get('detailed_analytics', {})
                if analytics_data:
                    print(f"\nActive Users: {analytics_data.get('active_users', 0)}")
                    print(f"Multi-Session Users: {analytics_data.get('multi_session_users', 0)}")
                    
                    age_dist = analytics_data.get('age_distribution', {})
                    print(f"Sessions (Last 24h): {age_dist.get('last_24h', 0)}")
        
        elif args.trends:
            trends = analytics.get_session_trends(args.trends)
            
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
        
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()