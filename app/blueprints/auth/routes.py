from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

# Import the user management blueprint
from .user_management_routes import user_management_bp

# Create auth blueprint that includes user management
auth_bp = Blueprint('auth', __name__)

# Register user management as a sub-blueprint
auth_bp.register_blueprint(user_management_bp)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Redirect to user management login"""
    return redirect(url_for('user_management.login'))

@auth_bp.route('/logout')
def logout():
    """Redirect to user management logout"""
    return redirect(url_for('user_management.logout'))

@auth_bp.route('/first_time_setup')
@login_required
def first_time_setup():
    """First-time platform setup for new users"""
    return render_template('first_time_setup.html')
