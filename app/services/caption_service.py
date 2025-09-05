from flask import current_app
from flask_login import current_user
from models import Image, CaptionGenerationUserSettings
from session_middleware_v2 import get_current_session_context
from security.core.security_utils import sanitize_for_log

class CaptionService:
    """Service for caption generation operations"""
    
    def __init__(self):
        self.db_manager = current_app.config.get('db_manager')
    
    def get_caption_generation_data(self):
        """Get data needed for caption generation page"""
        try:
            from web_caption_generation_service import WebCaptionGenerationService
            
            # Get platform context
            context = get_current_session_context()
            if not context or not context.get('platform_connection_id'):
                return None, "No active platform connection found"
            
            platform_connection_id = context['platform_connection_id']
            
            # Initialize caption service
            caption_service = WebCaptionGenerationService(self.db_manager)
            
            # Get storage status
            storage_status = self._get_storage_status()
            
            # Get active task
            active_task = self._get_active_task(caption_service)
            
            # Get task history
            task_history = self._get_task_history(caption_service)
            
            # Get user settings
            user_settings = self._get_user_settings(platform_connection_id)
            
            return {
                'active_task': active_task,
                'task_history': task_history,
                'user_settings': user_settings,
                'storage_status': storage_status
            }, None
            
        except Exception as e:
            current_app.logger.error(f"Error getting caption generation data: {sanitize_for_log(str(e))}")
            return None, "Error loading caption generation data"
    
    def _get_storage_status(self):
        """Get storage status for template"""
        try:
            from storage_user_notification_system import StorageUserNotificationSystem
            storage_notification_system = StorageUserNotificationSystem()
            return storage_notification_system.get_storage_status_for_template()
        except Exception as e:
            current_app.logger.error(f"Failed to get storage status: {sanitize_for_log(str(e))}")
            return {}
    
    def _get_active_task(self, caption_service):
        """Get user's active task"""
        try:
            return caption_service.task_queue_manager.get_user_active_task(current_user.id)
        except Exception as e:
            current_app.logger.error(f"Failed to get active task: {sanitize_for_log(str(e))}")
            return None
    
    def _get_task_history(self, caption_service):
        """Get user's task history - Fixed: Simplified async pattern"""
        try:
            # Use asyncio.run instead of manual event loop + threading
            task_history = asyncio.run(
                caption_service.get_user_task_history(current_user.id, limit=5)
            )
            return task_history
        except Exception as e:
            current_app.logger.error(f"Failed to get task history: {sanitize_for_log(str(e))}")
            return []
    
    def _get_user_settings(self, platform_connection_id):
        """Get user's caption generation settings"""
        try:
            with self.db_manager.get_session() as session:
                user_settings_record = session.query(CaptionGenerationUserSettings).filter_by(
                    user_id=current_user.id,
                    platform_connection_id=platform_connection_id
                ).first()
                
                if user_settings_record:
                    return user_settings_record.to_settings_dataclass()
                return None
        except Exception as e:
            current_app.logger.error(f"Failed to get user settings: {sanitize_for_log(str(e))}")
            return None
