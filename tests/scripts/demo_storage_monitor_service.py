#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo script for StorageMonitorService functionality.

This script demonstrates the storage monitoring service with various
file structures and caching behavior.
"""

import os
import sys
import tempfile
import shutil
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage_monitor_service import StorageMonitorService
from storage_configuration_service import StorageConfigurationService


def create_demo_files(storage_dir: str) -> dict:
    """Create demo files for testing"""
    files_created = {}
    
    # Create various subdirectories
    subdirs = ['photos', 'screenshots', 'uploads/user1', 'uploads/user2']
    for subdir in subdirs:
        subdir_path = os.path.join(storage_dir, subdir)
        os.makedirs(subdir_path, exist_ok=True)
    
    # Create files of various sizes
    demo_files = {
        'photos/vacation.jpg': 2 * 1024 * 1024,  # 2MB
        'photos/family.png': 1.5 * 1024 * 1024,  # 1.5MB
        'screenshots/bug_report.png': 500 * 1024,  # 500KB
        'screenshots/feature_demo.jpg': 750 * 1024,  # 750KB
        'uploads/user1/profile.jpg': 100 * 1024,  # 100KB
        'uploads/user1/banner.png': 200 * 1024,  # 200KB
        'uploads/user2/avatar.jpg': 80 * 1024,  # 80KB
        'uploads/user2/gallery1.png': 300 * 1024,  # 300KB
        'uploads/user2/gallery2.jpg': 250 * 1024,  # 250KB
    }
    
    total_size = 0
    for relative_path, size in demo_files.items():
        full_path = os.path.join(storage_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Create file with specified size
        with open(full_path, 'wb') as f:
            f.write(b'0' * int(size))
        
        files_created[relative_path] = size
        total_size += size
    
    return {
        'files': files_created,
        'total_size': total_size,
        'total_size_mb': total_size / (1024 * 1024)
    }


def demo_basic_functionality():
    """Demonstrate basic storage monitoring functionality"""
    print("=== StorageMonitorService Demo ===\n")
    
    # Create temporary directory for demo
    temp_dir = tempfile.mkdtemp(prefix="storage_demo_")
    demo_storage_dir = os.path.join(temp_dir, "storage", "images")
    os.makedirs(demo_storage_dir, exist_ok=True)
    
    try:
        # Create services with custom storage directory
        config_service = StorageConfigurationService()
        
        # Temporarily patch the storage directory for demo
        original_storage_dir = StorageMonitorService.STORAGE_IMAGES_DIR
        StorageMonitorService.STORAGE_IMAGES_DIR = demo_storage_dir
        
        monitor_service = StorageMonitorService(config_service)
        
        print("1. Configuration Settings:")
        print(f"   Max Storage Limit: {config_service.get_max_storage_gb()}GB")
        print(f"   Warning Threshold: {config_service.get_warning_threshold_gb()}GB")
        print(f"   Monitoring Enabled: {config_service.is_storage_monitoring_enabled()}")
        print()
        
        print("2. Empty Directory Test:")
        metrics = monitor_service.get_storage_metrics()
        print(f"   Total Storage: {metrics.total_gb:.4f}GB")
        print(f"   Usage Percentage: {metrics.usage_percentage:.2f}%")
        print(f"   Limit Exceeded: {metrics.is_limit_exceeded}")
        print(f"   Warning Exceeded: {metrics.is_warning_exceeded}")
        print()
        
        print("3. Creating Demo Files...")
        demo_info = create_demo_files(demo_storage_dir)
        print(f"   Created {len(demo_info['files'])} files")
        print(f"   Total Size: {demo_info['total_size_mb']:.2f}MB")
        print()
        
        print("4. Storage Calculation with Files:")
        # Invalidate cache to force recalculation
        monitor_service.invalidate_cache()
        metrics = monitor_service.get_storage_metrics()
        print(f"   Total Storage: {metrics.total_gb:.4f}GB ({metrics.total_bytes:,} bytes)")
        print(f"   Usage Percentage: {metrics.usage_percentage:.2f}%")
        print(f"   Limit Exceeded: {metrics.is_limit_exceeded}")
        print(f"   Warning Exceeded: {metrics.is_warning_exceeded}")
        print(f"   Last Calculated: {metrics.last_calculated}")
        print()
        
        print("5. Caching Demonstration:")
        cache_info = monitor_service.get_cache_info()
        print(f"   Has Cache: {cache_info['has_cache']}")
        print(f"   Is Valid: {cache_info['is_valid']}")
        print(f"   Cache Age: {cache_info['cache_age_seconds']:.2f}s")
        print(f"   Expires In: {cache_info['cache_expires_in_seconds']:.2f}s")
        print()
        
        print("6. Adding More Files (Cache Test)...")
        # Add more files
        extra_file = os.path.join(demo_storage_dir, "extra_large.jpg")
        with open(extra_file, 'wb') as f:
            f.write(b'0' * (1024 * 1024))  # 1MB
        
        # Get metrics again (should use cache)
        metrics_cached = monitor_service.get_storage_metrics()
        print(f"   Cached Total: {metrics_cached.total_gb:.4f}GB (should be same as before)")
        
        # Invalidate cache and get fresh metrics
        monitor_service.invalidate_cache()
        metrics_fresh = monitor_service.get_storage_metrics()
        print(f"   Fresh Total: {metrics_fresh.total_gb:.4f}GB (should include new file)")
        print()
        
        print("7. File Structure Analysis:")
        print("   Files by directory:")
        for file_path, size in demo_info['files'].items():
            directory = os.path.dirname(file_path) or "root"
            size_kb = size / 1024
            print(f"     {directory}: {os.path.basename(file_path)} ({size_kb:.0f}KB)")
        print()
        
        print("8. Performance Test:")
        start_time = time.time()
        for i in range(5):
            monitor_service.calculate_total_storage_bytes()
        end_time = time.time()
        avg_time = (end_time - start_time) / 5
        print(f"   Average calculation time: {avg_time:.4f}s")
        print()
        
        print("9. Metrics Serialization:")
        metrics_dict = metrics_fresh.to_dict()
        print("   Serialized metrics keys:", list(metrics_dict.keys()))
        print(f"   JSON-ready format: {type(metrics_dict['last_calculated'])}")
        print()
        
        # Restore original storage directory
        StorageMonitorService.STORAGE_IMAGES_DIR = original_storage_dir
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("=== Demo Complete ===")


def demo_error_handling():
    """Demonstrate error handling capabilities"""
    print("\n=== Error Handling Demo ===\n")
    
    # Test with non-existent directory
    config_service = StorageConfigurationService()
    
    # Use a non-existent directory
    non_existent_dir = "/tmp/non_existent_storage_demo"
    original_storage_dir = StorageMonitorService.STORAGE_IMAGES_DIR
    StorageMonitorService.STORAGE_IMAGES_DIR = non_existent_dir
    
    try:
        monitor_service = StorageMonitorService(config_service)
        
        print("1. Missing Directory Handling:")
        print(f"   Testing with: {non_existent_dir}")
        
        # This should create the directory and return 0
        total_bytes = monitor_service.calculate_total_storage_bytes()
        print(f"   Result: {total_bytes} bytes")
        print(f"   Directory created: {os.path.exists(non_existent_dir)}")
        
        # Clean up
        if os.path.exists(non_existent_dir):
            shutil.rmtree(non_existent_dir, ignore_errors=True)
        
    finally:
        StorageMonitorService.STORAGE_IMAGES_DIR = original_storage_dir
    
    print("\n=== Error Handling Demo Complete ===")


if __name__ == "__main__":
    try:
        demo_basic_functionality()
        demo_error_handling()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()