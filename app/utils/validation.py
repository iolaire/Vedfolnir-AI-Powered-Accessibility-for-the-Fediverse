from flask import current_app
from flask_login import current_user
from app.core.session.middleware.session_middleware_v2 import get_current_session_context

class ValidationUtils:
    """Common validation patterns"""
    
    @staticmethod
    def validate_platform_context():
        """Validate platform context exists"""
        context = get_current_session_context()
        if not context or not context.get('platform_connection_id'):
            return False, "No active platform connection found"
        return True, context['platform_connection_id']
    
    @staticmethod
    def validate_user_owns_resource(resource, user_id_field='user_id'):
        """Validate user owns the resource"""
        if not resource:
            return False, "Resource not found"
        
        if getattr(resource, user_id_field) != current_user.id:
            return False, "Access denied"
        
        return True, None
    
    @staticmethod
    def validate_required_fields(data, required_fields):
        """Validate required fields in request data"""
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        return True, None
