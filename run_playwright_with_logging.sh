#!/bin/bash

# Enhanced Playwright test runner with comprehensive error checking
set -e

echo "🚀 Starting Flask server with logging..."

# Start the Flask server in the background with output to log file
python web_app.py > logs/webapp.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 15

# Check if server is running
if curl -s http://127.0.0.1:5000 > /dev/null; then
    echo "✅ Server is running"
    
    # Check for any startup errors in the log
    echo "📋 Checking for startup errors..."
    if grep -i "error\|exception\|traceback" logs/webapp.log; then
        echo "⚠️ Found errors in startup log"
    else
        echo "✅ No startup errors found"
    fi
    
    # Run the Playwright test with enhanced logging
    echo "🧪 Running Playwright test with error capture..."
    cd tests/playwright
    
    # Capture console errors and network failures
    timeout 120 npx playwright test tests/0110_10_30_test_admin_platform_management.js \
        --config=0830_17_52_playwright.config.js \
        --reporter=line \
        2>&1 | tee ../../logs/playwright.log
    
    TEST_EXIT_CODE=${PIPESTATUS[0]}
    
    echo "📊 Test completed with exit code: $TEST_EXIT_CODE"
    
    # Check webapp.log for errors during test execution
    echo "📋 Checking webapp.log for runtime errors..."
    if tail -n 100 ../../logs/webapp.log | grep -i "error\|exception\|traceback"; then
        echo "⚠️ Found runtime errors in webapp.log"
    else
        echo "✅ No runtime errors in webapp.log"
    fi
    
    # Check for specific route errors
    echo "📋 Checking for route-related errors..."
    if tail -n 100 ../../logs/webapp.log | grep -i "404\|not found\|route"; then
        echo "⚠️ Found route-related issues"
    else
        echo "✅ No route issues found"
    fi
    
    cd ../..
    
    echo "🛑 Stopping server..."
    kill $SERVER_PID
    
    # Show summary
    echo "📋 Test Summary:"
    echo "- Server PID: $SERVER_PID"
    echo "- Test Exit Code: $TEST_EXIT_CODE"
    echo "- Logs available in: logs/webapp.log and logs/playwright.log"
    
    exit $TEST_EXIT_CODE
else
    echo "❌ Server failed to start"
    kill $SERVER_PID 2>/dev/null
    
    # Show startup errors
    echo "📋 Startup errors:"
    cat logs/webapp.log
    
    exit 1
fi
