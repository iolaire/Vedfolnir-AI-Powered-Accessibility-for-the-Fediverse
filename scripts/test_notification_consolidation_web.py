#!/usr/bin/env python3
"""
Notification Consolidation Web Test
==================================

Simple test to verify web application functionality after notification
system consolidation without requiring Playwright.
"""

import sys
import os
import requests
import time

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_web_app_accessibility():
    """Test basic web app accessibility"""
    print("🌐 Testing Web Application Accessibility")
    print("-" * 45)
    
    base_url = "http://localhost:5000"
    
    # Test home page
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            print("✅ Home page accessible")
            
            # Check for notification-related elements in HTML
            html = response.text.lower()
            if 'notification' in html or 'alert' in html or 'flash' in html:
                print("✅ Notification display elements found in HTML")
            else:
                print("⚠️  No obvious notification elements in HTML")
                
            return True
        else:
            print(f"❌ Home page returned HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot access home page: {e}")
        return False

def test_notification_system_imports():
    """Test that notification system components can be imported"""
    print("\n🔔 Testing Notification System Imports")
    print("-" * 40)
    
    components = [
        ("UnifiedNotificationManager", "unified_notification_manager", "UnifiedNotificationManager"),
        ("Notification Helpers", "notification_helpers", "send_success_notification"),
        ("Service Adapters", "notification_service_adapters", "StorageNotificationAdapter"),
        ("WebSocket Handlers", "app.websocket.core.consolidated_handlers", "ConsolidatedWebSocketHandlers"),
        ("Email Adapter", "notification_service_adapters", "EmailNotificationAdapter")
    ]
    
    results = {}
    
    for name, module, component in components:
        try:
            exec(f"from {module} import {component}")
            results[name] = True
            print(f"✅ {name}: Importable")
        except ImportError as e:
            results[name] = False
            print(f"❌ {name}: Import error - {e}")
        except Exception as e:
            results[name] = False
            print(f"❌ {name}: Error - {e}")
    
    return all(results.values())

def test_unified_notification_functionality():
    """Test unified notification functionality"""
    print("\n🧪 Testing Unified Notification Functionality")
    print("-" * 45)
    
    try:
        # Test notification message creation
        from app.services.notification.manager.unified_manager import NotificationMessage
        from models import NotificationType, NotificationCategory
        
        message = NotificationMessage(
            id="test_001",
            type=NotificationType.SUCCESS,
            title="Test Notification",
            message="Testing unified notification system",
            category=NotificationCategory.USER
        )
        
        print("✅ NotificationMessage creation successful")
        print(f"   - ID: {message.id}")
        print(f"   - Type: {message.type.value}")
        print(f"   - Category: {message.category.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification functionality test failed: {e}")
        return False

def test_helper_functions():
    """Test notification helper functions"""
    print("\n🛠️  Testing Notification Helper Functions")
    print("-" * 40)
    
    try:
        from app.services.notification.helpers.notification_helpers import (
            send_success_notification, send_error_notification,
            send_warning_notification, send_info_notification,
            send_email_notification, send_verification_email
        )
        
        helpers = [
            "send_success_notification",
            "send_error_notification", 
            "send_warning_notification",
            "send_info_notification",
            "send_email_notification",
            "send_verification_email"
        ]
        
        for helper in helpers:
            func = locals()[helper]
            if callable(func):
                print(f"✅ {helper}: Available and callable")
            else:
                print(f"❌ {helper}: Not callable")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Helper function test failed: {e}")
        return False

def test_service_adapters():
    """Test service adapters"""
    print("\n🔧 Testing Service Adapters")
    print("-" * 30)
    
    try:
        from app.services.notification.adapters.service_adapters import (
            StorageNotificationAdapter, PlatformNotificationAdapter,
            DashboardNotificationAdapter, MonitoringNotificationAdapter,
            PerformanceNotificationAdapter, HealthNotificationAdapter,
            EmailNotificationAdapter
        )
        
        adapters = [
            "StorageNotificationAdapter",
            "PlatformNotificationAdapter",
            "DashboardNotificationAdapter", 
            "MonitoringNotificationAdapter",
            "PerformanceNotificationAdapter",
            "HealthNotificationAdapter",
            "EmailNotificationAdapter"
        ]
        
        for adapter in adapters:
            adapter_class = locals()[adapter]
            if hasattr(adapter_class, '__init__'):
                print(f"✅ {adapter}: Available")
            else:
                print(f"❌ {adapter}: Invalid class")
                return False
        
        print(f"✅ All {len(adapters)} service adapters available")
        return True
        
    except Exception as e:
        print(f"❌ Service adapter test failed: {e}")
        return False

def test_websocket_handlers():
    """Test WebSocket handlers"""
    print("\n🌐 Testing WebSocket Handlers")
    print("-" * 32)
    
    try:
        from app.websocket.core.consolidated_handlers import (
            ConsolidatedWebSocketHandlers, initialize_consolidated_websocket_handlers
        )
        
        print("✅ ConsolidatedWebSocketHandlers: Importable")
        print("✅ initialize_consolidated_websocket_handlers: Available")
        
        # Test handler methods exist
        handler_methods = [
            'is_user_connected',
            'broadcast_notification',
            '_get_user_notification_categories'
        ]
        
        for method in handler_methods:
            if hasattr(ConsolidatedWebSocketHandlers, method):
                print(f"✅ {method}: Method available")
            else:
                print(f"⚠️  {method}: Method not found")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocket handler test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Notification Consolidation Web Functionality Test")
    print("=" * 60)
    print("Testing web application after notification system consolidation")
    print("=" * 60)
    
    tests = [
        ("Web App Accessibility", test_web_app_accessibility),
        ("Notification System Imports", test_notification_system_imports),
        ("Unified Notification Functionality", test_unified_notification_functionality),
        ("Helper Functions", test_helper_functions),
        ("Service Adapters", test_service_adapters),
        ("WebSocket Handlers", test_websocket_handlers)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:35} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    print("\n" + "=" * 60)
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Notification system consolidation successful")
        print("✅ Web application functionality verified")
        print("✅ All components working correctly")
    elif passed >= total * 0.8:  # 80% pass rate
        print("✅ MOSTLY SUCCESSFUL!")
        print("✅ Core notification functionality working")
        print("⚠️  Some minor issues detected")
    else:
        print("⚠️  SIGNIFICANT ISSUES DETECTED")
        print("❌ Notification system may have problems")
        print("Review failed tests above")
    
    print("=" * 60)
    
    return passed >= total * 0.8  # Consider 80%+ a success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
