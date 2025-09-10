#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Initialize System Configurations

This script initializes all default system configurations in the database.
Run this after setting up the database to ensure all configuration options
are available in the admin interface.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from app.core.configuration.core.system_configuration_manager import SystemConfigurationManager
from models import User, UserRole

def main():
    """Initialize default system configurations"""
    print("=== System Configuration Initialization ===")
    
    # Load environment
    load_dotenv()
    
    try:
        # Initialize components
        config = Config()
        db_manager = DatabaseManager(config)
        config_manager = SystemConfigurationManager(db_manager)
        
        print("✅ Components initialized successfully")
        
        # Find an admin user
        with db_manager.get_session() as session:
            admin_user = session.query(User).filter_by(role=UserRole.ADMIN).first()
            
            if not admin_user:
                print("❌ No admin user found. Please create an admin user first.")
                return False
            
            print(f"✅ Found admin user: {admin_user.username}")
        
        # Initialize default configurations
        print("\n📝 Initializing default configurations...")
        created_count, messages = config_manager.initialize_default_configurations(admin_user.id)
        
        print(f"\n✅ Initialization completed!")
        print(f"   Created: {created_count} configurations")
        
        if messages:
            print("\n📋 Details:")
            for message in messages:
                print(f"   • {message}")
        
        # Verify configurations are loaded
        print("\n🔍 Verifying configurations...")
        all_configs = config_manager.get_all_configurations(admin_user.id, include_sensitive=True)
        
        print(f"✅ Total configurations available: {len(all_configs)}")
        
        # Show configuration summary by category
        from app.core.configuration.core.system_configuration_manager import ConfigurationCategory
        
        print("\n📊 Configuration Summary by Category:")
        for category in ConfigurationCategory:
            category_configs = config_manager.get_all_configurations(
                admin_user.id, category=category, include_sensitive=True
            )
            print(f"   {category.value.title()}: {len(category_configs)} configurations")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)