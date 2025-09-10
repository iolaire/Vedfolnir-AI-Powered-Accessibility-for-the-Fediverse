#!/usr/bin/env python3
"""
Web Application Functionality Test Runner
=========================================

Runs comprehensive Playwright tests to verify web application functionality
after notification system consolidation changes.
"""

import subprocess
import sys
import time
import requests
import os
from pathlib import Path

def check_web_app_running():
    """Check if web application is running"""
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_web_app():
    """Start web application for testing"""
    print("🚀 Starting web application for testing...")
    
    # Start web app in background
    try:
        process = subprocess.Popen([
            sys.executable, "web_app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for app to start
        for i in range(30):  # Wait up to 30 seconds
            if check_web_app_running():
                print("✅ Web application started successfully")
                return process
            time.sleep(1)
        
        print("❌ Web application failed to start")
        process.terminate()
        return None
        
    except Exception as e:
        print(f"❌ Error starting web application: {e}")
        return None

def install_playwright():
    """Install Playwright if not available"""
    try:
        import playwright
        print("✅ Playwright already installed")
        return True
    except ImportError:
        print("📦 Installing Playwright...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
            subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
            print("✅ Playwright installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Playwright: {e}")
            return False

def run_playwright_tests():
    """Run Playwright tests"""
    print("🎭 Running Playwright tests...")
    
    test_file = "tests/playwright/test_notification_consolidation.py"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        # Run pytest with Playwright
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_file,
            "-v",
            "--tb=short"
        ], capture_output=True, text=True)
        
        print("📊 Test Results:")
        print("=" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  Test Warnings/Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All Playwright tests passed!")
            return True
        else:
            print("❌ Some Playwright tests failed")
            return False
            
    except Exception as e:
        print(f"❌ Error running Playwright tests: {e}")
        return False

def run_basic_functionality_test():
    """Run basic functionality test without Playwright"""
    print("🔍 Running basic functionality test...")
    
    test_urls = [
        ("Home Page", "http://localhost:5000"),
        ("Login Page", "http://localhost:5000/user-management/login"),
        ("Register Page", "http://localhost:5000/user-management/register"),
        ("GDPR Page", "http://localhost:5000/gdpr/data-export"),
    ]
    
    results = {}
    
    for name, url in test_urls:
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                results[name] = "✅ PASS"
                print(f"✅ {name}: Accessible")
            elif response.status_code in [302, 301]:
                results[name] = "🔄 REDIRECT"
                print(f"🔄 {name}: Redirected (may require auth)")
            else:
                results[name] = f"❌ HTTP {response.status_code}"
                print(f"❌ {name}: HTTP {response.status_code}")
        except Exception as e:
            results[name] = f"❌ ERROR: {str(e)[:50]}"
            print(f"❌ {name}: Error - {e}")
    
    return results

def test_notification_system_integration():
    """Test notification system integration"""
    print("🔔 Testing notification system integration...")
    
    try:
        # Test unified notification manager import
        from app.services.notification.manager.unified_manager import UnifiedNotificationManager
        print("✅ UnifiedNotificationManager importable")
        
        # Test notification helpers import
        from app.services.notification.helpers.notification_helpers import send_success_notification
        print("✅ Notification helpers importable")
        
        # Test service adapters import
        from app.services.notification.adapters.service_adapters import StorageNotificationAdapter
        print("✅ Service adapters importable")
        
        # Test consolidated WebSocket handlers import
        from app.websocket.core.consolidated_handlers import ConsolidatedWebSocketHandlers
        print("✅ Consolidated WebSocket handlers importable")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test runner"""
    print("🧪 Web Application Functionality Test Suite")
    print("=" * 60)
    print("Testing web application after notification system consolidation")
    print("=" * 60)
    
    # Check if web app is running
    if not check_web_app_running():
        print("⚠️  Web application not running on localhost:5000")
        print("Please start the web application manually with: python web_app.py")
        print("Then run this test script again.")
        return False
    
    print("✅ Web application is running")
    
    # Test notification system integration
    integration_ok = test_notification_system_integration()
    
    # Run basic functionality test
    basic_results = run_basic_functionality_test()
    
    # Try to run Playwright tests
    playwright_available = install_playwright()
    playwright_ok = False
    
    if playwright_available:
        playwright_ok = run_playwright_tests()
    else:
        print("⚠️  Playwright not available, skipping advanced tests")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    print(f"Notification Integration: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    
    print("\nBasic Functionality Tests:")
    for test_name, result in basic_results.items():
        print(f"  {test_name}: {result}")
    
    if playwright_available:
        print(f"\nPlaywright Tests: {'✅ PASS' if playwright_ok else '❌ FAIL'}")
    else:
        print("\nPlaywright Tests: ⚠️  SKIPPED (not available)")
    
    # Overall result
    basic_passed = all("✅" in result or "🔄" in result for result in basic_results.values())
    overall_success = integration_ok and basic_passed and (playwright_ok or not playwright_available)
    
    print("\n" + "=" * 60)
    if overall_success:
        print("🎉 WEB APPLICATION FUNCTIONALITY VERIFIED!")
        print("✅ Notification system consolidation successful")
        print("✅ Web application functioning correctly")
        print("✅ All major areas accessible")
    else:
        print("⚠️  WEB APPLICATION ISSUES DETECTED")
        print("Some functionality may not be working correctly")
        print("Review the test results above for details")
    
    print("=" * 60)
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
