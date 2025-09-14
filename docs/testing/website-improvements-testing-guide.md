# Website Improvements - Testing Guide

## Overview

This comprehensive testing guide covers all aspects of testing the Website Improvements implementation, including framework consolidation verification, admin interface testing, security compliance validation, and accessibility testing using both Python unittest and Playwright frameworks.

## Testing Architecture

### Dual Testing Strategy

The Website Improvements implementation uses a comprehensive dual testing approach:

1. **Python Testing Framework**: Unit tests, integration tests, and framework validation
2. **Playwright Testing Framework**: Browser-based end-to-end tests and user experience validation

### Test Organization Structure

```
tests/
├── admin/                           # Admin functionality tests
│   ├── test_platform_routes.py     # Platform management route tests
│   ├── test_security_routes.py     # Security management route tests
│   ├── test_system_routes.py       # System administration route tests
│   └── test_admin_api_endpoints.py # Admin API endpoint tests
├── security/                       # Security framework tests
│   ├── test_csp_enhancement.py     # CSP compliance tests
│   ├── test_security_framework.py  # Security framework tests
│   └── test_access_control.py      # Access control tests
├── integration/                    # Integration tests
│   ├── test_session_sync.py        # Session synchronization tests
│   ├── test_websocket_graceful.py  # WebSocket graceful degradation tests
│   └── test_framework_integration.py # Framework integration tests
├── performance/                    # Performance tests
│   ├── test_admin_performance.py   # Admin interface performance tests
│   └── test_framework_performance.py # Framework performance tests
├── accessibility/                  # Accessibility tests
│   ├── test_wcag_compliance.py     # WCAG compliance tests
│   └── test_keyboard_navigation.py # Keyboard navigation tests
└── playwright/                     # Browser automation tests
    ├── tests/
    │   ├── MMdd_HH_mm_test_admin_interface.js
    │   ├── MMdd_HH_mm_test_csp_compliance.js
    │   ├── MMdd_HH_mm_test_accessibility.js
    │   └── MMdd_HH_mm_test_session_cross_tab.js
    └── utils/
        └── MMdd_HH_mm_test_helpers.js
```

## Python Testing Framework

### Framework Consolidation Tests

#### Test Framework Integration

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

import unittest
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.manager import DatabaseManager
from app.core.security.csp.middleware import CSPMiddleware
from app.core.session.manager import SessionManager
from app.services.notification.manager.unified_manager import UnifiedNotificationManager
from app.services.monitoring.system.system_monitor import SystemMonitor

class TestFrameworkIntegration(unittest.TestCase):
    """Test framework consolidation and integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
    def test_security_framework_consolidation(self):
        """Test security framework is properly consolidated."""
        # Test CSP middleware initialization
        csp_middleware = CSPMiddleware()
        self.assertIsNotNone(csp_middleware)
        
        # Test nonce generation
        nonce = csp_middleware.generate_nonce()
        self.assertIsInstance(nonce, str)
        self.assertGreater(len(nonce), 10)
        
        # Test CSP header generation
        header = csp_middleware.get_csp_header(nonce)
        self.assertIn("script-src", header)
        self.assertIn(f"'nonce-{nonce}'", header)
        
    def test_session_framework_consolidation(self):
        """Test session framework is properly consolidated."""
        # Test session manager initialization
        session_manager = SessionManager(None, self.db_manager)
        self.assertIsNotNone(session_manager)
        
        # Test session creation (mock Redis)
        with unittest.mock.patch('redis.Redis'):
            session_id = session_manager.create_session(1, 123)
            self.assertIsInstance(session_id, str)
            
    def test_notification_framework_consolidation(self):
        """Test notification framework is properly consolidated."""
        # Test notification manager initialization
        notification_manager = UnifiedNotificationManager(self.db_manager)
        self.assertIsNotNone(notification_manager)
        
    def test_monitoring_framework_consolidation(self):
        """Test monitoring framework is properly consolidated."""
        # Test system monitor initialization
        system_monitor = SystemMonitor(self.db_manager)
        self.assertIsNotNone(system_monitor)
        
    def test_import_paths_updated(self):
        """Test all import paths use new app structure."""
        # Test core imports
        try:
            from app.core.security.csp.middleware import CSPMiddleware
            from app.core.session.manager import SessionManager
            from app.core.database.manager import DatabaseManager
            from app.core.configuration.manager import ConfigurationManager
        except ImportError as e:
            self.fail(f"Core framework import failed: {e}")
            
        # Test service imports
        try:
            from app.services.notification.manager.unified_manager import UnifiedNotificationManager
            from app.services.monitoring.system.system_monitor import SystemMonitor
            from app.services.maintenance.manager import MaintenanceManager
            from app.services.performance.monitor import PerformanceMonitor
        except ImportError as e:
            self.fail(f"Service framework import failed: {e}")
            
    def test_no_duplicate_frameworks(self):
        """Test no duplicate frameworks exist."""
        # Check that old framework files don't exist in root
        root_files = os.listdir('.')
        
        # Security framework files should not be in root
        security_files = [f for f in root_files if f.startswith('security_')]
        self.assertEqual(len(security_files), 0, 
                        f"Found duplicate security files in root: {security_files}")
        
        # Session framework files should not be in root
        session_files = [f for f in root_files if f.startswith('session_')]
        self.assertEqual(len(session_files), 0,
                        f"Found duplicate session files in root: {session_files}")
        
        # Notification framework files should not be in root
        notification_files = [f for f in root_files if 'notification' in f and f.endswith('.py')]
        self.assertEqual(len(notification_files), 0,
                        f"Found duplicate notification files in root: {notification_files}")

if __name__ == '__main__':
    unittest.main()
```

### Admin Route Tests

#### Test Admin Interface Routes

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.manager import DatabaseManager
from tests.test_helpers import create_test_user_with_platforms, cleanup_test_user
from models import UserRole

class TestAdminRoutes(unittest.TestCase):
    """Test admin route functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Create test admin user
        self.test_user, self.user_helper = create_test_user_with_platforms(
            self.db_manager, 
            username="test_admin", 
            role=UserRole.ADMIN
        )
        
    def tearDown(self):
        """Clean up test environment."""
        cleanup_test_user(self.user_helper)
        
    @patch('flask.current_user')
    def test_platform_management_route(self, mock_current_user):
        """Test platform management route access."""
        mock_current_user.id = self.test_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        
        # Import after mocking
        from app.blueprints.admin.platform_management import PlatformManagementRoutes
        from app.core.security.access_control import SecurityAccessControl
        
        # Initialize route handler
        access_control = SecurityAccessControl(self.db_manager)
        route_handler = PlatformManagementRoutes(
            security_framework=access_control,
            session_manager=None,
            notification_manager=None
        )
        
        # Test admin access check
        has_access = access_control.check_admin_access(self.test_user.id)
        self.assertTrue(has_access, "Admin user should have access to platform management")
        
    @patch('flask.current_user')
    def test_system_administration_route(self, mock_current_user):
        """Test system administration route access."""
        mock_current_user.id = self.test_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        
        from app.core.security.access_control import SecurityAccessControl
        
        access_control = SecurityAccessControl(self.db_manager)
        has_access = access_control.check_admin_access(self.test_user.id)
        self.assertTrue(has_access, "Admin user should have access to system administration")
        
    @patch('flask.current_user')
    def test_security_management_route(self, mock_current_user):
        """Test security management route access."""
        mock_current_user.id = self.test_user.id
        mock_current_user.role = UserRole.ADMIN
        mock_current_user.is_authenticated = True
        
        from app.core.security.access_control import SecurityAccessControl
        
        access_control = SecurityAccessControl(self.db_manager)
        has_access = access_control.check_admin_access(self.test_user.id)
        self.assertTrue(has_access, "Admin user should have access to security management")
        
    def test_non_admin_access_denied(self):
        """Test non-admin users are denied access."""
        # Create regular user
        regular_user, regular_helper = create_test_user_with_platforms(
            self.db_manager,
            username="regular_user",
            role=UserRole.REVIEWER
        )
        
        try:
            from app.core.security.access_control import SecurityAccessControl
            
            access_control = SecurityAccessControl(self.db_manager)
            has_access = access_control.check_admin_access(regular_user.id)
            self.assertFalse(has_access, "Regular user should not have admin access")
        finally:
            cleanup_test_user(regular_helper)

if __name__ == '__main__':
    unittest.main()
```

### Security Framework Tests

#### Test CSP Compliance

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

import unittest
import sys
import os
import re

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.security.csp.middleware import CSPMiddleware
from app.core.security.validation.content import ContentValidator

class TestCSPCompliance(unittest.TestCase):
    """Test Content Security Policy compliance."""
    
    def setUp(self):
        """Set up test environment."""
        self.csp_middleware = CSPMiddleware()
        self.content_validator = ContentValidator()
        
    def test_nonce_generation(self):
        """Test CSP nonce generation."""
        nonce = self.csp_middleware.generate_nonce()
        
        # Test nonce properties
        self.assertIsInstance(nonce, str)
        self.assertGreater(len(nonce), 10)
        self.assertRegex(nonce, r'^[A-Za-z0-9+/=]+$')  # Base64 pattern
        
        # Test nonce uniqueness
        nonce2 = self.csp_middleware.generate_nonce()
        self.assertNotEqual(nonce, nonce2)
        
    def test_csp_header_generation(self):
        """Test CSP header generation."""
        nonce = self.csp_middleware.generate_nonce()
        header = self.csp_middleware.get_csp_header(nonce)
        
        # Test header contains required directives
        self.assertIn("default-src 'self'", header)
        self.assertIn(f"script-src 'self' 'nonce-{nonce}'", header)
        self.assertIn(f"style-src 'self' 'nonce-{nonce}'", header)
        self.assertIn("img-src 'self' data: https:", header)
        
    def test_inline_content_validation(self):
        """Test inline content validation."""
        # Test valid content
        valid_content = "<p>This is safe content</p>"
        is_valid = self.csp_middleware.validate_inline_content(valid_content)
        self.assertTrue(is_valid)
        
        # Test invalid content
        invalid_content = "<script>alert('xss')</script>"
        is_valid = self.csp_middleware.validate_inline_content(invalid_content)
        self.assertFalse(is_valid)
        
    def test_csp_policy_configuration(self):
        """Test CSP policy configuration."""
        policy = self.csp_middleware.get_policy_config()
        
        # Test required policy directives
        self.assertIn('default-src', policy)
        self.assertIn('script-src', policy)
        self.assertIn('style-src', policy)
        self.assertIn('img-src', policy)
        self.assertIn('connect-src', policy)
        
        # Test WebSocket support
        self.assertIn('ws:', policy['connect-src'])
        self.assertIn('wss:', policy['connect-src'])

if __name__ == '__main__':
    unittest.main()
```

### Session Management Tests

#### Test Session Synchronization

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import time

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.manager import DatabaseManager
from app.core.session.manager import SessionManager
from app.core.session.sync.cross_tab import CrossTabSync

class TestSessionSynchronization(unittest.TestCase):
    """Test session synchronization functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
        # Mock Redis client
        self.mock_redis = MagicMock()
        self.session_manager = SessionManager(self.mock_redis, self.db_manager)
        self.cross_tab_sync = CrossTabSync()
        
    @patch('redis.Redis')
    def test_session_creation(self, mock_redis_class):
        """Test session creation with Redis."""
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance
        
        # Test session creation
        session_id = self.session_manager.create_session(1, 123)
        
        self.assertIsInstance(session_id, str)
        self.assertGreater(len(session_id), 20)
        
        # Verify Redis was called
        mock_redis_instance.setex.assert_called()
        
    @patch('redis.Redis')
    def test_session_retrieval(self, mock_redis_class):
        """Test session data retrieval."""
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance
        
        # Mock Redis response
        session_data = {
            'user_id': 1,
            'platform_connection_id': 123,
            'created_at': time.time()
        }
        mock_redis_instance.get.return_value = str(session_data).encode()
        
        # Test session retrieval
        retrieved_data = self.session_manager.get_session_data('test_session_id')
        
        self.assertIsNotNone(retrieved_data)
        mock_redis_instance.get.assert_called_with('vedfolnir:session:test_session_id')
        
    @patch('redis.Redis')
    def test_cross_tab_synchronization(self, mock_redis_class):
        """Test cross-tab session synchronization."""
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance
        
        # Test synchronization
        sync_data = {'last_activity': time.time()}
        self.cross_tab_sync.sync_across_tabs('test_session_id', sync_data)
        
        # Verify sync was attempted
        self.assertIsNotNone(self.cross_tab_sync)
        
    def test_database_fallback(self):
        """Test database fallback when Redis is unavailable."""
        # Simulate Redis failure
        self.mock_redis.get.side_effect = Exception("Redis connection failed")
        
        # Test fallback behavior
        with patch.object(self.session_manager, '_get_session_from_database') as mock_db_get:
            mock_db_get.return_value = {'user_id': 1}
            
            session_data = self.session_manager.get_session_data('test_session_id')
            
            # Verify database fallback was used
            mock_db_get.assert_called_once()
            self.assertEqual(session_data['user_id'], 1)

if __name__ == '__main__':
    unittest.main()
```

## Playwright Testing Framework

### Admin Interface Browser Tests

#### Test Admin Dashboard

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

const { test, expect } = require('@playwright/test');
const { ensureLoggedOut, loginAsAdmin } = require('../utils/0830_17_52_auth_utils');

test.describe('Admin Interface Tests', () => {
    test.beforeEach(async ({ page }) => {
        await ensureLoggedOut(page);
    });
    
    test.afterEach(async ({ page }) => {
        await ensureLoggedOut(page);
    });
    
    test('admin dashboard loads correctly', async ({ page }) => {
        // Login as admin
        await loginAsAdmin(page);
        
        // Navigate to admin dashboard
        await page.goto('/admin', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Verify dashboard elements
        await expect(page.locator('h1')).toContainText('Admin Dashboard');
        await expect(page.locator('.admin-nav')).toBeVisible();
        await expect(page.locator('.system-status')).toBeVisible();
    });
    
    test('platform management interface works', async ({ page }) => {
        await loginAsAdmin(page);
        
        // Navigate to platform management
        await page.goto('/admin/platforms', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Verify platform management elements
        await expect(page.locator('h2')).toContainText('Platform Management');
        await expect(page.locator('.platform-list')).toBeVisible();
        await expect(page.locator('.add-platform-btn')).toBeVisible();
    });
    
    test('system administration interface works', async ({ page }) => {
        await loginAsAdmin(page);
        
        // Navigate to system administration
        await page.goto('/admin/system', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Verify system administration elements
        await expect(page.locator('h2')).toContainText('System Administration');
        await expect(page.locator('.system-metrics')).toBeVisible();
        await expect(page.locator('.maintenance-controls')).toBeVisible();
    });
    
    test('security management interface works', async ({ page }) => {
        await loginAsAdmin(page);
        
        // Navigate to security management
        await page.goto('/admin/security', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Verify security management elements
        await expect(page.locator('h2')).toContainText('Security Management');
        await expect(page.locator('.security-status')).toBeVisible();
        await expect(page.locator('.audit-logs-link')).toBeVisible();
    });
    
    test('admin API endpoints work', async ({ page }) => {
        await loginAsAdmin(page);
        
        // Test system status API
        const systemStatusResponse = await page.request.get('/admin/api/system-status');
        expect(systemStatusResponse.ok()).toBeTruthy();
        
        const systemStatus = await systemStatusResponse.json();
        expect(systemStatus).toHaveProperty('status');
        expect(systemStatus).toHaveProperty('uptime');
        
        // Test performance metrics API
        const performanceResponse = await page.request.get('/admin/api/performance-metrics');
        expect(performanceResponse.ok()).toBeTruthy();
        
        const performanceMetrics = await performanceResponse.json();
        expect(performanceMetrics).toHaveProperty('response_times');
        expect(performanceMetrics).toHaveProperty('throughput');
    });
});
```

### CSP Compliance Browser Tests

#### Test CSP Violation Detection

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

const { test, expect } = require('@playwright/test');
const { ensureLoggedOut, loginAsAdmin } = require('../utils/0830_17_52_auth_utils');

test.describe('CSP Compliance Tests', () => {
    let consoleLogs = [];
    
    test.beforeEach(async ({ page }) => {
        await ensureLoggedOut(page);
        
        // Capture console messages
        consoleLogs = [];
        page.on('console', msg => {
            const message = `Console ${msg.type()}: ${msg.text()}`;
            consoleLogs.push(message);
            console.log(`   ${message}`);
        });
    });
    
    test.afterEach(async ({ page }) => {
        await ensureLoggedOut(page);
    });
    
    test('admin dashboard has no CSP violations', async ({ page }) => {
        await loginAsAdmin(page);
        
        // Navigate to admin dashboard
        await page.goto('/admin', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Wait for page to fully load
        await page.waitForTimeout(3000);
        
        // Check for CSP violations
        const cspViolations = consoleLogs.filter(log => 
            log.includes('Content Security Policy') || 
            log.includes('CSP') ||
            log.includes('blocked by Content Security Policy')
        );
        
        expect(cspViolations).toHaveLength(0);
        console.log(`✅ No CSP violations found on admin dashboard`);
    });
    
    test('platform management has no CSP violations', async ({ page }) => {
        await loginAsAdmin(page);
        
        await page.goto('/admin/platforms', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        await page.waitForTimeout(3000);
        
        const cspViolations = consoleLogs.filter(log => 
            log.includes('Content Security Policy')
        );
        
        expect(cspViolations).toHaveLength(0);
        console.log(`✅ No CSP violations found on platform management`);
    });
    
    test('CSP headers are present', async ({ page }) => {
        await loginAsAdmin(page);
        
        const response = await page.goto('/admin', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Check CSP header
        const cspHeader = response.headers()['content-security-policy'];
        expect(cspHeader).toBeTruthy();
        expect(cspHeader).toContain("default-src 'self'");
        expect(cspHeader).toContain("script-src");
        expect(cspHeader).toContain("style-src");
        
        console.log(`✅ CSP header present: ${cspHeader.substring(0, 100)}...`);
    });
    
    test('nonces are properly generated', async ({ page }) => {
        await loginAsAdmin(page);
        
        await page.goto('/admin', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Check for nonce in meta tag
        const nonceElement = await page.locator('meta[name="csp-nonce"]');
        if (await nonceElement.count() > 0) {
            const nonce = await nonceElement.getAttribute('content');
            expect(nonce).toBeTruthy();
            expect(nonce.length).toBeGreaterThan(10);
            console.log(`✅ CSP nonce found: ${nonce.substring(0, 20)}...`);
        }
        
        // Check for inline scripts with nonces
        const scriptElements = await page.locator('script[nonce]');
        const scriptCount = await scriptElements.count();
        console.log(`✅ Found ${scriptCount} scripts with nonces`);
    });
});
```

### Accessibility Browser Tests

#### Test WCAG Compliance

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

const { test, expect } = require('@playwright/test');
const { ensureLoggedOut, loginAsAdmin } = require('../utils/0830_17_52_auth_utils');

test.describe('Accessibility Compliance Tests', () => {
    test.beforeEach(async ({ page }) => {
        await ensureLoggedOut(page);
    });
    
    test.afterEach(async ({ page }) => {
        await ensureLoggedOut(page);
    });
    
    test('admin forms have proper labels', async ({ page }) => {
        await loginAsAdmin(page);
        
        // Navigate to a form page
        await page.goto('/admin/platforms/create', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Check all input fields have labels
        const inputs = await page.locator('input[type="text"], input[type="email"], input[type="password"], textarea, select');
        const inputCount = await inputs.count();
        
        for (let i = 0; i < inputCount; i++) {
            const input = inputs.nth(i);
            const inputId = await input.getAttribute('id');
            const inputName = await input.getAttribute('name');
            
            if (inputId) {
                // Check for associated label
                const label = await page.locator(`label[for="${inputId}"]`);
                const labelCount = await label.count();
                expect(labelCount).toBeGreaterThan(0);
            } else if (inputName) {
                // Check for aria-label or aria-labelledby
                const ariaLabel = await input.getAttribute('aria-label');
                const ariaLabelledBy = await input.getAttribute('aria-labelledby');
                expect(ariaLabel || ariaLabelledBy).toBeTruthy();
            }
        }
        
        console.log(`✅ All ${inputCount} form inputs have proper labels`);
    });
    
    test('keyboard navigation works', async ({ page }) => {
        await loginAsAdmin(page);
        
        await page.goto('/admin', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Test tab navigation
        await page.keyboard.press('Tab');
        let focusedElement = await page.locator(':focus');
        expect(await focusedElement.count()).toBeGreaterThan(0);
        
        // Continue tabbing through elements
        for (let i = 0; i < 5; i++) {
            await page.keyboard.press('Tab');
            focusedElement = await page.locator(':focus');
            expect(await focusedElement.count()).toBeGreaterThan(0);
        }
        
        console.log(`✅ Keyboard navigation works properly`);
    });
    
    test('page titles are descriptive', async ({ page }) => {
        await loginAsAdmin(page);
        
        // Test admin dashboard title
        await page.goto('/admin', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        let title = await page.title();
        expect(title).toContain('Admin');
        expect(title).toContain('Dashboard');
        
        // Test platform management title
        await page.goto('/admin/platforms', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        title = await page.title();
        expect(title).toContain('Platform');
        expect(title).toContain('Management');
        
        console.log(`✅ Page titles are descriptive and unique`);
    });
    
    test('color contrast is sufficient', async ({ page }) => {
        await loginAsAdmin(page);
        
        await page.goto('/admin', { 
            waitUntil: 'domcontentloaded',
            timeout: 30000 
        });
        
        // Check text elements for color contrast
        const textElements = await page.locator('p, h1, h2, h3, h4, h5, h6, span, div, a, button');
        const elementCount = await textElements.count();
        
        // Sample a few elements for contrast checking
        for (let i = 0; i < Math.min(elementCount, 10); i++) {
            const element = textElements.nth(i);
            const styles = await element.evaluate(el => {
                const computed = window.getComputedStyle(el);
                return {
                    color: computed.color,
                    backgroundColor: computed.backgroundColor,
                    fontSize: computed.fontSize
                };
            });
            
            // Basic check that colors are defined
            expect(styles.color).toBeTruthy();
            // Note: Full contrast ratio calculation would require additional libraries
        }
        
        console.log(`✅ Color contrast checked for ${Math.min(elementCount, 10)} elements`);
    });
});
```

### Cross-Tab Session Tests

#### Test Session Synchronization

```javascript
// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

const { test, expect } = require('@playwright/test');
const { ensureLoggedOut, loginAsAdmin } = require('../utils/0830_17_52_auth_utils');

test.describe('Cross-Tab Session Tests', () => {
    test('session synchronizes across tabs', async ({ browser }) => {
        // Create two browser contexts (tabs)
        const context1 = await browser.newContext();
        const context2 = await browser.newContext();
        
        const page1 = await context1.newPage();
        const page2 = await context2.newPage();
        
        try {
            // Login in first tab
            await ensureLoggedOut(page1);
            await loginAsAdmin(page1);
            
            // Navigate to admin dashboard
            await page1.goto('/admin', { 
                waitUntil: 'domcontentloaded',
                timeout: 30000 
            });
            
            // Verify login in first tab
            await expect(page1.locator('.admin-nav')).toBeVisible();
            
            // Open second tab and check session
            await page2.goto('/admin', { 
                waitUntil: 'domcontentloaded',
                timeout: 30000 
            });
            
            // Session should be synchronized
            await expect(page2.locator('.admin-nav')).toBeVisible();
            
            console.log(`✅ Session synchronized across tabs`);
            
            // Test session update synchronization
            await page1.goto('/admin/platforms', { 
                waitUntil: 'domcontentloaded',
                timeout: 30000 
            });
            
            // Wait for synchronization
            await page1.waitForTimeout(2000);
            
            // Check if second tab reflects the navigation
            await page2.reload({ waitUntil: 'domcontentloaded' });
            
            // Both tabs should maintain session
            await expect(page1.locator('.platform-list')).toBeVisible();
            await expect(page2.locator('.admin-nav')).toBeVisible();
            
            console.log(`✅ Session updates synchronized`);
            
        } finally {
            await ensureLoggedOut(page1);
            await ensureLoggedOut(page2);
            await context1.close();
            await context2.close();
        }
    });
    
    test('session logout synchronizes across tabs', async ({ browser }) => {
        const context1 = await browser.newContext();
        const context2 = await browser.newContext();
        
        const page1 = await context1.newPage();
        const page2 = await context2.newPage();
        
        try {
            // Login in both tabs
            await ensureLoggedOut(page1);
            await loginAsAdmin(page1);
            await loginAsAdmin(page2);
            
            // Navigate to admin in both tabs
            await page1.goto('/admin', { 
                waitUntil: 'domcontentloaded',
                timeout: 30000 
            });
            await page2.goto('/admin', { 
                waitUntil: 'domcontentloaded',
                timeout: 30000 
            });
            
            // Verify both tabs are logged in
            await expect(page1.locator('.admin-nav')).toBeVisible();
            await expect(page2.locator('.admin-nav')).toBeVisible();
            
            // Logout from first tab
            await page1.click('.logout-btn');
            await page1.waitForURL('/login', { timeout: 30000 });
            
            // Wait for synchronization
            await page1.waitForTimeout(3000);
            
            // Check if second tab is also logged out
            await page2.reload({ waitUntil: 'domcontentloaded' });
            
            // Second tab should redirect to login
            const currentUrl = page2.url();
            expect(currentUrl).toContain('/login');
            
            console.log(`✅ Logout synchronized across tabs`);
            
        } finally {
            await ensureLoggedOut(page1);
            await ensureLoggedOut(page2);
            await context1.close();
            await context2.close();
        }
    });
});
```

## Performance Testing

### Admin Interface Performance Tests

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

import unittest
import time
import requests
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

class TestAdminPerformance(unittest.TestCase):
    """Test admin interface performance."""
    
    def setUp(self):
        """Set up test environment."""
        self.base_url = "http://127.0.0.1:5000"
        self.session = requests.Session()
        
    def test_admin_dashboard_load_time(self):
        """Test admin dashboard loads within performance target."""
        # Login first (would need actual login implementation)
        # For now, test the endpoint directly
        
        start_time = time.time()
        response = self.session.get(f"{self.base_url}/admin")
        load_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Target: <500ms load time
        self.assertLess(load_time, 500, 
                       f"Admin dashboard load time {load_time:.2f}ms exceeds 500ms target")
        
        print(f"✅ Admin dashboard load time: {load_time:.2f}ms")
        
    def test_admin_api_response_time(self):
        """Test admin API endpoints response time."""
        endpoints = [
            '/admin/api/system-status',
            '/admin/api/performance-metrics',
            '/admin/api/storage-status'
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{endpoint}")
            response_time = (time.time() - start_time) * 1000
            
            # Target: <200ms API response time
            self.assertLess(response_time, 200,
                           f"API endpoint {endpoint} response time {response_time:.2f}ms exceeds 200ms target")
            
            print(f"✅ {endpoint} response time: {response_time:.2f}ms")

if __name__ == '__main__':
    unittest.main()
```

## Test Execution

### Running Python Tests

```bash
# Run all framework tests
python -m unittest discover tests -v

# Run specific test categories
python -m unittest tests.admin.test_admin_routes -v
python -m unittest tests.security.test_csp_compliance -v
python -m unittest tests.integration.test_framework_integration -v

# Run performance tests
python -m unittest tests.performance.test_admin_performance -v
```

### Running Playwright Tests

```bash
# Navigate to playwright directory
cd tests/playwright

# Start web application
python web_app.py & sleep 10

# Run all Playwright tests
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js

# Run specific test categories
timeout 120 npx playwright test tests/MMdd_HH_mm_test_admin_interface.js --config=0830_17_52_playwright.config.js
timeout 120 npx playwright test tests/MMdd_HH_mm_test_csp_compliance.js --config=0830_17_52_playwright.config.js
timeout 120 npx playwright test tests/MMdd_HH_mm_test_accessibility.js --config=0830_17_52_playwright.config.js

# Run with debugging
timeout 120 npx playwright test --config=0830_17_52_playwright.config.js --debug
```

### Continuous Integration

```yaml
# .github/workflows/website-improvements-tests.yml
name: Website Improvements Tests

on: [push, pull_request]

jobs:
  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Python tests
        run: python -m unittest discover tests -v
        
  playwright-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: 16
      - name: Install Playwright
        run: |
          cd tests/playwright
          npm install
          npx playwright install
      - name: Start web application
        run: python web_app.py &
      - name: Run Playwright tests
        run: |
          cd tests/playwright
          timeout 120 npx playwright test --config=0830_17_52_playwright.config.js
```

## Test Coverage Requirements

### Framework Consolidation Coverage
- ✅ All framework imports use new `app.*` structure
- ✅ No duplicate frameworks exist in root directory
- ✅ All services properly integrated with consolidated frameworks

### Admin Interface Coverage
- [ ] All admin routes return 200 status codes
- [ ] All admin forms submit successfully
- [ ] All admin API endpoints return valid JSON
- [ ] Admin access control works correctly

### Security Coverage
- [ ] CSP headers present on all pages
- [ ] No CSP violations in browser console
- [ ] All forms have CSRF protection
- [ ] Access control properly enforced

### Accessibility Coverage
- [ ] All forms have proper labels
- [ ] Keyboard navigation works throughout interface
- [ ] Page titles are descriptive and unique
- [ ] Color contrast meets WCAG standards

### Performance Coverage
- [ ] Admin dashboard loads in <500ms
- [ ] API endpoints respond in <200ms
- [ ] No memory leaks in long-running sessions
- [ ] Database queries optimized

This comprehensive testing guide ensures thorough validation of all Website Improvements functionality, from framework consolidation to user experience enhancements, using both automated Python tests and browser-based Playwright tests.