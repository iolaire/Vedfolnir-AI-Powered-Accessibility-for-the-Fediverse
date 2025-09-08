# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
System Recovery Integration

Integrates all recovery components with the Flask web application.
Provides initialization, startup recovery, and graceful shutdown capabilities.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from flask import Flask

from database import DatabaseManager
from task_queue_manager import TaskQueueManager
from progress_tracker import ProgressTracker
from system_recovery_manager import SystemRecoveryManager, initialize_system_recovery
from graceful_shutdown_handler import initialize_graceful_shutdown
from database_connection_recovery import DatabaseConnectionRecovery
from ai_service_monitor import AIServiceMonitor, initialize_ai_service_monitor
from concurrent_operation_manager import ConcurrentOperationManager, initialize_concurrent_operation_manager
from security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class SystemRecoveryIntegration:
    """Integrates all recovery components with the Flask application"""
    
    def __init__(self, app: Flask, db_manager: DatabaseManager):
        self.app = app
        self.db_manager = db_manager
        
        # Initialize core components
        self.task_queue_manager = TaskQueueManager(db_manager)
        self.progress_tracker = ProgressTracker(db_manager)
        
        # Initialize recovery components
        self.recovery_manager = None
        self.shutdown_handler = None
        self.db_recovery = None
        self.ai_monitor = None
        self.operation_manager = None
        
        # Recovery state
        self._initialized = False
        self._startup_recovery_completed = False
        
    def initialize_recovery_components(self) -> Dict[str, Any]:
        """Initialize all recovery components"""
        logger.info("Initializing system recovery components")
        
        try:
            # Initialize recovery manager
            self.recovery_manager = SystemRecoveryManager(
                self.db_manager, self.task_queue_manager, self.progress_tracker
            )
            
            # Initialize database connection recovery
            self.db_recovery = DatabaseConnectionRecovery(self.db_manager)
            
            # Initialize AI service monitor
            self.ai_monitor = AIServiceMonitor(
                self.db_manager, self.task_queue_manager, self.progress_tracker
            )
            
            # Initialize concurrent operation manager
            self.operation_manager = ConcurrentOperationManager(self.db_manager)
            
            # Initialize graceful shutdown handler
            self.shutdown_handler = initialize_graceful_shutdown(
                self.app, self.recovery_manager, shutdown_timeout=30
            )
            
            # Store components in app for access from routes
            self.app.recovery_manager = self.recovery_manager
            self.app.db_recovery = self.db_recovery
            self.app.ai_monitor = self.ai_monitor
            self.app.operation_manager = self.operation_manager
            self.app.shutdown_handler = self.shutdown_handler
            
            # Register recovery callbacks
            self._register_recovery_callbacks()
            
            self._initialized = True
            
            logger.info("System recovery components initialized successfully")
            
            return {
                "status": "success",
                "components_initialized": [
                    "recovery_manager",
                    "db_recovery", 
                    "ai_monitor",
                    "operation_manager",
                    "shutdown_handler"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize recovery components: {sanitize_for_log(str(e))}")
            return {
                "status": "error",
                "error": str(e)
            }    
   
 def _register_recovery_callbacks(self):
        """Register callbacks between recovery components"""
        # Database recovery callbacks
        def db_recovery_callback(event_type, data):
            logger.info(f"Database recovery event: {event_type}")
            if event_type == "recovery_success":
                # Restart AI monitoring if it was stopped due to DB issues
                if self.ai_monitor and not self.ai_monitor._monitoring_active:
                    self.ai_monitor.start_monitoring()
        
        self.db_recovery.register_recovery_callback(db_recovery_callback)
        
        # AI service monitor callbacks
        def ai_outage_callback(outage_data):
            logger.warning(f"AI service outage detected: {outage_data}")
            # Could trigger admin notifications here
        
        def ai_recovery_callback(recovery_data):
            logger.info(f"AI service recovered: {recovery_data}")
            # Could trigger admin notifications here
        
        if self.ai_monitor:
            self.ai_monitor.register_outage_callback(ai_outage_callback)
            self.ai_monitor.register_recovery_callback(ai_recovery_callback)
    
    async def perform_startup_recovery(self) -> Dict[str, Any]:
        """Perform startup recovery process"""
        if not self._initialized:
            return {"status": "error", "error": "Recovery components not initialized"}
        
        if self._startup_recovery_completed:
            return {"status": "already_completed"}
        
        logger.info("Starting system startup recovery")
        
        try:
            # Perform startup recovery
            recovery_stats = await self.recovery_manager.startup_recovery()
            
            # Start AI service monitoring
            if self.ai_monitor:
                self.ai_monitor.start_monitoring()
                logger.info("AI service monitoring started")
            
            self._startup_recovery_completed = True
            
            logger.info(f"Startup recovery completed: {recovery_stats}")
            
            return {
                "status": "success",
                "recovery_stats": recovery_stats,
                "ai_monitoring_started": True
            }
            
        except Exception as e:
            logger.error(f"Startup recovery failed: {sanitize_for_log(str(e))}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        health_status = {
            "initialized": self._initialized,
            "startup_recovery_completed": self._startup_recovery_completed,
            "database_health": None,
            "ai_service_status": None,
            "active_locks": 0,
            "recovery_manager_status": "unknown"
        }
        
        try:
            # Database health
            if self.db_recovery:
                health_status["database_health"] = self.db_recovery.get_connection_health()
            
            # AI service status
            if self.ai_monitor:
                health_status["ai_service_status"] = self.ai_monitor.get_service_status()
            
            # Operation manager status
            if self.operation_manager:
                lock_stats = self.operation_manager.get_lock_statistics()
                health_status["active_locks"] = lock_stats.get("active_locks", 0)
            
            # Recovery manager status
            if self.recovery_manager:
                health_status["recovery_manager_status"] = "active"
            
        except Exception as e:
            logger.error(f"Error getting system health: {sanitize_for_log(str(e))}")
            health_status["error"] = str(e)
        
        return health_status
    
    def shutdown(self):
        """Shutdown all recovery components"""
        logger.info("Shutting down system recovery integration")
        
        try:
            # Stop AI monitoring
            if self.ai_monitor:
                self.ai_monitor.stop_monitoring()
            
            # Shutdown operation manager
            if self.operation_manager:
                self.operation_manager.shutdown()
            
            # Note: Graceful shutdown is handled by the shutdown handler
            
            logger.info("System recovery integration shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during recovery integration shutdown: {sanitize_for_log(str(e))}")

def initialize_system_recovery_integration(app: Flask, db_manager: DatabaseManager) -> SystemRecoveryIntegration:
    """
    Initialize system recovery integration for a Flask application
    
    Args:
        app: Flask application instance
        db_manager: Database manager instance
        
    Returns:
        SystemRecoveryIntegration instance
    """
    integration = SystemRecoveryIntegration(app, db_manager)
    
    # Initialize recovery components
    init_result = integration.initialize_recovery_components()
    
    if init_result["status"] != "success":
        logger.error(f"Failed to initialize recovery integration: {init_result}")
        raise RuntimeError(f"Recovery integration initialization failed: {init_result.get('error')}")
    
    # Store integration in app
    app.recovery_integration = integration
    
    # Add recovery routes
    _add_recovery_routes(app, integration)
    
    logger.info("System recovery integration initialized successfully")
    return integration

def _add_recovery_routes(app: Flask, integration: SystemRecoveryIntegration):
    """Add recovery-related routes to the Flask app"""
    
    @app.route('/api/system/health')
    def system_health():
        from flask import jsonify
        health = integration.get_system_health()
        return jsonify(health)
    
    @app.route('/admin/api/system/recovery-status')
    def recovery_status():
        from flask import jsonify
        from flask_login import current_user
        from models import UserRole
        
        # Check admin authorization
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            return jsonify({"error": "Unauthorized"}), 403
        
        status = {
            "initialized": integration._initialized,
            "startup_recovery_completed": integration._startup_recovery_completed,
            "components": {
                "recovery_manager": integration.recovery_manager is not None,
                "db_recovery": integration.db_recovery is not None,
                "ai_monitor": integration.ai_monitor is not None,
                "operation_manager": integration.operation_manager is not None,
                "shutdown_handler": integration.shutdown_handler is not None
            }
        }
        
        return jsonify(status)
    
    @app.route('/admin/api/system/force-recovery', methods=['POST'])
    def force_recovery():
        from flask import jsonify, request
        from flask_login import current_user
        from models import UserRole
        
        # Check admin authorization
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Force startup recovery (can be run multiple times)
        integration._startup_recovery_completed = False
        
        # Run recovery using proper async pattern
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        async def run_recovery_async():
            try:
                result = await integration.perform_startup_recovery()
                logger.info(f"Force recovery completed: {result}")
                return result
            except Exception as e:
                logger.error(f"Recovery failed: {e}")
                raise
        
        # Use thread pool executor instead of manual event loop
        with ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, run_recovery_async())
        
        return jsonify({"message": "Recovery initiated", "status": "started"})

# Startup recovery function for use in application startup
async def run_startup_recovery(app: Flask) -> Dict[str, Any]:
    """
    Run startup recovery for a Flask application
    
    Args:
        app: Flask application instance
        
    Returns:
        Dict with recovery results
    """
    integration = getattr(app, 'recovery_integration', None)
    if not integration:
        logger.warning("No recovery integration found in app")
        return {"status": "no_integration"}
    
    return await integration.perform_startup_recovery()