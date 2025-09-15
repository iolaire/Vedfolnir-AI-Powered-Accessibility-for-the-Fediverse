#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSP Configuration Checker

This script checks your CSP configuration and provides recommendations
for optimal security and compatibility.
"""

import os
import sys
import requests
from urllib.parse import urljoin

def check_environment_variables():
    """Check CSP-related environment variables"""
    print("=== Environment Variables ===")
    
    env_vars = {
        'FLASK_ENV': os.getenv('FLASK_ENV', 'Not set'),
        'FLASK_DEBUG': os.getenv('FLASK_DEBUG', 'Not set'),
        'CSP_PERMISSIVE': os.getenv('CSP_PERMISSIVE', 'Not set'),
        'CSP_STRICT_MODE': os.getenv('CSP_STRICT_MODE', 'Not set'),
    }
    
    for var, value in env_vars.items():
        print(f"  {var}: {value}")
    
    # Recommendations
    print("\n--- Recommendations ---")
    
    if os.getenv('FLASK_ENV') == 'development':
        print("✅ Development mode detected - CSP will be more permissive")
    elif os.getenv('FLASK_DEBUG') == '1':
        print("✅ Debug mode detected - CSP will be more permissive")
    else:
        print("⚠️  Production mode - CSP will be strict")
        print("   Consider setting CSP_PERMISSIVE=1 for testing")
    
    if os.getenv('CSP_STRICT_MODE') == '1':
        print("⚠️  Strict CSP mode enabled - may cause more violations")
        print("   Consider disabling for initial testing")

def test_csp_headers(base_url="http://127.0.0.1:5000"):
    """Test CSP headers from the application"""
    print(f"\n=== CSP Headers Test ===")
    print(f"Testing: {base_url}")
    
    try:
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Application is responding")
        else:
            print(f"⚠️  Application returned status: {response.status_code}")
        
        # Check CSP header
        csp_header = response.headers.get('Content-Security-Policy')
        if csp_header:
            print("✅ CSP header is present")
            print(f"   Length: {len(csp_header)} characters")
            
            # Check for key directives
            directives = {
                'script-src': 'script-src' in csp_header,
                'script-src-elem': 'script-src-elem' in csp_header,
                'style-src': 'style-src' in csp_header,
                'connect-src': 'connect-src' in csp_header,
                'nonce': 'nonce-' in csp_header,
                'unsafe-inline': "'unsafe-inline'" in csp_header,
                'report-uri': 'report-uri' in csp_header,
            }
            
            print("\n--- CSP Directives ---")
            for directive, present in directives.items():
                status = "✅" if present else "❌"
                print(f"  {status} {directive}")
            
            # Check for Safari compatibility
            if directives['script-src-elem'] and directives['unsafe-inline']:
                print("\n✅ Safari compatibility: script-src-elem with unsafe-inline present")
            else:
                print("\n⚠️  Safari compatibility: Missing script-src-elem or unsafe-inline")
            
            # Show full CSP policy (truncated)
            print(f"\n--- CSP Policy (first 200 chars) ---")
            print(f"  {csp_header[:200]}...")
            
        else:
            print("❌ No CSP header found")
            print("   Check if security middleware is properly initialized")
        
        # Check other security headers
        security_headers = {
            'X-Content-Type-Options': response.headers.get('X-Content-Type-Options'),
            'X-Frame-Options': response.headers.get('X-Frame-Options'),
            'X-XSS-Protection': response.headers.get('X-XSS-Protection'),
            'Strict-Transport-Security': response.headers.get('Strict-Transport-Security'),
        }
        
        print(f"\n--- Other Security Headers ---")
        for header, value in security_headers.items():
            if value:
                print(f"  ✅ {header}: {value}")
            else:
                print(f"  ❌ {header}: Not present")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to application")
        print("   Make sure the web application is running on the specified URL")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        print("   Application may be slow to respond")
    except Exception as e:
        print(f"❌ Error testing headers: {e}")

def test_csp_report_endpoint(base_url="http://127.0.0.1:5000"):
    """Test the CSP report endpoint"""
    print(f"\n=== CSP Report Endpoint Test ===")
    
    report_url = urljoin(base_url, "/api/csp-report")
    print(f"Testing: {report_url}")
    
    # Sample CSP report
    sample_report = {
        "csp-report": {
            "document-uri": f"{base_url}/test",
            "referrer": "",
            "violated-directive": "script-src-elem",
            "effective-directive": "script-src-elem",
            "original-policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
            "disposition": "report",
            "blocked-uri": "inline",
            "status-code": 200,
            "script-sample": ""
        }
    }
    
    try:
        response = requests.post(
            report_url,
            json=sample_report,
            headers={'Content-Type': 'application/csp-report'},
            timeout=10
        )
        
        if response.status_code == 204:
            print("✅ CSP report endpoint is working correctly")
        else:
            print(f"⚠️  CSP report endpoint returned status: {response.status_code}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to CSP report endpoint")
    except Exception as e:
        print(f"❌ Error testing CSP report endpoint: {e}")

def check_nginx_config():
    """Check for common Nginx configuration issues"""
    print(f"\n=== Nginx Configuration Check ===")
    
    nginx_config_path = "/opt/homebrew/etc/nginx/servers/vedfolnir.org.conf"
    
    print(f"Expected config location: {nginx_config_path}")
    print("⚠️  Cannot directly access Nginx config from this script")
    print()
    print("--- Common Nginx CSP Issues ---")
    print("1. Duplicate CSP headers (Nginx + Flask)")
    print("   ❌ DON'T add 'add_header Content-Security-Policy' in Nginx")
    print("   ✅ Let Flask handle CSP headers exclusively")
    print()
    print("2. Missing proxy headers")
    print("   ✅ Ensure proxy_set_header X-Forwarded-Proto $scheme;")
    print("   ✅ Ensure proxy_set_header Host $host;")
    print()
    print("3. WebSocket support")
    print("   ✅ Ensure proxy_set_header Upgrade $http_upgrade;")
    print("   ✅ Ensure proxy_set_header Connection 'upgrade';")
    print()
    print("📄 See nginx_vedfolnir_recommended.conf for complete config")

def main():
    """Main function"""
    print("CSP Configuration Checker")
    print("=" * 50)
    
    # Check environment
    check_environment_variables()
    
    # Test application
    base_url = "http://127.0.0.1:5000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    test_csp_headers(base_url)
    test_csp_report_endpoint(base_url)
    check_nginx_config()
    
    print(f"\n=== Summary ===")
    print("Configuration check complete.")
    print()
    print("Next steps:")
    print("1. Fix any issues identified above")
    print("2. Restart services if changes were made")
    print("3. Run debug_csp_violations.py to analyze current violations")
    print("4. Test in different browsers (Safari, Chrome, Firefox)")

if __name__ == '__main__':
    main()