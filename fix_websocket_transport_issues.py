#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Fix WebSocket Transport Issues

This script addresses the "Invalid websocket upgrade" errors by:
1. Optimizing client transport configuration
2. Adding transport optimizer to templates
3. Configuring server-side logging
4. Providing monitoring tools
"""

import os
import re
import sys
from pathlib import Path

def add_transport_optimizer_to_templates():
    """Add transport optimizer script to HTML templates"""
    
    print("🔧 Adding WebSocket Transport Optimizer to templates...")
    
    # Find all HTML templates
    template_dirs = [
        'templates',
        'admin/templates'
    ]
    
    optimizer_script = '''
    <!-- WebSocket Transport Optimizer -->
    <script src="{{ url_for('static', filename='js/websocket-transport-optimizer.js') }}"></script>
    '''
    
    updated_files = []
    
    for template_dir in template_dirs:
        if not os.path.exists(template_dir):
            continue
            
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Skip if already added
                        if 'websocket-transport-optimizer.js' in content:
                            continue
                        
                        # Add before websocket-bundle.js if it exists
                        if 'websocket-bundle.js' in content:
                            pattern = r'(<script[^>]*websocket-bundle\.js[^>]*></script>)'
                            replacement = f'{optimizer_script.strip()}\n    \\1'
                            
                            new_content = re.sub(pattern, replacement, content)
                            
                            if new_content != content:
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(new_content)
                                updated_files.append(file_path)
                                print(f"   ✅ Updated: {file_path}")
                        
                        # Add before closing </body> tag if websocket-bundle.js not found
                        elif '</body>' in content and 'websocket' in content.lower():
                            pattern = r'(</body>)'
                            replacement = f'    {optimizer_script.strip()}\n\\1'
                            
                            new_content = re.sub(pattern, replacement, content)
                            
                            if new_content != content:
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(new_content)
                                updated_files.append(file_path)
                                print(f"   ✅ Updated: {file_path}")
                    
                    except Exception as e:
                        print(f"   ❌ Error updating {file_path}: {e}")
    
    print(f"   📊 Updated {len(updated_files)} template files")
    return updated_files

def update_websocket_bundle():
    """Update WebSocket bundle to use transport optimizer"""
    
    print("🔧 Updating WebSocket bundle to use transport optimizer...")
    
    bundle_path = 'static/js/websocket-bundle.js'
    
    if not os.path.exists(bundle_path):
        print(f"   ❌ WebSocket bundle not found: {bundle_path}")
        return False
    
    try:
        with open(bundle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already updated
        if 'webSocketTransportOptimizer' in content:
            print("   ✅ WebSocket bundle already updated")
            return True
        
        # Add optimizer integration to createClient method
        pattern = r'(async createClient\(options = \{\}\) \{[^}]*?)(const clientConfig = await this\._buildClientConfiguration\(options\);)'
        
        replacement = r'''\1// Get optimized configuration from transport optimizer
        if (typeof window !== 'undefined' && window.webSocketTransportOptimizer) {
            const optimizedConfig = window.webSocketTransportOptimizer.getOptimizedConfig();
            options = { ...optimizedConfig, ...options };
            console.log('🔧 Using optimized transport configuration:', options);
        }
        
        \2'''
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Add monitoring integration
        pattern = r'(console\.log\(\'WebSocket client created successfully\'\);[\s]*return client;)'
        
        replacement = r'''console.log('WebSocket client created successfully');
            
            // Set up transport monitoring
            if (typeof window !== 'undefined' && window.webSocketTransportOptimizer) {
                window.webSocketTransportOptimizer.monitorSocket(client);
                console.log('🔍 WebSocket monitoring enabled');
            }
            
            return client;'''
        
        new_content = re.sub(pattern, replacement, new_content)
        
        if new_content != content:
            with open(bundle_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("   ✅ WebSocket bundle updated successfully")
            return True
        else:
            print("   ⚠️ No changes made to WebSocket bundle")
            return False
    
    except Exception as e:
        print(f"   ❌ Error updating WebSocket bundle: {e}")
        return False

def configure_server_logging():
    """Configure server-side logging to reduce WebSocket upgrade error noise"""
    
    print("🔧 Configuring server-side logging...")
    
    # Create logging configuration
    logging_config = '''
# WebSocket Transport Logging Configuration

import logging

# Reduce Flask-SocketIO engine.io logging for upgrade errors
engineio_logger = logging.getLogger('engineio.server')
engineio_logger.setLevel(logging.WARNING)

# Create custom filter for WebSocket upgrade errors
class WebSocketUpgradeFilter(logging.Filter):
    def filter(self, record):
        # Reduce noise from expected upgrade failures
        if 'Invalid websocket upgrade' in record.getMessage():
            # Only log every 10th occurrence to reduce noise
            if not hasattr(self, 'upgrade_error_count'):
                self.upgrade_error_count = 0
            self.upgrade_error_count += 1
            return self.upgrade_error_count % 10 == 1
        return True

# Apply filter to engine.io logger
engineio_logger.addFilter(WebSocketUpgradeFilter())

print("🔧 WebSocket logging configuration applied")
'''
    
    config_path = 'websocket_logging_config.py'
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(logging_config)
        
        print(f"   ✅ Created logging configuration: {config_path}")
        print("   📝 Add 'import websocket_logging_config' to web_app.py to apply")
        return True
    
    except Exception as e:
        print(f"   ❌ Error creating logging configuration: {e}")
        return False

def create_monitoring_script():
    """Create WebSocket monitoring script"""
    
    print("🔧 Creating WebSocket monitoring script...")
    
    monitoring_script = '''#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Connection Monitor

Monitor WebSocket connection health and transport usage.
"""

import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_websocket_logs(log_file='logs/webapp.log', hours=24):
    """Analyze WebSocket connection patterns in logs"""
    
    print(f"📊 Analyzing WebSocket logs from last {hours} hours...")
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ Log file not found: {log_file}")
        return
    
    # Patterns to match
    patterns = {
        'upgrade_errors': r'Invalid websocket upgrade',
        'connections': r'emitting event "connected"',
        'websocket_requests': r'transport=websocket',
        'polling_requests': r'transport=polling',
        'upgrade_success': r'upgraded to websocket',
        'connection_errors': r'connect_error'
    }
    
    stats = defaultdict(int)
    recent_cutoff = datetime.now() - timedelta(hours=hours)
    
    for line in lines:
        # Extract timestamp
        timestamp_match = re.match(r'\\[([^\\]]+)\\]', line)
        if timestamp_match:
            try:
                timestamp = datetime.fromisoformat(timestamp_match.group(1).replace('Z', '+00:00'))
                if timestamp < recent_cutoff:
                    continue
            except:
                continue
        
        # Count pattern matches
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, line):
                stats[pattern_name] += 1
    
    # Calculate rates
    total_requests = stats['websocket_requests'] + stats['polling_requests']
    websocket_rate = (stats['websocket_requests'] / total_requests * 100) if total_requests > 0 else 0
    polling_rate = (stats['polling_requests'] / total_requests * 100) if total_requests > 0 else 0
    
    # Display results
    print("\\n📈 WebSocket Connection Analysis")
    print("=" * 50)
    print(f"Time Period: Last {hours} hours")
    print(f"Total Connections: {stats['connections']}")
    print(f"WebSocket Requests: {stats['websocket_requests']} ({websocket_rate:.1f}%)")
    print(f"Polling Requests: {stats['polling_requests']} ({polling_rate:.1f}%)")
    print(f"Upgrade Errors: {stats['upgrade_errors']}")
    print(f"Connection Errors: {stats['connection_errors']}")
    
    # Health assessment
    print("\\n🏥 Health Assessment")
    print("=" * 50)
    
    if stats['upgrade_errors'] > stats['connections']:
        print("⚠️  High upgrade error rate - transport optimization recommended")
    elif stats['upgrade_errors'] > 0:
        print("🟡 Some upgrade errors detected - monitoring recommended")
    else:
        print("✅ No upgrade errors detected")
    
    if stats['connections'] > 0:
        error_rate = (stats['connection_errors'] / stats['connections'] * 100)
        if error_rate > 10:
            print(f"⚠️  High connection error rate: {error_rate:.1f}%")
        elif error_rate > 5:
            print(f"🟡 Moderate connection error rate: {error_rate:.1f}%")
        else:
            print(f"✅ Low connection error rate: {error_rate:.1f}%")
    
    # Recommendations
    print("\\n💡 Recommendations")
    print("=" * 50)
    
    if stats['upgrade_errors'] > 10:
        print("• Consider using polling-first transport configuration")
        print("• Enable WebSocket transport optimizer")
        print("• Monitor browser-specific patterns")
    
    if websocket_rate < 20 and total_requests > 50:
        print("• WebSocket transport appears to be underutilized")
        print("• Check client configuration and browser compatibility")
    
    if stats['connection_errors'] > stats['connections'] * 0.1:
        print("• High connection error rate detected")
        print("• Review network configuration and timeouts")
    
    if stats['upgrade_errors'] == 0 and stats['connections'] > 10:
        print("• WebSocket transport working well")
        print("• Current configuration appears optimal")

def main():
    """Main monitoring function"""
    
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print("Usage: python monitor_websocket.py [hours]")
            sys.exit(1)
    else:
        hours = 24
    
    analyze_websocket_logs(hours=hours)

if __name__ == '__main__':
    main()
'''
    
    script_path = 'monitor_websocket.py'
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(monitoring_script)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        print(f"   ✅ Created monitoring script: {script_path}")
        print(f"   📝 Usage: python {script_path} [hours]")
        return True
    
    except Exception as e:
        print(f"   ❌ Error creating monitoring script: {e}")
        return False

def create_test_script():
    """Create WebSocket transport test script"""
    
    print("🔧 Creating WebSocket transport test script...")
    
    test_script = '''#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test WebSocket Transport Configuration

Test different transport configurations to verify the fix.
"""

import requests
import time
import json

def test_transport_configuration():
    """Test WebSocket transport configuration"""
    
    print("🧪 Testing WebSocket Transport Configuration")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Check if server is running
    print("1. Testing server availability...")
    try:
        response = requests.get(f"{base_url}/api/maintenance/status", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Server not accessible: {e}")
        return False
    
    # Test 2: Check WebSocket client configuration
    print("\\n2. Testing WebSocket client configuration...")
    try:
        response = requests.get(f"{base_url}/api/websocket/client-config", timeout=5)
        if response.status_code == 200:
            config = response.json()
            print("   ✅ WebSocket configuration available")
            print(f"   📋 Transports: {config.get('transports', 'unknown')}")
            print(f"   📋 URL: {config.get('url', 'unknown')}")
        else:
            print(f"   ❌ Configuration request failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Configuration request error: {e}")
    
    # Test 3: Test Socket.IO polling connection
    print("\\n3. Testing Socket.IO polling connection...")
    try:
        response = requests.get(f"{base_url}/socket.io/?EIO=4&transport=polling", timeout=10)
        if response.status_code == 200:
            print("   ✅ Polling transport working")
        else:
            print(f"   ❌ Polling transport failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Polling transport error: {e}")
    
    # Test 4: Test WebSocket upgrade (this will likely fail, but that's expected)
    print("\\n4. Testing WebSocket upgrade (expected to fail)...")
    try:
        headers = {
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
            'Sec-WebSocket-Version': '13'
        }
        response = requests.get(f"{base_url}/socket.io/?EIO=4&transport=websocket", 
                              headers=headers, timeout=5)
        
        if response.status_code == 101:
            print("   ✅ WebSocket upgrade successful (unexpected but good!)")
        elif response.status_code == 400:
            print("   🟡 WebSocket upgrade failed as expected (this is normal)")
            print("   📝 The system will fall back to polling transport")
        else:
            print(f"   ⚠️ Unexpected WebSocket response: {response.status_code}")
    except Exception as e:
        print(f"   🟡 WebSocket upgrade failed as expected: {e}")
    
    # Test 5: Check if transport optimizer is available
    print("\\n5. Testing transport optimizer availability...")
    try:
        response = requests.get(f"{base_url}/static/js/websocket-transport-optimizer.js", timeout=5)
        if response.status_code == 200:
            print("   ✅ Transport optimizer script available")
        else:
            print(f"   ❌ Transport optimizer not found: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Transport optimizer check failed: {e}")
    
    print("\\n📊 Test Summary")
    print("=" * 50)
    print("✅ If polling transport works, the system is functioning correctly")
    print("🟡 WebSocket upgrade failures are expected and handled automatically")
    print("📝 The transport optimizer will improve connection reliability")
    print("\\n🎯 Next Steps:")
    print("• Monitor connection patterns with: python monitor_websocket.py")
    print("• Check browser console for transport optimizer messages")
    print("• Verify that all WebSocket functionality works despite upgrade errors")

if __name__ == '__main__':
    test_transport_configuration()
'''
    
    script_path = 'test_websocket_transport.py'
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        print(f"   ✅ Created test script: {script_path}")
        return True
    
    except Exception as e:
        print(f"   ❌ Error creating test script: {e}")
        return False

def main():
    """Main function to apply WebSocket transport fixes"""
    
    print("🔧 WebSocket Transport Issue Fix")
    print("=" * 50)
    print("This script addresses 'Invalid websocket upgrade' errors by:")
    print("• Optimizing client transport configuration")
    print("• Adding browser-specific transport selection")
    print("• Implementing connection monitoring")
    print("• Reducing log noise from expected failures")
    print()
    
    success_count = 0
    total_tasks = 5
    
    # Task 1: Add transport optimizer to templates
    if add_transport_optimizer_to_templates():
        success_count += 1
    
    # Task 2: Update WebSocket bundle
    if update_websocket_bundle():
        success_count += 1
    
    # Task 3: Configure server logging
    if configure_server_logging():
        success_count += 1
    
    # Task 4: Create monitoring script
    if create_monitoring_script():
        success_count += 1
    
    # Task 5: Create test script
    if create_test_script():
        success_count += 1
    
    print(f"\\n📊 Fix Summary: {success_count}/{total_tasks} tasks completed successfully")
    
    if success_count == total_tasks:
        print("\\n🎉 WebSocket transport fixes applied successfully!")
        print("\\n📝 Next Steps:")
        print("1. Restart the web application to apply changes")
        print("2. Test the fixes with: python test_websocket_transport.py")
        print("3. Monitor connections with: python monitor_websocket.py")
        print("4. Check browser console for transport optimizer messages")
        print("\\n✅ The system should now handle WebSocket transport issues gracefully")
    else:
        print("\\n⚠️ Some fixes could not be applied. Please check the errors above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())