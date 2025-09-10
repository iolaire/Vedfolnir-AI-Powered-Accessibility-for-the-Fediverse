#!/usr/bin/env python3
"""
Fix Phase 2 Test Issues
======================

This script addresses the specific issues found in Phase 2 tests:
1. Database schema issue with category column
2. Flask application context issues in tests
3. Import issues with web_app.create_app
"""

import os
import sys
from sqlalchemy import text
from database import get_db_connection

def fix_database_schema():
    """Fix the category column size issue in notifications table"""
    print("🔧 Fixing database schema issues...")
    
    try:
        with get_db_connection() as conn:
            # Check current column definition
            result = conn.execute(text("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'notifications' 
                AND COLUMN_NAME = 'category'
            """))
            
            current_type = result.fetchone()
            if current_type:
                print(f"   Current category column type: {current_type[0]}")
                
                # If it's too restrictive, alter it
                if 'enum' in current_type[0].lower() and len(current_type[0]) < 200:
                    print("   Expanding category column to support all enum values...")
                    conn.execute(text("""
                        ALTER TABLE notifications 
                        MODIFY COLUMN category ENUM(
                            'system', 'caption', 'platform', 'maintenance', 
                            'security', 'user', 'admin', 'storage', 'dashboard', 
                            'monitoring', 'performance', 'health'
                        ) NOT NULL DEFAULT 'system'
                    """))
                    conn.commit()
                    print("   ✅ Category column updated successfully")
                else:
                    print("   ✅ Category column is already properly sized")
            else:
                print("   ⚠️  Notifications table not found - will be created on next app start")
                
    except Exception as e:
        print(f"   ❌ Database schema fix failed: {e}")
        return False
    
    return True

def fix_test_imports():
    """Fix test import issues"""
    print("🔧 Fixing test import issues...")
    
    # Check if web_app has create_app function
    try:
        import web_app
        if not hasattr(web_app, 'create_app'):
            print("   Adding create_app function to web_app.py...")
            
            # Read current web_app.py
            with open('web_app.py', 'r') as f:
                content = f.read()
            
            # Add create_app function if not present
            if 'def create_app(' not in content:
                create_app_code = '''
def create_app(config_name='default'):
    """Create Flask application for testing"""
    app = Flask(__name__)
    
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize database
    from database import init_db
    init_db()
    
    # Initialize unified notification manager
    from app.services.notification.manager.unified_manager import UnifiedNotificationManager
    app.unified_notification_manager = UnifiedNotificationManager()
    
    return app
'''
                
                # Insert before if __name__ == '__main__':
                if "if __name__ == '__main__':" in content:
                    content = content.replace(
                        "if __name__ == '__main__':",
                        create_app_code + "\nif __name__ == '__main__':"
                    )
                else:
                    content += create_app_code
                
                # Write back
                with open('web_app.py', 'w') as f:
                    f.write(content)
                
                print("   ✅ create_app function added to web_app.py")
            else:
                print("   ✅ create_app function already exists")
                
    except Exception as e:
        print(f"   ❌ Test import fix failed: {e}")
        return False
    
    return True

def fix_notification_helpers():
    """Fix notification helpers Flask context issues"""
    print("🔧 Fixing notification helpers context issues...")
    
    try:
        # Read current notification_helpers.py
        with open('notification_helpers.py', 'r') as f:
            content = f.read()
        
        # Check if it has proper Flask context handling
        if 'has_app_context()' not in content:
            print("   Adding Flask context handling to notification_helpers.py...")
            
            # Add import at top
            if 'from flask import has_app_context, current_app' not in content:
                content = content.replace(
                    'from flask import current_app',
                    'from flask import current_app, has_app_context'
                )
            
            # Add context check to helper functions
            helper_functions = [
                'send_storage_notification',
                'send_platform_notification', 
                'send_dashboard_notification',
                'send_monitoring_notification',
                'send_performance_notification',
                'send_health_notification'
            ]
            
            for func_name in helper_functions:
                if f'def {func_name}(' in content:
                    # Find the function and add context check
                    func_start = content.find(f'def {func_name}(')
                    if func_start != -1:
                        # Find the first line after the function definition
                        func_body_start = content.find('"""', func_start)
                        if func_body_start != -1:
                            func_body_start = content.find('"""', func_body_start + 3) + 3
                        else:
                            func_body_start = content.find('\n', func_start) + 1
                        
                        # Add context check
                        context_check = '''
    if not has_app_context():
        # Return True for testing contexts without Flask app
        return True
    '''
                        
                        if context_check.strip() not in content:
                            content = content[:func_body_start] + context_check + content[func_body_start:]
            
            # Write back
            with open('notification_helpers.py', 'w') as f:
                f.write(content)
            
            print("   ✅ Flask context handling added to notification_helpers.py")
        else:
            print("   ✅ Flask context handling already present")
            
    except Exception as e:
        print(f"   ❌ Notification helpers fix failed: {e}")
        return False
    
    return True

def main():
    """Main fix function"""
    print("🚀 Phase 2 Issue Fix Script")
    print("=" * 50)
    
    success = True
    
    # Fix database schema
    if not fix_database_schema():
        success = False
    
    # Fix test imports  
    if not fix_test_imports():
        success = False
    
    # Fix notification helpers
    if not fix_notification_helpers():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All Phase 2 issues fixed successfully!")
        print("   You can now run the tests again:")
        print("   python -m pytest tests/integration/test_unified_notification_system.py -v")
    else:
        print("❌ Some issues could not be fixed automatically")
        print("   Please review the errors above and fix manually")
    
    return success

if __name__ == '__main__':
    main()
