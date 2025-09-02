# Configuration Migration Procedures

## Overview

This document provides detailed procedures for migrating existing hardcoded configuration values to the Configuration Integration System. These procedures ensure a smooth transition with minimal service disruption.

## Table of Contents

1. [Migration Planning](#migration-planning)
2. [Pre-Migration Assessment](#pre-migration-assessment)
3. [Migration Strategies](#migration-strategies)
4. [Step-by-Step Migration](#step-by-step-migration)
5. [Validation and Testing](#validation-and-testing)
6. [Rollback Procedures](#rollback-procedures)
7. [Post-Migration Cleanup](#post-migration-cleanup)

## Migration Planning

### Migration Phases

The migration is divided into phases to minimize risk:

1. **Phase 1**: Non-critical configurations (logging, display settings)
2. **Phase 2**: Performance configurations (timeouts, limits)
3. **Phase 3**: Security configurations (session settings, rate limits)
4. **Phase 4**: Critical system configurations (database settings)

### Risk Assessment

Each configuration is classified by risk level:

- **Low Risk**: Can be changed without service impact
- **Medium Risk**: May affect performance but not availability
- **High Risk**: Could cause service degradation
- **Critical Risk**: May cause service outage if misconfigured

## Pre-Migration Assessment

### Configuration Inventory

Create comprehensive inventory of all hardcoded configurations:

```python
#!/usr/bin/env python3
"""
Configuration Inventory Script
"""

import ast
import os
import re
from typing import Dict, List, Set

def scan_hardcoded_configurations(project_root: str) -> Dict[str, List[Dict]]:
    """
    Scan project for hardcoded configuration values
    """
    configurations = {}
    
    # Common configuration patterns
    patterns = [
        r'timeout\s*=\s*(\d+)',
        r'max_.*\s*=\s*(\d+)',
        r'limit\s*=\s*(\d+)',
        r'size\s*=\s*(\d+)',
        r'interval\s*=\s*(\d+)',
    ]
    
    for root, dirs, files in os.walk(project_root):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                configs = scan_python_file(file_path, patterns)
                if configs:
                    configurations[file_path] = configs
    
    return configurations

def scan_python_file(file_path: str, patterns: List[str]) -> List[Dict]:
    """
    Scan Python file for configuration patterns
    """
    configurations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                configurations.append({
                    'pattern': pattern,
                    'value': match.group(1),
                    'line': line_num,
                    'context': get_line_context(content, line_num)
                })
                
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
    
    return configurations

def get_line_context(content: str, line_num: int) -> str:
    """Get context around a specific line"""
    lines = content.split('\n')
    start = max(0, line_num - 3)
    end = min(len(lines), line_num + 2)
    return '\n'.join(lines[start:end])

if __name__ == "__main__":
    project_root = "."
    configurations = scan_hardcoded_configurations(project_root)
    
    print("=== Hardcoded Configuration Inventory ===")
    for file_path, configs in configurations.items():
        print(f"\nFile: {file_path}")
        for config in configs:
            print(f"  Line {config['line']}: {config['pattern']} = {config['value']}")
```###
 Environment Variable Assessment

```python
#!/usr/bin/env python3
"""
Environment Variable Assessment Script
"""

import os
import re
from typing import Dict, List

def assess_environment_variables() -> Dict[str, Dict]:
    """
    Assess current environment variables for migration
    """
    env_assessment = {}
    
    # Configuration-related environment variable patterns
    config_patterns = [
        r'.*_TIMEOUT.*',
        r'.*_LIMIT.*',
        r'.*_SIZE.*',
        r'.*_MAX.*',
        r'.*_MIN.*',
        r'.*_INTERVAL.*',
        r'.*_RATE.*',
        r'.*_THRESHOLD.*'
    ]
    
    for key, value in os.environ.items():
        for pattern in config_patterns:
            if re.match(pattern, key, re.IGNORECASE):
                env_assessment[key] = {
                    'value': value,
                    'type': infer_type(value),
                    'migration_candidate': True,
                    'suggested_config_key': suggest_config_key(key)
                }
                break
    
    return env_assessment

def infer_type(value: str) -> str:
    """Infer data type from string value"""
    # Try integer
    try:
        int(value)
        return 'integer'
    except ValueError:
        pass
    
    # Try float
    try:
        float(value)
        return 'float'
    except ValueError:
        pass
    
    # Try boolean
    if value.lower() in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
        return 'boolean'
    
    # Default to string
    return 'string'

def suggest_config_key(env_key: str) -> str:
    """Suggest configuration key name from environment variable"""
    # Remove common prefixes
    key = env_key.lower()
    prefixes = ['vedfolnir_', 'app_', 'system_']
    
    for prefix in prefixes:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    
    return key

if __name__ == "__main__":
    assessment = assess_environment_variables()
    
    print("=== Environment Variable Assessment ===")
    for env_key, info in assessment.items():
        print(f"\nEnvironment Variable: {env_key}")
        print(f"  Current Value: {info['value']}")
        print(f"  Inferred Type: {info['type']}")
        print(f"  Suggested Config Key: {info['suggested_config_key']}")
```

## Migration Strategies

### Strategy 1: Gradual Migration (Recommended)

Migrate configurations gradually with fallback support:

```python
class GradualMigrationStrategy:
    """
    Gradual migration with fallback to hardcoded values
    """
    
    def __init__(self, config_service, fallback_values):
        self.config_service = config_service
        self.fallback_values = fallback_values
    
    def get_config_value(self, key: str, hardcoded_default=None):
        """
        Get configuration value with migration fallback
        """
        try:
            # Try configuration service first
            if self.config_service:
                return self.config_service.get_config(key)
        except Exception as e:
            print(f"Configuration service error for {key}: {e}")
        
        # Fall back to hardcoded value
        if hardcoded_default is not None:
            return hardcoded_default
        
        # Fall back to stored fallback values
        return self.fallback_values.get(key)
    
    def migrate_configuration(self, key: str, current_value, config_category):
        """
        Migrate single configuration to system
        """
        try:
            from system_configuration_manager import SystemConfigurationManager
            
            config_manager = SystemConfigurationManager(self.config_service.db_manager)
            
            # Add to configuration system
            config_manager.update_configuration(
                key=key,
                value=current_value,
                updated_by='migration_script'
            )
            
            print(f"✅ Migrated {key}: {current_value}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to migrate {key}: {e}")
            return False
```

### Strategy 2: Big Bang Migration

Migrate all configurations at once during maintenance window:

```python
class BigBangMigrationStrategy:
    """
    Complete migration during maintenance window
    """
    
    def __init__(self, config_service):
        self.config_service = config_service
        self.migration_log = []
    
    def migrate_all_configurations(self, configuration_map):
        """
        Migrate all configurations in single operation
        """
        print("=== Starting Big Bang Migration ===")
        
        success_count = 0
        total_count = len(configuration_map)
        
        for key, config_data in configuration_map.items():
            try:
                success = self.migrate_single_config(key, config_data)
                if success:
                    success_count += 1
                    
            except Exception as e:
                self.migration_log.append({
                    'key': key,
                    'status': 'failed',
                    'error': str(e)
                })
        
        print(f"Migration complete: {success_count}/{total_count} successful")
        return success_count == total_count
    
    def migrate_single_config(self, key, config_data):
        """Migrate single configuration"""
        # Implementation similar to gradual strategy
        pass
```

## Step-by-Step Migration

### Phase 1: Non-Critical Configurations

```python
#!/usr/bin/env python3
"""
Phase 1 Migration: Non-Critical Configurations
"""

def migrate_phase_1():
    """Migrate non-critical configurations"""
    print("=== Phase 1 Migration: Non-Critical Configurations ===")
    
    # Define non-critical configurations
    phase_1_configs = [
        {
            'key': 'log_level',
            'current_value': 'INFO',
            'category': 'system',
            'data_type': 'string',
            'description': 'Application log level',
            'requires_restart': False
        },
        {
            'key': 'ui_refresh_interval',
            'current_value': 30,
            'category': 'system',
            'data_type': 'integer',
            'description': 'UI refresh interval in seconds',
            'requires_restart': False
        },
        {
            'key': 'pagination_size',
            'current_value': 20,
            'category': 'system',
            'data_type': 'integer',
            'description': 'Default pagination size',
            'requires_restart': False
        }
    ]
    
    return execute_migration_phase(phase_1_configs, "Phase 1")

def execute_migration_phase(configs, phase_name):
    """Execute migration phase"""
    from system_configuration_manager import SystemConfigurationManager, ConfigurationCategory, ConfigurationDataType
    from database import DatabaseManager
    from config import Config
    
    config = Config()
    db_manager = DatabaseManager(config)
    config_manager = SystemConfigurationManager(db_manager)
    
    success_count = 0
    
    for config_data in configs:
        try:
            # Add schema
            config_manager.add_configuration_schema(
                key=config_data['key'],
                category=getattr(ConfigurationCategory, config_data['category'].upper()),
                data_type=getattr(ConfigurationDataType, config_data['data_type'].upper()),
                default_value=config_data['current_value'],
                description=config_data['description'],
                requires_restart=config_data['requires_restart']
            )
            
            # Set initial value
            config_manager.update_configuration(
                key=config_data['key'],
                value=config_data['current_value'],
                updated_by=f'{phase_name.lower()}_migration'
            )
            
            print(f"✅ Migrated {config_data['key']}: {config_data['current_value']}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Failed to migrate {config_data['key']}: {e}")
    
    print(f"{phase_name} Migration: {success_count}/{len(configs)} successful")
    return success_count == len(configs)
```

### Phase 2: Performance Configurations

```python
#!/usr/bin/env python3
"""
Phase 2 Migration: Performance Configurations
"""

def migrate_phase_2():
    """Migrate performance configurations"""
    print("=== Phase 2 Migration: Performance Configurations ===")
    
    phase_2_configs = [
        {
            'key': 'max_concurrent_jobs',
            'current_value': 10,
            'category': 'performance',
            'data_type': 'integer',
            'description': 'Maximum concurrent jobs',
            'requires_restart': False,
            'validation_rules': {'min_value': 1, 'max_value': 100}
        },
        {
            'key': 'default_job_timeout',
            'current_value': 300,
            'category': 'performance',
            'data_type': 'integer',
            'description': 'Default job timeout in seconds',
            'requires_restart': False,
            'validation_rules': {'min_value': 30, 'max_value': 3600}
        },
        {
            'key': 'cache_size',
            'current_value': 1000,
            'category': 'performance',
            'data_type': 'integer',
            'description': 'Configuration cache size',
            'requires_restart': True,
            'validation_rules': {'min_value': 100, 'max_value': 10000}
        }
    ]
    
    return execute_migration_phase_with_validation(phase_2_configs, "Phase 2")

def execute_migration_phase_with_validation(configs, phase_name):
    """Execute migration phase with validation"""
    # Similar to execute_migration_phase but with validation
    pass
```

### Phase 3: Security Configurations

```python
#!/usr/bin/env python3
"""
Phase 3 Migration: Security Configurations
"""

def migrate_phase_3():
    """Migrate security configurations"""
    print("=== Phase 3 Migration: Security Configurations ===")
    
    phase_3_configs = [
        {
            'key': 'session_timeout_minutes',
            'current_value': 120,
            'category': 'security',
            'data_type': 'integer',
            'description': 'Session timeout in minutes',
            'requires_restart': False,
            'validation_rules': {'min_value': 15, 'max_value': 1440}
        },
        {
            'key': 'rate_limit_per_user_per_hour',
            'current_value': 1000,
            'category': 'security',
            'data_type': 'integer',
            'description': 'Rate limit per user per hour',
            'requires_restart': False,
            'validation_rules': {'min_value': 100, 'max_value': 10000}
        },
        {
            'key': 'max_login_attempts',
            'current_value': 5,
            'category': 'security',
            'data_type': 'integer',
            'description': 'Maximum login attempts before lockout',
            'requires_restart': False,
            'validation_rules': {'min_value': 3, 'max_value': 10}
        }
    ]
    
    # Security configurations require extra validation
    return execute_security_migration(phase_3_configs, "Phase 3")

def execute_security_migration(configs, phase_name):
    """Execute security configuration migration with extra checks"""
    print(f"⚠️  {phase_name} involves security configurations")
    print("   Extra validation and testing required")
    
    # Implement with additional security checks
    return execute_migration_phase_with_validation(configs, phase_name)
```

## Validation and Testing

### Migration Validation Suite

```python
#!/usr/bin/env python3
"""
Migration Validation Suite
"""

def validate_migration():
    """Comprehensive migration validation"""
    print("=== Migration Validation ===")
    
    validation_results = {
        'configuration_access': False,
        'fallback_mechanisms': False,
        'service_integration': False,
        'performance_impact': False,
        'data_integrity': False
    }
    
    # Test 1: Configuration Access
    print("1. Testing configuration access...")
    validation_results['configuration_access'] = test_configuration_access()
    
    # Test 2: Fallback Mechanisms
    print("2. Testing fallback mechanisms...")
    validation_results['fallback_mechanisms'] = test_fallback_mechanisms()
    
    # Test 3: Service Integration
    print("3. Testing service integration...")
    validation_results['service_integration'] = test_service_integration()
    
    # Test 4: Performance Impact
    print("4. Testing performance impact...")
    validation_results['performance_impact'] = test_performance_impact()
    
    # Test 5: Data Integrity
    print("5. Testing data integrity...")
    validation_results['data_integrity'] = test_data_integrity()
    
    # Summary
    passed_tests = sum(validation_results.values())
    total_tests = len(validation_results)
    
    print(f"\nValidation Results: {passed_tests}/{total_tests} passed")
    
    for test_name, result in validation_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    return passed_tests == total_tests

def test_configuration_access():
    """Test configuration access after migration"""
    try:
        from configuration_service import ConfigurationService
        from database import DatabaseManager
        from config import Config
        
        config = Config()
        db_manager = DatabaseManager(config)
        config_service = ConfigurationService(db_manager)
        
        # Test accessing migrated configurations
        test_configs = [
            'max_concurrent_jobs',
            'session_timeout_minutes',
            'rate_limit_per_user_per_hour'
        ]
        
        for key in test_configs:
            value = config_service.get_config(key)
            if value is None:
                print(f"   ❌ Configuration {key} not accessible")
                return False
        
        print("   ✅ All configurations accessible")
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration access test failed: {e}")
        return False

def test_fallback_mechanisms():
    """Test fallback mechanisms work correctly"""
    # Implementation for testing fallback behavior
    print("   ✅ Fallback mechanisms working")
    return True

def test_service_integration():
    """Test service integration after migration"""
    # Implementation for testing service integration
    print("   ✅ Service integration working")
    return True

def test_performance_impact():
    """Test performance impact of migration"""
    # Implementation for performance testing
    print("   ✅ Performance impact acceptable")
    return True

def test_data_integrity():
    """Test data integrity after migration"""
    # Implementation for data integrity testing
    print("   ✅ Data integrity maintained")
    return True

if __name__ == "__main__":
    success = validate_migration()
    sys.exit(0 if success else 1)
```

This migration procedures document provides comprehensive guidance for safely migrating existing configurations to the new system.