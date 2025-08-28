# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Factory Demonstration

This script demonstrates how to use the WebSocket Factory to create and configure
SocketIO instances with standardized settings, replacing hardcoded configurations.
"""

import os
import logging
from flask import Flask
from config import Config
from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app_with_websocket_factory():
    """
    Demonstrate creating a Flask app with WebSocket factory
    
    Returns:
        Tuple of (app, socketio) instances
    """
    logger.info("=== WebSocket Factory Demonstration ===")
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'demo-secret-key'
    app.config['TESTING'] = True
    
    # Create configuration
    config = Config()
    
    # Create WebSocket configuration manager
    logger.info("Creating WebSocket configuration manager...")
    config_manager = WebSocketConfigManager(config)
    
    # Create CORS manager
    logger.info("Creating CORS manager...")
    cors_manager = CORSManager(config_manager)
    
    # Create WebSocket factory
    logger.info("Creating WebSocket factory...")
    factory = WebSocketFactory(config_manager, cors_manager)
    
    # Validate factory configuration
    logger.info("Validating factory configuration...")
    if factory.validate_factory_configuration():
        logger.info("✅ Factory configuration is valid")
    else:
        logger.warning("⚠️ Factory configuration has issues")
    
    # Create SocketIO instance using factory
    logger.info("Creating SocketIO instance using factory...")
    socketio = factory.create_socketio_instance(app)
    
    # Get factory status
    status = factory.get_factory_status()
    logger.info(f"Factory status: {status['config_manager_status']['status']}")
    logger.info(f"CORS origins configured: {status['config_manager_status']['cors_origins_count']}")
    logger.info(f"Transports: {status['config_manager_status']['transports']}")
    logger.info(f"Async mode: {status['config_manager_status']['async_mode']}")
    
    return app, socketio, factory


def demonstrate_namespace_configuration(factory, socketio):
    """
    Demonstrate namespace configuration
    
    Args:
        factory: WebSocket factory instance
        socketio: SocketIO instance
    """
    logger.info("\n=== Namespace Configuration Demonstration ===")
    
    # Define namespace configurations
    namespace_configs = {
        '/user': {
            'description': 'User namespace for regular user connections',
            'auth_required': True,
            'handlers': {
                'user_message': lambda data: logger.info(f"User message: {data}"),
                'user_status': lambda data: logger.info(f"User status: {data}"),
            }
        },
        '/admin': {
            'description': 'Admin namespace for administrative functions',
            'auth_required': True,
            'admin_only': True,
            'handlers': {
                'admin_command': lambda data: logger.info(f"Admin command: {data}"),
                'system_status': lambda data: logger.info(f"System status: {data}"),
            }
        }
    }
    
    # Configure namespaces
    logger.info("Configuring custom namespaces...")
    factory.configure_namespaces(socketio, namespace_configs)
    logger.info("✅ Namespaces configured successfully")


def demonstrate_middleware_and_error_handlers(factory):
    """
    Demonstrate middleware and error handler registration
    
    Args:
        factory: WebSocket factory instance
    """
    logger.info("\n=== Middleware and Error Handler Demonstration ===")
    
    # Register custom middleware
    def logging_middleware(socketio):
        """Example middleware for logging"""
        logger.info("Logging middleware applied to SocketIO instance")
    
    def security_middleware(socketio):
        """Example middleware for security"""
        logger.info("Security middleware applied to SocketIO instance")
    
    factory.register_middleware(logging_middleware)
    factory.register_middleware(security_middleware)
    logger.info("✅ Middleware functions registered")
    
    # Register custom error handlers
    def cors_error_handler(error):
        """Handle CORS-specific errors"""
        logger.error(f"CORS error occurred: {error}")
    
    def timeout_error_handler(error):
        """Handle timeout errors"""
        logger.error(f"Timeout error occurred: {error}")
    
    factory.register_error_handler('cors_error', cors_error_handler)
    factory.register_error_handler('timeout_error', timeout_error_handler)
    logger.info("✅ Error handlers registered")


def demonstrate_configuration_comparison():
    """
    Demonstrate the difference between old hardcoded config and new factory config
    """
    logger.info("\n=== Configuration Comparison ===")
    
    # Old hardcoded configuration (from web_app.py)
    old_config = {
        'cors_allowed_origins': "*",
        'cors_credentials': True,
        'async_mode': 'threading',
        'allow_upgrades': True,
        'transports': ['polling', 'websocket'],
        'ping_timeout': 60,
        'ping_interval': 25
    }
    
    logger.info("Old hardcoded configuration:")
    for key, value in old_config.items():
        logger.info(f"  {key}: {value}")
    
    # New factory configuration
    config = Config()
    config_manager = WebSocketConfigManager(config)
    cors_manager = CORSManager(config_manager)
    factory = WebSocketFactory(config_manager, cors_manager)
    
    new_config = factory._get_unified_socketio_config()
    
    logger.info("\nNew factory-generated configuration:")
    for key, value in new_config.items():
        if key == 'cors_allowed_origins' and isinstance(value, list) and len(value) > 3:
            logger.info(f"  {key}: [{len(value)} origins] {value[:3]}...")
        else:
            logger.info(f"  {key}: {value}")
    
    # Highlight improvements
    logger.info("\n✅ Improvements with factory configuration:")
    logger.info("  - Dynamic CORS origins based on environment")
    logger.info("  - Environment variable configuration")
    logger.info("  - Comprehensive error handling")
    logger.info("  - Namespace management")
    logger.info("  - Middleware support")
    logger.info("  - Configuration validation")
    logger.info("  - Fallback mechanisms")


def demonstrate_environment_configuration():
    """
    Demonstrate how environment variables affect configuration
    """
    logger.info("\n=== Environment Configuration Demonstration ===")
    
    # Show current environment variables
    env_vars = [
        'FLASK_HOST', 'FLASK_PORT', 'SOCKETIO_CORS_ORIGINS',
        'SOCKETIO_TRANSPORTS', 'SOCKETIO_ASYNC_MODE',
        'SOCKETIO_PING_TIMEOUT', 'SOCKETIO_PING_INTERVAL'
    ]
    
    logger.info("Current WebSocket-related environment variables:")
    for var in env_vars:
        value = os.getenv(var, 'Not set')
        logger.info(f"  {var}: {value}")
    
    # Demonstrate configuration with different environment settings
    logger.info("\nTesting with custom environment variables...")
    
    # Temporarily set environment variables
    original_values = {}
    test_env = {
        'FLASK_HOST': '127.0.0.1',
        'FLASK_PORT': '8080',
        'SOCKETIO_TRANSPORTS': 'websocket',
        'SOCKETIO_PING_TIMEOUT': '30'
    }
    
    for key, value in test_env.items():
        original_values[key] = os.getenv(key)
        os.environ[key] = value
    
    try:
        # Create new configuration with test environment
        config = Config()
        config_manager = WebSocketConfigManager(config)
        
        # Show how configuration changes
        logger.info("Configuration with test environment:")
        summary = config_manager.get_configuration_summary()
        logger.info(f"  CORS origins: {summary['cors_origins']}")
        logger.info(f"  Transports: {summary['transports']}")
        logger.info(f"  Ping timeout: {summary['timeouts']['ping_timeout']}")
        
    finally:
        # Restore original environment
        for key, original_value in original_values.items():
            if original_value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = original_value


def main():
    """Main demonstration function"""
    try:
        # Create app with WebSocket factory
        app, socketio, factory = create_app_with_websocket_factory()
        
        # Demonstrate namespace configuration
        demonstrate_namespace_configuration(factory, socketio)
        
        # Demonstrate middleware and error handlers
        demonstrate_middleware_and_error_handlers(factory)
        
        # Show configuration comparison
        demonstrate_configuration_comparison()
        
        # Show environment configuration
        demonstrate_environment_configuration()
        
        logger.info("\n=== WebSocket Factory Demonstration Complete ===")
        logger.info("✅ All demonstrations completed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Demonstration failed: {e}")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)