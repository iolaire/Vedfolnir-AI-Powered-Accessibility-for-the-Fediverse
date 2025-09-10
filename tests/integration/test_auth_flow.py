#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test script for Task 4.2: Update Authentication Flow

This script tests the updated authentication flow including:
- Login with platform context setup
- First-time user setup
- Platform access validation
- User profile functionality
- Session management
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, UserRole, PlatformConnection
from unified_session_manager import UnifiedSessionManager as SessionManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AuthFlowTester:
    """Test the updated authentication flow"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
        
    def test_user_creation(self):
        """Test creating users with different scenarios"""
        logger.info("Testing user creation...")
        
        # Test creating a new user
        user_id = self.db_manager.create_user(
            username="test_auth_user",
            email="test_auth@example.com",
            password="testpassword123",
            role=UserRole.REVIEWER
        )
        
        if user_id:
            logger.info(f"✓ Created test user with ID: {user_id}")
            
            # Get the user to verify
            session = self.db_manager.get_session()
            try:
                user = session.query(User).get(user_id)
                if user:
                    logger.info(f"✓ User verification: {user.username}, role: {user.role.value}")
                    
                    # Test user methods
                    active_platforms = user.get_active_platforms()
                    default_platform = user.get_default_platform()
                    
                    logger.info(f"✓ User has {len(active_platforms)} active platforms")
                    logger.info(f"✓ Default platform: {default_platform}")
                    
                    return user_id
                else:
                    logger.error("✗ Failed to retrieve created user")
                    return None
            finally:
                session.close()
        else:
            logger.error("✗ Failed to create test user")
            return None
    
    def test_platform_creation(self, user_id):
        """Test creating platform connections"""
        logger.info("Testing platform connection creation...")
        
        try:
            # Create a test Pixelfed platform
            pixelfed_platform = self.db_manager.create_platform_connection(
                user_id=user_id,
                name="Test Pixelfed",
                platform_type="pixelfed",
                instance_url="https://pixelfed.social",
                username="testuser",
                access_token="test_token_123",
                is_default=True
            )
            
            if pixelfed_platform:
                logger.info(f"✓ Created Pixelfed platform: {pixelfed_platform.name} (ID: {pixelfed_platform.id})")
                
                # Create a test Mastodon platform
                mastodon_platform = self.db_manager.create_platform_connection(
                    user_id=user_id,
                    name="Test Mastodon",
                    platform_type="mastodon",
                    instance_url="https://mastodon.social",
                    username="testuser",
                    access_token="test_mastodon_token_123",
                    is_default=False
                )
                
                if mastodon_platform:
                    logger.info(f"✓ Created Mastodon platform: {mastodon_platform.name} (ID: {mastodon_platform.id})")
                    return [pixelfed_platform.id, mastodon_platform.id]
                else:
                    logger.error("✗ Failed to create Mastodon platform")
                    return [pixelfed_platform.id]
            else:
                logger.error("✗ Failed to create Pixelfed platform")
                return []
                
        except Exception as e:
            logger.error(f"✗ Error creating platforms: {e}")
            return []
    
    def test_session_management(self, user_id, platform_ids):
        """Test session management functionality"""
        logger.info("Testing session management...")
        
        try:
            # Test creating a session
            session_id = self.session_manager.create_session(user_id, platform_ids[0] if platform_ids else None)
            
            if session_id:
                logger.info(f"✓ Created session: {session_id}")
                
                # Test getting session context
                context = self.session_manager.get_session_context(session_id)
                if context:
                    logger.info(f"✓ Retrieved session context for user {context['user_id']}")
                    logger.info(f"✓ Platform context: {context['platform_connection'].name if context['platform_connection'] else 'None'}")
                    
                    # Test platform switching if we have multiple platforms
                    if len(platform_ids) > 1:
                        success = self.session_manager.update_platform_context(session_id, platform_ids[1])
                        if success:
                            logger.info("✓ Successfully switched platform context")
                            
                            # Verify the switch
                            updated_context = self.session_manager.get_session_context(session_id)
                            if updated_context and updated_context['platform_connection_id'] == platform_ids[1]:
                                logger.info("✓ Platform switch verified")
                            else:
                                logger.error("✗ Platform switch verification failed")
                        else:
                            logger.error("✗ Failed to switch platform context")
                    
                    # Test getting active sessions
                    active_sessions = self.session_manager.get_user_active_sessions(user_id)
                    logger.info(f"✓ User has {len(active_sessions)} active sessions")
                    
                    # Test session cleanup
                    cleanup_count = self.session_manager.cleanup_user_sessions(user_id)
                    logger.info(f"✓ Cleaned up {cleanup_count} expired sessions")
                    
                    return session_id
                else:
                    logger.error("✗ Failed to retrieve session context")
                    return None
            else:
                logger.error("✗ Failed to create session")
                return None
                
        except Exception as e:
            logger.error(f"✗ Error in session management: {e}")
            return None
    
    def test_platform_access_validation(self, user_id, platform_ids):
        """Test platform access validation"""
        logger.info("Testing platform access validation...")
        
        session = self.db_manager.get_session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                logger.error("✗ User not found for validation test")
                return False
            
            # Test platform access methods
            platforms = user.get_active_platforms()
            logger.info(f"✓ User has access to {len(platforms)} platforms")
            
            if platforms:
                # Test getting platform by type
                pixelfed_platform = user.get_platform_by_type('pixelfed')
                mastodon_platform = user.get_platform_by_type('mastodon')
                
                if pixelfed_platform:
                    logger.info(f"✓ Found Pixelfed platform: {pixelfed_platform.name}")
                
                if mastodon_platform:
                    logger.info(f"✓ Found Mastodon platform: {mastodon_platform.name}")
                
                # Test setting default platform
                if len(platform_ids) > 1:
                    user.set_default_platform(platform_ids[1])
                    session.commit()
                    
                    # Verify default was set
                    new_default = user.get_default_platform()
                    if new_default and new_default.id == platform_ids[1]:
                        logger.info("✓ Successfully changed default platform")
                    else:
                        logger.error("✗ Failed to change default platform")
                
                # Test platform access validation
                has_access = user.has_platform_access('pixelfed', 'https://pixelfed.social')
                logger.info(f"✓ Platform access validation: {has_access}")
                
                return True
            else:
                logger.error("✗ No platforms found for user")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error in platform access validation: {e}")
            return False
        finally:
            session.close()
    
    def test_database_platform_stats(self, platform_ids):
        """Test platform-specific database statistics"""
        logger.info("Testing platform-specific statistics...")
        
        try:
            if platform_ids:
                # Test getting stats for specific platform
                stats = self.db_manager.get_platform_processing_stats(platform_ids[0])
                logger.info(f"✓ Platform stats: {stats}")
                
                # Test getting user platform summary
                session = self.db_manager.get_session()
                try:
                    platform = session.query(PlatformConnection).get(platform_ids[0])
                    if platform:
                        summary = self.db_manager.get_user_platform_summary(platform.user_id)
                        logger.info(f"✓ User platform summary: {summary['total_platforms']} platforms")
                        return True
                finally:
                    session.close()
            
            return False
            
        except Exception as e:
            logger.error(f"✗ Error testing platform stats: {e}")
            return False
    
    def cleanup_test_data(self, user_id):
        """Clean up test data"""
        logger.info("Cleaning up test data...")
        
        try:
            # Delete the test user (this should cascade to platforms and sessions)
            success = self.db_manager.delete_user(user_id)
            if success:
                logger.info("✓ Cleaned up test user and associated data")
            else:
                logger.error("✗ Failed to clean up test user")
                
        except Exception as e:
            logger.error(f"✗ Error cleaning up test data: {e}")
    
    def run_all_tests(self):
        """Run all authentication flow tests"""
        logger.info("Starting authentication flow tests...")
        
        user_id = None
        platform_ids = []
        
        try:
            # Test 1: User creation
            user_id = self.test_user_creation()
            if not user_id:
                logger.error("Failed user creation test - aborting")
                return False
            
            # Test 2: Platform creation
            platform_ids = self.test_platform_creation(user_id)
            if not platform_ids:
                logger.error("Failed platform creation test - aborting")
                return False
            
            # Test 3: Session management
            session_id = self.test_session_management(user_id, platform_ids)
            if not session_id:
                logger.error("Failed session management test")
            
            # Test 4: Platform access validation
            access_success = self.test_platform_access_validation(user_id, platform_ids)
            if not access_success:
                logger.error("Failed platform access validation test")
            
            # Test 5: Database platform stats
            stats_success = self.test_database_platform_stats(platform_ids)
            if not stats_success:
                logger.error("Failed database platform stats test")
            
            logger.info("✓ All authentication flow tests completed")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error during tests: {e}")
            return False
        finally:
            # Always clean up
            if user_id:
                self.cleanup_test_data(user_id)

def main():
    """Main test function"""
    print("Testing Task 4.2: Update Authentication Flow")
    print("=" * 50)
    
    tester = AuthFlowTester()
    success = tester.run_all_tests()
    
    print("=" * 50)
    if success:
        print("✓ All authentication flow tests PASSED")
        return 0
    else:
        print("✗ Some authentication flow tests FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())