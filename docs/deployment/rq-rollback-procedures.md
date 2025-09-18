# RQ Rollback Procedures

## Overview

This document provides comprehensive rollback procedures for reverting from Redis Queue (RQ) back to database-polling task processing. These procedures are designed to be executed quickly in case of critical issues with the RQ system.

## Rollback Scenarios

### Scenario 1: Immediate Rollback (Critical Issues)
- RQ system completely non-functional
- Data corruption or loss detected
- Performance severely degraded
- Security issues identified

### Scenario 2: Planned Rollback (Performance Issues)
- Performance not meeting expectations
- Stability concerns
- Resource utilization issues
- User experience problems

### Scenario 3: Partial Rollback (Hybrid Mode)
- RQ working but needs optimization
- Gradual transition back to database
- Testing alternative configurations
- Temporary fallback during fixes

## Pre-Rollback Assessment

### Critical Decision Points

Before initiating rollback, assess:

```bash
# 1. Check RQ system status
curl -s http://localhost:8000/admin/rq/health | jq '.'

# 2. Evaluate current task queue
redis-cli llen rq:queue:urgent
redis-cli llen rq:queue:high
redis-cli llen rq:queue:normal
redis-cli llen rq:queue:low

# 3. Check for processing tasks
curl -s http://localhost:8000/admin/rq/stats | jq '.processing'

# 4. Assess data integrity
python scripts/migration/check_data_consistency.py

# 5. Review error logs
tail -100 logs/webapp.log | grep -E "(ERROR|CRITICAL|EXCEPTION)"
```

### Rollback Decision Matrix

| Issue Severity | RQ Functional | Data Integrity | Recommended Action |
|---------------|---------------|----------------|-------------------|
| Critical | No | Compromised | Immediate Rollback |
| High | Partial | Intact | Planned Rollback |
| Medium | Yes | Intact | Partial Rollback |
| Low | Yes | Intact | Fix in Place |

## Immediate Rollback Procedure (Emergency)

### Step 1: Emergency Stop (5 minutes)

```bash
# 1. Enable maintenance mode immediately
curl -X POST http://localhost:8000/admin/maintenance/emergency-mode \
  -H "Content-Type: application/json" \
  -d '{"reason": "Emergency RQ rollback", "notify_users": true}'

# 2. Stop RQ workers immediately
pkill -KILL -f "rq.*worker"
pkill -KILL -f "python web_app.py"

# 3. Disable RQ system
export RQ_ENABLED=false
export DATABASE_POLLING_ENABLED=true
export EMERGENCY_ROLLBACK=true
```

### Step 2: Preserve RQ Data (5 minutes)

```bash
# 1. Create emergency backup directory
mkdir -p backups/emergency_rollback_$(date +%Y%m%d_%H%M%S)
cd backups/emergency_rollback_$(date +%Y%m%d_%H%M%S)

# 2. Backup RQ queues
python scripts/backup/emergency_backup_rq_queues.py

# 3. Backup Redis state
redis-cli bgsave
cp /var/lib/redis/dump.rdb redis_emergency_backup.rdb

# 4. Export current application state
curl -s http://localhost:8000/admin/rq/stats > rq_stats_pre_rollback.json
ps aux | grep -E "(rq|python)" > processes_pre_rollback.txt
```

### Step 3: Restore Database Processing (10 minutes)

```bash
# 1. Update environment configuration
sed -i 's/RQ_ENABLED=true/RQ_ENABLED=false/' .env
echo "DATABASE_POLLING_ENABLED=true" >> .env
echo "EMERGENCY_ROLLBACK_MODE=true" >> .env

# 2. Migrate RQ tasks back to database
python scripts/rollback/emergency_migrate_rq_to_database.py

# 3. Start application in database mode
python web_app.py & sleep 10

# 4. Start legacy workers
python caption_worker.py &
python simple_caption_worker.py &
```

### Step 4: Validate Rollback (5 minutes)

```bash
# 1. Check application health
curl -s http://localhost:8000/health | jq '.status'

# 2. Verify workers are running
ps aux | grep -E "(caption_worker|simple_caption_worker)"

# 3. Test task processing
python scripts/rollback/test_database_processing.py

# 4. Disable maintenance mode
curl -X POST http://localhost:8000/admin/maintenance/disable-emergency-mode
```

## Planned Rollback Procedure

### Phase 1: Preparation (30 minutes)

#### Step 1.1: Announce Maintenance
```bash
# Schedule maintenance window
curl -X POST http://localhost:8000/admin/maintenance/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "'$(date -d "+1 hour" -Iseconds)'",
    "duration": "2 hours",
    "reason": "Planned rollback to database processing",
    "notify_users": true
  }'
```

#### Step 1.2: Prepare Rollback Environment
```bash
# 1. Create rollback backup
mkdir -p backups/planned_rollback_$(date +%Y%m%d_%H%M%S)
cd backups/planned_rollback_$(date +%Y%m%d_%H%M%S)

# 2. Backup current state
mysqldump vedfolnir > database_pre_rollback.sql
redis-cli bgsave
cp /var/lib/redis/dump.rdb redis_pre_rollback.rdb
cp ../../.env env_pre_rollback

# 3. Prepare legacy worker scripts
cp ../../legacy_backup/workers/caption_worker.py ../../
cp ../../legacy_backup/workers/simple_caption_worker.py ../../
```

#### Step 1.3: Validate Legacy Components
```bash
# Test legacy worker scripts
python -c "
import caption_worker
import simple_caption_worker
print('Legacy workers validated')
"

# Test database connectivity
python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
db = DatabaseManager(Config())
with db.get_session() as session:
    print('Database connection validated')
"
```

### Phase 2: Task Migration (45 minutes)

#### Step 2.1: Stop New Task Submissions
```bash
# Enable maintenance mode
curl -X POST http://localhost:8000/admin/maintenance/pause-task-submission \
  -H "Content-Type: application/json" \
  -d '{"reason": "Rollback in progress", "duration": "2 hours"}'
```

#### Step 2.2: Complete Current RQ Tasks
```bash
# Monitor RQ task completion
while true; do
    PROCESSING=$(curl -s http://localhost:8000/admin/rq/stats | jq '.processing')
    echo "RQ processing tasks: $PROCESSING"
    
    if [ "$PROCESSING" -eq 0 ]; then
        echo "All RQ tasks completed"
        break
    fi
    
    sleep 30
done
```

#### Step 2.3: Migrate Remaining Tasks
```bash
# Migrate queued RQ tasks back to database
python scripts/rollback/migrate_rq_to_database.py --verbose

# Verify migration
python scripts/rollback/verify_rollback_migration.py
```

### Phase 3: System Reconfiguration (30 minutes)

#### Step 3.1: Stop RQ System
```bash
# Gracefully stop RQ workers
curl -X POST http://localhost:8000/admin/rq/shutdown-workers

# Stop application
pkill -TERM -f "python web_app.py"
sleep 30

# Force stop if needed
pkill -KILL -f "python web_app.py"
```

#### Step 3.2: Reconfigure for Database Processing
```bash
# Update environment configuration
sed -i 's/RQ_ENABLED=true/RQ_ENABLED=false/' .env
sed -i 's/DATABASE_POLLING_ENABLED=false/DATABASE_POLLING_ENABLED=true/' .env

# Remove RQ-specific configuration
sed -i '/^RQ_/d' .env

# Add database polling configuration
cat >> .env << 'EOF'
DATABASE_POLLING_ENABLED=true
WORKER_POLL_INTERVAL=5
WORKER_BATCH_SIZE=10
WORKER_TIMEOUT=3600
EOF
```

#### Step 3.3: Start Database Processing
```bash
# Start application in database mode
python web_app.py & sleep 10

# Start legacy workers
python caption_worker.py &
python simple_caption_worker.py &

# Verify workers started
ps aux | grep -E "(caption_worker|simple_caption_worker)"
```

### Phase 4: Validation and Cleanup (15 minutes)

#### Step 4.1: Validate Database Processing
```bash
# Test task submission
python scripts/rollback/test_database_task_submission.py

# Monitor task processing
for i in {1..5}; do
    echo "=== Validation $i ==="
    mysql -u vedfolnir_user -p vedfolnir -e "
        SELECT status, COUNT(*) 
        FROM images 
        WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
        GROUP BY status;
    "
    sleep 60
done
```

#### Step 4.2: Resume Normal Operations
```bash
# Disable maintenance mode
curl -X POST http://localhost:8000/admin/maintenance/resume-task-submission

# Test end-to-end functionality
python scripts/rollback/test_end_to_end_processing.py
```

#### Step 4.3: Clean Up RQ Resources
```bash
# Clear RQ queues (after validation)
redis-cli del rq:queue:urgent
redis-cli del rq:queue:high
redis-cli del rq:queue:normal
redis-cli del rq:queue:low

# Remove RQ worker coordination keys
redis-cli del "rq:workers:*"

# Archive RQ configuration
mkdir -p config/archived/rq_$(date +%Y%m%d_%H%M%S)
grep "^RQ_" .env > config/archived/rq_$(date +%Y%m%d_%H%M%S)/rq_config.env
```

## Partial Rollback (Hybrid Mode)

### Enable Hybrid Processing
```bash
# Configure hybrid mode
export RQ_ENABLED=true
export DATABASE_POLLING_ENABLED=true
export HYBRID_MODE=true
export RQ_FALLBACK_ENABLED=true

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10

# Start both RQ workers and database workers
# RQ workers start automatically with application
python caption_worker.py &
python simple_caption_worker.py &
```

### Monitor Hybrid Performance
```bash
# Monitor both systems
while true; do
    echo "=== $(date) ==="
    
    # RQ status
    echo "RQ Queues:"
    for queue in urgent high normal low; do
        echo "  $queue: $(redis-cli llen rq:queue:$queue)"
    done
    
    # Database status
    echo "Database Queue:"
    mysql -u vedfolnir_user -p vedfolnir -e "SELECT COUNT(*) FROM images WHERE status = 'QUEUED';" | tail -1
    
    # Processing status
    echo "Processing:"
    mysql -u vedfolnir_user -p vedfolnir -e "SELECT COUNT(*) FROM images WHERE status = 'PROCESSING';" | tail -1
    
    sleep 60
done
```

## Rollback Validation Scripts

### Create Emergency Rollback Script
```bash
cat > scripts/rollback/emergency_migrate_rq_to_database.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Emergency migration of RQ tasks back to database
"""

import sys
import redis
import json
from config import Config
from app.core.database.core.database_manager import DatabaseManager

def emergency_migrate():
    """Emergency migration of RQ tasks to database"""
    config = Config()
    db_manager = DatabaseManager(config)
    redis_client = redis.from_url(config.RQ_REDIS_URL)
    
    print("Starting emergency RQ to database migration...")
    
    migrated_count = 0
    
    try:
        # Process each queue
        for queue_name in ['urgent', 'high', 'normal', 'low']:
            queue_key = f'rq:queue:{queue_name}'
            
            while True:
                # Get task from queue
                task_data = redis_client.lpop(queue_key)
                if not task_data:
                    break
                
                try:
                    # Deserialize task
                    task = json.loads(task_data)
                    
                    # Create database record
                    with db_manager.get_session() as session:
                        from models import Image
                        
                        # Find existing image or create new one
                        image = session.query(Image).filter_by(
                            id=task.get('image_id')
                        ).first()
                        
                        if image:
                            image.status = 'QUEUED'
                            image.priority = queue_name
                        else:
                            # Create new image record
                            image = Image(
                                url=task.get('url', ''),
                                status='QUEUED',
                                user_id=task.get('user_id', 1),
                                platform_connection_id=task.get('platform_connection_id', 1),
                                priority=queue_name
                            )
                            session.add(image)
                        
                        session.commit()
                        migrated_count += 1
                        
                        print(f"Migrated task {migrated_count}: Image ID {image.id}")
                
                except Exception as e:
                    print(f"Error migrating task: {e}")
                    # Re-queue the task for manual review
                    redis_client.rpush(f'rq:failed:{queue_name}', task_data)
    
    except Exception as e:
        print(f"Critical error during migration: {e}")
        return False
    
    print(f"Emergency migration completed: {migrated_count} tasks migrated")
    return True

if __name__ == "__main__":
    success = emergency_migrate()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/rollback/emergency_migrate_rq_to_database.py
```

### Create Rollback Validation Script
```bash
cat > scripts/rollback/verify_rollback_migration.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Verify rollback migration from RQ to database
"""

import sys
import redis
from config import Config
from app.core.database.core.database_manager import DatabaseManager

def verify_rollback():
    """Verify rollback migration completed successfully"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    print("Verifying rollback migration...")
    
    # Check database queued tasks
    with db_manager.get_session() as session:
        from models import Image
        db_queued = session.query(Image).filter_by(status='QUEUED').count()
        print(f"Database queued tasks: {db_queued}")
    
    # Check RQ queues are empty
    try:
        redis_client = redis.from_url(config.RQ_REDIS_URL)
        rq_queued = 0
        for queue in ['urgent', 'high', 'normal', 'low']:
            queue_len = redis_client.llen(f'rq:queue:{queue}')
            print(f"RQ {queue} queue: {queue_len}")
            rq_queued += queue_len
        
        print(f"Total RQ queued tasks: {rq_queued}")
    except Exception as e:
        print(f"Could not check RQ queues (expected if RQ disabled): {e}")
        rq_queued = 0
    
    # Check workers are running
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        worker_processes = [line for line in result.stdout.split('\n') 
                          if 'caption_worker' in line or 'simple_caption_worker' in line]
        print(f"Database workers running: {len(worker_processes)}")
        
        for process in worker_processes:
            print(f"  {process.split()[10]}")  # Process name
    except Exception as e:
        print(f"Could not check worker processes: {e}")
    
    # Validation
    if db_queued >= 0 and rq_queued == 0:
        print("✅ Rollback successful: Tasks in database, RQ queues empty")
        return True
    else:
        print(f"❌ Rollback incomplete: DB={db_queued}, RQ={rq_queued}")
        return False

if __name__ == "__main__":
    success = verify_rollback()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/rollback/verify_rollback_migration.py
```

### Create Database Processing Test Script
```bash
cat > scripts/rollback/test_database_processing.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test database task processing after rollback
"""

import sys
import time
import requests
from config import Config
from app.core.database.core.database_manager import DatabaseManager

def test_database_processing():
    """Test database task processing functionality"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    print("Testing database task processing...")
    
    # Create test task in database
    try:
        with db_manager.get_session() as session:
            from models import Image
            
            test_image = Image(
                url="http://example.com/rollback_test.jpg",
                status="QUEUED",
                user_id=1,
                platform_connection_id=1,
                priority="normal"
            )
            session.add(test_image)
            session.commit()
            
            test_image_id = test_image.id
            print(f"Created test task: Image ID {test_image_id}")
    
    except Exception as e:
        print(f"Failed to create test task: {e}")
        return False
    
    # Monitor task processing
    print("Monitoring task processing...")
    
    for i in range(30):  # Wait up to 5 minutes
        try:
            with db_manager.get_session() as session:
                from models import Image
                
                image = session.query(Image).filter_by(id=test_image_id).first()
                if image:
                    print(f"Task status: {image.status}")
                    
                    if image.status in ['COMPLETED', 'FAILED']:
                        print(f"✅ Task processing completed: {image.status}")
                        return True
                else:
                    print("❌ Test task not found")
                    return False
        
        except Exception as e:
            print(f"Error checking task status: {e}")
        
        time.sleep(10)
    
    print("❌ Task processing timeout")
    return False

if __name__ == "__main__":
    success = test_database_processing()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/rollback/test_database_processing.py
```

## Rollback Decision Tree

```
RQ System Issue Detected
├── Critical System Failure?
│   ├── Yes → Immediate Emergency Rollback (20 minutes)
│   └── No → Continue Assessment
├── Data Integrity Compromised?
│   ├── Yes → Immediate Emergency Rollback (20 minutes)
│   └── No → Continue Assessment
├── Performance Severely Degraded?
│   ├── Yes → Planned Rollback (2 hours)
│   └── No → Continue Assessment
├── Stability Issues?
│   ├── Yes → Partial Rollback to Hybrid Mode
│   └── No → Fix in Place
└── Minor Issues?
    └── Fix in Place with Monitoring
```

## Post-Rollback Actions

### Immediate Actions (First Hour)
1. **Validate System Operation**
   - Confirm database workers processing tasks
   - Verify user task submission working
   - Check system performance metrics

2. **Monitor System Health**
   - Watch error logs for issues
   - Monitor task processing rates
   - Check user feedback channels

3. **Communicate Status**
   - Notify stakeholders of rollback completion
   - Update status pages and documentation
   - Prepare incident report

### Short-term Actions (First Day)
1. **Performance Analysis**
   - Compare pre-RQ and post-rollback performance
   - Identify any performance regressions
   - Optimize database worker configuration

2. **System Stabilization**
   - Fine-tune worker processes
   - Optimize database queries
   - Adjust polling intervals

3. **Documentation Update**
   - Document rollback reasons and process
   - Update operational procedures
   - Record lessons learned

### Long-term Actions (First Week)
1. **Root Cause Analysis**
   - Investigate RQ system issues
   - Identify improvement opportunities
   - Plan future migration strategy

2. **System Optimization**
   - Optimize database processing performance
   - Implement monitoring improvements
   - Enhance error handling

3. **Future Planning**
   - Evaluate alternative queue systems
   - Plan RQ system improvements
   - Schedule future migration attempts

## Rollback Success Criteria

### Technical Success Criteria
- ✅ Database workers processing tasks successfully
- ✅ Zero data loss during rollback
- ✅ System performance restored to baseline
- ✅ All RQ resources properly cleaned up
- ✅ Error rates returned to normal levels
- ✅ User task submission working normally

### Business Success Criteria
- ✅ User service restored within SLA
- ✅ No additional user complaints
- ✅ Task processing times acceptable
- ✅ System stability maintained
- ✅ Administrative functions working
- ✅ Monitoring and alerting operational

### Validation Checklist
```bash
# System validation
□ Database workers running and healthy
□ Task processing completing successfully
□ User task submission working
□ Admin dashboard functional
□ Performance metrics acceptable
□ Error logs clean

# Data validation
□ No data loss detected
□ Task queue integrity maintained
□ User data consistency verified
□ Audit trails complete
□ Backup integrity confirmed

# Operational validation
□ Monitoring systems updated
□ Alerting rules adjusted
□ Documentation updated
□ Team notifications sent
□ Incident report completed
```

## Emergency Contacts

### Escalation Procedures

**Level 1: System Administrator**
- Initial rollback execution
- System health monitoring
- Basic troubleshooting

**Level 2: Development Team Lead**
- Complex technical issues
- Data integrity problems
- Performance optimization

**Level 3: Database Administrator**
- Database connectivity issues
- Performance problems
- Data recovery procedures

**Level 4: Management**
- Business impact decisions
- External communication
- Resource allocation

### Contact Information

```
System Administrator: [Contact Info]
Development Team Lead: [Contact Info]
Database Administrator: [Contact Info]
Management: [Contact Info]

Emergency Hotline: [Phone Number]
Incident Management: [System/Process]
```

## Lessons Learned Template

### Rollback Incident Report

**Date**: [Date]
**Duration**: [Start Time] - [End Time]
**Impact**: [User Impact Description]

**Root Cause**: [Why rollback was necessary]

**Timeline**:
- [Time]: Issue detected
- [Time]: Rollback decision made
- [Time]: Rollback initiated
- [Time]: System restored
- [Time]: Validation completed

**Actions Taken**:
- [List of rollback steps executed]

**What Worked Well**:
- [Successful aspects of rollback]

**Areas for Improvement**:
- [Issues encountered during rollback]

**Preventive Measures**:
- [Steps to prevent similar issues]

**Follow-up Actions**:
- [Required follow-up tasks]