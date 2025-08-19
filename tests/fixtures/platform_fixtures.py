# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test fixtures for platform-aware functionality

Provides reusable test data and setup utilities for platform-aware unit tests.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, UserRole, PlatformConnection, UserSession, Post, Image, ProcessingRun, ProcessingStatus
from config import Config
from database import DatabaseManager


class PlatformTestFixtures:
    """Provides test fixtures for platform-aware testing"""
    
    @staticmethod
    def create_test_users():
        """Create test users with different roles"""
        return [
            {
                'username': 'test_admin',
                'email': 'admin@test.com',
                'password': 'admin123',
                'role': UserRole.ADMIN
            },
            {
                'username': 'test_reviewer',
                'email': 'reviewer@test.com', 
                'password': 'reviewer123',
                'role': UserRole.REVIEWER
            },
            {
                'username': 'test_viewer',
                'email': 'viewer@test.com',
                'password': 'viewer123',
                'role': UserRole.VIEWER
            }
        ]
    
    @staticmethod
    def create_test_platforms():
        """Create test platform connections"""
        return [
            {
                'name': 'Test Pixelfed',
                'platform_type': 'pixelfed',
                'instance_url': 'https://pixelfed.test',
                'username': 'testuser',
                'access_token': 'pixelfed_test_token_123',
                'is_default': True
            },
            {
                'name': 'Test Mastodon',
                'platform_type': 'mastodon',
                'instance_url': 'https://mastodon.test',
                'username': 'testuser',
                'access_token': 'mastodon_test_token_456',
                'client_key': 'mastodon_client_key',
                'client_secret': 'mastodon_client_secret',
                'is_default': False
            },
            {
                'name': 'Secondary Pixelfed',
                'platform_type': 'pixelfed',
                'instance_url': 'https://pixelfed2.test',
                'username': 'testuser2',
                'access_token': 'pixelfed2_test_token_789',
                'is_default': False
            }
        ]
    
    @staticmethod
    def create_test_posts():
        """Create test posts for different platforms"""
        return [
            {
                'post_id': 'post_123',
                'user_id': 'testuser',
                'post_url': 'https://pixelfed.test/p/testuser/123',
                'post_content': 'Test post content'
            },
            {
                'post_id': 'post_456', 
                'user_id': 'testuser',
                'post_url': 'https://mastodon.test/@testuser/456',
                'post_content': 'Another test post'
            }
        ]
    
    @staticmethod
    def create_test_images():
        """Create test images for different platforms"""
        return [
            {
                'image_url': 'https://pixelfed.test/storage/image1.jpg',
                'local_path': '/tmp/image1.jpg',
                'attachment_index': 0,
                'media_type': 'image/jpeg',
                'image_post_id': 'media_123',
                'generated_caption': 'A test image',
                'status': ProcessingStatus.PENDING
            },
            {
                'image_url': 'https://mastodon.test/media/image2.jpg',
                'local_path': '/tmp/image2.jpg', 
                'attachment_index': 0,
                'media_type': 'image/png',
                'image_post_id': 'media_456',
                'generated_caption': 'Another test image',
                'status': ProcessingStatus.APPROVED
            }
        ]


class PlatformTestCase(unittest.TestCase):
    """Base test case with platform-aware setup"""
    
    def setUp(self):
        """Set up test database and fixtures"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.db_url = f'sqlite:///{self.db_path}'
        
        # Set up test environment
        os.environ['DATABASE_URL'] = self.db_url
        # Generate a proper Fernet key for testing
        from cryptography.fernet import Fernet
        os.environ['PLATFORM_ENCRYPTION_KEY'] = Fernet.generate_key().decode()
        
        # Create test config
        self.config = Config()
        self.config.storage.database_url = self.db_url
        
        # Create database manager
        self.db_manager = DatabaseManager(self.config)
        
        # Create test session
        self.session = self.db_manager.get_session()
        
        # Create test data
        self.users = []
        self.platforms = []
        self.posts = []
        self.images = []
        
        self._create_test_data()
    
    def tearDown(self):
        """Clean up test database"""
        self.session.close()
        self.db_manager.close_session(self.session)
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_data(self):
        """Create test users, platforms, and data"""
        # Create test users
        for user_data in PlatformTestFixtures.create_test_users():
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                is_active=True
            )
            user.set_password(user_data['password'])
            self.session.add(user)
            self.users.append(user)
        
        self.session.commit()
        
        # Create test platforms for first user
        for platform_data in PlatformTestFixtures.create_test_platforms():
            platform = PlatformConnection(
                user_id=self.users[0].id,
                name=platform_data['name'],
                platform_type=platform_data['platform_type'],
                instance_url=platform_data['instance_url'],
                username=platform_data['username'],
                access_token=platform_data['access_token'],
                client_key=platform_data.get('client_key'),
                client_secret=platform_data.get('client_secret'),
                is_default=platform_data['is_default'],
                is_active=True
            )
            self.session.add(platform)
            self.platforms.append(platform)
        
        self.session.commit()
        
        # Create test posts
        for i, post_data in enumerate(PlatformTestFixtures.create_test_posts()):
            post = Post(
                post_id=post_data['post_id'],
                user_id=post_data['user_id'],
                post_url=post_data['post_url'],
                post_content=post_data['post_content'],
                platform_connection_id=self.platforms[i % len(self.platforms)].id
            )
            self.session.add(post)
            self.posts.append(post)
        
        self.session.commit()
        
        # Create test images
        for i, image_data in enumerate(PlatformTestFixtures.create_test_images()):
            image = Image(
                post_id=self.posts[i % len(self.posts)].id,
                image_url=image_data['image_url'],
                local_path=image_data['local_path'],
                attachment_index=image_data['attachment_index'],
                media_type=image_data['media_type'],
                image_post_id=image_data['image_post_id'],
                generated_caption=image_data['generated_caption'],
                status=image_data['status'],
                platform_connection_id=self.platforms[i % len(self.platforms)].id
            )
            self.session.add(image)
            self.images.append(image)
        
        self.session.commit()
    
    def get_test_user(self, role=UserRole.ADMIN):
        """Get test user by role"""
        for user in self.users:
            if user.role == role:
                return user
        return self.users[0]
    
    def get_test_platform(self, platform_type='pixelfed'):
        """Get test platform by type"""
        for platform in self.platforms:
            if platform.platform_type == platform_type:
                return platform
        return self.platforms[0]
    
    def create_test_session(self, user=None, platform=None):
        """Create test user session"""
        if user is None:
            user = self.get_test_user()
        if platform is None:
            platform = self.get_test_platform()
        
        session = UserSession(
            user_id=user.id,
            session_id=f'test_session_{user.id}_{platform.id}',
            active_platform_id=platform.id
        )
        self.session.add(session)
        self.session.commit()
        return session