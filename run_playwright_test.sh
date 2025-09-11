#!/bin/bash

# Start the Flask server in the background
echo "🚀 Starting Flask server..."
python web_app.py &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 10

# Check if server is running
if curl -s http://127.0.0.1:5000 > /dev/null; then
    echo "✅ Server is running"
    
    # Run the Playwright test
    echo "🧪 Running Playwright test..."
    cd tests/playwright
    timeout 120 npx playwright test tests/0110_10_30_test_admin_platform_management.js --config=0830_17_52_playwright.config.js
    TEST_EXIT_CODE=$?
    
    echo "🛑 Stopping server..."
    kill $SERVER_PID
    
    exit $TEST_EXIT_CODE
else
    echo "❌ Server failed to start"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi
