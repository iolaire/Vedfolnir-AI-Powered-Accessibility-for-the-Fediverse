#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Fix encryption key mismatch for platform credentials
"""

import os
from config import Config
from database import DatabaseManager
from models import PlatformConnection

def fix_encryption_key():
    """Fix encryption key mismatch by regenerating the key"""
    
    # Check if encryption key exists
    config = Config()
    current_key = os.environ.get('PLATFORM_ENCRYPTION_KEY')
    
    if not current_key:
        print("No PLATFORM_ENCRYPTION_KEY found in environment")
        print("Generating new encryption key...")
        
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key().decode()
        
        print(f"New encryption key: {new_key}")
        print("\nAdd this to your .env file:")
        print(f"PLATFORM_ENCRYPTION_KEY={new_key}")
        print("\nNote: You'll need to re-add your platform connections after setting this key.")
        
        return new_key
    else:
        print(f"Current encryption key: {current_key}")
        
        # Try to decrypt existing platforms
        db_manager = DatabaseManager(config)
        session = db_manager.get_session()
        
        try:
            platforms = session.query(PlatformConnection).all()
            print(f"Found {len(platforms)} platform connections")
            
            for platform in platforms:
                try:
                    # Try to access encrypted fields
                    _ = platform.access_token
                    print(f"✅ Platform '{platform.name}' credentials OK")
                except Exception as e:
                    print(f"❌ Platform '{platform.name}' credentials failed: {e}")
                    
        finally:
            session.close()
            
        return current_key

if __name__ == "__main__":
    fix_encryption_key()