"""
Vedfolnir Admin - Session Monitoring Routes

This module implements session monitoring functionality for the admin panel.
It provides comprehensive session tracking, statistics, and monitoring capabilities.

Author: Claude AI Assistant
Created: 2025-09-13
License: GNU Affero General Public License v3.0
"""

# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Admin Session Monitoring Routes"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from flask import render_template, request, jsonify, current_app, session
from flask_login import login_required, current_user
from sqlalchemy import text, func, and_, or_, desc

from models import User, UserSession
from app.core.security.core.security_middleware import rate_limit, validate_input_length, validate_csrf_token
from app.core.security.validation.enhanced_input_validation import enhanced_input_validation
from app.core.security.core.security_utils import sanitize_for_log
from app.services.admin.security.admin_access_control import admin_required
# Performance monitor not available, using basic timing
from app.services.admin.helpers.session_helpers import SessionHelper
# Admin helper not available

# Configure logging
logger = logging.getLogger(__name__)

# Session helper instance
session_helper = SessionHelper()



def register_routes(bp):
    """Register session monitoring routes with the admin blueprint"""
    
    
    @bp.route('/api/session-monitoring/statistics', methods=['GET'])
    @login_required
    @admin_required
    def api_session_statistics():
        """API endpoint to get session monitoring statistics"""
        try:
            time_range = request.args.get('time_range', '24h')
            stats = session_helper.get_session_statistics(time_range)
            
            return jsonify({
                'status': 'success',
                'data': stats
            })
        except Exception as e:
            logger.error(f"Error getting session statistics: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Failed to get statistics: {str(e)}'
            }), 500

    @bp.route('/api/session-monitoring/sessions', methods=['GET'])
    @login_required
    @admin_required
    def api_sessions_list():
        """API endpoint to get list of active sessions"""
        try:
            status = request.args.get('status', 'all')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            
            sessions_data = session_helper.get_filtered_sessions(status, page, per_page)
            
            return jsonify({
                'success': True,
                'data': sessions_data
            })
        except Exception as e:
            logger.error(f"Error getting sessions list: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to get sessions: {str(e)}'
            }), 500

    @bp.route('/api/session-monitoring/session/<session_id>', methods=['GET'])
    @login_required
    @admin_required
    def api_session_details(session_id):
        """API endpoint to get detailed session information"""
        try:
            session_details = session_helper.get_session_details(session_id)
            
            if not session_details:
                return jsonify({
                    'success': False,
                    'message': 'Session not found'
                }), 404
            
            return jsonify({
                'success': True,
                'data': session_details
            })
        except Exception as e:
            logger.error(f"Error getting session details: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to get session details: {str(e)}'
            }), 500

    @bp.route('/api/session-monitoring/terminate', methods=['POST'])
    @login_required
    @admin_required
    @validate_csrf_token
    @rate_limit(limit=5, window_seconds=60)
    @validate_input_length()
    @enhanced_input_validation
    def api_terminate_session():
        """API endpoint to terminate a session"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            reason = data.get('reason', 'Administrative termination')
            
            if not session_id:
                return jsonify({
                    'success': False,
                    'message': 'Session ID is required'
                }), 400
            
            result = session_helper.terminate_session(session_id, reason)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error terminating session: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to terminate session: {str(e)}'
            }), 500

    @bp.route('/api/session-monitoring/analytics', methods=['GET'])
    @login_required
    @admin_required
    def api_session_analytics():
        """API endpoint to get session analytics data"""
        try:
            time_range = request.args.get('time_range', '24h')
            analytics = session_helper.get_session_analytics(time_range)
            
            return jsonify({
                'success': True,
                'data': analytics
            })
        except Exception as e:
            logger.error(f"Error getting session analytics: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to get analytics: {str(e)}'
            }), 500

    @bp.route('/api/session-monitoring/export', methods=['GET'])
    @login_required
    @admin_required
    def api_session_export():
        """API endpoint to export session data"""
        try:
            export_format = request.args.get('format', 'json')
            time_range = request.args.get('time_range', '24h')
            
            export_data = session_helper.get_session_export_data(time_range, export_format)
            
            if export_format == 'csv':
                return jsonify({
                    'success': True,
                    'data': export_data,
                    'format': 'csv'
                })
            else:
                return jsonify({
                    'success': True,
                    'data': export_data,
                    'format': 'json'
                })
        except Exception as e:
            logger.error(f"Error exporting session data: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to export data: {str(e)}'
            }), 500

    @bp.route('/api/session-monitoring/alerts', methods=['GET'])
    @login_required
    @admin_required
    def api_session_alerts():
        """API endpoint to get session alerts and warnings"""
        try:
            alerts = session_helper.get_session_alerts()
            
            return jsonify({
                'success': True,
                'data': alerts
            })
        except Exception as e:
            logger.error(f"Error getting session alerts: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Failed to get alerts: {str(e)}'
            }), 500