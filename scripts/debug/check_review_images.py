#!/usr/bin/env python3
"""
Check what images are available for review in the database
"""

import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import Image, ProcessingStatus, PlatformConnection

def main():
    print("=== Review Images Status Check ===")
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        # Check total images
        total_images = session.query(Image).count()
        print(f"📊 Total images in database: {total_images}")
        
        # Check by status
        for status in ProcessingStatus:
            count = session.query(Image).filter_by(status=status).count()
            print(f"   {status.value}: {count}")
        
        print()
        
        # Show pending images with details
        pending_images = session.query(Image).filter_by(status=ProcessingStatus.PENDING).limit(5).all()
        
        if pending_images:
            print("🔍 Pending images for review:")
            for img in pending_images:
                platform_conn = session.query(PlatformConnection).filter_by(id=img.platform_connection_id).first()
                platform_name = platform_conn.name if platform_conn else "Unknown"
                
                print(f"   ID: {img.id}")
                print(f"   Platform: {platform_name}")
                print(f"   Image URL: {img.image_url[:80]}...")
                print(f"   Image Post ID: {img.image_post_id}")
                print(f"   Generated Caption: {(img.generated_caption or 'None')[:100]}...")
                print(f"   Created: {img.created_at}")
                print()
        else:
            print("ℹ️  No images pending review")
            
        # Show recently approved images
        approved_images = session.query(Image).filter_by(status=ProcessingStatus.APPROVED).limit(3).all()
        
        if approved_images:
            print("✅ Recently approved images:")
            for img in approved_images:
                platform_conn = session.query(PlatformConnection).filter_by(id=img.platform_connection_id).first()
                platform_name = platform_conn.name if platform_conn else "Unknown"
                
                print(f"   ID: {img.id}")
                print(f"   Platform: {platform_name}")
                print(f"   Image Post ID: {img.image_post_id}")
                print(f"   Final Caption: {(img.generated_caption or 'None')[:100]}...")
                print(f"   Updated: {img.updated_at}")
                print()

if __name__ == "__main__":
    main()