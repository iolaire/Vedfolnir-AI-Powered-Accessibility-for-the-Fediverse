# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Admin Maintenance Mode Routes

Provides admin interface for maintenance mode control and monitoring.
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import UserRole
from session_error_handlers import with_session_error_handling

logger = logging.getLogger(__name__)


def register_routes(bp):
    """Register maintenance mode admin routes"""
    
    @bp.route('/maintenance-mode')
    @login_required
    @with_session_error_handling
    def maintenance_mode_dashboard():
        """Maintenance mode control dashboard"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('admin.dashboard'))
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                flash('Maintenance service not available', 'error')
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
            flash('Error loading maintenance mode dashboard', 'error')
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/api/maintenance-mode/enable', methods=['POST'])
    @login_required
    @with_session_error_handling
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
            from enhanced_maintenance_mode_service import MaintenanceMode
            
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
    @with_session_error_handling
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
    @with_session_error_handling
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
    @with_session_error_handling
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
            from maintenance_configuration_validator import MaintenanceConfigurationValidator
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
    @with_session_error_handling
    def maintenance_monitoring_dashboard():
        """Maintenance monitoring dashboard with real-time status"""
        if not current_user.role == UserRole.ADMIN:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('admin.dashboard'))
        
        try:
            # Get maintenance service
            maintenance_service = current_app.config.get('maintenance_service')
            if not maintenance_service:
                flash('Maintenance service not available', 'error')
                return redirect(url_for('admin.dashboard'))
            
            # Collect monitoring data
            monitoring_data = _collect_monitoring_data(maintenance_service)
            
            return render_template('admin/maintenance_monitoring_dashboard.html',
                                 monitoring_data=monitoring_data)
        
        except Exception as e:
            logger.error(f"Error loading maintenance monitoring dashboard: {e}")
            flash('Error loading maintenance monitoring dashboard', 'error')
            return redirect(url_for('admin.dashboard'))
    
    @bp.route('/api/maintenance-mode/monitoring')
    @login_required
    @with_session_error_handling
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
    @with_session_error_handling
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