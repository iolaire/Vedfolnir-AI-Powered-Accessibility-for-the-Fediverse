# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Access Control Middleware

This middleware provides platform-scoped access control for viewer users,
ensuring they can only access content from their own platforms while
allowing admin users full access.

Requirements: 8.2, 8.3, 8.4, 8.5
"""

import logging
from flask import current_app, g, request
from flask_login import current_user
from models import UserRole, PlatformConnection, Image, Post
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class PlatformAccessMiddleware:
    """
    Middleware to handle platform-scoped access control for viewer users.
    
    Requirements: 8.2, 8.3, 8.4, 8.5
    """
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with the Flask app."""
        app.before_request(self.before_request)
        app.teardown_appcontext(self.teardown)
    
    def before_request(self):
        """Set up platform access context before each request."""
        if not current_user.is_authenticated:
            return
        
        try:
            # Cache user's accessible platforms in g for the request
            g.user_accessible_platforms = self._get_user_accessible_platforms()
            g.user_accessible_platform_ids = [p.id for p in g.user_accessible_platforms]
            
            # Set up content filtering context
            g.platform_access_middleware_active = True
            
        except Exception as e:
            logger.error(f"Error setting up platform access context: {e}")
            g.user_accessible_platforms = []
            g.user_accessible_platform_ids = []
            g.platform_access_middleware_active = False
    
    def teardown(self, exception):
        """Clean up platform access context after request."""
        g.pop('user_accessible_platforms', None)
        g.pop('user_accessible_platform_ids', None)
        g.pop('platform_access_middleware_active', None)
    
    def _get_user_accessible_platforms(self):
        """
        Get platforms accessible to the current user.
        
        Returns:
            list: List of PlatformConnection objects
        """
        if not current_user.is_authenticated:
            return []
        
        try:
            session_manager = current_app.request_session_manager
            with session_manager.session_scope() as db_session:
                # Admin users can access all platforms
                if current_user.role == UserRole.ADMIN:
                    platforms = db_session.query(PlatformConnection).filter_by(
                        is_active=True
                    ).options(joinedload(PlatformConnection.user)).all()
                else:
                    # Viewer users can only access their own platforms
                    platforms = db_session.query(PlatformConnection).filter_by(
                        user_id=current_user.id,
                        is_active=True
                    ).options(joinedload(PlatformConnection.user)).all()
                
                return platforms
                
        except Exception as e:
            logger.error(f"Error getting user accessible platforms: {e}")
            return []
    
    @staticmethod
    def filter_images_query(query):
        """
        Filter images query based on user platform access.
        
        Args:
            query: SQLAlchemy query object for Image model
            
        Returns:
            query: Filtered query object
            
        Requirements: 8.4, 8.5
        """
        if not current_user.is_authenticated:
            return query.filter(False)  # No access for unauthenticated users
        
        # Admin users can access all images
        if current_user.role == UserRole.ADMIN:
            return query
        
        # Viewer users can only access images from their platforms
        accessible_platform_ids = getattr(g, 'user_accessible_platform_ids', [])
        if not accessible_platform_ids:
            return query.filter(False)  # No platforms = no access
        
        return query.filter(Image.platform_connection_id.in_(accessible_platform_ids))
    
    @staticmethod
    def filter_posts_query(query):
        """
        Filter posts query based on user platform access.
        
        Args:
            query: SQLAlchemy query object for Post model
            
        Returns:
            query: Filtered query object
            
        Requirements: 8.4, 8.5
        """
        if not current_user.is_authenticated:
            return query.filter(False)  # No access for unauthenticated users
        
        # Admin users can access all posts
        if current_user.role == UserRole.ADMIN:
            return query
        
        # Viewer users can only access posts from their platforms
        accessible_platform_ids = getattr(g, 'user_accessible_platform_ids', [])
        if not accessible_platform_ids:
            return query.filter(False)  # No platforms = no access
        
        return query.filter(Post.platform_connection_id.in_(accessible_platform_ids))
    
    @staticmethod
    def filter_platforms_query(query):
        """
        Filter platforms query based on user access.
        
        Args:
            query: SQLAlchemy query object for PlatformConnection model
            
        Returns:
            query: Filtered query object
            
        Requirements: 8.2, 8.3
        """
        if not current_user.is_authenticated:
            return query.filter(False)  # No access for unauthenticated users
        
        # Admin users can access all platforms
        if current_user.role == UserRole.ADMIN:
            return query
        
        # Viewer users can only access their own platforms
        return query.filter(PlatformConnection.user_id == current_user.id)
    
    @staticmethod
    def check_image_access(image_id):
        """
        Check if current user has access to a specific image.
        
        Args:
            image_id (int): Image ID to check
            
        Returns:
            bool: True if user has access, False otherwise
            
        Requirements: 8.4, 8.5
        """
        if not current_user.is_authenticated:
            return False
        
        # Admin users have access to all images
        if current_user.role == UserRole.ADMIN:
            return True
        
        try:
            session_manager = current_app.request_session_manager
            with session_manager.session_scope() as db_session:
                image = db_session.query(Image).filter_by(id=image_id).first()
                if not image or not image.platform_connection_id:
                    return False
                
                accessible_platform_ids = getattr(g, 'user_accessible_platform_ids', [])
                return image.platform_connection_id in accessible_platform_ids
                
        except Exception as e:
            logger.error(f"Error checking image access for image {image_id}: {e}")
            return False
    
    @staticmethod
    def check_post_access(post_id):
        """
        Check if current user has access to a specific post.
        
        Args:
            post_id (int): Post ID to check
            
        Returns:
            bool: True if user has access, False otherwise
            
        Requirements: 8.4, 8.5
        """
        if not current_user.is_authenticated:
            return False
        
        # Admin users have access to all posts
        if current_user.role == UserRole.ADMIN:
            return True
        
        try:
            session_manager = current_app.request_session_manager
            with session_manager.session_scope() as db_session:
                post = db_session.query(Post).filter_by(id=post_id).first()
                if not post or not post.platform_connection_id:
                    return False
                
                accessible_platform_ids = getattr(g, 'user_accessible_platform_ids', [])
                return post.platform_connection_id in accessible_platform_ids
                
        except Exception as e:
            logger.error(f"Error checking post access for post {post_id}: {e}")
            return False
    
    @staticmethod
    def check_platform_access(platform_id):
        """
        Check if current user has access to a specific platform.
        
        Args:
            platform_id (int): Platform ID to check
            
        Returns:
            bool: True if user has access, False otherwise
            
        Requirements: 8.2, 8.3
        """
        if not current_user.is_authenticated:
            return False
        
        # Admin users have access to all platforms
        if current_user.role == UserRole.ADMIN:
            return True
        
        accessible_platform_ids = getattr(g, 'user_accessible_platform_ids', [])
        return platform_id in accessible_platform_ids
    
    @staticmethod
    def get_user_platform_stats():
        """
        Get platform statistics for the current user.
        
        Returns:
            dict: Platform statistics
            
        Requirements: 8.1, 8.2
        """
        if not current_user.is_authenticated:
            return {
                'platform_count': 0,
                'active_platforms': 0,
                'default_platform': None,
                'platforms': []
            }
        
        try:
            accessible_platforms = getattr(g, 'user_accessible_platforms', [])
            active_platforms = [p for p in accessible_platforms if p.is_active]
            default_platform = next((p for p in active_platforms if p.is_default), None)
            
            return {
                'platform_count': len(accessible_platforms),
                'active_platforms': len(active_platforms),
                'default_platform': default_platform,
                'platforms': accessible_platforms
            }
            
        except Exception as e:
            logger.error(f"Error getting user platform stats: {e}")
            return {
                'platform_count': 0,
                'active_platforms': 0,
                'default_platform': None,
                'platforms': []
            }
    
    @staticmethod
    def get_user_content_stats():
        """
        Get content statistics for the current user's accessible platforms.
        
        Returns:
            dict: Content statistics
            
        Requirements: 8.4, 8.5
        """
        if not current_user.is_authenticated:
            return {
                'total_images': 0,
                'pending_review': 0,
                'approved_images': 0,
                'total_posts': 0
            }
        
        try:
            session_manager = current_app.request_session_manager
            with session_manager.session_scope() as db_session:
                accessible_platform_ids = getattr(g, 'user_accessible_platform_ids', [])
                
                if not accessible_platform_ids:
                    return {
                        'total_images': 0,
                        'pending_review': 0,
                        'approved_images': 0,
                        'total_posts': 0
                    }
                
                # Count images
                images_query = db_session.query(Image).filter(
                    Image.platform_connection_id.in_(accessible_platform_ids)
                )
                total_images = images_query.count()
                
                from models import ProcessingStatus
                pending_review = images_query.filter(
                    Image.status == ProcessingStatus.PENDING
                ).count()
                
                approved_images = images_query.filter(
                    Image.status == ProcessingStatus.APPROVED
                ).count()
                
                # Count posts
                posts_query = db_session.query(Post).filter(
                    Post.platform_connection_id.in_(accessible_platform_ids)
                )
                total_posts = posts_query.count()
                
                return {
                    'total_images': total_images,
                    'pending_review': pending_review,
                    'approved_images': approved_images,
                    'total_posts': total_posts
                }
                
        except Exception as e:
            logger.error(f"Error getting user content stats: {e}")
            return {
                'total_images': 0,
                'pending_review': 0,
                'approved_images': 0,
                'total_posts': 0
            }


# Convenience functions for use in templates and views
def get_accessible_platforms():
    """Get platforms accessible to current user."""
    return getattr(g, 'user_accessible_platforms', [])


def get_accessible_platform_ids():
    """Get platform IDs accessible to current user."""
    return getattr(g, 'user_accessible_platform_ids', [])


def is_platform_accessible(platform_id):
    """Check if a platform is accessible to current user."""
    return PlatformAccessMiddleware.check_platform_access(platform_id)


def is_image_accessible(image_id):
    """Check if an image is accessible to current user."""
    return PlatformAccessMiddleware.check_image_access(image_id)


def is_post_accessible(post_id):
    """Check if a post is accessible to current user."""
    return PlatformAccessMiddleware.check_post_access(post_id)


def filter_images_for_user(query):
    """Filter images query for current user's access."""
    return PlatformAccessMiddleware.filter_images_query(query)


def filter_posts_for_user(query):
    """Filter posts query for current user's access."""
    return PlatformAccessMiddleware.filter_posts_query(query)


def filter_platforms_for_user(query):
    """Filter platforms query for current user's access."""
    return PlatformAccessMiddleware.filter_platforms_query(query)