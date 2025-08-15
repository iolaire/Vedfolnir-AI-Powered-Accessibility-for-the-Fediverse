# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin User Management Routes"""

from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import User, UserRole
from session_error_handlers import with_session_error_handling
from security.core.security_middleware import rate_limit, validate_input_length, validate_csrf_token
from enhanced_input_validation import enhanced_input_validation
from security.core.security_utils import sanitize_for_log
from ..forms.user_forms import EditUserForm, DeleteUserForm, AddUserForm
from ..services.user_service import UserService

def register_routes(bp):
    """Register user management routes"""
    
    @bp.route('/users')
    @login_required
    @with_session_error_handling
    def user_management():
        """User management interface"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
            
        db_manager = current_app.config['db_manager']
        user_service = UserService(db_manager)
        
        users = user_service.get_all_users()
        admin_count = user_service.get_admin_count()
        
        edit_form = EditUserForm()
        delete_form = DeleteUserForm()
        
        return render_template('user_management.html', 
                              users=users, 
                              admin_count=admin_count,
                              edit_form=edit_form, 
                              delete_form=delete_form)

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
        if form.validate_on_submit():
            db_manager = current_app.config['db_manager']
            user_service = UserService(db_manager)
            
            try:
                success = user_service.update_user(
                    user_id=form.user_id.data,
                    username=form.username.data,
                    email=form.email.data,
                    role=UserRole(form.role.data),
                    is_active=form.is_active.data,
                    password=form.password.data if form.password.data else None
                )
                
                if success:
                    flash(f'User {form.username.data} updated successfully', 'success')
                else:
                    flash('Failed to update user', 'error')
                    
            except Exception as e:
                current_app.logger.error(f"Error updating user: {sanitize_for_log(str(e))}")
                flash('An error occurred while updating the user', 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')
        
        return redirect(url_for('admin.user_management'))

    @bp.route('/users/delete', methods=['POST'])
    @login_required
    @with_session_error_handling
    def delete_user():
        """Delete a user"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        form = DeleteUserForm()
        if form.validate_on_submit():
            if int(form.user_id.data) == current_user.id:
                flash('You cannot delete your own account', 'error')
                return redirect(url_for('admin.user_management'))
            
            db_manager = current_app.config['db_manager']
            user_service = UserService(db_manager)
            
            try:
                success = user_service.delete_user(form.user_id.data)
                if success:
                    flash('User deleted successfully', 'success')
                else:
                    flash('User not found', 'error')
            except Exception as e:
                current_app.logger.error(f"Error deleting user: {sanitize_for_log(str(e))}")
                flash('An error occurred while deleting the user', 'error')
        
        return redirect(url_for('admin.user_management'))

    @bp.route('/users/add', methods=['POST'])
    @login_required
    @validate_csrf_token
    @rate_limit(limit=10, window_seconds=60)
    @validate_input_length()
    @enhanced_input_validation
    @with_session_error_handling
    def add_user():
        """Add a new user"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
            
        form = AddUserForm()
        if form.validate_on_submit():
            db_manager = current_app.config['db_manager']
            user_service = UserService(db_manager)
            
            try:
                user = user_service.create_user(
                    username=form.username.data,
                    email=form.email.data,
                    password=form.password.data,
                    role=UserRole(form.role.data),
                    is_active=form.is_active.data
                )
                
                if user:
                    current_app.logger.info(f"Admin {sanitize_for_log(current_user.username)} created new user {sanitize_for_log(form.username.data)}")
                    return jsonify({
                        'success': True,
                        'message': f'User {form.username.data} created successfully',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'role': user.role.value,
                            'is_active': user.is_active
                        }
                    })
                else:
                    return jsonify({'success': False, 'error': 'Failed to create user'}), 400
                    
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