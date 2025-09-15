#!/usr/bin/env python3
"""
Test script to verify user data deletion covers all images including pending ones
"""

import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import Image, ProcessingStatus, PlatformConnection, User
from scripts.maintenance.delete_user_data import UserDataDeleter

def test_image_detection():
    """Test that the deletion script finds all images for a user"""
    print("=== Testing User Data Deletion Image Detection ===")
    
    config = Config()
    db_manager = DatabaseManager(config)
    deleter = UserDataDeleter(config)
    
    with db_manager.get_session() as session:
        # Find a user with images
        users_with_images = session.query(User).join(PlatformConnection).join(Image).distinct().all()
        
        if not users_with_images:
            print("❌ No users with images found for testing")
            return
        
        for user in users_with_images[:3]:  # Test first 3 users
            print(f"\n🔍 Testing user: {user.username} (ID: {user.id})")
            
            # Get user's platform connections
            user_platforms = session.query(PlatformConnection).filter_by(user_id=user.id).all()
            platform_ids = [p.id for p in user_platforms]
            
            print(f"   Platform connections: {len(user_platforms)}")
            for platform in user_platforms:
                print(f"     - {platform.name} ({platform.platform_type})")
            
            # Count images by different methods
            
            # Method 1: Direct platform connection query (what we added)
            if platform_ids:
                platform_images = session.query(Image).filter(Image.platform_connection_id.in_(platform_ids)).all()
            else:
                platform_images = []
            
            # Method 2: Through posts (original method)
            from models import Post
            posts = session.query(Post).filter_by(user_id=str(user.id)).all()
            post_ids = [post.id for post in posts] if posts else []
            if post_ids:
                post_images = session.query(Image).filter(Image.post_id.in_(post_ids)).all()
            else:
                post_images = []
            
            # Combine and deduplicate
            all_images = []
            existing_ids = set()
            
            for img in platform_images + post_images:
                if img.id not in existing_ids:
                    all_images.append(img)
                    existing_ids.add(img.id)
            
            print(f"   Images found via platform connections: {len(platform_images)}")
            print(f"   Images found via posts: {len(post_images)}")
            print(f"   Total unique images: {len(all_images)}")
            
            # Show status breakdown
            status_counts = {}
            for image in all_images:
                status = image.status.value if image.status else 'unknown'
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                print("   Status breakdown:")
                for status, count in status_counts.items():
                    print(f"     - {status}: {count}")
            
            # Test the deletion script's detection
            print(f"\n🧪 Testing deletion script detection...")
            try:
                results = deleter.delete_user_data(user.id, dry_run=True)
                script_image_count = results.get('images', 0)
                
                if script_image_count == len(all_images):
                    print(f"   ✅ Script correctly found {script_image_count} images")
                else:
                    print(f"   ❌ Script found {script_image_count} images, expected {len(all_images)}")
                    
            except Exception as e:
                print(f"   ❌ Error testing deletion script: {e}")

def main():
    test_image_detection()

if __name__ == "__main__":
    main()