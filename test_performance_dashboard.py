#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright
import time

async def test_performance_dashboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        console_messages = []
        
        def handle_console(msg):
            console_messages.append(f"{msg.type}: {msg.text}")
            print(f"Console {msg.type}: {msg.text}")
        
        page.on("console", handle_console)
        
        try:
            print("🔍 Testing Performance Dashboard...")
            
            # Navigate to login page
            await page.goto('http://127.0.0.1:5000/login')
            await page.wait_for_load_state('networkidle')
            
            # Login with admin credentials
            print("🔐 Logging in as admin...")
            
            # Get CSRF token
            csrf_token = await page.get_attribute('input[name="csrf_token"]', 'value')
            print(f"CSRF token: {csrf_token[:20]}..." if csrf_token else "No CSRF token found")
            
            await page.fill('input[name="username_or_email"]', 'admin')
            await page.fill('input[name="password"]', 'BEw@e3pA*!Gv{(x9umOwIndQ')
            
            # Wait for login to complete and redirect
            await page.click('text=Login')
            await page.wait_for_load_state('networkidle')
            
            print(f"After login URL: {page.url}")
            
            # Navigate to performance dashboard
            print("📊 Navigating to performance dashboard...")
            await page.goto('http://127.0.0.1:5000/admin/performance')
            await page.wait_for_load_state('networkidle')
            
            print(f"Performance page URL: {page.url}")
            
            # Wait for charts to initialize
            await asyncio.sleep(5)
            
            # Check console messages for chart loading issues
            print("🔍 Console messages during chart loading:")
            for msg in console_messages:
                print(f"  {msg}")
            
            # Check if charts exist
            throughput_chart = await page.query_selector('#throughputChart')
            resource_chart = await page.query_selector('#resourceChart')
            
            print(f"Throughput chart found: {throughput_chart is not None}")
            print(f"Resource chart found: {resource_chart is not None}")
            
            # Take screenshot
            await page.screenshot(path='performance_dashboard_test.png')
            print("📸 Screenshot saved")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            await page.screenshot(path='error_screenshot.png')
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_performance_dashboard())
