# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Import application factory
from app.core.app_factory import create_app

# Create the Flask application
app = create_app()

# Import remaining routes that haven't been moved to blueprints yet
# These will be gradually moved to appropriate blueprints

from flask import render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.core.security.core.role_based_access import require_viewer_or_higher
from session_aware_decorators import with_session_error_handling
from models import UserRole

# Temporary routes - to be moved to appropriate blueprints
@app.route('/')
@login_required
@require_viewer_or_higher
@with_session_error_handling
def index():
    """Main dashboard - temporary route"""
    # This will be moved to a dashboard blueprint
    return render_template('index.html')

# Static file serving routes
@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve stored images"""
    from flask import send_from_directory
    from config import Config
    config = Config()
    return send_from_directory(config.storage.images_dir, filename)

@app.route('/static/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files with correct MIME type"""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static/js', filename))
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/favicon.ico')
@with_session_error_handling
def favicon():
    """Serve favicon"""
    from flask import send_from_directory
    return send_from_directory('static/favicons', 'favicon.ico')

# Health check and system status
def get_simple_system_health_for_index(db_session):
    """Get a simple system health status for the index route"""
    try:
        # Check database connectivity
        try:
            from sqlalchemy import text
            db_session.execute(text("SELECT 1"))
            db_healthy = True
        except Exception:
            db_healthy = False
        
        # Check if Ollama is accessible
        ollama_healthy = True
        try:
            import httpx
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{ollama_url}/api/tags")
                ollama_healthy = response.status_code == 200
        except Exception:
            ollama_healthy = False
        
        # Check storage
        storage_healthy = True
        try:
            storage_dirs = ['storage', 'storage/database', 'storage/images']
            for dir_path in storage_dirs:
                if not os.path.exists(dir_path):
                    storage_healthy = False
                    break
        except Exception:
            storage_healthy = False
        
        # Determine overall health
        if db_healthy and ollama_healthy and storage_healthy:
            return 'healthy'
        elif db_healthy:
            return 'warning'
        else:
            return 'critical'
            
    except Exception as e:
        app.logger.error(f"Error checking system health: {e}")
        return 'warning'

if __name__ == '__main__':
    try:
        from app.core.extensions import socketio
        from config import Config
        config = Config()
        
        # Set up logging
        import logging
        from app.utils.logging.logger import setup_logging
        
        os.makedirs(config.storage.logs_dir, exist_ok=True)
        setup_logging(
            log_level=config.log_level,
            log_file=os.path.join(config.storage.logs_dir, 'webapp.log'),
            use_json=False,
            include_traceback=True
        )
        
        # Start the application
        socketio.run(
            app,
            host=config.webapp.host,
            port=config.webapp.port,
            debug=config.webapp.debug,
            use_reloader=False,
            log_output=True,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        app.logger.info("Application shutdown requested")
    except Exception as e:
        from app.core.security.core.security_utils import sanitize_for_log
        app.logger.error(f"Application startup failed: {sanitize_for_log(str(e))}")
        raise
    finally:
        # Clean up resources
        try:
            if hasattr(app, 'websocket_progress_handler'):
                app.websocket_progress_handler.cleanup()
        except Exception as cleanup_error:
            from app.core.security.core.security_utils import sanitize_for_log
            app.logger.warning(f"Error during cleanup: {sanitize_for_log(str(cleanup_error))}")
