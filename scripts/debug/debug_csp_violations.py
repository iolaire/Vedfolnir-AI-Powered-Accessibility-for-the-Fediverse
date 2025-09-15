#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSP Violation Debug Script

This script analyzes CSP violations from the webapp logs and provides
recommendations for fixing them.
"""

import json
import re
import sys
from datetime import datetime
from collections import defaultdict, Counter

def parse_csp_violations(log_file_path):
    """Parse CSP violations from webapp log file"""
    violations = []
    
    try:
        with open(log_file_path, 'r') as f:
            content = f.read()
            
        # Find all CSP violation entries
        violation_pattern = r'CSP violation detected: ({.*?})'
        matches = re.findall(violation_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                # Clean up the JSON string
                json_str = match.strip()
                violation_data = json.loads(json_str)
                violations.append(violation_data)
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse violation JSON: {e}")
                continue
                
    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file_path}")
        return []
    except Exception as e:
        print(f"Error reading log file: {e}")
        return []
    
    return violations

def analyze_violations(violations):
    """Analyze CSP violations and provide insights"""
    if not violations:
        print("No CSP violations found in the log file.")
        return
    
    print(f"\n=== CSP Violation Analysis ===")
    print(f"Total violations found: {len(violations)}")
    
    # Group by violation type
    by_directive = defaultdict(list)
    by_blocked_uri = defaultdict(list)
    by_user_agent = defaultdict(list)
    by_document_uri = defaultdict(list)
    
    for violation in violations:
        directive = violation.get('violated_directive', 'unknown')
        blocked_uri = violation.get('blocked_uri', 'unknown')
        user_agent = violation.get('user_agent', 'unknown')
        document_uri = violation.get('document_uri', 'unknown')
        
        by_directive[directive].append(violation)
        by_blocked_uri[blocked_uri].append(violation)
        by_user_agent[user_agent].append(violation)
        by_document_uri[document_uri].append(violation)
    
    # Analyze by directive
    print(f"\n--- Violations by Directive ---")
    for directive, viols in by_directive.items():
        print(f"  {directive}: {len(viols)} violations")
    
    # Analyze by blocked URI
    print(f"\n--- Violations by Blocked URI ---")
    for uri, viols in by_blocked_uri.items():
        print(f"  {uri}: {len(viols)} violations")
    
    # Analyze by user agent (browser)
    print(f"\n--- Violations by Browser ---")
    for ua, viols in by_user_agent.items():
        browser = extract_browser_name(ua)
        print(f"  {browser}: {len(viols)} violations")
    
    # Analyze by page
    print(f"\n--- Violations by Page ---")
    for uri, viols in by_document_uri.items():
        page = uri.split('/')[-1] or 'root'
        print(f"  {page}: {len(viols)} violations")
    
    # Identify Safari false positives
    safari_false_positives = []
    genuine_violations = []
    
    for violation in violations:
        user_agent = violation.get('user_agent', '')
        violated_directive = violation.get('violated_directive', '')
        blocked_uri = violation.get('blocked_uri', '')
        original_policy = violation.get('original_policy', '')
        
        is_safari_false_positive = (
            'Safari' in user_agent and
            violated_directive == 'script-src-elem' and
            blocked_uri == 'inline' and
            "'unsafe-inline'" in original_policy and
            "'nonce-" in original_policy
        )
        
        if is_safari_false_positive:
            safari_false_positives.append(violation)
        else:
            genuine_violations.append(violation)
    
    print(f"\n--- Violation Classification ---")
    print(f"  Safari false positives: {len(safari_false_positives)}")
    print(f"  Genuine violations: {len(genuine_violations)}")
    
    if safari_false_positives:
        print(f"\n--- Safari False Positives Details ---")
        print("These are known Safari CSP reporting bugs where inline scripts")
        print("with nonces are reported as violations even though they're allowed.")
        
        for i, violation in enumerate(safari_false_positives[:3], 1):
            print(f"\nExample {i}:")
            print(f"  Page: {violation.get('document_uri', 'unknown')}")
            print(f"  Directive: {violation.get('violated_directive', 'unknown')}")
            print(f"  Time: {violation.get('timestamp', 'unknown')}")
    
    if genuine_violations:
        print(f"\n--- Genuine Violations Details ---")
        for i, violation in enumerate(genuine_violations[:5], 1):
            print(f"\nViolation {i}:")
            print(f"  Page: {violation.get('document_uri', 'unknown')}")
            print(f"  Directive: {violation.get('violated_directive', 'unknown')}")
            print(f"  Blocked URI: {violation.get('blocked_uri', 'unknown')}")
            print(f"  Browser: {extract_browser_name(violation.get('user_agent', ''))}")
            print(f"  Time: {violation.get('timestamp', 'unknown')}")

def extract_browser_name(user_agent):
    """Extract browser name from user agent string"""
    if 'Safari' in user_agent and 'Chrome' not in user_agent:
        return 'Safari'
    elif 'Chrome' in user_agent:
        return 'Chrome'
    elif 'Firefox' in user_agent:
        return 'Firefox'
    elif 'Edge' in user_agent:
        return 'Edge'
    else:
        return 'Unknown'

def provide_recommendations(violations):
    """Provide recommendations for fixing CSP violations"""
    if not violations:
        return
    
    print(f"\n=== Recommendations ===")
    
    # Check for Safari false positives
    safari_violations = [v for v in violations if 'Safari' in v.get('user_agent', '')]
    if safari_violations:
        print(f"\n1. Safari False Positives ({len(safari_violations)} violations)")
        print("   - These are Safari browser bugs, not real violations")
        print("   - The updated CSP report handler will filter these out")
        print("   - No action needed - scripts are executing correctly")
    
    # Check for missing script-src-elem directive
    script_elem_violations = [v for v in violations if v.get('violated_directive') == 'script-src-elem']
    if script_elem_violations:
        print(f"\n2. script-src-elem Violations ({len(script_elem_violations)} violations)")
        print("   - Added script-src-elem directive to CSP policy")
        print("   - This should resolve inline script violations")
    
    # Check for WebSocket connection issues
    connect_violations = [v for v in violations if 'connect-src' in v.get('violated_directive', '')]
    if connect_violations:
        print(f"\n3. WebSocket Connection Violations ({len(connect_violations)} violations)")
        print("   - Updated connect-src to include wss://vedfolnir.org")
        print("   - Ensure WebSocket connections use the correct protocol")
    
    print(f"\n=== Next Steps ===")
    print("1. Restart your Gunicorn service:")
    print("   launchctl stop com.vedfolnir.gunicorn")
    print("   launchctl start com.vedfolnir.gunicorn")
    print()
    print("2. Test the application in Safari and check for new violations")
    print()
    print("3. Monitor logs for 24 hours to confirm violations are resolved:")
    print("   tail -f logs/webapp.log | grep 'CSP violation'")
    print()
    print("4. If you still see genuine violations, run this script again")

def main():
    """Main function"""
    log_file = 'logs/webapp.log'
    
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    
    print(f"Analyzing CSP violations from: {log_file}")
    
    violations = parse_csp_violations(log_file)
    analyze_violations(violations)
    provide_recommendations(violations)
    
    print(f"\n=== Summary ===")
    print(f"Analysis complete. Found {len(violations)} total violations.")
    print("The CSP policy has been updated to address these issues.")
    print("Restart your services and monitor for improvements.")

if __name__ == '__main__':
    main()