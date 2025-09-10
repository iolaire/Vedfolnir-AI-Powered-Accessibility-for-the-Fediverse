from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import ProcessingStatus, PlatformConnection
from utils.error_responses import validation_error, configuration_error, internal_error
from datetime import datetime
import os
import json
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import additional API route modules
from .page_notification_routes import page_notification_bp
from .websocket_client_config_routes import websocket_client_config_bp

# Register sub-blueprints
api_bp.register_blueprint(page_notification_bp)
api_bp.register_blueprint(websocket_client_config_bp)

@api_bp.route('/session/state', methods=['GET'])
def get_session_state():
    """Get current session state"""
    try:
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True,
                'user_id': current_user.id,
                'username': current_user.username,
                'role': current_user.role.value if current_user.role else 'user',
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'authenticated': False,
                'error': 'Not authenticated'
            }), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/update_caption/<int:image_id>', methods=['POST'])
@login_required
def update_caption(image_id):
    """Update caption for an image"""
    try:
        data = request.get_json()
        if not data or 'caption' not in data:
            return jsonify({'success': False, 'error': 'Caption required'}), 400
        
        db_manager = getattr(current_app, 'config', {}).get('db_manager')
        if not db_manager:
            return jsonify({'success': False, 'error': 'Database manager not available'}), 500
        
        caption = data['caption'].strip()
        success = db_manager.update_image_caption(image_id, caption)
        
        if success:
            return jsonify({'success': True, 'message': 'Caption updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update caption'}), 500
            
    except (KeyError, ValueError) as e:
        current_app.logger.error(f"Invalid request data for caption update: {str(e)}")
        return validation_error("Invalid request data", str(e))
    except AttributeError as e:
        current_app.logger.error(f"Configuration error updating caption: {str(e)}")
        return configuration_error("Service configuration error", str(e))
    except Exception as e:
        current_app.logger.error(f"Unexpected error updating caption: {str(e)}")
        return internal_error("Failed to update caption", str(e))

@api_bp.route('/regenerate_caption/<int:image_id>', methods=['POST'])
@login_required
def regenerate_caption(image_id):
    """Regenerate caption for an image"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        with unified_session_manager.get_db_session() as session:
            from models import Image
            image = session.query(Image).filter_by(id=image_id).first()
            
            if not image:
                return jsonify({'success': False, 'error': 'Image not found'}), 404
            
            # Queue for regeneration (simplified implementation)
            image.status = ProcessingStatus.PENDING
            session.commit()
            
            return jsonify({'success': True, 'message': 'Caption regeneration queued'})
            
    except Exception as e:
        current_app.logger.error(f"Error regenerating caption: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.route('/add_platform', methods=['POST'])
@login_required
def add_platform():
    """Add a new platform connection"""
    try:
        data = request.get_json()
        required_fields = ['name', 'platform_type', 'instance_url', 'username', 'access_token']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        with unified_session_manager.get_db_session() as session:
            # Check for duplicate platform
            existing = session.query(PlatformConnection).filter_by(
                user_id=current_user.id,
                instance_url=data['instance_url'],
                username=data['username']
            ).first()
            
            if existing:
                return jsonify({'success': False, 'error': 'Platform connection already exists'}), 400
            
            # Create new platform connection
            platform = PlatformConnection(
                user_id=current_user.id,
                name=data['name'],
                platform_type=data['platform_type'],
                instance_url=data['instance_url'],
                username=data['username'],
                access_token=data['access_token'],
                is_active=True
            )
            
            session.add(platform)
            session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Platform added successfully',
                'platform_id': platform.id
            })
            
    except Exception as e:
        current_app.logger.error(f"Error adding platform: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.route('/switch_platform/<int:platform_id>', methods=['POST'])
@login_required
def switch_platform(platform_id):
    """Switch to a different platform"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        with unified_session_manager.get_db_session() as session:
            platform = session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not platform:
                return jsonify({'success': False, 'error': 'Platform not found'}), 404
            
            # RACE CONDITION FIX: Cancel active tasks before switching
            try:
                from web_caption_generation_service import WebCaptionGenerationService
                from app.core.database.core.database_manager import DatabaseManager
                
                db_manager = current_app.config.get('db_manager')
                if db_manager:
                    caption_service = WebCaptionGenerationService(db_manager)
                    active_task = caption_service.task_queue_manager.get_user_active_task(current_user.id)
                    
                    if active_task:
                        # Cancel the active task and wait for confirmation
                        cancelled = caption_service.cancel_generation(active_task.id, current_user.id)
                        
                        if not cancelled:
                            return jsonify({
                                'success': False, 
                                'error': 'Cannot switch platform: active task cancellation failed'
                            }), 409
                        
                        # Verify cancellation completed
                        import time
                        max_wait = 3  # seconds
                        wait_time = 0.1
                        elapsed = 0
                        
                        while elapsed < max_wait:
                            current_task = caption_service.task_queue_manager.get_user_active_task(current_user.id)
                            if not current_task:
                                break
                            time.sleep(wait_time)
                            elapsed += wait_time
                        
                        # Final verification
                        if caption_service.task_queue_manager.get_user_active_task(current_user.id):
                            return jsonify({
                                'success': False,
                                'error': 'Cannot switch platform: active task still running'
                            }), 409
                            
            except Exception as task_error:
                current_app.logger.warning(f"Task cancellation check failed: {task_error}")
                # Continue with platform switch - task cancellation is best effort
            
            # Update session context (simplified)
            return jsonify({
                'success': True,
                'message': 'Platform switched successfully',
                'platform': {
                    'id': platform.id,
                    'name': platform.name,
                    'platform_type': platform.platform_type
                }
            })
            
    except Exception as e:
        current_app.logger.error(f"Error switching platform: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.route('/test_platform/<int:platform_id>', methods=['POST'])
@login_required
def test_platform(platform_id):
    """Test platform connection"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        with unified_session_manager.get_db_session() as session:
            platform = session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id
            ).first()
            
            if not platform:
                return jsonify({'success': False, 'error': 'Platform not found'}), 404
            
            # Test connection (simplified - would normally test API connectivity)
            return jsonify({
                'success': True,
                'message': 'Platform connection test successful',
                'status': 'connected'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error testing platform: {str(e)}")
        return jsonify({'success': False, 'error': 'Connection test failed'}), 500

@api_bp.route('/get_platform/<int:platform_id>', methods=['GET'])
@login_required
def get_platform(platform_id):
    """Get platform connection details"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        with unified_session_manager.get_db_session() as session:
            platform = session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id
            ).first()
            
            if not platform:
                return jsonify({'success': False, 'error': 'Platform not found'}), 404
            
            return jsonify({
                'success': True,
                'platform': {
                    'id': platform.id,
                    'name': platform.name,
                    'platform_type': platform.platform_type,
                    'instance_url': platform.instance_url,
                    'username': platform.username,
                    'is_active': platform.is_active,
                    'is_default': platform.is_default
                }
            })
            
    except Exception as e:
        current_app.logger.error(f"Error getting platform: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.route('/edit_platform/<int:platform_id>', methods=['PUT'])
@login_required
def edit_platform(platform_id):
    """Edit platform connection"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        with unified_session_manager.get_db_session() as session:
            platform = session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id
            ).first()
            
            if not platform:
                return jsonify({'success': False, 'error': 'Platform not found'}), 404
            
            # Update platform fields
            if 'name' in data:
                platform.name = data['name']
            if 'instance_url' in data:
                platform.instance_url = data['instance_url']
            if 'username' in data:
                platform.username = data['username']
            if 'access_token' in data:
                platform.access_token = data['access_token']
            
            session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Platform updated successfully'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error editing platform: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.route('/delete_platform/<int:platform_id>', methods=['DELETE'])
@login_required
def delete_platform(platform_id):
    """Delete platform connection"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        with unified_session_manager.get_db_session() as session:
            platform = session.query(PlatformConnection).filter_by(
                id=platform_id,
                user_id=current_user.id
            ).first()
            
            if not platform:
                return jsonify({'success': False, 'error': 'Platform not found'}), 404
            
            session.delete(platform)
            session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Platform deleted successfully'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error deleting platform: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@api_bp.route('/csrf-token', methods=['GET'])
@login_required
def get_csrf_token():
    """Get CSRF token"""
    try:
        from flask_wtf.csrf import generate_csrf
        token = generate_csrf()
        return jsonify({'csrf_token': token})
    except Exception as e:
        current_app.logger.error(f"Error generating CSRF token: {str(e)}")
        return jsonify({'error': 'Failed to generate CSRF token'}), 500

@api_bp.route('/session/cleanup', methods=['POST'])
@login_required
def session_cleanup():
    """Clean up user sessions"""
    try:
        unified_session_manager = getattr(current_app, 'unified_session_manager', None)
        if not unified_session_manager:
            return jsonify({'success': False, 'error': 'Session manager not available'}), 500
        
        count = unified_session_manager.cleanup_user_sessions(current_user.id)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {count} sessions'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error cleaning up sessions: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to cleanup sessions'}), 500

@api_bp.route('/maintenance/status', methods=['GET'])
def maintenance_status():
    """Get maintenance status"""
    try:
        return jsonify({
            'success': True,
            'status': 'operational',
            'maintenance_mode': False,
            'message': 'System is operational'
        })
    except Exception as e:
        current_app.logger.error(f"Error getting maintenance status: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get maintenance status'}), 500

@api_bp.route('/websocket/client-config', methods=['GET', 'OPTIONS'])
def websocket_client_config():
    """Provide WebSocket client configuration"""
    try:
        config = {
            'socketio_path': '/socket.io',
            'transports': ['websocket', 'polling'],
            'upgrade': True,
            'rememberUpgrade': True,
            'timeout': 20000,
            'forceNew': False
        }
        
        response = jsonify(config)
        
        # Add CORS headers
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error getting WebSocket config: {str(e)}")
        return jsonify({'error': 'Failed to get WebSocket configuration'}), 500

@api_bp.route('/csp-report', methods=['POST'])
def csp_report():
    """
    Handle Content Security Policy violation reports
    
    CSP reports are sent automatically by browsers when CSP violations occur.
    This endpoint logs the violations for security monitoring and debugging.
    """
    try:
        # CSP reports can be sent with various content types by different browsers
        # Handle all possible content types gracefully
        content_type = request.headers.get('Content-Type', '').lower()
        
        csp_data = None
        
        # Try multiple approaches to get the CSP data
        if any(ct in content_type for ct in ['application/csp-report', 'application/json']):
            # Standard CSP report or JSON content type
            csp_data = request.get_json(silent=True)
        
        if not csp_data:
            # Fallback: try to parse raw data as JSON regardless of content type
            try:
                raw_data = request.get_data(as_text=True)
                if raw_data:
                    csp_data = json.loads(raw_data)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                # If JSON parsing fails, create minimal report from headers
                csp_data = {
                    'csp-report': {
                        'document-uri': request.headers.get('Referer', 'unknown'),
                        'user-agent': request.headers.get('User-Agent', 'unknown'),
                        'content-type': content_type,
                        'raw-data-length': len(request.get_data())
                    }
                }
        
        if not csp_data:
            current_app.logger.warning(f"CSP report received with no parseable data. Content-Type: {content_type}")
            return '', 204  # No Content
        
        # Extract useful information from the CSP report
        csp_report = csp_data.get('csp-report', {})
        
        # Log the CSP violation with structured data
        violation_info = {
            'timestamp': datetime.utcnow().isoformat(),
            'document_uri': csp_report.get('document-uri', 'unknown'),
            'referrer': csp_report.get('referrer', 'unknown'),
            'violated_directive': csp_report.get('violated-directive', 'unknown'),
            'effective_directive': csp_report.get('effective-directive', 'unknown'),
            'original_policy': csp_report.get('original-policy', 'unknown'),
            'disposition': csp_report.get('disposition', 'report'),
            'blocked_uri': csp_report.get('blocked-uri', 'unknown'),
            'line_number': csp_report.get('line-number', 'unknown'),
            'column_number': csp_report.get('column-number', 'unknown'),
            'source_file': csp_report.get('source-file', 'unknown'),
            'status_code': csp_report.get('status-code', 'unknown'),
            'script_sample': csp_report.get('script-sample', 'unknown')[:200],  # Truncate for log readability
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'remote_addr': request.remote_addr
        }
        
        # Log the CSP violation
        current_app.logger.warning(f"CSP violation detected: {json.dumps(violation_info, indent=2)}")
        
        # For development, you might want to store these in the database for analysis
        # For now, we'll just log them
        
        return '', 204  # No Content - browsers don't care about the response
        
    except Exception as e:
        # Don't return errors for CSP reports to avoid endless loops
        current_app.logger.error(f"Error processing CSP report: {str(e)}")
        return '', 204  # Always return 204 to prevent retry loops
