#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session consolidation validation script for Task 19

Validates that Flask session usage has been eliminated and unified session system works.
"""

import os
import re
import sys
from pathlib import Path

def scan_flask_session_usage():
    """Scan for remaining Flask session usage"""
    print("🔍 Scanning for Flask session usage...")
    
    project_root = Path('.')
    violations = []
    
    # Patterns that indicate Flask session usage
    flask_session_patterns = [
        r'from flask import.*session',
        r'session\[',
        r'session\.get\(',
        r'session\.clear\(',
        r'session\.pop\(',
    ]
    
    # Files to exclude (legacy/test files)
    exclude_patterns = [
        r'.*test.*flask.*session.*',
        r'.*legacy.*',
        r'.*deprecated.*',
        r'.*docs.*session-management-api\.md',
        r'.*docs.*session-management-examples\.md', 
        r'.*docs.*session-management-troubleshooting\.md',
        r'.*\.git.*',
        r'.*__pycache__.*',
    ]
    
    for py_file in project_root.rglob('*.py'):
        # Skip excluded files
        if any(re.search(pattern, str(py_file)) for pattern in exclude_patterns):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in flask_session_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Check for false positives
                        if not is_false_positive(line):
                            violations.append({
                                'file': str(py_file),
                                'line': line_num,
                                'content': line.strip()
                            })
        except Exception as e:
            print(f"  ⚠ Error scanning {py_file}: {e}")
    
    return violations

def is_false_positive(line):
    """Check if line is a false positive"""
    false_positives = [
        'database_session',
        'db_session',
        'session_manager',
        'unified_session',
        'get_session(',
        'session_scope',
        'request_session',
        'session_id',
        'session_context',
        '# DEPRECATED',
        '# LEGACY',
        'aiohttp',
        'requests.Session',
        'session.get(url',  # HTTP session
    ]
    
    return any(indicator in line.lower() for indicator in false_positives)

def check_unified_session_components():
    """Check that unified session components exist"""
    print("🔧 Checking unified session components...")
    
    required_files = [
        'unified_session_manager.py',
        'session_cookie_manager.py', 
        'database_session_middleware.py',
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    return missing_files

def check_database_session_middleware_usage():
    """Check that Redis session middleware functions are used"""
    print("📡 Checking Redis session middleware usage...")
    
    # Look for usage of middleware functions
    middleware_functions = [
        'get_current_session_context',
        'get_current_user_id', 
        'get_current_platform_id',
        'is_session_authenticated',
    ]
    
    usage_found = {}
    for func in middleware_functions:
        usage_found[func] = []
    
    for py_file in Path('.').rglob('*.py'):
        if 'test' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for func in middleware_functions:
                if func in content:
                    usage_found[func].append(str(py_file))
        except:
            continue
    
    return usage_found

def validate_session_consolidation():
    """Main validation function"""
    print("🚀 Session Consolidation Validation (Task 19)")
    print("=" * 50)
    
    all_passed = True
    
    # 1. Check Flask session elimination
    violations = scan_flask_session_usage()
    if violations:
        print(f"❌ Flask session usage found ({len(violations)} violations)")
        # Show first few violations
        for violation in violations[:5]:
            print(f"   {violation['file']}:{violation['line']} - {violation['content']}")
        if len(violations) > 5:
            print(f"   ... and {len(violations) - 5} more")
        all_passed = False
    else:
        print("✅ No Flask session usage found")
    
    # 2. Check unified components exist
    missing_files = check_unified_session_components()
    if missing_files:
        print(f"❌ Missing unified session components: {missing_files}")
        all_passed = False
    else:
        print("✅ All unified session components present")
    
    # 3. Check middleware usage
    usage = check_database_session_middleware_usage()
    middleware_used = any(files for files in usage.values())
    if middleware_used:
        print("✅ Redis session middleware functions in use")
        for func, files in usage.items():
            if files:
                print(f"   {func}: {len(files)} files")
    else:
        print("⚠ Redis session middleware functions not found in use")
    
    # 4. Basic import test
    try:
        from unified_session_manager import UnifiedSessionManager
        from session_cookie_manager import SessionCookieManager
        from redis_session_middleware import get_current_session_context
        print("✅ Unified session components can be imported")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ VALIDATION PASSED - Session consolidation appears successful")
        return True
    else:
        print("❌ VALIDATION FAILED - Issues found with session consolidation")
        return False

if __name__ == '__main__':
    # Change to project root
    os.chdir(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    success = validate_session_consolidation()
    sys.exit(0 if success else 1)