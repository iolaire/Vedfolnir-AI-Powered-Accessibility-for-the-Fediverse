#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Migration Script: Move from Database Sessions to Flask Sessions

This script migrates the application from database-based session management
to Flask's built-in session management using secure cookies.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from database import DatabaseManager
from migrations.remove_user_sessions import upgrade

def main():
    """Run the migration to Flask sessions"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize configuration and database
        config = Config()
        db_manager = DatabaseManager(config)
        
        logger.info("Starting migration to Flask-based session management...")
        
        # Run the migration
        with db_manager.get_session() as session:
            upgrade(session)
        
        logger.info("Migration completed successfully!")
        logger.info("The application now uses Flask's secure cookie sessions instead of database sessions.")
        logger.info("Users will need to log in again after this migration.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())