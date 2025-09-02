from flask import Flask
from config import Config

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    config = Config()
    app.config['SECRET_KEY'] = config.webapp.secret_key
    
    # Initialize extensions
    from .extensions import init_extensions
    init_extensions(app)
    
    # Register blueprints
    from .blueprints import register_blueprints
    register_blueprints(app)
    
    # Setup middleware
    from .middleware import setup_middleware
    setup_middleware(app)
    
    return app
