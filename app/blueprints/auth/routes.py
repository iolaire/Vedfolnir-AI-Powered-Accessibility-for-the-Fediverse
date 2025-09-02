from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/first_time_setup')
@login_required
def first_time_setup():
    """First-time platform setup for new users"""
    return render_template('first_time_setup.html')
