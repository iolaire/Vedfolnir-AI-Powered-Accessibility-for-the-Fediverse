#!/usr/bin/env python3

import asyncio
from playwright.async_api import async_playwright
import json

async def test_console_errors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        console_messages = []
        network_errors = []
        
        def handle_console(msg):
            console_messages.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            })
            print(f"Console {msg.type}: {msg.text}")
        
        def handle_response(response):
            if response.status >= 400:
                network_errors.append({
                    'url': response.url,
                    'status': response.status,
                    'status_text': response.status_text
                })
                print(f"Network Error: {response.status} {response.url}")
        
        page.on("console", handle_console)
        page.on("response", handle_response)
        
        try:
            print("🔍 Testing Performance Dashboard Console Errors...")
            
            # Navigate directly to performance dashboard (will redirect to login)
            await page.goto('http://127.0.0.1:5000/admin/performance')
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            print(f"📊 Current URL: {page.url}")
            
            # Wait a bit to capture any async console messages
            await asyncio.sleep(5)
            
            print(f"\n📝 Console Messages ({len(console_messages)}):")
            for msg in console_messages:
                print(f"  {msg['type']}: {msg['text']}")
            
            print(f"\n🌐 Network Errors ({len(network_errors)}):")
            for err in network_errors:
                print(f"  {err['status']}: {err['url']}")
            
            # Check if we can access the API endpoints directly
            print(f"\n🔍 Testing API Endpoints:")
            endpoints = [
                '/admin/api/performance/metrics',
                '/admin/api/performance/health',
                '/admin/api/performance/trends?hours=24'
            ]
            
            for endpoint in endpoints:
                try:
                    response = await page.goto(f'http://127.0.0.1:5000{endpoint}')
                    print(f"  {endpoint}: {response.status}")
                    if response.status == 200:
                        text = await response.text()
                        print(f"    Response: {text[:100]}...")
                except Exception as e:
                    print(f"  {endpoint}: Error - {e}")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_console_errors())
