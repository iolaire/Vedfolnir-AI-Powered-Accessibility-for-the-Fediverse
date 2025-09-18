# RQ Migration Procedures

## Overview

This document provides step-by-step procedures for migrating from the current database-polling task processing system to Redis Queue (RQ). The migration is designed to be safe, reversible, and minimize downtime.

## Migration Strategy

The migration follows a phased approach:
1. **Preparation Phase**: Setup and validation
2. **Hybrid Phase**: Run both systems in parallel
3. **Migration Phase**: Transfer tasks to RQ
4. **Validation Phase**: Verify RQ system operation
5. **Cleanup Phase**: Remove old system components

## Pre-Migration Requirements

### System Prerequisites
- Redis server running and accessible
- MySQL database with current schema
- Application backup completed
- Maintenance window scheduled (recommended 2-4 hours)

### Validation Checklist
```bash
# 1. Verify Redis connectivity
redis-cli ping
# Expected: PONG

# 2. Check Redis memory
redis-cli info memory | grep used_memory_human

# 3. Verify database connectivity
python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
db = DatabaseManager(Config())
with db.get_session() as session:
    print('Database connection: OK')
"

# 4. Check current task queue
mysql -u vedfolnir_user -p vedfolnir -e "SELECT COUNT(*) as queued_tasks FROM images WHERE status = 'QUEUED';"

# 5. Verify application is running
curl -s http://localhost:8000/health | jq '.status'
```

## Phase 1: Preparation

### Step 1.1: Create Backup
```bash
# Create comprehensive backup
mkdir -p backups/rq_migration_$(date +%Y%m%d_%H%M%S)
cd backups/rq_migration_$(date +%Y%m%d_%H%M%S)

# Database backup
mysqldump vedfolnir > vedfolnir_backup.sql

# Redis backup (if existing data)
redis-cli bgsave
cp /var/lib/redis/dump.rdb redis_backup.rdb

# Application configuration backup
cp ../../.env env_backup
cp -r ../../config config_backup

# Log current system state
ps aux | grep -E "(caption_worker|simple_caption_worker)" > worker_processes.txt
mysql -u vedfolnir_user -p vedfolnir -e "SELECT status, COUNT(*) FROM images GROUP BY status;" > task_status.txt
```

### Step 1.2: Install RQ Dependencies
```bash
# Install required packages
pip install rq redis msgpack

# Verify installation
python -c "import rq, redis, msgpack; print('RQ dependencies installed successfully')"
```

### Step 1.3: Configure Environment
```bash
# Backup current environment
cp .env .env.pre_rq_backup

# Add RQ configuration to .env
cat >> .env << 'EOF'

# RQ Configuration
RQ_ENABLED=false
RQ_REDIS_URL=redis://localhost:6379/0
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=2
RQ_DEFAULT_TIMEOUT=3600
RQ_RESULT_TTL=86400
RQ_MAX_RETRIES=3

# RQ Monitoring
RQ_MONITORING_ENABLED=true
RQ_HEALTH_CHECK_INTERVAL=30
RQ_CLEANUP_INTERVAL=3600

# RQ Fallback
RQ_FALLBACK_ENABLED=true
RQ_FALLBACK_TIMEOUT=30
RQ_REDIS_HEALTH_CHECK_INTERVAL=30
EOF
```

### Step 1.4: Validate RQ System (Disabled)
```bash
# Test RQ system initialization without enabling
python -c "
from app.services.task.core.task_queue_manager import RQQueueManager
from config import Config
config = Config()
print('RQ system validation: OK')
"
```

## Phase 2: Hybrid Mode Setup

### Step 2.1: Enable RQ in Hybrid Mode
```bash
# Update environment for hybrid mode
sed -i 's/RQ_ENABLED=false/RQ_ENABLED=true/' .env
echo "RQ_HYBRID_MODE=true" >> .env
echo "DATABASE_POLLING_ENABLED=true" >> .env

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

### Step 2.2: Verify Hybrid Operation
```bash
# Check RQ workers started
curl -s http://localhost:8000/admin/rq/health | jq '.workers'

# Verify database workers still running
ps aux | grep -E "(caption_worker|simple_caption_worker)"

# Test task submission to both systems
python scripts/migration/test_hybrid_task_submission.py
```

### Step 2.3: Monitor Hybrid Performance
```bash
# Monitor for 30 minutes minimum
for i in {1..30}; do
    echo "=== Minute $i ==="
    
    # RQ queue status
    echo "RQ Queues:"
    redis-cli llen rq:queue:urgent
    redis-cli llen rq:queue:high
    redis-cli llen rq:queue:normal
    redis-cli llen rq:queue:low
    
    # Database queue status
    echo "Database Queue:"
    mysql -u vedfolnir_user -p vedfolnir -e "SELECT COUNT(*) FROM images WHERE status = 'QUEUED';"
    
    # System resources
    echo "Memory Usage:"
    free -h | grep Mem
    
    sleep 60
done > logs/hybrid_monitoring_$(date +%Y%m%d_%H%M%S).log
```

## Phase 3: Task Migration

### Step 3.1: Stop New Task Creation
```bash
# Enable maintenance mode for task submission
curl -X POST http://localhost:8000/admin/maintenance/pause-task-submission \
  -H "Content-Type: application/json" \
  -d '{"reason": "RQ migration in progress", "duration": "2 hours"}'
```

### Step 3.2: Wait for Current Tasks to Complete
```bash
# Monitor task completion
while true; do
    PROCESSING=$(mysql -u vedfolnir_user -p vedfolnir -e "SELECT COUNT(*) FROM images WHERE status = 'PROCESSING';" | tail -1)
    echo "Processing tasks: $PROCESSING"
    
    if [ "$PROCESSING" -eq 0 ]; then
        echo "All processing tasks completed"
        break
    fi
    
    sleep 30
done
```

### Step 3.3: Migrate Queued Tasks
```bash
# Run migration script
python scripts/migration/migrate_database_tasks_to_rq.py --verbose

# Verify migration
python scripts/migration/verify_task_migration.py

# Check migration results
echo "Migration Summary:"
redis-cli llen rq:queue:urgent
redis-cli llen rq:queue:high
redis-cli llen rq:queue:normal
redis-cli llen rq:queue:low
mysql -u vedfolnir_user -p vedfolnir -e "SELECT COUNT(*) FROM images WHERE status = 'QUEUED';"
```

### Step 3.4: Stop Database Workers
```bash
# Gracefully stop database workers
pkill -TERM -f caption_worker.py
pkill -TERM -f simple_caption_worker.py

# Wait for graceful shutdown
sleep 30

# Force stop if needed
pkill -KILL -f caption_worker.py
pkill -KILL -f simple_caption_worker.py

# Verify workers stopped
ps aux | grep -E "(caption_worker|simple_caption_worker)"
```

## Phase 4: RQ-Only Mode

### Step 4.1: Switch to RQ-Only Mode
```bash
# Update configuration
sed -i 's/RQ_HYBRID_MODE=true/RQ_HYBRID_MODE=false/' .env
sed -i 's/DATABASE_POLLING_ENABLED=true/DATABASE_POLLING_ENABLED=false/' .env

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

### Step 4.2: Resume Task Submission
```bash
# Disable maintenance mode
curl -X POST http://localhost:8000/admin/maintenance/resume-task-submission
```

### Step 4.3: Validate RQ Operation
```bash
# Submit test tasks
python scripts/migration/submit_test_tasks.py --count 10

# Monitor processing
for i in {1..10}; do
    echo "=== Test $i ==="
    curl -s http://localhost:8000/admin/rq/stats | jq '.queues'
    sleep 30
done
```

## Phase 5: Validation and Cleanup

### Step 5.1: Performance Validation
```bash
# Run performance tests
python scripts/migration/performance_validation.py

# Load testing
python scripts/migration/load_test_rq.py --tasks 100 --concurrent 10

# Monitor for 2 hours
python scripts/migration/monitor_rq_performance.py --duration 7200
```

### Step 5.2: Data Integrity Validation
```bash
# Verify task processing integrity
python scripts/migration/validate_task_integrity.py

# Check for data loss
python scripts/migration/check_data_consistency.py

# Validate user task constraints
python scripts/migration/validate_user_constraints.py
```

### Step 5.3: Cleanup Legacy Components
```bash
# Remove legacy worker scripts (after validation)
# Note: Keep backups for rollback capability
mkdir -p legacy_backup/workers
mv caption_worker.py legacy_backup/workers/
mv simple_caption_worker.py legacy_backup/workers/

# Clean up legacy configuration
sed -i '/DATABASE_POLLING_ENABLED/d' .env
sed -i '/RQ_HYBRID_MODE/d' .env

# Update documentation
echo "RQ migration completed on $(date)" >> docs/deployment/migration_history.md
```

## Migration Validation Scripts

### Create Migration Test Script
```bash
cat > scripts/migration/test_hybrid_task_submission.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script for hybrid mode task submission
"""

import sys
import time
import requests
from config import Config
from app.core.database.core.database_manager import DatabaseManager

def test_hybrid_submission():
    """Test task submission in hybrid mode"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    print("Testing hybrid mode task submission...")
    
    # Test RQ submission
    try:
        response = requests.post('http://localhost:8000/api/test-rq-task')
        print(f"RQ task submission: {response.status_code}")
    except Exception as e:
        print(f"RQ task submission failed: {e}")
    
    # Test database task creation
    try:
        with db_manager.get_session() as session:
            # Create test task in database
            from models import Image
            test_image = Image(
                url="http://example.com/test.jpg",
                status="QUEUED",
                user_id=1,
                platform_connection_id=1
            )
            session.add(test_image)
            session.commit()
            print(f"Database task created: ID {test_image.id}")
    except Exception as e:
        print(f"Database task creation failed: {e}")
    
    print("Hybrid mode test completed")

if __name__ == "__main__":
    test_hybrid_submission()
EOF

chmod +x scripts/migration/test_hybrid_task_submission.py
```

### Create Migration Verification Script
```bash
cat > scripts/migration/verify_task_migration.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Verify task migration from database to RQ
"""

import redis
from config import Config
from app.core.database.core.database_manager import DatabaseManager

def verify_migration():
    """Verify task migration completed successfully"""
    config = Config()
    db_manager = DatabaseManager(config)
    redis_client = redis.from_url(config.RQ_REDIS_URL)
    
    print("Verifying task migration...")
    
    # Check database queued tasks
    with db_manager.get_session() as session:
        from models import Image
        db_queued = session.query(Image).filter_by(status='QUEUED').count()
        print(f"Database queued tasks: {db_queued}")
    
    # Check RQ queues
    rq_queued = 0
    for queue in ['urgent', 'high', 'normal', 'low']:
        queue_len = redis_client.llen(f'rq:queue:{queue}')
        print(f"RQ {queue} queue: {queue_len}")
        rq_queued += queue_len
    
    print(f"Total RQ queued tasks: {rq_queued}")
    
    # Validation
    if db_queued == 0 and rq_queued > 0:
        print("✅ Migration successful: Tasks moved from database to RQ")
        return True
    elif db_queued > 0 and rq_queued == 0:
        print("❌ Migration incomplete: Tasks still in database")
        return False
    else:
        print(f"⚠️  Migration status unclear: DB={db_queued}, RQ={rq_queued}")
        return False

if __name__ == "__main__":
    success = verify_migration()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/migration/verify_task_migration.py
```

### Create Performance Validation Script
```bash
cat > scripts/migration/performance_validation.py << 'EOF'
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Performance validation for RQ system
"""

import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor

def test_task_submission_performance():
    """Test task submission performance"""
    print("Testing task submission performance...")
    
    submission_times = []
    
    for i in range(50):
        start_time = time.time()
        try:
            response = requests.post('http://localhost:8000/api/test-rq-task', timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                submission_times.append(end_time - start_time)
            else:
                print(f"Task {i} failed: {response.status_code}")
        except Exception as e:
            print(f"Task {i} error: {e}")
    
    if submission_times:
        avg_time = statistics.mean(submission_times)
        max_time = max(submission_times)
        min_time = min(submission_times)
        
        print(f"Task submission performance:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Maximum: {max_time:.3f}s")
        print(f"  Minimum: {min_time:.3f}s")
        
        # Performance targets
        if avg_time < 0.1:  # 100ms average
            print("✅ Performance target met")
            return True
        else:
            print("❌ Performance target not met")
            return False
    else:
        print("❌ No successful submissions")
        return False

def test_concurrent_submissions():
    """Test concurrent task submissions"""
    print("Testing concurrent task submissions...")
    
    def submit_task(task_id):
        try:
            response = requests.post('http://localhost:8000/api/test-rq-task', timeout=10)
            return response.status_code == 200
        except:
            return False
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(submit_task, i) for i in range(20)]
        results = [future.result() for future in futures]
    
    end_time = time.time()
    
    successful = sum(results)
    total_time = end_time - start_time
    
    print(f"Concurrent submission results:")
    print(f"  Successful: {successful}/20")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Throughput: {successful/total_time:.1f} tasks/second")
    
    return successful >= 18  # 90% success rate

if __name__ == "__main__":
    submission_ok = test_task_submission_performance()
    concurrent_ok = test_concurrent_submissions()
    
    if submission_ok and concurrent_ok:
        print("✅ Performance validation passed")
        sys.exit(0)
    else:
        print("❌ Performance validation failed")
        sys.exit(1)
EOF

chmod +x scripts/migration/performance_validation.py
```

## Migration Timeline

### Recommended Schedule

**Week 1: Preparation**
- Day 1-2: Install dependencies and configure environment
- Day 3-4: Test RQ system in development
- Day 5-7: Prepare migration scripts and documentation

**Week 2: Staging Migration**
- Day 1-2: Execute migration in staging environment
- Day 3-4: Performance testing and validation
- Day 5-7: Fix issues and refine procedures

**Week 3: Production Migration**
- Day 1: Final preparation and team briefing
- Day 2: Execute production migration (maintenance window)
- Day 3-5: Monitor and validate production operation
- Day 6-7: Cleanup and documentation update

### Maintenance Window Requirements

**Minimum Window**: 2 hours
**Recommended Window**: 4 hours
**Optimal Time**: Low-traffic period (e.g., Sunday 2-6 AM)

**Window Breakdown**:
- 30 minutes: Preparation and validation
- 60 minutes: Migration execution
- 60 minutes: Validation and testing
- 30 minutes: Cleanup and documentation

## Risk Mitigation

### Pre-Migration Risks
- **Redis unavailable**: Verify Redis service and backup
- **Insufficient disk space**: Check available space for backups
- **Database connectivity**: Test database connections
- **Application dependencies**: Verify all packages installed

### Migration Risks
- **Task data loss**: Comprehensive backups and validation
- **Performance degradation**: Gradual migration and monitoring
- **User impact**: Maintenance mode and communication
- **Rollback complexity**: Detailed rollback procedures

### Post-Migration Risks
- **RQ system failure**: Fallback mechanisms and monitoring
- **Performance issues**: Scaling and optimization procedures
- **Data inconsistency**: Validation scripts and monitoring
- **User experience**: Testing and feedback collection

## Success Criteria

### Technical Success Criteria
- ✅ All queued tasks migrated to RQ
- ✅ Zero data loss during migration
- ✅ RQ workers processing tasks successfully
- ✅ Performance meets or exceeds baseline
- ✅ Fallback mechanisms working
- ✅ Monitoring and alerting operational

### Business Success Criteria
- ✅ No user-visible service interruption
- ✅ Task processing time improved or maintained
- ✅ System reliability improved
- ✅ Administrative capabilities enhanced
- ✅ Rollback capability maintained

### Validation Checklist
```bash
# Technical validation
□ RQ workers running and healthy
□ All queue types operational
□ Task processing completing successfully
□ Database fallback working
□ Monitoring dashboards updated
□ Performance metrics within targets

# Business validation
□ User task submission working
□ Caption generation completing
□ Admin dashboard functional
□ No error reports from users
□ System logs clean
□ Support tickets normal
```

## Communication Plan

### Stakeholder Notification

**Pre-Migration (1 week before)**:
- System administrators: Technical briefing
- Users: Maintenance window announcement
- Support team: Procedure overview

**During Migration**:
- Real-time status updates
- Issue escalation procedures
- Rollback decision points

**Post-Migration**:
- Success confirmation
- Performance report
- Lessons learned documentation

### User Communication Template

```
Subject: Scheduled Maintenance - Caption Generation System Upgrade

Dear Vedfolnir Users,

We will be performing a scheduled maintenance upgrade to improve the performance and reliability of our caption generation system.

Maintenance Window: [Date] [Time] - [Time] [Timezone]
Expected Duration: 2-4 hours
Impact: Caption generation temporarily unavailable

During this maintenance:
- New caption requests will be queued
- Existing captions remain accessible
- All other features remain available

We expect improved performance and reliability after this upgrade.

Thank you for your patience.

The Vedfolnir Team
```