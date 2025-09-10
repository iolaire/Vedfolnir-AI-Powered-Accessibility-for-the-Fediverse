# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MIGRATION NOTE: Flash messages in this file have been commented out as part of
# the notification system migration. The application now uses the unified
# WebSocket-based notification system. These comments should be replaced with
# appropriate unified notification calls in a future update.


from app.services.notification.manager.unified_manager import UnifiedNotificationManager
"""
Admin Storage Management Routes

This module provides admin routes for storage monitoring, management, and control.
Includes detailed storage dashboard, manual override controls, and storage refresh functionality.
"""

from flask import render_template, current_app, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from models import UserRole
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from session_error_handlers import with_session_error_handling
from app.services.admin.components.admin_storage_dashboard import AdminStorageDashboard
from app.services.storage.components.storage_override_system import StorageOverrideSystem, OverrideValidationError, OverrideNotFoundError, StorageOverrideSystemError
from app.core.database.core.database_manager import DatabaseManager
from config import Config
import logging

logger = logging.getLogger(__name__)


def register_routes(bp):
    """Register storage management routes"""
    
    @bp.route('/storage')
    @login_required
    def storage_dashboard():
        """Detailed storage monitoring dashboard"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('admin.dashboard'))
        
        try:
            storage_dashboard = AdminStorageDashboard()
            
            # Get comprehensive storage data
            dashboard_data = storage_dashboard.get_storage_dashboard_data()
            gauge_data = storage_dashboard.get_storage_gauge_data()
            summary_data = storage_dashboard.get_storage_summary_card_data()
            actions_data = storage_dashboard.get_quick_actions_data()
            
            # Get health check data
            health_data = storage_dashboard.health_check()
            
            return render_template('admin/storage_dashboard.html',
                                 dashboard_data=dashboard_data.to_dict(),
                                 gauge_data=gauge_data,
                                 summary_data=summary_data,
                                 actions_data=actions_data,
                                 health_data=health_data)
            
        except Exception as e:
            logger.error(f"Error loading storage dashboard: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(f"Error loading storage dashboard: {e}", "Error")
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/storage/api/data')
    @login_required
    def storage_api_data():
        """API endpoint for storage data (for AJAX updates)"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            storage_dashboard = AdminStorageDashboard()
            
            # Get current storage data
            dashboard_data = storage_dashboard.get_storage_dashboard_data()
            gauge_data = storage_dashboard.get_storage_gauge_data()
            summary_data = storage_dashboard.get_storage_summary_card_data()
            
            return jsonify({
                'success': True,
                'data': {
                    'dashboard': dashboard_data.to_dict(),
                    'gauge': gauge_data,
                    'summary': summary_data,
                    'timestamp': dashboard_data.last_calculated.isoformat() if dashboard_data.last_calculated else None
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting storage API data: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @bp.route('/storage/refresh', methods=['GET', 'POST'])
    @login_required
    def storage_refresh():
        """Refresh storage calculations (invalidate cache)"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('admin.dashboard'))
        
        # Handle GET requests by redirecting to storage dashboard
        if request.method == 'GET':
            # Send info notification
            from app.services.notification.helpers.notification_helpers import send_info_notification
            send_info_notification("Use the refresh button on the storage dashboard to refresh data.", "Information")
            return redirect(url_for('admin.storage_dashboard'))
        
        # Handle POST requests (actual refresh)
        try:
            storage_dashboard = AdminStorageDashboard()
            
            # Invalidate cache to force recalculation
            storage_dashboard.monitor_service.invalidate_cache()
            
            # Get fresh data
            dashboard_data = storage_dashboard.get_storage_dashboard_data()
            
            # Use the formatted values from the to_dict() method
            dashboard_dict = dashboard_data.to_dict()
            # Send success notification
            from app.services.notification.helpers.notification_helpers import send_success_notification
            send_success_notification(f"Storage data refreshed. Current usage: {dashboard_dict['formatted_usage']} / {dashboard_dict['formatted_limit']}", "Success")
            logger.info(f"Storage data refreshed by admin user {current_user.username}")
            
        except Exception as e:
            logger.error(f"Error refreshing storage data: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(f"Error refreshing storage data: {e}", "Error")
        
        # Redirect back to referring page or storage dashboard
        return redirect(request.referrer or url_for('admin.storage_dashboard'))
    
    @bp.route('/storage/override', methods=['GET', 'POST'])
    @login_required
    def storage_override():
        """Storage limit override management"""
        if not current_user.role == UserRole.ADMIN:
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification("Access denied. Admin privileges required.", "Access Denied")
            return redirect(url_for('admin.dashboard'))
        
        storage_dashboard = AdminStorageDashboard()
        
        # Initialize override system
        config = Config()
        db_manager = DatabaseManager(config)
        override_system = StorageOverrideSystem(db_manager)
        
        if request.method == 'POST':
            try:
                action = request.form.get('action')
                
                if action == 'activate':
                    # Activate storage override
                    duration_hours = int(request.form.get('duration_hours', 1))
                    reason = request.form.get('reason', 'Manual admin override')
                    
                    # Activate the override using the override system
                    override_info = override_system.activate_override(
                        admin_user_id=current_user.id,
                        duration_hours=duration_hours,
                        reason=reason
                    )
                    
                    # Send success notification
                    from app.services.notification.helpers.notification_helpers import send_success_notification
                    send_success_notification(f"Storage override activated for {duration_hours} hours: {reason}", "Success")
                    logger.info(f"Storage override {override_info.id} activated by {current_user.username} for {duration_hours}h: {reason}")
                    
                elif action == 'deactivate':
                    # Deactivate storage override
                    deactivation_reason = request.form.get('deactivation_reason', 'Manual admin deactivation')
                    
                    success = override_system.deactivate_override(
                        admin_user_id=current_user.id,
                        reason=deactivation_reason
                    )
                    
                    if success:
                        # Send success notification
                        from app.services.notification.helpers.notification_helpers import send_success_notification
                        send_success_notification("Storage override deactivated", "Success")
                        logger.info(f"Storage override deactivated by {current_user.username}: {deactivation_reason}")
                    else:
                        # Send warning notification
                        from app.services.notification.helpers.notification_helpers import send_warning_notification
                        send_warning_notification("No active override found to deactivate", "Warning")
                else:
                    # Send error notification
                    from app.services.notification.helpers.notification_helpers import send_error_notification
                    send_error_notification("Invalid override action", "Error")
                    
            except Exception as e:
                # Send error notification
                from app.services.notification.helpers.notification_helpers import send_error_notification
                send_error_notification(f"Override operation error: {e}", "Error")
                logger.error(f"Override operation error for {current_user.username}: {e}")
            
            return redirect(url_for('admin.storage_override'))
        
        # GET request - show override management page
        try:
            dashboard_data = storage_dashboard.get_storage_dashboard_data()
            
            # Get current override status
            active_override = override_system.get_active_override()
            if active_override:
                override_data = {
                    'is_active': True,
                    'id': active_override.id,
                    'remaining_time': active_override.remaining_time,
                    'remaining_time_seconds': active_override.remaining_time.total_seconds() if active_override.remaining_time else 0,
                    'reason': active_override.reason,
                    'activated_by': active_override.admin_username,
                    'activated_at': active_override.activated_at,
                    'expires_at': active_override.expires_at,
                    'duration_hours': active_override.duration_hours,
                    'storage_gb_at_activation': active_override.storage_gb_at_activation,
                    'limit_gb_at_activation': active_override.limit_gb_at_activation
                }
            else:
                override_data = {
                    'is_active': False,
                    'remaining_time': None,
                    'reason': None,
                    'activated_by': None,
                    'activated_at': None
                }
            
            # Get override statistics
            override_stats = override_system.get_override_statistics()
            
            # Get recent override history
            override_history = override_system.get_override_history(limit=10)
            
            return render_template('admin/storage_override.html',
                                 dashboard_data=dashboard_data.to_dict(),
                                 override_data=override_data,
                                 override_stats=override_stats,
                                 override_history=[o.to_dict() for o in override_history])
            
        except Exception as e:
            logger.error(f"Error loading storage override page: {e}")
            # Send error notification
            from app.services.notification.helpers.notification_helpers import send_error_notification
            send_error_notification(f"Error loading storage override page: {e}", "Error")
            return redirect(url_for('admin.storage_dashboard'))
    
    @bp.route('/storage/health')
    @login_required
    def storage_health():
        """Storage system health check endpoint"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            storage_dashboard = AdminStorageDashboard()
            health_data = storage_dashboard.health_check()
            
            return jsonify({
                'success': True,
                'health': health_data,
                'overall_healthy': health_data.get('overall_healthy', False)
            })
            
        except Exception as e:
            logger.error(f"Error getting storage health: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @bp.route('/storage/api/override/status')
    @login_required
    def override_status_api():
        """API endpoint for current override status"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            config = Config()
            db_manager = DatabaseManager(config)
            override_system = StorageOverrideSystem(db_manager)
            
            active_override = override_system.get_active_override()
            
            if active_override:
                return jsonify({
                    'success': True,
                    'is_active': True,
                    'override': active_override.to_dict()
                })
            else:
                return jsonify({
                    'success': True,
                    'is_active': False,
                    'override': None
                })
                
        except Exception as e:
            logger.error(f"Error getting override status: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @bp.route('/storage/api/override/activate', methods=['POST'])
    @login_required
    def activate_override_api():
        """API endpoint for activating storage override"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            duration_hours = data.get('duration_hours', 1)
            reason = data.get('reason', 'API override activation')
            
            config = Config()
            db_manager = DatabaseManager(config)
            override_system = StorageOverrideSystem(db_manager)
            
            override_info = override_system.activate_override(
                admin_user_id=current_user.id,
                duration_hours=duration_hours,
                reason=reason
            )
            
            logger.info(f"Storage override {override_info.id} activated via API by {current_user.username}")
            
            return jsonify({
                'success': True,
                'message': f'Override activated for {duration_hours} hours',
                'override': override_info.to_dict()
            })
            
        except OverrideValidationError as e:
            return jsonify({'success': False, 'error': f'Validation error: {e}'}), 400
        except StorageOverrideSystemError as e:
            return jsonify({'success': False, 'error': f'System error: {e}'}), 500
        except Exception as e:
            logger.error(f"Error activating override via API: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/storage/api/override/deactivate', methods=['POST'])
    @login_required
    def deactivate_override_api():
        """API endpoint for deactivating storage override"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            data = request.get_json() or {}
            reason = data.get('reason', 'API override deactivation')
            
            config = Config()
            db_manager = DatabaseManager(config)
            override_system = StorageOverrideSystem(db_manager)
            
            success = override_system.deactivate_override(
                admin_user_id=current_user.id,
                reason=reason
            )
            
            if success:
                logger.info(f"Storage override deactivated via API by {current_user.username}")
                return jsonify({
                    'success': True,
                    'message': 'Override deactivated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No active override found to deactivate'
                }), 404
                
        except OverrideValidationError as e:
            return jsonify({'success': False, 'error': f'Validation error: {e}'}), 400
        except OverrideNotFoundError as e:
            return jsonify({'success': False, 'error': f'Override not found: {e}'}), 404
        except StorageOverrideSystemError as e:
            return jsonify({'success': False, 'error': f'System error: {e}'}), 500
        except Exception as e:
            logger.error(f"Error deactivating override via API: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/storage/api/override/cleanup', methods=['POST'])
    @login_required
    def cleanup_overrides_api():
        """API endpoint for cleaning up expired overrides"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            config = Config()
            db_manager = DatabaseManager(config)
            override_system = StorageOverrideSystem(db_manager)
            
            cleanup_count = override_system.cleanup_expired_overrides()
            
            logger.info(f"Override cleanup performed by {current_user.username}: {cleanup_count} overrides cleaned up")
            
            return jsonify({
                'success': True,
                'message': f'Cleaned up {cleanup_count} expired override(s)',
                'cleanup_count': cleanup_count
            })
            
        except Exception as e:
            logger.error(f"Error cleaning up overrides via API: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/storage/api/override/statistics')
    @login_required
    def override_statistics_api():
        """API endpoint for override statistics"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            config = Config()
            db_manager = DatabaseManager(config)
            override_system = StorageOverrideSystem(db_manager)
            
            stats = override_system.get_override_statistics()
            
            return jsonify({
                'success': True,
                'statistics': stats
            })
            
        except Exception as e:
            logger.error(f"Error getting override statistics: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500