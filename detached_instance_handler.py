#!/usr/bin/env python3

"""
DetachedInstanceError Recovery Handler

This module provides comprehensive handling and recovery mechanisms for SQLAlchemy
DetachedInstanceError exceptions, ensuring database objects remain accessible
throughout the Flask request lifecycle.
"""

import logging
import time
from typing import Any, Optional, Type
from sqlalchemy.exc import InvalidRequestError, SQLAlchemyError
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.orm import Session
from flask import current_app, request, redirect, url_for, flash

class DetachedInstanceHandler:
    """Handler for DetachedInstanceError recovery with session manager integration"""
    
    def __init__(self, session_manager):
        """Initialize handler with session manager
        
        Args:
            session_manager: RequestScopedSessionManager instance
        """
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
    
    def handle_detached_instance(self, obj: Any, session: Optional[Session] = None) -> Any:
        """Recover detached objects using merge or reload
        
        Args:
            obj: The detached SQLAlchemy object
            session: Optional session to use, defaults to request session
            
        Returns:
            Recovered object attached to session
            
        Raises:
            InvalidRequestError: If recovery fails
        """
        if session is None:
            session = self.session_manager.get_request_session()
        
        # Time the recovery operation for performance monitoring
        start_time = time.time()
        object_type = type(obj).__name__
        recovery_successful = False
        
        try:
            # First attempt: merge the object back into the session
            self.logger.debug(f"Attempting to merge detached object: {object_type}")
            recovered_obj = session.merge(obj)
            recovery_duration = time.time() - start_time
            recovery_successful = True
            
            self.logger.debug(f"Successfully merged object: {object_type}")
            
            # Record performance metrics
            self._record_recovery_metrics(object_type, recovery_duration, True)
            
            return recovered_obj
            
        except InvalidRequestError as e:
            self.logger.warning(f"Merge failed for {object_type}: {e}")
            
            # Second attempt: reload from database using primary key
            if hasattr(obj, 'id') and obj.id is not None:
                try:
                    model_class = type(obj)
                    self.logger.debug(f"Attempting to reload {model_class.__name__} with id {obj.id}")
                    recovered_obj = session.query(model_class).get(obj.id)
                    
                    if recovered_obj is not None:
                        recovery_duration = time.time() - start_time
                        recovery_successful = True
                        
                        self.logger.debug(f"Successfully reloaded object: {model_class.__name__}")
                        
                        # Record performance metrics
                        self._record_recovery_metrics(object_type, recovery_duration, True)
                        
                        return recovered_obj
                    else:
                        self.logger.error(f"Object not found in database: {model_class.__name__} id={obj.id}")
                        
                except Exception as reload_error:
                    self.logger.error(f"Reload failed for {object_type}: {reload_error}")
            
            # If all recovery attempts fail, record failure and re-raise
            recovery_duration = time.time() - start_time
            self._record_recovery_metrics(object_type, recovery_duration, False)
            
            raise InvalidRequestError(f"Failed to recover detached instance: {object_type}")
    
    def safe_access(self, obj: Any, attr_name: str, default: Any = None) -> Any:
        """Safely access object attributes with automatic recovery
        
        Args:
            obj: The SQLAlchemy object
            attr_name: Name of the attribute to access
            default: Default value if access fails
            
        Returns:
            Attribute value or default
        """
        try:
            return getattr(obj, attr_name)
            
        except DetachedInstanceError:
            self.logger.info(f"DetachedInstanceError accessing {attr_name} on {type(obj).__name__}, attempting recovery")
            
            # Time the recovery operation
            start_time = time.time()
            object_type = type(obj).__name__
            
            try:
                # Attempt recovery
                session = self.session_manager.get_request_session()
                recovered_obj = self.handle_detached_instance(obj, session)
                result = getattr(recovered_obj, attr_name, default)
                
                recovery_duration = time.time() - start_time
                self._record_recovery_metrics(f"{object_type}.{attr_name}", recovery_duration, True)
                
                return result
                
            except Exception as recovery_error:
                recovery_duration = time.time() - start_time
                self.logger.error(f"Recovery failed for {object_type}.{attr_name}: {recovery_error}")
                self._record_recovery_metrics(f"{object_type}.{attr_name}", recovery_duration, False)
                return default
                
        except AttributeError:
            self.logger.debug(f"Attribute {attr_name} not found on {type(obj).__name__}")
            return default
            
        except Exception as e:
            self.logger.error(f"Unexpected error accessing {attr_name} on {type(obj).__name__}: {e}")
            return default
    
    def safe_relationship_access(self, obj: Any, relationship_name: str, default: Optional[list] = None) -> Any:
        """Safely access object relationships with automatic recovery
        
        Args:
            obj: The SQLAlchemy object
            relationship_name: Name of the relationship to access
            default: Default value if access fails (defaults to empty list)
            
        Returns:
            Relationship value or default
        """
        if default is None:
            default = []
            
        try:
            return getattr(obj, relationship_name)
            
        except DetachedInstanceError:
            self.logger.info(f"DetachedInstanceError accessing {relationship_name} on {type(obj).__name__}, attempting recovery")
            
            try:
                # Attempt recovery
                session = self.session_manager.get_request_session()
                recovered_obj = self.handle_detached_instance(obj, session)
                return getattr(recovered_obj, relationship_name, default)
                
            except Exception as recovery_error:
                self.logger.error(f"Recovery failed for {type(obj).__name__}.{relationship_name}: {recovery_error}")
                return default
                
        except AttributeError:
            self.logger.debug(f"Relationship {relationship_name} not found on {type(obj).__name__}")
            return default
            
        except Exception as e:
            self.logger.error(f"Unexpected error accessing {relationship_name} on {type(obj).__name__}: {e}")
            return default
    
    def ensure_attached(self, obj: Any, session: Optional[Session] = None) -> Any:
        """Ensure object is attached to session, recovering if necessary
        
        Args:
            obj: The SQLAlchemy object
            session: Optional session to use, defaults to request session
            
        Returns:
            Object attached to session
        """
        if session is None:
            session = self.session_manager.get_request_session()
        
        # Check if object is already in session
        if obj in session:
            return obj
        
        # Object is not in session, attempt recovery
        try:
            return self.handle_detached_instance(obj, session)
        except Exception as e:
            self.logger.error(f"Failed to ensure attachment for {type(obj).__name__}: {e}")
            return obj
    
    def _record_recovery_metrics(self, object_type: str, duration: float, success: bool):
        """Record recovery performance metrics"""
        try:
            from session_performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
            monitor.record_detached_instance_recovery(object_type, duration, success)
        except ImportError:
            # Performance monitoring not available
            pass
        except Exception as e:
            self.logger.debug(f"Failed to record recovery metrics: {e}")

def create_global_detached_instance_handler(app, session_manager):
    """Create global error handler for DetachedInstanceError exceptions
    
    Args:
        app: Flask application instance
        session_manager: RequestScopedSessionManager instance
    """
    handler = DetachedInstanceHandler(session_manager)
    
    @app.errorhandler(DetachedInstanceError)
    def handle_detached_instance_error(error):
        """Global handler for DetachedInstanceError"""
        app.logger.error(f"DetachedInstanceError occurred in {request.endpoint}: {error}")
        
        # Try to recover by redirecting to a safe page
        if request.endpoint == 'dashboard':
            # Session expired - handled by unified notification system
            pass
            return redirect(url_for('login'))
        elif request.endpoint and 'platform' in request.endpoint:
            # Platform connection issue - handled by unified notification system
            pass
            return redirect(url_for('dashboard'))
        
        # For other endpoints, return a generic error
        # Database connection issue - handled by unified notification system
        pass
        return redirect(url_for('index') if 'index' in app.view_functions else url_for('login'))
    
    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        """Global handler for general SQLAlchemy errors"""
        app.logger.error(f"SQLAlchemy error occurred in {request.endpoint}: {error}")
        
        # Check if it's a DetachedInstanceError wrapped in another exception
        if isinstance(error, DetachedInstanceError) or 'DetachedInstanceError' in str(error):
            return handle_detached_instance_error(error)
        
        # Handle other SQLAlchemy errors
        # Database error - handled by unified notification system
        pass
        return redirect(url_for('index') if 'index' in app.view_functions else url_for('login'))
    
    # Store handler in app for access by other components
    app.detached_instance_handler = handler
    
    return handler

def get_detached_instance_handler():
    """Get the current application's DetachedInstanceHandler
    
    Returns:
        DetachedInstanceHandler instance
        
    Raises:
        RuntimeError: If no handler is configured
    """
    if hasattr(current_app, 'detached_instance_handler'):
        return current_app.detached_instance_handler
    
    raise RuntimeError("DetachedInstanceHandler not configured. Call create_global_detached_instance_handler() during app initialization.")