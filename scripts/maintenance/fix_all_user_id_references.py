# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix All User ID References

This script fixes all remaining user_id references across all models to use proper
foreign key relationships instead of string-based usernames.

Models to fix:
- Post (already fixed)
- ProcessingRun
- Any other models with string-based user_id fields
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User, Post, ProcessingRun

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AllUserIdFixer:
    """Fix all user_id references to use proper foreign keys"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        
    def analyze_processing_runs(self):
        """Analyze ProcessingRun user_id values"""
        logger.info("=== Analyzing ProcessingRun Data ===")
        
        with self.db_manager.get_session() as session:
            runs = session.query(ProcessingRun).all()
            logger.info(f"ProcessingRun records: {len(runs)}")
            
            if not runs:
                return {}
            
            user_id_types = {}
            for run in runs:
                user_id_str = str(run.user_id)
                if user_id_str not in user_id_types:
                    user_id_types[user_id_str] = 0
                user_id_types[user_id_str] += 1
            
            logger.info("ProcessingRun user_id values:")
            for user_id, count in user_id_types.items():
                logger.info(f'  - "{user_id}": {count} runs')
            
            return user_id_types
    
    def create_user_mapping(self):
        """Create mapping from usernames to User IDs"""
        logger.info("=== Creating User Mapping ===")
        
        mapping = {}
        
        with self.db_manager.get_session() as session:
            users = session.query(User).all()
            for user in users:
                mapping[user.username] = user.id
                mapping[str(user.id)] = user.id  # Handle already-correct numeric IDs
                logger.info(f"Mapped '{user.username}' -> User ID {user.id}")
        
        return mapping
    
    def migrate_processing_runs(self, user_mapping):
        """Migrate ProcessingRun user_id values"""
        logger.info("=== Migrating ProcessingRun user_id Values ===")
        
        with self.db_manager.get_session() as session:
            try:
                runs_updated = 0
                runs_failed = 0
                
                runs = session.query(ProcessingRun).all()
                for run in runs:
                    current_user_id = str(run.user_id)
                    
                    if current_user_id in user_mapping:
                        new_user_id = user_mapping[current_user_id]
                        logger.info(f"Updating ProcessingRun {run.id}: '{current_user_id}' -> {new_user_id}")
                        run.user_id = str(new_user_id)  # Keep as string for now
                        runs_updated += 1
                    else:
                        logger.warning(f"No mapping found for ProcessingRun {run.id} user_id: '{current_user_id}'")
                        runs_failed += 1
                
                session.commit()
                logger.info(f"Migration complete: {runs_updated} runs updated, {runs_failed} failed")
                
                return runs_updated, runs_failed
                
            except Exception as e:
                session.rollback()
                logger.error(f"Migration failed: {e}")
                raise
    
    def update_processing_run_schema(self):
        """Update ProcessingRun schema to use proper foreign keys"""
        logger.info("=== Updating ProcessingRun Schema ===")
        
        with self.db_manager.get_session() as session:
            try:
                # Convert user_id column to INTEGER
                logger.info("Converting ProcessingRun.user_id to INTEGER type...")
                session.execute(text("""
                    ALTER TABLE processing_runs 
                    MODIFY COLUMN user_id INT NOT NULL
                """))
                
                # Add foreign key constraint
                logger.info("Adding foreign key constraint...")
                session.execute(text("""
                    ALTER TABLE processing_runs 
                    ADD CONSTRAINT fk_processing_runs_user_id 
                    FOREIGN KEY (user_id) REFERENCES users(id) 
                    ON DELETE CASCADE
                """))
                
                session.commit()
                logger.info("ProcessingRun schema update complete")
                
            except Exception as e:
                session.rollback()
                logger.error(f"ProcessingRun schema update failed: {e}")
                raise
    
    def verify_all_migrations(self):
        """Verify all migrations were successful"""
        logger.info("=== Verifying All Migrations ===")
        
        with self.db_manager.get_session() as session:
            # Check Posts
            posts = session.query(Post).all()
            invalid_posts = 0
            for post in posts:
                user = session.query(User).filter_by(id=post.user_id).first()
                if not user:
                    invalid_posts += 1
                    logger.warning(f"Post {post.id} has invalid user_id: {post.user_id}")
            
            logger.info(f"Posts: {len(posts)} total, {invalid_posts} invalid")
            
            # Check ProcessingRuns
            runs = session.query(ProcessingRun).all()
            invalid_runs = 0
            for run in runs:
                user = session.query(User).filter_by(id=run.user_id).first()
                if not user:
                    invalid_runs += 1
                    logger.warning(f"ProcessingRun {run.id} has invalid user_id: {run.user_id}")
            
            logger.info(f"ProcessingRuns: {len(runs)} total, {invalid_runs} invalid")
            
            # Test user-specific queries
            admin_user = session.query(User).filter_by(username='admin').first()
            if admin_user:
                user_posts = session.query(Post).filter_by(user_id=admin_user.id).all()
                user_runs = session.query(ProcessingRun).filter_by(user_id=admin_user.id).all()
                
                logger.info(f"Admin user ({admin_user.id}) has {len(user_posts)} posts and {len(user_runs)} processing runs")
            
            return invalid_posts == 0 and invalid_runs == 0
    
    def run_complete_fix(self):
        """Run the complete fix process"""
        logger.info("=== Starting Complete User ID Fix ===")
        
        try:
            # Step 1: Analyze current state
            processing_run_analysis = self.analyze_processing_runs()
            
            # Step 2: Create user mapping
            user_mapping = self.create_user_mapping()
            
            if not user_mapping:
                logger.error("No user mapping could be created. Fix aborted.")
                return False
            
            # Step 3: Migrate ProcessingRun data
            if processing_run_analysis:
                updated, failed = self.migrate_processing_runs(user_mapping)
                
                if failed > 0:
                    logger.error(f"ProcessingRun migration had {failed} failures. Check logs and fix manually.")
                    return False
            
            # Step 4: Update ProcessingRun schema
            self.update_processing_run_schema()
            
            # Step 5: Verify all migrations
            success = self.verify_all_migrations()
            
            if success:
                logger.info("=== Complete User ID Fix Completed Successfully ===")
                logger.info("All models now use proper foreign key relationships!")
            else:
                logger.error("=== Fix Completed with Issues ===")
                logger.error("Please review the logs and fix issues manually")
            
            return success
            
        except Exception as e:
            logger.error(f"Complete fix failed with error: {e}")
            return False

def main():
    """Main entry point"""
    fixer = AllUserIdFixer()
    success = fixer.run_complete_fix()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()