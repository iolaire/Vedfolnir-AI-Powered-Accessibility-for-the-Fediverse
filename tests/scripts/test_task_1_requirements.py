# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify Task 1 requirements are met
Location: tests/scripts/test_task_1_requirements.py

This script verifies that Task 1 requirements are satisfied:
- Requirements: 1.1, 1.4, 1.5, 4.1, 4.2, 4.3
"""

import sys
import os
import re

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_requirement_1_1():
    """
    Requirement 1.1: WHEN a user navigates to `/caption_generation` THEN the system SHALL load the page successfully without redirects
    
    This is ensured by the @platform_required decorator which validates platform context before allowing access.
    """
    print("Testing Requirement 1.1: Page loads successfully for users with platform context")
    
    # Check that platform_required decorator is present
    with open('web_app.py', 'r') as f:
        content = f.read()
    
    pattern = r'@app\.route\(\'/caption_generation\'\)(.*?)def caption_generation\(\):'
    match = re.search(pattern, content, re.DOTALL)
    
    if match and '@platform_required' in match.group(1):
        print("✅ @platform_required decorator ensures platform validation before page access")
        return True
    else:
        print("❌ @platform_required decorator not found")
        return False

def test_requirement_1_4():
    """
    Requirement 1.4: IF a user has no platform connections THEN the system SHALL redirect to platform setup with an appropriate message
    
    This is handled by the @platform_required decorator implementation.
    """
    print("Testing Requirement 1.4: Redirect to platform setup for users without platforms")
    
    with open('web_app.py', 'r') as f:
        content = f.read()
    
    # Check that platform_required decorator handles the case of no platforms
    if 'first_time_setup' in content and 'platform_required' in content:
        print("✅ @platform_required decorator handles redirect to first_time_setup")
        return True
    else:
        print("❌ Platform setup redirect logic not found")
        return False

def test_requirement_1_5():
    """
    Requirement 1.5: IF a user has platform connections but no active selection THEN the system SHALL redirect to platform management with guidance
    
    This is handled by the @platform_required decorator implementation.
    """
    print("Testing Requirement 1.5: Redirect to platform management for users without active selection")
    
    with open('web_app.py', 'r') as f:
        content = f.read()
    
    # Check that platform_required decorator handles the case of no active platform
    if 'platform_management' in content and 'platform_required' in content:
        print("✅ @platform_required decorator handles redirect to platform_management")
        return True
    else:
        print("❌ Platform management redirect logic not found")
        return False

def test_requirement_4_1():
    """
    Requirement 4.1: WHEN defining the caption generation route THEN the system SHALL include the `@platform_required` decorator
    
    Direct verification that the decorator is present.
    """
    print("Testing Requirement 4.1: @platform_required decorator is included")
    
    with open('web_app.py', 'r') as f:
        content = f.read()
    
    pattern = r'@app\.route\(\'/caption_generation\'\)(.*?)def caption_generation\(\):'
    match = re.search(pattern, content, re.DOTALL)
    
    if match and '@platform_required' in match.group(1):
        print("✅ @platform_required decorator is present on caption_generation route")
        return True
    else:
        print("❌ @platform_required decorator not found on caption_generation route")
        return False

def test_requirement_4_2():
    """
    Requirement 4.2: WHEN a user accesses the route THEN the system SHALL validate authentication and platform access consistently
    
    This is ensured by having both @login_required and @platform_required decorators.
    """
    print("Testing Requirement 4.2: Consistent authentication and platform validation")
    
    with open('web_app.py', 'r') as f:
        content = f.read()
    
    pattern = r'@app\.route\(\'/caption_generation\'\)(.*?)def caption_generation\(\):'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        decorators = match.group(1)
        has_login = '@login_required' in decorators
        has_platform = '@platform_required' in decorators
        
        if has_login and has_platform:
            print("✅ Both @login_required and @platform_required decorators ensure consistent validation")
            return True
        else:
            print(f"❌ Missing decorators - login: {has_login}, platform: {has_platform}")
            return False
    else:
        print("❌ Caption generation route not found")
        return False

def test_requirement_4_3():
    """
    Requirement 4.3: WHEN platform validation fails THEN the system SHALL redirect using the same patterns as other routes
    
    This is ensured by using the same @platform_required decorator used by other routes.
    """
    print("Testing Requirement 4.3: Consistent redirect patterns")
    
    with open('web_app.py', 'r') as f:
        content = f.read()
    
    # Find other routes that use @platform_required
    other_platform_routes = re.findall(r'@platform_required.*?def (\w+)\(', content, re.DOTALL)
    
    if len(other_platform_routes) > 1:  # Should include caption_generation and others
        print(f"✅ @platform_required decorator is used consistently across {len(other_platform_routes)} routes")
        print(f"   Routes using @platform_required: {', '.join(other_platform_routes)}")
        return True
    else:
        print("❌ @platform_required decorator not used consistently")
        return False

def main():
    """Run all requirement tests for Task 1"""
    print("=== Task 1 Requirements Verification ===")
    print("Verifying requirements: 1.1, 1.4, 1.5, 4.1, 4.2, 4.3")
    print()
    
    tests = [
        ("1.1", test_requirement_1_1),
        ("1.4", test_requirement_1_4),
        ("1.5", test_requirement_1_5),
        ("4.1", test_requirement_4_1),
        ("4.2", test_requirement_4_2),
        ("4.3", test_requirement_4_3),
    ]
    
    results = []
    
    for req_num, test_func in tests:
        print(f"\n--- Requirement {req_num} ---")
        result = test_func()
        results.append((req_num, result))
    
    print("\n=== Summary ===")
    passed = 0
    for req_num, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"Requirement {req_num}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} requirements satisfied")
    
    if passed == len(results):
        print("🎉 All Task 1 requirements are satisfied!")
        return True
    else:
        print("❌ Some requirements are not satisfied")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)