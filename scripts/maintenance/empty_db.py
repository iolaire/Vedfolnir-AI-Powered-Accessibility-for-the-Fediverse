#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
from config import Config
from models import Base
from sqlalchemy import create_engine

def empty_database():
    """Empty the database by dropping and recreating all tables"""
    config = Config()
    
    # Get database path
    db_path = os.path.join(os.getcwd(), "MySQL database")
    print(f"Emptying database at {db_path}")
    
    # Create engine
    engine = create_engine(config.storage.database_url)
    
    # Drop all tables
    Base.metadata.drop_all(engine)
    
    # Recreate all tables
    Base.metadata.create_all(engine)
    
    print("Database emptied successfully")

if __name__ == "__main__":
    empty_database()
