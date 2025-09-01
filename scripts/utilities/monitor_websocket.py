#!/usr/bin/env python3
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
        timestamp_match = re.match(r'\[([^\]]+)\]', line)
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
    print("\n📈 WebSocket Connection Analysis")
    print("=" * 50)
    print(f"Time Period: Last {hours} hours")
    print(f"Total Connections: {stats['connections']}")
    print(f"WebSocket Requests: {stats['websocket_requests']} ({websocket_rate:.1f}%)")
    print(f"Polling Requests: {stats['polling_requests']} ({polling_rate:.1f}%)")
    print(f"Upgrade Errors: {stats['upgrade_errors']}")
    print(f"Connection Errors: {stats['connection_errors']}")
    
    # Health assessment
    print("\n🏥 Health Assessment")
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
    print("\n💡 Recommendations")
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
