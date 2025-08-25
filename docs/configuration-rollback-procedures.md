# Configuration System Rollback Procedures

## Overview

This document provides comprehensive rollback procedures for the Configuration Integration System. These procedures ensure safe recovery from deployment issues or system problems.

## Table of Contents

1. [Rollback Triggers](#rollback-triggers)
2. [Rollback Types](#rollback-types)
3. [Emergency Rollback](#emergency-rollback)
4. [Planned Rollback](#planned-rollback)
5. [Partial Rollback](#partial-rollback)
6. [Data Recovery](#data-recovery)
7. [Post-Rollback Validation](#post-rollback-validation)

## Rollback Triggers

### Automatic Rollback Triggers

The system should automatically trigger rollback when:

- Configuration service unavailable for > 5 minutes
- Database connection failures > 10 consecutive attempts
- Memory usage > 90% for > 10 minutes
- Error rate > 50% for > 5 minutes
- Critical service failures

### Manual Rollback Triggers

Manual rollback should be considered when:

- Performance degradation > 50%
- User-reported functionality issues
- Security vulnerabilities discovered
- Data corruption detected
- Compliance violations

## Rollback Types

### Type 1: Configuration-Only Rollback

Rollback configuration values while keeping system components:

```bash
#!/bin/bash
# Configuration-Only Rollback Script

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "=== Configuration-Only Rollback ==="

python3 -c "
import json
import sys
from system_configuration_manager import SystemConfigurationManager
from database import DatabaseManager
from config import Config

# Load backup
try:
    with open('$BACKUP_FILE', 'r') as f:
        backup_data = json.load(f)
except Exception as e:
    print(f'Error loading backup: {e}')
    sys.exit(1)

# Initialize managers
config = Config()
db_manager = DatabaseManager(config)
config_manager = SystemConfigurationManager(db_manager)

# Restore configurations
restored_count = 0
for key, config_data in backup_data.get('configurations', {}).items():
    try:
        config_manager.update_configuration(
            key=key,
            value=config_data['value'],
            updated_by='rollback_script'
        )
        print(f'Restored {key}: {config_data[\"value\"]}')
        restored_count += 1
    except Exception as e:
        print(f'Failed to restore {key}: {e}')

print(f'Restored {restored_count} configurations')
"

echo "Configuration rollback complete"
```

### Type 2: Service Rollback

Rollback service integrations while keeping configuration system:

```python
#!/usr/bin/env python3
"""
Service Integration Rollback Script
"""

def rollback_service_integrations():
    """Rollback service integrations to pre-configuration state"""
    print("=== Service Integration Rollback ===")
    
    rollback_steps = [
        {
            'name': 'Disable configuration adapters',
            'function': disable_configuration_adapters
        },
        {
            'name': 'Restore hardcoded values',
            'function': restore_hardcoded_values
        },
        {
            'name': 'Update service initialization',
            'function': update_service_initialization
        },
        {
            'name': 'Restart services',
            'function': restart_services
        }
    ]
    
    for step in rollback_steps:
        try:
            print(f"Executing: {step['name']}")
            success = step['function']()
            if success:
                print(f"✅ {step['name']} completed")
            else:
                print(f"❌ {step['name']} failed")
                return False
        except Exception as e:
            print(f"❌ {step['name']} failed: {e}")
            return False
    
    print("=== Service Integration Rollback Complete ===")
    return True

def disable_configuration_adapters():
    """Disable all configuration adapters"""
    try:
        # This would disable adapters in the application
        # Implementation depends on how adapters are managed
        return True
    except Exception as e:
        print(f"Error disabling adapters: {e}")
        return False

def restore_hardcoded_values():
    """Restore hardcoded configuration values"""
    hardcoded_values = {
        'max_concurrent_jobs': 10,
        'default_job_timeout': 300,
        'session_timeout_minutes': 120,
        'rate_limit_per_user_per_hour': 1000
    }
    
    # Create temporary configuration file with hardcoded values
    import json
    with open('hardcoded_config.json', 'w') as f:
        json.dump(hardcoded_values, f, indent=2)
    
    print("Hardcoded values restored to hardcoded_config.json")
    return True

def update_service_initialization():
    """Update service initialization to use hardcoded values"""
    # This would modify service initialization code
    # In practice, this might involve code changes or configuration switches
    return True

def restart_services():
    """Restart services with rollback configuration"""
    import subprocess
    import time
    
    try:
        # Stop current services
        subprocess.run(['pkill', '-f', 'python.*web_app.py'], check=False)
        time.sleep(5)
        
        # Start services with rollback configuration
        subprocess.Popen(['python', 'web_app.py'])
        time.sleep(10)
        
        return True
    except Exception as e:
        print(f"Error restarting services: {e}")
        return False

if __name__ == "__main__":
    success = rollback_service_integrations()
    sys.exit(0 if success else 1)
```

### Type 3: Complete System Rollback

Complete rollback to pre-deployment state:

```bash
#!/bin/bash
# Complete System Rollback Script

BACKUP_DIR="$1"
ROLLBACK_REASON="$2"

if [ -z "$BACKUP_DIR" ] || [ -z "$ROLLBACK_REASON" ]; then
    echo "Usage: $0 <backup_directory> <rollback_reason>"
    exit 1
fi

echo "=== Complete System Rollback ==="
echo "Backup Directory: $BACKUP_DIR"
echo "Reason: $ROLLBACK_REASON"
echo

# Confirm rollback
read -p "This will completely rollback the system. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled"
    exit 0
fi

# Create rollback log
ROLLBACK_LOG="rollback_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$ROLLBACK_LOG")
exec 2>&1

echo "Starting complete system rollback at $(date)"

# Step 1: Stop all services
echo "1. Stopping services..."
pkill -f "python.*web_app.py"
pkill -f "monitor_configuration_system.py"
sleep 10

# Step 2: Backup current state (for potential re-rollback)
echo "2. Backing up current state..."
CURRENT_BACKUP="current_state_$(date +%Y%m%d_%H%M%S)"
mkdir -p "backups/$CURRENT_BACKUP"
mysqldump -u $DB_USER -p$DB_PASSWORD $DB_NAME > "backups/$CURRENT_BACKUP/database.sql"
cp -r config/ "backups/$CURRENT_BACKUP/config/"
cp .env "backups/$CURRENT_BACKUP/env"

# Step 3: Restore database
echo "3. Restoring database..."
if [ -f "$BACKUP_DIR/database_backup.sql" ]; then
    mysql -u $DB_USER -p$DB_PASSWORD $DB_NAME < "$BACKUP_DIR/database_backup.sql"
    echo "   ✅ Database restored"
else
    echo "   ❌ Database backup not found"
    exit 1
fi

# Step 4: Restore configuration files
echo "4. Restoring configuration files..."
if [ -d "$BACKUP_DIR/config_backup" ]; then
    rm -rf config/
    cp -r "$BACKUP_DIR/config_backup" config/
    echo "   ✅ Configuration files restored"
else
    echo "   ❌ Configuration backup not found"
fi

# Step 5: Restore environment file
echo "5. Restoring environment file..."
if [ -f "$BACKUP_DIR/env_backup" ]; then
    cp "$BACKUP_DIR/env_backup" .env
    echo "   ✅ Environment file restored"
else
    echo "   ❌ Environment backup not found"
fi

# Step 6: Remove configuration integration files
echo "6. Removing configuration integration files..."
rm -f configuration_service.py
rm -f configuration_cache.py
rm -f configuration_event_bus.py
rm -f *_configuration_adapter.py
rm -f feature_flag_service.py
rm -f maintenance_mode_service.py
rm -f monitor_configuration_system.py
echo "   ✅ Configuration integration files removed"

# Step 7: Restore application code
echo "7. Restoring application code..."
if [ -d "$BACKUP_DIR/application_backup" ]; then
    # Restore specific application files that were modified
    cp "$BACKUP_DIR/application_backup/"*.py .
    echo "   ✅ Application code restored"
fi

# Step 8: Restart services
echo "8. Restarting services..."
python web_app.py & sleep 10
echo "   ✅ Services restarted"

# Step 9: Validate rollback
echo "9. Validating rollback..."
python -c "
import requests
import time

# Wait for service to start
time.sleep(10)

try:
    response = requests.get('http://localhost:5000/health', timeout=10)
    if response.status_code == 200:
        print('   ✅ Service health check passed')
    else:
        print(f'   ❌ Service health check failed: {response.status_code}')
except Exception as e:
    print(f'   ❌ Service health check failed: {e}')
"

echo "Complete system rollback finished at $(date)"
echo "Rollback log saved to: $ROLLBACK_LOG"
```

## Emergency Rollback

### Automated Emergency Rollback

```python
#!/usr/bin/env python3
"""
Automated Emergency Rollback System
"""

import time
import logging
import subprocess
import json
from datetime import datetime, timedelta
from typing import Dict, List

class EmergencyRollbackMonitor:
    """
    Monitor system health and trigger emergency rollback if needed
    """
    
    def __init__(self, config_file: str = 'emergency_rollback_config.json'):
        self.config = self.load_config(config_file)
        self.health_history = []
        self.rollback_triggered = False
        
    def load_config(self, config_file: str) -> Dict:
        """Load emergency rollback configuration"""
        default_config = {
            'monitoring_interval': 30,  # seconds
            'health_check_timeout': 10,  # seconds
            'failure_threshold': 5,  # consecutive failures
            'memory_threshold': 0.9,  # 90%
            'error_rate_threshold': 0.5,  # 50%
            'rollback_script': './emergency_rollback.sh',
            'backup_directory': 'backups/latest'
        }
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                default_config.update(config)
                return default_config
        except FileNotFoundError:
            return default_config
    
    def start_monitoring(self):
        """Start emergency rollback monitoring"""
        logging.info("Starting emergency rollback monitoring")
        
        while not self.rollback_triggered:
            try:
                health_status = self.check_system_health()
                self.health_history.append({
                    'timestamp': datetime.utcnow(),
                    'status': health_status
                })
                
                # Keep only recent history
                cutoff_time = datetime.utcnow() - timedelta(minutes=10)
                self.health_history = [
                    h for h in self.health_history 
                    if h['timestamp'] > cutoff_time
                ]
                
                # Check if emergency rollback is needed
                if self.should_trigger_emergency_rollback():
                    self.trigger_emergency_rollback()
                    break
                
                time.sleep(self.config['monitoring_interval'])
                
            except Exception as e:
                logging.error(f"Error in emergency monitoring: {e}")
                time.sleep(self.config['monitoring_interval'])
    
    def check_system_health(self) -> Dict:
        """Check overall system health"""
        health_status = {
            'timestamp': datetime.utcnow(),
            'service_available': False,
            'database_available': False,
            'memory_usage': 0.0,
            'error_rate': 0.0,
            'response_time': 0.0
        }
        
        # Check service availability
        try:
            import requests
            start_time = time.time()
            response = requests.get(
                'http://localhost:5000/health',
                timeout=self.config['health_check_timeout']
            )
            health_status['response_time'] = time.time() - start_time
            health_status['service_available'] = response.status_code == 200
        except Exception as e:
            logging.error(f"Service health check failed: {e}")
        
        # Check database availability
        try:
            from database import DatabaseManager
            from config import Config
            
            config = Config()
            db_manager = DatabaseManager(config)
            with db_manager.get_session() as session:
                session.execute("SELECT 1")
            health_status['database_available'] = True
        except Exception as e:
            logging.error(f"Database health check failed: {e}")
        
        # Check memory usage
        try:
            import psutil
            memory = psutil.virtual_memory()
            health_status['memory_usage'] = memory.percent / 100.0
        except Exception as e:
            logging.error(f"Memory check failed: {e}")
        
        return health_status
    
    def should_trigger_emergency_rollback(self) -> bool:
        """Determine if emergency rollback should be triggered"""
        if len(self.health_history) < self.config['failure_threshold']:
            return False
        
        recent_checks = self.health_history[-self.config['failure_threshold']:]
        
        # Check for consecutive service failures
        service_failures = sum(
            1 for check in recent_checks 
            if not check['status']['service_available']
        )
        
        if service_failures >= self.config['failure_threshold']:
            logging.critical("Emergency rollback triggered: consecutive service failures")
            return True
        
        # Check for high memory usage
        high_memory_count = sum(
            1 for check in recent_checks 
            if check['status']['memory_usage'] > self.config['memory_threshold']
        )
        
        if high_memory_count >= self.config['failure_threshold']:
            logging.critical("Emergency rollback triggered: high memory usage")
            return True
        
        # Check for high error rate
        high_error_count = sum(
            1 for check in recent_checks 
            if check['status']['error_rate'] > self.config['error_rate_threshold']
        )
        
        if high_error_count >= self.config['failure_threshold']:
            logging.critical("Emergency rollback triggered: high error rate")
            return True
        
        return False
    
    def trigger_emergency_rollback(self):
        """Trigger emergency rollback"""
        self.rollback_triggered = True
        
        logging.critical("EMERGENCY ROLLBACK TRIGGERED")
        
        try:
            # Execute rollback script
            result = subprocess.run([
                self.config['rollback_script'],
                self.config['backup_directory'],
                'emergency_automatic_rollback'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logging.info("Emergency rollback completed successfully")
            else:
                logging.error(f"Emergency rollback failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logging.error("Emergency rollback timed out")
        except Exception as e:
            logging.error(f"Emergency rollback error: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('emergency_rollback.log'),
            logging.StreamHandler()
        ]
    )
    
    monitor = EmergencyRollbackMonitor()
    monitor.start_monitoring()
```

This rollback procedures document provides comprehensive guidance for safely rolling back the configuration system in various scenarios.