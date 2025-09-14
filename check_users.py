#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Check what users exist in the system
"""

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import User

def check_users():
    """Check what users exist in the system"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        users = session.query(User).all()
        
        print("=== Users in System ===")
        for user in users:
            print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Role: {user.role}, Active: {user.is_active}")
        
        if not users:
            print("No users found in system")
        
        return users

if __name__ == "__main__":
    check_users()