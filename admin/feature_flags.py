# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Feature Flag System for Multi-Tenant Admin Capabilities
Enables gradual rollout and safe deployment of admin features
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

class FeatureState(Enum):
    """Feature flag states"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    BETA = "beta"
    ROLLOUT = "rollout"
    DEPRECATED = "deprecated"

class RolloutStrategy(Enum):
    """Rollout strategies for features"""
    ALL_USERS = "all_users"
    ADMIN_ONLY = "admin_only"
    PERCENTAGE = "percentage"
    USER_LIST = "user_list"
    TIME_BASED = "time_based"

@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    name: str
    state: FeatureState
    description: str
    rollout_strategy: RolloutStrategy = RolloutStrategy.ALL_USERS
    rollout_percentage: int = 0
    allowed_users: List[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.allowed_users is None:
            self.allowed_users = []
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

class FeatureFlagManager:
    """Manages feature flags for admin capabilities"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.getenv('FEATURE_FLAGS_CONFIG', 'config/feature_flags.json')
        self.flags: Dict[str, FeatureFlag] = {}
        self.load_flags()
        
    def load_flags(self):
        """Load feature flags from configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self._parse_config(config)
            else:
                self._load_default_flags()
                self.save_flags()
        except Exception as e:
            logger.error(f"Failed to load feature flags: {e}")
            self._load_default_flags()
    
    def _parse_config(self, config: Dict[str, Any]):
        """Parse configuration into feature flags"""
        for name, flag_config in config.get('flags', {}).items():
            try:
                flag = FeatureFlag(
                    name=name,
                    state=FeatureState(flag_config.get('state', 'disabled')),
                    description=flag_config.get('description', ''),
                    rollout_strategy=RolloutStrategy(flag_config.get('rollout_strategy', 'all_users')),
                    rollout_percentage=flag_config.get('rollout_percentage', 0),
                    allowed_users=flag_config.get('allowed_users', []),
                    start_time=self._parse_datetime(flag_config.get('start_time')),
                    end_time=self._parse_datetime(flag_config.get('end_time')),
                    dependencies=flag_config.get('dependencies', []),
                    metadata=flag_config.get('metadata', {})
                )
                self.flags[name] = flag
            except Exception as e:
                logger.error(f"Failed to parse flag {name}: {e}")
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            logger.error(f"Invalid datetime format: {dt_str}")
            return None
    
    def _load_default_flags(self):
        """Load default feature flags for admin capabilities"""
        default_flags = {
            'multi_tenant_admin': FeatureFlag(
                name='multi_tenant_admin',
                state=FeatureState.DISABLED,
                description='Enable multi-tenant admin capabilities',
                rollout_strategy=RolloutStrategy.ADMIN_ONLY
            ),
            'admin_dashboard': FeatureFlag(
                name='admin_dashboard',
                state=FeatureState.DISABLED,
                description='Enable admin dashboard interface',
                rollout_strategy=RolloutStrategy.ADMIN_ONLY,
                dependencies=['multi_tenant_admin']
            ),
            'admin_job_management': FeatureFlag(
                name='admin_job_management',
                state=FeatureState.DISABLED,
                description='Enable admin job management capabilities',
                rollout_strategy=RolloutStrategy.ADMIN_ONLY,
                dependencies=['admin_dashboard']
            ),
            'admin_user_management': FeatureFlag(
                name='admin_user_management',
                state=FeatureState.DISABLED,
                description='Enable admin user management features',
                rollout_strategy=RolloutStrategy.ADMIN_ONLY,
                dependencies=['admin_dashboard']
            ),
            'system_monitoring': FeatureFlag(
                name='system_monitoring',
                state=FeatureState.DISABLED,
                description='Enable system monitoring and metrics',
                rollout_strategy=RolloutStrategy.ADMIN_ONLY,
                dependencies=['multi_tenant_admin']
            ),
            'alert_system': FeatureFlag(
                name='alert_system',
                state=FeatureState.DISABLED,
                description='Enable alert and notification system',
                rollout_strategy=RolloutStrategy.ADMIN_ONLY,
                dependencies=['system_monitoring']
            ),
            'performance_metrics': FeatureFlag(
                name='performance_metrics',
                state=FeatureState.DISABLED,
                description='Enable performance metrics collection',
                rollout_strategy=RolloutStrategy.ALL_USERS,
                dependencies=['system_monitoring']
            ),
            'enhanced_error_handling': FeatureFlag(
                name='enhanced_error_handling',
                state=FeatureState.DISABLED,
                description='Enable enhanced error handling and recovery',
                rollout_strategy=RolloutStrategy.ALL_USERS
            ),
            'audit_logging': FeatureFlag(
                name='audit_logging',
                state=FeatureState.DISABLED,
                description='Enable comprehensive audit logging',
                rollout_strategy=RolloutStrategy.ALL_USERS,
                dependencies=['multi_tenant_admin']
            ),
            'real_time_updates': FeatureFlag(
                name='real_time_updates',
                state=FeatureState.DISABLED,
                description='Enable real-time dashboard updates',
                rollout_strategy=RolloutStrategy.ADMIN_ONLY,
                dependencies=['admin_dashboard']
            )
        }
        
        self.flags = default_flags
    
    def save_flags(self):
        """Save feature flags to configuration file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config = {
                'flags': {},
                'updated_at': datetime.now().isoformat()
            }
            
            for name, flag in self.flags.items():
                config['flags'][name] = {
                    'state': flag.state.value,
                    'description': flag.description,
                    'rollout_strategy': flag.rollout_strategy.value,
                    'rollout_percentage': flag.rollout_percentage,
                    'allowed_users': flag.allowed_users,
                    'start_time': flag.start_time.isoformat() if flag.start_time else None,
                    'end_time': flag.end_time.isoformat() if flag.end_time else None,
                    'dependencies': flag.dependencies,
                    'metadata': flag.metadata
                }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save feature flags: {e}")
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None, 
                   user_role: Optional[str] = None) -> bool:
        """Check if a feature flag is enabled for a user"""
        flag = self.flags.get(flag_name)
        if not flag:
            logger.warning(f"Unknown feature flag: {flag_name}")
            return False
        
        # Check if flag is disabled
        if flag.state == FeatureState.DISABLED:
            return False
        
        # Check dependencies
        if not self._check_dependencies(flag):
            return False
        
        # Check time-based constraints
        if not self._check_time_constraints(flag):
            return False
        
        # Check rollout strategy
        return self._check_rollout_strategy(flag, user_id, user_role)
    
    def _check_dependencies(self, flag: FeatureFlag) -> bool:
        """Check if all dependencies are enabled"""
        for dep in flag.dependencies:
            if not self.is_enabled(dep):
                return False
        return True
    
    def _check_time_constraints(self, flag: FeatureFlag) -> bool:
        """Check time-based constraints"""
        now = datetime.now()
        
        if flag.start_time and now < flag.start_time:
            return False
        
        if flag.end_time and now > flag.end_time:
            return False
        
        return True
    
    def _check_rollout_strategy(self, flag: FeatureFlag, user_id: Optional[str], 
                               user_role: Optional[str]) -> bool:
        """Check rollout strategy"""
        if flag.state == FeatureState.ENABLED:
            return True
        
        if flag.rollout_strategy == RolloutStrategy.ALL_USERS:
            return True
        
        if flag.rollout_strategy == RolloutStrategy.ADMIN_ONLY:
            return user_role == 'admin'
        
        if flag.rollout_strategy == RolloutStrategy.USER_LIST:
            return user_id in flag.allowed_users
        
        if flag.rollout_strategy == RolloutStrategy.PERCENTAGE:
            if not user_id:
                return False
            # Simple hash-based percentage rollout
            user_hash = hash(user_id + flag.name) % 100
            return user_hash < flag.rollout_percentage
        
        return False
    
    def enable_flag(self, flag_name: str, rollout_strategy: RolloutStrategy = None,
                   rollout_percentage: int = None, allowed_users: List[str] = None):
        """Enable a feature flag"""
        if flag_name not in self.flags:
            logger.error(f"Unknown feature flag: {flag_name}")
            return False
        
        flag = self.flags[flag_name]
        flag.state = FeatureState.ENABLED
        
        if rollout_strategy:
            flag.rollout_strategy = rollout_strategy
        
        if rollout_percentage is not None:
            flag.rollout_percentage = rollout_percentage
        
        if allowed_users is not None:
            flag.allowed_users = allowed_users
        
        self.save_flags()
        logger.info(f"Enabled feature flag: {flag_name}")
        return True
    
    def disable_flag(self, flag_name: str):
        """Disable a feature flag"""
        if flag_name not in self.flags:
            logger.error(f"Unknown feature flag: {flag_name}")
            return False
        
        self.flags[flag_name].state = FeatureState.DISABLED
        self.save_flags()
        logger.info(f"Disabled feature flag: {flag_name}")
        return True
    
    def get_flag_status(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a feature flag"""
        flag = self.flags.get(flag_name)
        if not flag:
            return None
        
        return {
            'name': flag.name,
            'state': flag.state.value,
            'description': flag.description,
            'rollout_strategy': flag.rollout_strategy.value,
            'rollout_percentage': flag.rollout_percentage,
            'allowed_users': flag.allowed_users,
            'dependencies': flag.dependencies,
            'dependencies_met': self._check_dependencies(flag),
            'time_constraints_met': self._check_time_constraints(flag),
            'metadata': flag.metadata
        }
    
    def list_flags(self) -> Dict[str, Dict[str, Any]]:
        """List all feature flags with their status"""
        return {name: self.get_flag_status(name) for name in self.flags.keys()}

# Global feature flag manager instance
_feature_flag_manager = None

def get_feature_flag_manager() -> FeatureFlagManager:
    """Get global feature flag manager instance"""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager

def feature_flag(flag_name: str):
    """Decorator to check feature flags"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import session, abort
            
            manager = get_feature_flag_manager()
            user_id = session.get('user_id')
            user_role = session.get('role')
            
            if not manager.is_enabled(flag_name, str(user_id) if user_id else None, user_role):
                logger.warning(f"Feature {flag_name} not enabled for user {user_id}")
                abort(404)  # Feature not available
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def is_feature_enabled(flag_name: str, user_id: Optional[str] = None, 
                      user_role: Optional[str] = None) -> bool:
    """Check if a feature is enabled"""
    manager = get_feature_flag_manager()
    return manager.is_enabled(flag_name, user_id, user_role)