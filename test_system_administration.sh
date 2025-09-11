#!/bin/bash

# Simple test script to verify system administration functionality
echo "Testing System Administration Routes..."
echo "================================"

# Test 1: Check if login page is accessible
echo "1. Testing login page accessibility..."
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/user-management/login)
if [ "$LOGIN_STATUS" -eq 200 ]; then
    echo "✅ Login page is accessible (HTTP $LOGIN_STATUS)"
else
    echo "❌ Login page not accessible (HTTP $LOGIN_STATUS)"
    exit 1
fi

# Test 2: Check if system administration redirects unauthenticated users
echo "2. Testing system administration authentication redirect..."
SYSTEM_REDIRECT=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/admin/system)
if [ "$SYSTEM_REDIRECT" -eq 302 ]; then
    echo "✅ System administration properly redirects unauthenticated users (HTTP $SYSTEM_REDIRECT)"
else
    echo "❌ System administration not redirecting unauthenticated users (HTTP $SYSTEM_REDIRECT)"
    exit 1
fi

# Test 3: Check if system administration page loads after login
echo "3. Testing system administration page load (manual verification required)..."
echo "   Please manually test: http://127.0.0.1:5000/admin/system"
echo "   Expected: Should show 'System Administration' dashboard with content"

# Test 4: Check if API endpoints are properly secured (should redirect unauthenticated)
echo "4. Testing API endpoint security..."

# Test health API
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/admin/system/api/health)
if [ "$HEALTH_STATUS" -eq 302 ]; then
    echo "✅ Health API properly secured (HTTP $HEALTH_STATUS - redirects to login)"
else
    echo "❌ Health API security issue (HTTP $HEALTH_STATUS)"
    exit 1
fi

# Test performance API
PERFORMANCE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/admin/system/api/performance)
if [ "$PERFORMANCE_STATUS" -eq 302 ]; then
    echo "✅ Performance API properly secured (HTTP $PERFORMANCE_STATUS - redirects to login)"
else
    echo "❌ Performance API security issue (HTTP $PERFORMANCE_STATUS)"
    exit 1
fi

# Test resources API
RESOURCES_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/admin/system/api/resources)
if [ "$RESOURCES_STATUS" -eq 302 ]; then
    echo "✅ Resources API properly secured (HTTP $RESOURCES_STATUS - redirects to login)"
else
    echo "❌ Resources API security issue (HTTP $RESOURCES_STATUS)"
    exit 1
fi

echo ""
echo "🎉 All automated tests passed!"
echo ""
echo "Playwright test structure has been reorganized:"
echo "- Config files moved to: tests/playwright/config/"
echo "- Test files organized by category:"
echo "  * System tests: tests/playwright/tests/system/"
echo "  * Admin tests: tests/playwright/tests/admin/"
echo "  * Auth tests: tests/playwright/tests/auth/"
echo "  * Integration tests: tests/playwright/tests/integration/"
echo "- Utility files moved to: tests/playwright/utils/"
echo "- Scripts moved to: tests/playwright/scripts/"
echo ""
echo "To run the system administration Playwright test:"
echo "timeout 120 npx playwright test --config=tests/playwright/config/0830_17_52_playwright.config.js tests/playwright/tests/system/0910_14_52_test_system_administration.js"
echo ""
echo "Manual verification steps:"
echo "1. Open http://127.0.0.1:5000/user-management/login"
echo "2. Login with username: admin, password: admin123"
echo "3. Navigate to http://127.0.0.1:5000/admin/system"
echo "4. Verify the dashboard shows:"
echo "   - System Health Overview section"
echo "   - Performance Metrics section"
echo "   - Resource Usage section"
echo "   - Refresh and Export buttons"