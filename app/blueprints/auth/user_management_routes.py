# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Management Routes

This module contains all routes related to user management including registration,
email verification, login, and profile management.
"""

import asyncio
import logging
from datetime import datetime
from urllib.parse import urlparse as url_parse
from flask import Blueprint, render_template, request, redirect, url_for, current_app, make_response, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.orm import joinedload

# Import unified notification system
from app.services.notification.helpers.notification_helpers import (
    send_user_notification, send_success_notification, send_error_notification, 
    send_warning_notification, send_info_notification
)
from models import NotificationType, NotificationCategory

def validate_form_submission(form):
    """
    Manual form validation replacement for validate_on_submit()
    Since we're using regular WTForms instead of Flask-WTF
    """
    return request.method == 'POST' and form.validate()

from app.utils.forms.user_management_forms import (
    UserRegistrationForm, LoginForm, ProfileEditForm, PasswordChangeForm,
    PasswordResetRequestForm, PasswordResetForm, ProfileDeleteForm,
    EmailVerificationResendForm
)
from app.services.user.components.user_management_service import UserRegistrationService, UserAuthenticationService
from app.services.email.components.email_service import email_service
from models import User, UserRole, UserAuditLog
from app.core.security.core.decorators import conditional_rate_limit, conditional_validate_input_length
from app.core.security.core.security_utils import sanitize_for_log
from app.core.security.core.enhanced_rate_limiter import rate_limit_user_management

logger = logging.getLogger(__name__)
# from app.core.security.core.enhanced_csrf_protection import csrf_protect_user_management, csrf_protect_admin_operation
from app.core.security.core.decorators import conditional_validate_csrf_token
from app.core.security.validation.enhanced_input_validator import (
    validate_user_input, USER_REGISTRATION_RULES, USER_LOGIN_RULES, 
    PROFILE_UPDATE_RULES, PASSWORD_CHANGE_RULES, ADMIN_USER_CREATE_RULES
)
from app.core.security.monitoring.security_event_logger import get_security_event_logger
from app.core.security.error_handling.user_management_error_handler import (
    UserManagementErrorHandler, handle_user_management_errors, graceful_degradation,
    UserManagementError, ValidationError, AuthenticationError, DatabaseError
)
from app.core.security.error_handling.system_recovery import with_recovery, SystemRecoveryManager
from app.core.session.core.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Create blueprint for user management routes
user_management_bp = Blueprint('user_management', __name__, url_prefix='/user-management')

def get_client_ip():
    """Get client IP address from request"""
    try:
        # Check for forwarded IP first (behind proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr
    except Exception:
        return None

def get_user_agent():
    """Get user agent from request"""
    try:
        return request.headers.get('User-Agent', '')
    except Exception:
        return ''

def get_base_url():
    """Get base URL for email links"""
    return request.url_root.rstrip('/')

@user_management_bp.route('/register', methods=['GET', 'POST'])
@rate_limit_user_management('registration')
@conditional_validate_csrf_token
@validate_user_input(USER_REGISTRATION_RULES)
@handle_user_management_errors
@with_recovery('database_connection', max_retries=2)
def register():
    """User registration with email verification"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = UserRegistrationForm(request.form if request.method == 'POST' else None)
    
    if validate_form_submission(form):
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            unified_session_manager = getattr(current_app, "unified_session_manager", None)
            
            with unified_session_manager.get_db_session() as db_session:
                # Initialize registration service
                registration_service = UserRegistrationService(
                    db_session=db_session,
                    base_url=get_base_url()
                )
                
                # Get security event logger
                security_logger = get_security_event_logger(db_session)
                
                # Register user
                success, message, user = registration_service.register_user(
                    username=form.username.data,
                    email=form.email.data,
                    password=form.password.data,
                    role=UserRole.VIEWER,  # Default role for self-registration
                    first_name=form.first_name.data or None,
                    last_name=form.last_name.data or None,
                    require_email_verification=True,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Log registration event
                security_logger.log_registration_event(
                    success=success,
                    email=form.email.data,
                    user_id=user.id if user else None,
                    failure_reason=message if not success else None
                )
                
                if success and user:
                    # Send verification email using email service directly
                    try:
                        from app.services.email.components.email_service import email_service
                        import asyncio
                        
                        # Generate verification link
                        verification_token = user.generate_email_verification_token()
                        verification_link = url_for('auth.user_management.verify_email', 
                                                   token=verification_token, _external=True)
                        
                        # Send via email service directly (bypasses notification system)
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            email_sent = loop.run_until_complete(
                                email_service.send_verification_email(
                                    user_email=user.email,
                                    username=user.username,
                                    verification_token=verification_token,
                                    base_url=request.url_root
                                )
                            )
                        finally:
                            loop.close()
                        
                        if email_sent:
                            send_success_notification(
                                message='Registration successful! Please check your email for verification.',
                                title='Registration Complete',
                                user_id=user.id
                            )
                            logger.info(f"User {sanitize_for_log(user.username)} registered successfully")
                        else:
                            send_success_notification(
                                message='Registration successful! Please check your email for verification.',
                                title='Registration Complete',
                                user_id=user.id
                            )
                            # Also send notification for anonymous users (since they're not authenticated yet)
                            send_success_notification(
                                message='Registration successful! Please check your email for verification.',
                                title='Registration Complete'
                            )
                    except Exception as email_error:
                        logger.error(f"Error sending verification email: {email_error}")
                        send_success_notification(
                            message='Registration successful! Please check your email for verification.',
                            title='Registration Complete',
                            user_id=user.id
                        )
                        # Also send notification for anonymous users (since they're not authenticated yet)
                        send_success_notification(
                            message='Registration successful! Please check your email for verification.',
                            title='Registration Complete'
                        )
                        # Also send notification for anonymous users (since they're not authenticated yet)
                        send_success_notification(
                            message='Registration successful! Please check your email for verification.',
                            title='Registration Complete'
                        )
                    
                    return redirect(url_for('.login'))
                else:
                    send_error_notification(
                        message=message or 'Registration failed. Please try again.',
                        title='Registration Failed'
                    )
                    logger.warning(f"Registration failed: {sanitize_for_log(message)}")
                    
        except Exception as e:
            logger.error(f"Error during registration: {e}")
            send_error_notification(
                message='Registration failed due to a system error. Please try again.',
                title='Registration Error'
            )
    else:
        # Form validation failed - send notification about validation errors
        if request.method == 'POST':
            # Collect all form validation errors
            error_messages = []
            for field_name, field_errors in form.errors.items():
                for error in field_errors:
                    error_messages.append(f"{field_name.replace('_', ' ').title()}: {error}")
            
            if error_messages:
                # Send a notification with the validation errors
                send_error_notification(
                    message='; '.join(error_messages),
                    title='Registration Form Validation Failed'
                )
                logger.info(f"Registration form validation failed: {'; '.join(error_messages)}")
    
    return render_template('user_management/register.html', form=form)


@user_management_bp.route('/login', methods=['GET', 'POST'])
@conditional_rate_limit(limit=10, window_seconds=300)  # 10 attempts per 5 minutes per IP
@conditional_validate_input_length()
def login():
    """User login with Redis session management"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm(request.form)
    
    if validate_form_submission(form):
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            unified_session_manager = getattr(current_app, "unified_session_manager", None)
            
            with unified_session_manager.get_db_session() as db_session:
                # Initialize user authentication service with core session manager
                from app.services.user.components.user_management_service import UserAuthenticationService
                core_session_manager = getattr(current_app, 'core_session_manager', None)
                user_service = UserAuthenticationService(db_session, session_manager=core_session_manager)
                
                # Authenticate user
                success, message, user = user_service.authenticate_user(
                    username_or_email=form.username_or_email.data,
                    password=form.password.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success and user:
                    # Log in user with Flask-Login
                    login_user(user, remember=form.remember_me.data if hasattr(form, 'remember_me') else False)
                    
                    # Create Redis session using core session manager
                    core_session_manager = getattr(current_app, 'core_session_manager', None)
                    if core_session_manager:
                        session_token = core_session_manager.create_session(
                            user_id=user.id,
                            platform_connection_id=None  # Will be set when user selects platform
                        )
                        logger.info(f"User {sanitize_for_log(user.username)} logged in successfully")
                    
                    # Send success notification
                    from app.services.notification.helpers.notification_helpers import send_success_notification
                    send_success_notification("Login successful! Welcome back.", "Welcome Back")
                    
                    # Redirect to next page or dashboard
                    next_page = request.args.get('next')
                    if next_page and url_parse(next_page).netloc == '':
                        return redirect(next_page)
                    return redirect(url_for('main.index'))
                else:
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification(message or 'Invalid username/email or password.', 'Login Failed')
                    logger.warning(f"Failed login attempt for {sanitize_for_log(form.username_or_email.data)} from {sanitize_for_log(ip_address)}")
                    
        except Exception as e:
            logger.error(f"Error during login: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Login failed due to a system error. Please try again.", "Login Error")
    
    return render_template('user_management/login.html', form=form)

@user_management_bp.route('/forgot-password', methods=['GET', 'POST'])
@conditional_rate_limit(limit=5, window_seconds=3600)  # 5 attempts per hour per IP
@conditional_validate_input_length()
def forgot_password():
    """Password reset request"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = PasswordResetRequestForm()
    
    if validate_form_submission(form):
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            unified_session_manager = getattr(current_app, "unified_session_manager", None)
            
            with unified_session_manager.get_db_session() as db_session:
                # Initialize password management service
                from app.services.user.components.user_management_service import PasswordManagementService
                password_service = PasswordManagementService(
                    db_session=db_session,
                    base_url=get_base_url()
                )
                
                # Request password reset
                success, message = password_service.request_password_reset(
                    email=form.email.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    # Send success notification
                    from app.services.notification.helpers.notification_helpers import send_success_notification
                    send_success_notification("Password reset link sent to your email address.", "Reset Link Sent")
                    logger.info(f"Password reset requested for email {sanitize_for_log(form.email.data)}")
                else:
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification(message or 'Failed to send password reset link.', 'Reset Failed')
                    logger.warning(f"Password reset failed for email {sanitize_for_log(form.email.data)}")
                
        except Exception as e:
            logger.error(f"Error during password reset request: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Password reset failed due to a system error. Please try again.", "Reset Error")
    
    return render_template('user_management/forgot_password.html', form=form)


@user_management_bp.route('/get-anonymous-notifications', methods=['GET'])
def get_anonymous_notifications():
    """Get anonymous user notifications from session"""
    try:
        from app.services.notification.helpers.notification_helpers import get_anonymous_notifications
        
        # Retrieve anonymous notifications
        notifications = get_anonymous_notifications()
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'count': len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving anonymous notifications: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve notifications',
            'notifications': [],
            'count': 0
        }), 500


@user_management_bp.route('/resend-verification', methods=['POST'])
@login_required
@conditional_rate_limit(limit=3, window_seconds=300)  # 3 resends per 5 minutes per user
def resend_verification():
    """Resend email verification"""
    if current_user.email_verified:
        send_error_notification(
            message='Your email is already verified.',
            title='Already Verified'
        )
        return redirect(url_for('auth.user_management.profile'))
    
    try:
        # Use request-scoped session manager for database operations
        unified_session_manager = getattr(current_app, "unified_session_manager", None)
        
        with unified_session_manager.get_db_session() as db_session:
            # Initialize registration service
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url=get_base_url()
            )
            
            # Resend verification email using email service directly
            from app.services.email.components.email_service import email_service
            import asyncio
            
            # Generate verification link
            verification_token = current_user.generate_email_verification_token()
            verification_link = url_for('auth.user_management.verify_email', 
                                       token=verification_token, _external=True)
            
            # Send via email service directly (bypasses notification system)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                email_sent = loop.run_until_complete(
                    email_service.send_verification_email(
                        user_email=current_user.email,
                        username=current_user.username,
                        verification_token=verification_token,
                        base_url=request.url_root
                    )
                )
            finally:
                loop.close()
            
            if email_sent:
                send_success_notification(
                    message='Verification email sent! Please check your inbox.',
                    title='Email Sent'
                )
            else:
                send_error_notification(
                    message='Failed to send verification email. Please try again.',
                    title='Send Failed'
                )
                
    except Exception as e:
        logger.error(f"Error resending verification email: {e}")
        send_error_notification(
            message='Failed to send verification email due to system error.',
            title='System Error'
        )
    
    return redirect(url_for('auth.user_management.profile'))

@user_management_bp.route('/verify-email/<token>', methods=['GET'])
@conditional_rate_limit(limit=10, window_seconds=3600)  # 10 attempts per hour per IP
def verify_email(token):
    """Email verification with token validation"""
    # Redirect if user is already logged in and verified
    if current_user.is_authenticated and current_user.email_verified:
        return redirect(url_for('main.index'))
    
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Use request-scoped session manager for database operations
        unified_session_manager = getattr(current_app, "unified_session_manager", None)
        
        with unified_session_manager.get_db_session() as db_session:
            # Find user by verification token
            user = db_session.query(User).filter(User.email_verification_token == token).first()
            
            if user and user.verify_email_token(token):
                # Mark email as verified
                user.email_verified = True
                user.email_verification_token = None
                user.email_verification_sent_at = None
                db_session.commit()
                
                # Log successful verification
                send_success_notification(
                    message=f'Email verified successfully for user {user.email}, please login',
                    title='Email Verification Successful'
                )
                
                # If user is logged in, redirect to profile
                if current_user.is_authenticated and current_user.id == user.id:
                    return redirect(url_for('auth.user_management.profile'))
                else:
                    # Redirect to login with success message
                    return redirect(url_for('auth.user_management.login', 
                                          verification_success='true'))
            else:
                # Log failed verification
                logger.warning(f"Invalid or expired email verification token: {token[:10]}...")
                send_error_notification(
                    message='Invalid or expired verification token',
                    title='Email Verification Failed'
                )
                
                return render_template('user_management/verification_error.html', 
                                     error_message='Invalid or expired verification token.')
                
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        send_error_notification(
            message='Failed to verify email due to system error.',
            title='System Error'
        )
        return render_template('user_management/verification_error.html', 
                             error_message='System error occurred during verification.')

@user_management_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@conditional_rate_limit(limit=5, window_seconds=3600)  # 5 attempts per hour per IP
@conditional_validate_input_length()
def reset_password(token):
    """Password reset completion with token validation"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Use request-scoped session manager for database operations
        unified_session_manager = getattr(current_app, "unified_session_manager", None)
        
        with unified_session_manager.get_db_session() as db_session:
            # Initialize password management service
            from app.services.user.components.user_management_service import PasswordManagementService
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url=get_base_url()
            )
            
            # Verify token first
            token_valid, token_message, user = password_service.verify_reset_token(token)
            
            if not token_valid:
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification(f'Password reset failed: {token_message}', 'Password Reset Failed')
                logger.warning(f"Invalid password reset token attempted: {token[:10]}...")
                return redirect(url_for('auth.user_management.forgot_password'))
            
            # Token is valid, show reset form
            form = PasswordResetForm()
            
            if validate_form_submission(form):
                # Reset password
                reset_success, reset_message, reset_user = password_service.reset_password(
                    token=token,
                    new_password=form.password.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if reset_success and reset_user:
                    # Invalidate all existing sessions for security after password reset
                    try:
                        session_manager = getattr(current_app, 'core_session_manager', None)
                        if session_manager:
                            session_manager.cleanup_user_sessions(reset_user.id)
                            logger.info(f"Invalidated all sessions for user {sanitize_for_log(reset_user.username)} after password reset")
                    except Exception as e:
                        logger.warning(f"Failed to invalidate sessions after password reset: {e}")
                    
                    send_success_notification(
                        message='Password reset successful. You can now log in with your new password.',
                        title='Password Reset Complete'
                    )
                    return redirect(url_for('.login'))
                else:
                    send_error_notification(
                        message=reset_message or 'Password reset failed. Please try again.',
                        title='Password Reset Failed'
                    )
                    logger.warning(f"Password reset failed for token {token[:10]}...")
            
            return render_template('user_management/reset_password.html', form=form, token=token)
            
    except Exception as e:
        logger.error(f"Error during password reset: {e}")
        send_error_notification(
            message='Password reset failed due to a system error. Please try again.',
            title='Password Reset Error'
        )
        return redirect(url_for('auth.user_management.forgot_password'))

@user_management_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@conditional_rate_limit(limit=5, window_seconds=3600)  # 5 attempts per hour per user
@conditional_validate_input_length()
def change_password():
    """Password change for authenticated users"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.form)
    else:
        form = PasswordChangeForm()
    
    if validate_form_submission(form):
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            unified_session_manager = getattr(current_app, "unified_session_manager", None)
            
            with unified_session_manager.get_db_session() as db_session:
                # Initialize password management service
                from app.services.user.components.user_management_service import PasswordManagementService
                password_service = PasswordManagementService(
                    db_session=db_session,
                    base_url=get_base_url()
                )
                
                # Change password
                success, message = password_service.change_password(
                    user_id=current_user.id,
                    current_password=form.current_password.data,
                    new_password=form.new_password.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    send_success_notification(
                        message='Password changed successfully!',
                        title='Password Updated'
                    )
                    logger.info(f"Password changed for user {sanitize_for_log(current_user.username)}")
                    
                    # Invalidate all other sessions for security
                    try:
                        session_manager = getattr(current_app, 'core_session_manager', None)
                        if session_manager:
                            # Get current session ID from Redis session
                            from app.core.session.middleware.session_middleware_v2 import get_current_session_id
                            current_session_id = get_current_session_id()
                            session_manager.cleanup_user_sessions(current_user.id, keep_current=current_session_id)
                            logger.info(f"Invalidated other sessions for user {sanitize_for_log(current_user.username)} after password change")
                    except Exception as e:
                        logger.warning(f"Failed to invalidate other sessions after password change: {e}")
                    
                    # Send success notification and redirect to login page
                    send_success_notification(
                        message='Your password has been successfully changed. Please log in with your new password.',
                        title='Password Changed Successfully'
                    )
                    
                    # Log out the user after successful password change
                    from app.core.session.middleware.session_middleware_v2 import destroy_current_session
                    session_destroyed = destroy_current_session()
                    
                    if session_destroyed:
                        logger.info(f"Session destroyed for user {sanitize_for_log(current_user.username)} after password change")
                    
                    # Redirect to login page with success message
                    return redirect(url_for('auth.user_management.login'))
                else:
                    send_error_notification(
                        message=message or 'Password change failed. Please try again.',
                        title='Password Change Failed'
                    )
                    logger.warning(f"Password change failed for user {sanitize_for_log(current_user.username)}: {message}")
                    
        except Exception as e:
            logger.error(f"Error during password change: {e}")
            send_error_notification(
                message='Password change failed. Please try again.',
                title='Password Change Error'
            )
    else:
        # Form validation failed - send notification about validation errors
        if request.method == 'POST':
            # Collect all form validation errors
            error_messages = []
            for field_name, field_errors in form.errors.items():
                for error in field_errors:
                    error_messages.append(f"{field_name.replace('_', ' ').title()}: {error}")
            
            if error_messages:
                # Send a notification with the validation errors
                send_error_notification(
                    message='; '.join(error_messages),
                    title='Password Change Form Validation Failed'
                )
                logger.info(f"Password change form validation failed: {'; '.join(error_messages)}")
    
    return render_template('user_management/change_password.html', form=form)

@user_management_bp.route('/logout')
@login_required
def logout():
    """User logout with Redis session cleanup"""
    try:
        # Use new session middleware for logout
        from app.core.session.middleware.session_middleware_v2 import destroy_current_session
        
        # Destroy current session (handles both Redis and Flask session)
        session_destroyed = destroy_current_session()
        
        if session_destroyed:
            logger.info(f"Session destroyed for user {sanitize_for_log(current_user.username)}")
        
        # Log out from Flask-Login
        logout_user()
        
        send_success_notification(
            message='You have been logged out successfully.',
            title='Logged Out'
        )
        return redirect('/login')
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        # Still log out even if session cleanup fails
        logout_user()
        send_error_notification(
            message='Logout completed but there was a system error.',
            title='Logout Warning'
        )
        return redirect('/login')

@user_management_bp.route('/delete_profile', methods=['GET', 'POST'])
@login_required
def delete_profile():
    """Delete user profile"""
    form = ProfileDeleteForm(request.form)
    
    if request.method == 'POST':
        logger.info(f"Delete profile form data: {dict(request.form)}")
        logger.info(f"Form validation result: {form.validate()}")
        logger.info(f"Form errors: {form.errors}")
    
    if validate_form_submission(form):
        try:
            # Verify password before deletion
            if not current_user.check_password(form.password.data):
                send_error_notification(
                    message='Incorrect password. Profile deletion cancelled.',
                    title='Incorrect Password'
                )
                return render_template('user_management/delete_profile.html', form=form)
            
            # Store username for logging before deletion
            username = current_user.username
            user_id = current_user.id
            
            # Use request-scoped session manager for database operations
            unified_session_manager = getattr(current_app, "unified_session_manager", None)
            
            with unified_session_manager.get_db_session() as db_session:
                # Delete user profile
                user = db_session.query(User).filter_by(id=user_id).first()
                if user:
                    # Delete user record first
                    db_session.delete(user)
                    db_session.commit()
                    
                    # Clean up user sessions after deletion
                    try:
                        session_manager = getattr(current_app, 'core_session_manager', None)
                        if session_manager:
                            session_manager.cleanup_user_sessions(user_id)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup sessions during profile deletion: {e}")
                    
                    # Log out user
                    logout_user()
                    
                    logger.info(f"Profile deleted for user {sanitize_for_log(username) if username else 'unknown'}")
                    
                    # Send success notification and redirect
                    send_success_notification(
                        message='Your profile has been successfully deleted.',
                        title='Profile Deleted'
                    )
                    return redirect(url_for('auth.user_management.register'))
                else:
                    send_error_notification(
                        message='User not found.',
                        title='Profile Not Found'
                    )
                    
        except Exception as e:
            logger.error(f"Error during profile deletion: {e}")
            send_error_notification(
                message='Profile deletion failed. Please try again.',
                title='Deletion Failed'
            )
    
    return render_template('user_management/delete_profile.html', form=form)

@user_management_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    form = ProfileEditForm()
    profile_data = None
    
    try:
        # Use request-scoped session manager for database operations
        unified_session_manager = getattr(current_app, "unified_session_manager", None)
        
        with unified_session_manager.get_db_session() as db_session:
            # Fetch user profile data
            user = db_session.query(User).filter_by(id=current_user.id).first()
            if user:
                # Create profile data object
                profile_data = {
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
                    'email': user.email,
                    'email_verified': user.email_verified,
                    'role': user.role.value if user.role else 'viewer',
                    'is_active': user.is_active,
                    'created_at': user.created_at,
                    'last_login': user.last_login,
                    'data_processing_consent': getattr(user, 'data_processing_consent', False),
                    'data_processing_consent_date': getattr(user, 'data_processing_consent_date', None),
                    'platform_count': 0  # TODO: Count connected platforms
                }
                
                # Pre-populate form with current user data
                if request.method == 'GET':
                    form.first_name.data = user.first_name
                    form.last_name.data = user.last_name
                    form.email.data = user.email
                
                if validate_form_submission(form):
                    # Update user profile
                    user.first_name = form.first_name.data
                    user.last_name = form.last_name.data
                    user.email = form.email.data
                    db_session.commit()
                    
                    # Send success notification
                    from app.services.notification.helpers.notification_helpers import send_success_notification
                    send_success_notification("Profile updated successfully!", "Profile Updated")
                    logger.info(f"Profile updated for user {sanitize_for_log(user.username)}")
                    
                    # Redirect to refresh the page with updated data
                    return redirect(url_for('auth.user_management.profile'))
            else:
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification("User not found.", "Profile Error")
                logger.error(f"User not found for ID: {current_user.id}")
                
    except Exception as e:
        logger.error(f"Error loading/updating profile: {e}")
        # Send error notification
        from app.services.notification.helpers.notification_helpers import send_error_notification
        send_error_notification("Profile operation failed due to a system error.", "Profile Error")
    
    return render_template('user_management/profile.html', form=form, profile_data=profile_data)

@user_management_bp.route('/profile/export')
@login_required
@conditional_rate_limit(limit=5, window_seconds=3600)  # 5 exports per hour
def export_profile_data():
    """Export user's personal data for GDPR compliance"""
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Use request-scoped session manager for database operations
        unified_session_manager = getattr(current_app, "unified_session_manager", None)
        
        with unified_session_manager.get_db_session() as db_session:
            # Import profile service
            from app.services.user.components.user_management_service import UserProfileService
            profile_service = UserProfileService(db_session=db_session, base_url=get_base_url())
            
            # Export user data
            success, message, export_data = profile_service.export_user_data(
                user_id=current_user.id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success and export_data:
                # Create JSON response with proper headers
                import json
                from flask import Response
                
                json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
                
                response = Response(
                    json_data,
                    mimetype='application/json',
                    headers={
                        'Content-Disposition': f'attachment; filename="{current_user.username}_personal_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
                    }
                )
                
                logger.info(f"Personal data exported for user {sanitize_for_log(current_user.username)}")
                return response
            else:
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification(f'Failed to export personal data: {message}', 'Data Export Failed')
                logger.error(f"Data export failed for user {current_user.id}: {sanitize_for_log(message)}")
                return redirect(url_for('auth.user_management.profile'))
                
    except Exception as e:
        logger.error(f"Error exporting data for user {current_user.id}: {e}")
        send_error_notification(
            message='Data export failed due to a system error. Please try again.',
            title='Export Failed'
        )
        return redirect(url_for('auth.user_management.profile'))

def register_user_management_routes(app):
    """Register user management routes with the Flask app"""
    # Register the blueprint
    app.register_blueprint(user_management_bp)
    
    # Initialize email service with app
    from app.services.email.components.email_service import init_email_service
    init_email_service(app)
    
    # Store database manager in app config for route access
    if not hasattr(app.config, 'db_manager'):
        from app.core.database.core.database_manager import DatabaseManager
        from config import Config
        config = Config()
        app.config['db_manager'] = DatabaseManager(config)
    
    logger.info("User management routes registered successfully")