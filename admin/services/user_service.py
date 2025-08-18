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
    
    def __init__(self, db_manager, session_manager=None):
        self.db_manager = db_manager
        self.session_manager = session_manager  # Optional session manager parameter
        # Add unified session manager reference
        self._unified_session_manager = None
    

    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).all()
        finally:
            self.db_manager.close_session(session)
    
    def get_admin_count(self) -> int:
        """Get count of active admin users"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
        finally:
            self.db_manager.close_session(session)
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole = UserRole.VIEWER, is_active: bool = True) -> Dict[str, Any]:
        """Create a new user and return user data dict"""
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
            self.db_manager.close_session(session)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        finally:
            self.db_manager.close_session(session)
    
    def update_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Update user and return result"""
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
            self.db_manager.close_session(session)
    
    def delete_user(self, user_id: int, current_user_id: int) -> Dict[str, Any]:
        """Delete user (soft delete by deactivating)"""
        if user_id == current_user_id:
            return {'success': False, 'error': 'Cannot delete your own account'}
        
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
            self.db_manager.close_session(session)
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
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
            self.db_manager.close_session(session)
    
    def search_users(self, query: str, limit: int = 50) -> List[User]:
        """Search users by username or email"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).filter(
                (User.username.ilike(f'%{query}%')) | 
                (User.email.ilike(f'%{query}%'))
            ).limit(limit).all()
        finally:
            self.db_manager.close_session(session)
    
    def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get users by role"""
        session = self.db_manager.get_session()
        try:
            return session.query(User).filter_by(role=role, is_active=True).all()
        finally:
            self.db_manager.close_session(session)
    
    def reset_user_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """Reset user password"""
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
            self.db_manager.close_session(session)
    
    def get_users_with_filters(self, role=None, is_active=None, email_verified=None, 
                              account_locked=None, search_term=None, limit=25, offset=0):
        """Get users with filtering and pagination"""
        session = self.db_manager.get_session()
        try:
            query = session.query(User)
            
            # Apply filters
            if role is not None:
                query = query.filter(User.role == role)
            if is_active is not None:
                query = query.filter(User.is_active == is_active)
            if email_verified is not None:
                query = query.filter(User.email_verified == email_verified)
            if account_locked is not None:
                query = query.filter(User.account_locked == account_locked)
            if search_term:
                query = query.filter(
                    (User.username.ilike(f'%{search_term}%')) | 
                    (User.email.ilike(f'%{search_term}%'))
                )
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            users = query.offset(offset).limit(limit).all()
            
            return {
                'users': users,
                'total_count': total_count
            }
        finally:
            self.db_manager.close_session(session)
    
    def get_user_details(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed user information"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'is_active': user.is_active,
            'email_verified': getattr(user, 'email_verified', False),
            'account_locked': getattr(user, 'account_locked', False),
            'failed_login_attempts': getattr(user, 'failed_login_attempts', 0),
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if getattr(user, 'updated_at', None) else None,
            'last_login': user.last_login.isoformat() if getattr(user, 'last_login', None) else None
        }
    
    def create_admin_user(self, username: str, email: str, password: str, 
                         first_name=None, last_name=None, admin_user_id=None,
                         bypass_email_verification=False, ip_address=None, user_agent=None):
        """Create a new user with admin privileges"""
        result = self.create_user(username, email, password, UserRole.VIEWER, True)
        
        if result['success']:
            return True, 'User created successfully', result['user']
        else:
            return False, result['error'], None
    
    def update_user_role(self, user_id: int, new_role: UserRole, admin_user_id: int,
                        ip_address=None, user_agent=None):
        """Update user role with admin tracking"""
        result = self.update_user(user_id, role=new_role)
        
        if result['success']:
            return True, f'User role updated to {new_role.value}'
        else:
            return False, result['error']
    
    def update_user_status(self, user_id: int, is_active: bool, account_locked: bool,
                          admin_user_id: int, ip_address=None, user_agent=None):
        """Update user status with admin tracking"""
        result = self.update_user(user_id, is_active=is_active)
        
        if result['success']:
            status_msg = 'activated' if is_active else 'deactivated'
            return True, f'User {status_msg} successfully'
        else:
            return False, result['error']
    
    def admin_reset_user_password(self, user_id: int, admin_user_id: int,
                                 ip_address=None, user_agent=None):
        """Reset user password as admin"""
        import secrets
        import string
        
        # Generate temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        result = self.reset_user_password(user_id, temp_password)
        
        if result['success']:
            return True, 'Password reset successfully', temp_password
        else:
            return False, result['error'], None
    
    def preserve_admin_session(self, admin_user_id: int):
        """Preserve admin session during operations"""
        # This is a placeholder for session preservation logic
        # In a real implementation, this would ensure the admin's session remains valid
        pass
    
    def send_user_creation_email(self, user_data: Dict[str, Any], password: str):
        """Send user creation notification email"""
        # This is a placeholder for email sending logic
        # In a real implementation, this would send an email to the new user
        pass
