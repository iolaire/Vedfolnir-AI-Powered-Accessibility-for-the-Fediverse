# Copyright (C) 2025 iolaire mcfadden.
# Minimal web_app.py - All routes moved to blueprints

from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError

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

# Initialize database
from database import DatabaseManager
db_manager = DatabaseManager(config)
app.config['db_manager'] = db_manager

# Initialize consolidated session manager
from session_manager import SessionManager
unified_session_manager = SessionManager(db_manager)
app.unified_session_manager = unified_session_manager

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'user_management.login'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    try:
        with unified_session_manager.get_db_session() as session:
            user = session.query(User).filter(User.id == int(user_id)).first()
            if user:
                # Create a detached copy with all needed attributes
                from models import UserRole
                user_copy = User()
                user_copy.id = user.id
                user_copy.username = user.username
                user_copy.email = user.email
                user_copy.role = user.role
                user_copy.is_active = user.is_active
                user_copy.email_verified = user.email_verified
                user_copy.account_locked = user.account_locked
                return user_copy
            return None
    except (ValueError, TypeError) as e:
        current_app.logger.error(f"Invalid user ID format {user_id}: {e}")
        return None
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error loading user {user_id}: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error loading user {user_id}: {e}")
        return None

# Initialize security (simplified)
try:
    from security.core.csrf_token_manager import csrf_token_manager
    csrf_token_manager.init_app(app)
except Exception:
    pass

# Register all blueprints
from app.core.blueprints import register_blueprints
register_blueprints(app)

# Register session state API
try:
    from session_state_api import create_session_state_routes
    create_session_state_routes(app)
except Exception as e:
    app.logger.warning(f"Session state API registration failed: {e}")

# Initialize performance dashboard (minimal)
try:
    from admin.routes.performance_dashboard import create_performance_dashboard
    
    # Create minimal mock optimizers with correct method names
    class MockOptimizer:
        def get_performance_metrics(self):
            return {
                'response_time': 50.0,
                'memory_usage_mb': 128.0,
                'cpu_usage_percent': 15.0,
                'optimization_level': 'good'
            }
        def get_recommendations(self): 
            return [{'id': 1, 'message': 'System running normally', 'priority': 'low'}]
        def get_health_status(self): 
            return {'status': 'healthy', 'components': {'database': 'healthy', 'redis': 'healthy'}}
        def get_metrics(self): 
            return self.get_performance_metrics()
    
    mock_optimizer = MockOptimizer()
    app.performance_dashboard = create_performance_dashboard(
        mock_optimizer, mock_optimizer, mock_optimizer
    )
except Exception as e:
    app.logger.warning(f"Performance dashboard initialization failed: {e}")

# Register admin blueprint
try:
    from admin import create_admin_blueprint
    admin_bp = create_admin_blueprint(app)
    app.register_blueprint(admin_bp)
    print("✅ Admin blueprint registered successfully")
except Exception as e:
    print(f"❌ Failed to register admin blueprint: {e}")
    import traceback
    traceback.print_exc()

# Register existing route blueprints
try:
    from routes.user_management_routes import user_management_bp
    app.register_blueprint(user_management_bp)
except Exception:
    pass

# Context processor for templates
@app.context_processor
def inject_role_context():
    from flask_login import current_user
    try:
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()
    except Exception:
        csrf_token = 'no-csrf'
    
    # Provide current_user_safe for templates
    current_user_safe = current_user if current_user.is_authenticated else None
    
    return {
        'current_user': current_user,
        'current_user_safe': current_user_safe,
        'csrf_token': csrf_token
    }

# Initialize SocketIO for real-time features
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(app, 
                       cors_allowed_origins="*", 
                       async_mode='threading',
                       logger=False,
                       engineio_logger=False,
                       allow_upgrades=True,
                       transports=['polling', 'websocket'])
    
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')
        
except ImportError:
    socketio = None
    print("SocketIO not available - real-time features disabled")

if __name__ == '__main__':
    if socketio:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
