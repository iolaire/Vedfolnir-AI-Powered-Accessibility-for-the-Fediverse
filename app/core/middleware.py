def setup_middleware(app):
    """Setup application middleware"""
    
    # Add WebSocket WSGI middleware
    from websocket_wsgi_middleware import create_websocket_wsgi_middleware
    app.wsgi_app = create_websocket_wsgi_middleware(app.wsgi_app)
    app.logger.debug("WebSocket WSGI middleware applied")
    
    # Set up WebSocket error filtering
    from websocket_log_filter import setup_websocket_log_filter
    websocket_filter = setup_websocket_log_filter()
    app.websocket_filter = websocket_filter
    app.logger.info("WebSocket error filter applied")
    
    # Initialize WebSocket system
    from websocket_config_manager import WebSocketConfigManager
    from websocket_cors_manager import CORSManager
    from websocket_factory import WebSocketFactory
    from websocket_auth_handler import WebSocketAuthHandler
    from websocket_namespace_manager import WebSocketNamespaceManager
    
    # Initialize WebSocket configuration manager
    from config import Config
    config = Config()
    websocket_config_manager = WebSocketConfigManager(config)
    app.logger.debug("WebSocket configuration manager initialized")
    
    # Register secure error handlers
    from security.logging.secure_error_handlers import register_secure_error_handlers
    register_secure_error_handlers(app)
