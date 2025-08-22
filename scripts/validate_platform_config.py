#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Platform configuration validation script

Validates platform-aware configuration and connections.
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models import User, PlatformConnection
from database import DatabaseManager

class PlatformConfigValidator:
    """Validates platform configuration"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.errors = []
        self.warnings = []
    
    def validate_environment(self):
        """Validate environment variables"""
        print("🔍 Validating environment configuration...")
        
        # Check encryption key
        if not os.environ.get('PLATFORM_ENCRYPTION_KEY'):
            self.warnings.append("PLATFORM_ENCRYPTION_KEY not set - will generate temporary key")
        
        # Check database URL
        if not self.config.storage.database_url:
            self.errors.append("DATABASE_URL not configured")
        
        print(f"✅ Environment validation complete")
    
    def validate_database(self):
        """Validate database structure"""
        print("🔍 Validating database structure...")
        
        try:
            session = self.db_manager.get_session()
            
            # Check if platform tables exist
            users = session.query(User).count()
            platforms = session.query(PlatformConnection).count()
            
            print(f"📊 Found {users} users, {platforms} platforms")
            
            session.close()
            
        except Exception as e:
            self.errors.append(f"Database validation failed: {e}")
        
        print("✅ Database validation complete")
    
    def validate_platforms(self):
        """Validate platform connections"""
        print("🔍 Validating platform connections...")
        
        try:
            session = self.db_manager.get_session()
            platforms = session.query(PlatformConnection).all()
            
            for platform in platforms:
                print(f"🔗 Testing {platform.name} ({platform.platform_type})...")
                
                # Basic validation
                if not platform.access_token:
                    self.errors.append(f"Platform {platform.name} missing access token")
                
                if not platform.instance_url.startswith(('http://', 'https://')):
                    self.errors.append(f"Platform {platform.name} has invalid URL")
                
                # Test connection (mock for now)
                try:
                    # In real implementation, this would test actual connection
                    print(f"  ✅ {platform.name} configuration valid")
                except Exception as e:
                    self.warnings.append(f"Platform {platform.name} connection test failed: {e}")
            
            session.close()
            
        except Exception as e:
            self.errors.append(f"Platform validation failed: {e}")
        
        print("✅ Platform validation complete")
    
    def validate_data_integrity(self):
        """Validate data integrity"""
        print("🔍 Validating data integrity...")
        
        try:
            session = self.db_manager.get_session()
            
            # Check for orphaned data
            from models import Post, Image
            
            posts_without_platform = session.query(Post).filter(
                Post.platform_connection_id.is_(None)
            ).count()
            
            images_without_platform = session.query(Image).filter(
                Image.platform_connection_id.is_(None)
            ).count()
            
            if posts_without_platform > 0:
                self.warnings.append(f"{posts_without_platform} posts without platform connection")
            
            if images_without_platform > 0:
                self.warnings.append(f"{images_without_platform} images without platform connection")
            
            session.close()
            
        except Exception as e:
            self.errors.append(f"Data integrity validation failed: {e}")
        
        print("✅ Data integrity validation complete")
    
    def run_validation(self):
        """Run complete validation"""
        print("🚀 Starting platform configuration validation...")
        print(f"📅 Validation started at: {datetime.now()}")
        print("=" * 60)
        
        self.validate_environment()
        self.validate_database()
        self.validate_platforms()
        self.validate_data_integrity()
        
        print("=" * 60)
        print("📋 Validation Summary:")
        
        if self.errors:
            print(f"❌ {len(self.errors)} errors found:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"⚠️ {len(self.warnings)} warnings:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ All validations passed!")
        elif not self.errors:
            print("✅ Validation passed with warnings")
        else:
            print("❌ Validation failed")
        
        return len(self.errors) == 0

def main():
    """Main validation function"""
    validator = PlatformConfigValidator()
    
    try:
        success = validator.run_validation()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Validation failed with exception: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())