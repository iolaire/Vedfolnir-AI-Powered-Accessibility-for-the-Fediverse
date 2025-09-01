#!/usr/bin/env python3
"""
Wrapper script to run web_app_simple.py with better error handling
"""

import sys
import traceback
import signal
import time

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n\n🛑 Shutting down web application...')
    sys.exit(0)

def main():
    """Main function to run the web app with error handling"""
    print("🚀 Starting Simplified Web Application")
    print("=" * 50)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Import and run the web app
        print("📦 Importing web_app_simple...")
        import web_app_simple
        
        print("✅ Import successful!")
        print(f"   App: {web_app_simple.app}")
        print(f"   Config loaded: {web_app_simple.config}")
        print(f"   Redis client: {web_app_simple.redis_client}")
        print(f"   Database manager: {web_app_simple.db_manager}")
        
        print("\n🌐 Starting Flask development server...")
        print("   URL: http://127.0.0.1:5000")
        print("   Press Ctrl+C to stop")
        print("-" * 50)
        
        # Run the Flask app
        web_app_simple.app.run(
            host=web_app_simple.config.webapp.host,
            port=web_app_simple.config.webapp.port,
            debug=web_app_simple.config.webapp.debug,
            use_reloader=False  # Disable reloader to avoid issues
        )
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nThis usually means a required module is missing.")
        print("Check that all dependencies are installed:")
        print("   pip install -r requirements.txt")
        traceback.print_exc()
        return False
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port Error: {e}")
            print("\nPort 5000 is already in use.")
            print("Either:")
            print("   1. Stop the other process using port 5000")
            print("   2. Change FLASK_PORT in your .env file")
            print("   3. Kill existing process: lsof -ti:5000 | xargs kill")
        else:
            print(f"❌ OS Error: {e}")
            traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
