#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright

async def test_performance_data_loading():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Capture console errors
        js_errors = []
        api_errors = []
        page.on("console", lambda msg: 
            js_errors.append(msg.text) if 'error' in msg.type else None)
        page.on("response", lambda response: 
            api_errors.append(f"{response.status} {response.url}") if response.status >= 400 else None)
        
        try:
            print("=== Testing Performance Data Loading ===")
            
            # Login
            await page.goto("http://localhost:5000/login")
            await page.wait_for_load_state("networkidle")
            
            await page.fill('input[name="username_or_email"]', 'admin')
            await page.fill('input[name="password"]', ')z0p>14_S9>}samLqf0t?{!Y')
            await page.click('input[type="submit"]')
            await page.wait_for_load_state("networkidle")
            
            # Go to performance page
            print("\n1. Loading performance page...")
            await page.goto("http://localhost:5000/admin/performance")
            await page.wait_for_load_state("networkidle")
            
            # Wait for data loading
            await page.wait_for_timeout(5000)
            
            print(f"2. Page loaded: {await page.title()}")
            
            # Check for data elements
            print("\n3. Checking data loading...")
            
            # Check metrics cards
            metrics_cards = await page.query_selector_all('.metric-card, .performance-metric, [data-metric]')
            print(f"Metrics cards found: {len(metrics_cards)}")
            
            # Check for "No data" or error messages
            no_data_elements = await page.query_selector_all('text="No data", text="Error", text="Failed"')
            print(f"No data/error messages: {len(no_data_elements)}")
            
            # Check specific performance data
            system_status = await page.query_selector('.system-status, #system-status')
            if system_status:
                status_text = await system_status.text_content()
                print(f"System status: {status_text[:100]}...")
            else:
                print("❌ System status element not found")
            
            # Check for loading indicators
            loading_elements = await page.query_selector_all('.loading, .spinner, text="Loading"')
            print(f"Loading indicators: {len(loading_elements)}")
            
            # Print JavaScript errors
            print(f"\n4. JavaScript Errors ({len(js_errors)} total):")
            for error in js_errors[:10]:  # Show first 10
                print(f"❌ {error}")
            
            # Print API errors
            print(f"\n5. API Errors ({len(api_errors)} total):")
            for error in api_errors[:10]:  # Show first 10
                print(f"❌ {error}")
            
            # Check if data actually loaded
            print(f"\n6. Data Loading Assessment:")
            if len(metrics_cards) > 0:
                print("✅ Metrics cards present")
            else:
                print("❌ No metrics cards found")
                
            if len(no_data_elements) == 0:
                print("✅ No 'no data' messages")
            else:
                print("❌ Found 'no data' or error messages")
                
            if len(loading_elements) == 0:
                print("✅ No loading indicators (data loaded)")
            else:
                print("⚠️ Still showing loading indicators")
            
        except Exception as e:
            print(f"Test error: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_performance_data_loading())
