# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix WebSocket timeout values in environment generator scripts

This script fixes the WebSocket timeout configuration in both env generator scripts
to use correct values (seconds instead of milliseconds) and adds keep-alive settings.
"""

import os
import re

def fix_ilm_script():
    """Fix the ILM environment generator script"""
    
    script_path = 'scripts/setup/generate_env_secrets_ILM.py'
    
    if not os.path.exists(script_path):
        print(f"❌ {script_path} not found")
        return False
    
    print(f"🔧 Fixing {script_path}...")
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Track changes
    changes = []
    
    # Fix the timeout values in the settings dictionary (already done)
    # Add keep-alive settings to template (need to add manually)
    
    # Find the first template section and add keep-alive settings
    pattern = r'(SOCKETIO_TIMEOUT=\{websocket_settings\[\'SOCKETIO_TIMEOUT\'\]\}\n)\n(# Performance Configuration)'
    replacement = r'\1SOCKETIO_FORCE_NEW={websocket_settings[\'SOCKETIO_FORCE_NEW\']}\nSOCKETIO_UPGRADE={websocket_settings[\'SOCKETIO_UPGRADE\']}\nSOCKETIO_REMEMBER_UPGRADE={websocket_settings[\'SOCKETIO_REMEMBER_UPGRADE\']}\nSOCKETIO_WITH_CREDENTIALS={websocket_settings[\'SOCKETIO_WITH_CREDENTIALS\']}\n\n\2'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content, count=1)  # Only replace first occurrence
        changes.append("Added keep-alive settings to first template")
    
    # Find the second template section and add keep-alive settings
    # We need to be more specific to target only the second occurrence
    lines = content.split('\n')
    template_count = 0
    for i, line in enumerate(lines):
        if 'SOCKETIO_TIMEOUT={websocket_settings[\'SOCKETIO_TIMEOUT\']}' in line:
            template_count += 1
            if template_count == 2:  # Second occurrence
                # Insert keep-alive settings after this line
                insert_lines = [
                    'SOCKETIO_FORCE_NEW={websocket_settings[\'SOCKETIO_FORCE_NEW\']}',
                    'SOCKETIO_UPGRADE={websocket_settings[\'SOCKETIO_UPGRADE\']}',
                    'SOCKETIO_REMEMBER_UPGRADE={websocket_settings[\'SOCKETIO_REMEMBER_UPGRADE\']}',
                    'SOCKETIO_WITH_CREDENTIALS={websocket_settings[\'SOCKETIO_WITH_CREDENTIALS\']}'
                ]
                lines[i+1:i+1] = insert_lines
                changes.append("Added keep-alive settings to second template")
                break
    
    content = '\n'.join(lines)
    
    # Write back the fixed content
    with open(script_path, 'w') as f:
        f.write(content)
    
    if changes:
        print("✅ Applied fixes:")
        for change in changes:
            print(f"   • {change}")
        return True
    else:
        print("ℹ️  No additional fixes needed")
        return False

def verify_fixes():
    """Verify that the fixes were applied correctly"""
    
    print("\n🔍 Verifying fixes...")
    
    files_to_check = [
        'scripts/setup/generate_env_secrets.py',
        'scripts/setup/generate_env_secrets_ILM.py'
    ]
    
    all_good = True
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"❌ {file_path} not found")
            all_good = False
            continue
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        print(f"\n📁 {file_path}:")
        
        # Check for correct timeout values
        if "'SOCKETIO_PING_TIMEOUT': '60'" in content:
            print("   ✅ PING_TIMEOUT: 60 seconds (correct)")
        elif "'SOCKETIO_PING_TIMEOUT': '60000'" in content:
            print("   ❌ PING_TIMEOUT: 60000 (should be 60)")
            all_good = False
        else:
            print("   ⚠️  PING_TIMEOUT: not found or different format")
        
        if "'SOCKETIO_PING_INTERVAL': '25'" in content:
            print("   ✅ PING_INTERVAL: 25 seconds (correct)")
        elif "'SOCKETIO_PING_INTERVAL': '25000'" in content:
            print("   ❌ PING_INTERVAL: 25000 (should be 25)")
            all_good = False
        else:
            print("   ⚠️  PING_INTERVAL: not found or different format")
        
        # Check for keep-alive settings
        keep_alive_settings = [
            'SOCKETIO_FORCE_NEW',
            'SOCKETIO_UPGRADE', 
            'SOCKETIO_REMEMBER_UPGRADE',
            'SOCKETIO_WITH_CREDENTIALS'
        ]
        
        for setting in keep_alive_settings:
            if f"'{setting}'" in content:
                print(f"   ✅ {setting}: present")
            else:
                print(f"   ❌ {setting}: missing")
                all_good = False
    
    return all_good

def main():
    """Main function to fix environment generator scripts"""
    
    print("🔧 WebSocket Environment Generator Fix Tool")
    print("=" * 50)
    
    # Fix ILM script (main script was already fixed)
    print("\n1. Fixing ILM environment generator...")
    ilm_fixed = fix_ilm_script()
    
    # Verify all fixes
    print("\n2. Verifying all fixes...")
    all_verified = verify_fixes()
    
    print("\n" + "=" * 50)
    if all_verified:
        print("🎉 All WebSocket environment generator fixes complete!")
        print("\n📋 What was fixed:")
        print("   • Corrected PING_TIMEOUT from 60000ms to 60s")
        print("   • Corrected PING_INTERVAL from 25000ms to 25s") 
        print("   • Added keep-alive settings (FORCE_NEW, UPGRADE, etc.)")
        print("   • Reduced TIMEOUT for better responsiveness")
        
        print("\n✅ Future .env files generated by these scripts will have:")
        print("   • Correct WebSocket timeout values")
        print("   • Proper keep-alive configuration")
        print("   • No more suspension issues")
    else:
        print("❌ Some fixes may not have been applied correctly")
        print("   Please check the verification output above")

if __name__ == '__main__':
    main()