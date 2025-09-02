from flask import current_app, redirect, url_for
from security.core.security_utils import sanitize_for_log

class ErrorHandler:
    """Centralized error handling utility"""
    
    @staticmethod
    def handle_error(error, operation_name, redirect_route='index', user_message=None):
        """Standard error handling pattern"""
        current_app.logger.error(f"Error in {operation_name}: {sanitize_for_log(str(error))}")
        
        from notification_helpers import send_error_notification
        message = user_message or f"An error occurred in {operation_name}"
        send_error_notification(message, "Error")
        
        return redirect(url_for(redirect_route))
    
    @staticmethod
    def handle_warning(message, operation_name, redirect_route='index'):
        """Standard warning handling pattern"""
        current_app.logger.warning(f"Warning in {operation_name}: {sanitize_for_log(message)}")
        
        from notification_helpers import send_warning_notification
        send_warning_notification(message, "Warning")
        
        return redirect(url_for(redirect_route))
    
    @staticmethod
    def handle_success(message, operation_name):
        """Standard success handling pattern"""
        current_app.logger.info(f"Success in {operation_name}: {sanitize_for_log(message)}")
        
        from notification_helpers import send_success_notification
        send_success_notification(message, "Success")
