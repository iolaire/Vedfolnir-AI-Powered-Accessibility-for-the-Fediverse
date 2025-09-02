# Emergency Quick Reference Card

## 🚨 CRITICAL NOTIFICATION SYSTEM FAILURE

### Immediate Response (First 5 Minutes)

#### 1. Assess Situation
```bash
# Quick health check
python scripts/enhanced_notification_emergency_cli.py health-check

# Check system status
curl -I http://127.0.0.1:5000/
ps aux | grep "python.*web_app.py"
```

#### 2. Activate Emergency Mode
```bash
# Activate emergency procedures
python scripts/enhanced_notification_emergency_cli.py backup
python scripts/notification_emergency_cli.py activate-emergency \
  --reason "Critical system failure" --triggered-by "$(whoami)"
```

#### 3. Emergency Rollback (If Required)
```bash
# Execute immediate rollback
python scripts/enhanced_notification_emergency_cli.py rollback --confirm

# Monitor rollback progress
tail -f /var/log/notification_rollback.log
```

---

## 📞 Emergency Contacts

- **Senior Administrator**: [Contact Info]
- **System Administrator**: [Contact Info]  
- **Emergency Hotline**: [Phone Number]
- **Security Team**: [Contact Info]

---

## 🔧 Quick Diagnostics

### System Health
```bash
# Database connectivity
mysql -u vedfolnir_user -p vedfolnir -e "SELECT 1"

# Redis connectivity  
redis-cli ping

# Web application
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/
```

### Performance Check
```bash
# System resources
free -m && df -h
top -bn1 | head -20

# Process status
ps aux | grep -E "(python|mysql|redis)"
```

---

## 🔄 Recovery Actions

### Restart Services
```bash
# Stop services
pkill -f "python.*web_app.py"
sudo systemctl stop redis-server

# Start services
sudo systemctl start redis-server
python web_app.py & sleep 10
```

### Clear Caches
```bash
# Clear Redis cache
redis-cli FLUSHDB

# Clear application cache
rm -rf __pycache__/
rm -rf storage/temp/*
```

---

## 📋 Validation Checklist

After any recovery action:

- [ ] Web application responding (HTTP 200)
- [ ] Database connectivity working
- [ ] Redis connectivity working  
- [ ] User login functionality working
- [ ] Admin dashboard accessible
- [ ] No critical errors in logs
- [ ] System performance acceptable

---

## 📄 Documentation Links

- **Full Emergency Procedures**: `docs/notification-system-emergency-procedures.md`
- **Rollback Procedures**: `docs/notification-system-rollback-procedures.md`
- **System Architecture**: `docs/system-architecture.md`

---

## 🛠️ Emergency Tools

### CLI Tools
```bash
# Enhanced emergency CLI
python scripts/enhanced_notification_emergency_cli.py [command]

# Original emergency CLI  
python scripts/notification_emergency_cli.py [command]

# Validation script
python scripts/validate_emergency_recovery.py
```

### Rollback Script
```bash
# Automated rollback
bash scripts/rollback_notification_system.sh
```

---

## 📊 Status Codes

- **🟢 Healthy**: All systems operational
- **🟡 Warning**: Minor issues, monitor closely
- **🟠 Degraded**: Significant issues, action required
- **🔴 Critical**: System failure, immediate action required

---

**Keep this card accessible during emergencies**  
**Last Updated**: August 30, 2025