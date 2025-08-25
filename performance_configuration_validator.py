# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance Configuration Validator

Implements validation for performance-related configuration values with
safe fallback mechanisms and warning system for problematic configurations.
"""

import logging
import psutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Validation result with details"""
    key: str
    severity: ValidationSeverity
    message: str
    current_value: Any
    suggested_value: Optional[Any] = None
    impact_description: Optional[str] = None


@dataclass
class SystemResources:
    """System resource information"""
    total_memory_mb: int
    available_memory_mb: int
    cpu_count: int
    cpu_usage_percent: float


class PerformanceConfigurationValidator:
    """
    Performance configuration validator with system resource awareness
    
    Features:
    - Memory limit validation against system capacity
    - Priority weight validation and ordering checks
    - Cross-configuration impact assessment
    - Safe fallback value recommendations
    - System resource-aware validation
    """
    
    def __init__(self):
        """Initialize the validator"""
        self._system_resources = self._get_system_resources()
        
        # Configuration limits and defaults
        self.MEMORY_LIMITS = {
            'min_mb': 512,
            'max_mb': 16384,
            'safe_system_usage_percent': 80.0  # Don't use more than 80% of system memory
        }
        
        self.PRIORITY_WEIGHT_LIMITS = {
            'min_weight': 0.1,
            'max_weight': 10.0
        }
        
        # Safe fallback values
        self.SAFE_FALLBACKS = {
            'max_memory_usage_mb': 2048,
            'processing_priority_weights': {
                'urgent': 4.0,
                'high': 3.0,
                'normal': 2.0,
                'low': 1.0
            }
        }
    
    def _get_system_resources(self) -> SystemResources:
        """Get current system resource information"""
        try:
            memory = psutil.virtual_memory()
            cpu_count = psutil.cpu_count()
            cpu_usage = psutil.cpu_percent(interval=1)
            
            return SystemResources(
                total_memory_mb=int(memory.total / (1024 * 1024)),
                available_memory_mb=int(memory.available / (1024 * 1024)),
                cpu_count=cpu_count,
                cpu_usage_percent=cpu_usage
            )
        except Exception as e:
            logger.error(f"Error getting system resources: {str(e)}")
            # Return conservative defaults
            return SystemResources(
                total_memory_mb=4096,  # 4GB default
                available_memory_mb=2048,  # 2GB available
                cpu_count=4,
                cpu_usage_percent=50.0
            )
    
    def validate_memory_configuration(self, memory_limit_mb: Any, max_concurrent_jobs: Any = 3) -> List[ValidationResult]:
        """
        Validate memory configuration against system resources
        
        Args:
            memory_limit_mb: Memory limit per job in MB
            max_concurrent_jobs: Maximum concurrent jobs
            
        Returns:
            List of validation results
        """
        results = []
        
        try:
            # Validate memory limit type
            if not isinstance(memory_limit_mb, (int, float)):
                results.append(ValidationResult(
                    key="max_memory_usage_mb",
                    severity=ValidationSeverity.ERROR,
                    message=f"Memory limit must be a number, got {type(memory_limit_mb).__name__}",
                    current_value=memory_limit_mb,
                    suggested_value=self.SAFE_FALLBACKS['max_memory_usage_mb']
                ))
                return results
            
            memory_limit_mb = int(memory_limit_mb)
            
            # Check minimum limit
            if memory_limit_mb < self.MEMORY_LIMITS['min_mb']:
                results.append(ValidationResult(
                    key="max_memory_usage_mb",
                    severity=ValidationSeverity.ERROR,
                    message=f"Memory limit {memory_limit_mb}MB is below minimum {self.MEMORY_LIMITS['min_mb']}MB",
                    current_value=memory_limit_mb,
                    suggested_value=self.MEMORY_LIMITS['min_mb'],
                    impact_description="Jobs may fail due to insufficient memory allocation"
                ))
            
            # Check maximum limit
            if memory_limit_mb > self.MEMORY_LIMITS['max_mb']:
                results.append(ValidationResult(
                    key="max_memory_usage_mb",
                    severity=ValidationSeverity.WARNING,
                    message=f"Memory limit {memory_limit_mb}MB is very high (max recommended: {self.MEMORY_LIMITS['max_mb']}MB)",
                    current_value=memory_limit_mb,
                    suggested_value=self.MEMORY_LIMITS['max_mb'],
                    impact_description="May cause system instability on machines with limited memory"
                ))
            
            # Check against system memory
            if isinstance(max_concurrent_jobs, (int, float)):
                total_memory_needed = memory_limit_mb * int(max_concurrent_jobs)
                safe_system_memory = int(self._system_resources.total_memory_mb * (self.MEMORY_LIMITS['safe_system_usage_percent'] / 100))
                
                if total_memory_needed > safe_system_memory:
                    suggested_memory_per_job = safe_system_memory // int(max_concurrent_jobs)
                    results.append(ValidationResult(
                        key="max_memory_usage_mb",
                        severity=ValidationSeverity.WARNING,
                        message=f"Total memory usage ({total_memory_needed}MB) may exceed safe system limits ({safe_system_memory}MB)",
                        current_value=memory_limit_mb,
                        suggested_value=suggested_memory_per_job,
                        impact_description=f"System has {self._system_resources.total_memory_mb}MB total memory. Consider reducing memory per job or concurrent jobs."
                    ))
                
                # Check against available memory
                if total_memory_needed > self._system_resources.available_memory_mb:
                    results.append(ValidationResult(
                        key="max_memory_usage_mb",
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Total memory usage ({total_memory_needed}MB) exceeds currently available memory ({self._system_resources.available_memory_mb}MB)",
                        current_value=memory_limit_mb,
                        suggested_value=self._system_resources.available_memory_mb // int(max_concurrent_jobs),
                        impact_description="Jobs will likely fail due to insufficient available memory"
                    ))
            
            # Provide optimization suggestions
            if memory_limit_mb > 4096:  # 4GB
                results.append(ValidationResult(
                    key="max_memory_usage_mb",
                    severity=ValidationSeverity.INFO,
                    message=f"High memory limit ({memory_limit_mb}MB) detected. Consider if this is necessary for your workload.",
                    current_value=memory_limit_mb,
                    impact_description="Higher memory limits may reduce the number of concurrent jobs that can run safely"
                ))
            
        except Exception as e:
            logger.error(f"Error validating memory configuration: {str(e)}")
            results.append(ValidationResult(
                key="max_memory_usage_mb",
                severity=ValidationSeverity.ERROR,
                message=f"Validation error: {str(e)}",
                current_value=memory_limit_mb,
                suggested_value=self.SAFE_FALLBACKS['max_memory_usage_mb']
            ))
        
        return results
    
    def validate_priority_weights(self, priority_weights: Any) -> List[ValidationResult]:
        """
        Validate priority weight configuration
        
        Args:
            priority_weights: Priority weights dictionary
            
        Returns:
            List of validation results
        """
        results = []
        
        try:
            # Check if it's a dictionary
            if not isinstance(priority_weights, dict):
                results.append(ValidationResult(
                    key="processing_priority_weights",
                    severity=ValidationSeverity.ERROR,
                    message=f"Priority weights must be a dictionary, got {type(priority_weights).__name__}",
                    current_value=priority_weights,
                    suggested_value=self.SAFE_FALLBACKS['processing_priority_weights']
                ))
                return results
            
            # Check required keys
            required_keys = ['urgent', 'high', 'normal', 'low']
            missing_keys = [key for key in required_keys if key not in priority_weights]
            
            if missing_keys:
                results.append(ValidationResult(
                    key="processing_priority_weights",
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required priority weight keys: {', '.join(missing_keys)}",
                    current_value=priority_weights,
                    suggested_value=self.SAFE_FALLBACKS['processing_priority_weights'],
                    impact_description="Missing priority levels will use default values"
                ))
            
            # Validate individual weights
            valid_weights = {}
            for key in required_keys:
                if key in priority_weights:
                    try:
                        weight = float(priority_weights[key])
                        
                        # Check range
                        if weight < self.PRIORITY_WEIGHT_LIMITS['min_weight']:
                            results.append(ValidationResult(
                                key=f"processing_priority_weights.{key}",
                                severity=ValidationSeverity.WARNING,
                                message=f"Priority weight '{key}' ({weight}) is below minimum ({self.PRIORITY_WEIGHT_LIMITS['min_weight']})",
                                current_value=weight,
                                suggested_value=self.PRIORITY_WEIGHT_LIMITS['min_weight']
                            ))
                        elif weight > self.PRIORITY_WEIGHT_LIMITS['max_weight']:
                            results.append(ValidationResult(
                                key=f"processing_priority_weights.{key}",
                                severity=ValidationSeverity.WARNING,
                                message=f"Priority weight '{key}' ({weight}) is above maximum ({self.PRIORITY_WEIGHT_LIMITS['max_weight']})",
                                current_value=weight,
                                suggested_value=self.PRIORITY_WEIGHT_LIMITS['max_weight']
                            ))
                        else:
                            valid_weights[key] = weight
                            
                    except (ValueError, TypeError):
                        results.append(ValidationResult(
                            key=f"processing_priority_weights.{key}",
                            severity=ValidationSeverity.ERROR,
                            message=f"Priority weight '{key}' must be a number, got {priority_weights[key]}",
                            current_value=priority_weights[key],
                            suggested_value=self.SAFE_FALLBACKS['processing_priority_weights'][key]
                        ))
            
            # Check priority ordering (urgent should be highest)
            if len(valid_weights) >= 4:
                weights_list = [
                    ('urgent', valid_weights.get('urgent', 0)),
                    ('high', valid_weights.get('high', 0)),
                    ('normal', valid_weights.get('normal', 0)),
                    ('low', valid_weights.get('low', 0))
                ]
                
                # Check if weights are in descending order
                for i in range(len(weights_list) - 1):
                    current_name, current_weight = weights_list[i]
                    next_name, next_weight = weights_list[i + 1]
                    
                    if current_weight < next_weight:
                        results.append(ValidationResult(
                            key="processing_priority_weights",
                            severity=ValidationSeverity.WARNING,
                            message=f"Priority weight ordering issue: {current_name} ({current_weight}) should be >= {next_name} ({next_weight})",
                            current_value=priority_weights,
                            suggested_value=self.SAFE_FALLBACKS['processing_priority_weights'],
                            impact_description="Incorrect ordering may cause lower priority jobs to be processed before higher priority ones"
                        ))
                        break
            
            # Check for extreme ratios
            if len(valid_weights) >= 2:
                max_weight = max(valid_weights.values())
                min_weight = min(valid_weights.values())
                
                if min_weight > 0 and (max_weight / min_weight) > 20:
                    results.append(ValidationResult(
                        key="processing_priority_weights",
                        severity=ValidationSeverity.WARNING,
                        message=f"Large priority weight ratio detected ({max_weight:.1f}:{min_weight:.1f}). This may cause starvation of low priority jobs.",
                        current_value=priority_weights,
                        impact_description="Consider reducing the ratio between highest and lowest priority weights"
                    ))
            
        except Exception as e:
            logger.error(f"Error validating priority weights: {str(e)}")
            results.append(ValidationResult(
                key="processing_priority_weights",
                severity=ValidationSeverity.ERROR,
                message=f"Validation error: {str(e)}",
                current_value=priority_weights,
                suggested_value=self.SAFE_FALLBACKS['processing_priority_weights']
            ))
        
        return results
    
    def validate_performance_configuration(self, config: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate complete performance configuration
        
        Args:
            config: Performance configuration dictionary
            
        Returns:
            List of validation results
        """
        results = []
        
        try:
            # Validate memory configuration
            memory_limit = config.get('max_memory_usage_mb')
            max_concurrent_jobs = config.get('max_concurrent_jobs', 3)
            
            if memory_limit is not None:
                memory_results = self.validate_memory_configuration(memory_limit, max_concurrent_jobs)
                results.extend(memory_results)
            
            # Validate priority weights
            priority_weights = config.get('processing_priority_weights')
            if priority_weights is not None:
                priority_results = self.validate_priority_weights(priority_weights)
                results.extend(priority_results)
            
            # Cross-configuration validation
            cross_validation_results = self._validate_cross_configuration_impacts(config)
            results.extend(cross_validation_results)
            
        except Exception as e:
            logger.error(f"Error in performance configuration validation: {str(e)}")
            results.append(ValidationResult(
                key="performance_configuration",
                severity=ValidationSeverity.ERROR,
                message=f"Configuration validation error: {str(e)}",
                current_value=config
            ))
        
        return results
    
    def _validate_cross_configuration_impacts(self, config: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate cross-configuration impacts and dependencies
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of validation results
        """
        results = []
        
        try:
            memory_limit = config.get('max_memory_usage_mb')
            max_concurrent_jobs = config.get('max_concurrent_jobs')
            queue_size_limit = config.get('queue_size_limit')
            
            # Memory vs concurrent jobs validation
            if memory_limit and max_concurrent_jobs:
                try:
                    total_memory = int(memory_limit) * int(max_concurrent_jobs)
                    
                    # Check against system memory
                    if total_memory > self._system_resources.total_memory_mb:
                        results.append(ValidationResult(
                            key="performance_configuration",
                            severity=ValidationSeverity.CRITICAL,
                            message=f"Total memory allocation ({total_memory}MB) exceeds system memory ({self._system_resources.total_memory_mb}MB)",
                            current_value={"memory_per_job": memory_limit, "concurrent_jobs": max_concurrent_jobs},
                            impact_description="System will likely become unstable or jobs will fail"
                        ))
                    
                    # Warn about high memory usage
                    safe_limit = int(self._system_resources.total_memory_mb * 0.8)
                    if total_memory > safe_limit:
                        results.append(ValidationResult(
                            key="performance_configuration",
                            severity=ValidationSeverity.WARNING,
                            message=f"Total memory allocation ({total_memory}MB) exceeds safe limit ({safe_limit}MB)",
                            current_value={"memory_per_job": memory_limit, "concurrent_jobs": max_concurrent_jobs},
                            impact_description="May cause system performance degradation"
                        ))
                        
                except (ValueError, TypeError):
                    pass  # Skip if values aren't numeric
            
            # Queue size vs concurrent jobs validation
            if queue_size_limit and max_concurrent_jobs:
                try:
                    queue_limit = int(queue_size_limit)
                    concurrent_limit = int(max_concurrent_jobs)
                    
                    if queue_limit < concurrent_limit * 2:
                        results.append(ValidationResult(
                            key="performance_configuration",
                            severity=ValidationSeverity.INFO,
                            message=f"Queue size limit ({queue_limit}) is small relative to concurrent jobs ({concurrent_limit}). Consider increasing for better throughput.",
                            current_value={"queue_size_limit": queue_limit, "max_concurrent_jobs": concurrent_limit},
                            suggested_value={"queue_size_limit": concurrent_limit * 5},
                            impact_description="Small queue may limit job throughput during peak usage"
                        ))
                        
                except (ValueError, TypeError):
                    pass  # Skip if values aren't numeric
            
        except Exception as e:
            logger.error(f"Error in cross-configuration validation: {str(e)}")
        
        return results
    
    def get_safe_fallback_value(self, key: str) -> Any:
        """
        Get safe fallback value for a configuration key
        
        Args:
            key: Configuration key
            
        Returns:
            Safe fallback value
        """
        return self.SAFE_FALLBACKS.get(key)
    
    def assess_configuration_impact(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the impact of configuration changes
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Impact assessment dictionary
        """
        try:
            impact = {
                'system_resource_usage': {},
                'performance_implications': [],
                'stability_risks': [],
                'recommendations': []
            }
            
            # Assess memory impact
            memory_limit = config.get('max_memory_usage_mb')
            max_concurrent_jobs = config.get('max_concurrent_jobs', 3)
            
            if memory_limit and max_concurrent_jobs:
                try:
                    total_memory = int(memory_limit) * int(max_concurrent_jobs)
                    memory_usage_percent = (total_memory / self._system_resources.total_memory_mb) * 100
                    
                    impact['system_resource_usage']['memory'] = {
                        'total_allocation_mb': total_memory,
                        'system_usage_percent': memory_usage_percent,
                        'available_memory_mb': self._system_resources.available_memory_mb
                    }
                    
                    if memory_usage_percent > 80:
                        impact['stability_risks'].append("High memory usage may cause system instability")
                    
                    if memory_usage_percent > 50:
                        impact['performance_implications'].append("Moderate to high memory usage expected")
                    
                except (ValueError, TypeError):
                    pass
            
            # Assess priority weight impact
            priority_weights = config.get('processing_priority_weights')
            if priority_weights and isinstance(priority_weights, dict):
                try:
                    weights = [float(w) for w in priority_weights.values() if isinstance(w, (int, float))]
                    if weights:
                        max_weight = max(weights)
                        min_weight = min(weights)
                        
                        if min_weight > 0:
                            ratio = max_weight / min_weight
                            if ratio > 10:
                                impact['performance_implications'].append(f"High priority ratio ({ratio:.1f}:1) may cause job starvation")
                            
                except (ValueError, TypeError):
                    pass
            
            # Generate recommendations
            if impact['stability_risks']:
                impact['recommendations'].append("Consider reducing memory limits or concurrent jobs to improve stability")
            
            if impact['performance_implications']:
                impact['recommendations'].append("Monitor system performance after applying these settings")
            
            if not impact['stability_risks'] and not impact['performance_implications']:
                impact['recommendations'].append("Configuration appears safe for your system")
            
            return impact
            
        except Exception as e:
            logger.error(f"Error assessing configuration impact: {str(e)}")
            return {'error': str(e)}
    
    def get_system_resource_info(self) -> Dict[str, Any]:
        """
        Get current system resource information
        
        Returns:
            System resource information dictionary
        """
        try:
            # Refresh system resources
            self._system_resources = self._get_system_resources()
            
            return {
                'memory': {
                    'total_mb': self._system_resources.total_memory_mb,
                    'available_mb': self._system_resources.available_memory_mb,
                    'usage_percent': ((self._system_resources.total_memory_mb - self._system_resources.available_memory_mb) / self._system_resources.total_memory_mb) * 100
                },
                'cpu': {
                    'count': self._system_resources.cpu_count,
                    'usage_percent': self._system_resources.cpu_usage_percent
                },
                'recommendations': {
                    'safe_memory_limit_mb': int(self._system_resources.available_memory_mb * 0.8),
                    'max_concurrent_jobs_for_2gb_per_job': self._system_resources.available_memory_mb // 2048
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system resource info: {str(e)}")
            return {'error': str(e)}