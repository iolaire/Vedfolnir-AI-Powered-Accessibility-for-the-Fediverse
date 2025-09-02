#!/usr/bin/env python3
"""
Template Route Verification Script
Checks all HTML templates for route references and verifies they exist in Flask blueprints
"""

import os
import re
import sys
from pathlib import Path

def find_route_references(file_path):
    """Extract route references from HTML template"""
    routes = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find url_for references
        url_for_pattern = r"url_for\(['\"]([^'\"]+)['\"]"
        matches = re.findall(url_for_pattern, content)
        routes.update(matches)
        
        # Find href="/route" references
        href_pattern = r'href=["\']([^"\']+)["\']'
        href_matches = re.findall(href_pattern, content)
        for href in href_matches:
            if href.startswith('/') and not href.startswith('//') and not href.startswith('/#'):
                routes.add(href.lstrip('/'))
        
        # Find action="/route" references
        action_pattern = r'action=["\']([^"\']+)["\']'
        action_matches = re.findall(action_pattern, content)
        for action in action_matches:
            if action.startswith('/') and not action.startswith('//'):
                routes.add(action.lstrip('/'))
                
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        
    return routes

def get_flask_routes():
    """Get available Flask routes from the application"""
    routes = set()
    
    # Check main app routes
    try:
        sys.path.insert(0, '.')
        from web_app import app
        
        with app.app_context():
            for rule in app.url_map.iter_rules():
                endpoint = rule.endpoint
                if endpoint and not endpoint.startswith('static'):
                    routes.add(endpoint)
                    
                # Also add the URL pattern without parameters
                url_pattern = str(rule.rule)
                if url_pattern.startswith('/'):
                    clean_pattern = re.sub(r'<[^>]+>', '', url_pattern).strip('/')
                    if clean_pattern:
                        routes.add(clean_pattern)
                        
    except Exception as e:
        print(f"Error getting Flask routes: {e}")
        
    return routes

def main():
    """Main verification function"""
    print("🔍 Template Route Verification")
    print("=" * 50)
    
    # Find all template files
    template_dirs = ['./templates', './admin/templates']
    template_files = []
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        template_files.append(os.path.join(root, file))
    
    print(f"Found {len(template_files)} template files")
    
    # Get Flask routes
    flask_routes = get_flask_routes()
    print(f"Found {len(flask_routes)} Flask routes")
    
    # Check each template
    all_template_routes = set()
    missing_routes = set()
    template_route_map = {}
    
    for template_file in template_files:
        routes = find_route_references(template_file)
        all_template_routes.update(routes)
        
        if routes:
            template_route_map[template_file] = routes
            
        # Check for missing routes
        for route in routes:
            # Check exact match
            if route in flask_routes:
                continue
            
            # Check if route starts with any flask route (for URL patterns)
            if any(route.startswith(fr) for fr in flask_routes):
                continue
                
            # Check if any flask route ends with this route (for blueprint routes)
            if any(fr.endswith('.' + route) for fr in flask_routes):
                continue
                
            # Route is missing
            missing_routes.add(route)
    
    print(f"\n📊 Summary:")
    print(f"Total unique routes in templates: {len(all_template_routes)}")
    print(f"Missing routes: {len(missing_routes)}")
    
    if missing_routes:
        print(f"\n❌ Missing Routes:")
        for route in sorted(missing_routes):
            print(f"  - {route}")
            
        print(f"\n📍 Templates using missing routes:")
        for template_file, routes in template_route_map.items():
            missing_in_template = routes.intersection(missing_routes)
            if missing_in_template:
                print(f"  {template_file}:")
                for route in sorted(missing_in_template):
                    print(f"    - {route}")
    else:
        print("\n✅ All template routes are available!")
    
    print(f"\n🔧 Available Flask Routes:")
    for route in sorted(flask_routes):
        print(f"  - {route}")

if __name__ == "__main__":
    main()
