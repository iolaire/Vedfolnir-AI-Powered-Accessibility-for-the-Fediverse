# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Manager Compatibility Layer

This module provides backward compatibility for legacy session_manager imports
while redirecting to the unified session management system.

DEPRECATED: This module is for migration purposes only. Use unified_session_manager directly.

Usage:
    # Legacy code (deprecated)
    from session_manager import SessionManager, get_current_platform_context
    
    # New code (recommended)
    from unified_session_manager import UnifiedSessionManager, get_current_platform_context
"""

import warnings
from logging import getLogger

logger = getLogger(__name__)

# Issue deprecation warning
warnings.warn(
    "session_manager is deprecated. Use unified_session_manager instead. "
    "This compatibility layer will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Import everything from unified_session_manager
try:
    from unified_session_manager import (
        UnifiedSessionManager,
        SessionValidationError,
        SessionExpiredError,
        SessionNotFoundError,
        SessionDatabaseError,
        get_current_platform_context,
        get_current_platform,
        get_current_user_from_context,
        switch_platform_context
    )
    
    # Provide compatibility alias
    SessionManager = UnifiedSessionManager
    
    # Log the compatibility usage
    logger.warning("Using deprecated session_manager compatibility layer. Please migrate to unified_session_manager.")
    
except ImportError as e:
    logger.error(f"Failed to import from unified_session_manager: {e}")
    raise ImportError(
        "unified_session_manager is not available. "
        "Please ensure unified_session_manager.py exists and is properly configured."
    ) from e

# Legacy middleware class for backward compatibility
class PlatformContextMiddleware:
    """
    Legacy middleware class - redirects to DatabaseSessionMiddleware
    
    DEPRECATED: Use DatabaseSessionMiddleware directly
    """
    
    def __init__(self, app, session_manager):
        warnings.warn(
            "PlatformContextMiddleware is deprecated. Use DatabaseSessionMiddleware instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Try to initialize the new middleware
        try:
            from database_session_middleware import DatabaseSessionMiddleware
            from session_cookie_manager import get_session_cookie_manager
            
            # Get or create session cookie manager
            cookie_manager = get_session_cookie_manager()
            
            # Initialize the new middleware
            self.middleware = DatabaseSessionMiddleware(app, session_manager, cookie_manager)
            logger.warning("PlatformContextMiddleware redirected to DatabaseSessionMiddleware")
            
        except ImportError as e:
            logger.error(f"Could not initialize DatabaseSessionMiddleware: {e}")
            # Fallback to basic initialization
            self.app = app
            self.session_manager = session_manager
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        # Basic fallback implementation
        logger.warning("Using fallback PlatformContextMiddleware implementation")
        
        @app.before_request
        def before_request():
            from flask import g
            g.session_manager = self.session_manager
        
        @app.after_request
        def after_request(response):
            return response

# Re-export all the important symbols
__all__ = [
    'SessionManager',  # Alias for UnifiedSessionManager
    'UnifiedSessionManager',
    'SessionValidationError',
    'SessionExpiredError', 
    'SessionNotFoundError',
    'SessionDatabaseError',
    'get_current_platform_context',
    'get_current_platform',
    'get_current_user_from_context',
    'switch_platform_context',
    'PlatformContextMiddleware'  # Legacy middleware
]

# Module-level deprecation notice
def __getattr__(name):
    """Handle any missing attributes with helpful error messages"""
    if name in __all__:
        # This shouldn't happen, but just in case
        return globals()[name]
    
    # Provide helpful error for common legacy patterns
    legacy_mappings = {
        'create_user_session': 'create_session',
        'get_user_session': 'get_session_context',
        'validate_user_session': 'validate_session',
        'cleanup_user_session': 'destroy_session'
    }
    
    if name in legacy_mappings:
        new_name = legacy_mappings[name]
        raise AttributeError(
            f"'{name}' has been renamed to '{new_name}' in UnifiedSessionManager. "
            f"Please update your code to use unified_session_manager.UnifiedSessionManager.{new_name}()"
        )
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Provide migration guidance
def get_migration_help():
    """Get help text for migrating from legacy session_manager"""
    return """
    Session Manager Migration Guide
    ==============================
    
    The legacy session_manager has been replaced with unified_session_manager.
    
    Migration steps:
    1. Replace imports:
       OLD: from session_manager import SessionManager
       NEW: from unified_session_manager import UnifiedSessionManager
    
    2. Update class names:
       OLD: SessionManager(db_manager)
       NEW: UnifiedSessionManager(db_manager)
    
    3. Update method calls (most remain the same):
       - create_session() - same interface
       - get_session_context() - same interface  
       - validate_session() - same interface
       - destroy_session() - same interface
    
    4. Platform context functions remain the same:
       - get_current_platform_context()
       - get_current_platform()
       - get_current_user_from_context()
       - switch_platform_context()
    
    For detailed migration instructions, see:
    SESSION_MANAGER_MIGRATION_INSTRUCTIONS.md
    """

# Print migration help if this module is run directly
if __name__ == '__main__':
    print(get_migration_help())
