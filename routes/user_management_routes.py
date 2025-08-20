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
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.orm import joinedload

def validate_form_submission(form):
    """
    Manual form validation replacement for validate_on_submit()
    Since we're using regular WTForms instead of Flask-WTF
    """
    return request.method == 'POST' and form.validate()

from forms.user_management_forms import (
    UserRegistrationForm, LoginForm, ProfileEditForm, PasswordChangeForm,
    PasswordResetRequestForm, PasswordResetForm, ProfileDeleteForm,
    EmailVerificationResendForm
)
from services.user_management_service import UserRegistrationService, UserAuthenticationService
from services.email_service import email_service
from models import User, UserRole, UserAuditLog
from security_decorators import conditional_rate_limit, conditional_validate_input_length
from security.core.security_utils import sanitize_for_log
from security.core.enhanced_rate_limiter import rate_limit_user_management
# from security.core.enhanced_csrf_protection import csrf_protect_user_management, csrf_protect_admin_operation
from security_decorators import conditional_validate_csrf_token
from security.validation.enhanced_input_validator import (
    validate_user_input, USER_REGISTRATION_RULES, USER_LOGIN_RULES, 
    PROFILE_UPDATE_RULES, PASSWORD_CHANGE_RULES, ADMIN_USER_CREATE_RULES
)
from security.monitoring.security_event_logger import get_security_event_logger
from security.error_handling.user_management_error_handler import (
    UserManagementErrorHandler, handle_user_management_errors, graceful_degradation,
    UserManagementError, ValidationError, AuthenticationError, DatabaseError
)
from security.error_handling.system_recovery import with_recovery, SystemRecoveryManager
from request_scoped_session_manager import RequestScopedSessionManager

logger = logging.getLogger(__name__)

# Create blueprint for user management routes
user_management_bp = Blueprint('user_management', __name__)


def get_client_ip():
    """Get client IP address from request"""
    try:
        # Check for forwarded IP first (behind proxy)
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
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
        return redirect(url_for('index'))
    
    form = UserRegistrationForm()
    
    if form.validate_on_submit():
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
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
                    # Send verification email asynchronously
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        email_sent, email_message = loop.run_until_complete(
                            registration_service.send_verification_email(user)
                        )
                        loop.close()
                        
                        if email_sent:
                            flash(
                                f'Registration successful! Please check your email ({user.email}) '
                                f'for a verification link to activate your account.',
                                'success'
                            )
                            logger.info(f"User {sanitize_for_log(user.username)} registered successfully")
                        else:
                            flash(
                                'Registration successful, but there was an issue sending the verification email. '
                                'Please contact support for assistance.',
                                'warning'
                            )
                            logger.warning(f"Registration successful but email failed for {sanitize_for_log(user.username)}: {email_message}")
                        
                        return redirect(url_for('user_management.login'))
                        
                    except Exception as e:
                        logger.error(f"Error sending verification email: {e}")
                        flash(
                            'Registration successful, but there was an issue sending the verification email. '
                            'Please contact support for assistance.',
                            'warning'
                        )
                        return redirect(url_for('user_management.login'))
                else:
                    flash(f'Registration failed: {message}', 'error')
                    logger.warning(f"Registration failed: {sanitize_for_log(message)}")
                    
        except Exception as e:
            logger.error(f"Error during registration: {e}")
            flash('Registration failed due to a system error. Please try again.', 'error')
    
    return render_template('user_management/register.html', form=form)


@user_management_bp.route('/verify-email/<token>')
@conditional_rate_limit(limit=10, window_seconds=3600)  # 10 verification attempts per hour per IP
def verify_email(token):
    """Email verification endpoint"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('index'))
    
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Use request-scoped session manager for database operations
        request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
        
        with request_session_manager.session_scope() as db_session:
            # Initialize registration service
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url=get_base_url()
            )
            
            # Verify email token
            success, message, user = registration_service.verify_email(
                token=token,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success and user:
                flash(
                    f'Email verification successful! Your account is now active. '
                    f'You can now log in with your username and password.',
                    'success'
                )
                logger.info(f"Email verified successfully for user {sanitize_for_log(user.username)}")
                return redirect(url_for('user_management.login'))
            else:
                flash(f'Email verification failed: {message}', 'error')
                logger.warning(f"Email verification failed: {sanitize_for_log(message)}")
                return redirect(url_for('user_management.login'))
                
    except Exception as e:
        logger.error(f"Error during email verification: {e}")
        flash('Email verification failed due to a system error. Please try again.', 'error')
        return redirect(url_for('user_management.login'))


@user_management_bp.route('/resend-verification', methods=['POST'])
@login_required
@conditional_rate_limit(limit=3, window_seconds=300)  # 3 resends per 5 minutes per user
def resend_verification():
    """Resend email verification"""
    if current_user.email_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('index'))
    
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Use request-scoped session manager for database operations
        request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
        
        with request_session_manager.session_scope() as db_session:
            # Initialize registration service
            registration_service = UserRegistrationService(
                db_session=db_session,
                base_url=get_base_url()
            )
            
            # Resend verification email
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(
                registration_service.resend_verification_email(
                    user_id=current_user.id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            )
            loop.close()
            
            if success:
                flash('Verification email sent! Please check your email.', 'success')
                logger.info(f"Verification email resent for user {sanitize_for_log(current_user.username)}")
            else:
                flash(f'Failed to send verification email: {message}', 'error')
                logger.warning(f"Failed to resend verification email: {sanitize_for_log(message)}")
                
    except Exception as e:
        logger.error(f"Error resending verification email: {e}")
        flash('Failed to send verification email due to a system error.', 'error')
    
    return redirect(url_for('index'))


@user_management_bp.route('/login', methods=['GET', 'POST'])
@rate_limit_user_management('login')
@conditional_validate_csrf_token
@validate_user_input(USER_LOGIN_RULES)
@handle_user_management_errors
@with_recovery('database_connection', max_retries=2)
def login():
    """Enhanced user login with email verification check and account lockout handling"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm(request.form if request.method == 'POST' else None)
    
    if validate_form_submission(form):
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                # Initialize authentication service with session manager integration
                session_manager = getattr(current_app, 'unified_session_manager', None)
                auth_service = UserAuthenticationService(
                    db_session=db_session,
                    session_manager=session_manager
                )
                
                # Get security event logger
                security_logger = get_security_event_logger(db_session)
                
                # Authenticate user with enhanced security
                success, message, user = auth_service.authenticate_user(
                    username_or_email=form.username_or_email.data,
                    password=form.password.data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Log authentication event
                security_logger.log_authentication_event(
                    success=success,
                    username_or_email=form.username_or_email.data,
                    user_id=user.id if user else None,
                    failure_reason=message if not success else None,
                    blocked='account_locked' in message.lower() if message else False
                )
                
                if success and user:
                    # Load user relationships to prevent DetachedInstanceError
                    user = db_session.query(User).options(
                        joinedload(User.platform_connections),
                        joinedload(User.sessions)
                    ).filter_by(id=user.id).first()
                    
                    # Store user info before login_user() call
                    user_id = user.id
                    username = user.username
                    user_role = user.role
                    
                    # Create secure Redis session using enhanced authentication service
                    try:
                        session_success, session_message, session_id = auth_service.login_user_with_session(
                            user=user,
                            remember=form.remember_me.data,
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
                        
                        if session_success and session_id:
                            # Log in the user with Flask-Login (this will use our custom user loader)
                            login_user(user, remember=form.remember_me.data)
                            
                            # Ensure Flask session is marked as modified to trigger save
                            from flask import session as flask_session
                            flask_session.permanent = True
                            flask_session.modified = True
                            
                            # Debug: Check what Flask-Login stored in session
                            current_app.logger.info(f"Flask session after login_user: {dict(flask_session)}")
                            
                            # Flask Redis session interface handles session cookies automatically
                            response = make_response(redirect(
                                request.args.get('next') if request.args.get('next') and request.args.get('next').startswith('/') 
                                else url_for('index')
                            ))
                            
                            # Success message
                            flash(f'Welcome back, {username}!', 'success')
                            logger.info(f"User {sanitize_for_log(username)} logged in successfully with Redis session {session_id}")
                            
                            return response
                        else:
                            # Session creation failed
                            flash('Login failed due to session security error. Please try again.', 'error')
                            logger.error(f"Failed to create Redis session for user {sanitize_for_log(username)}: {session_message}")
                    
                    except Exception as e:
                        # Session creation failed
                        logger.error(f"Error creating Redis session: {e}")
                        flash('Login failed due to session error. Please try again.', 'error')
                
                else:
                    # Authentication failed - provide appropriate feedback
                    flash(message, 'error')
                    
                    # Special handling for different failure types
                    if 'not verified' in message.lower():
                        # Try to find the user to offer resend option
                        user = db_session.query(User).filter(
                            (User.username == form.username_or_email.data) | 
                            (User.email == form.username_or_email.data)
                        ).first()
                        
                        if user and not user.email_verified:
                            flash(
                                'Your email address has not been verified. '
                                'Please check your email for a verification link, or contact support.',
                                'warning'
                            )
                    
                    elif 'locked' in message.lower():
                        # Account is locked - provide appropriate guidance
                        if 'temporarily' in message.lower():
                            flash(
                                'Your account is temporarily locked due to too many failed login attempts. '
                                'Please wait and try again later, or contact support if you need immediate assistance.',
                                'warning'
                            )
                        else:
                            flash(
                                'Your account has been locked. Please contact support for assistance.',
                                'warning'
                            )
                    
                    elif 'deactivated' in message.lower():
                        flash(
                            'Your account has been deactivated. Please contact support for assistance.',
                            'warning'
                        )
                    
                    elif 'attempts remaining' in message.lower():
                        # Show remaining attempts warning
                        flash(
                            f'{message} Your account will be temporarily locked if you exceed the maximum attempts.',
                            'warning'
                        )
                    
        except Exception as e:
            logger.error(f"Error during login: {e}")
            flash('Login failed due to a system error. Please try again.', 'error')
    
    return render_template('user_management/login.html', form=form)


@user_management_bp.route('/forgot-password', methods=['GET', 'POST'])
@rate_limit_user_management('password_reset')
@conditional_validate_csrf_token
@validate_user_input({'email': {'type': 'email', 'required': True}})
def forgot_password():
    """Password reset request with enhanced security"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = PasswordResetRequestForm()
    
    if form.validate_on_submit():
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                # Initialize password management service
                from services.user_management_service import PasswordManagementService
                password_service = PasswordManagementService(
                    db_session=db_session,
                    base_url=get_base_url()
                )
                
                # Initiate password reset
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success, message = loop.run_until_complete(
                    password_service.initiate_password_reset(
                        email=form.email.data,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                )
                loop.close()
                
                if success:
                    flash(message, 'success')
                    logger.info(f"Password reset initiated for email {sanitize_for_log(form.email.data)}")
                else:
                    flash(message, 'error')
                    logger.warning(f"Password reset failed for email {sanitize_for_log(form.email.data)}: {message}")
                
                # Always redirect to login page regardless of success/failure for security
                return redirect(url_for('user_management.login'))
                
        except Exception as e:
            logger.error(f"Error during password reset request: {e}")
            flash('Password reset request failed due to a system error. Please try again.', 'error')
    
    return render_template('user_management/forgot_password.html', form=form)


@user_management_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@conditional_rate_limit(limit=5, window_seconds=3600)  # 5 attempts per hour per IP
@conditional_validate_input_length()
def reset_password(token):
    """Password reset completion with token validation"""
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Use request-scoped session manager for database operations
        request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
        
        with request_session_manager.session_scope() as db_session:
            # Initialize password management service
            from services.user_management_service import PasswordManagementService
            password_service = PasswordManagementService(
                db_session=db_session,
                base_url=get_base_url()
            )
            
            # Verify token first
            token_valid, token_message, user = password_service.verify_reset_token(token)
            
            if not token_valid:
                flash(f'Password reset failed: {token_message}', 'error')
                logger.warning(f"Invalid password reset token attempted: {token[:10]}...")
                return redirect(url_for('user_management.forgot_password'))
            
            # Token is valid, show reset form
            form = PasswordResetForm()
            
            if form.validate_on_submit():
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
                        session_manager = getattr(current_app, 'unified_session_manager', None)
                        if session_manager:
                            session_manager.cleanup_user_sessions(reset_user.id)
                            logger.info(f"Invalidated all sessions for user {sanitize_for_log(reset_user.username)} after password reset")
                    except Exception as e:
                        logger.warning(f"Failed to invalidate sessions after password reset: {e}")
                    
                    flash(
                        'Password reset successful! You can now log in with your new password. All other sessions have been logged out for security.',
                        'success'
                    )
                    logger.info(f"Password reset completed for user {sanitize_for_log(reset_user.username)}")
                    return redirect(url_for('user_management.login'))
                else:
                    flash(f'Password reset failed: {reset_message}', 'error')
                    logger.error(f"Password reset failed for token {token[:10]}...: {reset_message}")
            
            return render_template('user_management/reset_password.html', form=form, token=token)
            
    except Exception as e:
        logger.error(f"Error during password reset: {e}")
        flash('Password reset failed due to a system error. Please try again.', 'error')
        return redirect(url_for('user_management.forgot_password'))


@user_management_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@conditional_rate_limit(limit=5, window_seconds=3600)  # 5 attempts per hour per user
@conditional_validate_input_length()
def change_password():
    """Password change for authenticated users"""
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        # Get client information for audit logging
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        try:
            # Use request-scoped session manager for database operations
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                # Initialize password management service
                from services.user_management_service import PasswordManagementService
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
                    flash('Password changed successfully!', 'success')
                    logger.info(f"Password changed for user {sanitize_for_log(current_user.username)}")
                    
                    # Invalidate all other sessions for security
                    try:
                        session_manager = getattr(current_app, 'unified_session_manager', None)
                        if session_manager:
                            # Get current session ID from Redis session
                            from session_middleware_v2 import get_current_session_id
                            current_session_id = get_current_session_id()
                            session_manager.cleanup_user_sessions(current_user.id, keep_current=current_session_id)
                            logger.info(f"Invalidated other sessions for user {sanitize_for_log(current_user.username)} after password change")
                    except Exception as e:
                        logger.warning(f"Failed to invalidate other sessions after password change: {e}")
                    
                    return redirect(url_for('index'))
                else:
                    flash(message, 'error')
                    logger.warning(f"Password change failed for user {sanitize_for_log(current_user.username)}: {message}")
                    
        except Exception as e:
            logger.error(f"Error during password change: {e}")
            flash('Password change failed due to a system error. Please try again.', 'error')
    
    return render_template('user_management/change_password.html', form=form)


@user_management_bp.route('/logout')
@login_required
def logout():
    """User logout with Redis session cleanup"""
    try:
        # Use new session middleware for logout
        from session_middleware_v2 import destroy_current_session
        
        # Destroy current session (handles both Redis and Flask session)
        session_destroyed = destroy_current_session()
        
        if session_destroyed:
            logger.info(f"Session destroyed for user {sanitize_for_log(current_user.username)}")
        
        # Log out from Flask-Login
        logout_user()
        
        flash('You have been logged out successfully.', 'info')
        return redirect(url_for('user_management.login'))
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        # Still log out even if session cleanup fails
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('user_management.login'))


@user_management_bp.route('/profile')
@login_required
def profile():
    """Display user profile"""
    try:
        # Use request-scoped session manager for database operations
        request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
        
        with request_session_manager.session_scope() as db_session:
            # Import profile service
            from services.user_management_service import UserProfileService
            profile_service = UserProfileService(db_session=db_session, base_url=get_base_url())
            
            # Get profile data
            success, message, profile_data = profile_service.get_profile_data(current_user.id)
            
            if success and profile_data:
                return render_template('user_management/profile.html', profile_data=profile_data)
            else:
                flash(f'Failed to load profile: {message}', 'error')
                return redirect(url_for('index'))
                
    except Exception as e:
        logger.error(f"Error loading profile for user {current_user.id}: {e}")
        flash('Failed to load profile due to a system error.', 'error')
        return redirect(url_for('index'))


@user_management_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@rate_limit_user_management('profile_update')
@conditional_validate_csrf_token
@validate_user_input(PROFILE_UPDATE_RULES)
def edit_profile():
    """Edit user profile"""
    form = ProfileEditForm()
    
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        # Use request-scoped session manager for database operations
        request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
        
        with request_session_manager.session_scope() as db_session:
            # Import profile service
            from services.user_management_service import UserProfileService
            profile_service = UserProfileService(db_session=db_session, base_url=get_base_url())
            
            if request.method == 'GET':
                # Pre-populate form with current user data
                success, message, profile_data = profile_service.get_profile_data(current_user.id)
                
                if success and profile_data:
                    form.first_name.data = profile_data.get('first_name', '')
                    form.last_name.data = profile_data.get('last_name', '')
                    form.email.data = profile_data.get('email', '')
                else:
                    flash(f'Failed to load profile data: {message}', 'error')
                    return redirect(url_for('user_management.profile'))
            
            elif form.validate_on_submit():
                # Update profile
                profile_data = {
                    'first_name': form.first_name.data,
                    'last_name': form.last_name.data,
                    'email': form.email.data
                }
                
                success, message, updated_data = profile_service.update_profile(
                    user_id=current_user.id,
                    profile_data=profile_data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    if updated_data and updated_data.get('email_changed'):
                        flash(
                            'Profile updated successfully! Your email address has been changed and requires re-verification. '
                            'Please check your new email for a verification link.',
                            'success'
                        )
                        # Log out user if email changed to force re-verification
                        logout_user()
                        response = make_response(redirect(url_for('user_management.login')))
                        # Flask Redis session interface handles session cleanup automatically
                        return response
                    else:
                        flash('Profile updated successfully!', 'success')
                        logger.info(f"Profile updated for user {sanitize_for_log(current_user.username)}")
                    
                    return redirect(url_for('user_management.profile'))
                else:
                    flash(f'Failed to update profile: {message}', 'error')
                    logger.warning(f"Profile update failed for user {current_user.id}: {sanitize_for_log(message)}")
                    
    except Exception as e:
        logger.error(f"Error updating profile for user {current_user.id}: {e}")
        flash('Failed to update profile due to a system error.', 'error')
    
    return render_template('user_management/edit_profile.html', form=form)


@user_management_bp.route('/profile/delete', methods=['GET', 'POST'])
@login_required
@conditional_rate_limit(limit=3, window_seconds=3600)  # 3 deletion attempts per hour
@conditional_validate_input_length()
def delete_profile():
    """Delete user profile with GDPR compliance"""
    form = ProfileDeleteForm()
    
    # Get client information for audit logging
    ip_address = get_client_ip()
    user_agent = get_user_agent()
    
    if form.validate_on_submit():
        try:
            # Use request-scoped session manager for database operations
            request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
            
            with request_session_manager.session_scope() as db_session:
                # Verify current password
                from services.user_management_service import UserAuthenticationService
                auth_service = UserAuthenticationService(db_session=db_session)
                
                # Get current user from database
                user = db_session.query(User).filter_by(id=current_user.id).first()
                if not user or not user.check_password(form.password.data):
                    flash('Incorrect password. Profile deletion cancelled.', 'error')
                    return render_template('user_management/delete_profile.html', form=form)
                
                # Import deletion service
                from services.user_management_service import UserDeletionService
                deletion_service = UserDeletionService(db_session=db_session)
                
                # Validate deletion request
                can_delete, validation_message = deletion_service.validate_deletion_request(
                    user_id=current_user.id,
                    requesting_user_id=current_user.id
                )
                
                if not can_delete:
                    flash(f'Profile deletion not allowed: {validation_message}', 'error')
                    return render_template('user_management/delete_profile.html', form=form)
                
                # Store user info before deletion
                username = user.username
                user_id = user.id
                
                # Delete user profile
                success, message, deletion_summary = deletion_service.delete_user_profile(
                    user_id=user_id,
                    admin_user_id=None,  # Self-deletion
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    # Log out user immediately
                    logout_user()
                    response = make_response(redirect(url_for('user_management.login')))
                    # Flask Redis session interface handles session cleanup automatically
                    
                    flash(
                        f'Your profile has been completely deleted. All your data has been removed from the system. '
                        f'Thank you for using our service.',
                        'success'
                    )
                    logger.info(f"User profile deleted: {sanitize_for_log(username)} (ID: {user_id})")
                    return response
                else:
                    flash(f'Profile deletion failed: {message}', 'error')
                    logger.error(f"Profile deletion failed for user {user_id}: {sanitize_for_log(message)}")
                    
        except Exception as e:
            logger.error(f"Error deleting profile for user {current_user.id}: {e}")
            flash('Profile deletion failed due to a system error. Please try again or contact support.', 'error')
    
    return render_template('user_management/delete_profile.html', form=form)


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
        request_session_manager = RequestScopedSessionManager(current_app.config['db_manager'])
        
        with request_session_manager.session_scope() as db_session:
            # Import profile service
            from services.user_management_service import UserProfileService
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
                flash(f'Failed to export personal data: {message}', 'error')
                logger.error(f"Data export failed for user {current_user.id}: {sanitize_for_log(message)}")
                return redirect(url_for('user_management.profile'))
                
    except Exception as e:
        logger.error(f"Error exporting data for user {current_user.id}: {e}")
        flash('Data export failed due to a system error.', 'error')
        return redirect(url_for('user_management.profile'))





def register_user_management_routes(app):
    """Register user management routes with the Flask app"""
    # Register the blueprint
    app.register_blueprint(user_management_bp)
    
    # Initialize email service with app
    from services.email_service import init_email_service
    init_email_service(app)
    
    # Store database manager in app config for route access
    if not hasattr(app.config, 'db_manager'):
        from database import DatabaseManager
        from config import Config
        config = Config()
        app.config['db_manager'] = DatabaseManager(config)
    
    logger.info("User management routes registered successfully")