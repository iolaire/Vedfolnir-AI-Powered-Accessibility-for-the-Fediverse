#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix Configuration Metadata

This script fixes existing configurations that have incorrect or missing
category and data_type information by updating them to match the schema.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from config import Config
from database import DatabaseManager
from system_configuration_manager import SystemConfigurationManager
from models import SystemConfiguration, User, UserRole

def main():
    """Fix configuration metadata"""
    print("=== Configuration Metadata Fix ===")
    
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
        
        # Get schema for reference
        schema = config_manager.get_configuration_schema()
        
        # Fix configurations
        print("\n🔧 Fixing configuration metadata...")
        fixed_count = 0
        
        with db_manager.get_session() as session:
            # Get all configurations that need fixing
            all_configs = session.query(SystemConfiguration).all()
            
            for config_record in all_configs:
                schema_info = schema.get(config_record.key)
                
                if schema_info:
                    needs_update = False
                    
                    # Check if category needs fixing
                    expected_category = schema_info.category.value
                    if config_record.category != expected_category:
                        print(f"  Fixing category for {config_record.key}: {config_record.category} → {expected_category}")
                        config_record.category = expected_category
                        needs_update = True
                    
                    # Check if data_type needs fixing
                    expected_data_type = schema_info.data_type.value
                    if config_record.data_type != expected_data_type:
                        print(f"  Fixing data_type for {config_record.key}: {config_record.data_type} → {expected_data_type}")
                        config_record.data_type = expected_data_type
                        needs_update = True
                    
                    # Check if description needs updating
                    if not config_record.description or config_record.description != schema_info.description:
                        print(f"  Updating description for {config_record.key}")
                        config_record.description = schema_info.description
                        needs_update = True
                    
                    # Check if is_sensitive needs updating
                    if config_record.is_sensitive != schema_info.is_sensitive:
                        print(f"  Fixing is_sensitive for {config_record.key}: {config_record.is_sensitive} → {schema_info.is_sensitive}")
                        config_record.is_sensitive = schema_info.is_sensitive
                        needs_update = True
                    
                    if needs_update:
                        config_record.updated_by = admin_user.id
                        fixed_count += 1
                else:
                    print(f"  ⚠️  No schema found for configuration: {config_record.key}")
            
            session.commit()
        
        print(f"\n✅ Fixed {fixed_count} configurations")
        
        # Verify the fix
        print("\n🔍 Verifying fixes...")
        
        with db_manager.get_session() as session:
            maintenance_configs = session.query(SystemConfiguration).filter(
                SystemConfiguration.key.in_(['maintenance_mode', 'maintenance_reason'])
            ).all()
            
            print("Maintenance configurations after fix:")
            for config in maintenance_configs:
                print(f"  {config.key}: category={config.category}, data_type={config.data_type}")
        
        # Test category filtering
        from system_configuration_manager import ConfigurationCategory
        maintenance_configs = config_manager.get_all_configurations(
            admin_user.id, category=ConfigurationCategory.MAINTENANCE, include_sensitive=True
        )
        
        print(f"\nMaintenance category now has {len(maintenance_configs)} configurations:")
        for key, value in maintenance_configs.items():
            print(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)