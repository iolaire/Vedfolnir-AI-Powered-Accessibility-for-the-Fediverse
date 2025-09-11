from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect

# Global extension instances
login_manager = LoginManager()
socketio = SocketIO()
csrf = CSRFProtect()

def init_extensions(app):
    """Initialize Flask extensions"""
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.user_management.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Set up user loader
    from models import User
    from unified_session_manager import unified_session_manager
    
    @login_manager.user_loader
    def load_user(user_id):
        with unified_session_manager.get_db_session() as session:
            return session.query(User).get(int(user_id))
