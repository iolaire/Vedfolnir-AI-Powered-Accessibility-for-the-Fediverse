# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix User ID Data Model Inconsistency

This script fixes the critical data model issue where Post.user_id stores platform usernames
instead of proper foreign key references to User.id. This creates data integrity issues
and prevents proper user-specific queries.

The fix:
1. Updates Post model to use proper foreign key to User table
2. Migrates existing data to use proper User IDs
3. Updates all queries to use proper relationships
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import text, Integer, ForeignKey
from sqlalchemy.exc import SQLAlchemyError

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, Post, Image, PlatformConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserIdDataModelFixer:
    """Fix the user_id data model inconsistency"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
    def analyze_current_state(self):
        """Analyze the current state of user_id data"""
        logger.info("=== Analyzing Current Data Model State ===")
        
        with self.db_manager.get_session() as session:
            # Check users
            users = session.query(User).all()
            logger.info(f"Users in database: {len(users)}")
            for user in users:
                logger.info(f"  - User ID: {user.id}, Username: {user.username}")
            
            # Check posts and their user_id values
            posts = session.query(Post).all()
            logger.info(f"Posts in database: {len(posts)}")
            
            user_id_types = {}
            for post in posts:
                user_id_str = str(post.user_id)
                if user_id_str not in user_id_types:
                    user_id_types[user_id_str] = 0
                user_id_types[user_id_str] += 1
            
            logger.info("Post user_id values found:")
            for user_id, count in user_id_types.items():
                logger.info(f"  - '{user_id}': {count} posts")
            
            # Check platform connections
            platforms = session.query(PlatformConnection).all()
            logger.info(f"Platform connections: {len(platforms)}")
            for platform in platforms:
                logger.info(f"  - Platform ID: {platform.id}, User ID: {platform.user_id}, Username: {platform.username}")
            
            return {
                'users': users,
                'posts': posts,
                'platforms': platforms,
                'user_id_types': user_id_types
            }
    
    def create_user_mapping(self, analysis_data):
        """Create mapping from platform usernames to User IDs"""
        logger.info("=== Creating User Mapping ===")
        
        mapping = {}
        
        # Map platform usernames to User IDs through PlatformConnection
        for platform in analysis_data['platforms']:
            platform_username = platform.username
            user_id = platform.user_id
            
            if platform_username and user_id:
                # Map both plain username and @username formats
                mapping[platform_username] = user_id
                mapping[f"@{platform_username}"] = user_id
                logger.info(f"Mapped platform username '{platform_username}' and '@{platform_username}' -> User ID {user_id}")
        
        # Check for unmapped user_id values in posts
        unmapped = []
        for user_id_str in analysis_data['user_id_types'].keys():
            if user_id_str not in mapping:
                # Check if it's already a valid User ID (numeric string)
                try:
                    numeric_id = int(user_id_str)
                    with self.db_manager.get_session() as session:
                        user = session.query(User).filter_by(id=numeric_id).first()
                        if user:
                            mapping[user_id_str] = numeric_id
                            logger.info(f"Mapped numeric user_id '{user_id_str}' -> User ID {numeric_id} (already correct)")
                            continue
                except ValueError:
                    pass
                
                # Try to find by username in User table (handle @ prefix)
                clean_username = user_id_str.lstrip('@')
                
                with self.db_manager.get_session() as session:
                    user = session.query(User).filter_by(username=clean_username).first()
                    if user:
                        mapping[user_id_str] = user.id
                        logger.info(f"Mapped username '{user_id_str}' -> User ID {user.id}")
                    else:
                        # Try to match with platform connections by username
                        platform = session.query(PlatformConnection).filter_by(username=clean_username).first()
                        if platform:
                            mapping[user_id_str] = platform.user_id
                            logger.info(f"Mapped platform username '{user_id_str}' -> User ID {platform.user_id}")
                        else:
                            unmapped.append(user_id_str)
        
        if unmapped:
            logger.warning(f"Unmapped user_id values: {unmapped}")
            logger.warning("These posts may need manual review")
        
        return mapping
    
    def backup_current_data(self):
        """Create backup of current data before migration"""
        logger.info("=== Creating Data Backup ===")
        
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"storage/backups/user_id_fix_backup_{backup_timestamp}.sql"
        
        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        
        try:
            # Create MySQL dump of relevant tables
            import subprocess
            
            # Get database connection info from config
            db_url = self.config.database_url
            # Parse connection string to get components
            # mysql+pymysql://user:password@host:port/database
            import re
            match = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):?(\d+)?/([^?]+)', db_url)
            if match:
                user, password, host, port, database = match.groups()
                port = port or '3306'
                
                cmd = [
                    'mysqldump',
                    f'--host={host}',
                    f'--port={port}',
                    f'--user={user}',
                    f'--password={password}',
                    '--single-transaction',
                    '--routines',
                    '--triggers',
                    database,
                    'users', 'posts', 'images', 'platform_connections'
                ]
                
                with open(backup_file, 'w') as f:
                    subprocess.run(cmd, stdout=f, check=True)
                
                logger.info(f"Backup created: {backup_file}")
                return backup_file
            else:
                logger.error("Could not parse database URL for backup")
                return None
                
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    def migrate_post_user_ids(self, user_mapping):
        """Migrate Post.user_id from usernames to proper User IDs"""
        logger.info("=== Migrating Post user_id Values ===")
        
        with self.db_manager.get_session() as session:
            try:
                posts_updated = 0
                posts_failed = 0
                
                posts = session.query(Post).all()
                for post in posts:
                    current_user_id = str(post.user_id)
                    
                    if current_user_id in user_mapping:
                        new_user_id = user_mapping[current_user_id]
                        logger.info(f"Updating Post {post.id}: '{current_user_id}' -> {new_user_id}")
                        post.user_id = str(new_user_id)  # Keep as string for now
                        posts_updated += 1
                    else:
                        logger.warning(f"No mapping found for Post {post.id} user_id: '{current_user_id}'")
                        posts_failed += 1
                
                session.commit()
                logger.info(f"Migration complete: {posts_updated} posts updated, {posts_failed} failed")
                
                return posts_updated, posts_failed
                
            except Exception as e:
                session.rollback()
                logger.error(f"Migration failed: {e}")
                raise
    
    def update_database_schema(self):
        """Update the database schema to use proper foreign keys"""
        logger.info("=== Updating Database Schema ===")
        
        with self.db_manager.get_session() as session:
            try:
                # First, convert user_id column to INTEGER
                logger.info("Converting Post.user_id to INTEGER type...")
                session.execute(text("""
                    ALTER TABLE posts 
                    MODIFY COLUMN user_id INT NOT NULL
                """))
                
                # Add foreign key constraint
                logger.info("Adding foreign key constraint...")
                session.execute(text("""
                    ALTER TABLE posts 
                    ADD CONSTRAINT fk_posts_user_id 
                    FOREIGN KEY (user_id) REFERENCES users(id) 
                    ON DELETE CASCADE
                """))
                
                session.commit()
                logger.info("Schema update complete")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Schema update failed: {e}")
                raise
    
    def update_model_definition(self):
        """Update the Post model definition in models.py"""
        logger.info("=== Updating Model Definition ===")
        
        # Read current models.py
        with open('models.py', 'r') as f:
            content = f.read()
        
        # Replace the user_id field definition
        old_definition = 'user_id = Column(String(200), nullable=False)'
        new_definition = 'user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)'
        
        if old_definition in content:
            content = content.replace(old_definition, new_definition)
            
            # Add relationship if not present
            if 'user = relationship("User")' not in content:
                # Find the relationships section and add it
                relationships_section = '    # Relationships'
                if relationships_section in content:
                    content = content.replace(
                        relationships_section,
                        relationships_section + '\n    user = relationship("User")'
                    )
            
            # Write updated content
            with open('models.py', 'w') as f:
                f.write(content)
            
            logger.info("Model definition updated in models.py")
        else:
            logger.warning("Could not find user_id definition to update")
    
    def update_query_methods(self):
        """Update database manager methods to use proper relationships"""
        logger.info("=== Updating Query Methods ===")
        
        # Read database manager file
        db_manager_file = 'app/core/database/core/database_manager.py'
        with open(db_manager_file, 'r') as f:
            content = f.read()
        
        # Replace string conversions with proper integer usage
        replacements = [
            ('Post.user_id == str(user_id)', 'Post.user_id == user_id'),
            ('post_query = session.query(Post).filter(Post.user_id == str(user_id))', 
             'post_query = session.query(Post).filter(Post.user_id == user_id)'),
            ('image_query = session.query(Image).join(Post).filter(Post.user_id == str(user_id))',
             'image_query = session.query(Image).join(Post).filter(Post.user_id == user_id)'),
        ]
        
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                logger.info(f"Updated query: {old[:50]}...")
        
        # Write updated content
        with open(db_manager_file, 'w') as f:
            f.write(content)
        
        logger.info("Query methods updated")
    
    def verify_migration(self):
        """Verify the migration was successful"""
        logger.info("=== Verifying Migration ===")
        
        with self.db_manager.get_session() as session:
            # Check that all posts have valid user_id references
            posts = session.query(Post).all()
            valid_posts = 0
            invalid_posts = 0
            
            for post in posts:
                user = session.query(User).filter_by(id=post.user_id).first()
                if user:
                    valid_posts += 1
                else:
                    invalid_posts += 1
                    logger.warning(f"Post {post.id} has invalid user_id: {post.user_id}")
            
            logger.info(f"Verification complete: {valid_posts} valid, {invalid_posts} invalid")
            
            # Test user-specific queries
            admin_user = session.query(User).filter_by(username='admin').first()
            if admin_user:
                user_posts = session.query(Post).filter_by(user_id=admin_user.id).all()
                user_images = session.query(Image).join(Post).filter(Post.user_id == admin_user.id).all()
                
                logger.info(f"Admin user ({admin_user.id}) has {len(user_posts)} posts and {len(user_images)} images")
            
            return invalid_posts == 0
    
    def run_migration(self, create_backup=True):
        """Run the complete migration process"""
        logger.info("=== Starting User ID Data Model Migration ===")
        
        try:
            # Step 1: Analyze current state
            analysis = self.analyze_current_state()
            
            # Step 2: Create user mapping
            user_mapping = self.create_user_mapping(analysis)
            
            if not user_mapping:
                logger.error("No user mapping could be created. Migration aborted.")
                return False
            
            # Step 3: Create backup
            if create_backup:
                backup_file = self.backup_current_data()
                if not backup_file:
                    logger.warning("Backup failed, but continuing with migration")
            
            # Step 4: Migrate data
            updated, failed = self.migrate_post_user_ids(user_mapping)
            
            if failed > 0:
                logger.error(f"Migration had {failed} failures. Check logs and fix manually.")
                return False
            
            # Step 5: Update schema (commented out for safety - run manually)
            # self.update_database_schema()
            
            # Step 6: Update model definition (commented out for safety - run manually)
            # self.update_model_definition()
            
            # Step 7: Update query methods (commented out for safety - run manually)
            # self.update_query_methods()
            
            # Step 8: Verify migration
            success = self.verify_migration()
            
            if success:
                logger.info("=== Migration Completed Successfully ===")
                logger.info("Next steps:")
                logger.info("1. Review the migrated data")
                logger.info("2. Run schema update manually if needed")
                logger.info("3. Update model definitions")
                logger.info("4. Test the web interface")
            else:
                logger.error("=== Migration Completed with Issues ===")
                logger.error("Please review the logs and fix issues manually")
            
            return success
            
        except Exception as e:
            logger.error(f"Migration failed with error: {e}")
            return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix User ID Data Model')
    parser.add_argument('--analyze-only', action='store_true', 
                       help='Only analyze current state, do not migrate')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip creating backup')
    
    args = parser.parse_args()
    
    fixer = UserIdDataModelFixer()
    
    if args.analyze_only:
        fixer.analyze_current_state()
    else:
        success = fixer.run_migration(create_backup=not args.no_backup)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()