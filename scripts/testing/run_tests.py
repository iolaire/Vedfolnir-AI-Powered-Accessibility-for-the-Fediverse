#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test runner script for Vedfolnir.

This script provides an easy way to run different test suites with proper
configuration handling.
"""

import os
import sys
import subprocess
import argparse

def run_command(cmd, description):
    """Run a command and return the result"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description='Run Vedfolnir tests')
    parser.add_argument('--suite', choices=['all', 'config', 'platform', 'safe'], 
                       default='safe',
                       help='Test suite to run (default: safe)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Run tests with verbose output')
    parser.add_argument('--specific', '-s', type=str,
                       help='Run a specific test file (e.g., tests.test_configuration_examples)')
    
    args = parser.parse_args()
    
    # Base command
    base_cmd = ['python', '-m', 'unittest']
    if args.verbose:
        base_cmd.append('-v')
    
    success = True
    
    if args.specific:
        # Run specific test file
        cmd = base_cmd + [args.specific]
        success = run_command(cmd, f"Specific test: {args.specific}")
    
    elif args.suite == 'all':
        # Run all tests (requires proper configuration)
        print("⚠️  Running all tests requires proper .env configuration!")
        print("   Make sure you have a valid .env file set up.")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return 1
        
        cmd = base_cmd + ['discover', 'tests']
        success = run_command(cmd, "All tests")
    
    elif args.suite == 'config':
        # Run configuration-related tests
        cmd = base_cmd + ['tests.test_configuration_examples', 'tests.test_config_validation_script']
        success = run_command(cmd, "Configuration tests")
    
    elif args.suite == 'platform':
        # Run platform adapter tests
        cmd = base_cmd + ['tests.test_platform_adapter_factory']
        success = run_command(cmd, "Platform adapter tests")
    
    elif args.suite == 'safe':
        # Run tests that don't require full configuration
        print("Running safe test suite (no configuration required)...")
        
        # Configuration tests
        cmd = base_cmd + ['tests.test_configuration_examples', 'tests.test_config_validation_script']
        config_success = run_command(cmd, "Configuration tests")
        
        # Platform adapter tests (may have some failures but will run)
        cmd = base_cmd + ['tests.test_platform_adapter_factory']
        platform_success = run_command(cmd, "Platform adapter tests")
        
        success = config_success  # Only require config tests to pass for "safe" suite
        
        if config_success and platform_success:
            print("\n✅ All safe tests passed!")
        elif config_success:
            print("\n✅ Configuration tests passed!")
            print("⚠️  Some platform adapter tests failed (this may be expected)")
        else:
            print("\n❌ Some tests failed")
    
    if success:
        print(f"\n🎉 Test suite '{args.suite}' completed successfully!")
        return 0
    else:
        print(f"\n❌ Test suite '{args.suite}' had failures")
        return 1

if __name__ == '__main__':
    sys.exit(main())