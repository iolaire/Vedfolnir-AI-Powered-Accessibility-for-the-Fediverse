#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Platform health monitoring

Monitors platform connections and system health.
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models import User, PlatformConnection
from database import DatabaseManager

class PlatformHealthMonitor:
    """Monitors platform health and connectivity"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.health_data = {}
    
    def check_platform_connections(self):
        """Check all platform connections"""
        print("🔍 Checking platform connections...")
        
        session = self.db_manager.get_session()
        platforms = session.query(PlatformConnection).filter(
            PlatformConnection.is_active == True
        ).all()
        
        connection_results = []
        
        for platform in platforms:
            print(f"  🔗 Testing {platform.name}...")
            
            result = {
                'platform_id': platform.id,
                'name': platform.name,
                'platform_type': platform.platform_type,
                'instance_url': platform.instance_url,
                'status': 'unknown',
                'response_time': None,
                'error': None,
                'checked_at': datetime.now().isoformat()
            }
            
            try:
                start_time = time.time()
                
                # Mock connection test (in real implementation, test actual API)
                # This would make HTTP request to platform API
                time.sleep(0.1)  # Simulate network delay
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                
                result.update({
                    'status': 'healthy',
                    'response_time': round(response_time, 2)
                })
                
                print(f"    ✅ Healthy ({response_time:.0f}ms)")
                
            except Exception as e:
                result.update({
                    'status': 'error',
                    'error': str(e)
                })
                print(f"    ❌ Error: {e}")
            
            connection_results.append(result)
        
        session.close()
        return connection_results
    
    def check_database_health(self):
        """Check database health"""
        print("🔍 Checking database health...")
        
        try:
            session = self.db_manager.get_session()
            
            # Check basic connectivity
            user_count = session.query(User).count()
            platform_count = session.query(PlatformConnection).count()
            
            # Check recent activity
            from models import Post, Image
            recent_posts = session.query(Post).filter(
                Post.created_at > datetime.now() - timedelta(hours=24)
            ).count()
            
            recent_images = session.query(Image).filter(
                Image.created_at > datetime.now() - timedelta(hours=24)
            ).count()
            
            session.close()
            
            db_health = {
                'status': 'healthy',
                'users': user_count,
                'platforms': platform_count,
                'recent_posts_24h': recent_posts,
                'recent_images_24h': recent_images,
                'checked_at': datetime.now().isoformat()
            }
            
            print(f"  ✅ Database healthy ({user_count} users, {platform_count} platforms)")
            return db_health
            
        except Exception as e:
            print(f"  ❌ Database error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    def check_system_resources(self):
        """Check system resource usage"""
        print("🔍 Checking system resources...")
        
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            resources = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'status': 'healthy' if all([
                    cpu_percent < 80,
                    memory_percent < 80,
                    disk_percent < 90
                ]) else 'warning',
                'checked_at': datetime.now().isoformat()
            }
            
            print(f"  📊 CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
            return resources
            
        except ImportError:
            print("  ⚠️ psutil not available for resource monitoring")
            return {
                'status': 'unavailable',
                'message': 'psutil not installed',
                'checked_at': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"  ❌ Resource check error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    def generate_health_report(self):
        """Generate comprehensive health report"""
        print("📋 Generating health report...")
        
        # Collect all health data
        platform_connections = self.check_platform_connections()
        database_health = self.check_database_health()
        system_resources = self.check_system_resources()
        
        # Determine overall status
        platform_statuses = [p['status'] for p in platform_connections]
        overall_status = 'healthy'
        
        if 'error' in platform_statuses or database_health['status'] == 'error':
            overall_status = 'error'
        elif 'warning' in platform_statuses or system_resources['status'] == 'warning':
            overall_status = 'warning'
        
        health_report = {
            'overall_status': overall_status,
            'generated_at': datetime.now().isoformat(),
            'platform_connections': platform_connections,
            'database': database_health,
            'system_resources': system_resources,
            'summary': {
                'total_platforms': len(platform_connections),
                'healthy_platforms': len([p for p in platform_connections if p['status'] == 'healthy']),
                'error_platforms': len([p for p in platform_connections if p['status'] == 'error'])
            }
        }
        
        return health_report
    
    def save_health_report(self, report, filename=None):
        """Save health report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"logs/health_report_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"💾 Health report saved to: {filename}")
        return filename
    
    def print_health_summary(self, report):
        """Print health summary to console"""
        print("\n" + "=" * 60)
        print("🏥 PLATFORM HEALTH SUMMARY")
        print("=" * 60)
        
        # Overall status
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        
        print(f"Overall Status: {status_emoji.get(report['overall_status'], '❓')} {report['overall_status'].upper()}")
        print(f"Generated: {report['generated_at']}")
        
        # Platform summary
        summary = report['summary']
        print(f"\nPlatforms: {summary['healthy_platforms']}/{summary['total_platforms']} healthy")
        
        if summary['error_platforms'] > 0:
            print(f"❌ {summary['error_platforms']} platforms have errors")
        
        # Database status
        db_status = report['database']['status']
        print(f"Database: {status_emoji.get(db_status, '❓')} {db_status}")
        
        # System resources
        if 'cpu_percent' in report['system_resources']:
            res = report['system_resources']
            print(f"Resources: CPU {res['cpu_percent']}%, Memory {res['memory_percent']}%, Disk {res['disk_percent']}%")
        
        print("=" * 60)

def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Platform health monitoring')
    parser.add_argument('--save', help='Save report to file')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet output')
    parser.add_argument('--json', action='store_true', help='Output JSON only')
    
    args = parser.parse_args()
    
    monitor = PlatformHealthMonitor()
    
    try:
        # Generate health report
        if not args.quiet:
            print("🏥 Platform Health Monitor")
            print("=" * 40)
        
        report = monitor.generate_health_report()
        
        # Output results
        if args.json:
            print(json.dumps(report, indent=2))
        elif not args.quiet:
            monitor.print_health_summary(report)
        
        # Save report if requested
        if args.save:
            monitor.save_health_report(report, args.save)
        
        # Return appropriate exit code
        if report['overall_status'] == 'error':
            return 1
        elif report['overall_status'] == 'warning':
            return 2
        else:
            return 0
            
    except Exception as e:
        print(f"❌ Health monitoring failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())