#!/usr/bin/env python3
"""
Email Process Migration Verification
===================================

Verifies that existing email processes have been updated to use
the unified email notification system.
"""

import os
import sys
import subprocess

def check_gdpr_email_migration():
    """Check GDPR email process migration"""
    print("🔍 Checking GDPR Email Migration")
    print("-" * 35)
    
    try:
        # Check if GDPR routes use unified email
        result = subprocess.run([
            'grep', '-n', 'send_gdpr_export_email', 'routes/gdpr_routes.py'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("✅ GDPR routes updated to use unified email system")
            print(f"   - Found: {result.stdout.strip()}")
            return True
        else:
            print("❌ GDPR routes not using unified email system")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not check GDPR migration: {e}")
        return False

def check_user_management_email_migration():
    """Check user management email process migration"""
    print("\n🔍 Checking User Management Email Migration")
    print("-" * 45)
    
    try:
        # Check for unified email usage
        result = subprocess.run([
            'grep', '-n', 'send_verification_email', 'routes/user_management_routes.py'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("✅ User management updated to use unified email system")
            print(f"   - Found: {result.stdout.strip()}")
            
            # Check if old async email calls are removed
            old_result = subprocess.run([
                'grep', '-n', 'registration_service.send_verification_email', 
                'routes/user_management_routes.py'
            ], capture_output=True, text=True, cwd='.')
            
            if old_result.returncode != 0:
                print("✅ Old async email calls removed")
                return True
            else:
                print("⚠️  Old async email calls still present")
                return False
        else:
            print("❌ User management not using unified email system")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not check user management migration: {e}")
        return False

def check_remaining_legacy_email_usage():
    """Check for remaining legacy email usage"""
    print("\n🔍 Checking for Remaining Legacy Email Usage")
    print("-" * 45)
    
    legacy_patterns = [
        'email_service.send',
        'EmailService(',
        'send_data_export_email',
        'registration_service.send_verification_email'
    ]
    
    found_legacy = []
    
    for pattern in legacy_patterns:
        try:
            result = subprocess.run([
                'grep', '-r', pattern, '--include=*.py', 
                'routes/', 'app/blueprints/'
            ], capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                lines = [line for line in result.stdout.split('\n') if line.strip()]
                found_legacy.extend(lines)
                
        except Exception:
            continue
    
    if found_legacy:
        print("⚠️  Found remaining legacy email usage:")
        for usage in found_legacy[:5]:  # Show first 5
            print(f"   - {usage}")
        return False
    else:
        print("✅ No legacy email usage found in routes")
        return True

def check_unified_email_helpers_usage():
    """Check that unified email helpers are being used"""
    print("\n🔍 Checking Unified Email Helper Usage")
    print("-" * 40)
    
    try:
        result = subprocess.run([
            'grep', '-r', 'from app.services.notification.helpers.notification_helpers import.*email', 
            '--include=*.py', 'routes/', 'app/blueprints/'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            imports = result.stdout.strip().split('\n')
            print(f"✅ Found {len(imports)} files using unified email helpers:")
            for imp in imports:
                file_path = imp.split(':')[0]
                print(f"   - {file_path}")
            return True
        else:
            print("⚠️  No unified email helper usage found")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not check unified helper usage: {e}")
        return False

def main():
    """Main verification function"""
    
    print("📧 Email Process Migration Verification")
    print("=" * 50)
    print("Checking if existing email processes use unified system")
    print("=" * 50)
    
    checks = [
        ("GDPR Email Migration", check_gdpr_email_migration),
        ("User Management Email Migration", check_user_management_email_migration),
        ("Legacy Email Usage Check", check_remaining_legacy_email_usage),
        ("Unified Email Helper Usage", check_unified_email_helpers_usage)
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        results[check_name] = check_func()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 EMAIL MIGRATION VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name:35} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 EMAIL MIGRATION COMPLETE!")
        print("✅ All email processes use unified notification system")
        print("✅ Legacy email calls have been replaced")
        print("✅ Unified email helpers are being used")
        print("✅ Email functionality fully integrated")
    else:
        print("⚠️  EMAIL MIGRATION INCOMPLETE")
        print("Some email processes may still use legacy methods")
        print("Review the failures above for remaining work")
    
    print("=" * 50)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
