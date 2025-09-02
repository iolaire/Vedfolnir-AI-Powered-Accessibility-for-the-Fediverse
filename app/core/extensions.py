from flask_login import LoginManager
from flask_socketio import SocketIO

# Global extension instances
login_manager = LoginManager()
socketio = SocketIO()

def init_extensions(app):
    """Initialize Flask extensions"""
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'user_management.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Set up user loader
    from models import User
    from unified_session_manager import unified_session_manager
    
    @login_manager.user_loader
    def load_user(user_id):
        with unified_session_manager.get_db_session() as session:
            return session.query(User).get(int(user_id))
