# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
AI Service Monitor

Monitors AI service availability and handles automatic job failure
when the AI service becomes unavailable. Provides health checking,
outage detection, and recovery notifications.
"""

import logging
import asyncio
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from app.core.database.core.database_manager import DatabaseManager
from models import CaptionGenerationTask, TaskStatus
from app.services.task.core.task_queue_manager import TaskQueueManager
from progress_tracker import ProgressTracker
from app.core.security.core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class ServiceHealthCheck:
    """Result of a service health check"""
    status: ServiceStatus
    response_time_ms: Optional[float]
    error_message: Optional[str]
    timestamp: datetime
    check_type: str

class AIServiceMonitor:
    """Monitors AI service availability and handles outages"""
    
    def __init__(self, db_manager: DatabaseManager, task_queue_manager: TaskQueueManager,
                 progress_tracker: ProgressTracker):
        self.db_manager = db_manager
        self.task_queue_manager = task_queue_manager
        self.progress_tracker = progress_tracker
        
        # Service status tracking
        self._current_status = ServiceStatus.UNKNOWN
        self._last_check_time = None
        self._last_available_time = None
        self._outage_start_time = None
        
        # Configuration
        self._check_interval = 30  # seconds
        self._health_check_timeout = 10  # seconds
        self._outage_threshold = 3  # consecutive failures before declaring outage
        self._recovery_threshold = 2  # consecutive successes before declaring recovery
        
        # Failure tracking
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._total_checks = 0
        self._total_failures = 0
        
        # Health check history
        self._health_history = []
        self._max_history_size = 100
        
        # Monitoring control
        self._monitoring_active = False
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        # Callbacks
        self._outage_callbacks = []
        self._recovery_callbacks = []
        self._status_change_callbacks = []
        
        logger.info("AI service monitor initialized")
    
    def register_outage_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for service outage events"""
        self._outage_callbacks.append(callback)
    
    def register_recovery_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for service recovery events"""
        self._recovery_callbacks.append(callback)
    
    def register_status_change_callback(self, callback: Callable[[ServiceStatus, ServiceStatus], None]):
        """Register callback for status change events"""
        self._status_change_callbacks.append(callback)
    
    async def check_service_health(self) -> ServiceHealthCheck:
        """
        Perform a health check on the AI service
        
        Returns:
            ServiceHealthCheck with results
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Import here to avoid circular imports
            from ollama_caption_generator import OllamaCaptionGenerator
            
            # Create generator instance
            generator = OllamaCaptionGenerator()
            
            # Perform health check with timeout
            try:
                available = await asyncio.wait_for(
                    generator.test_connection(),
                    timeout=self._health_check_timeout
                )
                
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                if available:
                    return ServiceHealthCheck(
                        status=ServiceStatus.AVAILABLE,
                        response_time_ms=response_time,
                        error_message=None,
                        timestamp=timestamp,
                        check_type="connection_test"
                    )
                else:
                    return ServiceHealthCheck(
                        status=ServiceStatus.UNAVAILABLE,
                        response_time_ms=response_time,
                        error_message="Service connection test failed",
                        timestamp=timestamp,
                        check_type="connection_test"
                    )
                    
            except asyncio.TimeoutError:
                return ServiceHealthCheck(
                    status=ServiceStatus.UNAVAILABLE,
                    response_time_ms=self._health_check_timeout * 1000,
                    error_message=f"Health check timed out after {self._health_check_timeout}s",
                    timestamp=timestamp,
                    check_type="connection_test"
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealthCheck(
                status=ServiceStatus.UNAVAILABLE,
                response_time_ms=response_time,
                error_message=f"Health check failed: {str(e)}",
                timestamp=timestamp,
                check_type="connection_test"
            )
    
    async def perform_comprehensive_health_check(self) -> ServiceHealthCheck:
        """
        Perform a comprehensive health check including model availability
        
        Returns:
            ServiceHealthCheck with detailed results
        """
        start_time = time.time()
        timestamp = datetime.now(timezone.utc)
        
        try:
            from ollama_caption_generator import OllamaCaptionGenerator
            
            generator = OllamaCaptionGenerator()
            
            # Test basic connection
            connection_available = await asyncio.wait_for(
                generator.test_connection(),
                timeout=self._health_check_timeout
            )
            
            if not connection_available:
                return ServiceHealthCheck(
                    status=ServiceStatus.UNAVAILABLE,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error_message="AI service connection failed",
                    timestamp=timestamp,
                    check_type="comprehensive"
                )
            
            # Test model availability (if connection is available)
            try:
                model_available = await asyncio.wait_for(
                    generator.test_model_availability(),
                    timeout=self._health_check_timeout
                )
                
                response_time = (time.time() - start_time) * 1000
                
                if model_available:
                    return ServiceHealthCheck(
                        status=ServiceStatus.AVAILABLE,
                        response_time_ms=response_time,
                        error_message=None,
                        timestamp=timestamp,
                        check_type="comprehensive"
                    )
                else:
                    return ServiceHealthCheck(
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        error_message="AI service available but model not ready",
                        timestamp=timestamp,
                        check_type="comprehensive"
                    )
                    
            except asyncio.TimeoutError:
                return ServiceHealthCheck(
                    status=ServiceStatus.DEGRADED,
                    response_time_ms=self._health_check_timeout * 1000,
                    error_message="Model availability check timed out",
                    timestamp=timestamp,
                    check_type="comprehensive"
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealthCheck(
                status=ServiceStatus.UNAVAILABLE,
                response_time_ms=response_time,
                error_message=f"Comprehensive health check failed: {str(e)}",
                timestamp=timestamp,
                check_type="comprehensive"
            )
    
    def _update_status(self, health_check: ServiceHealthCheck):
        """Update service status based on health check result"""
        old_status = self._current_status
        self._last_check_time = health_check.timestamp
        self._total_checks += 1
        
        # Add to history
        self._health_history.append(health_check)
        if len(self._health_history) > self._max_history_size:
            self._health_history.pop(0)
        
        # Update failure/success counters
        if health_check.status == ServiceStatus.AVAILABLE:
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            self._last_available_time = health_check.timestamp
            
            # Check for recovery
            if (old_status != ServiceStatus.AVAILABLE and 
                self._consecutive_successes >= self._recovery_threshold):
                self._current_status = ServiceStatus.AVAILABLE
                self._outage_start_time = None
                logger.info("AI service recovery detected")
                self._notify_recovery_callbacks()
                
        else:
            self._consecutive_successes = 0
            self._consecutive_failures += 1
            self._total_failures += 1
            
            # Check for outage
            if (old_status == ServiceStatus.AVAILABLE and 
                self._consecutive_failures >= self._outage_threshold):
                self._current_status = health_check.status
                self._outage_start_time = health_check.timestamp
                logger.warning(f"AI service outage detected: {health_check.error_message}")
                asyncio.create_task(self._handle_service_outage())
                self._notify_outage_callbacks(health_check)
            elif old_status != health_check.status:
                self._current_status = health_check.status
        
        # Notify status change callbacks
        if old_status != self._current_status:
            self._notify_status_change_callbacks(old_status, self._current_status)
    
    async def _handle_service_outage(self):
        """Handle AI service outage by failing running tasks"""
        logger.info("Handling AI service outage - failing running tasks")
        
        try:
            # Find tasks that are currently running and depend on AI service
            with self.db_manager.get_session() as session:
                running_tasks = session.query(CaptionGenerationTask).filter(
                    CaptionGenerationTask.status == TaskStatus.RUNNING
                ).all()
                
                failed_tasks = 0
                for task in running_tasks:
                    try:
                        logger.info(f"Failing task {sanitize_for_log(task.id)} due to AI service outage")
                        
                        # Mark task as failed
                        success = self.task_queue_manager.complete_task(
                            task.id,
                            success=False,
                            error_message="AI service is currently unavailable. Please try again later."
                        )
                        
                        if success:
                            failed_tasks += 1
                            
                            # Update progress tracker
                            self.progress_tracker.update_progress(
                                task.id,
                                "Failed - AI service unavailable",
                                100,
                                {
                                    "error": "AI service outage detected",
                                    "outage_time": self._outage_start_time.isoformat() if self._outage_start_time else None,
                                    "recovery_suggestion": "The AI service is temporarily unavailable. Please try again in a few minutes."
                                }
                            )
                        
                    except Exception as e:
                        logger.error(f"Failed to handle outage for task {sanitize_for_log(task.id)}: {sanitize_for_log(str(e))}")
                
                logger.info(f"Failed {failed_tasks} running tasks due to AI service outage")
                
        except Exception as e:
            logger.error(f"Error handling AI service outage: {sanitize_for_log(str(e))}")
    
    def _notify_outage_callbacks(self, health_check: ServiceHealthCheck):
        """Notify outage callbacks"""
        outage_data = {
            "outage_start_time": self._outage_start_time.isoformat() if self._outage_start_time else None,
            "consecutive_failures": self._consecutive_failures,
            "last_error": health_check.error_message,
            "response_time_ms": health_check.response_time_ms
        }
        
        for callback in self._outage_callbacks:
            try:
                callback(outage_data)
            except Exception as e:
                logger.error(f"Outage callback failed: {sanitize_for_log(str(e))}")
    
    def _notify_recovery_callbacks(self):
        """Notify recovery callbacks"""
        recovery_data = {
            "recovery_time": datetime.now(timezone.utc).isoformat(),
            "outage_duration_seconds": (
                (datetime.now(timezone.utc) - self._outage_start_time).total_seconds()
                if self._outage_start_time else 0
            ),
            "consecutive_successes": self._consecutive_successes
        }
        
        for callback in self._recovery_callbacks:
            try:
                callback(recovery_data)
            except Exception as e:
                logger.error(f"Recovery callback failed: {sanitize_for_log(str(e))}")
    
    def _notify_status_change_callbacks(self, old_status: ServiceStatus, new_status: ServiceStatus):
        """Notify status change callbacks"""
        for callback in self._status_change_callbacks:
            try:
                callback(old_status, new_status)
            except Exception as e:
                logger.error(f"Status change callback failed: {sanitize_for_log(str(e))}")
    
    def start_monitoring(self):
        """Start continuous AI service monitoring"""
        if self._monitoring_active:
            logger.warning("AI service monitoring is already active")
            return
        
        logger.info("Starting AI service monitoring")
        self._monitoring_active = True
        self._stop_monitoring.clear()
        
        # Start monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="AIServiceMonitor",
            daemon=True
        )
        self._monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop continuous AI service monitoring"""
        if not self._monitoring_active:
            logger.warning("AI service monitoring is not active")
            return
        
        logger.info("Stopping AI service monitoring")
        self._monitoring_active = False
        self._stop_monitoring.set()
        
        # Wait for monitoring thread to finish
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
            if self._monitoring_thread.is_alive():
                logger.warning("Monitoring thread did not stop gracefully")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("AI service monitoring loop started")
        
        while not self._stop_monitoring.is_set():
            try:
                # Perform health check using proper async pattern
                health_check = asyncio.run(self.check_service_health())
                self._update_status(health_check)
                
                logger.debug(f"AI service health check: {health_check.status.value} "
                           f"({health_check.response_time_ms:.1f}ms)")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {sanitize_for_log(str(e))}")
                
                # Create error health check
                error_check = ServiceHealthCheck(
                    status=ServiceStatus.UNAVAILABLE,
                    response_time_ms=None,
                    error_message=f"Monitoring error: {str(e)}",
                    timestamp=datetime.now(timezone.utc),
                    check_type="monitoring_error"
                )
                self._update_status(error_check)
            
            # Wait for next check
            self._stop_monitoring.wait(self._check_interval)
        
        logger.info("AI service monitoring loop stopped")
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current AI service status
        
        Returns:
            Dict with service status information
        """
        return {
            "status": self._current_status.value,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "last_available_time": self._last_available_time.isoformat() if self._last_available_time else None,
            "outage_start_time": self._outage_start_time.isoformat() if self._outage_start_time else None,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
            "total_checks": self._total_checks,
            "total_failures": self._total_failures,
            "monitoring_active": self._monitoring_active,
            "uptime_percentage": self._calculate_uptime_percentage()
        }
    
    def get_health_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent health check history
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of health check results
        """
        recent_history = self._health_history[-limit:] if limit > 0 else self._health_history
        
        return [
            {
                "status": check.status.value,
                "response_time_ms": check.response_time_ms,
                "error_message": check.error_message,
                "timestamp": check.timestamp.isoformat(),
                "check_type": check.check_type
            }
            for check in recent_history
        ]
    
    def _calculate_uptime_percentage(self) -> float:
        """Calculate service uptime percentage"""
        if self._total_checks == 0:
            return 0.0
        
        successful_checks = self._total_checks - self._total_failures
        return (successful_checks / self._total_checks) * 100.0
    
    def is_service_available(self) -> bool:
        """Check if AI service is currently available"""
        return self._current_status == ServiceStatus.AVAILABLE
    
    def get_outage_duration(self) -> Optional[timedelta]:
        """Get current outage duration if service is down"""
        if self._outage_start_time and self._current_status != ServiceStatus.AVAILABLE:
            return datetime.now(timezone.utc) - self._outage_start_time
        return None

# Global instance
_ai_service_monitor = None

def initialize_ai_service_monitor(db_manager: DatabaseManager, task_queue_manager: TaskQueueManager,
                                progress_tracker: ProgressTracker) -> AIServiceMonitor:
    """Initialize the global AI service monitor"""
    global _ai_service_monitor
    _ai_service_monitor = AIServiceMonitor(db_manager, task_queue_manager, progress_tracker)
    return _ai_service_monitor

def get_ai_service_monitor() -> Optional[AIServiceMonitor]:
    """Get the global AI service monitor"""
    return _ai_service_monitor