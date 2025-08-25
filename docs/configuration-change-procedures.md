# Configuration Change Procedures and Best Practices

## Overview

This document outlines the procedures and best practices for making configuration changes in the Configuration Integration System. Following these procedures ensures safe, reliable configuration management with minimal risk of system disruption.

## Table of Contents

1. [Change Management Process](#change-management-process)
2. [Configuration Change Types](#configuration-change-types)
3. [Pre-Change Procedures](#pre-change-procedures)
4. [Change Execution](#change-execution)
5. [Post-Change Validation](#post-change-validation)
6. [Rollback Procedures](#rollback-procedures)
7. [Best Practices](#best-practices)
8. [Emergency Procedures](#emergency-procedures)

## Change Management Process

### Change Classification

All configuration changes are classified into categories based on their impact and risk level:

#### Low Risk Changes
- **Definition**: Changes that don't affect system stability or performance
- **Examples**: Log levels, non-critical timeouts, display settings
- **Approval**: Self-service through admin interface
- **Testing**: Basic validation only

#### Medium Risk Changes
- **Definition**: Changes that may affect performance or user experience
- **Examples**: Session timeouts, rate limits, cache sizes
- **Approval**: Admin approval required
- **Testing**: Staging environment testing recommended

#### High Risk Changes
- **Definition**: Changes that could cause system instability or outages
- **Examples**: Database connection limits, core service settings
- **Approval**: Senior admin approval required
- **Testing**: Mandatory staging environment testing

#### Critical Changes
- **Definition**: Changes requiring application restart or affecting security
- **Examples**: Encryption keys, core system parameters
- **Approval**: Change management board approval
- **Testing**: Full testing cycle including rollback testing

### Change Request Process

1. **Identify Change Requirements**
   - Document the business need for the change
   - Identify affected systems and services
   - Assess potential impact and risks

2. **Plan the Change**
   - Determine change classification
   - Plan testing approach
   - Identify rollback strategy
   - Schedule change window if needed

3. **Get Approval**
   - Submit change request with documentation
   - Get appropriate approval based on classification
   - Ensure all stakeholders are informed

4. **Execute Change**
   - Follow documented procedures
   - Monitor system during change
   - Validate change effectiveness

5. **Post-Change Review**
   - Verify change objectives were met
   - Document any issues encountered
   - Update procedures if needed

## Configuration Change Types

### Runtime Changes (Hot Reload)

Changes that take effect immediately without restart:

**Supported Configuration Types**:
- Session timeouts
- Rate limiting settings
- Alert thresholds
- Feature flags
- Maintenance mode settings
- Performance tuning parameters

**Procedure**:
1. Update configuration through admin interface
2. System automatically propagates changes
3. Verify change took effect within 60 seconds
4. Monitor system for any adverse effects

**Example**:
```python
# Update session timeout
config_manager.update_configuration(
    key="session_timeout_minutes",
    value=180,  # 3 hours
    updated_by="admin_user"
)

# Change propagates automatically to all session managers
# No restart required
```

### Restart-Required Changes

Changes that require application restart to take effect:

**Configuration Types**:
- Database connection settings
- Core system parameters
- Security encryption keys
- Service binding addresses

**Procedure**:
1. Update configuration during maintenance window
2. System marks configuration as "restart required"
3. Schedule and execute application restart
4. Verify configuration took effect after restart

**Example**:
```python
# Update database pool size (requires restart)
config_manager.update_configuration(
    key="db_pool_size",
    value=50,
    updated_by="admin_user"
)

# System shows restart required indicator
# Schedule maintenance window for restart
```

### Batch Changes

Multiple related configuration changes applied together:

**Use Cases**:
- Performance tuning across multiple services
- Security policy updates
- Feature rollout configurations

**Procedure**:
1. Group related configuration changes
2. Apply all changes in single transaction
3. Validate consistency across all changes
4. Monitor system behavior after batch update

## Pre-Change Procedures

### 1. Configuration Backup

Always backup current configuration before making changes:

```python
def backup_configuration(config_manager, backup_name):
    """Create configuration backup"""
    backup_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'configurations': {}
    }
    
    # Get all current configurations
    with config_manager.db_manager.get_session() as session:
        configs = session.query(SystemConfiguration).all()
        for config in configs:
            backup_data['configurations'][config.key] = {
                'value': config.value,
                'data_type': config.data_type,
                'updated_at': config.updated_at.isoformat(),
                'updated_by': config.updated_by
            }
    
    # Save backup
    backup_file = f"config_backup_{backup_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(f"backups/{backup_file}", 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    return backup_file
```

### 2. Impact Assessment

Assess the potential impact of configuration changes:

```python
def assess_configuration_impact(config_service, key, new_value):
    """Assess impact of configuration change"""
    impact_assessment = {
        'restart_required': False,
        'affected_services': [],
        'risk_level': 'low',
        'validation_results': []
    }
    
    # Check if restart is required
    schema = config_service.system_config_manager.get_configuration_schema(key)
    if schema and schema.requires_restart:
        impact_assessment['restart_required'] = True
        impact_assessment['risk_level'] = 'high'
    
    # Identify affected services
    affected_services = _get_affected_services(key)
    impact_assessment['affected_services'] = affected_services
    
    # Validate new value
    validation_result = _validate_configuration_value(key, new_value)
    impact_assessment['validation_results'] = validation_result
    
    return impact_assessment
```

### 3. Staging Environment Testing

Test configuration changes in staging environment:

```python
def test_configuration_in_staging(staging_config_service, key, value):
    """Test configuration change in staging environment"""
    test_results = {
        'success': False,
        'errors': [],
        'performance_impact': {},
        'service_health': {}
    }
    
    try:
        # Apply configuration change
        staging_config_service.notify_change(key, None, value)
        
        # Wait for propagation
        time.sleep(30)
        
        # Check service health
        health_results = _check_service_health(staging_config_service)
        test_results['service_health'] = health_results
        
        # Measure performance impact
        performance_results = _measure_performance_impact(key, value)
        test_results['performance_impact'] = performance_results
        
        test_results['success'] = True
        
    except Exception as e:
        test_results['errors'].append(str(e))
    
    return test_results
```

## Change Execution

### 1. Standard Change Execution

For routine configuration changes:

```python
def execute_standard_configuration_change(config_manager, change_request):
    """Execute standard configuration change"""
    change_log = {
        'change_id': change_request['id'],
        'timestamp': datetime.utcnow(),
        'status': 'in_progress',
        'steps': []
    }
    
    try:
        # Step 1: Validate change request
        validation_result = _validate_change_request(change_request)
        change_log['steps'].append({
            'step': 'validation',
            'status': 'completed',
            'result': validation_result
        })
        
        # Step 2: Create backup
        backup_file = backup_configuration(config_manager, change_request['id'])
        change_log['steps'].append({
            'step': 'backup',
            'status': 'completed',
            'backup_file': backup_file
        })
        
        # Step 3: Apply configuration change
        config_manager.update_configuration(
            key=change_request['key'],
            value=change_request['value'],
            updated_by=change_request['requested_by']
        )
        change_log['steps'].append({
            'step': 'apply_change',
            'status': 'completed'
        })
        
        # Step 4: Verify change propagation
        verification_result = _verify_change_propagation(
            config_manager.config_service,
            change_request['key'],
            change_request['value']
        )
        change_log['steps'].append({
            'step': 'verification',
            'status': 'completed',
            'result': verification_result
        })
        
        change_log['status'] = 'completed'
        
    except Exception as e:
        change_log['status'] = 'failed'
        change_log['error'] = str(e)
        
        # Attempt rollback
        try:
            _rollback_configuration_change(config_manager, backup_file)
            change_log['rollback_status'] = 'completed'
        except Exception as rollback_error:
            change_log['rollback_status'] = 'failed'
            change_log['rollback_error'] = str(rollback_error)
    
    return change_log
```

### 2. Emergency Change Execution

For urgent configuration changes:

```python
def execute_emergency_configuration_change(config_manager, emergency_change):
    """Execute emergency configuration change with minimal validation"""
    emergency_log = {
        'change_id': emergency_change['id'],
        'timestamp': datetime.utcnow(),
        'emergency': True,
        'status': 'in_progress'
    }
    
    try:
        # Quick backup
        backup_file = backup_configuration(config_manager, f"emergency_{emergency_change['id']}")
        
        # Apply change immediately
        config_manager.update_configuration(
            key=emergency_change['key'],
            value=emergency_change['value'],
            updated_by=emergency_change['requested_by']
        )
        
        # Quick verification
        time.sleep(5)  # Brief wait for propagation
        current_value = config_manager.config_service.get_config(emergency_change['key'])
        
        if current_value == emergency_change['value']:
            emergency_log['status'] = 'completed'
        else:
            emergency_log['status'] = 'verification_failed'
        
        emergency_log['backup_file'] = backup_file
        
    except Exception as e:
        emergency_log['status'] = 'failed'
        emergency_log['error'] = str(e)
    
    return emergency_log
```

## Post-Change Validation

### 1. Configuration Propagation Verification

Verify that configuration changes have propagated to all services:

```python
def verify_configuration_propagation(config_service, key, expected_value, timeout=60):
    """Verify configuration change has propagated to all services"""
    start_time = time.time()
    verification_results = {
        'success': False,
        'propagation_time': 0,
        'service_status': {}
    }
    
    while time.time() - start_time < timeout:
        # Check configuration service
        current_value = config_service.get_config(key)
        if current_value == expected_value:
            verification_results['success'] = True
            verification_results['propagation_time'] = time.time() - start_time
            break
        
        time.sleep(1)
    
    # Check individual service adapters
    service_adapters = _get_service_adapters_for_key(key)
    for service_name, adapter in service_adapters.items():
        try:
            service_value = _get_service_configuration_value(adapter, key)
            verification_results['service_status'][service_name] = {
                'value': service_value,
                'matches_expected': service_value == expected_value
            }
        except Exception as e:
            verification_results['service_status'][service_name] = {
                'error': str(e),
                'matches_expected': False
            }
    
    return verification_results
```

### 2. System Health Monitoring

Monitor system health after configuration changes:

```python
def monitor_system_health_after_change(config_service, monitoring_duration=300):
    """Monitor system health after configuration change"""
    monitoring_results = {
        'start_time': datetime.utcnow(),
        'duration': monitoring_duration,
        'health_checks': [],
        'performance_metrics': [],
        'alerts_triggered': []
    }
    
    start_time = time.time()
    
    while time.time() - start_time < monitoring_duration:
        # Perform health checks
        health_check = _perform_system_health_check(config_service)
        monitoring_results['health_checks'].append({
            'timestamp': datetime.utcnow(),
            'status': health_check
        })
        
        # Collect performance metrics
        performance_metrics = _collect_performance_metrics(config_service)
        monitoring_results['performance_metrics'].append({
            'timestamp': datetime.utcnow(),
            'metrics': performance_metrics
        })
        
        # Check for alerts
        alerts = _check_for_alerts()
        if alerts:
            monitoring_results['alerts_triggered'].extend(alerts)
        
        time.sleep(30)  # Check every 30 seconds
    
    return monitoring_results
```

## Rollback Procedures

### 1. Automatic Rollback

For critical failures, implement automatic rollback:

```python
def setup_automatic_rollback(config_service, key, original_value, rollback_conditions):
    """Set up automatic rollback based on conditions"""
    rollback_monitor = {
        'key': key,
        'original_value': original_value,
        'conditions': rollback_conditions,
        'monitoring': True
    }
    
    def monitor_and_rollback():
        while rollback_monitor['monitoring']:
            try:
                # Check rollback conditions
                should_rollback = _evaluate_rollback_conditions(rollback_conditions)
                
                if should_rollback:
                    logger.warning(f"Automatic rollback triggered for {key}")
                    
                    # Execute rollback
                    config_service.notify_change(key, None, original_value)
                    
                    # Log rollback
                    logger.info(f"Automatic rollback completed for {key}")
                    rollback_monitor['monitoring'] = False
                    break
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in automatic rollback monitor: {e}")
                time.sleep(30)
    
    # Start monitoring in background thread
    import threading
    monitor_thread = threading.Thread(target=monitor_and_rollback)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    return rollback_monitor
```

### 2. Manual Rollback

For manual rollback procedures:

```python
def execute_manual_rollback(config_manager, backup_file):
    """Execute manual rollback from backup"""
    rollback_log = {
        'timestamp': datetime.utcnow(),
        'backup_file': backup_file,
        'status': 'in_progress',
        'restored_configurations': []
    }
    
    try:
        # Load backup
        with open(f"backups/{backup_file}", 'r') as f:
            backup_data = json.load(f)
        
        # Restore configurations
        for key, config_data in backup_data['configurations'].items():
            try:
                config_manager.update_configuration(
                    key=key,
                    value=config_data['value'],
                    updated_by="system_rollback"
                )
                rollback_log['restored_configurations'].append({
                    'key': key,
                    'status': 'restored'
                })
            except Exception as e:
                rollback_log['restored_configurations'].append({
                    'key': key,
                    'status': 'failed',
                    'error': str(e)
                })
        
        rollback_log['status'] = 'completed'
        
    except Exception as e:
        rollback_log['status'] = 'failed'
        rollback_log['error'] = str(e)
    
    return rollback_log
```

## Best Practices

### 1. Change Planning

- **Document all changes**: Maintain detailed records of all configuration changes
- **Test in staging**: Always test non-trivial changes in staging environment
- **Plan rollback strategy**: Have a rollback plan before making changes
- **Schedule appropriately**: Make high-risk changes during maintenance windows

### 2. Change Execution

- **Use version control**: Track configuration changes in version control
- **Implement gradual rollout**: For major changes, consider gradual rollout
- **Monitor continuously**: Monitor system health during and after changes
- **Communicate changes**: Inform stakeholders of significant changes

### 3. Validation and Testing

- **Validate inputs**: Always validate configuration values before applying
- **Test edge cases**: Test configuration changes with edge case values
- **Performance testing**: Assess performance impact of configuration changes
- **Security review**: Review security implications of configuration changes

### 4. Documentation

- **Update documentation**: Keep configuration documentation current
- **Document dependencies**: Document configuration dependencies and relationships
- **Maintain change log**: Keep detailed change log for audit purposes
- **Share knowledge**: Ensure multiple team members understand procedures

## Emergency Procedures

### Emergency Change Process

For critical system issues requiring immediate configuration changes:

1. **Assess Urgency**
   - Determine if issue requires immediate action
   - Evaluate risk of not making change vs. risk of making change

2. **Get Emergency Approval**
   - Contact emergency change approver
   - Document business justification
   - Get verbal approval if needed

3. **Execute Emergency Change**
   - Create quick backup
   - Apply configuration change
   - Monitor system immediately

4. **Post-Emergency Actions**
   - Document change thoroughly
   - Schedule proper testing
   - Plan permanent solution if needed

### Emergency Rollback

For immediate rollback of problematic changes:

```bash
# Emergency rollback script
#!/bin/bash

# Usage: emergency_rollback.sh <config_key> <backup_file>

CONFIG_KEY=$1
BACKUP_FILE=$2

echo "EMERGENCY ROLLBACK INITIATED"
echo "Configuration Key: $CONFIG_KEY"
echo "Backup File: $BACKUP_FILE"

# Execute rollback
python -c "
from system_configuration_manager import SystemConfigurationManager
from database import DatabaseManager
from config import Config
import json

config = Config()
db_manager = DatabaseManager(config)
config_manager = SystemConfigurationManager(db_manager)

# Load backup
with open('backups/$BACKUP_FILE', 'r') as f:
    backup_data = json.load(f)

# Restore specific configuration
if '$CONFIG_KEY' in backup_data['configurations']:
    config_data = backup_data['configurations']['$CONFIG_KEY']
    config_manager.update_configuration(
        key='$CONFIG_KEY',
        value=config_data['value'],
        updated_by='emergency_rollback'
    )
    print(f'Rollback completed for $CONFIG_KEY')
else:
    print(f'Configuration $CONFIG_KEY not found in backup')
"

echo "EMERGENCY ROLLBACK COMPLETED"
```

### Emergency Contacts

Maintain emergency contact list for configuration issues:

- **Primary Configuration Admin**: [Contact Info]
- **Secondary Configuration Admin**: [Contact Info]
- **System Administrator**: [Contact Info]
- **Database Administrator**: [Contact Info]
- **On-Call Engineer**: [Contact Info]

This document provides comprehensive procedures for safe configuration management. Always follow these procedures to minimize risk and ensure system stability.