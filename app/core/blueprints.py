def register_blueprints(app):
    """Register all application blueprints"""
    
    # Register authentication blueprint
    from app.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # Register platform management blueprint
    from app.blueprints.platform import platform_bp
    app.register_blueprint(platform_bp)
    
    # Register existing admin blueprint
    from admin import create_admin_blueprint
    admin_bp = create_admin_blueprint(app)
    app.register_blueprint(admin_bp)
    
    # Register existing GDPR routes
    from routes.gdpr_routes import gdpr_bp
    app.register_blueprint(gdpr_bp)
    
    # Register existing WebSocket client config routes
    from routes.websocket_client_config_routes import websocket_client_config_bp
    app.register_blueprint(websocket_client_config_bp)
