# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for User Management Forms
"""

import unittest
from unittest.mock import patch, Mock
from flask import Flask
from wtforms.validators import ValidationError

from forms.user_management_forms import (
    UserRegistrationForm, LoginForm, ProfileEditForm, PasswordChangeForm,
    PasswordResetRequestForm, PasswordResetForm, ProfileDeleteForm,
    EmailVerificationResendForm, AdminUserCreateForm, AdminUserEditForm,
    AdminPasswordResetForm
)
from models import UserRole

class TestUserManagementForms(unittest.TestCase):
    """Test user management forms validation and functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.app_context.pop()

class TestUserRegistrationForm(TestUserManagementForms):
    """Test UserRegistrationForm"""
    
    def test_valid_registration_form(self):
        """Test valid registration form data"""
        with patch('forms.user_management_forms.User') as mock_user:
            mock_user.query.filter_by.return_value.first.return_value = None
            
            form_data = {
                'username': 'testuser',
                'email': 'test@test.com',
                'first_name': 'Test',
                'last_name': 'User',
                'password': 'password123',
                'confirm_password': 'password123',
                'data_processing_consent': True
            }
            
            form = UserRegistrationForm(data=form_data)
            self.assertTrue(form.validate())
    
    def test_username_validation_too_short(self):
        """Test username validation with too short username"""
        form_data = {
            'username': 'ab',  # Too short
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'data_processing_consent': True
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Username must be between 3 and 64 characters', str(form.username.errors))
    
    def test_username_validation_too_long(self):
        """Test username validation with too long username"""
        form_data = {
            'username': 'a' * 65,  # Too long
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'data_processing_consent': True
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Username must be between 3 and 64 characters', str(form.username.errors))
    
    def test_username_validation_invalid_characters(self):
        """Test username validation with invalid characters"""
        with patch('forms.user_management_forms.User') as mock_user:
            mock_user.query.filter_by.return_value.first.return_value = None
            
            form_data = {
                'username': 'test@user',  # Invalid character @
                'email': 'test@test.com',
                'password': 'password123',
                'confirm_password': 'password123',
                'data_processing_consent': True
            }
            
            form = UserRegistrationForm(data=form_data)
            self.assertFalse(form.validate())
            self.assertIn('can only contain letters, numbers, hyphens, and underscores', str(form.username.errors))
    
    def test_email_validation_invalid_format(self):
        """Test email validation with invalid format"""
        form_data = {
            'username': 'testuser',
            'email': 'invalid-email',  # Invalid format
            'password': 'password123',
            'confirm_password': 'password123',
            'data_processing_consent': True
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertTrue(any('valid email address' in str(error) for error in form.email.errors))
    
    def test_password_validation_too_short(self):
        """Test password validation with too short password"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'pass1',  # Too short
            'confirm_password': 'pass1',
            'data_processing_consent': True
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Password must be between 8 and 128 characters', str(form.password.errors))
    
    def test_password_validation_no_letter(self):
        """Test password validation with no letters"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': '12345678',  # No letters
            'confirm_password': '12345678',
            'data_processing_consent': True
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('at least one letter and one number', str(form.password.errors))
    
    def test_password_validation_no_number(self):
        """Test password validation with no numbers"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password',  # No numbers
            'confirm_password': 'password',
            'data_processing_consent': True
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('at least one letter and one number', str(form.password.errors))
    
    def test_password_confirmation_mismatch(self):
        """Test password confirmation mismatch"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'different123',  # Doesn't match
            'data_processing_consent': True
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Passwords must match', str(form.confirm_password.errors))
    
    def test_data_processing_consent_required(self):
        """Test that data processing consent is required"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'data_processing_consent': False  # Not consented
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('consent to data processing', str(form.data_processing_consent.errors))

class TestLoginForm(TestUserManagementForms):
    """Test LoginForm"""
    
    def test_valid_login_form(self):
        """Test valid login form data"""
        form_data = {
            'username_or_email': 'testuser',
            'password': 'password123',
            'remember_me': True
        }
        
        form = LoginForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_login_form_missing_username(self):
        """Test login form with missing username"""
        form_data = {
            'username_or_email': '',  # Missing
            'password': 'password123'
        }
        
        form = LoginForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Username or email is required', str(form.username_or_email.errors))
    
    def test_login_form_missing_password(self):
        """Test login form with missing password"""
        form_data = {
            'username_or_email': 'testuser',
            'password': ''  # Missing
        }
        
        form = LoginForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Password is required', str(form.password.errors))

class TestProfileEditForm(TestUserManagementForms):
    """Test ProfileEditForm"""
    
    def test_valid_profile_edit_form(self):
        """Test valid profile edit form data"""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@test.com'
        }
        
        form = ProfileEditForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_profile_edit_form_invalid_email(self):
        """Test profile edit form with invalid email"""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email'  # Invalid format
        }
        
        form = ProfileEditForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertTrue(any('valid email address' in str(error) for error in form.email.errors))
    
    def test_profile_edit_form_optional_names(self):
        """Test profile edit form with optional names"""
        form_data = {
            'first_name': '',  # Optional
            'last_name': '',   # Optional
            'email': 'test@test.com'
        }
        
        form = ProfileEditForm(data=form_data)
        self.assertTrue(form.validate())

class TestPasswordChangeForm(TestUserManagementForms):
    """Test PasswordChangeForm"""
    
    def test_valid_password_change_form(self):
        """Test valid password change form data"""
        form_data = {
            'current_password': 'oldpassword123',
            'new_password': 'newpassword123',
            'confirm_new_password': 'newpassword123'
        }
        
        form = PasswordChangeForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_password_change_form_mismatch(self):
        """Test password change form with password mismatch"""
        form_data = {
            'current_password': 'oldpassword123',
            'new_password': 'newpassword123',
            'confirm_new_password': 'different123'  # Doesn't match
        }
        
        form = PasswordChangeForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Passwords must match', str(form.confirm_new_password.errors))
    
    def test_password_change_form_weak_password(self):
        """Test password change form with weak password"""
        form_data = {
            'current_password': 'oldpassword123',
            'new_password': 'password',  # No numbers
            'confirm_new_password': 'password'
        }
        
        form = PasswordChangeForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('at least one letter and one number', str(form.new_password.errors))

class TestPasswordResetRequestForm(TestUserManagementForms):
    """Test PasswordResetRequestForm"""
    
    def test_valid_password_reset_request_form(self):
        """Test valid password reset request form data"""
        form_data = {
            'email': 'test@test.com'
        }
        
        form = PasswordResetRequestForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_password_reset_request_form_invalid_email(self):
        """Test password reset request form with invalid email"""
        form_data = {
            'email': 'invalid-email'  # Invalid format
        }
        
        form = PasswordResetRequestForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertTrue(any('valid email address' in str(error) for error in form.email.errors))

class TestPasswordResetForm(TestUserManagementForms):
    """Test PasswordResetForm"""
    
    def test_valid_password_reset_form(self):
        """Test valid password reset form data"""
        form_data = {
            'password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }
        
        form = PasswordResetForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_password_reset_form_mismatch(self):
        """Test password reset form with password mismatch"""
        form_data = {
            'password': 'newpassword123',
            'confirm_password': 'different123'  # Doesn't match
        }
        
        form = PasswordResetForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Passwords must match', str(form.confirm_password.errors))
    
    def test_password_reset_form_weak_password(self):
        """Test password reset form with weak password"""
        form_data = {
            'password': 'password',  # No numbers
            'confirm_password': 'password'
        }
        
        form = PasswordResetForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('at least one letter and one number', str(form.password.errors))

class TestProfileDeleteForm(TestUserManagementForms):
    """Test ProfileDeleteForm"""
    
    def test_valid_profile_delete_form(self):
        """Test valid profile delete form data"""
        form_data = {
            'confirmation': 'DELETE',
            'password': 'password123'
        }
        
        form = ProfileDeleteForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_profile_delete_form_wrong_confirmation(self):
        """Test profile delete form with wrong confirmation"""
        form_data = {
            'confirmation': 'delete',  # Wrong case
            'password': 'password123'
        }
        
        form = ProfileDeleteForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('type DELETE exactly', str(form.confirmation.errors))
    
    def test_profile_delete_form_missing_password(self):
        """Test profile delete form with missing password"""
        form_data = {
            'confirmation': 'DELETE',
            'password': ''  # Missing
        }
        
        form = ProfileDeleteForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Current password is required', str(form.password.errors))

class TestEmailVerificationResendForm(TestUserManagementForms):
    """Test EmailVerificationResendForm"""
    
    def test_email_verification_resend_form(self):
        """Test email verification resend form"""
        form = EmailVerificationResendForm()
        # This form has no validation requirements, just a submit button
        self.assertTrue(form.validate())

class TestAdminUserCreateForm(TestUserManagementForms):
    """Test AdminUserCreateForm"""
    
    def test_valid_admin_user_create_form(self):
        """Test valid admin user create form data"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'role': UserRole.VIEWER.value,
            'password': 'temppass123',
            'confirm_password': 'temppass123',
            'send_email': True,
            'bypass_email_verification': False,
            'is_active': True
        }
        
        form = AdminUserCreateForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_admin_user_create_form_invalid_username(self):
        """Test admin user create form with invalid username"""
        form_data = {
            'username': 'user@name',  # Invalid character
            'email': 'newuser@test.com',
            'role': UserRole.VIEWER.value,
            'password': 'temppass123',
            'confirm_password': 'temppass123'
        }
        
        form = AdminUserCreateForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('can only contain letters, numbers, hyphens, and underscores', str(form.username.errors))
    
    def test_admin_user_create_form_weak_password(self):
        """Test admin user create form with weak password"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'role': UserRole.VIEWER.value,
            'password': 'password',  # No numbers
            'confirm_password': 'password'
        }
        
        form = AdminUserCreateForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('at least one letter and one number', str(form.password.errors))

class TestAdminUserEditForm(TestUserManagementForms):
    """Test AdminUserEditForm"""
    
    def test_valid_admin_user_edit_form(self):
        """Test valid admin user edit form data"""
        form_data = {
            'user_id': '1',
            'username': 'editeduser',
            'email': 'edited@test.com',
            'first_name': 'Edited',
            'last_name': 'User',
            'role': UserRole.ADMIN.value,
            'is_active': True,
            'email_verified': True,
            'account_locked': False,
            'reset_failed_attempts': False
        }
        
        form = AdminUserEditForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_admin_user_edit_form_missing_user_id(self):
        """Test admin user edit form with missing user ID"""
        form_data = {
            'user_id': '',  # Missing
            'username': 'editeduser',
            'email': 'edited@test.com',
            'role': UserRole.ADMIN.value
        }
        
        form = AdminUserEditForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('This field is required', str(form.user_id.errors))

class TestAdminPasswordResetForm(TestUserManagementForms):
    """Test AdminPasswordResetForm"""
    
    def test_valid_admin_password_reset_form(self):
        """Test valid admin password reset form data"""
        form_data = {
            'user_id': '1',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123',
            'send_notification': True
        }
        
        form = AdminPasswordResetForm(data=form_data)
        self.assertTrue(form.validate())
    
    def test_admin_password_reset_form_mismatch(self):
        """Test admin password reset form with password mismatch"""
        form_data = {
            'user_id': '1',
            'new_password': 'newpass123',
            'confirm_password': 'different123',  # Doesn't match
            'send_notification': True
        }
        
        form = AdminPasswordResetForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('Passwords must match', str(form.confirm_password.errors))
    
    def test_admin_password_reset_form_weak_password(self):
        """Test admin password reset form with weak password"""
        form_data = {
            'user_id': '1',
            'new_password': 'password',  # No numbers
            'confirm_password': 'password',
            'send_notification': True
        }
        
        form = AdminPasswordResetForm(data=form_data)
        self.assertFalse(form.validate())
        self.assertIn('at least one letter and one number', str(form.new_password.errors))

if __name__ == '__main__':
    unittest.main()