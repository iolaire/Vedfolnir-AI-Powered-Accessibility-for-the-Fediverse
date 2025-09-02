#!/usr/bin/env python3
"""
Route Verification Script

Verifies that all expected routes are properly registered after blueprint refactoring.
"""

from web_app import app

def main():
    """Verify all routes are properly registered"""
    
    with app.app_context():
        print("✓ Registered Blueprints:")
        for bp_name, bp in app.blueprints.items():
            print(f"  - {bp_name}: {bp.url_prefix or '/'}")
        
        print("\n✓ Available Routes:")
        routes = []
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith('/static'):
                routes.append((rule.rule, rule.endpoint, sorted(rule.methods)))
        
        # Sort routes for better readability
        routes.sort()
        
        for route, endpoint, methods in routes:
            methods_str = ', '.join(m for m in methods if m not in ['HEAD', 'OPTIONS'])
            print(f"  {methods_str:12} {route:30} -> {endpoint}")
        
        # Check for specific routes that templates expect
        expected_routes = [
            'main.index',
            'main.caption_generation', 
            'review.review_list',
            'review.batch_review',
            'platform.management',
            'caption.generation',
            'user_management.login',
            'auth.first_time_setup'
        ]
        
        print(f"\n✓ Checking Expected Routes:")
        missing_routes = []
        for route in expected_routes:
            try:
                url = app.url_for(route)
                print(f"  ✓ {route:25} -> {url}")
            except Exception as e:
                print(f"  ✗ {route:25} -> ERROR: {e}")
                missing_routes.append(route)
        
        if missing_routes:
            print(f"\n⚠️  Missing Routes: {len(missing_routes)}")
            for route in missing_routes:
                print(f"  - {route}")
        else:
            print(f"\n✅ All expected routes are available!")

if __name__ == '__main__':
    main()
