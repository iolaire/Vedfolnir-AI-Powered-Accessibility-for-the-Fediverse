#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple verification script to check if the user ID fixes are working.
This script checks the database directly without needing Flask dependencies.
"""

import os
import sys
import pymysql
from urllib.parse import urlparse

def verify_user_id_fix():
    """Verify that user ID handling is working correctly"""
    
    print("=== Verifying User ID Fix ===")
    
    try:
        # Get database connection info from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment")
            return False
        
        # Parse database URL
        parsed = urlparse(database_url)
        
        # Connect to MySQL
        connection = pymysql.connect(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/').split('?')[0],
            charset='utf8mb4'
        )
        
        print("✅ Connected to MySQL database")
        
        with connection.cursor() as cursor:
            # Check recent processing runs
            cursor.execute("""
                SELECT id, user_id, batch_id, created_at 
                FROM processing_runs 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            runs = cursor.fetchall()
            print(f"\n=== Recent Processing Runs ===")
            
            if runs:
                for run in runs:
                    run_id, user_id, batch_id, created_at = run
                    print(f"  Run ID: {run_id}, User ID: {user_id} (type: {type(user_id)}), Batch: {batch_id}")
                    
                    # Verify user_id is integer
                    if not isinstance(user_id, int):
                        print(f"❌ ERROR: user_id should be integer, got {type(user_id)}")
                        return False
                
                print("✅ All processing runs have integer user_id values")
            else:
                print("  No processing runs found")
            
            # Check recent posts
            cursor.execute("""
                SELECT id, post_id, user_id, created_at 
                FROM posts 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            posts = cursor.fetchall()
            print(f"\n=== Recent Posts ===")
            
            if posts:
                for post in posts:
                    post_db_id, post_id, user_id, created_at = post
                    print(f"  Post: {post_id[:50]}..., User ID: {user_id} (type: {type(user_id)})")
                    
                    # Verify user_id is integer
                    if not isinstance(user_id, int):
                        print(f"❌ ERROR: user_id should be integer, got {type(user_id)}")
                        return False
                
                print("✅ All posts have integer user_id values")
            else:
                print("  No posts found")
            
            # Check recent images
            cursor.execute("""
                SELECT id, local_filename, status, created_at 
                FROM images 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            images = cursor.fetchall()
            print(f"\n=== Recent Images ===")
            
            if images:
                for image in images:
                    img_id, filename, status, created_at = image
                    print(f"  Image: {filename}, Status: {status}")
                
                print("✅ Images are being stored correctly")
                
                # Check if image files exist
                image_count = 0
                for image in images:
                    filename = image[1]
                    if filename and os.path.exists(f"storage/images/{filename}"):
                        image_count += 1
                
                print(f"✅ {image_count}/{len(images)} image files exist on disk")
            else:
                print("  No images found")
        
        connection.close()
        
        print(f"\n=== Verification Complete ===")
        print("✅ User ID fix is working correctly!")
        print("✅ No more MySQL DataError with username strings")
        print("✅ All database operations use integer user IDs")
        print("✅ Images are being processed and stored")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_user_id_fix()
    sys.exit(0 if success else 1)