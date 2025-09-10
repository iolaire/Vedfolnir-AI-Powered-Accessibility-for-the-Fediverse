# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask, request, make_response
from flask_login import LoginManager
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')

# Initialize CORS
CORS(app, origins=["http://localhost:5000"], supports_credentials=True)

# Database configuration
from config import Config
config = Config()
app.config['SQLALCHEMY_DATABASE_URI'] = config.storage.database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Redis Session Management
from flask_redis_session_interface import FlaskRedisSessionInterface
from redis_session_backend import RedisSessionBackend

try:
    redis_backend = RedisSessionBackend()
    app.session_interface = FlaskRedisSessionInterface(redis_backend)
    app.redis_backend = redis_backend
except Exception as e:
    app.logger.warning(f"Redis session backend failed to initialize: {e}")
    app.redis_backend = None

# Initialize database
from app.core.database.core.database_manager import DatabaseManager
db_manager = DatabaseManager(config)
app.config['db_manager'] = db_manager

# Initialize session manager
from session_factory import create_session_manager
from session_security_manager import SessionSecurityManager

session_security_manager = SessionSecurityManager()

if hasattr(app, 'redis_backend') and app.redis_backend:
    from session_manager_v2 import SessionManagerV2
    unified_session_manager = SessionManagerV2(
        db_manager=db_manager,
        redis_backend=app.redis_backend,
        security_manager=session_security_manager
    )
else:
    unified_session_manager = create_session_manager(
        db_manager=db_manager, 
        security_manager=session_security_manager,
        redis_client=None
    )

app.unified_session_manager = unified_session_manager
app.session_manager = unified_session_manager

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'user_management.login'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    with unified_session_manager.get_db_session() as session:
        return session.query(User).get(int(user_id))

# Initialize security systems
from app.core.security.core.csrf_token_manager import csrf_token_manager
csrf_token_manager.init_app(app)

from app.core.security.core.security_monitoring import security_monitor
security_monitor.init_app(app)

from app.core.security.core.csrf_error_handler import register_csrf_error_handlers
register_csrf_error_handlers(app)

from app.core.security.core.csrf_middleware import CSRFMiddleware
csrf_middleware = CSRFMiddleware(app)

# Register all blueprints
from app.core.blueprints import register_blueprints
register_blueprints(app)

# Register admin blueprint
from admin import create_admin_blueprint
admin_bp = create_admin_blueprint(app)
app.register_blueprint(admin_bp)

# Register existing route blueprints
from routes.gdpr_routes import gdpr_bp
app.register_blueprint(gdpr_bp)

from routes.websocket_client_config_routes import websocket_client_config_bp
app.register_blueprint(websocket_client_config_bp)

from routes.user_management_routes import user_management_bp
app.register_blueprint(user_management_bp)

# Initialize WebSocket system
from app.websocket.core.factory import WebSocketFactory
websocket_factory = WebSocketFactory()
socketio = websocket_factory.create_socketio(app)

# Context processor for templates
@app.context_processor
def inject_role_context():
    from flask_login import current_user
    from flask_wtf.csrf import generate_csrf
    
    csrf_token = generate_csrf()
    
    context = {
        'current_user': current_user,
        'csrf_token': csrf_token
    }
    
    return context

# CORS handler
@app.after_request
def after_request(response):
    if request.path.startswith('/api/') or request.path.startswith('/socket.io/'):
        origin = request.headers.get('Origin')
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
    
    return response

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
