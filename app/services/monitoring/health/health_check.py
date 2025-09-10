# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Health check module for Vedfolnir system monitoring.

This module provides health check functionality for various system components
including database connectivity, Ollama service, ActivityPub client, and
overall system status.
"""

import logging
import time
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import ProcessingRun, Image, Post
from app.services.activitypub.components.activitypub_client import ActivityPubClient
from app.utils.processing.ollama_caption_generator import OllamaCaptionGenerator

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class ComponentHealth:
    """Health status for a system component"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class SystemHealth:
    """Overall system health status"""
    status: HealthStatus
    timestamp: datetime
    components: Dict[str, ComponentHealth]
    uptime_seconds: Optional[float] = None
    version: Optional[str] = None

class HealthChecker:
    """System health checker with responsiveness monitoring and recovery capabilities"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.start_time = time.time()
        
        # Initialize responsiveness monitoring
        self.responsiveness_config = config.responsiveness
        self._last_responsiveness_check = 0
        self._responsiveness_metrics = {}
        
        # Initialize SystemOptimizer for responsiveness monitoring
        try:
            from web_app import SystemOptimizer
            self.system_optimizer = SystemOptimizer(config)
        except ImportError:
            self.system_optimizer = None
        
        # Initialize responsiveness recovery manager
        self._recovery_manager = None
        
        # Health check history for trend analysis
        self.health_history = []
        self.max_health_history = 50
        
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.start_time
    
    async def check_database_health(self) -> ComponentHealth:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            session = self.db_manager.get_session()
            try:
                # Test basic connectivity
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
                
                # Get some basic statistics
                post_count = session.query(Post).count()
                image_count = session.query(Image).count()
                run_count = session.query(ProcessingRun).count()
                
                # Check for recent activity (last 24 hours)
                recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_runs = session.query(ProcessingRun).filter(
                    ProcessingRun.started_at >= recent_cutoff
                ).count()
                
                response_time = (time.time() - start_time) * 1000
                
                details = {
                    "posts": post_count,
                    "images": image_count,
                    "processing_runs": run_count,
                    "recent_runs_24h": recent_runs,
                    "database_url": self.config.storage.database_url.split("://")[0] + "://***"
                }
                
                # Determine status based on response time
                if response_time > 5000:  # 5 seconds
                    status = HealthStatus.DEGRADED
                    message = f"Database responding slowly ({response_time:.0f}ms)"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database connection healthy"
                
                return ComponentHealth(
                    name="database",
                    status=status,
                    message=message,
                    response_time_ms=response_time,
                    last_check=datetime.now(timezone.utc),
                    details=details
                )
                
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Unexpected database error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    async def check_ollama_health(self) -> ComponentHealth:
        """Check Ollama service connectivity and model availability"""
        start_time = time.time()
        
        try:
            # Create caption generator to test Ollama connection
            caption_generator = OllamaCaptionGenerator(self.config.ollama)
            
            # Test basic connectivity
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.config.ollama.url}/api/tags")
                response.raise_for_status()
                
                models_data = response.json()
                models = [model["name"] for model in models_data.get("models", [])]
                
                response_time = (time.time() - start_time) * 1000
                
                # Check if required model is available
                required_model = self.config.ollama.model_name
                model_available = any(required_model in model for model in models)
                
                details = {
                    "base_url": self.config.ollama.url,
                    "required_model": required_model,
                    "model_available": model_available,
                    "available_models": models[:5]  # Limit to first 5 models
                }
                
                if not model_available:
                    status = HealthStatus.DEGRADED
                    message = f"Required model '{required_model}' not found"
                elif response_time > 3000:  # 3 seconds
                    status = HealthStatus.DEGRADED
                    message = f"Ollama responding slowly ({response_time:.0f}ms)"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Ollama service healthy"
                
                return ComponentHealth(
                    name="ollama",
                    status=status,
                    message=message,
                    response_time_ms=response_time,
                    last_check=datetime.now(timezone.utc),
                    details=details
                )
                
        except httpx.TimeoutException:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message="Ollama service timeout",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": "Connection timeout"}
            )
        except httpx.RequestError as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Ollama connection failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Unexpected Ollama error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    async def check_activitypub_health(self) -> ComponentHealth:
        """Check ActivityPub connectivity using platform-aware configuration"""
        start_time = time.time()
        
        try:
            # Get a platform connection from the database for health checking
            from models import PlatformConnection
            session = self.db_manager.get_session()
            try:
                # Get the first active platform connection for health checking
                platform = session.query(PlatformConnection).filter_by(is_active=True).first()
                
                if not platform:
                    return ComponentHealth(
                        name="activitypub",
                        status=HealthStatus.UNHEALTHY,
                        message="No active platform connections found",
                        response_time_ms=(time.time() - start_time) * 1000,
                        last_check=datetime.now(timezone.utc),
                        details={"error": "No platform connections configured"}
                    )
                
                # Check if we can decrypt the access token
                try:
                    access_token = platform.access_token
                    if not access_token:
                        return ComponentHealth(
                            name="activitypub",
                            status=HealthStatus.DEGRADED,
                            message=f"Platform '{platform.name}' has no access token",
                            response_time_ms=(time.time() - start_time) * 1000,
                            last_check=datetime.now(timezone.utc),
                            details={
                                "error": "No access token",
                                "platform_name": platform.name,
                                "platform_type": platform.platform_type,
                                "instance_url": platform.instance_url,
                                "suggestion": "Re-add platform connection through web interface"
                            }
                        )
                except Exception as decrypt_error:
                    return ComponentHealth(
                        name="activitypub",
                        status=HealthStatus.DEGRADED,
                        message=f"Platform '{platform.name}' has encrypted credentials that cannot be decrypted (encryption key mismatch)",
                        response_time_ms=(time.time() - start_time) * 1000,
                        last_check=datetime.now(timezone.utc),
                        details={
                            "error": "Credential decryption failed",
                            "platform_name": platform.name,
                            "platform_type": platform.platform_type,
                            "instance_url": platform.instance_url,
                            "suggestion": "Re-add platform connection through web interface"
                        }
                    )
                
            finally:
                session.close()
            
            # Test basic connectivity by getting instance info
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.get(
                    f"{platform.instance_url}/api/v1/instance"
                )
                response.raise_for_status()
                
                instance_data = response.json()
                response_time = (time.time() - start_time) * 1000
                
                details = {
                    "platform_name": platform.name,
                    "platform_type": platform.platform_type,
                    "instance_url": platform.instance_url,
                    "instance_title": instance_data.get("title", "Unknown"),
                    "instance_version": instance_data.get("version", "Unknown"),
                    "user_count": instance_data.get("stats", {}).get("user_count", 0),
                    "status_count": instance_data.get("stats", {}).get("status_count", 0)
                }
                
                if response_time > 5000:  # 5 seconds
                    status = HealthStatus.DEGRADED
                    message = f"ActivityPub responding slowly ({response_time:.0f}ms)"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"ActivityPub connection healthy ({platform.name})"
                
                return ComponentHealth(
                    name="activitypub",
                    status=status,
                    message=message,
                    response_time_ms=response_time,
                    last_check=datetime.now(timezone.utc),
                    details=details
                )
                    
        except httpx.TimeoutException:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="activitypub",
                status=HealthStatus.UNHEALTHY,
                message="ActivityPub service timeout",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": "Connection timeout"}
            )
        except httpx.RequestError as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="activitypub",
                status=HealthStatus.UNHEALTHY,
                message=f"ActivityPub connection failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="activitypub",
                status=HealthStatus.UNHEALTHY,
                message=f"Unexpected ActivityPub error: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    async def check_storage_health(self) -> ComponentHealth:
        """Check storage health - database connection and file storage"""
        start_time = time.time()
        
        try:
            issues = []
            details = {}
            
            # Check database type and connection
            database_url = self.config.storage.database_url
            
            if database_url.startswith('mysql'):
                # MySQL/MariaDB database health check
                try:
                    session = self.db_manager.get_session()
                    try:
                        from sqlalchemy import text
                        
                        # Test basic connectivity
                        session.execute(text("SELECT 1"))
                        
                        # Get MySQL-specific information
                        result = session.execute(text("SELECT VERSION()"))
                        mysql_version = result.fetchone()[0]
                        
                        # Get database name
                        result = session.execute(text("SELECT DATABASE()"))
                        database_name = result.fetchone()[0]
                        
                        # Get database size (MySQL 5.0+)
                        try:
                            result = session.execute(text("""
                                SELECT 
                                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size in MB'
                                FROM information_schema.tables 
                                WHERE table_schema = DATABASE()
                            """))
                            db_size_mb = result.fetchone()[0] or 0
                        except Exception:
                            db_size_mb = 0
                        
                        # Get table count
                        result = session.execute(text("""
                            SELECT COUNT(*) FROM information_schema.tables 
                            WHERE table_schema = DATABASE()
                        """))
                        table_count = result.fetchone()[0]
                        
                        # Get connection info
                        try:
                            result = session.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
                            connections = result.fetchone()[1] if result.fetchone() else 0
                        except Exception:
                            connections = 0
                        
                        details.update({
                            "database_type": "MySQL/MariaDB",
                            "database_name": database_name,
                            "mysql_version": mysql_version,
                            "database_size_mb": db_size_mb,
                            "table_count": table_count,
                            "active_connections": connections,
                            "connection_url": database_url.split("://")[0] + "://***"
                        })
                        
                    finally:
                        session.close()
                        
                except Exception as e:
                    issues.append(f"MySQL database connection failed: {str(e)}")
                    details["database_error"] = str(e)
                    
            elif database_url.startswith('MySQL'):
                # MySQL
                try:
                    # Test MySQL connection and get database information
                    from app.core.database.core.database_manager import DatabaseManager
                    from config import Config
                    
                    config = Config()
                    db_manager = DatabaseManager(config)
                    
                    # Test MySQL connection
                    is_connected, connection_message = db_manager.test_mysql_connection()
                    
                    if not is_connected:
                        issues.append(f"MySQL connection failed: {connection_message}")
                    
                    # Get MySQL performance stats
                    try:
                        mysql_stats = db_manager.get_mysql_performance_stats()
                        if 'error' in mysql_stats:
                            issues.append(f"MySQL stats error: {mysql_stats['error']}")
                        else:
                            details.update({
                                "database_type": "MySQL",
                                "connection_status": "Connected" if is_connected else "Failed",
                                "connection_message": connection_message,
                                "connection_pool": mysql_stats.get('connection_pool', {}),
                                "mysql_threads": mysql_stats.get('mysql_threads', {}),
                                "total_connections": mysql_stats.get('total_connections', 'Unknown')
                            })
                    except Exception as e:
                        issues.append(f"Failed to get MySQL performance stats: {e}")
                        details.update({
                            "database_type": "MySQL",
                            "connection_status": "Connected" if is_connected else "Failed",
                            "connection_message": connection_message,
                            "stats_error": str(e)
                        })
                    
                    # Check disk space (warn if less than 1GB free)
                    if db_usage.free < 1024**3:
                        issues.append("Low disk space for database (less than 1GB free)")
                        
                except Exception as e:
                    issues.append(f"MySQL database check failed: {str(e)}")
                    details["database_error"] = str(e)
            
            # Check images directory (common for both database types)
            try:
                images_dir = self.config.storage.images_dir
                
                if not os.path.exists(images_dir):
                    issues.append(f"Images directory does not exist: {images_dir}")
                elif not os.access(images_dir, os.W_OK):
                    issues.append(f"Images directory not writable: {images_dir}")
                else:
                    # Get storage statistics for images
                    import shutil
                    images_usage = shutil.disk_usage(images_dir)
                    
                    # Count stored images and calculate total size
                    image_files = [f for f in os.listdir(images_dir) 
                                  if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))]
                    image_count = len(image_files)
                    
                    # Calculate total size of stored images
                    total_image_size_bytes = 0
                    for image_file in image_files:
                        try:
                            image_path = os.path.join(images_dir, image_file)
                            total_image_size_bytes += os.path.getsize(image_path)
                        except (OSError, IOError):
                            # Skip files that can't be accessed
                            continue
                    
                    # Convert to human-readable format
                    if total_image_size_bytes >= 1024**3:  # GB
                        image_size_display = f"{total_image_size_bytes / (1024**3):.2f}GB"
                    elif total_image_size_bytes >= 1024**2:  # MB
                        image_size_display = f"{total_image_size_bytes / (1024**2):.1f}MB"
                    elif total_image_size_bytes >= 1024:  # KB
                        image_size_display = f"{total_image_size_bytes / 1024:.1f}KB"
                    else:  # Bytes
                        image_size_display = f"{total_image_size_bytes}B"
                    
                    details.update({
                        "images_directory": images_dir,
                        "stored_images": image_count,
                        "stored_images_size": image_size_display,
                        "stored_images_size_bytes": total_image_size_bytes,
                        "images_disk_free_gb": round(images_usage.free / (1024**3), 2),
                        "images_disk_total_gb": round(images_usage.total / (1024**3), 2)
                    })
                    
                    # Check disk space (warn if less than 1GB free)
                    if images_usage.free < 1024**3:
                        issues.append("Low disk space for images (less than 1GB free)")
                        
            except Exception as e:
                issues.append(f"Images directory check failed: {str(e)}")
                details["images_error"] = str(e)
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine health status
            if issues:
                # Check for critical issues
                critical_issues = [issue for issue in issues if 
                                 "connection failed" in issue.lower() or 
                                 "does not exist" in issue.lower() or 
                                 "not writable" in issue.lower()]
                
                if critical_issues:
                    status = HealthStatus.UNHEALTHY
                    message = "; ".join(critical_issues)
                else:
                    status = HealthStatus.DEGRADED
                    message = "; ".join(issues)
            else:
                status = HealthStatus.HEALTHY
                if database_url.startswith('mysql'):
                    message = f"MySQL storage healthy ({details.get('database_name', 'unknown')} database)"
                else:
                    message = "MySQL storage healthy"
            
            return ComponentHealth(
                name="storage",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details=details
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="storage",
                status=HealthStatus.UNHEALTHY,
                message=f"Storage check failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )

    async def check_session_health(self) -> ComponentHealth:
        """Check Redis session storage health"""
        start_time = time.time()
        
        try:
            import redis
            
            # Get Redis configuration from environment
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_db = int(os.getenv('REDIS_DB', '0'))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            # Create Redis client
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0
            )
            
            # Test basic connectivity
            redis_client.ping()
            
            # Get Redis server info
            redis_info = redis_client.info()
            
            # Get session-related statistics
            session_keys = redis_client.keys("session:*")
            platform_keys = redis_client.keys("user_platforms:*")
            platform_individual_keys = redis_client.keys("platform:*")
            platform_stats_keys = redis_client.keys("platform_stats:*")
            
            # Get memory usage
            memory_used = redis_info.get('used_memory_human', 'unknown')
            memory_peak = redis_info.get('used_memory_peak_human', 'unknown')
            
            # Get connection info
            connected_clients = redis_info.get('connected_clients', 0)
            total_connections = redis_info.get('total_connections_received', 0)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            details = {
                "redis_host": redis_host,
                "redis_port": redis_port,
                "redis_db": redis_db,
                "redis_version": redis_info.get('redis_version', 'unknown'),
                "session_keys": len(session_keys),
                "platform_cache_keys": len(platform_keys),
                "individual_platform_keys": len(platform_individual_keys),
                "platform_stats_keys": len(platform_stats_keys),
                "total_keys": len(session_keys) + len(platform_keys) + len(platform_individual_keys) + len(platform_stats_keys),
                "memory_used": memory_used,
                "memory_peak": memory_peak,
                "connected_clients": connected_clients,
                "total_connections": total_connections,
                "uptime_seconds": redis_info.get('uptime_in_seconds', 0)
            }
            
            # Determine health status
            if response_time > 1000:  # 1 second
                status = HealthStatus.DEGRADED
                message = f"Redis responding slowly ({response_time:.0f}ms)"
            elif connected_clients > 100:  # High connection count
                status = HealthStatus.DEGRADED
                message = f"High Redis connection count ({connected_clients})"
            else:
                status = HealthStatus.HEALTHY
                total_keys = details["total_keys"]
                message = f"Redis session storage healthy ({total_keys} cached items)"
            
            return ComponentHealth(
                name="sessions",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details=details
            )
            
        except redis.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="sessions",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="sessions",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis session check failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    def get_recovery_manager(self):
        """Get or create responsiveness recovery manager"""
        if self._recovery_manager is None:
            from responsiveness_error_recovery import get_responsiveness_recovery_manager
            self._recovery_manager = get_responsiveness_recovery_manager(
                db_manager=self.db_manager,
                system_optimizer=self.system_optimizer
            )
        return self._recovery_manager
    
    async def check_system_health_with_recovery(self) -> SystemHealth:
        """Check system health with responsiveness recovery integration"""
        try:
            # Get base system health
            system_health = await self.check_system_health()
            
            # Integrate with responsiveness recovery manager
            recovery_manager = self.get_recovery_manager()
            
            # Extend health check with recovery status
            enhanced_health_data = await recovery_manager.extend_health_check_error_handling(
                asdict(system_health)
            )
            
            # Update system health with recovery information
            if 'responsiveness_recovery' in enhanced_health_data:
                recovery_status = enhanced_health_data['responsiveness_recovery']
                
                # Add recovery component to system health
                recovery_component = ComponentHealth(
                    name="responsiveness_recovery",
                    status=HealthStatus.HEALTHY if recovery_status['status'] == 'healthy' else 
                           HealthStatus.DEGRADED if recovery_status['status'] == 'degraded' else 
                           HealthStatus.UNHEALTHY,
                    message=f"Recovery system {recovery_status['status']} - {len(recovery_status['issues'])} issues",
                    last_check=datetime.now(timezone.utc),
                    details=recovery_status['recovery_stats']
                )
                
                system_health.components['responsiveness_recovery'] = recovery_component
                
                # Update overall status if recovery system has issues
                if recovery_status['status'] == 'degraded' and system_health.status == HealthStatus.HEALTHY:
                    system_health.status = HealthStatus.DEGRADED
                elif recovery_status['status'] not in ['healthy', 'recovering']:
                    system_health.status = HealthStatus.UNHEALTHY
            
            # Store health check in history
            self.health_history.append({
                'timestamp': system_health.timestamp.isoformat(),
                'overall_status': system_health.status.value,
                'component_count': len(system_health.components),
                'recovery_active': 'responsiveness_recovery' in system_health.components
            })
            
            # Trim history if needed
            if len(self.health_history) > self.max_health_history:
                self.health_history = self.health_history[-self.max_health_history:]
            
            return system_health
            
        except Exception as e:
            logger.error(f"Error in enhanced health check: {e}")
            # Fallback to basic health check
            return await self.check_system_health()
    
    async def check_system_health(self) -> SystemHealth:
        """Check overall system health"""
        components = {}
        
        # Check all components
        components["database"] = await self.check_database_health()
        components["ollama"] = await self.check_ollama_health()
        components["activitypub"] = await self.check_activitypub_health()
        components["storage"] = await self.check_storage_health()
        components["sessions"] = await self.check_session_health()
        
        # Determine overall status
        statuses = [comp.status for comp in components.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return SystemHealth(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            components=components,
            uptime_seconds=self.get_uptime(),
            version=self.config.app.version if hasattr(self.config, 'app') else None
        )
    
    async def check_responsiveness_health(self) -> ComponentHealth:
        """Check system responsiveness monitoring capabilities"""
        start_time = time.time()
        
        try:
            # Check if SystemOptimizer is available for responsiveness monitoring
            if not self.system_optimizer:
                return ComponentHealth(
                    name="responsiveness",
                    status=HealthStatus.DEGRADED,
                    message="SystemOptimizer not available - responsiveness monitoring limited",
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.now(timezone.utc),
                    details={"system_optimizer_available": False}
                )
            
            # Get responsiveness analysis from SystemOptimizer
            responsiveness_analysis = self.system_optimizer.check_responsiveness()
            performance_metrics = self.system_optimizer.get_performance_metrics()
            
            # Get current system metrics for responsiveness assessment
            import psutil
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            response_time = (time.time() - start_time) * 1000
            
            # Analyze responsiveness health
            issues = responsiveness_analysis.get('issues', [])
            overall_responsive = responsiveness_analysis.get('responsive', True)
            
            # Determine health status based on responsiveness analysis
            if not overall_responsive:
                critical_issues = [issue for issue in issues if issue.get('severity') == 'critical']
                if critical_issues:
                    status = HealthStatus.UNHEALTHY
                    message = f"Critical responsiveness issues detected: {len(critical_issues)} critical, {len(issues)} total"
                else:
                    status = HealthStatus.DEGRADED
                    message = f"Responsiveness issues detected: {len(issues)} issues"
            else:
                status = HealthStatus.HEALTHY
                message = "System responsiveness healthy"
            
            # Check for automated cleanup triggers
            cleanup_triggered = performance_metrics.get('cleanup_triggered', False)
            if cleanup_triggered:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                message += " - Automated cleanup triggered"
            
            # Prepare detailed metrics
            details = {
                "responsive": overall_responsive,
                "issues_count": len(issues),
                "critical_issues": len([i for i in issues if i.get('severity') == 'critical']),
                "warning_issues": len([i for i in issues if i.get('severity') == 'warning']),
                "issues": issues,
                "cleanup_triggered": cleanup_triggered,
                "system_optimizer_available": self.system_optimizer is not None,
                "thresholds": {
                    "memory_warning": f"{self.responsiveness_config.memory_warning_threshold * 100:.0f}%",
                    "memory_critical": f"{self.responsiveness_config.memory_critical_threshold * 100:.0f}%",
                    "cpu_warning": f"{self.responsiveness_config.cpu_warning_threshold * 100:.0f}%",
                    "cpu_critical": f"{self.responsiveness_config.cpu_critical_threshold * 100:.0f}%",
                    "connection_pool_warning": f"{self.responsiveness_config.connection_pool_warning_threshold * 100:.0f}%"
                },
                "current_metrics": {
                    "memory_percent": memory.percent,
                    "cpu_percent": cpu_percent,
                    "connection_pool_utilization": performance_metrics.get('connection_pool_utilization', 0),
                    "background_tasks_count": performance_metrics.get('background_tasks_count', 0),
                    "avg_request_time": performance_metrics.get('avg_request_time', 0),
                    "slow_request_count": performance_metrics.get('slow_request_count', 0)
                },
                "monitoring_config": {
                    "monitoring_interval": self.responsiveness_config.monitoring_interval,
                    "cleanup_enabled": self.responsiveness_config.cleanup_enabled
                }
            }
            
            # Store metrics for trend analysis
            self._responsiveness_metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "responsive": overall_responsive,
                "issues_count": len(issues),
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "response_time_ms": response_time
            }
            self._last_responsiveness_check = time.time()
            
            return ComponentHealth(
                name="responsiveness",
                status=status,
                message=message,
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details=details
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Responsiveness health check failed: {e}")
            
            return ComponentHealth(
                name="responsiveness",
                status=HealthStatus.UNHEALTHY,
                message=f"Responsiveness monitoring failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e)}
            )
    
    async def check_system_health(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        logger.info("Starting system health check")
        
        # Run all component health checks concurrently
        tasks = [
            self.check_database_health(),
            self.check_ollama_health(),
            self.check_storage_health(),
            self.check_session_health(),
            self.check_responsiveness_health()
        ]
        
        component_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for i, result in enumerate(component_results):
            if isinstance(result, Exception):
                # Handle unexpected errors in health checks
                component_name = ["database", "ollama", "storage", "sessions", "responsiveness"][i]
                components[component_name] = ComponentHealth(
                    name=component_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(result)}",
                    last_check=datetime.now(timezone.utc),
                    details={"error": str(result)}
                )
                overall_status = HealthStatus.UNHEALTHY
            else:
                components[result.name] = result
                
                # Determine overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        # Get version info if available
        version = os.getenv("APP_VERSION", "unknown")
        
        system_health = SystemHealth(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            components=components,
            uptime_seconds=self.get_uptime(),
            version=version
        )
        
        logger.info(f"System health check completed: {overall_status.value}")
        return system_health
    
    def to_dict(self, system_health: SystemHealth) -> Dict[str, Any]:
        """Convert SystemHealth to dictionary for JSON serialization"""
        result = asdict(system_health)
        
        # Convert enums to strings
        result["status"] = system_health.status.value
        
        for component_name, component in result["components"].items():
            component["status"] = system_health.components[component_name].status.value
            if component["last_check"]:
                component["last_check"] = component["last_check"].isoformat()
        
        result["timestamp"] = system_health.timestamp.isoformat()
        
        return result
    
    def send_responsiveness_alerts(self, responsiveness_health: ComponentHealth) -> bool:
        """Send responsiveness alerts to admin notification system"""
        try:
            if responsiveness_health.status == HealthStatus.HEALTHY:
                return True  # No alerts needed for healthy status
            
            # Import notification helpers
            from app.services.notification.helpers.notification_helpers import send_admin_notification
            from models import NotificationType, NotificationPriority
            
            # Determine notification type and priority based on status
            if responsiveness_health.status == HealthStatus.UNHEALTHY:
                notification_type = NotificationType.ERROR
                priority = NotificationPriority.HIGH
                title = "Critical Responsiveness Issue"
            else:  # DEGRADED
                notification_type = NotificationType.WARNING
                priority = NotificationPriority.NORMAL
                title = "Responsiveness Warning"
            
            # Extract key issues from details
            details = responsiveness_health.details or {}
            issues = details.get('issues', [])
            current_metrics = details.get('current_metrics', {})
            
            # Build alert message
            message_parts = [responsiveness_health.message]
            
            # Add key metrics
            if current_metrics:
                metrics_info = []
                if 'memory_percent' in current_metrics:
                    metrics_info.append(f"Memory: {current_metrics['memory_percent']:.1f}%")
                if 'cpu_percent' in current_metrics:
                    metrics_info.append(f"CPU: {current_metrics['cpu_percent']:.1f}%")
                if 'connection_pool_utilization' in current_metrics:
                    metrics_info.append(f"Connection Pool: {current_metrics['connection_pool_utilization'] * 100:.1f}%")
                
                if metrics_info:
                    message_parts.append(f"Current metrics: {', '.join(metrics_info)}")
            
            # Add cleanup status
            if details.get('cleanup_triggered', False):
                message_parts.append("Automated cleanup has been triggered.")
            
            # Add recommendations for critical issues
            if responsiveness_health.status == HealthStatus.UNHEALTHY:
                message_parts.append("Immediate attention required to prevent system unresponsiveness.")
            
            alert_message = " ".join(message_parts)
            
            # Send admin notification
            success = send_admin_notification(
                message=alert_message,
                notification_type=notification_type,
                title=title,
                priority=priority,
                data={
                    'component': 'responsiveness',
                    'status': responsiveness_health.status.value,
                    'response_time_ms': responsiveness_health.response_time_ms,
                    'issues_count': len(issues),
                    'metrics': current_metrics,
                    'timestamp': responsiveness_health.last_check.isoformat() if responsiveness_health.last_check else None
                }
            )
            
            if success:
                logger.info(f"Responsiveness alert sent: {title} - {responsiveness_health.status.value}")
            else:
                logger.error(f"Failed to send responsiveness alert: {title}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending responsiveness alerts: {e}")
            return False