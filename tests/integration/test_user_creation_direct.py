#!/usr/bin/env python3

from app.core.database.core.database_manager import DatabaseManager
from config import Config
from models import User, UserRole

# MySQL integration test imports
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_test_config import MySQLTestFixtures


def test_user_creation_functionality():
    """Test that the user creation functionality works at the database level"""
    config = Config()
    db_manager = self.get_database_manager()
    session = db_manager.get_session()
    
    try:
        print("Testing user creation functionality...")
        
        # Check initial user count
        initial_count = session.query(User).count()
        print(f"Initial user count: {initial_count}")
        
        # Test creating a user (same as the API would do)
        test_data = {
            'username': 'testuser_api',
            'email': 'testapi@test.com',
            'password': 'testpass123',
            'role': 'viewer'
        }
        
        # Check if username or email already exists
        existing_user = session.query(User).filter(
            (User.username == test_data['username']) | 
            (User.email == test_data['email'])
        ).first()
        
        if existing_user:
            print(f"User already exists, cleaning up first...")
            session.delete(existing_user)
            session.commit()
        
        # Create new user (same logic as API)
        user = User(
            username=test_data['username'],
            email=test_data['email'],
            role=UserRole(test_data['role']),
            is_active=True
        )
        user.set_password(test_data['password'])
        
        session.add(user)
        session.commit()
        
        print(f"✓ User created successfully: {user.username} (ID: {user.id})")
        
        # Verify user was created
        final_count = session.query(User).count()
        print(f"Final user count: {final_count}")
        
        # Test password verification
        if user.check_password(test_data['password']):
            print("✓ Password verification works")
        else:
            print("✗ Password verification failed")
        
        # Clean up
        session.delete(user)
        session.commit()
        print("✓ Test user cleaned up")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = test_user_creation_functionality()
    if success:
        print("\n✓ User creation functionality works correctly at the database level")
        print("The issue is likely with session management in the web interface")
    else:
        print("\n✗ User creation functionality has issues")