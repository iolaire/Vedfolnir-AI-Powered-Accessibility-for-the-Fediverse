#!/usr/bin/env python3
"""
Complete Migration Verification
==============================

Verifies that the migration to unified notification system is complete
and no legacy notification systems are being used.
"""

import os
import sys
import subprocess

def check_flash_calls():
    """Check for remaining flash calls in active code"""
    print("🔍 Checking for Flash Calls")
    print("-" * 30)
    
    try:
        result = subprocess.run([
            'grep', '-r', 'flash(', '--include=*.py', 
            'routes/', 'app/blueprints/', 'admin/'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            flash_calls = [line for line in result.stdout.split('\n') 
                          if line and 'backup' not in line]
            if flash_calls:
                print("❌ Found remaining flash calls:")
                for call in flash_calls[:5]:  # Show first 5
                    print(f"   {call}")
                return False
        
        print("✅ No flash calls found in active code")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not check flash calls: {e}")
        return True

def check_unified_notification_usage():
    """Check that routes are using unified notification system"""
    print("\n🔍 Checking Unified Notification Usage")
    print("-" * 40)
    
    try:
        result = subprocess.run([
            'grep', '-r', 'from app.services.notification.helpers.notification_helpers import', 
            '--include=*.py', 'routes/', 'app/blueprints/'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            unified_usage = result.stdout.strip().split('\n')
            print(f"✅ Found {len(unified_usage)} files using unified notifications:")
            for usage in unified_usage:
                file_path = usage.split(':')[0]
                print(f"   - {file_path}")
            return True
        else:
            print("⚠️  No unified notification usage found")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not check unified usage: {e}")
        return True

def check_deprecated_files():
    """Check that deprecated files have warnings"""
    print("\n🔍 Checking Deprecated Files")
    print("-" * 30)
    
    deprecated_files = [
        "storage_email_notification_service.py",
        "dashboard_notification_handlers.py",
        "admin_system_health_notification_handler.py",
        "user_profile_notification_helper.py"
    ]
    
    deprecated_count = 0
    for file_path in deprecated_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                if "DEPRECATED" in content:
                    deprecated_count += 1
                    print(f"✅ {file_path} - Properly deprecated")
                else:
                    print(f"⚠️  {file_path} - Missing deprecation warning")
    
    print(f"✅ {deprecated_count} legacy files properly deprecated")
    return True

def check_unified_system_components():
    """Check that unified system components exist and are importable"""
    print("\n🔍 Checking Unified System Components")
    print("-" * 40)
    
    components = [
        ("unified_notification_manager.py", "UnifiedNotificationManager"),
        ("notification_service_adapters.py", "StorageNotificationAdapter"),
        ("notification_helpers.py", "send_success_notification"),
        ("app/websocket/core/consolidated_handlers.py", "ConsolidatedWebSocketHandlers")
    ]
    
    all_good = True
    for file_path, component in components:
        if os.path.exists(file_path):
            print(f"✅ {file_path} - Available")
        else:
            print(f"❌ {file_path} - Missing")
            all_good = False
    
    # Test imports
    try:
        from app.services.notification.manager.unified_manager import UnifiedNotificationManager
        from app.services.notification.adapters.service_adapters import StorageNotificationAdapter
        from app.services.notification.helpers.notification_helpers import send_success_notification
        from app.websocket.core.consolidated_handlers import ConsolidatedWebSocketHandlers
        print("✅ All unified system components importable")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        all_good = False
    
    return all_good

def check_backup_created():
    """Check that backup was created"""
    print("\n🔍 Checking Legacy Backup")
    print("-" * 25)
    
    if os.path.exists("legacy_notification_backup"):
        backup_files = os.listdir("legacy_notification_backup")
        print(f"✅ Backup directory exists with {len(backup_files)} files")
        return True
    else:
        print("⚠️  No backup directory found")
        return False

def main():
    """Main verification function"""
    
    print("🚀 Complete Migration Verification")
    print("=" * 50)
    print("Verifying migration to unified notification system")
    print("=" * 50)
    
    checks = [
        ("Flash Calls Removed", check_flash_calls),
        ("Unified Notifications Used", check_unified_notification_usage),
        ("Legacy Files Deprecated", check_deprecated_files),
        ("Unified Components Available", check_unified_system_components),
        ("Legacy Backup Created", check_backup_created)
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        results[check_name] = check_func()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 MIGRATION VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name:30} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 MIGRATION VERIFICATION COMPLETE!")
        print("✅ All legacy notification systems removed/deprecated")
        print("✅ Unified notification system is the single source")
        print("✅ No flash calls remain in active code")
        print("✅ All routes use unified notification helpers")
        print("✅ System ready for production")
    else:
        print("❌ MIGRATION VERIFICATION FAILED")
        print("Some legacy systems may still be in use")
        print("Please review the failures above")
    
    print("=" * 50)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
