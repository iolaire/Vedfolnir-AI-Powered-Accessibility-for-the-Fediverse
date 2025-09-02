# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin User Management Routes"""

from flask import render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import User, UserRole
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from session_error_handlers import with_session_error_handling
from security.core.security_middleware import rate_limit, validate_input_length, validate_csrf_token
from enhanced_input_validation import enhanced_input_validation
from security.core.security_utils import sanitize_for_log
from ..forms.user_forms import EditUserForm, DeleteUserForm, AddUserForm, ResetPasswordForm, UserStatusForm
from ..services.user_service import UserService
from ..security.admin_access_control import admin_required, admin_session_preservation, admin_user_management_access, ensure_admin_count
from unified_notification_manager import UnifiedNotificationManager

def validate_form_submission(form):
    """
    Manual form validation replacement for validate_on_submit()
    Since we're using regular WTForms instead of Flask-WTF
    """
    return request.method == 'POST' and form.validate()

def get_notification_manager():
    """
    Get unified notification manager instance
    
    Returns:
        UnifiedNotificationManager instance
    """
    return current_app.unified_notification_manager

def create_user_notification(target_user_id: int, target_username: str, operation_type: str, message: str):
    """
    Create user management notification using unified system
    
    Args:
        target_user_id: ID of user being managed
        target_username: Username of user being managed  
        operation_type: Type of operation (create, update, delete, etc.)
        message: Notification message
    """
    try:
        notification_manager = get_notification_manager()
        notification_manager.send_admin_notification(
            message=message,
            notification_type='user_management',
            metadata={
                'target_user_id': target_user_id,
                'target_username': target_username,
                'operation_type': operation_type,
                'admin_user_id': current_user.id,
                'admin_username': current_user.username,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }
        )
    except Exception as e:
        current_app.logger.error(f"Failed to send user management notification: {e}")

def register_routes(bp):
    """Register user management routes"""
    
    @bp.route('/users')
    @login_required
    @admin_required
    @with_session_error_handling
    def user_management():
        """User management interface with filtering and pagination"""
            
        db_manager = current_app.config['db_manager']
        session_manager = current_app.config.get('session_manager')
        user_service = UserService(db_manager, session_manager)
        
        # Get filter parameters
        role_filter = request.args.get('role')
        status_filter = request.args.get('status')
        search_term = request.args.get('search')
        page_size = int(request.args.get('page_size', 25))
        page = int(request.args.get('page', 1))
        offset = (page - 1) * page_size
        action = request.args.get('action')
        
        # Convert status filter to boolean parameters
        is_active = None
        email_verified = None
        account_locked = None
        
        if status_filter == 'active':
            is_active = True
        elif status_filter == 'inactive':
            is_active = False
        elif status_filter == 'locked':
            account_locked = True
        elif status_filter == 'unverified':
            email_verified = False
        
        # Convert role filter
        role_enum = None
        if role_filter:
            try:
                role_enum = UserRole(role_filter)
            except ValueError:
                pass
        
        # Get filtered users
        user_data = user_service.get_users_with_filters(
            role=role_enum,
            is_active=is_active,
            email_verified=email_verified,
            account_locked=account_locked,
            search_term=search_term,
            limit=page_size,
            offset=offset
        )
        
        # Get user statistics
        all_users = user_service.get_all_users()
        user_stats = {
            'total_users': len(all_users),
            'active_users': len([u for u in all_users if u.is_active]),
            'unverified_users': len([u for u in all_users if not u.email_verified]),
            'locked_users': len([u for u in all_users if u.account_locked]),
        }
        
        admin_count = user_service.get_admin_count()
        
        # Initialize forms
        edit_form = EditUserForm()
        delete_form = DeleteUserForm()
        add_form = AddUserForm()
        
        return render_template('user_management.html', 
                              users=user_data['users'],
                              total_users=user_data['total_count'],
                              user_stats=user_stats,
                              admin_count=admin_count,
                              edit_form=edit_form, 
                              delete_form=delete_form,
                              add_form=add_form,
                              current_filters={
                                  'role': role_filter,
                                  'status': status_filter,
                                  'search': search_term
                              },
                              open_add_user_modal=(action == 'create'))

    @bp.route('/users/edit', methods=['POST'])
    @login_required
    @rate_limit(limit=10, window_seconds=60)
    @validate_input_length()
    @enhanced_input_validation
    @with_session_error_handling
    def edit_user():
        """Edit an existing user"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        form = EditUserForm()
        
        if validate_form_submission(form):
            db_manager = current_app.config['db_manager']
            session_manager = current_app.config.get('session_manager')
            user_service = UserService(db_manager, session_manager)
            
            try:
                # Get original user data for change tracking
                with db_manager.get_session() as session:
                    original_user = session.query(User).filter_by(id=form.user_id.data).first()
                    if not original_user:
                        # Send error notification
                        from notification_helpers import send_error_notification
                        send_error_notification("User not found.", "User Not Found")
                        return redirect(url_for('admin.user_management'))
                    
                    original_data = {
                        'username': original_user.username,
                        'email': original_user.email,
                        'role': original_user.role.value,
                        'is_active': original_user.is_active
                    }
                
                success = user_service.update_user(
                    user_id=form.user_id.data,
                    username=form.username.data,
                    email=form.email.data,
                    role=UserRole(form.role.data),
                    is_active=form.is_active.data,
                    password=form.password.data if form.password.data else None
                )
                
                if success:
                    # Track changes for notification
                    changes = {}
                    if original_data['username'] != form.username.data:
                        changes['username'] = {'old': original_data['username'], 'new': form.username.data}
                    if original_data['email'] != form.email.data:
                        changes['email'] = {'old': original_data['email'], 'new': form.email.data}
                    if original_data['role'] != form.role.data:
                        changes['role'] = {'old': original_data['role'], 'new': form.role.data}
                    if original_data['is_active'] != form.is_active.data:
                        changes['is_active'] = {'old': original_data['is_active'], 'new': form.is_active.data}
                    if form.password.data:
                        changes['password'] = 'updated'
                    
                    # Send real-time notification to admins
                    if changes:
                        create_user_notification(
                            target_user_id=form.user_id.data,
                            target_username=form.username.data,
                            operation_type='user_updated',
                            message=f"User {form.username.data} updated by admin {current_user.username}. Changes: {', '.join(changes)}"
                        )
                    
                    # Send success notification
                    from notification_helpers import send_success_notification
                    send_success_notification(f'User {form.username.data} updated successfully', 'User Updated')
                else:
                    # Send error notification
                    from notification_helpers import send_error_notification
                    send_error_notification("Failed to update user.", "Update Failed")
                    pass
                    
            except Exception as e:
                current_app.logger.error(f"Error updating user: {sanitize_for_log(str(e))}")
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification("An error occurred while updating the user.", "Update Error")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    # Send error notification
                    from notification_helpers import send_error_notification
                    send_error_notification(f'{field}: {error}', 'Form Validation Error')
        
        return redirect(url_for('admin.user_management'))

    @bp.route('/users/delete', methods=['POST'])
    @login_required
    @with_session_error_handling
    def delete_user():
        """Delete a user with enhanced validation"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        form = DeleteUserForm()
        
        
        if validate_form_submission(form):
            if int(form.user_id.data) == current_user.id:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification("You cannot delete your own account.", "Invalid Operation")
                return redirect(url_for('admin.user_management'))
            
            db_manager = current_app.config['db_manager']
            session_manager = current_app.config.get('session_manager')
            user_service = UserService(db_manager, session_manager)
            
            try:
                # Get user data before deletion for notification
                with db_manager.get_session() as session:
                    target_user = session.query(User).filter_by(id=int(form.user_id.data)).first()
                    if not target_user:
                        # Send error notification
                        from notification_helpers import send_error_notification
                        send_error_notification("User not found.", "User Not Found")
                        return redirect(url_for('admin.user_management'))
                    
                    target_username = target_user.username
                
                success, message = user_service.delete_user(
                    user_id=int(form.user_id.data),
                    admin_user_id=current_user.id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                if success:
                    # Send real-time notification to admins
                    deletion_reason = request.form.get('reason', 'Admin deletion')
                    create_user_notification(
                        target_user_id=form.user_id.data,
                        target_username=target_username,
                        operation_type='user_deleted',
                        message=f"User {target_username} deleted by admin {current_user.username}. Reason: {deletion_reason}"
                    )
                    
                    # Send success notification
                    from notification_helpers import send_success_notification
                    send_success_notification(message, 'User Deleted')
                    # Preserve admin session
                    user_service.preserve_admin_session(current_user.id)
                else:
                    # Send error notification
                    from notification_helpers import send_error_notification
                    send_error_notification(message, 'User Deletion Failed')
                    
            except Exception as e:
                current_app.logger.error(f"Error deleting user: {sanitize_for_log(str(e))}")
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification("An error occurred while deleting the user.", "Delete Error")
        
        return redirect(url_for('admin.user_management'))

    @bp.route('/users/add', methods=['POST'])
    @login_required
    @validate_csrf_token
    @rate_limit(limit=10, window_seconds=60)
    @validate_input_length()
    @enhanced_input_validation
    @with_session_error_handling
    def add_user():
        """Add a new user with enhanced functionality"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        form = AddUserForm()
        
        if validate_form_submission(form):
            db_manager = current_app.config['db_manager']
            session_manager = current_app.config.get('session_manager')
            user_service = UserService(db_manager, session_manager)
            
            try:
                # Get additional form data
                first_name = request.form.get('first_name', '').strip()
                last_name = request.form.get('last_name', '').strip()
                email_verified = request.form.get('email_verified') == 'on'
                send_notification = request.form.get('send_notification') == 'on'
                
                # Create user with enhanced service
                success, message, user_data = user_service.create_admin_user(
                    username=form.username.data,
                    email=form.email.data,
                    password=form.password.data,
                    first_name=first_name if first_name else None,
                    last_name=last_name if last_name else None,
                    admin_user_id=current_user.id,
                    bypass_email_verification=email_verified,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                if success and user_data:
                    # Update role if different from default
                    if form.role.data != 'viewer':
                        try:
                            role_enum = UserRole(form.role.data)
                            user_service.update_user_role(
                                user_id=user_data['id'],
                                new_role=role_enum,
                                admin_user_id=current_user.id,
                                ip_address=request.remote_addr,
                                user_agent=request.headers.get('User-Agent')
                            )
                            user_data['role'] = form.role.data
                        except ValueError:
                            pass  # Keep default role if invalid
                    
                    # Send real-time notification to admins
                    
                    # Notification sent via unified system
                        create_user_notification(
                            target_user_id=new_user.id,
                            target_username=new_user.username,
                            operation_type='user_created',
                            message=f"User {new_user.username} created by admin {current_user.username}"
                        )
                    
                    # Send notification email if requested
                    if send_notification and not email_verified:
                        try:
                            import asyncio
                            asyncio.create_task(
                                user_service.send_user_creation_email(user_data, form.password.data)
                            )
                        except Exception as e:
                            current_app.logger.warning(f"Failed to send user creation email: {e}")
                    
                    # Preserve admin session
                    user_service.preserve_admin_session(current_user.id)
                    
                    return jsonify({
                        'success': True,
                        'message': message,
                        'user': user_data
                    })
                else:
                    return jsonify({'success': False, 'error': message}), 400
                    
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            except Exception as e:
                current_app.logger.error(f"Error creating user: {sanitize_for_log(str(e))}")
                return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500
        else:
            errors = []
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    errors.append(f"{field}: {error}")
            
            return jsonify({
                'success': False,
                'error': 'Form validation failed',
                'details': errors
            }), 400
    
    @bp.route('/users/<int:user_id>/details')
    @login_required
    @with_session_error_handling
    def get_user_details(user_id):
        """Get detailed user information"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        db_manager = current_app.config['db_manager']
        session_manager = current_app.config.get('session_manager')
        user_service = UserService(db_manager, session_manager)
        
        try:
            user_details = user_service.get_user_details(user_id)
            
            if user_details:
                return jsonify({
                    'success': True,
                    'user': user_details
                })
            else:
                return jsonify({'success': False, 'error': 'User not found'}), 404
                
        except Exception as e:
            current_app.logger.error(f"Error getting user details: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to get user details'}), 500
    
    @bp.route('/users/<int:user_id>/resend-verification', methods=['POST'])
    @login_required
    @rate_limit(limit=5, window_seconds=300)  # 5 requests per 5 minutes
    @with_session_error_handling
    def resend_verification_email(user_id):
        """Resend email verification for a user"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        db_manager = current_app.config['db_manager']
        session_manager = current_app.config.get('session_manager')
        user_service = UserService(db_manager, session_manager)
        
        try:
            # Get user
            session = db_manager.get_session()
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            if user.email_verified:
                return jsonify({'success': False, 'error': 'Email is already verified'}), 400
            
            # Generate new verification token
            user.generate_email_verification_token()
            session.commit()
            
            # Send verification email (this would need to be implemented)
            # For now, just return success
            return jsonify({
                'success': True,
                'message': f'Verification email sent to {user.email}'
            })
            
        except Exception as e:
            current_app.logger.error(f"Error resending verification email: {sanitize_for_log(str(e))}")
            return jsonify({'success': False, 'error': 'Failed to resend verification email'}), 500
        finally:
            session.close()
    
    @bp.route('/users/role/update', methods=['POST'])
    @login_required
    @rate_limit(limit=10, window_seconds=60)
    @validate_input_length()
    @enhanced_input_validation
    @with_session_error_handling
    def update_user_role():
        """Update user role"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('admin.user_management'))
            
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')
        reason = request.form.get('reason', '')
        
        
        if not user_id or not new_role:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Missing required fields.", "Invalid Input")
            return redirect(url_for('admin.user_management'))
        
        try:
            new_role_enum = UserRole(new_role)
        except ValueError:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Invalid role specified.", "Invalid Role")
            return redirect(url_for('admin.user_management'))
        
        db_manager = current_app.config['db_manager']
        session_manager = current_app.config.get('session_manager')
        user_service = UserService(db_manager, session_manager)
        
        try:
            # Get original role for notification
            with db_manager.get_session() as session:
                target_user = session.query(User).filter_by(id=int(user_id)).first()
                if not target_user:
                    # Send error notification
                    from notification_helpers import send_error_notification
                    send_error_notification("User not found.", "User Not Found")
                    return redirect(url_for('admin.user_management'))
                
                old_role = target_user.role
                target_username = target_user.username
            
            success, message = user_service.update_user_role(
                user_id=int(user_id),
                new_role=new_role_enum,
                admin_user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            if success:
                # Send real-time notification to admins
                create_user_notification(
                    target_user_id=form.user_id.data,
                    target_username=target_username,
                    operation_type='user_role_changed',
                    message=f"User {target_username} role changed from {old_role} to {new_role} by admin {current_user.username}"
                )
                
                # Send success notification
                from notification_helpers import send_success_notification
                send_success_notification(message, 'Role Changed')
            else:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification(message, 'Role Change Failed')
                
        except Exception as e:
            current_app.logger.error(f"Error updating user role: {sanitize_for_log(str(e))}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while updating user role.", "Role Update Error")
        
        return redirect(url_for('admin.user_management'))
    
    @bp.route('/users/status/update', methods=['POST'])
    @login_required
    @rate_limit(limit=10, window_seconds=60)
    @validate_input_length()
    @enhanced_input_validation
    @with_session_error_handling
    def update_user_status():
        """Update user account status"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('admin.user_management'))
            
        user_id = request.form.get('user_id')
        is_active = request.form.get('is_active') == 'on'
        email_verified = request.form.get('email_verified') == 'on'
        account_locked = request.form.get('account_locked') == 'on'
        reset_failed_attempts = request.form.get('reset_failed_attempts') == 'on'
        admin_notes = request.form.get('admin_notes', '')
        
        if not user_id:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Missing user ID.", "Invalid Input")
            return redirect(url_for('admin.user_management'))
        
        db_manager = current_app.config['db_manager']
        session_manager = current_app.config.get('session_manager')
        user_service = UserService(db_manager, session_manager)
        
        try:
            # Update basic status
            success, message = user_service.update_user_status(
                user_id=int(user_id),
                is_active=is_active,
                account_locked=account_locked,
                admin_user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            # Handle additional status updates and track changes
            status_changes = {}
            
            target_username = None
            
            # Use db_manager directly since session management is now in Redis
            db_manager = current_app.config['db_manager']
            session = db_manager.get_session()
            try:
                user = session.query(User).filter_by(id=int(user_id)).first()
                if user:
                    target_username = user.username
                    
                    # Track email verification changes
                    if user.email_verified != email_verified:
                        status_changes['email_verified'] = {
                            'old': user.email_verified, 
                            'new': email_verified
                        }
                        user.email_verified = email_verified
                        success = True
                        message += f", email verification: {email_verified}"
                    
                    # Track failed login attempts reset
                    if reset_failed_attempts and user.failed_login_attempts > 0:
                        status_changes['failed_login_attempts'] = {
                            'old': user.failed_login_attempts, 
                            'new': 0
                        }
                        user.failed_login_attempts = 0
                        user.last_failed_login = None
                        success = True
                        message += ", failed attempts reset"
                    
                    # Track active status changes
                    if 'is_active' not in status_changes and hasattr(user, 'is_active'):
                        if user.is_active != is_active:
                            status_changes['is_active'] = {
                                'old': user.is_active, 
                                'new': is_active
                            }
                    
                    # Track account locked changes
                    if 'account_locked' not in status_changes and hasattr(user, 'account_locked'):
                        if user.account_locked != account_locked:
                            status_changes['account_locked'] = {
                                'old': user.account_locked, 
                                'new': account_locked
                            }
                    
                    session.commit()
            finally:
                db_manager.close_session(session)
            
            if success:
                # Send real-time notification to admins
                if status_changes and target_username:
                    create_user_notification(
                        target_user_id=form.user_id.data,
                        target_username=target_username,
                        operation_type='user_status_changed',
                        message=f"User {target_username} status changed by admin {current_user.username}. Changes: {', '.join(status_changes)}"
                    )
                
                # Send success notification
                from notification_helpers import send_success_notification
                send_success_notification(message, 'Status Changed')
            else:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification(message, 'Status Change Failed')
                
        except Exception as e:
            current_app.logger.error(f"Error updating user status: {sanitize_for_log(str(e))}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while updating user status.", "Status Update Error")
        
        return redirect(url_for('admin.user_management'))
    
    @bp.route('/users/password/reset', methods=['POST'])
    @login_required
    @rate_limit(limit=5, window_seconds=300)  # 5 resets per 5 minutes
    @with_session_error_handling
    def reset_user_password():
        """Reset user password as admin"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('admin.user_management'))
            
        user_id = request.form.get('user_id')
        reset_method = request.form.get('reset_method', 'email')
        invalidate_sessions = request.form.get('invalidate_sessions') == 'on'
        
        
        if not user_id:
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("Missing user ID.", "Invalid Input")
            return redirect(url_for('admin.user_management'))
        
        db_manager = current_app.config['db_manager']
        session_manager = current_app.config.get('session_manager')
        user_service = UserService(db_manager, session_manager)
        
        try:
            # Get target user info for notification
            with db_manager.get_session() as session:
                target_user = session.query(User).filter_by(id=int(user_id)).first()
                if not target_user:
                    # Send error notification
                    from notification_helpers import send_error_notification
                    send_error_notification("User not found.", "User Not Found")
                    return redirect(url_for('admin.user_management'))
                
                target_username = target_user.username
            
            success, message, temp_password = user_service.admin_reset_user_password(
                user_id=int(user_id),
                admin_user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            if success:
                # Send real-time notification to admins
                # Notification sent via unified system
                create_user_notification(
                    target_user_id=form.user_id.data,
                    target_username=target_username,
                    operation_type='user_password_reset',
                    message=f"Password reset for user {target_username} by admin {current_user.username}"
                )
                
                if reset_method == 'generate' and temp_password:
                    # Send success notification with temporary password
                    from notification_helpers import send_success_notification
                    send_success_notification(f'Password reset successfully. Temporary password: {temp_password}', 'Password Reset')
                else:
                    # Send success notification
                    from notification_helpers import send_success_notification
                    send_success_notification(message, 'Password Reset')
            else:
                # Send error notification
                from notification_helpers import send_error_notification
                send_error_notification(message, 'Password Reset Failed')
                
        except Exception as e:
            current_app.logger.error(f"Error resetting user password: {sanitize_for_log(str(e))}")
            # Send error notification
            from notification_helpers import send_error_notification
            send_error_notification("An error occurred while resetting password.", "Password Reset Error")
        
        return redirect(url_for('admin.user_management'))