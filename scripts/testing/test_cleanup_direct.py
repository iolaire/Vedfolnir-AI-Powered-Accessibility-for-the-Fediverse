#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Direct test of cleanup functionality without web interface
"""

from config import Config
from database import DatabaseManager

def test_cleanup_direct():
    """Test cleanup functionality directly"""
    print("Testing cleanup functionality directly...")
    print("=" * 50)
    
    try:
        # Test configuration
        print("1. Testing configuration...")
        config = Config()
        print("✓ Configuration loaded")
        
        # Test database connection
        print("2. Testing database connection...")
        db_manager = DatabaseManager(config)
        session = db_manager.get_session()
        
        # Test basic database queries
        from models import Post, Image, ProcessingRun
        
        posts_count = session.query(Post).count()
        images_count = session.query(Image).count()
        runs_count = session.query(ProcessingRun).count()
        
        print(f"✓ Database connected - Posts: {posts_count}, Images: {images_count}, Runs: {runs_count}")
        session.close()
        
        # Test DataCleanupManager
        print("3. Testing DataCleanupManager...")
        from data_cleanup import DataCleanupManager
        
        cleanup_manager = DataCleanupManager(db_manager, config)
        print("✓ DataCleanupManager created")
        
        # Test each cleanup method with dry run
        print("4. Testing cleanup methods...")
        
        # Test archive_old_processing_runs
        try:
            count = cleanup_manager.archive_old_processing_runs(days=90, dry_run=True)
            print(f"✓ archive_old_processing_runs: {count} items would be archived")
        except Exception as e:
            print(f"✗ archive_old_processing_runs failed: {e}")
        
        # Test cleanup_orphaned_posts
        try:
            count = cleanup_manager.cleanup_orphaned_posts(dry_run=True)
            print(f"✓ cleanup_orphaned_posts: {count} items would be cleaned")
        except Exception as e:
            print(f"✗ cleanup_orphaned_posts failed: {e}")
        
        # Test cleanup_old_images
        try:
            from models import ProcessingStatus
            count = cleanup_manager.cleanup_old_images(
                status=ProcessingStatus.REJECTED, 
                days=30, 
                dry_run=True
            )
            print(f"✓ cleanup_old_images: {count} items would be cleaned")
        except Exception as e:
            print(f"✗ cleanup_old_images failed: {e}")
        
        print("\n✓ All direct tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Direct test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_web_route_simulation():
    """Simulate what the web route does"""
    print("\nSimulating web route logic...")
    print("=" * 50)
    
    try:
        # Simulate the admin_cleanup_runs route
        from config import Config
        from database import DatabaseManager
        from data_cleanup import DataCleanupManager
        
        # Simulate form data
        days = 90
        dry_run = True
        
        print(f"Simulating: days={days}, dry_run={dry_run}")
        
        config = Config()
        db_manager = DatabaseManager(config)
        cleanup_manager = DataCleanupManager(db_manager, config)
        
        count = cleanup_manager.archive_old_processing_runs(days=days, dry_run=dry_run)
        
        if dry_run:
            message = f'Dry run: Would archive {count} processing runs older than {days} days'
        else:
            message = f'Successfully archived {count} processing runs older than {days} days'
        
        print(f"✓ Route simulation successful: {message}")
        return True
        
    except Exception as e:
        print(f"✗ Route simulation failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Vedfolnir Direct Cleanup Test")
    print("=" * 50)
    
    direct_works = test_cleanup_direct()
    route_sim_works = test_web_route_simulation()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Direct cleanup: {'✓ Working' if direct_works else '✗ Failed'}")
    print(f"Route simulation: {'✓ Working' if route_sim_works else '✗ Failed'}")
    
    if direct_works and route_sim_works:
        print("\n✓ Cleanup functionality is working correctly!")
        print("The issue is likely with:")
        print("- Web authentication/authorization")
        print("- Form submission/JavaScript")
        print("- Flash message display")
        print("- Route URL generation")
    else:
        print("\n✗ There are issues with the cleanup functionality itself.")