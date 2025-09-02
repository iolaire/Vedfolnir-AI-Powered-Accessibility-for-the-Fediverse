#!/usr/bin/env python3
"""
Template Route Checker

Checks all url_for references in templates to identify missing routes.
"""

import re
from pathlib import Path
from web_app import app

def extract_url_for_calls(file_path):
    """Extract all url_for calls from a template file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all url_for calls
        pattern = r"url_for\(['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)
        return matches
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def main():
    """Check all template routes"""
    
    # Find all template files
    template_dirs = ['templates', 'admin/templates']
    all_routes = set()
    
    for template_dir in template_dirs:
        template_path = Path(template_dir)
        if template_path.exists():
            for html_file in template_path.rglob('*.html'):
                routes = extract_url_for_calls(html_file)
                for route in routes:
                    all_routes.add(route)
    
    print(f"Found {len(all_routes)} unique route references in templates")
    
    # Test routes with Flask app
    with app.app_context():
        missing_routes = []
        working_routes = []
        
        for route in sorted(all_routes):
            try:
                url = app.url_for(route)
                working_routes.append(route)
                print(f"✓ {route:40} -> {url}")
            except Exception as e:
                missing_routes.append(route)
                print(f"✗ {route:40} -> ERROR: {str(e)[:50]}")
        
        print(f"\n=== SUMMARY ===")
        print(f"✓ Working routes: {len(working_routes)}")
        print(f"✗ Missing routes: {len(missing_routes)}")
        
        if missing_routes:
            print(f"\n=== MISSING ROUTES ===")
            for route in missing_routes:
                print(f"  - {route}")
        
        return len(missing_routes) == 0

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
