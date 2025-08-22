# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Management Services

This module provides comprehensive user management services including registration,
authentication, profile management, and password reset functionality.
"""

import logging
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from models import User, UserRole, UserAuditLog
from services.email_service import email_service

logger = logging.getLogger(__name__)

class UserRegistrationService:
    """Service for handling user registration and email verification"""
    
    def __init__(self, db_session: Session, base_url: str = "http://localhost:5000"):
        """Initialize registration service"""
        self.db_session = db_session
        self.base_url = base_url
    
    def validate_email_address(self, email: str) -> Tuple[bool, str]:
        """Validate email address using email_validator"""
        try:
            # Validate and get normalized result
            valid = validate_email(email)
            return True, valid.email
        except EmailNotValidError as e:
            logger.warning(f"Invalid email address {email}: {e}")
            return False, str(e)
    
    def validate_username(self, username: str) -> Tuple[bool, str]:
        """Validate username format and availability"""
        # Check format
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 64:
            return False, "Username must be no more than 64 characters long"
        
        if not username.replace('_', '').replace('-', '').isalnum():
            return False, "Username can only contain letters, numbers, hyphens, and underscores"
        
        # Check availability
        existing_user = self.db_session.query(User).filter_by(username=username).first()
        if existing_user:
            return False, "Username is already taken"
        
        return True, "Username is valid"
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be no more than 128 characters long"
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            return False, "Password must contain at least one letter and one number"
        
        return True, "Password is valid"
    
    def register_user(self, username: str, email: str, password: str, 
                     role: UserRole = UserRole.VIEWER, 
                     first_name: Optional[str] = None,
                     last_name: Optional[str] = None,
                     require_email_verification: bool = True,
                     ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """Register a new user with email verification requirement"""
        
        # Validate username
        username_valid, username_msg = self.validate_username(username)
        if not username_valid:
            return False, username_msg, None
        
        # Validate email
        email_valid, email_result = self.validate_email_address(email)
        if not email_valid:
            return False, f"Invalid email address: {email_result}", None
        
        normalized_email = email_result
        
        # Check if email is already registered
        existing_user = self.db_session.query(User).filter_by(email=normalized_email).first()
        if existing_user:
            return False, "Email address is already registered", None
        
        # Validate password
        password_valid, password_msg = self.validate_password(password)
        if not password_valid:
            return False, password_msg, None
        
        try:
            # Create new user
            user = User(
                username=username,
                email=normalized_email,
                role=role,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                email_verified=not require_email_verification,  # Skip verification if not required
                data_processing_consent=True,  # Required for registration
                data_processing_consent_date=datetime.utcnow()
            )
            
            # Set password
            user.set_password(password)
            
            # Generate email verification token if required
            if require_email_verification:
                user.generate_email_verification_token()
            
            # Add to database
            self.db_session.add(user)
            self.db_session.commit()
            
            # Log registration
            UserAuditLog.log_action(
                self.db_session,
                action="user_registered",
                user_id=user.id,
                details=f"User registered with email {normalized_email}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"User {username} registered successfully with email {normalized_email}")
            return True, "User registered successfully", user
            
        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Database integrity error during registration: {e}")
            return False, "Registration failed due to database constraint", None
        
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Unexpected error during registration: {e}")
            return False, "Registration failed due to system error", None
    
    async def send_verification_email(self, user: User) -> Tuple[bool, str]:
        """Send email verification email to user"""
        if not user.email_verification_token:
            user.generate_email_verification_token()
            self.db_session.commit()
        
        try:
            success = await email_service.send_verification_email(
                user_email=user.email,
                username=user.username,
                verification_token=user.email_verification_token,
                base_url=self.base_url
            )
            
            if success:
                # Update sent timestamp
                user.email_verification_sent_at = datetime.utcnow()
                self.db_session.commit()
                
                # Log email sent
                UserAuditLog.log_action(
                    self.db_session,
                    action="verification_email_sent",
                    user_id=user.id,
                    details=f"Verification email sent to {user.email}"
                )
                self.db_session.commit()
                
                logger.info(f"Verification email sent to {user.email}")
                return True, "Verification email sent successfully"
            else:
                logger.error(f"Failed to send verification email to {user.email}")
                return False, "Failed to send verification email"
                
        except Exception as e:
            logger.error(f"Error sending verification email to {user.email}: {e}")
            return False, f"Error sending verification email: {str(e)}"
    
    def verify_email(self, token: str, ip_address: Optional[str] = None,
                    user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """Verify email address using verification token"""
        if not token:
            return False, "Verification token is required", None
        
        try:
            # Find user with this token
            user = self.db_session.query(User).filter_by(email_verification_token=token).first()
            
            if not user:
                logger.warning(f"Invalid verification token attempted: {token[:10]}...")
                return False, "Invalid or expired verification token", None
            
            # Verify token and mark email as verified
            if user.verify_email_token(token):
                self.db_session.commit()
                
                # Log verification
                UserAuditLog.log_action(
                    self.db_session,
                    action="email_verified",
                    user_id=user.id,
                    details=f"Email {user.email} verified successfully",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                
                logger.info(f"Email verified successfully for user {user.username}")
                return True, "Email verified successfully", user
            else:
                logger.warning(f"Expired verification token for user {user.username}")
                return False, "Verification token has expired", None
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error during email verification: {e}")
            return False, "Email verification failed due to system error", None
    
    async def resend_verification_email(self, user_id: int, 
                                      ip_address: Optional[str] = None,
                                      user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Resend verification email to user"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found"
            
            if user.email_verified:
                return False, "Email is already verified"
            
            # Check rate limiting - only allow resend every 5 minutes
            if user.email_verification_sent_at:
                time_since_last = datetime.utcnow() - user.email_verification_sent_at
                if time_since_last < timedelta(minutes=5):
                    remaining = 5 - int(time_since_last.total_seconds() / 60)
                    return False, f"Please wait {remaining} minutes before requesting another verification email"
            
            # Generate new token and send email
            user.generate_email_verification_token()
            self.db_session.commit()
            
            success, message = await self.send_verification_email(user)
            
            if success:
                # Log resend
                UserAuditLog.log_action(
                    self.db_session,
                    action="verification_email_resent",
                    user_id=user.id,
                    details=f"Verification email resent to {user.email}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error resending verification email: {e}")
            return False, "Failed to resend verification email"
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        try:
            return self.db_session.query(User).filter_by(email=email).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return self.db_session.query(User).filter_by(username=username).first()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            return self.db_session.query(User).filter_by(id=user_id).first()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

class UserAuthenticationService:
    """Service for handling user authentication with enhanced security"""
    
    def __init__(self, db_session: Session, session_manager=None):
        """Initialize authentication service"""
        self.db_session = db_session
        self.session_manager = session_manager
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)  # Account lockout duration
    
    def authenticate_user(self, username_or_email: str, password: str,
                         ip_address: Optional[str] = None,
                         user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """Authenticate user with username/email and password with enhanced security"""
        if not username_or_email or not password:
            return False, "Username/email and password are required", None
        
        try:
            # Find user by username or email
            user = self.db_session.query(User).filter(
                (User.username == username_or_email) | (User.email == username_or_email)
            ).first()
            
            if not user:
                logger.warning(f"Authentication attempt with non-existent user: {username_or_email}")
                # Log failed attempt for non-existent user (for security monitoring)
                UserAuditLog.log_action(
                    self.db_session,
                    action="login_attempt_invalid_user",
                    details=f"Login attempt with non-existent user: {username_or_email}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                return False, "Invalid username/email or password", None
            
            # Check if account is temporarily locked due to failed attempts
            if self._is_account_temporarily_locked(user):
                remaining_time = self._get_lockout_remaining_time(user)
                logger.warning(f"Login attempt on temporarily locked account: {user.username}")
                UserAuditLog.log_action(
                    self.db_session,
                    action="login_attempt_locked_account",
                    user_id=user.id,
                    details=f"Login attempt on locked account from {ip_address or 'unknown IP'}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                return False, f"Account temporarily locked. Try again in {remaining_time} minutes.", None
            
            # Check if user can login (email verified, account active, etc.)
            if not user.can_login():
                if not user.is_active:
                    reason = "Account is deactivated"
                elif not user.email_verified:
                    reason = "Email address not verified. Please check your email for a verification link."
                elif user.account_locked:
                    reason = "Account is permanently locked. Please contact support."
                else:
                    reason = "Account access denied"
                
                logger.warning(f"Login denied for user {user.username}: {reason}")
                UserAuditLog.log_action(
                    self.db_session,
                    action="login_denied",
                    user_id=user.id,
                    details=f"Login denied: {reason}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                return False, reason, None
            
            # Check password
            if user.check_password(password):
                # Successful login - reset failed attempts and update last login
                user.failed_login_attempts = 0
                user.last_failed_login = None
                user.last_login = datetime.utcnow()
                self.db_session.commit()
                
                # Log successful login
                UserAuditLog.log_action(
                    self.db_session,
                    action="user_login_success",
                    user_id=user.id,
                    details=f"Successful login from {ip_address or 'unknown IP'}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                
                logger.info(f"Successful login for user {user.username}")
                return True, "Login successful", user
            else:
                # Failed login - record attempt and check for lockout
                user.record_failed_login()
                
                # Check if account should be locked after this attempt
                if user.failed_login_attempts >= self.max_failed_attempts:
                    user.account_locked = True
                    lockout_reason = "Account locked due to too many failed login attempts"
                    
                    # Log account lockout
                    UserAuditLog.log_action(
                        self.db_session,
                        action="account_locked",
                        user_id=user.id,
                        details=f"Account locked after {self.max_failed_attempts} failed attempts from {ip_address or 'unknown IP'}",
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    self.db_session.commit()
                    
                    logger.warning(f"Account locked for user {user.username} after {self.max_failed_attempts} failed attempts")
                    return False, lockout_reason, None
                else:
                    self.db_session.commit()
                    
                    # Log failed login
                    UserAuditLog.log_action(
                        self.db_session,
                        action="user_login_failed",
                        user_id=user.id,
                        details=f"Failed login attempt from {ip_address or 'unknown IP'} (attempt {user.failed_login_attempts}/{self.max_failed_attempts})",
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    self.db_session.commit()
                    
                    logger.warning(f"Failed login attempt for user {user.username} (attempt {user.failed_login_attempts}/{self.max_failed_attempts})")
                    
                    remaining_attempts = self.max_failed_attempts - user.failed_login_attempts
                    return False, f"Invalid password. {remaining_attempts} attempts remaining before account lockout.", None
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error during authentication: {e}")
            return False, "Authentication failed due to system error", None
    
    def _is_account_temporarily_locked(self, user: User) -> bool:
        """Check if account is temporarily locked due to recent failed attempts"""
        if not user.last_failed_login:
            return False
        
        # Check if enough time has passed since last failed attempt
        time_since_last_failure = datetime.utcnow() - user.last_failed_login
        
        # If user has max failed attempts and it's within lockout duration, account is locked
        if user.failed_login_attempts >= self.max_failed_attempts and time_since_last_failure < self.lockout_duration:
            return True
        
        # If lockout duration has passed, reset failed attempts
        if user.failed_login_attempts >= self.max_failed_attempts and time_since_last_failure >= self.lockout_duration:
            user.failed_login_attempts = 0
            user.last_failed_login = None
            self.db_session.commit()
            logger.info(f"Temporary lockout expired for user {user.username}, resetting failed attempts")
        
        return False
    
    def _get_lockout_remaining_time(self, user: User) -> int:
        """Get remaining lockout time in minutes"""
        if not user.last_failed_login:
            return 0
        
        time_since_last_failure = datetime.utcnow() - user.last_failed_login
        remaining_time = self.lockout_duration - time_since_last_failure
        
        return max(0, int(remaining_time.total_seconds() / 60))
    
    def login_user_with_session(self, user: User, remember: bool = False,
                               ip_address: Optional[str] = None,
                               user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Login user and create secure session with SessionManager integration"""
        try:
            if not self.session_manager:
                logger.error("Session manager not available for secure session creation")
                return False, "Session management not available", None
            
            # Get user's default platform for session context
            platform_connection_id = None
            if user.role != UserRole.ADMIN:  # Non-admin users need platform context
                default_platform = next(
                    (pc for pc in user.platform_connections if pc.is_default and pc.is_active),
                    None
                )
                if default_platform:
                    platform_connection_id = default_platform.id
            
            # Create database session
            session_id = self.session_manager.create_session(
                user_id=user.id,
                platform_connection_id=platform_connection_id
            )
            
            if session_id:
                # Log session creation
                UserAuditLog.log_action(
                    self.db_session,
                    action="session_created",
                    user_id=user.id,
                    details=f"Database session created from {ip_address or 'unknown IP'}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                
                logger.info(f"Secure session created for user {user.username}")
                return True, "Session created successfully", session_id
            else:
                logger.error(f"Failed to create database session for user {user.username}")
                return False, "Failed to create secure session", None
                
        except Exception as e:
            logger.error(f"Error creating secure session for user {user.username}: {e}")
            return False, "Session creation failed due to system error", None
    
    def unlock_user_account(self, user_id: int, admin_user_id: Optional[int] = None,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Unlock a user account (admin function)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found"
            
            if not user.account_locked and user.failed_login_attempts == 0:
                return False, "Account is not locked"
            
            # Unlock account
            user.unlock_account()
            self.db_session.commit()
            
            # Log account unlock
            UserAuditLog.log_action(
                self.db_session,
                action="account_unlocked",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"Account unlocked by admin from {ip_address or 'unknown IP'}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"Account unlocked for user {user.username} by admin {admin_user_id}")
            return True, "Account unlocked successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error unlocking account: {e}")
            return False, "Failed to unlock account due to system error"
    
    def get_user_login_status(self, user_id: int) -> Dict[str, Any]:
        """Get user's login status and security information"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return {"error": "User not found"}
            
            status = {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "account_locked": user.account_locked,
                "failed_login_attempts": user.failed_login_attempts,
                "last_failed_login": user.last_failed_login.isoformat() if user.last_failed_login else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "can_login": user.can_login(),
                "temporarily_locked": self._is_account_temporarily_locked(user)
            }
            
            if status["temporarily_locked"]:
                status["lockout_remaining_minutes"] = self._get_lockout_remaining_time(user)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting user login status: {e}")
            return {"error": "Failed to get login status"}
    
    def validate_session_security(self, session_id: str, user_id: int) -> bool:
        """Validate session security with authentication service integration"""
        try:
            if not self.session_manager:
                logger.warning("Session manager not available for security validation")
                return False
            
            # Use session manager's validation
            return self.session_manager.validate_session(session_id, user_id)
            
        except Exception as e:
            logger.error(f"Error validating session security: {e}")
            return False

class PasswordManagementService:
    """Service for handling password reset and management"""
    
    def __init__(self, db_session: Session, base_url: str = "http://localhost:5000"):
        """Initialize password management service"""
        self.db_session = db_session
        self.base_url = base_url
        self.reset_token_lifetime = timedelta(hours=1)  # Password reset tokens expire in 1 hour
    
    async def initiate_password_reset(self, email: str,
                                    ip_address: Optional[str] = None,
                                    user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Initiate password reset process by sending reset email"""
        try:
            # Find user by email
            user = self.db_session.query(User).filter_by(email=email).first()
            
            if not user:
                # Don't reveal whether email exists for security
                logger.warning(f"Password reset requested for non-existent email: {email}")
                UserAuditLog.log_action(
                    self.db_session,
                    action="password_reset_invalid_email",
                    details=f"Password reset requested for non-existent email: {email}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                return True, "If the email address exists, a password reset link has been sent."
            
            # Check if user account is active
            if not user.is_active:
                logger.warning(f"Password reset requested for inactive account: {user.username}")
                UserAuditLog.log_action(
                    self.db_session,
                    action="password_reset_inactive_account",
                    user_id=user.id,
                    details=f"Password reset requested for inactive account",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                return True, "If the email address exists, a password reset link has been sent."
            
            # Check rate limiting - only allow one reset request per 5 minutes
            if user.password_reset_sent_at:
                time_since_last = datetime.utcnow() - user.password_reset_sent_at
                if time_since_last < timedelta(minutes=5):
                    remaining = 5 - int(time_since_last.total_seconds() / 60)
                    logger.warning(f"Rate limited password reset request for user {user.username}")
                    return False, f"Please wait {remaining} minutes before requesting another password reset."
            
            # Generate reset token
            reset_token = user.generate_password_reset_token()
            self.db_session.commit()
            
            # Send reset email
            success = await email_service.send_password_reset_email(
                user_email=user.email,
                username=user.username,
                reset_token=reset_token,
                base_url=self.base_url
            )
            
            if success:
                # Update sent timestamp
                user.password_reset_sent_at = datetime.utcnow()
                self.db_session.commit()
                
                # Log password reset request
                UserAuditLog.log_action(
                    self.db_session,
                    action="password_reset_requested",
                    user_id=user.id,
                    details=f"Password reset email sent to {user.email}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                
                logger.info(f"Password reset email sent to {user.email}")
                return True, "If the email address exists, a password reset link has been sent."
            else:
                logger.error(f"Failed to send password reset email to {user.email}")
                return False, "Failed to send password reset email. Please try again later."
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error initiating password reset: {e}")
            return False, "Password reset failed due to system error"
    
    def verify_reset_token(self, token: str) -> Tuple[bool, str, Optional[User]]:
        """Verify password reset token"""
        if not token:
            return False, "Reset token is required", None
        
        try:
            # Find user with this token
            user = self.db_session.query(User).filter_by(password_reset_token=token).first()
            
            if not user:
                logger.warning(f"Invalid password reset token attempted: {token[:10]}...")
                return False, "Invalid or expired reset token", None
            
            # Verify token
            if user.verify_password_reset_token(token):
                logger.info(f"Valid password reset token for user {user.username}")
                return True, "Reset token is valid", user
            else:
                logger.warning(f"Expired password reset token for user {user.username}")
                return False, "Reset token has expired", None
                
        except Exception as e:
            logger.error(f"Error verifying reset token: {e}")
            return False, "Token verification failed due to system error", None
    
    def reset_password(self, token: str, new_password: str,
                      ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """Reset user password using reset token"""
        try:
            # Verify token first
            token_valid, token_message, user = self.verify_reset_token(token)
            
            if not token_valid or not user:
                return False, token_message, None
            
            # Validate new password
            from services.user_management_service import UserRegistrationService
            registration_service = UserRegistrationService(self.db_session)
            password_valid, password_message = registration_service.validate_password(new_password)
            
            if not password_valid:
                return False, password_message, None
            
            # Reset password
            if user.reset_password(new_password, token):
                self.db_session.commit()
                
                # Log password reset
                UserAuditLog.log_action(
                    self.db_session,
                    action="password_reset_completed",
                    user_id=user.id,
                    details=f"Password reset completed from {ip_address or 'unknown IP'}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                
                logger.info(f"Password reset completed for user {user.username}")
                return True, "Password reset successfully", user
            else:
                logger.error(f"Failed to reset password for user {user.username}")
                return False, "Failed to reset password", None
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error resetting password: {e}")
            return False, "Password reset failed due to system error", None
    
    def change_password(self, user_id: int, current_password: str, new_password: str,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None) -> Tuple[bool, str]:
        """Change user password (requires current password)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found"
            
            # Verify current password
            if not user.check_password(current_password):
                # Log failed password change attempt
                UserAuditLog.log_action(
                    self.db_session,
                    action="password_change_failed",
                    user_id=user.id,
                    details=f"Failed password change attempt - incorrect current password from {ip_address or 'unknown IP'}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                
                logger.warning(f"Failed password change attempt for user {user.username} - incorrect current password")
                return False, "Current password is incorrect"
            
            # Validate new password
            from services.user_management_service import UserRegistrationService
            registration_service = UserRegistrationService(self.db_session)
            password_valid, password_message = registration_service.validate_password(new_password)
            
            if not password_valid:
                return False, password_message
            
            # Check if new password is different from current
            if user.check_password(new_password):
                return False, "New password must be different from current password"
            
            # Change password
            user.set_password(new_password)
            
            # Reset any failed login attempts
            user.failed_login_attempts = 0
            user.last_failed_login = None
            user.account_locked = False
            
            self.db_session.commit()
            
            # Log password change
            UserAuditLog.log_action(
                self.db_session,
                action="password_changed",
                user_id=user.id,
                details=f"Password changed successfully from {ip_address or 'unknown IP'}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"Password changed successfully for user {user.username}")
            return True, "Password changed successfully"
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error changing password: {e}")
            return False, "Password change failed due to system error"
    
    def get_user_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by password reset token"""
        try:
            return self.db_session.query(User).filter_by(password_reset_token=token).first()
        except Exception as e:
            logger.error(f"Error getting user by reset token: {e}")
            return None
    
    def cleanup_expired_reset_tokens(self) -> int:
        """Clean up expired password reset tokens"""
        try:
            expired_cutoff = datetime.utcnow() - self.reset_token_lifetime
            
            # Find users with expired tokens
            expired_users = self.db_session.query(User).filter(
                User.password_reset_token.isnot(None),
                User.password_reset_sent_at < expired_cutoff
            ).all()
            
            count = 0
            for user in expired_users:
                user.password_reset_token = None
                user.password_reset_sent_at = None
                user.password_reset_used = False
                count += 1
            
            if count > 0:
                self.db_session.commit()
                logger.info(f"Cleaned up {count} expired password reset tokens")
            
            return count
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error cleaning up expired reset tokens: {e}")
            return 0

class UserProfileService:
    """Service for handling user profile management with GDPR compliance"""
    
    def __init__(self, db_session: Session, base_url: str = "http://localhost:5000"):
        """Initialize profile management service"""
        self.db_session = db_session
        self.base_url = base_url
    
    def update_profile(self, user_id: int, profile_data: Dict[str, Any],
                      ip_address: Optional[str] = None,
                      user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Update user profile information with validation and audit logging"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Store original values for audit logging
            original_values = {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            
            changes_made = []
            email_changed = False
            
            # Update first name
            if 'first_name' in profile_data:
                new_first_name = profile_data['first_name']
                if new_first_name != user.first_name:
                    # Validate first name
                    if new_first_name and len(new_first_name.strip()) > 100:
                        return False, "First name must be no more than 100 characters", None
                    
                    user.first_name = new_first_name.strip() if new_first_name else None
                    changes_made.append(f"first_name: '{original_values['first_name']}' -> '{user.first_name}'")
            
            # Update last name
            if 'last_name' in profile_data:
                new_last_name = profile_data['last_name']
                if new_last_name != user.last_name:
                    # Validate last name
                    if new_last_name and len(new_last_name.strip()) > 100:
                        return False, "Last name must be no more than 100 characters", None
                    
                    user.last_name = new_last_name.strip() if new_last_name else None
                    changes_made.append(f"last_name: '{original_values['last_name']}' -> '{user.last_name}'")
            
            # Update email (requires re-verification)
            if 'email' in profile_data:
                new_email = profile_data['email']
                if new_email != user.email:
                    # Validate email
                    from services.user_management_service import UserRegistrationService
                    registration_service = UserRegistrationService(self.db_session)
                    email_valid, email_result = registration_service.validate_email_address(new_email)
                    
                    if not email_valid:
                        return False, f"Invalid email address: {email_result}", None
                    
                    normalized_email = email_result
                    
                    # Check if email is already in use by another user
                    existing_user = self.db_session.query(User).filter(
                        User.email == normalized_email,
                        User.id != user_id
                    ).first()
                    
                    if existing_user:
                        return False, "Email address is already in use by another user", None
                    
                    # Update email and mark as unverified
                    user.email = normalized_email
                    user.email_verified = False
                    user.email_verification_token = None
                    user.email_verification_sent_at = None
                    
                    changes_made.append(f"email: '{original_values['email']}' -> '{user.email}' (requires re-verification)")
                    email_changed = True
            
            # If no changes were made, return success without database update
            if not changes_made:
                return True, "No changes were made to the profile", {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.get_full_name(),
                    'email_verified': user.email_verified,
                    'email_changed': False
                }
            
            # Save changes
            self.db_session.commit()
            
            # Log profile update
            UserAuditLog.log_action(
                self.db_session,
                action="profile_updated",
                user_id=user.id,
                details=f"Profile updated: {'; '.join(changes_made)}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"Profile updated for user {user.username}: {'; '.join(changes_made)}")
            
            return True, "Profile updated successfully", {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'email_verified': user.email_verified,
                'email_changed': email_changed
            }
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return False, "Profile update failed due to system error", None
    
    async def change_email(self, user_id: int, new_email: str,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None) -> Tuple[bool, str, bool]:
        """Change user email address with re-verification requirement"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", False
            
            # Validate email
            from services.user_management_service import UserRegistrationService
            registration_service = UserRegistrationService(self.db_session, self.base_url)
            email_valid, email_result = registration_service.validate_email_address(new_email)
            
            if not email_valid:
                return False, f"Invalid email address: {email_result}", False
            
            normalized_email = email_result
            
            # Check if email is the same as current
            if normalized_email == user.email:
                return False, "New email address is the same as current email address", False
            
            # Check if email is already in use
            existing_user = self.db_session.query(User).filter(
                User.email == normalized_email,
                User.id != user_id
            ).first()
            
            if existing_user:
                return False, "Email address is already in use by another user", False
            
            # Store old email for audit
            old_email = user.email
            
            # Update email and mark as unverified
            user.email = normalized_email
            user.email_verified = False
            user.generate_email_verification_token()
            
            self.db_session.commit()
            
            # Send verification email to new address
            success, message = await registration_service.send_verification_email(user)
            
            if success:
                # Log email change
                UserAuditLog.log_action(
                    self.db_session,
                    action="email_changed",
                    user_id=user.id,
                    details=f"Email changed from {old_email} to {normalized_email} - verification email sent",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db_session.commit()
                
                logger.info(f"Email changed for user {user.username} from {old_email} to {normalized_email}")
                return True, "Email address updated. Please check your new email for a verification link.", True
            else:
                # Rollback email change if verification email failed
                user.email = old_email
                user.email_verified = True  # Restore original verification status
                user.email_verification_token = None
                user.email_verification_sent_at = None
                self.db_session.commit()
                
                logger.error(f"Failed to send verification email after email change for user {user.username}")
                return False, "Failed to send verification email. Email address not changed.", False
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error changing email for user {user_id}: {e}")
            return False, "Email change failed due to system error", False
    
    def get_profile_data(self, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Get user profile data for editing"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            profile_data = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'role': user.role.value if user.role else None,
                'is_active': user.is_active,
                'email_verified': user.email_verified,
                'data_processing_consent': user.data_processing_consent,
                'data_processing_consent_date': user.data_processing_consent_date,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'platform_count': len([pc for pc in user.platform_connections if pc.is_active])
            }
            
            return True, "Profile data retrieved successfully", profile_data
            
        except Exception as e:
            logger.error(f"Error getting profile data for user {user_id}: {e}")
            return False, "Failed to retrieve profile data", None
    
    def validate_profile_data(self, profile_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate profile data before update"""
        errors = []
        
        # Validate first name
        if 'first_name' in profile_data:
            first_name = profile_data['first_name']
            if first_name and len(first_name.strip()) > 100:
                errors.append("First name must be no more than 100 characters")
            if first_name and not first_name.strip().replace(' ', '').replace('-', '').replace("'", '').isalpha():
                errors.append("First name can only contain letters, spaces, hyphens, and apostrophes")
        
        # Validate last name
        if 'last_name' in profile_data:
            last_name = profile_data['last_name']
            if last_name and len(last_name.strip()) > 100:
                errors.append("Last name must be no more than 100 characters")
            if last_name and not last_name.strip().replace(' ', '').replace('-', '').replace("'", '').isalpha():
                errors.append("Last name can only contain letters, spaces, hyphens, and apostrophes")
        
        # Validate email
        if 'email' in profile_data:
            email = profile_data['email']
            if not email or not email.strip():
                errors.append("Email address is required")
            else:
                from services.user_management_service import UserRegistrationService
                registration_service = UserRegistrationService(self.db_session)
                email_valid, email_message = registration_service.validate_email_address(email)
                if not email_valid:
                    errors.append(f"Invalid email address: {email_message}")
        
        return len(errors) == 0, errors
    
    def export_user_data(self, user_id: int, 
                        ip_address: Optional[str] = None,
                        user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Export user's personal data for GDPR compliance"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Get comprehensive user data
            user_data = user.export_personal_data()
            
            # Add additional data from related tables
            from models import Post, Image, ProcessingRun
            
            # Get user's posts (if any - this would be for admin users who might have posts)
            posts_data = []
            posts = self.db_session.query(Post).join(Post.platform_connection).filter(
                Post.platform_connection.has(user_id=user_id)
            ).all()
            
            for post in posts:
                posts_data.append({
                    'post_id': post.post_id,
                    'post_url': post.post_url,
                    'created_at': post.created_at.isoformat() if post.created_at else None,
                    'platform_type': post.platform_type,
                    'instance_url': post.instance_url
                })
            
            # Get user's images (captions they've reviewed)
            images_data = []
            images = self.db_session.query(Image).join(Image.platform_connection).filter(
                Image.platform_connection.has(user_id=user_id)
            ).all()
            
            for image in images:
                images_data.append({
                    'image_id': image.id,
                    'original_caption': image.original_caption,
                    'generated_caption': image.generated_caption,
                    'reviewed_caption': image.reviewed_caption,
                    'final_caption': image.final_caption,
                    'status': image.status.value if image.status else None,
                    'created_at': image.created_at.isoformat() if image.created_at else None,
                    'reviewed_at': image.reviewed_at.isoformat() if image.reviewed_at else None,
                    'reviewer_notes': image.reviewer_notes
                })
            
            # Get processing runs
            processing_runs_data = []
            processing_runs = self.db_session.query(ProcessingRun).join(ProcessingRun.platform_connection).filter(
                ProcessingRun.platform_connection.has(user_id=user_id)
            ).all()
            
            for run in processing_runs:
                processing_runs_data.append({
                    'run_id': run.id,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'posts_processed': run.posts_processed,
                    'images_processed': run.images_processed,
                    'captions_generated': run.captions_generated,
                    'status': run.status
                })
            
            # Get audit log entries
            audit_logs = []
            user_audit_entries = self.db_session.query(UserAuditLog).filter_by(user_id=user_id).all()
            
            for entry in user_audit_entries:
                audit_logs.append({
                    'action': entry.action,
                    'details': entry.details,
                    'created_at': entry.created_at.isoformat() if entry.created_at else None,
                    'ip_address': entry.ip_address
                })
            
            # Compile complete data export
            complete_data = {
                'user_profile': user_data,
                'posts': posts_data,
                'images': images_data,
                'processing_runs': processing_runs_data,
                'audit_log': audit_logs,
                'export_timestamp': datetime.utcnow().isoformat(),
                'export_format': 'GDPR_compliant_JSON'
            }
            
            # Log data export
            UserAuditLog.log_action(
                self.db_session,
                action="data_exported",
                user_id=user.id,
                details=f"Personal data exported from {ip_address or 'unknown IP'}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"Personal data exported for user {user.username}")
            return True, "Personal data exported successfully", complete_data
            
        except Exception as e:
            logger.error(f"Error exporting data for user {user_id}: {e}")
            return False, "Data export failed due to system error", None

class UserDeletionService:
    """Service for handling complete user profile deletion with GDPR compliance"""
    
    def __init__(self, db_session: Session):
        """Initialize user deletion service"""
        self.db_session = db_session
    
    def delete_user_profile(self, user_id: int, admin_user_id: Optional[int] = None,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None,
                           confirmation_token: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Delete user profile completely with GDPR compliance"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Prevent deletion of the last admin user
            if user.role == UserRole.ADMIN:
                admin_count = self.db_session.query(User).filter(
                    User.role == UserRole.ADMIN,
                    User.is_active == True,
                    User.id != user_id
                ).count()
                
                if admin_count == 0:
                    return False, "Cannot delete the last admin user", None
            
            # Store user info for audit and return data
            user_info = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.value if user.role else None,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'deletion_timestamp': datetime.utcnow().isoformat()
            }
            
            # Log deletion start
            UserAuditLog.log_action(
                self.db_session,
                action="user_deletion_started",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"User deletion initiated from {ip_address or 'unknown IP'}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            # Step 1: Delete user images from storage
            deleted_images = self._delete_user_images(user)
            
            # Step 2: Delete database entries (cascading will handle related records)
            deleted_records = self._delete_user_database_entries(user)
            
            # Step 3: Remove platform connections and associated content
            deleted_platforms = self._delete_user_platforms(user)
            
            # Step 4: Final user record deletion
            username = user.username
            self.db_session.delete(user)
            self.db_session.commit()
            
            # Log successful deletion (create new audit entry since user is deleted)
            UserAuditLog.log_action(
                self.db_session,
                action="user_deletion_completed",
                user_id=None,  # User no longer exists
                admin_user_id=admin_user_id,
                details=f"User {username} (ID: {user_id}) completely deleted - Images: {deleted_images}, DB records: {deleted_records}, Platforms: {deleted_platforms}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"User {username} (ID: {user_id}) completely deleted")
            
            deletion_summary = {
                'user_info': user_info,
                'deleted_images': deleted_images,
                'deleted_database_records': deleted_records,
                'deleted_platforms': deleted_platforms,
                'deletion_method': 'complete_deletion'
            }
            
            return True, f"User {username} has been completely deleted", deletion_summary
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            return False, "User deletion failed due to system error", None
    
    def _delete_user_images(self, user: User) -> int:
        """Delete all images associated with user from storage"""
        import os
        from pathlib import Path
        
        deleted_count = 0
        
        try:
            # Get all images associated with user's platforms
            from models import Image
            
            user_images = self.db_session.query(Image).join(Image.platform_connection).filter(
                Image.platform_connection.has(user_id=user.id)
            ).all()
            
            for image in user_images:
                if image.local_path and os.path.exists(image.local_path):
                    try:
                        os.remove(image.local_path)
                        deleted_count += 1
                        logger.debug(f"Deleted image file: {image.local_path}")
                    except OSError as e:
                        logger.warning(f"Failed to delete image file {image.local_path}: {e}")
            
            # Also clean up any user-specific directories in storage/images
            storage_path = Path("storage/images")
            if storage_path.exists():
                for user_dir in storage_path.glob(f"user_{user.id}_*"):
                    if user_dir.is_dir():
                        try:
                            import shutil
                            shutil.rmtree(user_dir)
                            logger.debug(f"Deleted user directory: {user_dir}")
                        except OSError as e:
                            logger.warning(f"Failed to delete user directory {user_dir}: {e}")
            
        except Exception as e:
            logger.error(f"Error deleting images for user {user.id}: {e}")
        
        return deleted_count
    
    def _delete_user_database_entries(self, user: User) -> int:
        """Delete all database entries associated with user"""
        deleted_count = 0
        
        try:
            from models import Post, Image, ProcessingRun, UserSession
            
            # Delete processing runs
            processing_runs = self.db_session.query(ProcessingRun).join(ProcessingRun.platform_connection).filter(
                ProcessingRun.platform_connection.has(user_id=user.id)
            ).all()
            
            for run in processing_runs:
                self.db_session.delete(run)
                deleted_count += 1
            
            # Delete images (this will cascade to related records)
            images = self.db_session.query(Image).join(Image.platform_connection).filter(
                Image.platform_connection.has(user_id=user.id)
            ).all()
            
            for image in images:
                self.db_session.delete(image)
                deleted_count += 1
            
            # Delete posts (this will cascade to related records)
            posts = self.db_session.query(Post).join(Post.platform_connection).filter(
                Post.platform_connection.has(user_id=user.id)
            ).all()
            
            for post in posts:
                self.db_session.delete(post)
                deleted_count += 1
            
            # Delete user sessions
            sessions = self.db_session.query(UserSession).filter_by(user_id=user.id).all()
            for session in sessions:
                self.db_session.delete(session)
                deleted_count += 1
            
        except Exception as e:
            logger.error(f"Error deleting database entries for user {user.id}: {e}")
        
        return deleted_count
    
    def _delete_user_platforms(self, user: User) -> int:
        """Delete user's platform connections"""
        deleted_count = 0
        
        try:
            # Platform connections will be deleted by cascade when user is deleted
            # But we count them here for reporting
            deleted_count = len([pc for pc in user.platform_connections if pc.is_active])
            
        except Exception as e:
            logger.error(f"Error counting platforms for user {user.id}: {e}")
        
        return deleted_count
    
    def anonymize_user_profile(self, user_id: int, admin_user_id: Optional[int] = None,
                              ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Anonymize user profile instead of complete deletion (GDPR alternative)"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return False, "User not found", None
            
            # Prevent anonymization of the last admin user
            if user.role == UserRole.ADMIN:
                admin_count = self.db_session.query(User).filter(
                    User.role == UserRole.ADMIN,
                    User.is_active == True,
                    User.id != user_id
                ).count()
                
                if admin_count == 0:
                    return False, "Cannot anonymize the last admin user", None
            
            # Store original info for audit
            original_username = user.username
            original_email = user.email
            
            # Anonymize user data
            anonymous_id = user.anonymize_data()
            
            # Deactivate platform connections
            for platform_connection in user.platform_connections:
                platform_connection.is_active = False
            
            self.db_session.commit()
            
            # Log anonymization
            UserAuditLog.log_action(
                self.db_session,
                action="user_anonymized",
                user_id=user.id,
                admin_user_id=admin_user_id,
                details=f"User {original_username} anonymized to {user.username} from {ip_address or 'unknown IP'}",
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db_session.commit()
            
            logger.info(f"User {original_username} (ID: {user_id}) anonymized to {user.username}")
            
            anonymization_summary = {
                'user_id': user.id,
                'original_username': original_username,
                'original_email': original_email,
                'anonymous_username': user.username,
                'anonymous_email': user.email,
                'anonymous_id': anonymous_id,
                'anonymization_timestamp': datetime.utcnow().isoformat(),
                'deletion_method': 'anonymization'
            }
            
            return True, f"User {original_username} has been anonymized", anonymization_summary
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error anonymizing user {user_id}: {e}")
            return False, "User anonymization failed due to system error", None
    
    def validate_deletion_request(self, user_id: int, requesting_user_id: int) -> Tuple[bool, str]:
        """Validate if user deletion request is allowed"""
        try:
            user = self.db_session.query(User).filter_by(id=user_id).first()
            requesting_user = self.db_session.query(User).filter_by(id=requesting_user_id).first()
            
            if not user:
                return False, "User to delete not found"
            
            if not requesting_user:
                return False, "Requesting user not found"
            
            # Users can delete their own profile
            if user_id == requesting_user_id:
                return True, "User can delete their own profile"
            
            # Admin users can delete other users (except other admins unless they're the last admin)
            if requesting_user.role == UserRole.ADMIN:
                if user.role == UserRole.ADMIN:
                    # Check if this would leave no admin users
                    admin_count = self.db_session.query(User).filter(
                        User.role == UserRole.ADMIN,
                        User.is_active == True,
                        User.id != user_id
                    ).count()
                    
                    if admin_count == 0:
                        return False, "Cannot delete the last admin user"
                
                return True, "Admin can delete user"
            
            return False, "Insufficient permissions to delete user"
            
        except Exception as e:
            logger.error(f"Error validating deletion request: {e}")
            return False, "Validation failed due to system error"