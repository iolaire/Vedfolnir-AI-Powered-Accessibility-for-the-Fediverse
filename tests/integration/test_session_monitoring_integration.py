#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Integration test for session performance monitoring.
This script tests the complete session monitoring system.
"""

import time
from session_performance_monitor import SessionPerformanceMonitor, get_performance_monitor

def test_basic_monitoring():
    """Test basic monitoring functionality"""
    print("Testing basic monitoring functionality...")
    
    monitor = SessionPerformanceMonitor("integration_test")
    
    # Test session lifecycle
    monitor.record_session_creation(0.1)
    monitor.record_session_commit()
    monitor.record_session_reattachment("User")
    monitor.record_detached_instance_recovery("PlatformConnection", 0.05, True)
    monitor.record_session_closure(0.08)
    
    # Get metrics
    metrics = monitor.get_current_metrics()
    
    # Verify metrics
    assert metrics['session_metrics']['creations'] == 1
    assert metrics['session_metrics']['closures'] == 1
    assert metrics['session_metrics']['commits'] == 1
    assert metrics['recovery_metrics']['detached_instance_recoveries'] == 1
    assert metrics['recovery_metrics']['session_reattachments'] == 1
    
    print("✅ Basic monitoring test passed")

def test_performance_summary():
    """Test performance summary generation"""
    print("Testing performance summary generation...")
    
    monitor = SessionPerformanceMonitor("summary_test")
    
    # Add some test data
    monitor.record_session_creation(0.2)
    monitor.record_session_creation(0.3)
    monitor.record_session_closure(0.1)
    monitor.record_session_closure(0.15)
    monitor.record_detached_instance_recovery("User", 0.05, True)
    monitor.record_detached_instance_recovery("Platform", 0.08, False)
    
    # Get summary
    summary = monitor.get_performance_summary()
    
    # Verify summary contains expected sections
    assert "Session Performance Summary" in summary
    assert "Recovery Metrics" in summary
    assert "Performance Timing" in summary
    assert "Database Pool" in summary
    
    print("✅ Performance summary test passed")

def test_error_scenarios():
    """Test error scenario monitoring"""
    print("Testing error scenario monitoring...")
    
    monitor = SessionPerformanceMonitor("error_test")
    
    # Simulate error scenarios
    monitor.record_session_creation(0.1)
    monitor.record_session_error("connection_timeout", "Connection timed out")
    monitor.record_detached_instance_recovery("User", 0.2, False)  # Failed recovery
    monitor.record_session_rollback()
    monitor.record_session_closure(0.05)
    
    metrics = monitor.get_current_metrics()
    
    # Verify error tracking
    assert metrics['session_metrics']['errors'] == 1
    assert metrics['session_metrics']['rollbacks'] == 1
    assert metrics['recovery_metrics']['detached_instance_recoveries'] == 1
    
    print("✅ Error scenario test passed")

def test_performance_thresholds():
    """Test performance threshold detection"""
    print("Testing performance threshold detection...")
    
    monitor = SessionPerformanceMonitor("threshold_test")
    
    # Record slow operations (above 1.0s threshold)
    monitor.record_session_creation(2.0)  # Slow creation
    monitor.record_session_closure(1.5)   # Slow cleanup
    monitor.record_detached_instance_recovery("User", 3.0, True)  # Slow recovery
    
    metrics = monitor.get_current_metrics()
    
    # Check that slow operations were recorded
    assert metrics['performance_metrics']['avg_creation_time'] > 1.0
    assert metrics['performance_metrics']['avg_cleanup_time'] > 1.0
    assert metrics['performance_metrics']['avg_recovery_time'] > 1.0
    
    print("✅ Performance threshold test passed")

def test_singleton_monitor():
    """Test global monitor singleton"""
    print("Testing global monitor singleton...")
    
    monitor1 = get_performance_monitor()
    monitor2 = get_performance_monitor()
    
    # Should be the same instance
    assert monitor1 is monitor2
    
    # Test that it works
    monitor1.record_session_creation(0.1)
    metrics = monitor2.get_current_metrics()
    
    assert metrics['session_metrics']['creations'] >= 1
    
    print("✅ Singleton monitor test passed")

def main():
    """Run all integration tests"""
    print("Starting session performance monitoring integration tests...")
    print("=" * 60)
    
    try:
        test_basic_monitoring()
        test_performance_summary()
        test_error_scenarios()
        test_performance_thresholds()
        test_singleton_monitor()
        
        print("=" * 60)
        print("🎉 All integration tests passed!")
        
        # Show final summary
        monitor = get_performance_monitor()
        print("\nFinal Performance Summary:")
        print(monitor.get_performance_summary())
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise

if __name__ == "__main__":
    main()