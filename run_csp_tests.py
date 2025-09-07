#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSP compliance test runner
"""

import os
import sys
import unittest
import subprocess
import time
from pathlib import Path


def main():
    """Run CSP compliance tests"""
    print("🔒 CSP Compliance Test Runner")
    print("="*50)
    
    # Set environment for CSP testing
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['CSP_STRICT_MODE'] = 'true'
    
    # Run CSP compliance tests
    test_modules = [
        'tests.security.test_strict_csp_compliance',
        'tests.security.test_csp_compliance'
    ]
    
    all_passed = True
    
    for module in test_modules:
        print(f"\n🧪 Running {module}...")
        
        try:
            # Run test module
            result = subprocess.run([
                sys.executable, '-m', 'unittest', module, '-v'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ {module} - PASSED")
            else:
                print(f"❌ {module} - FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {module} - TIMEOUT")
            all_passed = False
        except Exception as e:
            print(f"❌ {module} - ERROR: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ ALL CSP COMPLIANCE TESTS PASSED")
        return 0
    else:
        print("❌ SOME CSP COMPLIANCE TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
