# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin User Management Forms"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from models import UserRole

class EditUserForm(FlaskForm):
    """Form for editing an existing user"""
    user_id = HiddenField('User ID')
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password')
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[EqualTo('password', message='Passwords must match')])
    role = SelectField('Role', choices=[(role.value, role.value.capitalize()) for role in UserRole])
    is_active = BooleanField('Active')
    submit = SubmitField('Save Changes')

class DeleteUserForm(FlaskForm):
    """Form for deleting a user"""
    user_id = HiddenField('User ID', validators=[DataRequired()])
    submit = SubmitField('Delete User')

class AddUserForm(FlaskForm):
    """Form for adding a new user"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    role = SelectField('Role', choices=[(role.value, role.value.capitalize()) for role in UserRole], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Add User')