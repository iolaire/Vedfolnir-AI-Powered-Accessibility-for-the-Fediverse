#!/usr/bin/env python3
"""
Create compliance tables in the database
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.session.manager import unified_session_manager
from models import Base

def create_compliance_tables():
    """Create compliance tables in the database"""
    try:
        print("Creating compliance tables...")
        
        # Get the database engine from unified_session_manager
        engine = unified_session_manager.engine
        
        # Create the compliance tables
        Base.metadata.create_all(engine)
        
        print("✓ Compliance tables created successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error creating compliance tables: {e}")
        return False

if __name__ == "__main__":
    print("Compliance Tables Creation Script")
    print("=" * 40)
    
    if create_compliance_tables():
        print("Tables created successfully!")
    else:
        sys.exit(1)