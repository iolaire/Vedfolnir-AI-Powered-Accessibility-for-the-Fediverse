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
from database import DatabaseManager
from models import ProcessingRun, Image, Post
from activitypub_client import ActivityPubClient
from ollama_caption_generator import OllamaCaptionGenerator

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
    """System health checker"""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.start_time = time.time()
        
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
                    
            elif database_url.startswith('sqlite'):
                # SQLite database health check
                try:
                    # Check if database directory exists and is writable
                    database_path = database_url.replace("sqlite:///", "")
                    database_dir = os.path.dirname(database_path)
                    
                    if not os.path.exists(database_dir):
                        issues.append(f"Database directory does not exist: {database_dir}")
                    elif not os.access(database_dir, os.W_OK):
                        issues.append(f"Database directory not writable: {database_dir}")
                    
                    # Get database file size
                    if os.path.exists(database_path):
                        db_size_bytes = os.path.getsize(database_path)
                        db_size_mb = round(db_size_bytes / (1024**2), 2)
                    else:
                        db_size_mb = 0
                    
                    # Get disk usage for database directory
                    import shutil
                    db_usage = shutil.disk_usage(database_dir)
                    
                    details.update({
                        "database_type": "SQLite",
                        "database_path": database_path,
                        "database_size_mb": db_size_mb,
                        "database_directory": database_dir,
                        "db_disk_free_gb": round(db_usage.free / (1024**3), 2),
                        "db_disk_total_gb": round(db_usage.total / (1024**3), 2)
                    })
                    
                    # Check disk space (warn if less than 1GB free)
                    if db_usage.free < 1024**3:
                        issues.append("Low disk space for database (less than 1GB free)")
                        
                except Exception as e:
                    issues.append(f"SQLite database check failed: {str(e)}")
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
                    message = "SQLite storage healthy"
            
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
            logger.error(f"Redis connection failed: {e}")
            
            return ComponentHealth(
                name="sessions",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e), "redis_host": redis_host, "redis_port": redis_port}
            )
            
        except redis.TimeoutError as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Redis timeout: {e}")
            
            return ComponentHealth(
                name="sessions",
                status=HealthStatus.DEGRADED,
                message=f"Redis timeout: {str(e)}",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                details={"error": str(e), "redis_host": redis_host, "redis_port": redis_port}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Session health check failed: {e}")
            
            return ComponentHealth(
                name="sessions",
                status=HealthStatus.UNHEALTHY,
                message=f"Session health check failed: {str(e)}",
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
            self.check_session_health()
        ]
        
        component_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for i, result in enumerate(component_results):
            if isinstance(result, Exception):
                # Handle unexpected errors in health checks
                component_name = ["database", "ollama", "storage", "sessions"][i]
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