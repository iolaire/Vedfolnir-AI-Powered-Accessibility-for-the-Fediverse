# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Token Manager

Centralized CSRF token generation, validation, and management system.
Provides secure token handling with entropy validation, session binding,
and expiration management.
"""

import hashlib
import hmac
import secrets
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from flask import request, current_app
import logging

logger = logging.getLogger(__name__)

class CSRFTokenManager:
    """Centralized CSRF token management system"""
    
    def __init__(self, secret_key: Optional[str] = None, token_lifetime: int = 3600):
        """Initialize CSRF token manager
        
        Args:
            secret_key: Secret key for token signing (uses Flask secret key if None)
            token_lifetime: Token lifetime in seconds (default: 1 hour)
        """
        self.secret_key = secret_key
        self.token_lifetime = token_lifetime
        self.min_entropy_bits = 128  # Minimum entropy requirement
        
    def generate_token(self, session_id: Optional[str] = None) -> str:
        """Generate a secure CSRF token
        
        Args:
            session_id: Session identifier (uses current session if None)
            
        Returns:
            Secure CSRF token string
        """
        try:
            # Get session ID
            if session_id is None:
                session_id = self._get_current_session_id()
            
            # Generate random token with sufficient entropy
            random_bytes = secrets.token_bytes(32)  # 256 bits of entropy
            timestamp = int(time.time())
            
            # Create token payload
            payload = f"{session_id}:{timestamp}:{random_bytes.hex()}"
            
            # Sign the token
            signature = self._sign_token(payload)
            token = f"{payload}:{signature}"
            
            logger.debug(f"Generated CSRF token for session {session_id[:8]}...")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate CSRF token: {e}")
            raise CSRFTokenError(f"Token generation failed: {e}")
    
    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """Validate a CSRF token
        
        Args:
            token: CSRF token to validate
            session_id: Session identifier (uses current session if None)
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            if not token:
                logger.warning("Empty CSRF token provided for validation")
                return False
            
            # Get session ID
            if session_id is None:
                session_id = self._get_current_session_id()
            
            # Parse token
            parts = token.split(':')
            if len(parts) != 4:
                logger.warning(f"Invalid CSRF token format: expected 4 parts, got {len(parts)}")
                return False
            
            token_session_id, timestamp_str, random_hex, signature = parts
            
            # Verify session ID matches (Redis session or request-based)
            current_session_id = self._get_current_session_id()
            if token_session_id != current_session_id:
                # For unauthenticated requests, allow request-based ID matching
                request_based_id = self._generate_request_based_id()
                if token_session_id != request_based_id:
                    logger.warning(f"CSRF token session mismatch: token={token_session_id[:8]}..., current={current_session_id[:8]}..., request_based={request_based_id[:8]}...")
                    return False
                else:
                    logger.debug("CSRF token validated using request-based session ID")
            
            # Verify signature
            payload = f"{token_session_id}:{timestamp_str}:{random_hex}"
            expected_signature = self._sign_token(payload)
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("CSRF token signature verification failed")
                return False
            
            # Check expiration
            try:
                timestamp = int(timestamp_str)
                if self.is_token_expired_by_timestamp(timestamp):
                    logger.warning(f"CSRF token expired: {timestamp}")
                    return False
            except ValueError:
                logger.warning(f"Invalid timestamp in CSRF token: {timestamp_str}")
                return False
            
            # Validate entropy
            try:
                random_bytes = bytes.fromhex(random_hex)
                if not self._validate_token_entropy(random_bytes):
                    logger.warning("CSRF token failed entropy validation")
                    return False
            except ValueError:
                logger.warning(f"Invalid random hex in CSRF token: {random_hex}")
                return False
            
            logger.debug(f"CSRF token validation successful for session {session_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"CSRF token validation error: {e}")
            return False
    
    def is_token_expired(self, token: str) -> bool:
        """Check if a CSRF token is expired
        
        Args:
            token: CSRF token to check
            
        Returns:
            True if token is expired, False otherwise
        """
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return True
            
            timestamp_str = parts[1]
            timestamp = int(timestamp_str)
            return self.is_token_expired_by_timestamp(timestamp)
            
        except (ValueError, IndexError):
            return True
    
    def is_token_expired_by_timestamp(self, timestamp: int) -> bool:
        """Check if a timestamp is expired
        
        Args:
            timestamp: Unix timestamp to check
            
        Returns:
            True if timestamp is expired, False otherwise
        """
        current_time = int(time.time())
        return (current_time - timestamp) > self.token_lifetime
    
    def refresh_token(self, session_id: Optional[str] = None) -> str:
        """Generate a new CSRF token (refresh)
        
        Args:
            session_id: Session identifier (uses current session if None)
            
        Returns:
            New CSRF token
        """
        logger.debug("Refreshing CSRF token")
        return self.generate_token(session_id)
    
    def extract_token_info(self, token: str) -> Dict[str, Any]:
        """Extract information from a CSRF token for debugging
        
        Args:
            token: CSRF token to analyze
            
        Returns:
            Dictionary with token information
        """
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return {'error': 'Invalid token format'}
            
            session_id, timestamp_str, random_hex, signature = parts
            
            try:
                timestamp = int(timestamp_str)
                created_at = datetime.fromtimestamp(timestamp)
                expires_at = created_at + timedelta(seconds=self.token_lifetime)
                is_expired = self.is_token_expired_by_timestamp(timestamp)
            except ValueError:
                created_at = None
                expires_at = None
                is_expired = True
            
            return {
                'session_id': session_id[:8] + '...' if len(session_id) > 8 else session_id,
                'created_at': created_at.isoformat() if created_at else 'Invalid',
                'expires_at': expires_at.isoformat() if expires_at else 'Invalid',
                'is_expired': is_expired,
                'entropy_bits': len(random_hex) * 4 if random_hex else 0,  # Hex chars = 4 bits each
                'signature_valid': self._verify_token_signature(token)
            }
            
        except Exception as e:
            return {'error': f'Failed to extract token info: {e}'}
    
    def _get_current_session_id(self) -> str:
        """Get current session ID for CSRF tokens
        
        Returns:
            Session ID suitable for CSRF token generation/validation
        """
        try:
            # First try Redis session (for authenticated users)
            from app.core.session.middleware.session_middleware_v2 import get_current_session_id
            redis_session_id = get_current_session_id()
            
            if redis_session_id and not redis_session_id.startswith('.eJ') and not redis_session_id.startswith('eyJ'):
                return redis_session_id
            
            # For unauthenticated users, use Flask session cookie ID
            from flask import request, current_app
            cookie_name = getattr(current_app, 'session_cookie_name', 
                                current_app.config.get('SESSION_COOKIE_NAME', 'session'))
            flask_session_id = request.cookies.get(cookie_name)
            
            if flask_session_id:
                # Use the Flask session cookie ID directly (without prefix for consistency)
                return flask_session_id
            
            # No session available - generate request-based ID
            logger.debug("No session ID available, using request-based ID for CSRF token")
            return self._generate_request_based_id()
            
        except Exception as e:
            logger.error(f"Failed to get session ID for CSRF: {e}")
            return self._generate_request_based_id()
    
    def _generate_request_based_id(self) -> str:
        """Generate a request-based session ID as fallback
        
        Returns:
            Request-based session identifier
        """
        try:
            # Use request information to generate a consistent ID
            request_info = f"{request.remote_addr}:{request.headers.get('User-Agent', '')}"
            return hashlib.sha256(request_info.encode()).hexdigest()[:32]
        except Exception:
            # Ultimate fallback
            return secrets.token_hex(16)
    
    def _sign_token(self, payload: str) -> str:
        """Sign a token payload
        
        Args:
            payload: Token payload to sign
            
        Returns:
            Token signature
        """
        secret = self._get_secret_key()
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _verify_token_signature(self, token: str) -> bool:
        """Verify token signature
        
        Args:
            token: Token to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return False
            
            payload = ':'.join(parts[:3])
            signature = parts[3]
            expected_signature = self._sign_token(payload)
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False
    
    def _get_secret_key(self) -> str:
        """Get secret key for token signing
        
        Returns:
            Secret key string
        """
        if self.secret_key:
            return self.secret_key
        
        try:
            return current_app.secret_key
        except RuntimeError:
            logger.warning("No Flask app context, using fallback secret key")
            return "fallback-secret-key-for-testing"
    
    def _validate_token_entropy(self, random_bytes: bytes) -> bool:
        """Validate that token has sufficient entropy
        
        Args:
            random_bytes: Random bytes from token
            
        Returns:
            True if entropy is sufficient, False otherwise
        """
        # Check minimum length (32 bytes = 256 bits)
        if len(random_bytes) < 32:
            return False
        
        # Simple entropy check - ensure not all bytes are the same
        if len(set(random_bytes)) < 16:  # At least 16 different byte values
            return False
        
        return True

class CSRFTokenError(Exception):
    """Exception raised for CSRF token errors"""
    pass

class CSRFValidationContext:
    """Context information for CSRF validation"""
    
    def __init__(self, request_method: str, endpoint: str, user_id: Optional[int] = None):
        """Initialize validation context
        
        Args:
            request_method: HTTP request method
            endpoint: Request endpoint
            user_id: User ID if available
        """
        self.request_method = request_method
        self.endpoint = endpoint
        self.user_id = user_id
        self.session_id = self._get_session_id()
        self.timestamp = datetime.now()
        self.validation_result = False
        self.error_details: Optional[str] = None
        self.token_source: Optional[str] = None  # 'form', 'header', 'meta'
    
    def _get_session_id(self) -> str:
        """Get session ID for context"""
        try:
            # Try Redis session first
            from app.core.session.middleware.session_middleware_v2 import get_current_session_id
            redis_session_id = get_current_session_id()
            if redis_session_id and not redis_session_id.startswith('.eJ') and not redis_session_id.startswith('eyJ'):
                return redis_session_id
            
            # Fallback to Flask session cookie (without prefix for consistency)
            from flask import request, current_app
            cookie_name = getattr(current_app, 'session_cookie_name', 
                                current_app.config.get('SESSION_COOKIE_NAME', 'session'))
            flask_session_id = request.cookies.get(cookie_name)
            if flask_session_id:
                return flask_session_id
            
            return 'no-session'
        except Exception:
            return 'unknown-session'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary
        
        Returns:
            Dictionary representation of context
        """
        return {
            'request_method': self.request_method,
            'endpoint': self.endpoint,
            'user_id': self.user_id,
            'session_id': self.session_id[:8] + '...' if len(self.session_id) > 8 else self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'validation_result': self.validation_result,
            'error_details': self.error_details,
            'token_source': self.token_source
        }

# Global CSRF token manager instance
_csrf_token_manager: Optional[CSRFTokenManager] = None

def get_csrf_token_manager() -> CSRFTokenManager:
    """Get the global CSRF token manager instance
    
    Returns:
        CSRFTokenManager instance
    """
    global _csrf_token_manager
    if _csrf_token_manager is None:
        _csrf_token_manager = CSRFTokenManager()
    return _csrf_token_manager

def initialize_csrf_token_manager(app) -> CSRFTokenManager:
    """Initialize CSRF token manager for Flask app
    
    Args:
        app: Flask application instance
        
    Returns:
        Initialized CSRFTokenManager
    """
    global _csrf_token_manager
    
    # Check if already initialized to prevent duplicate initialization
    if _csrf_token_manager is not None:
        return _csrf_token_manager
    
    # Get configuration from app
    token_lifetime = app.config.get('CSRF_TOKEN_LIFETIME', 3600)
    
    _csrf_token_manager = CSRFTokenManager(
        secret_key=app.secret_key,
        token_lifetime=token_lifetime
    )
    
    # Store in app for access by other components
    app.csrf_token_manager = _csrf_token_manager
    
    logger.info("CSRF token manager initialized")
    return _csrf_token_manager