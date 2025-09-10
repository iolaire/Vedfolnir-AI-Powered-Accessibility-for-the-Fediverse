# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Maintenance Mode Routes

Provides admin interface for maintenance mode control and monitoring.
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import UserRole
# from notification_flash_replacement import send_notification  # Removed - using unified notification system
from app.core.session.error_handling.session_error_handlers import with_session_error_handling

logger = logging.getLogger(__name__)


def register_routes(bp):
    """Register maintenance mode admin routes"""
    
    @bp.route('/maintenance-mode')
    @login_required
    def maintenance_mode_dashboard():
        """Maintenance mode control dashboard"""
        if not current_user.role == UserRole.ADMIN:
            # Send access denied notification via WebSocket instead of flash
            try:
                from app.services.notification.manager.unified_manager import AdminNotificationMessage
                from models import NotificationType, NotificationPriority, NotificationCategory
                
                notification_manager = current_app.config.get('notification_manager')
                if notification_manager:
                    notification = AdminNotificationMessage(
                        id=f"access_denied_{int(datetime.now(timezone.utc).timestamp())}",
                        type=NotificationType.ERROR,
                        title="Access Denied",
                        message="Admin privileges required to access maintenance mode.",
                        user_id=current_user.id,
                        priority=NotificationPriority.HIGH,
                        category=NotificationCategory.ADMIN,
                        admin_only=False
                    )
                    notification_manager.send_user_notification(current_user.id, notification)
            except Exception as e:
                logger.error(f"Error sending access denied notification: {e}")
            
            return redirect(url_for('admin.dashboard'))
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                # Send service unavailable notification via WebSocket instead of flash
                try:
                    from app.services.notification.manager.unified_manager import AdminNotificationMessage
                    from models import NotificationType, NotificationPriority, NotificationCategory
                    
                    notification_manager = current_app.config.get('notification_manager')
                    if notification_manager:
                        notification = AdminNotificationMessage(
                            id=f"dashboard_service_unavailable_{int(datetime.now(timezone.utc).timestamp())}",
                            type=NotificationType.ERROR,
                            title="Service Unavailable",
                            message="Maintenance service is not available at this time.",
                            user_id=current_user.id,
                            priority=NotificationPriority.HIGH,
                            category=NotificationCategory.ADMIN,
                            admin_only=True
                        )
                        notification_manager.send_admin_notification(notification)
                except Exception as e:
                    logger.error(f"Error sending dashboard service unavailable notification: {e}")
                
                return redirect(url_for('admin.dashboard'))
            
            # Get current maintenance status
            status = maintenance_service.get_maintenance_status()
            blocked_operations = maintenance_service.get_blocked_operations()
            service_stats = maintenance_service.get_service_stats()
            
            # Get maintenance history (if available)
            maintenance_history = []
            try:
                maintenance_history = maintenance_service.get_maintenance_history(limit=10)
            except Exception as e:
                logger.warning(f"Could not get maintenance history: {e}")
            
            return render_template('admin/maintenance_mode_dashboard.html',
                                 status=status,
                                 blocked_operations=blocked_operations,
                                 service_stats=service_stats,
                                 maintenance_history=maintenance_history)
        
        except Exception as e:
            logger.error(f"Error loading maintenance mode dashboard: {e}")
            # Send error notification via WebSocket instead of flash
            try:
                from app.services.notification.manager.unified_manager import AdminNotificationMessage
                from models import NotificationType, NotificationPriority, NotificationCategory
                
                notification_manager = current_app.config.get('notification_manager')
                if notification_manager:
                    notification = AdminNotificationMessage(
                        id=f"dashboard_error_{int(datetime.now(timezone.utc).timestamp())}",
                        type=NotificationType.ERROR,
                        title="Dashboard Error",
                        message="Error loading maintenance mode dashboard. Please try again.",
                        user_id=current_user.id,
                        priority=NotificationPriority.HIGH,
                        category=NotificationCategory.ADMIN,
                        admin_only=True
                    )
                    notification_manager.send_admin_notification(notification)
            except Exception as notification_error:
                logger.error(f"Error sending dashboard error notification: {notification_error}")
            
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/api/maintenance-mode/enable', methods=['POST'])
    @login_required
    def enable_maintenance_mode():
        """Enable maintenance mode via API"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                return jsonify({'success': False, 'error': 'Maintenance service not available'}), 500
            
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # Validate required fields
            reason = data.get('reason', '').strip()
            if not reason:
                return jsonify({'success': False, 'error': 'Maintenance reason is required'}), 400
            
            # Get optional fields
            duration = data.get('duration')  # Duration in minutes
            mode_str = data.get('mode', 'normal').lower()
            
            # Validate duration
            if duration is not None:
                try:
                    duration = int(duration)
                    if duration <= 0 or duration > 1440:  # Max 24 hours
                        return jsonify({'success': False, 'error': 'Duration must be between 1 and 1440 minutes'}), 400
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Invalid duration format'}), 400
            
            # Import maintenance mode enum
            from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import MaintenanceMode
            
            # Validate and convert mode
            mode_mapping = {
                'normal': MaintenanceMode.NORMAL,
                'emergency': MaintenanceMode.EMERGENCY,
                'test': MaintenanceMode.TEST
            }
            
            if mode_str not in mode_mapping:
                return jsonify({'success': False, 'error': 'Invalid maintenance mode'}), 400
            
            mode = mode_mapping[mode_str]
            
            # Enable maintenance mode
            success = maintenance_service.enable_maintenance(
                reason=reason,
                duration=duration,
                mode=mode,
                enabled_by=current_user.username
            )
            
            if success:
                # Log the maintenance event
                maintenance_service.log_maintenance_event(
                    event_type='maintenance_enabled',
                    details={
                        'mode': mode.value,
                        'reason': reason,
                        'duration': duration
                    },
                    administrator=current_user.username
                )
                
                # Send unified maintenance notifications
                try:
                    from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler, MaintenanceNotificationData
                    from datetime import timedelta
                    
                    # Get notification manager
                    notification_manager = current_app.config.get('notification_manager')
                    if notification_manager:
                        maintenance_handler = AdminMaintenanceNotificationHandler(
                            notification_manager, current_app.db_manager
                        )
                        
                        # Calculate estimated completion
                        estimated_completion = None
                        if duration:
                            estimated_completion = datetime.now(timezone.utc) + timedelta(minutes=duration)
                        
                        # Create maintenance notification data
                        maintenance_data = MaintenanceNotificationData(
                            operation_type=f"system_maintenance_{mode.value}",
                            operation_id=f"maintenance_{int(datetime.now(timezone.utc).timestamp())}",
                            status="started",
                            estimated_duration=duration,
                            estimated_completion=estimated_completion,
                            affected_operations=['caption_generation', 'platform_operations'],
                            affected_users_count=0,  # Will be calculated by service
                            admin_action_required=False,
                            rollback_available=True
                        )
                        
                        # Send admin notification for maintenance start
                        maintenance_handler.send_maintenance_started_notification(
                            current_user.id, maintenance_data
                        )
                        
                        # Send system pause notification
                        maintenance_handler.send_system_pause_notification(
                            current_user.id, {
                                'reason': reason,
                                'duration': duration,
                                'mode': mode.value,
                                'affected_operations': ['caption_generation', 'platform_operations'],
                                'estimated_completion': estimated_completion.isoformat() if estimated_completion else None
                            }
                        )
                    
                    # Also send notifications to affected users via progress tracker
                    from progress_tracker import ProgressTracker
                    progress_tracker = ProgressTracker(current_app.db_manager)
                    progress_tracker.handle_maintenance_mode_change(True, {
                        'reason': reason,
                        'estimated_duration': duration,
                        'mode': mode.value,
                        'affects_functionality': ['caption_generation'],
                        'enabled_by': current_user.username
                    })
                except Exception as e:
                    logger.error(f"Error sending maintenance notifications: {e}")
                
                # Get updated status
                status = maintenance_service.get_maintenance_status()
                
                return jsonify({
                    'success': True,
                    'message': f'Maintenance mode enabled successfully ({mode.value})',
                    'status': {
                        'is_active': status.is_active,
                        'mode': status.mode.value,
                        'reason': status.reason,
                        'estimated_duration': status.estimated_duration,
                        'started_at': status.started_at.isoformat() if status.started_at else None,
                        'estimated_completion': status.estimated_completion.isoformat() if status.estimated_completion else None
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to enable maintenance mode'}), 500
        
        except Exception as e:
            logger.error(f"Error enabling maintenance mode: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/maintenance-mode/disable', methods=['POST'])
    @login_required
    def disable_maintenance_mode():
        """Disable maintenance mode via API"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                return jsonify({'success': False, 'error': 'Maintenance service not available'}), 500
            
            # Disable maintenance mode
            success = maintenance_service.disable_maintenance(disabled_by=current_user.username)
            
            if success:
                # Log the maintenance event
                maintenance_service.log_maintenance_event(
                    event_type='maintenance_disabled',
                    details={},
                    administrator=current_user.username
                )
                
                # Send unified maintenance completion notifications
                try:
                    from admin_maintenance_notification_handler import AdminMaintenanceNotificationHandler
                    
                    # Get notification manager
                    notification_manager = current_app.config.get('notification_manager')
                    if notification_manager:
                        maintenance_handler = AdminMaintenanceNotificationHandler(
                            notification_manager, current_app.db_manager
                        )
                        
                        # Send system resume notification to admin
                        maintenance_handler.send_system_resume_notification(
                            current_user.id, {
                                'maintenance_duration': 'Completed',
                                'completed_operations': ['system_maintenance'],
                                'restored_functionality': ['caption_generation', 'platform_operations']
                            }
                        )
                    
                    # Also send notifications to affected users via progress tracker
                    from progress_tracker import ProgressTracker
                    progress_tracker = ProgressTracker(current_app.db_manager)
                    progress_tracker.handle_maintenance_mode_change(False, {
                        'reason': 'Maintenance completed',
                        'disabled_by': current_user.username
                    })
                except Exception as e:
                    logger.error(f"Error sending maintenance completion notifications: {e}")
                
                return jsonify({
                    'success': True,
                    'message': 'Maintenance mode disabled successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to disable maintenance mode'}), 500
        
        except Exception as e:
            logger.error(f"Error disabling maintenance mode: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/maintenance-mode/status')
    @login_required
    def get_maintenance_status():
        """Get current maintenance status via API"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                return jsonify({'success': False, 'error': 'Maintenance service not available'}), 500
            
            # Get status
            status = maintenance_service.get_maintenance_status()
            blocked_operations = maintenance_service.get_blocked_operations()
            service_stats = maintenance_service.get_service_stats()
            
            return jsonify({
                'success': True,
                'status': {
                    'is_active': status.is_active,
                    'mode': status.mode.value,
                    'reason': status.reason,
                    'estimated_duration': status.estimated_duration,
                    'started_at': status.started_at.isoformat() if status.started_at else None,
                    'estimated_completion': status.estimated_completion.isoformat() if status.estimated_completion else None,
                    'enabled_by': status.enabled_by,
                    'active_jobs_count': status.active_jobs_count,
                    'invalidated_sessions': status.invalidated_sessions,
                    'test_mode': status.test_mode
                },
                'blocked_operations': blocked_operations,
                'service_stats': service_stats
            })
        
        except Exception as e:
            logger.error(f"Error getting maintenance status: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/maintenance-mode/validate', methods=['POST'])
    @login_required
    def validate_maintenance_config():
        """Validate maintenance mode configuration using comprehensive validator"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # Get maintenance service for context validation
            maintenance_service = current_app.config.get('maintenance_service')
            
            # Import and create validator
            from app.services.maintenance.components.maintenance_configuration_validator import MaintenanceConfigurationValidator
            validator = MaintenanceConfigurationValidator(maintenance_service=maintenance_service)
            
            # Perform comprehensive validation
            result = validator.validate_configuration(data)
            
            # Convert validation messages to simple lists for frontend
            errors = [msg.message for msg in result.messages if msg.severity.value == 'error']
            warnings = [msg.message for msg in result.messages if msg.severity.value == 'warning']
            info = [msg.message for msg in result.messages if msg.severity.value == 'info']
            
            # Get validation statistics
            stats = validator.get_validation_statistics()
            
            return jsonify({
                'success': True,
                'valid': result.is_valid,
                'errors': errors,
                'warnings': warnings,
                'info': info,
                'validation_details': {
                    'errors_count': result.errors_count,
                    'warnings_count': result.warnings_count,
                    'info_count': result.info_count,
                    'validated_config': result.validated_config
                },
                'validation_stats': stats
            })
        
        except Exception as e:
            logger.error(f"Error validating maintenance config: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/maintenance-monitoring')
    @login_required
    def maintenance_monitoring_dashboard():
        """Maintenance monitoring dashboard with real-time status"""
        if not current_user.role == UserRole.ADMIN:
            # Send access denied notification via WebSocket instead of flash
            try:
                from app.services.notification.manager.unified_manager import AdminNotificationMessage
                from models import NotificationType, NotificationPriority, NotificationCategory
                
                notification_manager = current_app.config.get('notification_manager')
                if notification_manager:
                    notification = AdminNotificationMessage(
                        id=f"monitoring_access_denied_{int(datetime.now(timezone.utc).timestamp())}",
                        type=NotificationType.ERROR,
                        title="Access Denied",
                        message="Admin privileges required to access maintenance monitoring.",
                        user_id=current_user.id,
                        priority=NotificationPriority.HIGH,
                        category=NotificationCategory.ADMIN,
                        admin_only=False
                    )
                    notification_manager.send_user_notification(current_user.id, notification)
            except Exception as e:
                logger.error(f"Error sending monitoring access denied notification: {e}")
            
            return redirect(url_for('admin.dashboard'))
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                # Send service unavailable notification via WebSocket instead of flash
                try:
                    from app.services.notification.manager.unified_manager import AdminNotificationMessage
                    from models import NotificationType, NotificationPriority, NotificationCategory
                    
                    notification_manager = current_app.config.get('notification_manager')
                    if notification_manager:
                        notification = AdminNotificationMessage(
                            id=f"monitoring_service_unavailable_{int(datetime.now(timezone.utc).timestamp())}",
                            type=NotificationType.ERROR,
                            title="Service Unavailable",
                            message="Maintenance service is not available for monitoring.",
                            user_id=current_user.id,
                            priority=NotificationPriority.HIGH,
                            category=NotificationCategory.ADMIN,
                            admin_only=True
                        )
                        notification_manager.send_admin_notification(notification)
                except Exception as e:
                    logger.error(f"Error sending monitoring service unavailable notification: {e}")
                
                return redirect(url_for('admin.dashboard'))
            
            # Collect monitoring data
            monitoring_data = _collect_monitoring_data(maintenance_service)
            
            return render_template('admin/maintenance_monitoring_dashboard.html',
                                 monitoring_data=monitoring_data)
        
        except Exception as e:
            logger.error(f"Error loading maintenance monitoring dashboard: {e}")
            # Send error notification via WebSocket instead of flash
            try:
                from app.services.notification.manager.unified_manager import AdminNotificationMessage
                from models import NotificationType, NotificationPriority, NotificationCategory
                
                notification_manager = current_app.config.get('notification_manager')
                if notification_manager:
                    notification = AdminNotificationMessage(
                        id=f"monitoring_dashboard_error_{int(datetime.now(timezone.utc).timestamp())}",
                        type=NotificationType.ERROR,
                        title="Dashboard Error",
                        message="Error loading maintenance monitoring dashboard. Please try again.",
                        user_id=current_user.id,
                        priority=NotificationPriority.HIGH,
                        category=NotificationCategory.ADMIN,
                        admin_only=True
                    )
                    notification_manager.send_admin_notification(notification)
            except Exception as notification_error:
                logger.error(f"Error sending monitoring dashboard error notification: {notification_error}")
            
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/api/maintenance-mode/monitoring')
    @login_required
    def get_maintenance_monitoring_data():
        """Get maintenance monitoring data via API"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                return jsonify({'success': False, 'error': 'Maintenance service not available'}), 500
            
            # Collect monitoring data
            monitoring_data = _collect_monitoring_data(maintenance_service)
            
            return jsonify({
                'success': True,
                'monitoring_data': monitoring_data
            })
        
        except Exception as e:
            logger.error(f"Error getting maintenance monitoring data: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/maintenance-mode/monitoring/export')
    @login_required
    def export_maintenance_monitoring_report():
        """Export maintenance monitoring report"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                return jsonify({'success': False, 'error': 'Maintenance service not available'}), 500
            
            # Create comprehensive report
            report = maintenance_service.create_maintenance_report()
            
            # Add monitoring-specific data
            monitoring_data = _collect_monitoring_data(maintenance_service)
            report['monitoring_data'] = monitoring_data
            report['export_timestamp'] = datetime.now(timezone.utc).isoformat()
            report['exported_by'] = current_user.username
            
            return jsonify(report)
        
        except Exception as e:
            logger.error(f"Error exporting maintenance monitoring report: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/maintenance-mode/progress/<operation_id>')
    @login_required
    def get_maintenance_progress(operation_id):
        """Get real-time progress for a maintenance operation"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get progress handler from app config
            progress_handler = current_app.config.get('maintenance_progress_handler')
            if not progress_handler:
                return jsonify({'success': False, 'error': 'Progress handler not available'}), 500
            
            # Get active operations
            active_operations = progress_handler.get_active_operations()
            
            if operation_id not in active_operations:
                return jsonify({'success': False, 'error': 'Operation not found'}), 404
            
            operation_info = active_operations[operation_id]
            
            return jsonify({
                'success': True,
                'operation': {
                    'operation_id': operation_id,
                    'operation_type': operation_info['operation_type'],
                    'progress_percentage': operation_info.get('progress_percentage', 0),
                    'current_step': operation_info.get('current_step', 0),
                    'total_steps': operation_info.get('total_steps'),
                    'started_at': operation_info['started_at'].isoformat(),
                    'last_update': operation_info['last_update'].isoformat(),
                    'status': operation_info['status']
                }
            })
        
        except Exception as e:
            logger.error(f"Error getting maintenance progress: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/maintenance-mode/operations/active')
    @login_required
    def get_active_maintenance_operations():
        """Get all active maintenance operations"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get progress handler from app config
            progress_handler = current_app.config.get('maintenance_progress_handler')
            if not progress_handler:
                return jsonify({'success': False, 'error': 'Progress handler not available'}), 500
            
            # Get active operations
            active_operations = progress_handler.get_active_operations()
            
            # Format operations for response
            operations = []
            for operation_id, operation_info in active_operations.items():
                operations.append({
                    'operation_id': operation_id,
                    'operation_type': operation_info['operation_type'],
                    'progress_percentage': operation_info.get('progress_percentage', 0),
                    'current_step': operation_info.get('current_step', 0),
                    'total_steps': operation_info.get('total_steps'),
                    'started_at': operation_info['started_at'].isoformat(),
                    'last_update': operation_info['last_update'].isoformat(),
                    'status': operation_info['status'],
                    'admin_user_id': operation_info['admin_user_id']
                })
            
            return jsonify({
                'success': True,
                'operations': operations,
                'total_count': len(operations)
            })
        
        except Exception as e:
            logger.error(f"Error getting active maintenance operations: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/api/maintenance-mode/operations/<operation_id>/cancel', methods=['POST'])
    @login_required
    def cancel_maintenance_operation(operation_id):
        """Cancel an active maintenance operation"""
        if not current_user.role == UserRole.ADMIN:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        try:
            # Get request data
            data = request.get_json() or {}
            cancellation_reason = data.get('reason', 'Operation cancelled by administrator')
            
            # Get progress handler from app config
            progress_handler = current_app.config.get('maintenance_progress_handler')
            if not progress_handler:
                return jsonify({'success': False, 'error': 'Progress handler not available'}), 500
            
            # Cancel the operation
            success = progress_handler.cancel_operation(operation_id, cancellation_reason)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Operation {operation_id} cancelled successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to cancel operation'}), 500
        
        except Exception as e:
            logger.error(f"Error cancelling maintenance operation: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


def _collect_monitoring_data(maintenance_service):
    """Collect comprehensive monitoring data"""
    try:
        # Get current status
        status = maintenance_service.get_maintenance_status()
        blocked_operations = maintenance_service.get_blocked_operations()
        service_stats = maintenance_service.get_service_stats()
        
        # Get maintenance history
        maintenance_history = []
        try:
            maintenance_history = maintenance_service.get_maintenance_history(limit=20)
        except Exception as e:
            logger.warning(f"Could not get maintenance history: {e}")
        
        # Calculate impact metrics
        impact_percentage = _calculate_impact_percentage(status, blocked_operations)
        affected_users_count = _get_affected_users_count(status)
        blocked_requests_count = _get_blocked_requests_count(service_stats)
        
        # Get active sessions (mock data for now)
        active_sessions = _get_active_sessions_data()
        
        # Performance metrics (mock data for now)
        performance_metrics = {
            'avg_response_time': 45,
            'uptime_percentage': 99.8,
            'total_requests': 15420
        }
        
        return {
            'current_status': status,
            'blocked_operations': blocked_operations,
            'blocked_operations_count': len(blocked_operations),
            'active_jobs_count': status.active_jobs_count,
            'invalidated_sessions_count': status.invalidated_sessions,
            'impact_percentage': impact_percentage,
            'affected_users_count': affected_users_count,
            'blocked_requests_count': blocked_requests_count,
            'active_sessions': active_sessions,
            'maintenance_history': maintenance_history,
            'statistics': service_stats.get('statistics', {}),
            'performance': performance_metrics
        }
    
    except Exception as e:
        logger.error(f"Error collecting monitoring data: {e}")
        # Return safe defaults
        return {
            'current_status': {
                'is_active': False,
                'mode': 'normal',
                'reason': None,
                'test_mode': False
            },
            'blocked_operations': [],
            'blocked_operations_count': 0,
            'active_jobs_count': 0,
            'invalidated_sessions_count': 0,
            'impact_percentage': 0,
            'affected_users_count': 0,
            'blocked_requests_count': 0,
            'active_sessions': [],
            'maintenance_history': [],
            'statistics': {},
            'performance': {
                'avg_response_time': 0,
                'uptime_percentage': 100,
                'total_requests': 0
            }
        }


def _calculate_impact_percentage(status, blocked_operations):
    """Calculate system impact percentage"""
    if not status.is_active:
        return 0
    
    # Base impact based on mode
    base_impact = {
        'normal': 30,
        'emergency': 90,
        'test': 5
    }.get(status.mode.value if hasattr(status.mode, 'value') else str(status.mode), 30)
    
    # Additional impact based on blocked operations
    operation_impact = min(len(blocked_operations) * 10, 50)
    
    # Additional impact based on active jobs
    job_impact = min(status.active_jobs_count * 5, 20)
    
    total_impact = min(base_impact + operation_impact + job_impact, 100)
    return total_impact


def _get_affected_users_count(status):
    """Get count of affected users"""
    if not status.is_active:
        return 0
    
    # In a real implementation, this would query the database
    # For now, return a calculated estimate
    base_users = 10 if status.mode.value == 'emergency' else 5
    return base_users + status.invalidated_sessions


def _get_blocked_requests_count(service_stats):
    """Get count of blocked requests"""
    if service_stats and 'statistics' in service_stats:
        return service_stats['statistics'].get('blocked_operations', 0)
    return 0


def _get_active_sessions_data():
    """Get active sessions data (mock implementation)"""
    # In a real implementation, this would query the session manager
    return [
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'is_admin': True,
            'is_invalidated': False,
            'platform_name': 'System Admin',
            'last_activity': '2 minutes ago'
        },
        {
            'username': 'user1',
            'email': 'user1@example.com',
            'is_admin': False,
            'is_invalidated': True,
            'platform_name': 'Mastodon Instance',
            'last_activity': '5 minutes ago'
        }
    ]