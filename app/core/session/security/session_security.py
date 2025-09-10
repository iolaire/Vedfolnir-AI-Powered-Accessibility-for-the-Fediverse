# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Security and Validation

This module provides enhanced security features for database session management,
including session fingerprinting, validation, and security audit logging.
"""

import hashlib
import hmac
import secrets
from logging import getLogger
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from flask import request, g
from app.core.session.manager import SessionValidationError, SessionExpiredError, SessionNotFoundError
from models import UserSession, User
from app.core.database.core.database_manager import DatabaseManager

logger = getLogger(__name__)

class SessionSecurityManager:
    """Enhanced security manager for database sessions"""
    
    def __init__(self, db_manager: DatabaseManager, secret_key: str):
        self.db_manager = db_manager
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.max_session_age = timedelta(hours=24)
        self.max_inactive_time = timedelta(hours=2)
        
    def create_session_fingerprint(self) -> str:
        """
        Create a session fingerprint based on request characteristics
        
        Returns:
            Fingerprint string
        """
        try:
            # Collect request characteristics
            user_agent = request.headers.get('User-Agent', '')
            accept_language = request.headers.get('Accept-Language', '')
            accept_encoding = request.headers.get('Accept-Encoding', '')
            
            # Create fingerprint data
            fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}"
            
            # Hash the fingerprint data
            fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()
            
            # Create HMAC signature
            signature = hmac.new(
                self.secret_key,
                fingerprint_hash.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return f"{fingerprint_hash}:{signature}"
            
        except Exception as e:
            logger.warning(f"Failed to create session fingerprint: {e}")
            return secrets.token_hex(32)
    
    def validate_session_fingerprint(self, session: UserSession) -> bool:
        """
        Validate session fingerprint against current request
        
        Args:
            session: UserSession object
            
        Returns:
            True if fingerprint is valid, False otherwise
        """
        if not session.session_fingerprint:
            # No fingerprint stored - allow but log warning
            logger.warning(f"Session {session.session_id} has no fingerprint")
            return True
        
        try:
            # Create current fingerprint
            current_fingerprint = self.create_session_fingerprint()
            
            # Extract stored fingerprint components
            if ':' not in session.session_fingerprint:
                logger.warning(f"Invalid fingerprint format for session {session.session_id}")
                return False
            
            stored_hash, stored_signature = session.session_fingerprint.split(':', 1)
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                stored_hash.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(stored_signature, expected_signature):
                logger.warning(f"Invalid fingerprint signature for session {session.session_id}")
                return False
            
            # For now, we'll be lenient with fingerprint changes to avoid breaking legitimate users
            # In a stricter implementation, you might require exact matches
            return True
            
        except Exception as e:
            logger.error(f"Error validating session fingerprint: {e}")
            return False
    
    def validate_session_comprehensive(self, session_id: str) -> UserSession:
        """
        Comprehensive session validation with security checks
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            UserSession object if valid
            
        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionExpiredError: If session is expired
            SessionValidationError: If session fails security checks
        """
        with self.db_manager.get_session() as db_session:
            # Find session
            user_session = UserSession.find_by_session_id(db_session, session_id)
            if not user_session:
                raise SessionNotFoundError(f"Session {session_id} not found")
            
            # Check if session is active
            if not user_session.is_active:
                raise SessionExpiredError(f"Session {session_id} is inactive")
            
            # Check expiration
            if user_session.is_expired():
                # Mark as inactive
                user_session.is_active = False
                db_session.commit()
                raise SessionExpiredError(f"Session {session_id} has expired")
            
            # Check for excessive inactivity
            if not user_session.is_recently_active(minutes=120):  # 2 hours
                logger.warning(f"Session {session_id} has been inactive for over 2 hours")
                # Don't fail validation but log for monitoring
            
            # Validate fingerprint
            if not self.validate_session_fingerprint(user_session):
                logger.warning(f"Session {session_id} failed fingerprint validation")
                # Don't fail validation but log for security monitoring
            
            # Check user status
            if user_session.user and not user_session.user.is_active:
                user_session.is_active = False
                db_session.commit()
                raise SessionValidationError(f"User for session {session_id} is inactive")
            
            # Update activity
            user_session.update_activity()
            db_session.commit()
            
            return user_session
    
    def detect_suspicious_activity(self, session: UserSession) -> List[str]:
        """
        Detect suspicious session activity
        
        Args:
            session: UserSession object
            
        Returns:
            List of suspicious activity indicators
        """
        suspicious_indicators = []
        
        try:
            # Check for rapid platform switching
            if hasattr(g, 'platform_switch_count'):
                if g.platform_switch_count > 5:  # More than 5 switches in this request cycle
                    suspicious_indicators.append("rapid_platform_switching")
            
            # Check session age
            session_age = session.get_session_duration()
            if session_age > 86400 * 7:  # Older than 7 days
                suspicious_indicators.append("very_old_session")
            
            # Check for unusual user agent changes (if we stored previous user agent)
            current_user_agent = request.headers.get('User-Agent', '') if request else ''
            if session.user_agent and current_user_agent:
                if session.user_agent != current_user_agent:
                    suspicious_indicators.append("user_agent_change")
            
            # Check for IP address changes (basic check)
            current_ip = self._get_client_ip()
            if session.ip_address and current_ip:
                if session.ip_address != current_ip:
                    suspicious_indicators.append("ip_address_change")
            
        except Exception as e:
            logger.error(f"Error detecting suspicious activity: {e}")
        
        return suspicious_indicators
    
    def create_security_audit_event(self, event_type: str, session_id: str, user_id: int, details: Dict[str, Any]):
        """
        Create security audit event for session operations
        
        Args:
            event_type: Type of security event
            session_id: Session ID
            user_id: User ID
            details: Additional event details
        """
        try:
            # For now, just log the event
            # In a full implementation, you might store these in a separate audit table
            audit_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'session_id': session_id,
                'user_id': user_id,
                'ip_address': self._get_client_ip(),
                'user_agent': request.headers.get('User-Agent', '') if request else '',
                'details': details
            }
            
            logger.info(f"Security audit event: {audit_data}")
            
        except Exception as e:
            logger.error(f"Failed to create security audit event: {e}")
    
    def cleanup_suspicious_sessions(self) -> int:
        """
        Clean up sessions that show suspicious activity
        
        Returns:
            Number of sessions cleaned up
        """
        cleaned_count = 0
        
        try:
            with self.db_manager.get_session() as db_session:
                # Find sessions that are very old
                old_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                old_sessions = db_session.query(UserSession).filter(
                    UserSession.created_at < old_cutoff
                ).all()
                
                for session in old_sessions:
                    self.create_security_audit_event(
                        'session_cleanup_old',
                        session.session_id,
                        session.user_id,
                        {'reason': 'session_too_old', 'age_days': (datetime.now(timezone.utc) - session.created_at).days}
                    )
                    db_session.delete(session)
                    cleaned_count += 1
                
                # Find sessions with inactive users
                inactive_user_sessions = db_session.query(UserSession).join(User).filter(
                    User.is_active == False
                ).all()
                
                for session in inactive_user_sessions:
                    self.create_security_audit_event(
                        'session_cleanup_inactive_user',
                        session.session_id,
                        session.user_id,
                        {'reason': 'user_inactive'}
                    )
                    db_session.delete(session)
                    cleaned_count += 1
                
                db_session.commit()
                
        except Exception as e:
            logger.error(f"Error cleaning up suspicious sessions: {e}")
        
        return cleaned_count
    
    def _get_client_ip(self) -> Optional[str]:
        """Get client IP address from request"""
        try:
            if request:
                return request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        except Exception:
            pass
        return None

def create_session_security_manager(app_config: dict, db_manager: DatabaseManager) -> SessionSecurityManager:
    """
    Create session security manager from app configuration
    
    Args:
        app_config: Flask app configuration
        db_manager: Database manager instance
        
    Returns:
        SessionSecurityManager instance
    """
    secret_key = app_config.get('SECRET_KEY', 'default-secret-key')
    return SessionSecurityManager(db_manager, secret_key)