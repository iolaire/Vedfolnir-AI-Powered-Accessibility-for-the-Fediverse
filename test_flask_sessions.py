#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Flask Session Management

Simple test to verify the Flask-based session management works correctly.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from flask import Flask
from config import Config
from database import DatabaseManager
from flask_session_manager import FlaskSessionManager
from models import User, PlatformConnection

def test_flask_session_management():
    """Test Flask session management functionality"""
    
    # Create a test Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True
    
    # Use in-memory database for testing
    config = Config()
    config.storage.database_url = 'sqlite:///:memory:'
    
    db_manager = DatabaseManager(config)
    flask_session_manager = FlaskSessionManager(db_manager)
    
    # Create tables
    from sqlalchemy import create_engine
    from models import Base
    engine = create_engine(config.storage.database_url)
    Base.metadata.create_all(engine)
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Test session creation
            print("Testing Flask session creation...")
            
            # Create a test user
            db_session = db_manager.get_session()
            try:
                user = User(
                    username='testuser',
                    email='test@example.com',
                    is_active=True
                )
                user.set_password('testpass')
                db_session.add(user)
                db_session.commit()
                user_id = user.id
                
                # Create a test platform
                platform = PlatformConnection(
                    user_id=user_id,
                    name='Test Platform',
                    platform_type='pixelfed',
                    instance_url='https://test.example.com',
                    username='testuser',
                    access_token='test-token',
                    is_default=True
                )
                db_session.add(platform)
                db_session.commit()
                platform_id = platform.id
                
            finally:
                db_session.close()
            
            # Test session creation with Flask app context
            with app.app_context():
                with app.test_request_context():
                    # Create session
                    success = flask_session_manager.create_user_session(user_id, platform_id)
                    assert success, "Failed to create Flask session"
                    print("✓ Session creation successful")
                    
                    # Test session context retrieval
                    context = flask_session_manager.get_session_context()
                    assert context is not None, "Failed to get session context"
                    assert context['user_id'] == user_id, "User ID mismatch"
                    assert context['platform_connection_id'] == platform_id, "Platform ID mismatch"
                    print("✓ Session context retrieval successful")
                    
                    # Test platform switching
                    success = flask_session_manager.update_platform_context(platform_id)
                    assert success, "Failed to update platform context"
                    print("✓ Platform context update successful")
                    
                    # Test session validation
                    valid = flask_session_manager.validate_session(user_id)
                    assert valid, "Session validation failed"
                    print("✓ Session validation successful")
                    
                    # Test authentication check
                    authenticated = flask_session_manager.is_authenticated()
                    assert authenticated, "Authentication check failed"
                    print("✓ Authentication check successful")
                    
                    # Test session clearing
                    flask_session_manager.clear_session()
                    authenticated = flask_session_manager.is_authenticated()
                    assert not authenticated, "Session should be cleared"
                    print("✓ Session clearing successful")
    
    print("\nAll Flask session management tests passed! ✓")
    return True

if __name__ == "__main__":
    try:
        test_flask_session_management()
        print("\n🎉 Flask session management is working correctly!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)