# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple test to verify HealthChecker can be imported and initialized
"""

def test_health_checker_import():
    """Test that HealthChecker can be imported and initialized"""
    print("=== Testing HealthChecker Import and Initialization ===")
    
    try:
        # Test import
        print("1. Testing HealthChecker import...")
        from health_check import HealthChecker
        print("✅ HealthChecker imported successfully")
        
        # Test config import
        print("2. Testing Config import...")
        from config import Config
        config = Config()
        print("✅ Config initialized successfully")
        
        # Test database manager import
        print("3. Testing DatabaseManager import...")
        from app.core.database.core.database_manager import DatabaseManager
        db_manager = DatabaseManager(config)
        print("✅ DatabaseManager initialized successfully")
        
        # Test HealthChecker initialization
        print("4. Testing HealthChecker initialization...")
        health_checker = HealthChecker(config, db_manager)
        print("✅ HealthChecker initialized successfully")
        
        # Test that it has the expected attributes
        print("5. Testing HealthChecker attributes...")
        assert hasattr(health_checker, 'config'), "HealthChecker missing config attribute"
        assert hasattr(health_checker, 'db_manager'), "HealthChecker missing db_manager attribute"
        assert hasattr(health_checker, 'responsiveness_config'), "HealthChecker missing responsiveness_config attribute"
        print("✅ HealthChecker has expected attributes")
        
        # Test that responsiveness config is loaded
        print("6. Testing responsiveness configuration...")
        responsiveness_config = health_checker.responsiveness_config
        assert hasattr(responsiveness_config, 'memory_warning_threshold'), "Missing memory_warning_threshold"
        assert hasattr(responsiveness_config, 'memory_critical_threshold'), "Missing memory_critical_threshold"
        assert hasattr(responsiveness_config, 'cpu_warning_threshold'), "Missing cpu_warning_threshold"
        assert hasattr(responsiveness_config, 'cpu_critical_threshold'), "Missing cpu_critical_threshold"
        print("✅ Responsiveness configuration loaded successfully")
        
        print("\n🎉 All tests passed! HealthChecker is ready to use.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

if __name__ == "__main__":
    success = test_health_checker_import()
    if success:
        print("\n✅ HealthChecker is properly configured!")
    else:
        print("\n❌ HealthChecker configuration has issues!")