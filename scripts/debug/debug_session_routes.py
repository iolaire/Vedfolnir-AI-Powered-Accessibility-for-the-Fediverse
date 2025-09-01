#!/usr/bin/env python3
"""
Debug Session Routes

Temporary debug routes to help troubleshoot session persistence issues.
These routes should be removed in production.
"""

from flask import Blueprint, jsonify, session, g, current_app
from flask_login import login_required, current_user
from session_middleware_v2 import get_current_session_context, get_current_session_id
from session_platform_fix import validate_platform_session, debug_session_state
import json

debug_bp = Blueprint('debug_session', __name__, url_prefix='/debug')

@debug_bp.route('/session')
@login_required
def debug_session():
    """Debug current session state"""
    try:
        debug_info = debug_session_state()
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@debug_bp.route('/platform')
@login_required
def debug_platform():
    """Debug current platform state"""
    try:
        validation_result = validate_platform_session()
        
        return jsonify({
            'success': True,
            'validation': validation_result,
            'current_user_id': current_user.id if current_user else None,
            'flask_session_keys': list(session.keys()),
            'g_has_session_context': hasattr(g, 'session_context'),
            'g_session_context': getattr(g, 'session_context', None)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@debug_bp.route('/context')
@login_required
def debug_context():
    """Debug session context specifically"""
    try:
        context = get_current_session_context()
        session_id = get_current_session_id()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_context': context,
            'flask_session_platform_data': {
                'platform_connection_id': session.get('platform_connection_id'),
                'platform_name': session.get('platform_name'),
                'platform_type': session.get('platform_type'),
                'platform_instance_url': session.get('platform_instance_url')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@debug_bp.route('/force_platform_update/<int:platform_id>')
@login_required
def debug_force_platform_update(platform_id):
    """Force platform update and show results"""
    try:
        from session_middleware_v2 import update_session_platform
        
        # Get state before update
        before_state = debug_session_state()
        
        # Perform update
        success = update_session_platform(platform_id)
        
        # Get state after update
        after_state = debug_session_state()
        
        # Validate result
        validation = validate_platform_session(platform_id)
        
        return jsonify({
            'success': success,
            'platform_id': platform_id,
            'before_state': before_state,
            'after_state': after_state,
            'validation': validation
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_debug_routes(app):
    """Register debug routes with the Flask app"""
    app.register_blueprint(debug_bp)
