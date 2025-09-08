#!/usr/bin/env python3
"""
Pre-Authentication Session Handler

Handles session creation and management for unauthenticated users,
specifically for CSRF token generation and validation.
"""

from typing import Optional, Dict, Any
from flask import session, request, g, current_app
from logging import getLogger
import secrets
import time

logger = getLogger(__name__)

class PreAuthSessionHandler:
    """
    Handles pre-authentication sessions for CSRF tokens
    
    This ensures that even unauthenticated users have a session
    context for CSRF token generation and validation.
    """
    
    def __init__(self, app=None):
        """Initialize pre-auth session handler"""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        
        # Register before_request handler with high priority
        app.before_request_funcs.setdefault(None, []).insert(0, self.ensure_session)
    
    def ensure_session(self):
        """
        Ensure a session exists for CSRF token generation
        
        This runs before every request to guarantee that even
        unauthenticated users have a session for CSRF protection.
        """
        try:
            # Check if we already have a session
            if hasattr(g, 'session_ensured'):
                return
            
            # Mark that we've checked session for this request
            g.session_ensured = True
            
            # For login and other auth routes, ensure session exists
            if self._needs_session():
                self._ensure_flask_session()
                
        except Exception as e:
            logger.error(f"Error ensuring pre-auth session: {e}")
    
    def _needs_session(self) -> bool:
        """
        Check if current request needs a session
        
        Returns:
            True if session is needed for this request
        """
        # Always need session for POST requests (CSRF protection)
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            return True
        
        # Need session for login page (to generate CSRF tokens)
        if request.endpoint in ['user_management.login', 'login']:
            return True
        
        # Need session for any form pages
        form_endpoints = [
            'user_management.register',
            'user_management.forgot_password',
            'user_management.reset_password'
        ]
        if request.endpoint in form_endpoints:
            return True
        
        return False
    
    def _ensure_flask_session(self):
        """
        Ensure Flask session exists and has required data
        """
        try:
            # Access session to trigger creation if needed
            if not session:
                # Session is empty, initialize it
                session['_created'] = time.time()
                session.permanent = True
                logger.debug("Created new pre-auth session")
            
            # Ensure session has a stable ID for CSRF
            if '_csrf_session_id' not in session:
                session['_csrf_session_id'] = self._generate_csrf_session_id()
                logger.debug("Added CSRF session ID to session")
            
            # Update last activity
            session['_last_activity'] = time.time()
            
        except Exception as e:
            logger.error(f"Error ensuring Flask session: {e}")
    
    def _generate_csrf_session_id(self) -> str:
        """
        Generate a stable session ID for CSRF tokens
        
        Returns:
            Secure session ID for CSRF purposes
        """
        return f"csrf_{secrets.token_urlsafe(32)}"
    
    def get_csrf_session_id(self) -> Optional[str]:
        """
        Get the CSRF session ID for the current request
        
        Returns:
            CSRF session ID or None if no session
        """
        try:
            # First, ensure we have a session
            self._ensure_flask_session()
            
            # Get CSRF session ID from Flask session (most reliable)
            csrf_id = session.get('_csrf_session_id')
            if csrf_id:
                return csrf_id
            
            # If no CSRF ID in session, try to get Flask session ID from cookie
            from flask import request
            cookie_name = getattr(current_app, 'session_cookie_name', 
                                current_app.config.get('SESSION_COOKIE_NAME', 'session'))
            flask_sid = request.cookies.get(cookie_name)
            if flask_sid:
                return f"flask_{flask_sid}"
            
            # Fallback: generate temporary ID based on request (but this should be avoided)
            return self._generate_request_based_id()
            
        except Exception as e:
            logger.error(f"Error getting CSRF session ID: {e}")
            return self._generate_request_based_id()
    
    def _generate_request_based_id(self) -> str:
        """
        Generate request-based ID as fallback
        
        Returns:
            Request-based session ID
        """
        try:
            # Use request information to create consistent ID
            ip = request.environ.get('REMOTE_ADDR', 'unknown')
            user_agent = request.environ.get('HTTP_USER_AGENT', 'unknown')
            
            # Create hash of request info
            import hashlib
            request_info = f"{ip}:{user_agent}:{request.endpoint}"
            request_hash = hashlib.sha256(request_info.encode()).hexdigest()[:16]
            
            return f"req_{request_hash}"
            
        except Exception as e:
            logger.error(f"Error generating request-based ID: {e}")
            return f"fallback_{secrets.token_urlsafe(8)}"

# Global instance
pre_auth_handler = PreAuthSessionHandler()

def get_pre_auth_session_id() -> Optional[str]:
    """
    Get pre-authentication session ID for CSRF tokens
    
    Returns:
        Session ID suitable for CSRF token generation
    """
    return pre_auth_handler.get_csrf_session_id()

def ensure_pre_auth_session():
    """
    Ensure pre-authentication session exists
    
    Call this before generating CSRF tokens for unauthenticated users
    """
    pre_auth_handler.ensure_session()
