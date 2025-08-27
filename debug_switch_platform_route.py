#!/usr/bin/env python3
"""
Debug the switch platform route by adding logging to each step
"""

import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def patch_switch_platform_route():
    """Add debugging to the switch platform route"""
    
    # Import the web app
    import web_app
    from flask import request, jsonify, current_app, g
    from flask_login import current_user
    from functools import wraps
    
    # Get the original route function
    original_func = web_app.api_switch_platform
    
    @wraps(original_func)
    def debug_api_switch_platform(platform_id):
        """Debug version of api_switch_platform"""
        
        print(f"\n{'='*60}")
        print(f"DEBUG: api_switch_platform called with platform_id={platform_id}")
        print(f"Request method: {request.method}")
        print(f"Request path: {request.path}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request content type: {request.content_type}")
        print(f"Request data: {request.get_data()}")
        print(f"Request form: {dict(request.form)}")
        print(f"Request json: {request.get_json(silent=True)}")
        print(f"Request args: {dict(request.args)}")
        
        # Check authentication
        try:
            print(f"Current user authenticated: {current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else 'No current_user'}")
            if hasattr(current_user, 'id'):
                print(f"Current user ID: {current_user.id}")
                print(f"Current user username: {getattr(current_user, 'username', 'N/A')}")
                print(f"Current user role: {getattr(current_user, 'role', 'N/A')}")
        except Exception as e:
            print(f"Error checking current_user: {e}")
        
        # Check session context
        try:
            session_context = getattr(g, 'session_context', None)
            print(f"Session context: {session_context}")
            session_id = getattr(g, 'session_id', None)
            print(f"Session ID: {session_id}")
        except Exception as e:
            print(f"Error checking session context: {e}")
        
        print(f"{'='*60}\n")
        
        # Call the original function
        try:
            result = original_func(platform_id)
            print(f"DEBUG: Route completed successfully")
            return result
        except Exception as e:
            print(f"DEBUG: Route failed with exception: {e}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    # Replace the route function
    web_app.api_switch_platform = debug_api_switch_platform
    
    # Also patch the route registration
    for rule in web_app.app.url_map.iter_rules():
        if rule.endpoint == 'api_switch_platform':
            print(f"Found route: {rule.rule} -> {rule.endpoint}")
            # The route is already registered, we just patched the function
            break
    
    print("DEBUG: Patched api_switch_platform route with debugging")

if __name__ == "__main__":
    print("Patching switch platform route with debugging...")
    patch_switch_platform_route()
    
    # Start the web app with debugging
    import web_app
    print("Starting web app with debugging enabled...")
    web_app.app.run(debug=True, port=5000)  # Use different port to avoid conflicts
