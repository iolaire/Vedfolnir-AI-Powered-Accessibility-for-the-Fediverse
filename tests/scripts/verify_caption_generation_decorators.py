# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Verification script for caption generation route decorators
Location: tests/scripts/verify_caption_generation_decorators.py
"""

import sys
import os
import re

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def verify_caption_generation_decorators():
    """Verify that the caption generation route has the correct decorators"""
    
    print("=== Caption Generation Route Decorator Verification ===")
    
    # Read the web_app.py file
    try:
        with open('web_app.py', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ web_app.py file not found")
        return False
    
    # Find the caption generation route
    pattern = r'@app\.route\(\'/caption_generation\'\)(.*?)def caption_generation\(\):'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("❌ Caption generation route not found")
        return False
    
    route_decorators = match.group(1)
    print("Found caption generation route with decorators:")
    print(route_decorators)
    
    # Check for required decorators
    required_decorators = [
        '@login_required',
        '@platform_required',
        '@rate_limit',
        '@with_session_error_handling'
    ]
    
    missing_decorators = []
    found_decorators = []
    
    for decorator in required_decorators:
        if decorator in route_decorators:
            found_decorators.append(decorator)
            print(f"✅ Found: {decorator}")
        else:
            missing_decorators.append(decorator)
            print(f"❌ Missing: {decorator}")
    
    # Check decorator order (platform_required should be after login_required)
    login_pos = route_decorators.find('@login_required')
    platform_pos = route_decorators.find('@platform_required')
    
    if login_pos != -1 and platform_pos != -1:
        if platform_pos > login_pos:
            print("✅ Decorator order correct: @platform_required comes after @login_required")
        else:
            print("⚠️  Decorator order issue: @platform_required should come after @login_required")
    
    # Check that platform_required decorator is defined in the file
    if 'def platform_required(f):' in content:
        print("✅ platform_required decorator is defined in web_app.py")
    else:
        print("❌ platform_required decorator definition not found")
    
    # Summary
    if not missing_decorators:
        print("\n✅ All required decorators are present!")
        print("✅ Caption generation route is properly configured with @platform_required")
        return True
    else:
        print(f"\n❌ Missing decorators: {missing_decorators}")
        return False

if __name__ == '__main__':
    success = verify_caption_generation_decorators()
    sys.exit(0 if success else 1)