#!/usr/bin/env python3
"""
MySQL Schema Generation Script for Vedfolnir
Generates CREATE TABLE statements for MySQL database migration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, MetaData
from sqlalchemy.schema import CreateTable
from sqlalchemy.engine import create_mock_engine
from models import Base
from config import Config

def generate_mysql_schema():
    """Generate MySQL CREATE TABLE statements"""
    
    # Create a mock MySQL engine for schema generation
    def dump(sql, *multiparams, **params):
        print(str(sql.compile(dialect=engine.dialect)) + ";")
        print("")
    
    engine = create_mock_engine('mysql+pymysql://', dump)
    
    print("-- Vedfolnir MySQL Database Schema")
    print("-- Generated for MySQL with utf8mb4 charset")
    print("-- Database: database_user_1d7b0d0696a20")
    print("-- Authentication: Unix socket")
    print("")
    
    print("-- Set charset and collation")
    print("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print("SET CHARACTER SET utf8mb4;")
    print("")
    
    # Generate CREATE TABLE statements for all models
    Base.metadata.create_all(engine, checkfirst=False)
    
    print("-- Indexes and constraints are automatically created by the above statements")
    print("-- Foreign key constraints are included in the table definitions")
    print("")
    print("-- Migration complete!")

if __name__ == "__main__":
    generate_mysql_schema()
