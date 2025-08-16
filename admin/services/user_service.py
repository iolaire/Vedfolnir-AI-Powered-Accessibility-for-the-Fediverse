# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin User Management Service"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from email_validator import validate_email, EmailNotValidError

from models import User, UserRole, UserAuditLog
from services.user_management_service import UserRegistrationService, PasswordManagementService
from services.email_service import email_service

logger = logging.getLogger(__name__)

class UserService:
    """Service for admin user management operations"""
    
    def __init__(self, db_manager, session_manager=None, base_url: str = "http://localhost:5000"):
        self.db_manager = db_manager
        self.session_manager = session_manager
        self.base_url = base_url
    
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
    
    def delete_user(self, user_id: int, admin_user_id: Optional[int] = None,
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Delete a user with enhanced validation and audit logging"""
        session = self.db_manager.get_session()
        try:
            user = session.query(User).get(user_id)
            if not user:
                return False, "User not found"
            
            # Prevent deletion of the last admin user
            if user.role == UserRole.ADMIN:
                admin_count = session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
                if admin_count <= 1:
                    return False, "Cannot delete the last admin user"
            
            username = user.username
            email = user.email
            
            # Log user deletion before deleting
            UserAuditLog.log_action(
                session,
                action="user_deleted",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"User {username} ({email}) deleted by admin",
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            session.delete(user)
            session.commit()
            
            logger.info(f"User {username} deleted by admin {admin_user_id}")
            return True, f"User {username} deleted successfully"
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            return False, "Failed to delete user due to database error"
        finally:
            session.close()
    
    def create_admin_user(self, username: str, email: str, password: str, 
                         first_name: Optional[str] = None, last_name: Optional[str] = None,
                         admin_user_id: Optional[int] = None, bypass_email_verification: bool = True,
                         ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[dict]]:
        """Create a new user via admin interface with email verification bypass option"""
        session = self.db_manager.get_session()
        try:
            # Use registration service for validation
            registration_service = UserRegistrationService(session, self.base_url)
            
            # Validate inputs
            username_valid, username_msg = registration_service.validate_username(username)
            if not username_valid:
                return False, username_msg, None
            
            email_valid, email_result = registration_service.validate_email_address(email)
            if not email_valid:
                return False, f"Invalid email address: {email_result}", None
            
            password_valid, password_msg = registration_service.validate_password(password)
            if not password_valid:
                return False, password_msg, None
            
            normalized_email = email_result
            
            # Check for existing users
            existing = session.query(User).filter(
                (User.username == username) | (User.email == normalized_email)
            ).first()
            
            if existing:
                if existing.username == username:
                    return False, f'Username {username} already exists', None
                else:
                    return False, f'Email {normalized_email} is already registered', None
            
            # Create new user
            user = User(
                username=username,
                email=normalized_email,
                role=UserRole.VIEWER,  # Default role, can be changed later
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                email_verified=bypass_email_verification,  # Admin can bypass verification
                data_processing_consent=True,
                data_processing_consent_date=datetime.utcnow()
            )
            
            user.set_password(password)
            
            # Generate verification token if email verification is required
            if not bypass_email_verification:
                user.generate_email_verification_token()
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Log user creation
            UserAuditLog.log_action(
                session,
                action="user_created_by_admin",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"User {username} created by admin with email {normalized_email}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.commit()
            
            # Extract user data before session closes
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role.value,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
            
            logger.info(f"User {username} created by admin {admin_user_id}")
            return True, "User created successfully", user_data
            
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Database integrity error during admin user creation: {e}")
            return False, "User creation failed due to database constraint", None
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user via admin: {e}")
            return False, "User creation failed due to system error", None
        finally:
            session.close()
    
    async def send_user_creation_email(self, user_data: dict, temporary_password: str) -> Tuple[bool, str]:
        """Send email notification to newly created user"""
        try:
            if not email_service.is_configured():
                logger.warning("Email service not configured - user creation email not sent")
                return False, "Email service not configured"
            
            success = await email_service.send_account_created_email(
                user_email=user_data['email'],
                username=user_data['username'],
                temporary_password=temporary_password,
                base_url=self.base_url
            )
            
            if success:
                logger.info(f"User creation email sent to {user_data['email']}")
                return True, "User creation email sent successfully"
            else:
                logger.error(f"Failed to send user creation email to {user_data['email']}")
                return False, "Failed to send user creation email"
                
        except Exception as e:
            logger.error(f"Error sending user creation email: {e}")
            return False, f"Error sending email: {str(e)}"
    
    def admin_reset_user_password(self, user_id: int, new_password: Optional[str] = None,
                                 admin_user_id: Optional[int] = None,
                                 ip_address: Optional[str] = None, 
                                 user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Reset user password as admin with optional temporary password generation"""
        session = self.db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Generate secure temporary password if none provided
            if not new_password:
                new_password = self._generate_temporary_password()
            
            # Validate password if provided
            if new_password:
                registration_service = UserRegistrationService(session, self.base_url)
                password_valid, password_msg = registration_service.validate_password(new_password)
                if not password_valid:
                    return False, password_msg, None
            
            # Set new password
            user.set_password(new_password)
            
            # Clear any existing password reset tokens
            user.password_reset_token = None
            user.password_reset_sent_at = None
            user.password_reset_used = False
            
            # Unlock account if locked
            if user.account_locked:
                user.unlock_account()
            
            session.commit()
            
            # Log password reset
            UserAuditLog.log_action(
                session,
                action="password_reset_by_admin",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"Password reset by admin for user {user.username}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.commit()
            
            # Invalidate all user sessions if session manager is available
            if self.session_manager:
                try:
                    self.session_manager.invalidate_user_sessions(user_id)
                    logger.info(f"All sessions invalidated for user {user.username} after admin password reset")
                except Exception as e:
                    logger.warning(f"Failed to invalidate sessions for user {user.username}: {e}")
            
            logger.info(f"Password reset by admin {admin_user_id} for user {user.username}")
            return True, "Password reset successfully", new_password
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error resetting password for user {user_id}: {e}")
            return False, "Failed to reset password due to system error", None
        finally:
            session.close()
    
    def update_user_status(self, user_id: int, is_active: Optional[bool] = None,
                          account_locked: Optional[bool] = None,
                          admin_user_id: Optional[int] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Update user account status (active/inactive, locked/unlocked)"""
        session = self.db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found"
            
            changes = []
            
            # Update active status
            if is_active is not None and user.is_active != is_active:
                user.is_active = is_active
                changes.append(f"active: {is_active}")
            
            # Update locked status
            if account_locked is not None and user.account_locked != account_locked:
                if account_locked:
                    user.account_locked = True
                    changes.append("account: locked")
                else:
                    user.unlock_account()
                    changes.append("account: unlocked")
            
            if not changes:
                return False, "No changes to apply"
            
            session.commit()
            
            # Log status change
            UserAuditLog.log_action(
                session,
                action="user_status_updated",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"User {user.username} status updated: {', '.join(changes)}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.commit()
            
            logger.info(f"User {user.username} status updated by admin {admin_user_id}: {', '.join(changes)}")
            return True, f"User status updated: {', '.join(changes)}"
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating user status: {e}")
            return False, "Failed to update user status due to system error"
        finally:
            session.close()
    
    def update_user_role(self, user_id: int, new_role: UserRole,
                        admin_user_id: Optional[int] = None,
                        ip_address: Optional[str] = None,
                        user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Update user role with validation"""
        session = self.db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found"
            
            old_role = user.role
            
            # Prevent removing admin role from last admin
            if old_role == UserRole.ADMIN and new_role != UserRole.ADMIN:
                admin_count = session.query(User).filter_by(role=UserRole.ADMIN, is_active=True).count()
                if admin_count <= 1:
                    return False, "Cannot remove admin role from the last admin user"
            
            if old_role == new_role:
                return False, f"User already has role {new_role.value}"
            
            user.role = new_role
            session.commit()
            
            # Log role change
            UserAuditLog.log_action(
                session,
                action="user_role_updated",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"User {user.username} role changed from {old_role.value} to {new_role.value}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.commit()
            
            logger.info(f"User {user.username} role updated from {old_role.value} to {new_role.value} by admin {admin_user_id}")
            return True, f"User role updated from {old_role.value} to {new_role.value}"
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating user role: {e}")
            return False, "Failed to update user role due to system error"
        finally:
            session.close()
    
    def get_user_details(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed user information for admin interface"""
        session = self.db_manager.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return None
            
            # Get platform connections count
            platform_count = len([pc for pc in user.platform_connections if pc.is_active])
            
            # Get recent audit logs
            recent_logs = session.query(UserAuditLog).filter_by(user_id=user_id)\
                                .order_by(UserAuditLog.created_at.desc()).limit(10).all()
            
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'role': user.role.value,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'account_locked': user.account_locked,
                'failed_login_attempts': user.failed_login_attempts,
                'last_failed_login': user.last_failed_login.isoformat() if user.last_failed_login else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'data_processing_consent': user.data_processing_consent,
                'platform_connections_count': platform_count,
                'recent_activity': [
                    {
                        'action': log.action,
                        'details': log.details,
                        'created_at': log.created_at.isoformat() if log.created_at else None,
                        'ip_address': log.ip_address
                    }
                    for log in recent_logs
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting user details: {e}")
            return None
        finally:
            session.close()
    
    def get_users_with_filters(self, role: Optional[UserRole] = None, 
                              is_active: Optional[bool] = None,
                              email_verified: Optional[bool] = None,
                              account_locked: Optional[bool] = None,
                              search_term: Optional[str] = None,
                              limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get users with filtering and pagination for admin interface"""
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
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    (User.username.ilike(search_pattern)) |
                    (User.email.ilike(search_pattern)) |
                    (User.first_name.ilike(search_pattern)) |
                    (User.last_name.ilike(search_pattern))
                )
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination and ordering
            users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
            
            # Format user data
            user_list = []
            for user in users:
                platform_count = len([pc for pc in user.platform_connections if pc.is_active])
                
                user_list.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.get_full_name(),
                    'role': user.role.value,
                    'is_active': user.is_active,
                    'email_verified': user.email_verified,
                    'account_locked': user.account_locked,
                    'failed_login_attempts': user.failed_login_attempts,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'platform_connections_count': platform_count
                })
            
            return {
                'users': user_list,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total_count
            }
            
        except Exception as e:
            logger.error(f"Error getting users with filters: {e}")
            return {'users': [], 'total_count': 0, 'limit': limit, 'offset': offset, 'has_more': False}
        finally:
            session.close()
    
    def preserve_admin_session(self, admin_user_id: int) -> bool:
        """Preserve admin session during user management operations"""
        if not self.session_manager:
            logger.warning("Session manager not available for session preservation")
            return False
        
        try:
            # Extend admin session timeout
            success = self.session_manager.extend_session_timeout(admin_user_id)
            if success:
                logger.debug(f"Admin session preserved for user {admin_user_id}")
            return success
        except Exception as e:
            logger.error(f"Error preserving admin session: {e}")
            return False
    
    def _generate_temporary_password(self) -> str:
        """Generate a secure temporary password"""
        # Generate a password with letters, numbers, and symbols
        import string
        import random
        
        length = 12
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        
        # Ensure at least one of each type
        password = [
            random.choice(string.ascii_lowercase),
            random.choice(string.ascii_uppercase),
            random.choice(string.digits),
            random.choice("!@#$%^&*")
        ]
        
        # Fill the rest randomly
        for _ in range(length - 4):
            password.append(random.choice(characters))
        
        # Shuffle the password
        random.shuffle(password)
        
        return ''.join(password)