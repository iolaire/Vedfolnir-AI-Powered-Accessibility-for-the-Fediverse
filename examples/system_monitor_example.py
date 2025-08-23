# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
System Monitor Integration Example

This example demonstrates how to integrate the SystemMonitor class
with the existing multi-tenant caption management system.
"""

import asyncio
import logging
from datetime import datetime, timezone
from config import Config
from database import DatabaseManager
from system_monitor import SystemMonitor
import redis

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main example function"""
    print("System Monitor Integration Example")
    print("=" * 50)
    
    # Initialize configuration and database
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Initialize Redis client for metrics storage
    try:
        redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=1,  # Use different DB for metrics
            password=config.redis.password,
            decode_responses=True
        )
        redis_client.ping()
        print("✓ Connected to Redis for metrics storage")
    except Exception as e:
        print(f"⚠ Redis connection failed: {e}")
        redis_client = None
    
    # Initialize system monitor
    monitor = SystemMonitor(
        db_manager=db_manager,
        redis_client=redis_client,
        stuck_job_timeout=3600,  # 1 hour
        metrics_retention_hours=168  # 7 days
    )
    
    print("✓ System monitor initialized")
    print()
    
    # Demonstrate system health monitoring
    print("1. System Health Monitoring")
    print("-" * 30)
    
    health = monitor.get_system_health()
    print(f"Overall Status: {health.status}")
    print(f"CPU Usage: {health.cpu_usage:.1f}%")
    print(f"Memory Usage: {health.memory_usage:.1f}%")
    print(f"Disk Usage: {health.disk_usage:.1f}%")
    print(f"Database Status: {health.database_status}")
    print(f"Redis Status: {health.redis_status}")
    print(f"Active Tasks: {health.active_tasks}")
    print(f"Queued Tasks: {health.queued_tasks}")
    print(f"Failed Tasks (Last Hour): {health.failed_tasks_last_hour}")
    print(f"Avg Processing Time: {health.avg_processing_time:.1f}s")
    print()
    
    # Demonstrate performance metrics
    print("2. Performance Metrics")
    print("-" * 30)
    
    metrics = monitor.get_performance_metrics()
    print(f"Job Completion Rate: {metrics.job_completion_rate:.1f} jobs/hour")
    print(f"Average Processing Time: {metrics.avg_processing_time:.1f}s")
    print(f"Success Rate: {metrics.success_rate:.1f}%")
    print(f"Error Rate: {metrics.error_rate:.1f}%")
    print(f"Queue Wait Time: {metrics.queue_wait_time:.1f}s")
    print(f"Resource Usage: {metrics.resource_usage}")
    print(f"Throughput Metrics: {metrics.throughput_metrics}")
    print()
    
    # Demonstrate resource usage monitoring
    print("3. Resource Usage Monitoring")
    print("-" * 30)
    
    usage = monitor.check_resource_usage()
    print(f"CPU: {usage.cpu_percent:.1f}%")
    print(f"Memory: {usage.memory_percent:.1f}% ({usage.memory_used_mb:.0f}MB / {usage.memory_total_mb:.0f}MB)")
    print(f"Disk: {usage.disk_percent:.1f}% ({usage.disk_used_gb:.1f}GB / {usage.disk_total_gb:.1f}GB)")
    print(f"Database Connections: {usage.database_connections}")
    print(f"Redis Memory: {usage.redis_memory_mb:.1f}MB")
    print()
    
    # Demonstrate stuck job detection
    print("4. Stuck Job Detection")
    print("-" * 30)
    
    stuck_jobs = monitor.detect_stuck_jobs()
    if stuck_jobs:
        print(f"Found {len(stuck_jobs)} stuck jobs:")
        for job_id in stuck_jobs:
            print(f"  - {job_id}")
    else:
        print("No stuck jobs detected")
    print()
    
    # Demonstrate error trend analysis
    print("5. Error Trend Analysis")
    print("-" * 30)
    
    error_trends = monitor.get_error_trends(hours=24)
    print(f"Total Errors (24h): {error_trends.total_errors}")
    print(f"Error Rate: {error_trends.error_rate:.1f}%")
    print(f"Error Categories: {error_trends.error_categories}")
    if error_trends.trending_errors:
        print("Recent Errors:")
        for error in error_trends.trending_errors[-3:]:  # Show last 3
            print(f"  - {error['category']}: {error['error_message'][:50]}...")
    if error_trends.error_patterns:
        print("Error Patterns:")
        for pattern in error_trends.error_patterns:
            print(f"  - {pattern['description']}")
    print()
    
    # Demonstrate queue wait time prediction
    print("6. Queue Wait Time Prediction")
    print("-" * 30)
    
    predicted_wait = monitor.predict_queue_wait_time()
    print(f"Predicted Queue Wait Time: {predicted_wait}s ({predicted_wait // 60}m {predicted_wait % 60}s)")
    print()
    
    # Demonstrate historical metrics (if Redis is available)
    if redis_client:
        print("7. Historical Metrics")
        print("-" * 30)
        
        # Get historical health metrics
        historical_health = monitor.get_historical_metrics('health', hours=1)
        print(f"Historical Health Records (1h): {len(historical_health)}")
        
        # Get historical performance metrics
        historical_performance = monitor.get_historical_metrics('performance', hours=1)
        print(f"Historical Performance Records (1h): {len(historical_performance)}")
        
        # Clean up old metrics
        monitor.cleanup_old_metrics()
        print("✓ Cleaned up old metrics")
        print()
    
    # Demonstrate continuous monitoring simulation
    print("8. Continuous Monitoring Simulation")
    print("-" * 30)
    
    print("Simulating continuous monitoring for 30 seconds...")
    for i in range(6):  # 6 iterations, 5 seconds apart
        await asyncio.sleep(5)
        
        # Get fresh metrics
        health = monitor.get_system_health()
        metrics = monitor.get_performance_metrics()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"Status: {health.status}, "
              f"CPU: {health.cpu_usage:.1f}%, "
              f"Memory: {health.memory_usage:.1f}%, "
              f"Active: {health.active_tasks}, "
              f"Queued: {health.queued_tasks}")
    
    print()
    print("System Monitor Example Complete!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())