#!/usr/bin/env python3
"""
Critical Route Verification

Verifies that the most critical routes referenced in templates are available.
"""

from web_app import app

def main():
    """Verify critical routes are available"""
    
    # Most critical routes that templates reference
    critical_routes = [
        # Main navigation
        'main.index',
        'main.caption_generation',
        
        # User management
        'user_management.login',
        'user_management.logout', 
        'user_management.profile',
        
        # Review system
        'review.review_list',
        'review.batch_review',
        'review.review_single',
        
        # Platform management
        'platform.management',
        
        # Caption system
        'caption.generation',
        'caption.settings',
        
        # Static routes
        'static.logout_all',
        'static.serve_image',
        
        # Admin (most used)
        'admin.dashboard',
        'admin.user_management',
        
        # GDPR
        'gdpr.privacy_policy',
        'gdpr.consent_management'
    ]
    
    with app.app_context():
        print("=== CRITICAL ROUTE VERIFICATION ===")
        
        working = []
        missing = []
        
        for route in critical_routes:
            try:
                # Test if route exists by trying to build URL
                url = app.url_for(route)
                working.append(route)
                print(f"✓ {route:35} -> {url}")
            except Exception as e:
                missing.append(route)
                print(f"✗ {route:35} -> {str(e)[:50]}")
        
        print(f"\n=== SUMMARY ===")
        print(f"✓ Working: {len(working)}/{len(critical_routes)}")
        print(f"✗ Missing: {len(missing)}/{len(critical_routes)}")
        
        if missing:
            print(f"\n=== MISSING CRITICAL ROUTES ===")
            for route in missing:
                print(f"  - {route}")
            return False
        else:
            print(f"\n🎉 All critical routes are available!")
            return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
