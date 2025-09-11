from flask import current_app
from flask_login import current_user
from models import PlatformConnection
from app.core.session.middleware.session_middleware import update_session_platform
from app.core.security.core.security_utils import sanitize_for_log

class PlatformService:
    """Service for platform management operations"""
    
    def __init__(self):
        self.db_manager = current_app.config.get('db_manager')
    
    def get_user_platforms(self, include_stats=False):
        """Get platforms for current user"""
        try:
            from app.services.platform.components.platform_identification import identify_user_platform
            
            result = identify_user_platform(
                current_user.id,
                current_app.config.get('redis_platform_manager'),
                self.db_manager,
                include_stats=include_stats
            )
            
            return {
                'platforms': result.user_platforms or [],
                'current_platform': result.current_platform,
                'platform_stats': result.platform_stats or {}
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting user platforms: {sanitize_for_log(str(e))}")
            return {'platforms': [], 'current_platform': None, 'platform_stats': {}}
    
    def switch_platform(self, platform_id):
        """Switch to a different platform"""
        try:
            unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            
            with request_session_manager.session_scope() as db_session:
                platform = db_session.query(PlatformConnection).filter_by(
                    id=platform_id,
                    user_id=current_user.id,
                    is_active=True
                ).first()
                
                if not platform:
                    return False, "Platform not found or access denied"
                
                # Update session platform context
                update_session_platform(platform_id)
                
                current_app.logger.info(f"User {current_user.id} switched to platform {platform_id}")
                return True, f"Switched to platform: {platform.name}"
                
        except Exception as e:
            current_app.logger.error(f"Error switching platform: {sanitize_for_log(str(e))}")
            return False, "Error switching platform"
    
    def get_maintenance_status(self):
        """Get system maintenance status"""
        try:
            from app.services.maintenance.enhanced.enhanced_maintenance_mode_service import EnhancedMaintenanceModeService
            from app.services.maintenance.components.maintenance_response_helper import MaintenanceResponseHelper
            from app.core.configuration.core.configuration_service import ConfigurationService
            
            config_service = ConfigurationService(self.db_manager)
            maintenance_service = EnhancedMaintenanceModeService(config_service, self.db_manager)
            response_helper = MaintenanceResponseHelper()
            
            maintenance_status = maintenance_service.get_maintenance_status()
            return response_helper.create_maintenance_status_dict(maintenance_status)
            
        except Exception as e:
            current_app.logger.error(f"Error getting maintenance status: {str(e)}")
            return None
