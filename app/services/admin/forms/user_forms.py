# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin User Management Forms"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, HiddenField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from models import UserRole

class EditUserForm(FlaskForm):
    """Form for editing an existing user"""
    user_id = HiddenField('User ID', render_kw={'id': 'edit_user_id'})
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[Length(max=100)])
    last_name = StringField('Last Name', validators=[Length(max=100)])
    password = PasswordField('Password', render_kw={'autocomplete': 'new-password'})
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[EqualTo('password', message='Passwords must match')],
                                    render_kw={'autocomplete': 'new-password'})
    role = SelectField('Role', choices=[(role.value, role.value.capitalize()) for role in UserRole])
    is_active = BooleanField('Active')
    email_verified = BooleanField('Email Verified')
    account_locked = BooleanField('Account Locked')
    submit = SubmitField('Save Changes')

class DeleteUserForm(FlaskForm):
    """Form for deleting a user"""
    user_id = HiddenField('User ID', validators=[DataRequired()], render_kw={'id': 'delete_user_id'})
    submit = SubmitField('Delete User')

class AddUserForm(FlaskForm):
    """Form for adding a new user"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField('First Name', validators=[Length(max=100)])
    last_name = StringField('Last Name', validators=[Length(max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)], 
                            render_kw={'autocomplete': 'new-password'})
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password', message='Passwords must match')],
                                    render_kw={'autocomplete': 'new-password'})
    role = SelectField('Role', choices=[(role.value, role.value.capitalize()) for role in UserRole], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    email_verified = BooleanField('Email Verified', default=True)
    send_notification = BooleanField('Send Welcome Email', default=True)
    submit = SubmitField('Add User')

class ResetPasswordForm(FlaskForm):
    """Form for admin password reset"""
    user_id = HiddenField('User ID', validators=[DataRequired()], render_kw={'id': 'reset_password_user_id'})
    reset_method = SelectField('Reset Method', 
                              choices=[('email', 'Send temporary password via email'),
                                     ('generate', 'Generate and display temporary password')],
                              default='email')
    invalidate_sessions = BooleanField('Invalidate all existing user sessions', default=True)
    submit = SubmitField('Reset Password')

class UserStatusForm(FlaskForm):
    """Form for managing user status"""
    user_id = HiddenField('User ID', validators=[DataRequired()], render_kw={'id': 'status_form_user_id'})
    is_active = BooleanField('Account Active')
    email_verified = BooleanField('Email Verified')
    account_locked = BooleanField('Account Locked')
    reset_failed_attempts = BooleanField('Reset failed login attempts')
    send_verification_email = BooleanField('Send new email verification')
    admin_notes = TextAreaField('Admin Notes', validators=[Length(max=500)])
    submit = SubmitField('Update Status')

class RoleAssignmentForm(FlaskForm):
    """Form for changing user roles"""
    user_id = HiddenField('User ID', validators=[DataRequired()], render_kw={'id': 'role_form_user_id'})
    new_role = SelectField('New Role', 
                          choices=[(role.value, f"{role.value.capitalize()} - {role.name}") for role in UserRole],
                          validators=[DataRequired()])
    reason = TextAreaField('Reason for role change', validators=[Length(max=500)])
    submit = SubmitField('Change Role')