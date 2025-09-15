#!/usr/bin/env python3
"""
Comprehensive test for user data deletion to ensure all images are found
"""

import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import Image, ProcessingStatus, PlatformConnection, User, Post

def test_all_images():
    """Test that we can find all images in the database"""
    print("=== Comprehensive Image Detection Test ===")
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        # Get all images
        all_images = session.query(Image).all()
        print(f"📊 Total images in database: {len(all_images)}")
        
        # Group by platform_connection_id
        by_platform = {}
        orphaned_images = []
        
        for image in all_images:
            if image.platform_connection_id:
                if image.platform_connection_id not in by_platform:
                    by_platform[image.platform_connection_id] = []
                by_platform[image.platform_connection_id].append(image)
            else:
                orphaned_images.append(image)
        
        print(f"📊 Images by platform connection:")
        for platform_id, images in by_platform.items():
            platform = session.query(PlatformConnection).filter_by(id=platform_id).first()
            platform_name = f"{platform.name} (User: {platform.user_id})" if platform else f"Unknown Platform {platform_id}"
            print(f"   Platform {platform_id} ({platform_name}): {len(images)} images")
            
            # Show status breakdown
            status_counts = {}
            for img in images:
                status = img.status.value if img.status else 'unknown'
                status_counts[status] = status_counts.get(status, 0) + 1
            
            status_summary = ', '.join([f"{status}: {count}" for status, count in status_counts.items()])
            print(f"     Status: {status_summary}")
        
        if orphaned_images:
            print(f"⚠️  Orphaned images (no platform_connection_id): {len(orphaned_images)}")
            for img in orphaned_images:
                print(f"     Image {img.id}: {img.image_url[:60]}... (Status: {img.status.value if img.status else 'unknown'})")
                
                # Try to find the post and its user
                if img.post_id:
                    post = session.query(Post).filter_by(id=img.post_id).first()
                    if post:
                        print(f"       Associated with post {post.id} (User: {post.user_id})")
                    else:
                        print(f"       Post {img.post_id} not found!")
        
        # Test what happens if we try to delete data for users with orphaned images
        if orphaned_images:
            print(f"\n🧪 Testing deletion for users with orphaned images...")
            
            # Find users who have posts with orphaned images
            users_with_orphaned = set()
            for img in orphaned_images:
                if img.post_id:
                    post = session.query(Post).filter_by(id=img.post_id).first()
                    if post:
                        try:
                            # Handle both numeric and string user IDs
                            if post.user_id.startswith('@'):
                                # This is a username, need to find the actual user ID
                                username = post.user_id[1:]  # Remove @
                                user = session.query(User).filter_by(username=username).first()
                                if user:
                                    users_with_orphaned.add(user.id)
                            else:
                                users_with_orphaned.add(int(post.user_id))
                        except (ValueError, AttributeError) as e:
                            print(f"       Warning: Could not parse user_id '{post.user_id}': {e}")
            
            print(f"   Users with orphaned images: {users_with_orphaned}")
            
            # Test deletion script for these users
            from scripts.maintenance.delete_user_data import UserDataDeleter
            deleter = UserDataDeleter(config)
            
            for user_id in list(users_with_orphaned)[:2]:  # Test first 2 users
                print(f"\n   Testing user {user_id}:")
                try:
                    results = deleter.delete_user_data(user_id, dry_run=True)
                    print(f"     Would delete {results.get('images', 0)} images")
                    print(f"     Would delete {results.get('posts', 0)} posts")
                except Exception as e:
                    print(f"     ❌ Error: {e}")

def main():
    test_all_images()

if __name__ == "__main__":
    main()