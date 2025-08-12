#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Configuration Management Utility

Provides tools for managing session configuration, validating settings,
and applying environment-specific configurations.
"""

import os
import sys
import json
import argparse
from datetime import timedelta
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from session_config import get_session_config, reload_session_config, SessionConfig, SessionEnvironment

def validate_configuration() -> Dict[str, Any]:
    """Validate current session configuration"""
    print("🔍 Validating session configuration...")
    
    config = get_session_config()
    issues = config.validate_configuration()
    
    result = {
        'valid': len(issues) == 0,
        'issues': issues,
        'environment': config.environment.value,
        'summary': config.get_config_summary()
    }
    
    if result['valid']:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    return result

def show_configuration() -> Dict[str, Any]:
    """Display current session configuration"""
    print("📋 Current session configuration:")
    
    config = get_session_config()
    
    config_data = {
        'environment': config.environment.value,
        'debug_mode': config.debug_mode,
        'timeout': {
            'session_lifetime_hours': config.timeout.session_lifetime.total_seconds() / 3600,
            'idle_timeout_hours': config.timeout.idle_timeout.total_seconds() / 3600,
            'absolute_timeout_days': config.timeout.absolute_timeout.total_seconds() / (24 * 3600),
            'expiration_grace_minutes': config.timeout.expiration_grace_period.total_seconds() / 60,
            'cleanup_grace_minutes': config.timeout.cleanup_grace_period.total_seconds() / 60,
            'warning_threshold_minutes': config.timeout.expiration_warning_threshold.total_seconds() / 60
        },
        'cleanup': {
            'cleanup_interval_minutes': config.cleanup.cleanup_interval.total_seconds() / 60,
            'batch_cleanup_interval_hours': config.cleanup.batch_cleanup_interval.total_seconds() / 3600,
            'deep_cleanup_interval_hours': config.cleanup.deep_cleanup_interval.total_seconds() / 3600,
            'cleanup_batch_size': config.cleanup.cleanup_batch_size,
            'max_cleanup_batches_per_run': config.cleanup.max_cleanup_batches_per_run,
            'max_expired_sessions_threshold': config.cleanup.max_expired_sessions_threshold,
            'cleanup_trigger_threshold': config.cleanup.cleanup_trigger_threshold,
            'expired_session_retention_days': config.cleanup.expired_session_retention_days,
            'audit_log_retention_days': config.cleanup.audit_log_retention_days
        },
        'sync': {
            'sync_check_interval_seconds': config.sync.sync_check_interval.total_seconds(),
            'heartbeat_interval_seconds': config.sync.heartbeat_interval.total_seconds(),
            'sync_timeout_seconds': config.sync.sync_timeout.total_seconds(),
            'tab_response_timeout_seconds': config.sync.tab_response_timeout.total_seconds(),
            'localStorage_key_prefix': config.sync.localStorage_key_prefix,
            'max_sync_data_size': config.sync.max_sync_data_size
        },
        'security': {
            'enable_fingerprinting': config.security.enable_fingerprinting,
            'enable_suspicious_activity_detection': config.security.enable_suspicious_activity_detection,
            'enable_audit_logging': config.security.enable_audit_logging,
            'max_concurrent_sessions_per_user': config.security.max_concurrent_sessions_per_user,
            'suspicious_activity_threshold': config.security.suspicious_activity_threshold,
            'max_platform_switches_per_hour': config.security.max_platform_switches_per_hour,
            'security_check_interval_minutes': config.security.security_check_interval.total_seconds() / 60
        },
        'monitoring': {
            'enable_performance_monitoring': config.monitoring.enable_performance_monitoring,
            'enable_metrics_collection': config.monitoring.enable_metrics_collection,
            'enable_health_checks': config.monitoring.enable_health_checks,
            'metrics_collection_interval_seconds': config.monitoring.metrics_collection_interval.total_seconds(),
            'health_check_interval_seconds': config.monitoring.health_check_interval.total_seconds(),
            'metrics_buffer_size': config.monitoring.metrics_buffer_size,
            'events_buffer_size': config.monitoring.events_buffer_size,
            'alert_thresholds': config.monitoring.alert_thresholds
        },
        'features': {
            'enable_cross_tab_sync': config.features.enable_cross_tab_sync,
            'enable_platform_switching': config.features.enable_platform_switching,
            'enable_session_persistence': config.features.enable_session_persistence,
            'enable_optimistic_ui_updates': config.features.enable_optimistic_ui_updates,
            'enable_background_cleanup': config.features.enable_background_cleanup,
            'enable_session_analytics': config.features.enable_session_analytics,
            'enable_session_clustering': config.features.enable_session_clustering,
            'enable_distributed_sessions': config.features.enable_distributed_sessions,
            'enable_session_caching': config.features.enable_session_caching
        },
        'custom_settings': config.custom_settings
    }
    
    print(json.dumps(config_data, indent=2))
    return config_data

def set_environment(environment: str) -> bool:
    """Set session management environment"""
    try:
        env = SessionEnvironment(environment.lower())
        print(f"🔧 Setting session environment to: {env.value}")
        
        # Update environment variable
        os.environ['SESSION_ENVIRONMENT'] = env.value
        
        # Reload configuration
        reload_session_config()
        
        print("✅ Environment updated successfully")
        return True
        
    except ValueError:
        valid_envs = [e.value for e in SessionEnvironment]
        print(f"❌ Invalid environment: {environment}")
        print(f"   Valid environments: {', '.join(valid_envs)}")
        return False

def optimize_for_environment(environment: str) -> bool:
    """Apply optimized settings for specific environment"""
    try:
        env = SessionEnvironment(environment.lower())
        print(f"🚀 Optimizing session configuration for: {env.value}")
        
        # Get environment-specific optimizations
        optimizations = {
            SessionEnvironment.DEVELOPMENT: {
                'SESSION_LIFETIME_SECONDS': str(24 * 3600),  # 24 hours
                'SESSION_CLEANUP_INTERVAL_SECONDS': str(15 * 60),  # 15 minutes
                'SESSION_DEBUG_MODE': 'true',
                'SESSION_ENABLE_PERFORMANCE_MONITORING': 'true',
                'SESSION_ENABLE_ANALYTICS': 'true'
            },
            SessionEnvironment.TESTING: {
                'SESSION_LIFETIME_SECONDS': str(30 * 60),  # 30 minutes
                'SESSION_CLEANUP_INTERVAL_SECONDS': str(5 * 60),  # 5 minutes
                'SESSION_DEBUG_MODE': 'true',
                'SESSION_ENABLE_PERFORMANCE_MONITORING': 'false',
                'SESSION_ENABLE_ANALYTICS': 'false',
                'SESSION_CLEANUP_BATCH_SIZE': '10'
            },
            SessionEnvironment.STAGING: {
                'SESSION_LIFETIME_SECONDS': str(48 * 3600),  # 48 hours
                'SESSION_CLEANUP_INTERVAL_SECONDS': str(30 * 60),  # 30 minutes
                'SESSION_DEBUG_MODE': 'false',
                'SESSION_ENABLE_PERFORMANCE_MONITORING': 'true',
                'SESSION_ENABLE_ANALYTICS': 'true'
            },
            SessionEnvironment.PRODUCTION: {
                'SESSION_LIFETIME_SECONDS': str(48 * 3600),  # 48 hours
                'SESSION_CLEANUP_INTERVAL_SECONDS': str(60 * 60),  # 1 hour
                'SESSION_DEBUG_MODE': 'false',
                'SESSION_ENABLE_PERFORMANCE_MONITORING': 'true',
                'SESSION_ENABLE_ANALYTICS': 'true',
                'SESSION_CLEANUP_BATCH_SIZE': '200',
                'SESSION_MAX_CLEANUP_BATCHES': '20'
            }
        }
        
        env_settings = optimizations.get(env, {})
        
        # Apply optimizations
        for key, value in env_settings.items():
            os.environ[key] = value
            print(f"   Set {key} = {value}")
        
        # Set environment
        os.environ['SESSION_ENVIRONMENT'] = env.value
        
        # Reload configuration
        reload_session_config()
        
        print("✅ Environment optimization completed")
        return True
        
    except ValueError:
        valid_envs = [e.value for e in SessionEnvironment]
        print(f"❌ Invalid environment: {environment}")
        print(f"   Valid environments: {', '.join(valid_envs)}")
        return False

def generate_env_template() -> str:
    """Generate environment template with current settings"""
    print("📝 Generating session configuration template...")
    
    config = get_session_config()
    
    template = f"""# Session Management Configuration Template
# Generated automatically - customize as needed

# Session Environment
SESSION_ENVIRONMENT={config.environment.value}
SESSION_DEBUG_MODE={str(config.debug_mode).lower()}

# Session Timeout Configuration
SESSION_LIFETIME_SECONDS={int(config.timeout.session_lifetime.total_seconds())}
SESSION_IDLE_TIMEOUT_SECONDS={int(config.timeout.idle_timeout.total_seconds())}
SESSION_ABSOLUTE_TIMEOUT_SECONDS={int(config.timeout.absolute_timeout.total_seconds())}
SESSION_EXPIRATION_GRACE_SECONDS={int(config.timeout.expiration_grace_period.total_seconds())}
SESSION_CLEANUP_GRACE_SECONDS={int(config.timeout.cleanup_grace_period.total_seconds())}
SESSION_WARNING_THRESHOLD_SECONDS={int(config.timeout.expiration_warning_threshold.total_seconds())}

# Session Cleanup Configuration
SESSION_CLEANUP_INTERVAL_SECONDS={int(config.cleanup.cleanup_interval.total_seconds())}
SESSION_BATCH_CLEANUP_INTERVAL_SECONDS={int(config.cleanup.batch_cleanup_interval.total_seconds())}
SESSION_DEEP_CLEANUP_INTERVAL_SECONDS={int(config.cleanup.deep_cleanup_interval.total_seconds())}
SESSION_CLEANUP_BATCH_SIZE={config.cleanup.cleanup_batch_size}
SESSION_MAX_CLEANUP_BATCHES={config.cleanup.max_cleanup_batches_per_run}
SESSION_MAX_EXPIRED_THRESHOLD={config.cleanup.max_expired_sessions_threshold}
SESSION_CLEANUP_TRIGGER_THRESHOLD={config.cleanup.cleanup_trigger_threshold}
SESSION_EXPIRED_RETENTION_DAYS={config.cleanup.expired_session_retention_days}
SESSION_AUDIT_RETENTION_DAYS={config.cleanup.audit_log_retention_days}

# Cross-Tab Synchronization Configuration
SESSION_SYNC_CHECK_INTERVAL_SECONDS={int(config.sync.sync_check_interval.total_seconds())}
SESSION_HEARTBEAT_INTERVAL_SECONDS={int(config.sync.heartbeat_interval.total_seconds())}
SESSION_SYNC_TIMEOUT_SECONDS={int(config.sync.sync_timeout.total_seconds())}
SESSION_TAB_RESPONSE_TIMEOUT_SECONDS={int(config.sync.tab_response_timeout.total_seconds())}
SESSION_LOCALSTORAGE_PREFIX={config.sync.localStorage_key_prefix}
SESSION_MAX_SYNC_DATA_SIZE={config.sync.max_sync_data_size}

# Session Security Configuration
SESSION_ENABLE_FINGERPRINTING={str(config.security.enable_fingerprinting).lower()}
SESSION_ENABLE_SUSPICIOUS_DETECTION={str(config.security.enable_suspicious_activity_detection).lower()}
SESSION_ENABLE_AUDIT_LOGGING={str(config.security.enable_audit_logging).lower()}
SESSION_MAX_CONCURRENT_PER_USER={config.security.max_concurrent_sessions_per_user}
SESSION_SUSPICIOUS_ACTIVITY_THRESHOLD={config.security.suspicious_activity_threshold}
SESSION_MAX_PLATFORM_SWITCHES_PER_HOUR={config.security.max_platform_switches_per_hour}
SESSION_SECURITY_CHECK_INTERVAL_SECONDS={int(config.security.security_check_interval.total_seconds())}

# Session Monitoring Configuration
SESSION_ENABLE_PERFORMANCE_MONITORING={str(config.monitoring.enable_performance_monitoring).lower()}
SESSION_ENABLE_METRICS_COLLECTION={str(config.monitoring.enable_metrics_collection).lower()}
SESSION_ENABLE_HEALTH_CHECKS={str(config.monitoring.enable_health_checks).lower()}
SESSION_METRICS_INTERVAL_SECONDS={int(config.monitoring.metrics_collection_interval.total_seconds())}
SESSION_HEALTH_CHECK_INTERVAL_SECONDS={int(config.monitoring.health_check_interval.total_seconds())}
SESSION_METRICS_BUFFER_SIZE={config.monitoring.metrics_buffer_size}
SESSION_EVENTS_BUFFER_SIZE={config.monitoring.events_buffer_size}

# Session Alert Thresholds
"""
    
    for key, value in config.monitoring.alert_thresholds.items():
        template += f"SESSION_ALERT_{key.upper()}={value}\n"
    
    template += f"""
# Session Feature Flags
SESSION_FEATURE_CROSS_TAB_SYNC={str(config.features.enable_cross_tab_sync).lower()}
SESSION_FEATURE_PLATFORM_SWITCHING={str(config.features.enable_platform_switching).lower()}
SESSION_FEATURE_PERSISTENCE={str(config.features.enable_session_persistence).lower()}
SESSION_FEATURE_OPTIMISTIC_UI={str(config.features.enable_optimistic_ui_updates).lower()}
SESSION_FEATURE_BACKGROUND_CLEANUP={str(config.features.enable_background_cleanup).lower()}
SESSION_FEATURE_ANALYTICS={str(config.features.enable_session_analytics).lower()}
SESSION_FEATURE_CLUSTERING={str(config.features.enable_session_clustering).lower()}
SESSION_FEATURE_DISTRIBUTED={str(config.features.enable_distributed_sessions).lower()}
SESSION_FEATURE_CACHING={str(config.features.enable_session_caching).lower()}

# Custom Session Settings
"""
    
    for key, value in config.custom_settings.items():
        template += f"SESSION_CUSTOM_{key.upper()}={value}\n"
    
    return template

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Session Configuration Management Utility')
    parser.add_argument('--validate', action='store_true', help='Validate current configuration')
    parser.add_argument('--show', action='store_true', help='Show current configuration')
    parser.add_argument('--set-env', type=str, help='Set session environment (development, testing, staging, production)')
    parser.add_argument('--optimize-for', type=str, help='Optimize configuration for environment')
    parser.add_argument('--generate-template', action='store_true', help='Generate environment template')
    parser.add_argument('--output', type=str, help='Output file for generated template')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    try:
        if args.validate:
            result = validate_configuration()
            if not result['valid']:
                sys.exit(1)
        
        if args.show:
            show_configuration()
        
        if args.set_env:
            if not set_environment(args.set_env):
                sys.exit(1)
        
        if args.optimize_for:
            if not optimize_for_environment(args.optimize_for):
                sys.exit(1)
        
        if args.generate_template:
            template = generate_env_template()
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(template)
                print(f"✅ Template saved to: {args.output}")
            else:
                print(template)
    
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()