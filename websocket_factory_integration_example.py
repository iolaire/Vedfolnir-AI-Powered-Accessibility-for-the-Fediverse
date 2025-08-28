# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Factory Integration Example

This example shows how to refactor the existing web_app.py SocketIO initialization
to use the new WebSocket Factory for standardized configuration.
"""

import logging
from flask import Flask
from config import Config
from websocket_factory import WebSocketFactory
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_legacy_socketio(app):
    """
    Legacy SocketIO creation (current web_app.py approach)
    
    This is how SocketIO is currently created in web_app.py with hardcoded configuration.
    """
    from flask_socketio import SocketIO
    
    logger.info("Creating SocketIO with legacy hardcoded configuration...")
    
    # Current hardcoded configuration from web_app.py
    socketio = SocketIO(app, 
                       cors_allowed_origins="*",  # More permissive for development
                       cors_credentials=True,  # Allow credentials (cookies)
                       async_mode='threading',
                       allow_upgrades=True,
                       transports=['polling', 'websocket'],
                       ping_timeout=60,
                       ping_interval=25)
    
    logger.info("✅ Legacy SocketIO created")
    return socketio


def create_factory_socketio(app):
    """
    New SocketIO creation using WebSocket Factory
    
    This shows how to replace the legacy approach with the factory pattern.
    """
    logger.info("Creating SocketIO with WebSocket Factory...")
    
    # Create configuration
    config = Config()
    
    # Create WebSocket configuration manager
    config_manager = WebSocketConfigManager(config)
    
    # Create CORS manager
    cors_manager = CORSManager(config_manager)
    
    # Create WebSocket factory
    factory = WebSocketFactory(config_manager, cors_manager)
    
    # Create SocketIO instance using factory
    socketio = factory.create_socketio_instance(app)
    
    logger.info("✅ Factory SocketIO created")
    return socketio, factory


def demonstrate_refactoring():
    """
    Demonstrate the refactoring process from legacy to factory approach
    """
    logger.info("=== WebSocket Factory Integration Example ===")
    
    # Create Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'example-secret-key'
    app.config['TESTING'] = True
    
    logger.info("\n--- Legacy Approach ---")
    legacy_socketio = create_legacy_socketio(app)
    
    logger.info("\n--- Factory Approach ---")
    factory_socketio, factory = create_factory_socketio(app)
    
    # Compare configurations
    logger.info("\n--- Configuration Comparison ---")
    
    # Get factory configuration for comparison
    factory_config = factory._get_unified_socketio_config()
    
    logger.info("Key differences:")
    logger.info(f"  CORS Origins:")
    logger.info(f"    Legacy: '*' (wildcard - less secure)")
    logger.info(f"    Factory: {len(factory_config['cors_allowed_origins'])} specific origins (more secure)")
    
    logger.info(f"  Transport Order:")
    logger.info(f"    Legacy: ['polling', 'websocket'] (polling first)")
    logger.info(f"    Factory: {factory_config['transports']} (websocket first)")
    
    logger.info(f"  Additional Features:")
    logger.info(f"    Legacy: Basic configuration only")
    logger.info(f"    Factory: Error handling, middleware, namespace management, validation")
    
    return True


def show_migration_steps():
    """
    Show the step-by-step migration process
    """
    logger.info("\n=== Migration Steps ===")
    
    logger.info("Step 1: Import the factory components")
    logger.info("  from websocket_factory import WebSocketFactory")
    logger.info("  from websocket_config_manager import WebSocketConfigManager")
    logger.info("  from websocket_cors_manager import CORSManager")
    
    logger.info("\nStep 2: Replace the hardcoded SocketIO creation")
    logger.info("  # OLD:")
    logger.info("  socketio = SocketIO(app, cors_allowed_origins='*', ...)")
    logger.info("  ")
    logger.info("  # NEW:")
    logger.info("  config_manager = WebSocketConfigManager(config)")
    logger.info("  cors_manager = CORSManager(config_manager)")
    logger.info("  factory = WebSocketFactory(config_manager, cors_manager)")
    logger.info("  socketio = factory.create_socketio_instance(app)")
    
    logger.info("\nStep 3: Configure environment variables (optional)")
    logger.info("  SOCKETIO_CORS_ORIGINS=http://localhost:3000,http://localhost:5000")
    logger.info("  SOCKETIO_TRANSPORTS=websocket,polling")
    logger.info("  SOCKETIO_PING_TIMEOUT=60")
    
    logger.info("\nStep 4: Test the migration")
    logger.info("  - Verify WebSocket connections work")
    logger.info("  - Check CORS functionality")
    logger.info("  - Test error handling")
    
    logger.info("\n✅ Migration complete!")


def main():
    """Main example function"""
    try:
        # Demonstrate the refactoring
        demonstrate_refactoring()
        
        # Show migration steps
        show_migration_steps()
        
        logger.info("\n=== Integration Example Complete ===")
        logger.info("✅ Ready to integrate WebSocket Factory into web_app.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration example failed: {e}")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)