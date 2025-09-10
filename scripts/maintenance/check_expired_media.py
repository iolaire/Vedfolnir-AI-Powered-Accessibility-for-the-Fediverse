#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Script to check for and optionally clean up expired media attachments.

Mastodon and Pixelfed media attachments expire after a certain period (typically 24-48 hours).
This script helps identify images that may have expired media attachments.
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import Image, ProcessingStatus

def check_expired_media(days_threshold=2, dry_run=True):
    """
    Check for images with potentially expired media attachments.
    
    Args:
        days_threshold: Number of days after which media is considered potentially expired
        dry_run: If True, only report findings without making changes
    """
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    
    session = db_manager.get_session()
    try:
        # Find approved images older than threshold with media IDs
        potentially_expired = session.query(Image).filter(
            Image.status == ProcessingStatus.APPROVED,
            Image.image_post_id.isnot(None),
            Image.image_post_id != '',
            Image.original_post_date < cutoff_date
        ).order_by(Image.original_post_date.desc()).all()
        
        print(f"Found {len(potentially_expired)} approved images with media IDs older than {days_threshold} days")
        print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        if potentially_expired:
            print("Potentially expired media attachments:")
            print("-" * 80)
            
            for image in potentially_expired:
                platform_info = image.get_platform_info()
                age_days = (datetime.now(timezone.utc) - image.original_post_date).days
                
                print(f"Image ID: {image.id}")
                print(f"Media ID: {image.image_post_id}")
                print(f"Platform: {platform_info['platform_type']} ({platform_info['instance_url']})")
                print(f"Post Date: {image.original_post_date.strftime('%Y-%m-%d %H:%M:%S UTC')} ({age_days} days ago)")
                print(f"Image URL: {image.image_url}")
                print(f"Caption: {(image.final_caption or image.reviewed_caption or '')[:100]}...")
                print("-" * 80)
        
        # Find images that failed to post (might be due to expired media)
        failed_posts = session.query(Image).filter(
            Image.status == ProcessingStatus.APPROVED,
            Image.image_post_id.isnot(None),
            Image.image_post_id != '',
            Image.posted_at.is_(None),
            Image.original_post_date < cutoff_date
        ).count()
        
        print(f"\nFound {failed_posts} approved images that failed to post (may be due to expired media)")
        
        if not dry_run and potentially_expired:
            print(f"\nWould you like to mark these {len(potentially_expired)} images as 'posted' to clean up the queue?")
            print("This is safe to do since expired media cannot be updated anyway.")
            response = input("Type 'yes' to proceed: ").lower().strip()
            
            if response == 'yes':
                updated_count = 0
                for image in potentially_expired:
                    image.status = ProcessingStatus.POSTED
                    image.posted_at = datetime.now(timezone.utc)
                    updated_count += 1
                
                session.commit()
                print(f"Updated {updated_count} images to 'posted' status")
            else:
                print("No changes made")
        elif dry_run:
            print(f"\nDry run mode - no changes made")
            print(f"Run with --no-dry-run to actually update expired media entries")
            
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        return False
    finally:
        session.close()
    
    return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check for expired media attachments')
    parser.add_argument('--days', type=int, default=2, 
                       help='Number of days after which media is considered expired (default: 2)')
    parser.add_argument('--no-dry-run', action='store_true',
                       help='Actually update expired media entries (default: dry run only)')
    
    args = parser.parse_args()
    
    print("Checking for expired media attachments...")
    print(f"Days threshold: {args.days}")
    print(f"Mode: {'Update' if args.no_dry_run else 'Dry run'}")
    print()
    
    success = check_expired_media(
        days_threshold=args.days,
        dry_run=not args.no_dry_run
    )
    
    if success:
        print("\nCheck completed successfully")
        return 0
    else:
        print("\nCheck failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())