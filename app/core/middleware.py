def setup_middleware(app):
    """Setup application middleware"""
    
    # Add WebSocket WSGI middleware
    # WebSocket middleware now integrated into consolidated system
    pass
    app.wsgi_app = create_websocket_wsgi_middleware(app.wsgi_app)
    app.logger.debug("WebSocket WSGI middleware applied")
    
    # Set up WebSocket error filtering
    # WebSocket log filtering now integrated into consolidated error handler
    pass
    websocket_filter = setup_websocket_log_filter()
    app.websocket_filter = websocket_filter
    app.logger.info("WebSocket error filter applied")
    
    # Initialize WebSocket system
    from app.websocket.core.config_manager import ConsolidatedWebSocketConfigManager as WebSocketConfigManager
    from app.websocket.core.factory import WebSocketFactory
    from app.websocket.core.auth_handler import WebSocketAuthHandler
    from app.websocket.core.namespace_manager import WebSocketNamespaceManager
    
    # Initialize WebSocket configuration manager
    from config import Config
    config = Config()
    websocket_config_manager = WebSocketConfigManager(config)
    app.logger.debug("WebSocket configuration manager initialized")
    
    # Register secure error handlers
    from app.core.security.logging.secure_error_handlers import register_secure_error_handlers
    register_secure_error_handlers(app)
