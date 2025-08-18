#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin User Service

Provides user management functionality for admin interface.
"""

from typing import List, Optional, Dict, Any
from werkzeug.security import generate_password_hash
from models import User, UserRole
from datetime import datetime, timezone

class UserService:
    """Service for managing users in admin interface"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        # Add unified session manager reference
        self._unified_session_manager = None
    
    @property
    def unified_session_manager(self):
        if self._unified_session_manager is None:
            try:
                from flask import current_app
                self._unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            except RuntimeError:
                # Outside Flask context
                pass
        return self._unified_session_manager
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                return session.query(User).all()
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                return session.query(User).all()
            finally:
                session.close()
    
    def get_admin_count(self) -> int:
        """Get count of active admin users"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                return session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                return session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
            finally:
                session.close()
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole = UserRole.VIEWER, is_active: bool = True) -> Dict[str, Any]:
        """Create a new user and return user data dict"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                # Check for existing username/email
                existing = session.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first()
                
                if existing:
                    if existing.username == username:
                        return {'success': False, 'error': 'Username already exists'}
                    else:
                        return {'success': False, 'error': 'Email already exists'}
                
                # Create new user
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    role=role,
                    is_active=is_active,
                    created_at=datetime.now(timezone.utc)
                )
                
                session.add(user)
                session.flush()  # Get the ID
                
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat()
                }
                
                return {'success': True, 'user': user_data}
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                # Check for existing username/email
                existing = session.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first()
                
                if existing:
                    if existing.username == username:
                        return {'success': False, 'error': 'Username already exists'}
                    else:
                        return {'success': False, 'error': 'Email already exists'}
                
                # Create new user
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    role=role,
                    is_active=is_active,
                    created_at=datetime.now(timezone.utc)
                )
                
                session.add(user)
                session.commit()
                session.flush()  # Get the ID
                
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat()
                }
                
                return {'success': True, 'user': user_data}
            except Exception as e:
                session.rollback()
                return {'success': False, 'error': str(e)}
            finally:
                session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                return session.query(User).filter_by(id=user_id).first()
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                return session.query(User).filter_by(id=user_id).first()
            finally:
                session.close()
    
    def update_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Update user and return result"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                # Update allowed fields
                allowed_fields = ['username', 'email', 'role', 'is_active']
                for field, value in kwargs.items():
                    if field in allowed_fields:
                        if field == 'role' and isinstance(value, str):
                            value = UserRole(value)
                        setattr(user, field, value)
                
                user.updated_at = datetime.now(timezone.utc)
                
                return {'success': True, 'message': 'User updated successfully'}
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                # Update allowed fields
                allowed_fields = ['username', 'email', 'role', 'is_active']
                for field, value in kwargs.items():
                    if field in allowed_fields:
                        if field == 'role' and isinstance(value, str):
                            value = UserRole(value)
                        setattr(user, field, value)
                
                user.updated_at = datetime.now(timezone.utc)
                session.commit()
                
                return {'success': True, 'message': 'User updated successfully'}
            except Exception as e:
                session.rollback()
                return {'success': False, 'error': str(e)}
            finally:
                session.close()
    
    def delete_user(self, user_id: int, current_user_id: int) -> Dict[str, Any]:
        """Delete user (soft delete by deactivating)"""
        if user_id == current_user_id:
            return {'success': False, 'error': 'Cannot delete your own account'}
        
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                # Check if this is the last admin
                if user.role == UserRole.ADMIN:
                    admin_count = session.query(User).filter_by(
                        role=UserRole.ADMIN, is_active=True
                    ).count()
                    if admin_count <= 1:
                        return {'success': False, 'error': 'Cannot delete the last admin user'}
                
                # Soft delete by deactivating
                user.is_active = False
                user.updated_at = datetime.now(timezone.utc)
                
                return {'success': True, 'message': 'User deactivated successfully'}
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                # Check if this is the last admin
                if user.role == UserRole.ADMIN:
                    admin_count = session.query(User).filter_by(
                        role=UserRole.ADMIN, is_active=True
                    ).count()
                    if admin_count <= 1:
                        return {'success': False, 'error': 'Cannot delete the last admin user'}
                
                # Soft delete by deactivating
                user.is_active = False
                user.updated_at = datetime.now(timezone.utc)
                session.commit()
                
                return {'success': True, 'message': 'User deactivated successfully'}
            except Exception as e:
                session.rollback()
                return {'success': False, 'error': str(e)}
            finally:
                session.close()
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                total_users = session.query(User).count()
                active_users = session.query(User).filter_by(is_active=True).count()
                admin_users = session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
                reviewer_users = session.query(User).filter_by(role=UserRole.REVIEWER, is_active=True).count()
                viewer_users = session.query(User).filter_by(role=UserRole.VIEWER, is_active=True).count()
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'inactive_users': total_users - active_users,
                    'admin_users': admin_users,
                    'reviewer_users': reviewer_users,
                    'viewer_users': viewer_users
                }
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                total_users = session.query(User).count()
                active_users = session.query(User).filter_by(is_active=True).count()
                admin_users = session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
                reviewer_users = session.query(User).filter_by(role=UserRole.REVIEWER, is_active=True).count()
                viewer_users = session.query(User).filter_by(role=UserRole.VIEWER, is_active=True).count()
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'inactive_users': total_users - active_users,
                    'admin_users': admin_users,
                    'reviewer_users': reviewer_users,
                    'viewer_users': viewer_users
                }
            finally:
                session.close()
    
    def search_users(self, query: str, limit: int = 50) -> List[User]:
        """Search users by username or email"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                return session.query(User).filter(
                    (User.username.ilike(f'%{query}%')) | 
                    (User.email.ilike(f'%{query}%'))
                ).limit(limit).all()
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                return session.query(User).filter(
                    (User.username.ilike(f'%{query}%')) | 
                    (User.email.ilike(f'%{query}%'))
                ).limit(limit).all()
            finally:
                session.close()
    
    def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get users by role"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                return session.query(User).filter_by(role=role, is_active=True).all()
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                return session.query(User).filter_by(role=role, is_active=True).all()
            finally:
                session.close()
    
    def reset_user_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """Reset user password"""
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                user.password_hash = generate_password_hash(new_password)
                user.updated_at = datetime.now(timezone.utc)
                
                return {'success': True, 'message': 'Password reset successfully'}
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                user.password_hash = generate_password_hash(new_password)
                user.updated_at = datetime.now(timezone.utc)
                session.commit()
                
                return {'success': True, 'message': 'Password reset successfully'}
            except Exception as e:
                session.rollback()
                return {'success': False, 'error': str(e)}
            finally:
                session.close()
