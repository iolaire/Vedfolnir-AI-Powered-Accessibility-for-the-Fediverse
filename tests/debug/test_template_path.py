# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify template path configuration
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_template_paths():
    """Test that template paths are correctly configured"""
    print("=== Testing Template Path Configuration ===")
    
    # Check if admin template exists
    admin_template_path = os.path.join('admin', 'templates', 'user_management.html')
    if os.path.exists(admin_template_path):
        print(f"✅ Admin template exists at: {admin_template_path}")
    else:
        print(f"❌ Admin template not found at: {admin_template_path}")
        return False
    
    # Check if base admin template exists
    base_admin_template_path = os.path.join('admin', 'templates', 'base_admin.html')
    if os.path.exists(base_admin_template_path):
        print(f"✅ Base admin template exists at: {base_admin_template_path}")
    else:
        print(f"❌ Base admin template not found at: {base_admin_template_path}")
        return False
    
    return True

def test_blueprint_configuration():
    """Test that the admin blueprint is configured correctly"""
    print("\n=== Testing Blueprint Configuration ===")
    
    try:
        from flask import Flask
        from app.blueprints.admin import admin_bp
        
        # Create a test app
        app = Flask(__name__)
        app.register_blueprint(admin_bp)
        
        # Check blueprint configuration
        print(f"✅ Admin blueprint registered successfully")
        print(f"   Template folder: {admin_bp.template_folder}")
        print(f"   Static folder: {admin_bp.static_folder}")
        print(f"   URL prefix: {admin_bp.url_prefix}")
        
        # Check if template folder exists
        if os.path.exists(admin_bp.template_folder):
            print(f"✅ Template folder exists: {admin_bp.template_folder}")
        else:
            print(f"❌ Template folder not found: {admin_bp.template_folder}")
            return False
        
        # Check if user_management.html exists in template folder
        user_mgmt_template = os.path.join(admin_bp.template_folder, 'user_management.html')
        if os.path.exists(user_mgmt_template):
            print(f"✅ User management template found: {user_mgmt_template}")
        else:
            print(f"❌ User management template not found: {user_mgmt_template}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Blueprint configuration test failed: {e}")
        return False

def test_template_rendering():
    """Test template rendering in isolation"""
    print("\n=== Testing Template Rendering ===")
    
    try:
        from flask import Flask, render_template_string
        from app.blueprints.admin import admin_bp
        
        # Create a test app
        app = Flask(__name__)
        app.register_blueprint(admin_bp)
        
        with app.app_context():
            # Try to render a simple template string first
            simple_template = "Hello {{ name }}!"
            result = render_template_string(simple_template, name="World")
            if result == "Hello World!":
                print("✅ Basic template rendering works")
            else:
                print("❌ Basic template rendering failed")
                return False
            
            # Try to check if the template exists and can be loaded
            try:
                from jinja2 import TemplateNotFound
                template_loader = app.jinja_loader
                
                # Check if we can find the template
                template_source = template_loader.get_source(app.jinja_env, 'user_management.html')
                print("✅ User management template can be loaded by Jinja2")
                return True
                
            except TemplateNotFound as e:
                print(f"❌ Template not found by Jinja2: {e}")
                return False
            except Exception as e:
                print(f"❌ Template loading error: {e}")
                return False
        
    except Exception as e:
        print(f"❌ Template rendering test failed: {e}")
        return False

def main():
    """Run all template path tests"""
    print("Testing Template Path Configuration")
    print("=" * 40)
    
    tests = [
        test_template_paths,
        test_blueprint_configuration,
        test_template_rendering
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 40)
    print("Test Results Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All template path tests passed!")
        return True
    else:
        print("❌ Some template path tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)