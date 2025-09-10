from flask import current_app
from flask_login import current_user
from models import Image, CaptionGenerationUserSettings
from app.core.session.middleware.session_middleware_v2 import get_current_session_context
from app.core.security.core.security_utils import sanitize_for_log

class CaptionService:
    """Service for caption generation operations"""
    
    def __init__(self):
        self.db_manager = current_app.config.get('db_manager')
    
    def get_caption_generation_data(self):
        """Get data needed for caption generation page"""
        try:
            from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
            
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
        """Get storage status for template using unified notification system"""
        try:
            from flask import current_user
            from app.services.notification.helpers.notification_helpers import send_storage_notification
            
            # Get storage context from storage monitoring system
            storage_context = self._get_storage_notification_context()
            
            if storage_context and current_user.is_authenticated:
                # Send notification via unified system (replaces StorageUserNotificationSystem)
                if storage_context.is_blocked or storage_context.usage_percentage > 90:
                    send_storage_notification(current_user.id, storage_context)
                
                # Return storage status for template
                return {
                    'is_blocked': storage_context.is_blocked,
                    'should_hide_form': storage_context.should_hide_form,
                    'usage_percentage': storage_context.usage_percentage,
                    'storage_gb': storage_context.storage_gb,
                    'limit_gb': storage_context.limit_gb,
                    'reason': storage_context.reason
                }
            
            return {}
            
        except Exception as e:
            current_app.logger.error(f"Failed to get storage status: {sanitize_for_log(str(e))}")
            return {}
    
    def _get_storage_notification_context(self):
        """Get storage notification context from storage monitoring system"""
        try:
            from app.services.storage.components.storage_user_notification_system import get_storage_notification_context
            return get_storage_notification_context()
        except ImportError:
            # Fallback if storage system not available
            return None
        except Exception as e:
            current_app.logger.error(f"Failed to get storage context: {sanitize_for_log(str(e))}")
            return None
    
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
