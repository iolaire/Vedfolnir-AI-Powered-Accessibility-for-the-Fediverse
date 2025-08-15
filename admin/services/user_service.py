# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin User Management Service"""

from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from models import User, UserRole

class UserService:
    """Service for admin user management operations"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).all()
        finally:
            session.close()
    
    def get_admin_count(self) -> int:
        """Get count of active admin users"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
        finally:
            session.close()
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole, is_active: bool = True) -> Optional[dict]:
        """Create a new user and return user data dict"""
        session = self.db_manager.get_session()
        try:
            # Check for existing username/email
            existing = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing:
                if existing.username == username:
                    raise ValueError(f'Username {username} already exists')
                else:
                    raise ValueError(f'Email {email} is already registered')
            
            user = User(
                username=username,
                email=email,
                role=role,
                is_active=is_active
            )
            user.set_password(password)
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Extract user data before session closes
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'is_active': user.is_active
            }
            return user_data
            
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
    
    def update_user(self, user_id: int, username: str, email: str, 
                   role: UserRole, is_active: bool, password: Optional[str] = None) -> bool:
        """Update an existing user"""
        session = self.db_manager.get_session()
        try:
            # Single optimized query to get user and check conflicts
            from sqlalchemy import and_, or_
            
            # Get user and check for conflicts in one query using subquery
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Optimized conflict check using EXISTS
            conflict_exists = session.query(
                session.query(User).filter(
                    and_(
                        or_(User.username == username, User.email == email),
                        User.id != user_id
                    )
                ).exists()
            ).scalar()
            
            if conflict_exists:
                # Only query for specific conflict details if needed
                existing = session.query(User).filter(
                    and_(
                        or_(User.username == username, User.email == email),
                        User.id != user_id
                    )
                ).first()
                
                if existing.username == username:
                    raise ValueError(f'Username {username} is already taken')
                else:
                    raise ValueError(f'Email {email} is already registered')
            
            user.username = username
            user.email = email
            user.role = role
            user.is_active = is_active
            
            if password:
                user.set_password(password)
            
            session.commit()
            return True
            
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user"""
        session = self.db_manager.get_session()
        try:
            user = session.query(User).get(user_id)
            if user:
                session.delete(user)
                session.commit()
                return True
            return False
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()