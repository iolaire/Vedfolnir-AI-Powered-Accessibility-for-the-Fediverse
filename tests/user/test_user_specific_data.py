#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test that the dashboard shows user-specific data by directly testing the database methods
"""

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User

def test_user_specific_stats():
    """Test that get_processing_stats returns user-specific data"""
    print("=== Testing User-Specific Statistics ===")
    
    config = Config()
    db_manager = DatabaseManager(config)
    
    # Get all users
    with db_manager.get_session() as session:
        users = session.query(User).all()
        
        print(f"Found {len(users)} users in system:")
        for user in users:
            print(f"  - ID: {user.id}, Username: {user.username}, Role: {user.role}")
    
    # Test stats for each user
    for user in users:
        print(f"\n--- Testing stats for user {user.username} (ID: {user.id}) ---")
        
        try:
            # Get user-specific stats
            stats = db_manager.get_processing_stats(platform_aware=True, user_id=user.id)
            print(f"User-specific stats: {stats}")
            
            # Get global stats for comparison
            global_stats = db_manager.get_processing_stats(platform_aware=False)
            print(f"Global stats: {global_stats}")
            
            # Check if user stats are different from global stats
            if (stats['total_posts'] != global_stats['total_posts'] or 
                stats['total_images'] != global_stats['total_images']):
                print("✅ User stats are different from global stats (good!)")
            else:
                if stats['total_posts'] == 0 and stats['total_images'] == 0:
                    print("✅ User has no data (0 posts/images) - this is expected for test users")
                else:
                    print("⚠️  User stats match global stats - may indicate filtering issue")
            
        except Exception as e:
            print(f"❌ Error getting stats for user {user.username}: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_user_specific_stats()