# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Management Forms

This module contains all forms related to user management including registration,
login, profile management, and password reset functionality.
"""

from flask_wtf import FlaskForm
# Import regular WTForms Form class (no Flask-WTF CSRF)
from wtforms import Form, StringField, PasswordField, BooleanField, SelectField, HiddenField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError
from models import UserRole, User
from email_validator import validate_email, EmailNotValidError

class UserRegistrationForm(Form):
    """Form for user self-registration""" # Using regular WTForms (no Flask-WTF CSRF)
    
    username = StringField(
        'Username', 
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=64, message="Username must be between 3 and 64 characters")
        ],
        render_kw={
            "placeholder": "Enter your username",
            "class": "form-control",
            "autocomplete": "username"
        }
    )
    
    email = StringField(
        'Email Address', 
        validators=[
            DataRequired(message="Email address is required"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email address must be no more than 120 characters")
        ],
        render_kw={
            "placeholder": "Enter your email address",
            "class": "form-control",
            "type": "email",
            "autocomplete": "email"
        }
    )
    
    first_name = StringField(
        'First Name',
        validators=[
            Optional(),
            Length(max=100, message="First name must be no more than 100 characters")
        ],
        render_kw={
            "placeholder": "Enter your first name (optional)",
            "class": "form-control",
            "autocomplete": "given-name"
        }
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            Optional(),
            Length(max=100, message="Last name must be no more than 100 characters")
        ],
        render_kw={
            "placeholder": "Enter your last name (optional)",
            "class": "form-control",
            "autocomplete": "family-name"
        }
    )
    
    password = PasswordField(
        'Password', 
        validators=[
            DataRequired(message="Password is required"),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters")
        ],
        render_kw={
            "placeholder": "Enter your password",
            "class": "form-control",
            "autocomplete": "new-password"
        }
    )
    
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo('password', message='Passwords must match')
        ],
        render_kw={
            "placeholder": "Confirm your password",
            "class": "form-control",
            "autocomplete": "new-password"
        }
    )
    
    data_processing_consent = BooleanField(
        'I consent to the processing of my personal data',
        validators=[DataRequired(message="You must consent to data processing to register")],
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Register',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_username(self, field):
        """Custom username validation"""
        username = field.data
        
        if not username.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("Username can only contain letters, numbers, hyphens, and underscores")
        
        # Check if username is already taken (this will be done in the service layer too)
        # We do a basic check here for immediate feedback
        from database import DatabaseManager
        from config import Config
        
        try:
            config = Config()
            db_manager = DatabaseManager(config)
            with db_manager.get_session() as session:
                existing_user = session.query(User).filter_by(username=username).first()
                if existing_user:
                    raise ValidationError("Username is already taken")
        except Exception:
            # If we can't check, let the service layer handle it
            pass
    
    def validate_email(self, field):
        """Custom email validation"""
        email = field.data
        
        # Use email_validator for thorough validation
        try:
            validate_email(email)
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email address: {str(e)}")
        
        # Check if email is already registered
        from database import DatabaseManager
        from config import Config
        
        try:
            config = Config()
            db_manager = DatabaseManager(config)
            with db_manager.get_session() as session:
                existing_user = session.query(User).filter_by(email=email).first()
                if existing_user:
                    raise ValidationError("Email address is already registered")
        except Exception:
            # If we can't check, let the service layer handle it
            pass
    
    def validate_password(self, field):
        """Custom password validation"""
        password = field.data
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            raise ValidationError("Password must contain at least one letter and one number")

class LoginForm(Form):
    """Form for user authentication""" # Using regular WTForms (no Flask-WTF CSRF)
    
    username_or_email = StringField(
        'Username or Email', 
        validators=[
            DataRequired(message="Username or email is required"),
            Length(max=120, message="Input is too long")
        ],
        render_kw={
            "placeholder": "Enter your username or email",
            "class": "form-control",
            "autocomplete": "username"
        }
    )
    
    password = PasswordField(
        'Password', 
        validators=[DataRequired(message="Password is required")],
        render_kw={
            "placeholder": "Enter your password",
            "class": "form-control",
            "autocomplete": "current-password"
        }
    )
    
    remember_me = BooleanField(
        'Remember me',
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Login',
        render_kw={"class": "btn btn-primary"}
    )

class ProfileEditForm(Form):
    """Form for profile management""" # Using regular WTForms (no Flask-WTF CSRF)
    
    first_name = StringField(
        'First Name',
        validators=[
            Optional(),
            Length(max=100, message="First name must be no more than 100 characters")
        ],
        render_kw={
            "placeholder": "Enter your first name",
            "class": "form-control",
            "autocomplete": "given-name"
        }
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            Optional(),
            Length(max=100, message="Last name must be no more than 100 characters")
        ],
        render_kw={
            "placeholder": "Enter your last name",
            "class": "form-control",
            "autocomplete": "family-name"
        }
    )
    
    email = StringField(
        'Email Address', 
        validators=[
            DataRequired(message="Email address is required"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email address must be no more than 120 characters")
        ],
        render_kw={
            "placeholder": "Enter your email address",
            "class": "form-control",
            "type": "email",
            "autocomplete": "email"
        }
    )
    
    submit = SubmitField(
        'Update Profile',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_email(self, field):
        """Custom email validation"""
        email = field.data
        
        # Use email_validator for thorough validation
        try:
            validate_email(email)
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email address: {str(e)}")

class PasswordChangeForm(Form):
    """Form for password changes by authenticated users""" # Using regular WTForms (no Flask-WTF CSRF)
    
    current_password = PasswordField(
        'Current Password', 
        validators=[DataRequired(message="Current password is required")],
        render_kw={
            "placeholder": "Enter your current password",
            "class": "form-control",
            "autocomplete": "current-password"
        }
    )
    
    new_password = PasswordField(
        'New Password', 
        validators=[
            DataRequired(message="New password is required"),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters")
        ],
        render_kw={
            "placeholder": "Enter your new password",
            "class": "form-control",
            "autocomplete": "new-password"
        }
    )
    
    confirm_new_password = PasswordField(
        'Confirm New Password', 
        validators=[
            DataRequired(message="Please confirm your new password"),
            EqualTo('new_password', message='Passwords must match')
        ],
        render_kw={
            "placeholder": "Confirm your new password",
            "class": "form-control",
            "autocomplete": "new-password"
        }
    )
    
    submit = SubmitField(
        'Change Password',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_new_password(self, field):
        """Custom password validation"""
        password = field.data
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            raise ValidationError("Password must contain at least one letter and one number")

class PasswordResetRequestForm(Form):
    """Form for password reset initiation""" # Using regular WTForms (no Flask-WTF CSRF)
    
    email = StringField(
        'Email Address', 
        validators=[
            DataRequired(message="Email address is required"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email address is too long")
        ],
        render_kw={
            "placeholder": "Enter your email address",
            "class": "form-control",
            "type": "email",
            "autocomplete": "email"
        }
    )
    
    submit = SubmitField(
        'Send Reset Link',
        render_kw={"class": "btn btn-primary"}
    )

class PasswordResetForm(Form):
    """Form for password reset completion""" # Using regular WTForms (no Flask-WTF CSRF)
    
    password = PasswordField(
        'New Password', 
        validators=[
            DataRequired(message="Password is required"),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters")
        ],
        render_kw={
            "placeholder": "Enter your new password",
            "class": "form-control",
            "autocomplete": "new-password"
        }
    )
    
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo('password', message='Passwords must match')
        ],
        render_kw={
            "placeholder": "Confirm your new password",
            "class": "form-control",
            "autocomplete": "new-password"
        }
    )
    
    submit = SubmitField(
        'Reset Password',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_password(self, field):
        """Custom password validation"""
        password = field.data
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            raise ValidationError("Password must contain at least one letter and one number")

class ProfileDeleteForm(Form):
    """Form for profile deletion confirmation""" # Using regular WTForms (no Flask-WTF CSRF)
    
    confirmation = StringField(
        'Type "DELETE" to confirm',
        validators=[
            DataRequired(message="Please type DELETE to confirm"),
        ],
        render_kw={
            "placeholder": "Type DELETE to confirm",
            "class": "form-control"
        }
    )
    
    password = PasswordField(
        'Current Password', 
        validators=[DataRequired(message="Current password is required for confirmation")],
        render_kw={
            "placeholder": "Enter your current password",
            "class": "form-control",
            "autocomplete": "current-password"
        }
    )
    
    submit = SubmitField(
        'Delete My Profile',
        render_kw={"class": "btn btn-danger"}
    )
    
    def validate_confirmation(self, field):
        """Validate deletion confirmation"""
        if field.data != "DELETE":
            raise ValidationError("Please type DELETE exactly to confirm profile deletion")

class EmailVerificationResendForm(Form):
    """Form for resending email verification""" # Using regular WTForms (no Flask-WTF CSRF)
    
    submit = SubmitField(
        'Resend Verification Email',
        render_kw={"class": "btn btn-secondary"}
    )

# Admin forms (extending existing admin forms)
class AdminUserCreateForm(Form):
    """Form for admin user creation""" # Using regular WTForms (no Flask-WTF CSRF)
    
    username = StringField(
        'Username', 
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=64, message="Username must be between 3 and 64 characters")
        ],
        render_kw={
            "placeholder": "Enter username",
            "class": "form-control"
        }
    )
    
    email = StringField(
        'Email Address', 
        validators=[
            DataRequired(message="Email address is required"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email address must be no more than 120 characters")
        ],
        render_kw={
            "placeholder": "Enter email address",
            "class": "form-control",
            "type": "email"
        }
    )
    
    first_name = StringField(
        'First Name',
        validators=[
            Optional(),
            Length(max=100, message="First name must be no more than 100 characters")
        ],
        render_kw={
            "placeholder": "Enter first name (optional)",
            "class": "form-control"
        }
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            Optional(),
            Length(max=100, message="Last name must be no more than 100 characters")
        ],
        render_kw={
            "placeholder": "Enter last name (optional)",
            "class": "form-control"
        }
    )
    
    role = SelectField(
        'Role', 
        choices=[(role.value, role.value.capitalize()) for role in UserRole],
        validators=[DataRequired(message="Role is required")],
        render_kw={"class": "form-select"}
    )
    
    password = PasswordField(
        'Temporary Password', 
        validators=[
            DataRequired(message="Temporary password is required"),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters")
        ],
        render_kw={
            "placeholder": "Enter temporary password",
            "class": "form-control"
        }
    )
    
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[
            DataRequired(message="Please confirm the password"),
            EqualTo('password', message='Passwords must match')
        ],
        render_kw={
            "placeholder": "Confirm temporary password",
            "class": "form-control"
        }
    )
    
    send_email = BooleanField(
        'Send account creation email to user',
        default=True,
        render_kw={"class": "form-check-input"}
    )
    
    bypass_email_verification = BooleanField(
        'Skip email verification (activate account immediately)',
        default=False,
        render_kw={"class": "form-check-input"}
    )
    
    is_active = BooleanField(
        'Active',
        default=True,
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Create User',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_username(self, field):
        """Custom username validation"""
        username = field.data
        
        if not username.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("Username can only contain letters, numbers, hyphens, and underscores")
    
    def validate_password(self, field):
        """Custom password validation"""
        password = field.data
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            raise ValidationError("Password must contain at least one letter and one number")

class AdminUserEditForm(Form):
    """Form for admin user editing""" # Using regular WTForms (no Flask-WTF CSRF)
    
    user_id = HiddenField('User ID', validators=[DataRequired()])
    
    username = StringField(
        'Username', 
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=64, message="Username must be between 3 and 64 characters")
        ],
        render_kw={
            "class": "form-control"
        }
    )
    
    email = StringField(
        'Email Address', 
        validators=[
            DataRequired(message="Email address is required"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email address must be no more than 120 characters")
        ],
        render_kw={
            "class": "form-control",
            "type": "email"
        }
    )
    
    first_name = StringField(
        'First Name',
        validators=[
            Optional(),
            Length(max=100, message="First name must be no more than 100 characters")
        ],
        render_kw={"class": "form-control"}
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            Optional(),
            Length(max=100, message="Last name must be no more than 100 characters")
        ],
        render_kw={"class": "form-control"}
    )
    
    role = SelectField(
        'Role', 
        choices=[(role.value, role.value.capitalize()) for role in UserRole],
        validators=[DataRequired(message="Role is required")],
        render_kw={"class": "form-select"}
    )
    
    is_active = BooleanField(
        'Active',
        render_kw={"class": "form-check-input"}
    )
    
    email_verified = BooleanField(
        'Email Verified',
        render_kw={"class": "form-check-input"}
    )
    
    account_locked = BooleanField(
        'Account Locked',
        render_kw={"class": "form-check-input"}
    )
    
    reset_failed_attempts = BooleanField(
        'Reset Failed Login Attempts',
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Update User',
        render_kw={"class": "btn btn-primary"}
    )

class AdminPasswordResetForm(Form):
    """Form for admin password reset""" # Using regular WTForms (no Flask-WTF CSRF)
    
    user_id = HiddenField('User ID', validators=[DataRequired()])
    
    new_password = PasswordField(
        'New Password', 
        validators=[
            DataRequired(message="New password is required"),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters")
        ],
        render_kw={
            "placeholder": "Enter new password",
            "class": "form-control"
        }
    )
    
    confirm_password = PasswordField(
        'Confirm Password', 
        validators=[
            DataRequired(message="Please confirm the password"),
            EqualTo('new_password', message='Passwords must match')
        ],
        render_kw={
            "placeholder": "Confirm new password",
            "class": "form-control"
        }
    )
    
    send_notification = BooleanField(
        'Send password change notification to user',
        default=True,
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Reset Password',
        render_kw={"class": "btn btn-warning"}
    )
    
    def validate_new_password(self, field):
        """Custom password validation"""
        password = field.data
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            raise ValidationError("Password must contain at least one letter and one number")