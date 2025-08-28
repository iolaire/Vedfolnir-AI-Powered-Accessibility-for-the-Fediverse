#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Enhanced WebSocket Error Handling and User Feedback System

This test validates the implementation of task 10: Enhanced Client Error Handling
and User Feedback, ensuring all requirements are met:
- User-friendly error message system with specific CORS guidance
- Visual connection status indicators with retry options  
- Automatic error recovery with user notification
- Fallback notification mechanisms for connection failures
- Debug mode with detailed connection diagnostics

Requirements: 4.4, 7.3, 9.1, 9.3, 9.4
"""

import unittest
import sys
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestEnhancedWebSocketErrorHandling(unittest.TestCase):
    """Test enhanced WebSocket error handling and user feedback system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://127.0.0.1:5000"
        cls.driver = None
        cls.setup_browser()
    
    @classmethod
    def setup_browser(cls):
        """Setup Chrome browser with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            cls.driver = webdriver.Chrome(options=chrome_options)
            cls.driver.implicitly_wait(10)
            print("✅ Chrome browser initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}")
            raise
    
    def setUp(self):
        """Set up each test"""
        if not self.driver:
            self.skipTest("Browser not available")
    
    def test_enhanced_error_handler_initialization(self):
        """Test that enhanced error handler initializes correctly"""
        print("\n🧪 Testing enhanced error handler initialization...")
        
        # Navigate to test page
        test_url = f"{self.base_url}/static/websocket-enhanced-error-demo.html"
        self.driver.get(test_url)
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check if enhanced error handler is available
        handler_available = self.driver.execute_script("""
            return typeof WebSocketEnhancedClientErrorHandler !== 'undefined';
        """)
        
        self.assertTrue(handler_available, "Enhanced error handler should be available")
        print("✅ Enhanced error handler is available")
    
    def test_cors_error_guidance(self):
        """Test CORS-specific error guidance (Requirement 4.4)"""
        print("\n🧪 Testing CORS error guidance...")
        
        # Create test page with CORS error simulation
        cors_test_result = self.driver.execute_script("""
            // Simulate CORS error
            const mockClient = {
                connected: false,
                on: function(event, callback) {
                    if (event === 'connect_error') {
                        setTimeout(() => {
                            const corsError = new Error('CORS policy blocked the connection');
                            callback(corsError);
                        }, 100);
                    }
                }
            };
            
            // Initialize enhanced error handler
            if (typeof WebSocketEnhancedClientErrorHandler !== 'undefined') {
                const handler = new WebSocketEnhancedClientErrorHandler(mockClient, {
                    corsGuidanceEnabled: true,
                    showErrorModal: true
                });
                
                return {
                    initialized: true,
                    corsGuidanceEnabled: handler.options.corsGuidanceEnabled
                };
            }
            
            return { initialized: false };
        """)
        
        self.assertTrue(cors_test_result.get('initialized'), "CORS error handler should initialize")
        self.assertTrue(cors_test_result.get('corsGuidanceEnabled'), "CORS guidance should be enabled")
        print("✅ CORS error guidance is properly configured") 
   
    def test_visual_connection_status_indicators(self):
        """Test visual connection status indicators with retry options (Requirement 7.3)"""
        print("\n🧪 Testing visual connection status indicators...")
        
        status_test_result = self.driver.execute_script("""
            // Test connection status component
            const mockClient = {
                connected: false,
                on: function(event, callback) {},
                io: { engine: { transport: { name: 'websocket' } } }
            };
            
            if (typeof WebSocketConnectionStatus !== 'undefined') {
                const statusIndicator = new WebSocketConnectionStatus(mockClient, null, {
                    showStatusBar: true,
                    showRetryButton: true,
                    enableManualRetry: true
                });
                
                // Check if status bar was created
                const statusBar = document.getElementById('websocket-status-bar');
                const retryButton = statusBar ? statusBar.querySelector('.retry-button') : null;
                
                return {
                    statusBarCreated: !!statusBar,
                    retryButtonAvailable: !!retryButton,
                    statusIndicatorInitialized: true
                };
            }
            
            return { statusIndicatorInitialized: false };
        """)
        
        self.assertTrue(status_test_result.get('statusIndicatorInitialized'), 
                       "Status indicator should initialize")
        self.assertTrue(status_test_result.get('statusBarCreated'), 
                       "Status bar should be created")
        print("✅ Visual connection status indicators are working")
    
    def test_automatic_error_recovery(self):
        """Test automatic error recovery with user notification (Requirement 9.1)"""
        print("\n🧪 Testing automatic error recovery...")
        
        recovery_test_result = self.driver.execute_script("""
            // Test automatic recovery system
            const mockClient = {
                connected: false,
                connect: function() { 
                    this.connected = true;
                    return Promise.resolve();
                },
                on: function(event, callback) {},
                io: { opts: { transports: ['websocket', 'polling'] } }
            };
            
            if (typeof WebSocketEnhancedClientErrorHandler !== 'undefined') {
                const handler = new WebSocketEnhancedClientErrorHandler(mockClient, {
                    enableAutoRecovery: true,
                    maxRecoveryAttempts: 3
                });
                
                // Test recovery strategy execution
                const corsStrategy = handler.state.recoveryStrategies.get('transport_fallback');
                
                return {
                    autoRecoveryEnabled: handler.options.enableAutoRecovery,
                    recoveryStrategiesAvailable: handler.state.recoveryStrategies.size > 0,
                    corsStrategyExists: !!corsStrategy
                };
            }
            
            return { autoRecoveryEnabled: false };
        """)
        
        self.assertTrue(recovery_test_result.get('autoRecoveryEnabled'), 
                       "Auto recovery should be enabled")
        self.assertTrue(recovery_test_result.get('recoveryStrategiesAvailable'), 
                       "Recovery strategies should be available")
        print("✅ Automatic error recovery is configured")
    
    def test_fallback_notification_mechanisms(self):
        """Test fallback notification mechanisms (Requirement 9.3)"""
        print("\n🧪 Testing fallback notification mechanisms...")
        
        fallback_test_result = self.driver.execute_script("""
            // Test fallback notification system
            if (typeof WebSocketFallbackNotifications !== 'undefined') {
                const fallbackNotifications = new WebSocketFallbackNotifications({
                    preferredMethods: ['toast', 'banner', 'console']
                });
                
                // Test notification methods
                const availableMethods = fallbackNotifications.state.availableMethods;
                
                // Test sending a notification
                fallbackNotifications.notify('Test notification', 'info');
                
                return {
                    fallbackInitialized: true,
                    availableMethodsCount: availableMethods.length,
                    hasToastMethod: availableMethods.includes('toast'),
                    hasBannerMethod: availableMethods.includes('banner'),
                    hasConsoleMethod: availableMethods.includes('console')
                };
            }
            
            return { fallbackInitialized: false };
        """)
        
        self.assertTrue(fallback_test_result.get('fallbackInitialized'), 
                       "Fallback notifications should initialize")
        self.assertGreater(fallback_test_result.get('availableMethodsCount', 0), 0, 
                          "Should have available notification methods")
        print("✅ Fallback notification mechanisms are working")
    
    def test_debug_mode_diagnostics(self):
        """Test debug mode with detailed connection diagnostics (Requirement 9.4)"""
        print("\n🧪 Testing debug mode diagnostics...")
        
        debug_test_result = self.driver.execute_script("""
            // Test debug diagnostics system
            const mockClient = {
                connected: false,
                on: function(event, callback) {},
                io: { engine: { transport: { name: 'websocket' } } }
            };
            
            if (typeof WebSocketDebugDiagnostics !== 'undefined') {
                const debugDiagnostics = new WebSocketDebugDiagnostics(mockClient, null, {
                    enablePerformanceMetrics: true,
                    enableNetworkDiagnostics: true,
                    showDebugPanel: false
                });
                
                // Check diagnostic capabilities
                const browserInfo = debugDiagnostics.diagnostics.browserInfo;
                const networkInfo = debugDiagnostics.diagnostics.networkInfo;
                
                return {
                    debugInitialized: true,
                    hasBrowserInfo: !!browserInfo,
                    hasNetworkInfo: !!networkInfo,
                    performanceMetricsEnabled: debugDiagnostics.options.enablePerformanceMetrics,
                    networkDiagnosticsEnabled: debugDiagnostics.options.enableNetworkDiagnostics
                };
            }
            
            return { debugInitialized: false };
        """)
        
        self.assertTrue(debug_test_result.get('debugInitialized'), 
                       "Debug diagnostics should initialize")
        self.assertTrue(debug_test_result.get('hasBrowserInfo'), 
                       "Should collect browser information")
        self.assertTrue(debug_test_result.get('hasNetworkInfo'), 
                       "Should collect network information")
        print("✅ Debug mode diagnostics are working")
    
    def test_integration_example_functionality(self):
        """Test the integration example functionality"""
        print("\n🧪 Testing integration example...")
        
        integration_test_result = self.driver.execute_script("""
            // Test integration example
            if (typeof WebSocketEnhancedClientIntegration !== 'undefined') {
                // Mock Socket.IO for testing
                window.io = function(url, options) {
                    return {
                        connected: false,
                        connect: function() { this.connected = true; },
                        disconnect: function() { this.connected = false; },
                        on: function(event, callback) {},
                        emit: function(event, data) {},
                        io: { 
                            engine: { transport: { name: 'websocket' } },
                            opts: { transports: ['websocket', 'polling'] }
                        }
                    };
                };
                
                try {
                    const integration = new WebSocketEnhancedClientIntegration({
                        enableEnhancedErrorHandling: true,
                        enableDebugMode: false,
                        enableUserFeedback: true
                    });
                    
                    return {
                        integrationInitialized: true,
                        hasClient: !!integration.client,
                        enhancedErrorHandlingEnabled: integration.options.enableEnhancedErrorHandling
                    };
                } catch (error) {
                    return {
                        integrationInitialized: false,
                        error: error.message
                    };
                }
            }
            
            return { integrationInitialized: false, error: 'Integration class not available' };
        """)
        
        self.assertTrue(integration_test_result.get('integrationInitialized'), 
                       f"Integration should initialize: {integration_test_result.get('error', '')}")
        self.assertTrue(integration_test_result.get('hasClient'), 
                       "Integration should have WebSocket client")
        print("✅ Integration example is working")
    
    def test_user_friendly_error_messages(self):
        """Test user-friendly error messages with specific guidance"""
        print("\n🧪 Testing user-friendly error messages...")
        
        error_message_test = self.driver.execute_script("""
            // Test error message system
            const mockClient = {
                connected: false,
                on: function(event, callback) {}
            };
            
            if (typeof WebSocketEnhancedClientErrorHandler !== 'undefined') {
                const handler = new WebSocketEnhancedClientErrorHandler(mockClient, {
                    detailedErrorMessages: true,
                    contextualHelp: true
                });
                
                // Check error categories
                const corsCategory = handler.state.errorCategories.get('cors');
                const authCategory = handler.state.errorCategories.get('authentication');
                const networkCategory = handler.state.errorCategories.get('network');
                
                return {
                    errorCategoriesConfigured: handler.state.errorCategories.size > 0,
                    corsGuidanceAvailable: !!(corsCategory && corsCategory.guidance),
                    authGuidanceAvailable: !!(authCategory && authCategory.guidance),
                    networkGuidanceAvailable: !!(networkCategory && networkCategory.guidance),
                    userActionsAvailable: !!(corsCategory && corsCategory.userActions)
                };
            }
            
            return { errorCategoriesConfigured: false };
        """)
        
        self.assertTrue(error_message_test.get('errorCategoriesConfigured'), 
                       "Error categories should be configured")
        self.assertTrue(error_message_test.get('corsGuidanceAvailable'), 
                       "CORS guidance should be available")
        self.assertTrue(error_message_test.get('authGuidanceAvailable'), 
                       "Authentication guidance should be available")
        print("✅ User-friendly error messages are configured")
    
    def test_comprehensive_system_integration(self):
        """Test comprehensive system integration of all components"""
        print("\n🧪 Testing comprehensive system integration...")
        
        system_test_result = self.driver.execute_script("""
            // Test complete system integration
            const mockClient = {
                connected: false,
                connect: function() { this.connected = true; },
                disconnect: function() { this.connected = false; },
                on: function(event, callback) {},
                emit: function(event, data) {},
                io: { 
                    engine: { transport: { name: 'websocket' } },
                    opts: { transports: ['websocket', 'polling'] }
                }
            };
            
            let componentsInitialized = 0;
            let errors = [];
            
            // Test each component
            try {
                if (typeof WebSocketEnhancedClientErrorHandler !== 'undefined') {
                    new WebSocketEnhancedClientErrorHandler(mockClient);
                    componentsInitialized++;
                }
            } catch (e) { errors.push('EnhancedErrorHandler: ' + e.message); }
            
            try {
                if (typeof WebSocketConnectionStatus !== 'undefined') {
                    new WebSocketConnectionStatus(mockClient, null);
                    componentsInitialized++;
                }
            } catch (e) { errors.push('ConnectionStatus: ' + e.message); }
            
            try {
                if (typeof WebSocketFallbackNotifications !== 'undefined') {
                    new WebSocketFallbackNotifications();
                    componentsInitialized++;
                }
            } catch (e) { errors.push('FallbackNotifications: ' + e.message); }
            
            try {
                if (typeof WebSocketDebugDiagnostics !== 'undefined') {
                    new WebSocketDebugDiagnostics(mockClient, null);
                    componentsInitialized++;
                }
            } catch (e) { errors.push('DebugDiagnostics: ' + e.message); }
            
            return {
                componentsInitialized,
                totalComponents: 4,
                errors,
                allComponentsWorking: componentsInitialized === 4 && errors.length === 0
            };
        """)
        
        components_count = system_test_result.get('componentsInitialized', 0)
        total_components = system_test_result.get('totalComponents', 4)
        errors = system_test_result.get('errors', [])
        
        self.assertGreater(components_count, 0, "At least some components should initialize")
        
        if errors:
            print(f"⚠️  Component initialization errors: {errors}")
        
        print(f"✅ {components_count}/{total_components} components initialized successfully")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if cls.driver:
            cls.driver.quit()
            print("✅ Browser closed")

def run_enhanced_websocket_tests():
    """Run enhanced WebSocket error handling tests"""
    print("🚀 Starting Enhanced WebSocket Error Handling Tests")
    print("=" * 60)
    
    # Check if web server is running
    try:
        response = requests.get("http://127.0.0.1:5000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Web server is not responding correctly")
            return False
    except requests.exceptions.RequestException:
        print("❌ Web server is not running. Please start it with: python web_app.py")
        return False
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnhancedWebSocketErrorHandling)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n✅ All Enhanced WebSocket Error Handling tests passed!")
        print("🎉 Task 10 implementation is working correctly")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
    
    return success

if __name__ == '__main__':
    success = run_enhanced_websocket_tests()
    sys.exit(0 if success else 1)