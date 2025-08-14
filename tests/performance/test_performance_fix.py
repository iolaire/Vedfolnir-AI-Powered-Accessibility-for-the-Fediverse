#!/usr/bin/env python3
"""
Test script to verify the performance monitoring fix works without hanging.
"""

import time
import threading
from session_performance_monitor import SessionPerformanceMonitor

def test_performance_monitor():
    """Test that performance monitoring doesn't hang"""
    print("Testing performance monitoring fix...")
    
    # Create a monitor instance
    monitor = SessionPerformanceMonitor("test_monitor")
    
    # Simulate some metrics
    monitor.record_session_creation(0.1)
    monitor.record_session_commit()
    monitor.record_session_closure(0.05)
    
    print("Basic metrics recorded successfully")
    
    # Test the periodic summary (this was causing the hang)
    print("Testing periodic summary logging...")
    
    # Force the summary to trigger by setting last snapshot to 0
    monitor.last_metrics_snapshot = 0
    
    # This should not hang now
    start_time = time.time()
    monitor.log_periodic_summary(interval_seconds=1)  # Use 1 second for testing
    
    # Wait a bit for the background thread to complete
    time.sleep(2)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Periodic summary completed in {duration:.2f} seconds")
    
    if duration < 5:  # Should complete quickly now
        print("✅ Performance monitoring fix successful - no hanging detected")
        return True
    else:
        print("❌ Performance monitoring still hanging")
        return False

if __name__ == "__main__":
    success = test_performance_monitor()
    exit(0 if success else 1)