#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Script to enable strict Content Security Policy for CSS security enhancement testing
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from security.config.strict_csp_config import StrictCSPConfig


def setup_logging(verbose=False):
    """Set up logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def update_security_middleware(project_root, strict_mode=True, report_only=False):
    """Update security middleware to use strict CSP"""
    logger = logging.getLogger(__name__)
    
    security_middleware_path = project_root / "security" / "core" / "security_middleware.py"
    
    if not security_middleware_path.exists():
        logger.error(f"Security middleware not found: {security_middleware_path}")
        return False
    
    try:
        # Read current middleware
        with open(security_middleware_path, 'r') as f:
            content = f.read()
        
        # Create backup
        backup_path = security_middleware_path.with_suffix('.py.backup')
        with open(backup_path, 'w') as f:
            f.write(content)
        logger.info(f"Created backup: {backup_path}")
        
        # Update CSP policy generation
        if strict_mode:
            # Replace the CSP policy generation with strict version
            import re
            
            # Find the CSP policy section
            csp_pattern = re.compile(
                r'(csp_policy = \(\s*)(.*?)(\s*\))',
                re.DOTALL
            )
            
            if report_only:
                new_csp = '''f"default-src 'self'; "
            f"script-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com https://unpkg.com; "
            f"style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net; "  # NO unsafe-inline
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"connect-src 'self' wss: ws:; "
            f"frame-ancestors 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"object-src 'none'; "
            f"media-src 'self'; "
            f"report-uri /api/csp-report"'''
            else:
                new_csp = '''f"default-src 'self'; "
            f"script-src 'self' 'nonce-{csp_nonce}' https://cdn.jsdelivr.net https://cdn.socket.io https://cdnjs.cloudflare.com https://unpkg.com; "
            f"style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net; "  # NO unsafe-inline
            f"img-src 'self' data: https:; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            f"connect-src 'self' wss: ws:; "
            f"frame-ancestors 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'; "
            f"object-src 'none'; "
            f"media-src 'self'; "
            f"upgrade-insecure-requests"'''
            
            # Replace the CSP policy
            new_content = csp_pattern.sub(
                rf'\1{new_csp}\3',
                content
            )
            
            if new_content != content:
                # Add CSP report-only header if requested
                if report_only:
                    # Add report-only header
                    header_pattern = re.compile(
                        r"(response\.headers\['Content-Security-Policy'\] = csp_policy)"
                    )
                    new_content = header_pattern.sub(
                        r"response.headers['Content-Security-Policy-Report-Only'] = csp_policy",
                        new_content
                    )
                
                # Write updated content
                with open(security_middleware_path, 'w') as f:
                    f.write(new_content)
                
                logger.info("✅ Updated security middleware with strict CSP")
                return True
            else:
                logger.warning("⚠️  No CSP policy pattern found to update")
                return False
        
    except Exception as e:
        logger.error(f"❌ Error updating security middleware: {e}")
        return False


def create_csp_test_config(project_root):
    """Create CSP test configuration file"""
    logger = logging.getLogger(__name__)
    
    config_path = project_root / "config_csp_test.py"
    
    config_content = '''# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Configuration for CSP compliance testing
"""

import os
from config import Config


class CSPTestConfig(Config):
    """Configuration with strict CSP enabled for testing"""
    
    # Enable strict CSP testing
    CSP_STRICT_MODE = True
    CSP_REPORT_ONLY = os.environ.get('CSP_REPORT_ONLY', 'false').lower() == 'true'
    
    # Security settings
    SECURITY_CSP_ENABLED = True
    SECURITY_HEADERS_ENABLED = True
    
    # Testing settings
    TESTING = True
    WTF_CSRF_ENABLED = True
    
    @staticmethod
    def init_app(app):
        """Initialize app with CSP testing configuration"""
        Config.init_app(app)
        
        # Enable CSP testing middleware
        from security.config.strict_csp_config import CSPTestingMiddleware
        
        csp_middleware = CSPTestingMiddleware(
            app=app,
            strict_mode=CSPTestConfig.CSP_STRICT_MODE,
            report_only=CSPTestConfig.CSP_REPORT_ONLY
        )
        
        # Store middleware reference for testing
        app.csp_testing_middleware = csp_middleware
'''
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"✅ Created CSP test configuration: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating CSP test config: {e}")
        return False


def create_csp_test_runner(project_root):
    """Create CSP test runner script"""
    logger = logging.getLogger(__name__)
    
    runner_path = project_root / "run_csp_tests.py"
    
    runner_content = '''#!/usr/bin/env python3
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
        print(f"\\n🧪 Running {module}...")
        
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
    
    print("\\n" + "="*50)
    if all_passed:
        print("✅ ALL CSP COMPLIANCE TESTS PASSED")
        return 0
    else:
        print("❌ SOME CSP COMPLIANCE TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
'''
    
    try:
        with open(runner_path, 'w') as f:
            f.write(runner_content)
        
        # Make executable
        os.chmod(runner_path, 0o755)
        
        logger.info(f"✅ Created CSP test runner: {runner_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating CSP test runner: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Enable strict CSP for testing')
    parser.add_argument('--report-only', action='store_true',
                       help='Enable CSP in report-only mode')
    parser.add_argument('--disable', action='store_true',
                       help='Disable strict CSP (restore backup)')
    parser.add_argument('--test', action='store_true',
                       help='Run CSP compliance tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    logger = setup_logging(args.verbose)
    project_root = Path(__file__).parent.parent.parent
    
    logger.info("🔒 CSP Security Enhancement Configuration")
    logger.info(f"Project root: {project_root}")
    
    if args.disable:
        # Restore backup
        security_middleware_path = project_root / "security" / "core" / "security_middleware.py"
        backup_path = security_middleware_path.with_suffix('.py.backup')
        
        if backup_path.exists():
            try:
                with open(backup_path, 'r') as f:
                    content = f.read()
                
                with open(security_middleware_path, 'w') as f:
                    f.write(content)
                
                logger.info("✅ Restored security middleware from backup")
                return 0
                
            except Exception as e:
                logger.error(f"❌ Error restoring backup: {e}")
                return 1
        else:
            logger.error("❌ No backup found to restore")
            return 1
    
    success = True
    
    # Update security middleware
    if not update_security_middleware(project_root, strict_mode=True, report_only=args.report_only):
        success = False
    
    # Create test configuration
    if not create_csp_test_config(project_root):
        success = False
    
    # Create test runner
    if not create_csp_test_runner(project_root):
        success = False
    
    if success:
        logger.info("✅ CSP strict mode configuration complete")
        
        if args.report_only:
            logger.info("ℹ️  CSP is in report-only mode - violations will be logged but not blocked")
        else:
            logger.info("⚠️  CSP is in enforcement mode - violations will be blocked")
        
        logger.info("📋 Next steps:")
        logger.info("  1. Run: python run_csp_tests.py")
        logger.info("  2. Check for CSP violations in logs")
        logger.info("  3. Fix any remaining inline styles")
        logger.info("  4. Test with: python -m unittest tests.security.test_strict_csp_compliance -v")
        
        if args.test:
            logger.info("🧪 Running CSP compliance tests...")
            os.system("python run_csp_tests.py")
        
        return 0
    else:
        logger.error("❌ CSP configuration failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())