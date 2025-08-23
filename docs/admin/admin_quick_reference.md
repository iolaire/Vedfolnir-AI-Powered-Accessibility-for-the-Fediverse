# Administrator Quick Reference Guide

## Emergency Procedures

### 🚨 System Emergency
```bash
# Emergency stop all jobs
python scripts/deployment/manage_feature_flags.py emergency

# Check system health
python scripts/deployment/admin_health_checks.py

# Emergency rollback
python scripts/deployment/rollback_procedures.py emergency --confirm
```

### 🔧 Common Admin Tasks

**Access Admin Dashboard**
```
URL: /admin/dashboard
Login with admin credentials
```

**Cancel User Job**
1. Admin Dashboard → Job Management
2. Find job → Click "Cancel"
3. Provide reason → Confirm

**Suspend User Account**
1. Admin Dashboard → User Management
2. Find user → Click "Suspend"
3. Provide reason → Confirm

**Enable/Disable Features**
```bash
# Enable admin dashboard
python scripts/deployment/manage_feature_flags.py enable admin_dashboard

# Disable feature
python scripts/deployment/manage_feature_flags.py disable feature_name
```

## System Monitoring

### Health Check Commands
```bash
# Full health check
python scripts/deployment/admin_health_checks.py

# Specific service
python scripts/deployment/admin_health_checks.py --service database

# Continuous monitoring
python scripts/deployment/admin_health_checks.py --continuous
```

### Log Locations
- Application: `logs/webapp.log`
- Caption Generation: `logs/caption_generation_steps.log`
- Security Events: `logs/security_events.log`
- Admin Actions: `logs/admin_actions.log`

## Configuration Management

### Feature Flags
```bash
# List all flags
python scripts/deployment/manage_feature_flags.py list

# Show specific flag
python scripts/deployment/manage_feature_flags.py show multi_tenant_admin

# Rollout plan
python scripts/deployment/manage_feature_flags.py rollout phase1_readonly
```

### Configuration Files
- Feature Flags: `config/feature_flags.json`
- Admin Settings: `config/admin_settings.json`
- Environment: `.env`

## Database Operations

### Migration Commands
```bash
# Run admin migration
python scripts/deployment/run_multi_tenant_migration.py --action migrate

# Verify migration
python scripts/deployment/run_multi_tenant_migration.py --action verify

# Rollback migration
python scripts/deployment/run_multi_tenant_migration.py --action rollback
```

### Database Health
```bash
# Check database
python -c "from database import DatabaseManager; from config import Config; 
           db = DatabaseManager(Config()); 
           with db.get_session() as s: print('Database OK')"
```

## User Management

### Admin User Creation
```bash
# Create admin user
python scripts/setup/create_admin_user.py --username admin --email admin@example.com

# Promote existing user
python scripts/setup/promote_user_to_admin.py --username existing_user
```

### User Account Actions
- **View Users**: Admin Dashboard → User Management
- **Create User**: Click "Add New User"
- **Modify User**: Click username → Edit details
- **Suspend User**: User details → "Suspend Account"

## Job Management

### Job Actions
- **View All Jobs**: Admin Dashboard → Job Management
- **Cancel Job**: Job list → "Cancel" button
- **Restart Job**: Failed jobs → "Restart" button
- **Set Priority**: Job list → "Set Priority"

### Bulk Operations
1. Select jobs with checkboxes
2. Choose bulk action from dropdown
3. Confirm action

## Alert Management

### Alert Configuration
```
Admin Dashboard → System Monitoring → Alert Configuration
```

### Alert Response
1. **Acknowledge**: Click alert → "Acknowledge"
2. **Resolve**: Fix issue → "Resolve"
3. **Escalate**: Forward to technical team

## Troubleshooting

### Common Issues

**Jobs Stuck in Pending**
- Check AI service: `curl http://localhost:11434/api/version`
- Restart job processing
- Check system resources

**Users Can't Login**
- Check Redis: `redis-cli ping`
- Verify user account status
- Check session configuration

**High Error Rates**
- Review error logs: `tail -f logs/webapp.log | grep ERROR`
- Check platform API status
- Verify credentials

### Diagnostic Commands
```bash
# System status
python scripts/deployment/admin_health_checks.py

# Database performance
python scripts/monitoring/check_database_health.py

# Redis status
redis-cli info
```

## Backup and Recovery

### Create Backup
```bash
# Full system backup
python scripts/deployment/rollback_procedures.py create --description "Pre-maintenance backup"

# Configuration backup
python scripts/deployment/configuration_migration.py backup
```

### Restore from Backup
```bash
# Emergency rollback
python scripts/deployment/rollback_procedures.py emergency --confirm

# Specific rollback point
python scripts/deployment/rollback_procedures.py rollback rollback_20250822_120000 --confirm
```

## Performance Optimization

### Resource Monitoring
- **CPU/Memory**: Admin Dashboard → System Monitoring
- **Database**: Check slow queries and connections
- **Redis**: Monitor memory usage and hit rates

### Optimization Actions
- Clear caches
- Restart services
- Adjust job limits
- Optimize database queries

## Security

### Security Checklist
- [ ] Review admin account activity
- [ ] Check failed login attempts
- [ ] Monitor suspicious user behavior
- [ ] Review audit logs
- [ ] Update security configurations

### Security Commands
```bash
# Security audit
python scripts/security/run_security_audit.py

# Check failed logins
grep "Failed login" logs/security_events.log
```

## Contact Information

### Emergency Contacts
- **System Administrator**: [Contact Info]
- **Technical Support**: [Contact Info]
- **Security Team**: [Contact Info]

### Documentation Links
- **Full Admin Guide**: `docs/admin/administrator_training_guide.md`
- **API Reference**: `docs/api/admin_api_reference.md`
- **Troubleshooting**: `docs/admin/troubleshooting_guide.md`
- **Security Manual**: `docs/security/admin_security_guide.md`

---

**Remember**: Always create backups before making significant changes!