# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# User Management API Documentation

This document provides comprehensive API documentation for the Vedfolnir user management system, including service interfaces, data models, and integration examples.

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication and Authorization](#authentication-and-authorization)
3. [User Registration Services](#user-registration-services)
4. [User Authentication Services](#user-authentication-services)
5. [User Profile Services](#user-profile-services)
6. [Password Management Services](#password-management-services)
7. [Email Services](#email-services)
8. [Admin User Management Services](#admin-user-management-services)
9. [GDPR Compliance Services](#gdpr-compliance-services)
10. [Data Models](#data-models)
11. [Error Handling](#error-handling)
12. [Integration Examples](#integration-examples)

## API Overview

### Service Architecture

The user management system is built using a service-oriented architecture with the following components:

```python
services/
├── user_management_service.py    # Core user management operations
├── email_service.py             # Email communication services
└── gdpr_service.py              # GDPR compliance services
```

### Service Dependencies

```python
# Core dependencies
from sqlalchemy.orm import Session
from models import User, UserSession, EmailVerificationToken
from config import Config
from database import DatabaseManager

# Security dependencies
from werkzeug.security import generate_password_hash, check_password_hash
from secrets import token_urlsafe
import email_validator

# Email dependencies
from flask_mailing import Mail, Message
```

### Service Initialization

```python
from services.user_management_service import (
    UserRegistrationService,
    UserAuthenticationService,
    UserProfileService,
    PasswordManagementService
)
from services.email_service import EmailService
from services.gdpr_service import GDPRService

# Initialize services
config = Config()
db_manager = DatabaseManager(config)
email_service = EmailService(config)

registration_service = UserRegistrationService(db_manager, email_service)
auth_service = UserAuthenticationService(db_manager)
profile_service = UserProfileService(db_manager, email_service)
password_service = PasswordManagementService(db_manager, email_service)
gdpr_service = GDPRService(db_manager)
```

## Authentication and Authorization

### Session-Based Authentication

The system uses database-stored sessions for authentication:

```python
from session_manager import SessionManager

class AuthenticationRequired:
    """Decorator for routes requiring authentication"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
    
    def __call__(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_token = request.cookies.get('session_token')
            if not session_token:
                return redirect(url_for('login'))
            
            user_session = self.session_manager.validate_session(session_token)
            if not user_session:
                return redirect(url_for('login'))
            
            g.current_user = user_session.user
            g.current_session = user_session
            return f(*args, **kwargs)
        return decorated_function
```

### Role-Based Authorization

```python
from functools import wraps
from models import UserRole

def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.current_user or g.current_user.role != UserRole.ADMIN:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def viewer_or_admin_required(f):
    """Decorator for viewer or admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.current_user:
            abort(401)
        if g.current_user.role not in [UserRole.VIEWER, UserRole.ADMIN]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
```

## User Registration Services

### UserRegistrationService

```python
class UserRegistrationService:
    """Service for handling user registration operations"""
    
    def __init__(self, db_manager: DatabaseManager, email_service: EmailService):
        self.db_manager = db_manager
        self.email_service = email_service
    
    def register_user(self, username: str, email: str, password: str, 
                     first_name: str = None, last_name: str = None,
                     role: UserRole = UserRole.VIEWER) -> Dict[str, Any]:
        """
        Register a new user account
        
        Args:
            username: Unique username for the account
            email: Valid email address for verification
            password: Plain text password (will be hashed)
            first_name: Optional first name
            last_name: Optional last name
            role: User role (default: VIEWER)
        
        Returns:
            Dict containing registration result and user information
        
        Raises:
            ValidationError: If input validation fails
            DuplicateUserError: If username or email already exists
            EmailDeliveryError: If verification email fails to send
        """
        
    def send_verification_email(self, user_id: int) -> bool:
        """
        Send email verification to user
        
        Args:
            user_id: ID of user to send verification email
        
        Returns:
            True if email sent successfully, False otherwise
        """
        
    def verify_email(self, token: str) -> Dict[str, Any]:
        """
        Verify user email using verification token
        
        Args:
            token: Email verification token
        
        Returns:
            Dict containing verification result
        
        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        
    def resend_verification_email(self, user_id: int) -> bool:
        """
        Resend verification email to user
        
        Args:
            user_id: ID of user to resend verification email
        
        Returns:
            True if email sent successfully, False otherwise
        """
```

### Registration API Usage

```python
# Example: User self-registration
try:
    result = registration_service.register_user(
        username="john_doe",
        email="john@example.com",
        password="SecurePass123!",
        first_name="John",
        last_name="Doe"
    )
    
    if result['success']:
        user_id = result['user_id']
        print(f"User registered successfully: {user_id}")
        print("Verification email sent")
    else:
        print(f"Registration failed: {result['error']}")
        
except ValidationError as e:
    print(f"Validation error: {e}")
except DuplicateUserError as e:
    print(f"User already exists: {e}")
```

## User Authentication Services

### UserAuthenticationService

```python
class UserAuthenticationService:
    """Service for handling user authentication operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session_manager = SessionManager(db_manager)
    
    def authenticate_user(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user credentials
        
        Args:
            username_or_email: Username or email address
            password: Plain text password
        
        Returns:
            Dict containing authentication result and user information
        
        Raises:
            AuthenticationError: If credentials are invalid
            AccountLockedError: If account is locked
            EmailNotVerifiedError: If email is not verified
        """
        
    def login_user(self, user: User, remember: bool = False) -> str:
        """
        Create user session and return session token
        
        Args:
            user: User object to create session for
            remember: Whether to create long-lived session
        
        Returns:
            Session token string
        """
        
    def logout_user(self, session_token: str) -> bool:
        """
        Invalidate user session
        
        Args:
            session_token: Session token to invalidate
        
        Returns:
            True if logout successful, False otherwise
        """
        
    def check_account_status(self, user: User) -> Dict[str, Any]:
        """
        Check user account status and restrictions
        
        Args:
            user: User object to check
        
        Returns:
            Dict containing account status information
        """
```

### Authentication API Usage

```python
# Example: User login
try:
    auth_result = auth_service.authenticate_user(
        username_or_email="john_doe",
        password="SecurePass123!"
    )
    
    if auth_result['success']:
        user = auth_result['user']
        session_token = auth_service.login_user(user, remember=True)
        print(f"Login successful, session: {session_token}")
    else:
        print(f"Login failed: {auth_result['error']}")
        
except AccountLockedError as e:
    print(f"Account locked: {e}")
except EmailNotVerifiedError as e:
    print(f"Email not verified: {e}")
```

## User Profile Services

### UserProfileService

```python
class UserProfileService:
    """Service for handling user profile operations"""
    
    def __init__(self, db_manager: DatabaseManager, email_service: EmailService):
        self.db_manager = db_manager
        self.email_service = email_service
    
    def update_profile(self, user_id: int, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user profile information
        
        Args:
            user_id: ID of user to update
            profile_data: Dictionary containing profile updates
        
        Returns:
            Dict containing update result
        
        Raises:
            ValidationError: If profile data is invalid
            UserNotFoundError: If user doesn't exist
        """
        
    def change_email(self, user_id: int, new_email: str) -> Dict[str, Any]:
        """
        Initiate email change process
        
        Args:
            user_id: ID of user changing email
            new_email: New email address
        
        Returns:
            Dict containing email change result
        
        Raises:
            ValidationError: If email format is invalid
            DuplicateEmailError: If email already in use
        """
        
    def delete_user_profile(self, user_id: int, admin_user_id: int = None) -> Dict[str, Any]:
        """
        Delete user profile and all associated data
        
        Args:
            user_id: ID of user to delete
            admin_user_id: ID of admin performing deletion (if applicable)
        
        Returns:
            Dict containing deletion result
        
        Raises:
            UserNotFoundError: If user doesn't exist
            PermissionError: If deletion not allowed
        """
        
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Export all user data for GDPR compliance
        
        Args:
            user_id: ID of user to export data for
        
        Returns:
            Dict containing complete user data export
        """
```

### Profile API Usage

```python
# Example: Update user profile
try:
    profile_data = {
        'first_name': 'John',
        'last_name': 'Smith',
        'email': 'john.smith@example.com'
    }
    
    result = profile_service.update_profile(user_id=123, profile_data=profile_data)
    
    if result['success']:
        print("Profile updated successfully")
        if result.get('email_verification_required'):
            print("Email verification required for new email address")
    else:
        print(f"Profile update failed: {result['error']}")
        
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Password Management Services

### PasswordManagementService

```python
class PasswordManagementService:
    """Service for handling password management operations"""
    
    def __init__(self, db_manager: DatabaseManager, email_service: EmailService):
        self.db_manager = db_manager
        self.email_service = email_service
    
    def initiate_password_reset(self, email: str) -> Dict[str, Any]:
        """
        Initiate password reset process
        
        Args:
            email: Email address of user requesting reset
        
        Returns:
            Dict containing reset initiation result
        
        Raises:
            UserNotFoundError: If no user with email exists
            EmailDeliveryError: If reset email fails to send
        """
        
    def verify_reset_token(self, token: str) -> Dict[str, Any]:
        """
        Verify password reset token
        
        Args:
            token: Password reset token
        
        Returns:
            Dict containing token verification result
        
        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        
    def reset_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """
        Complete password reset using token
        
        Args:
            token: Valid password reset token
            new_password: New password (plain text, will be hashed)
        
        Returns:
            Dict containing password reset result
        
        Raises:
            InvalidTokenError: If token is invalid or expired
            ValidationError: If password doesn't meet requirements
        """
        
    def change_password(self, user_id: int, current_password: str, 
                       new_password: str) -> Dict[str, Any]:
        """
        Change user password (authenticated user)
        
        Args:
            user_id: ID of user changing password
            current_password: Current password for verification
            new_password: New password (plain text, will be hashed)
        
        Returns:
            Dict containing password change result
        
        Raises:
            AuthenticationError: If current password is incorrect
            ValidationError: If new password doesn't meet requirements
        """
```

### Password Management API Usage

```python
# Example: Password reset flow
try:
    # Step 1: Initiate reset
    reset_result = password_service.initiate_password_reset("john@example.com")
    
    if reset_result['success']:
        print("Password reset email sent")
        
        # Step 2: User clicks link, verify token
        token = "reset_token_from_email"
        verify_result = password_service.verify_reset_token(token)
        
        if verify_result['valid']:
            # Step 3: Complete reset
            new_password = "NewSecurePass123!"
            reset_complete = password_service.reset_password(token, new_password)
            
            if reset_complete['success']:
                print("Password reset completed successfully")
            else:
                print(f"Password reset failed: {reset_complete['error']}")
        else:
            print("Invalid or expired reset token")
    else:
        print(f"Reset initiation failed: {reset_result['error']}")
        
except UserNotFoundError as e:
    print(f"User not found: {e}")
```

## Email Services

### EmailService

```python
class EmailService:
    """Service for handling email communications"""
    
    def __init__(self, config: Config):
        self.config = config
        self.mail = Mail()
    
    def send_verification_email(self, user: User, token: str) -> bool:
        """
        Send email verification email
        
        Args:
            user: User object to send email to
            token: Verification token
        
        Returns:
            True if email sent successfully, False otherwise
        """
        
    def send_password_reset_email(self, user: User, token: str) -> bool:
        """
        Send password reset email
        
        Args:
            user: User object to send email to
            token: Password reset token
        
        Returns:
            True if email sent successfully, False otherwise
        """
        
    def send_account_created_email(self, user: User, temporary_password: str) -> bool:
        """
        Send account created notification (admin-created accounts)
        
        Args:
            user: User object to send email to
            temporary_password: Temporary password for first login
        
        Returns:
            True if email sent successfully, False otherwise
        """
        
    def send_profile_deleted_confirmation(self, email: str) -> bool:
        """
        Send profile deletion confirmation
        
        Args:
            email: Email address to send confirmation to
        
        Returns:
            True if email sent successfully, False otherwise
        """
```

### Email Service Configuration

```python
# Email configuration in config.py
class Config:
    # Email settings from environment variables
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Email template settings
    MAIL_TEMPLATE_FOLDER = 'templates/emails'
    VERIFICATION_TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours
    RESET_TOKEN_EXPIRY = 60 * 60  # 1 hour
```

## Admin User Management Services

### AdminUserService

```python
class AdminUserService:
    """Service for admin user management operations"""
    
    def __init__(self, db_manager: DatabaseManager, email_service: EmailService):
        self.db_manager = db_manager
        self.email_service = email_service
        self.user_service = UserProfileService(db_manager, email_service)
    
    def create_user(self, admin_user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new user account (admin operation)
        
        Args:
            admin_user_id: ID of admin creating the user
            user_data: Dictionary containing user information
        
        Returns:
            Dict containing user creation result
        
        Raises:
            PermissionError: If admin doesn't have permission
            ValidationError: If user data is invalid
        """
        
    def update_user(self, admin_user_id: int, user_id: int, 
                   update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user account (admin operation)
        
        Args:
            admin_user_id: ID of admin performing update
            user_id: ID of user to update
            update_data: Dictionary containing updates
        
        Returns:
            Dict containing update result
        """
        
    def delete_user(self, admin_user_id: int, user_id: int) -> Dict[str, Any]:
        """
        Delete user account (admin operation)
        
        Args:
            admin_user_id: ID of admin performing deletion
            user_id: ID of user to delete
        
        Returns:
            Dict containing deletion result
        """
        
    def reset_user_password(self, admin_user_id: int, user_id: int) -> Dict[str, Any]:
        """
        Reset user password (admin operation)
        
        Args:
            admin_user_id: ID of admin performing reset
            user_id: ID of user whose password to reset
        
        Returns:
            Dict containing password reset result
        """
        
    def get_user_list(self, admin_user_id: int, filters: Dict[str, Any] = None) -> List[Dict]:
        """
        Get list of users with optional filtering
        
        Args:
            admin_user_id: ID of admin requesting list
            filters: Optional filters for user list
        
        Returns:
            List of user dictionaries
        """
        
    def get_user_statistics(self, admin_user_id: int) -> Dict[str, Any]:
        """
        Get user management statistics
        
        Args:
            admin_user_id: ID of admin requesting statistics
        
        Returns:
            Dict containing user statistics
        """
```

## GDPR Compliance Services

### GDPRService

```python
class GDPRService:
    """Service for GDPR compliance operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Export all user data for GDPR compliance
        
        Args:
            user_id: ID of user to export data for
        
        Returns:
            Dict containing complete user data export
        """
        
    def anonymize_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Anonymize user data while preserving system integrity
        
        Args:
            user_id: ID of user to anonymize
        
        Returns:
            Dict containing anonymization result
        """
        
    def delete_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Completely delete all user data
        
        Args:
            user_id: ID of user to delete data for
        
        Returns:
            Dict containing deletion result
        """
        
    def generate_compliance_report(self, user_id: int) -> Dict[str, Any]:
        """
        Generate GDPR compliance report for user
        
        Args:
            user_id: ID of user to generate report for
        
        Returns:
            Dict containing compliance report
        """
```

## Data Models

### User Model

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

Base = declarative_base()

class UserRole(PyEnum):
    ADMIN = "admin"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Basic information
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Personal information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Role and status
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_sent_at = Column(DateTime, nullable=True)
    password_reset_used = Column(Boolean, default=False)
    
    # GDPR compliance
    data_processing_consent = Column(Boolean, default=False)
    data_processing_consent_date = Column(DateTime, nullable=True)
    
    # Account security
    account_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'account_locked': self.account_locked,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
```

### Email Verification Token Model

```python
class EmailVerificationToken(Base):
    __tablename__ = 'email_verification_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    email = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", backref="verification_tokens")
```

### User Audit Log Model

```python
class UserAuditLog(Base):
    __tablename__ = 'user_audit_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    admin_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="audit_logs")
    admin_user = relationship("User", foreign_keys=[admin_user_id])
```

## Error Handling

### Custom Exceptions

```python
class UserManagementError(Exception):
    """Base exception for user management errors"""
    pass

class ValidationError(UserManagementError):
    """Raised when input validation fails"""
    pass

class DuplicateUserError(UserManagementError):
    """Raised when attempting to create duplicate user"""
    pass

class UserNotFoundError(UserManagementError):
    """Raised when user is not found"""
    pass

class AuthenticationError(UserManagementError):
    """Raised when authentication fails"""
    pass

class AccountLockedError(UserManagementError):
    """Raised when account is locked"""
    pass

class EmailNotVerifiedError(UserManagementError):
    """Raised when email is not verified"""
    pass

class InvalidTokenError(UserManagementError):
    """Raised when token is invalid or expired"""
    pass

class EmailDeliveryError(UserManagementError):
    """Raised when email delivery fails"""
    pass

class PermissionError(UserManagementError):
    """Raised when user lacks required permissions"""
    pass
```

### Error Response Format

```python
def create_error_response(error: Exception, status_code: int = 400) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        'success': False,
        'error': {
            'type': error.__class__.__name__,
            'message': str(error),
            'status_code': status_code
        }
    }

def create_success_response(data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create standardized success response"""
    response = {'success': True}
    if data:
        response.update(data)
    return response
```

## Integration Examples

### Flask Route Integration

```python
from flask import Blueprint, request, jsonify, g
from services.user_management_service import UserRegistrationService

user_bp = Blueprint('user', __name__)

@user_bp.route('/register', methods=['POST'])
def register_user():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        result = registration_service.register_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name')
        )
        
        return jsonify(create_success_response(result))
        
    except ValidationError as e:
        return jsonify(create_error_response(e, 400)), 400
    except DuplicateUserError as e:
        return jsonify(create_error_response(e, 409)), 409
    except Exception as e:
        return jsonify(create_error_response(e, 500)), 500

@user_bp.route('/login', methods=['POST'])
@csrf.exempt  # Handle CSRF in service layer
def login_user():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        auth_result = auth_service.authenticate_user(
            username_or_email=data['username_or_email'],
            password=data['password']
        )
        
        if auth_result['success']:
            session_token = auth_service.login_user(
                user=auth_result['user'],
                remember=data.get('remember', False)
            )
            
            response = jsonify(create_success_response({
                'user': auth_result['user'].to_dict(),
                'session_token': session_token
            }))
            
            # Set secure cookie
            response.set_cookie(
                'session_token',
                session_token,
                httponly=True,
                secure=True,
                samesite='Strict'
            )
            
            return response
        else:
            return jsonify(create_error_response(
                Exception(auth_result['error']), 401
            )), 401
            
    except AccountLockedError as e:
        return jsonify(create_error_response(e, 423)), 423
    except EmailNotVerifiedError as e:
        return jsonify(create_error_response(e, 403)), 403
    except Exception as e:
        return jsonify(create_error_response(e, 500)), 500
```

### Service Layer Testing

```python
import unittest
from unittest.mock import Mock, patch
from services.user_management_service import UserRegistrationService

class TestUserRegistrationService(unittest.TestCase):
    
    def setUp(self):
        self.db_manager = Mock()
        self.email_service = Mock()
        self.service = UserRegistrationService(self.db_manager, self.email_service)
    
    def test_register_user_success(self):
        """Test successful user registration"""
        # Mock database operations
        self.db_manager.get_user_by_username.return_value = None
        self.db_manager.get_user_by_email.return_value = None
        self.db_manager.create_user.return_value = Mock(id=123)
        
        # Mock email service
        self.email_service.send_verification_email.return_value = True
        
        result = self.service.register_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['user_id'], 123)
        self.db_manager.create_user.assert_called_once()
        self.email_service.send_verification_email.assert_called_once()
    
    def test_register_user_duplicate_username(self):
        """Test registration with duplicate username"""
        # Mock existing user
        self.db_manager.get_user_by_username.return_value = Mock()
        
        with self.assertRaises(DuplicateUserError):
            self.service.register_user(
                username="existinguser",
                email="test@example.com",
                password="TestPass123!"
            )
```

This API documentation provides comprehensive information for integrating with and extending the Vedfolnir user management system. All services follow consistent patterns and provide robust error handling for reliable operation.