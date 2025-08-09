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
        """Check file storage health"""
        start_time = time.time()
        
        try:
            # Check if storage directories exist and are writable
            images_dir = self.config.storage.images_dir
            database_dir = os.path.dirname(self.config.storage.database_url.replace("sqlite:///", ""))
            
            issues = []
            
            # Check images directory
            if not os.path.exists(images_dir):
                issues.append(f"Images directory does not exist: {images_dir}")
            elif not os.access(images_dir, os.W_OK):
                issues.append(f"Images directory not writable: {images_dir}")
            
            # Check database directory
            if not os.path.exists(database_dir):
                issues.append(f"Database directory does not exist: {database_dir}")
            elif not os.access(database_dir, os.W_OK):
                issues.append(f"Database directory not writable: {database_dir}")
            
            # Get storage statistics
            try:
                import shutil
                images_usage = shutil.disk_usage(images_dir)
                db_usage = shutil.disk_usage(database_dir)
                
                # Count stored images
                image_count = len([f for f in os.listdir(images_dir) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))])
                
                details = {
                    "images_directory": images_dir,
                    "database_directory": database_dir,
                    "stored_images": image_count,
                    "images_disk_free_gb": round(images_usage.free / (1024**3), 2),
                    "images_disk_total_gb": round(images_usage.total / (1024**3), 2),
                    "db_disk_free_gb": round(db_usage.free / (1024**3), 2),
                    "db_disk_total_gb": round(db_usage.total / (1024**3), 2)
                }
                
                # Check disk space (warn if less than 1GB free)
                if images_usage.free < 1024**3 or db_usage.free < 1024**3:
                    issues.append("Low disk space (less than 1GB free)")
                    
            except Exception as e:
                details = {"error": f"Could not get storage statistics: {str(e)}"}
            
            response_time = (time.time() - start_time) * 1000
            
            if issues:
                status = HealthStatus.UNHEALTHY if any("not exist" in issue or "not writable" in issue for issue in issues) else HealthStatus.DEGRADED
                message = "; ".join(issues)
            else:
                status = HealthStatus.HEALTHY
                message = "Storage system healthy"
            
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
    
    async def check_system_health(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        logger.info("Starting system health check")
        
        # Run all component health checks concurrently
        tasks = [
            self.check_database_health(),
            self.check_ollama_health(),
            self.check_activitypub_health(),
            self.check_storage_health()
        ]
        
        component_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for i, result in enumerate(component_results):
            if isinstance(result, Exception):
                # Handle unexpected errors in health checks
                component_name = ["database", "ollama", "activitypub", "storage"][i]
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