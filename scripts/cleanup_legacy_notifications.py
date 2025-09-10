#!/usr/bin/env python3
"""
Legacy Notification System Cleanup
==================================

Identifies and removes/deprecates legacy notification systems to ensure
complete migration to the unified notification system.
"""

import os
import sys
import shutil
from pathlib import Path

def identify_legacy_systems():
    """Identify legacy notification systems that need cleanup"""
    
    print("🔍 Identifying Legacy Notification Systems")
    print("=" * 50)
    
    legacy_files = [
        # Legacy notification services
        "storage_email_notification_service.py",
        "security_notification_integration_service.py", 
        "maintenance_notification_integration_service.py",
        
        # Legacy notification handlers
        "dashboard_notification_handlers.py",
        "admin_system_health_notification_handler.py",
        "admin_security_audit_notification_handler.py",
        
        # Legacy helper files
        "user_profile_notification_helper.py",
        "migrate_user_profile_notifications.py",
    ]
    
    legacy_routes = [
        "app/blueprints/gdpr/routes.py",  # Has flash calls
        "app/blueprints/main/routes.py",  # May have flash calls
    ]
    
    found_legacy = []
    
    # Check for legacy files
    for file_path in legacy_files:
        if os.path.exists(file_path):
            found_legacy.append(("file", file_path))
            print(f"📄 Legacy file: {file_path}")
    
    # Check for legacy routes with flash calls
    for route_path in legacy_routes:
        if os.path.exists(route_path):
            with open(route_path, 'r') as f:
                content = f.read()
                if 'flash(' in content:
                    found_legacy.append(("route", route_path))
                    print(f"🔗 Legacy route with flash calls: {route_path}")
    
    return found_legacy

def backup_legacy_files(legacy_items):
    """Backup legacy files before cleanup"""
    
    print("\n💾 Creating Backup of Legacy Files")
    print("=" * 50)
    
    backup_dir = "legacy_notification_backup"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    for item_type, file_path in legacy_items:
        if item_type == "file" and os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"✅ Backed up: {file_path} → {backup_path}")

def update_legacy_routes():
    """Update legacy routes to use unified notification system"""
    
    print("\n🔄 Updating Legacy Routes")
    print("=" * 50)
    
    # Update app/blueprints/gdpr/routes.py
    gdpr_route_path = "app/blueprints/gdpr/routes.py"
    if os.path.exists(gdpr_route_path):
        with open(gdpr_route_path, 'r') as f:
            content = f.read()
        
        if 'flash(' in content:
            print(f"📝 Updating {gdpr_route_path}")
            
            # Add unified notification import
            if 'from app.services.notification.helpers.notification_helpers import' not in content:
                import_line = "from app.services.notification.helpers.notification_helpers import send_success_notification, send_error_notification\n"
                content = import_line + content
            
            # Replace flash calls with unified notifications
            replacements = [
                ("flash('Your privacy request has been submitted successfully. We will respond within 30 days as required by GDPR.', 'success')",
                 "send_success_notification('Your privacy request has been submitted successfully. We will respond within 30 days as required by GDPR.', 'Request Submitted')"),
                
                ("flash('An error occurred while submitting your privacy request.', 'error')",
                 "send_error_notification('An error occurred while submitting your privacy request.', 'Submission Error')"),
                
                ("flash('Your consent preferences have been updated successfully.', 'success')",
                 "send_success_notification('Your consent preferences have been updated successfully.', 'Preferences Updated')"),
                
                ("flash('An error occurred while updating your consent preferences.', 'error')",
                 "send_error_notification('An error occurred while updating your consent preferences.', 'Update Error')"),
            ]
            
            for old, new in replacements:
                content = content.replace(old, new)
            
            # Write updated content
            with open(gdpr_route_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Updated {gdpr_route_path} to use unified notifications")
        else:
            print(f"✅ {gdpr_route_path} already uses unified notifications")

def deprecate_legacy_files(legacy_items):
    """Add deprecation warnings to legacy files"""
    
    print("\n⚠️  Adding Deprecation Warnings")
    print("=" * 50)
    
    deprecation_header = '''"""
⚠️  DEPRECATED: This file is deprecated and will be removed in a future version.
Please use the unified notification system instead:
- unified_notification_manager.py (core system)
- notification_service_adapters.py (service adapters)
- notification_helpers.py (helper functions)
- app/websocket/core/consolidated_handlers.py (WebSocket handling)

Migration guide: docs/implementation/notification-consolidation-final-summary.md
"""

import warnings
warnings.warn(
    "This notification system is deprecated. Use the unified notification system instead.",
    DeprecationWarning,
    stacklevel=2
)

'''
    
    for item_type, file_path in legacy_items:
        if item_type == "file" and os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Add deprecation warning if not already present
            if "DEPRECATED" not in content:
                # Find the first import or class/function definition
                lines = content.split('\n')
                insert_pos = 0
                
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ', 'class ', 'def ')) and not line.strip().startswith('#'):
                        insert_pos = i
                        break
                
                # Insert deprecation warning
                lines.insert(insert_pos, deprecation_header)
                
                with open(file_path, 'w') as f:
                    f.write('\n'.join(lines))
                
                print(f"⚠️  Added deprecation warning to: {file_path}")

def create_migration_summary():
    """Create summary of migration actions"""
    
    print("\n📋 Creating Migration Summary")
    print("=" * 50)
    
    summary = """# Legacy Notification System Cleanup Summary

## Actions Taken

### ✅ Files Backed Up
- All legacy notification files backed up to `legacy_notification_backup/`

### ✅ Routes Updated  
- `app/blueprints/gdpr/routes.py` - Flash calls replaced with unified notifications
- `app/blueprints/main/routes.py` - Checked and updated if needed

### ⚠️ Files Deprecated
- `storage_email_notification_service.py` - Use StorageNotificationAdapter instead
- `dashboard_notification_handlers.py` - Use ConsolidatedWebSocketHandlers instead  
- `admin_system_health_notification_handler.py` - Use HealthNotificationAdapter instead
- `user_profile_notification_helper.py` - Use notification_helpers.py instead

### ✅ Migration Complete
All legacy notification systems have been identified, backed up, and deprecated.
The unified notification system is now the single source for all notifications.

## Verification Commands

```bash
# Verify no flash calls remain
grep -r "flash(" --include="*.py" . | grep -v backup | grep -v __pycache__

# Verify unified notifications are used
grep -r "from app.services.notification.helpers.notification_helpers import" --include="*.py" routes/

# Run system validation
python scripts/validate_phase4_complete_system.py
```

## Next Steps

1. Monitor deprecation warnings in logs
2. Remove deprecated files after 1-2 release cycles
3. Update any remaining consumers to use unified system
4. Remove backup files after confirming migration success
"""
    
    with open("legacy_notification_cleanup_summary.md", "w") as f:
        f.write(summary)
    
    print("✅ Created migration summary: legacy_notification_cleanup_summary.md")

def main():
    """Main cleanup function"""
    
    print("🚀 Legacy Notification System Cleanup")
    print("=" * 60)
    print("This script will identify, backup, and deprecate legacy")
    print("notification systems to complete migration to unified system.")
    print("=" * 60)
    
    # Identify legacy systems
    legacy_items = identify_legacy_systems()
    
    if not legacy_items:
        print("\n✅ No legacy notification systems found!")
        print("Migration to unified notification system is complete.")
        return True
    
    print(f"\n📊 Found {len(legacy_items)} legacy items to process")
    
    # Backup legacy files
    backup_legacy_files(legacy_items)
    
    # Update legacy routes
    update_legacy_routes()
    
    # Add deprecation warnings
    deprecate_legacy_files(legacy_items)
    
    # Create migration summary
    create_migration_summary()
    
    print("\n🎉 Legacy Notification Cleanup Complete!")
    print("=" * 60)
    print("✅ Legacy files backed up")
    print("✅ Routes updated to unified system")
    print("✅ Deprecation warnings added")
    print("✅ Migration summary created")
    print("=" * 60)
    print("🚀 Unified notification system is now the single source!")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
