# Session Management System Deployment Guide

## Pre-Deployment Validation

### Run Deployment Checker
```bash
python scripts/deployment/session_management_deployment_checklist.py
```

### Run E2E Tests
```bash
python scripts/testing/run_session_management_e2e_tests.py
```

## Deployment Steps

### 1. Database Migration
```bash
# Backup database
pg_dump vedfolnir > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migrations
python -c "from database import DatabaseManager; from config import Config; DatabaseManager(Config()).create_tables()"
```

### 2. Deploy Application
```bash
# Stop application
sudo systemctl stop vedfolnir

# Deploy code
git pull origin main
pip install -r requirements.txt

# Validate deployment
python scripts/deployment/session_management_deployment_checklist.py

# Start application
sudo systemctl start vedfolnir
```

## Post-Deployment Validation

### Health Checks
```bash
# Basic health
curl -f http://localhost:5000/health

# Session health (admin)
curl -f -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:5000/admin/session-health/status
```

### Performance Targets
- Session creation: < 200ms
- Session validation: < 100ms
- Platform switching: < 150ms

## Rollback
```bash
./rollback_session_management.sh
```

## Monitoring
- Session creation/validation rates
- Database connection pool usage
- Error rates and response times
- Cross-tab synchronization performance