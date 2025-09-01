# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket CORS Manager

This module provides comprehensive CORS (Cross-Origin Resource Sharing) management
for WebSocket connections, including dynamic origin calculation, protocol detection,
localhost variant handling, and preflight request management.
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse
from flask import Flask, request, Response, make_response
from websocket_config_manager import WebSocketConfigManager

logger = logging.getLogger(__name__)


class CORSManager:
    """
    Handles Cross-Origin Resource Sharing configuration and validation for WebSocket connections
    
    Provides dynamic origin calculation based on environment variables, protocol detection,
    localhost/127.0.0.1 variant handling, and comprehensive preflight request handling.
    """
    
    def __init__(self, config_manager: WebSocketConfigManager):
        """
        Initialize CORS manager
        
        Args:
            config_manager: WebSocket configuration manager instance
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self._allowed_origins_cache = None
        self._origin_patterns = []
        self._setup_origin_patterns()
    
    def _setup_origin_patterns(self) -> None:
        """Setup origin validation patterns for dynamic matching"""
        # Common localhost patterns
        self._origin_patterns = [
            re.compile(r'^https?://localhost(:\d+)?/?$'),
            re.compile(r'^https?://127\.0\.0\.1(:\d+)?/?$'),
            re.compile(r'^https?://\[::1\](:\d+)?/?$'),  # IPv6 localhost
        ]
        
        # Add environment-specific patterns
        flask_host = os.getenv("FLASK_HOST", "127.0.0.1")
        if flask_host not in ["localhost", "127.0.0.1", "::1"]:
            # Add pattern for custom host
            escaped_host = re.escape(flask_host)
            pattern = re.compile(f'^https?://{escaped_host}(:\\d+)?/?$')
            self._origin_patterns.append(pattern)
    
    def get_allowed_origins(self) -> List[str]:
        """
        Get list of allowed CORS origins with dynamic calculation
        
        Returns:
            List of allowed CORS origins
        """
        if self._allowed_origins_cache is None:
            self._allowed_origins_cache = self._calculate_allowed_origins()
        
        return self._allowed_origins_cache.copy()
    
    def _calculate_allowed_origins(self) -> List[str]:
        """
        Calculate allowed origins with dynamic protocol and host detection
        
        Returns:
            List of calculated allowed origins
        """
        origins = set()
        
        # Get base origins from config manager
        base_origins = self.config_manager.get_cors_origins()
        
        # Check for wildcard
        if "*" in base_origins:
            self.logger.warning("Wildcard CORS origin detected - this should only be used in development")
            return ["*"]
        
        # Process each base origin
        for origin in base_origins:
            processed_origins = self._process_origin_variants(origin)
            origins.update(processed_origins)
        
        # Add environment-specific origins
        env_origins = self._get_environment_origins()
        origins.update(env_origins)
        
        # Convert to sorted list for consistency
        origin_list = sorted(list(origins))
        
        self.logger.info(f"Calculated {len(origin_list)} allowed CORS origins")
        self.logger.debug(f"Allowed origins: {origin_list}")
        
        return origin_list
    
    def _process_origin_variants(self, origin: str) -> Set[str]:
        """
        Process origin to generate protocol and host variants
        
        Args:
            origin: Base origin URL
            
        Returns:
            Set of origin variants
        """
        variants = set()
        
        try:
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc:
                self.logger.warning(f"Invalid origin format: {origin}")
                return variants
            
            # Add original origin
            variants.add(origin)
            
            # Generate protocol variants (HTTP/HTTPS)
            if parsed.scheme == "http":
                # Add HTTPS variant
                https_origin = urlunparse((
                    "https", parsed.netloc, parsed.path,
                    parsed.params, parsed.query, parsed.fragment
                ))
                variants.add(https_origin)
            elif parsed.scheme == "https":
                # Add HTTP variant for development
                http_origin = urlunparse((
                    "http", parsed.netloc, parsed.path,
                    parsed.params, parsed.query, parsed.fragment
                ))
                variants.add(http_origin)
            
            # Generate localhost variants
            if parsed.hostname in ["localhost", "127.0.0.1"]:
                localhost_variants = self._generate_localhost_variants(parsed)
                variants.update(localhost_variants)
            
        except Exception as e:
            self.logger.error(f"Error processing origin variants for {origin}: {e}")
        
        return variants
    
    def _generate_localhost_variants(self, parsed_url) -> Set[str]:
        """
        Generate localhost/127.0.0.1 variants for an origin
        
        Args:
            parsed_url: Parsed URL object
            
        Returns:
            Set of localhost variants
        """
        variants = set()
        
        # Localhost variants
        localhost_hosts = ["localhost", "127.0.0.1"]
        
        for host in localhost_hosts:
            for scheme in ["http", "https"]:
                if parsed_url.port:
                    netloc = f"{host}:{parsed_url.port}"
                else:
                    netloc = host
                
                variant = urlunparse((
                    scheme, netloc, parsed_url.path or "/",
                    parsed_url.params, parsed_url.query, parsed_url.fragment
                ))
                variants.add(variant)
        
        return variants
    
    def _get_environment_origins(self) -> Set[str]:
        """
        Get additional origins based on environment configuration
        
        Returns:
            Set of environment-specific origins
        """
        origins = set()
        
        # Get current environment
        flask_env = os.getenv("FLASK_ENV", "production")
        
        # Add development-specific origins
        if flask_env in ["development", "dev"]:
            dev_origins = [
                "http://localhost:3000",   # React dev server
                "http://127.0.0.1:3000",
                "http://localhost:8080",   # Vue/webpack dev server
                "http://127.0.0.1:8080",
                "http://localhost:4200",   # Angular dev server
                "http://127.0.0.1:4200",
                "http://localhost:8000",   # Django dev server
                "http://127.0.0.1:8000",
            ]
            origins.update(dev_origins)
        
        # Add production-specific origins
        if flask_env == "production":
            # Add HTTPS variants of configured origins
            flask_host = os.getenv("FLASK_HOST", "127.0.0.1")
            flask_port = int(os.getenv("FLASK_PORT", "5000"))
            
            if flask_port == 443:
                origins.add(f"https://{flask_host}")
            else:
                origins.add(f"https://{flask_host}:{flask_port}")
        
        return origins
    
    def validate_origin(self, origin: str) -> bool:
        """
        Validate if an origin is allowed for CORS requests
        
        Args:
            origin: Origin header value to validate
            
        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            return False
        
        # Check against allowed origins
        allowed_origins = self.get_allowed_origins()
        
        # Check for wildcard
        if "*" in allowed_origins:
            return True
        
        # Exact match check
        if origin in allowed_origins:
            return True
        
        # Pattern-based validation for dynamic origins
        return self._validate_origin_pattern(origin)
    
    def _validate_origin_pattern(self, origin: str) -> bool:
        """
        Validate origin against dynamic patterns
        
        Args:
            origin: Origin to validate
            
        Returns:
            True if origin matches allowed patterns
        """
        try:
            parsed = urlparse(origin)
            
            # Validate basic structure
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check against origin patterns
            for pattern in self._origin_patterns:
                if pattern.match(origin):
                    return True
            
            # Check if it's a localhost variant with different port
            if parsed.hostname in ["localhost", "127.0.0.1", "::1"]:
                return self._validate_localhost_port(parsed.port)
            
        except Exception as e:
            self.logger.error(f"Error validating origin pattern for {origin}: {e}")
        
        return False
    
    def _validate_localhost_port(self, port: Optional[int]) -> bool:
        """
        Validate if a localhost port is allowed
        
        Args:
            port: Port number to validate
            
        Returns:
            True if port is allowed for localhost
        """
        if port is None:
            return True  # Default ports (80/443)
        
        # Allow common development ports
        allowed_ports = {
            80, 443, 3000, 3001, 4200, 5000, 5001, 8000, 8080, 8443, 9000
        }
        
        # Allow configured Flask port
        flask_port = int(os.getenv("FLASK_PORT", "5000"))
        allowed_ports.add(flask_port)
        
        return port in allowed_ports
    
    def setup_cors_headers(self, app: Flask) -> None:
        """
        Setup CORS headers for the Flask application
        
        Args:
            app: Flask application instance
        """
        @app.after_request
        def after_request(response: Response) -> Response:
            """Add CORS headers to all responses"""
            origin = request.headers.get('Origin')
            
            if origin and self.validate_origin(origin):
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = (
                    'Content-Type, Authorization, X-Requested-With, '
                    'X-CSRFToken, Accept, Accept-Version, Content-Length, '
                    'Content-MD5, Date, X-Api-Version'
                )
                response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
            
            return response
        
        self.logger.info("CORS headers configured for Flask application")
    
    def handle_preflight_requests(self, app: Flask) -> None:
        """
        Setup comprehensive preflight request handlers
        
        Args:
            app: Flask application instance
        """
        @app.before_request
        def handle_preflight():
            """Handle CORS preflight requests"""
            if request.method == 'OPTIONS':
                origin = request.headers.get('Origin')
                
                if not origin:
                    # No origin header - not a CORS request
                    return None
                
                if not self.validate_origin(origin):
                    # Origin not allowed
                    self.logger.warning(f"CORS preflight rejected for origin: {origin}")
                    return make_response('', 403)
                
                # Create preflight response
                response = make_response('', 200)
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = (
                    'Content-Type, Authorization, X-Requested-With, '
                    'X-CSRFToken, Accept, Accept-Version, Content-Length, '
                    'Content-MD5, Date, X-Api-Version'
                )
                response.headers['Access-Control-Max-Age'] = '86400'
                
                self.logger.debug(f"CORS preflight approved for origin: {origin}")
                return response
            
            return None
        
        self.logger.info("CORS preflight handlers configured")
    
    def get_cors_config_for_socketio(self) -> Dict[str, Any]:
        """
        Get CORS configuration specifically formatted for Flask-SocketIO
        
        Returns:
            CORS configuration dictionary for Flask-SocketIO
        """
        allowed_origins = self.get_allowed_origins()
        
        # Flask-SocketIO CORS configuration
        # For wildcard access, use "*" string instead of True to avoid EngineIO compatibility issues
        if (isinstance(allowed_origins, list) and len(allowed_origins) == 1 and allowed_origins[0] == "*") or allowed_origins == "*":
            cors_origins = "*"  # Use string instead of True for better compatibility
        elif isinstance(allowed_origins, list) and len(allowed_origins) > 0:
            # Valid list of origins
            cors_origins = allowed_origins
        elif isinstance(allowed_origins, bool):
            # If somehow a boolean got through, handle it properly
            cors_origins = "*" if allowed_origins else []
        elif isinstance(allowed_origins, str):
            # If it's a string, use it directly
            cors_origins = allowed_origins
        else:
            # Fallback to empty list for any other type
            self.logger.warning(f"Unexpected allowed_origins type: {type(allowed_origins)}, value: {allowed_origins}")
            cors_origins = []
        
        self.logger.debug(f"CORS config for SocketIO - allowed_origins: {allowed_origins}, cors_origins: {cors_origins}")
        
        return {
            'cors_allowed_origins': cors_origins,
            'cors_credentials': True,
        }
    
    def detect_protocol_from_request(self) -> str:
        """
        Detect the protocol (HTTP/HTTPS) from the current request
        
        Returns:
            Protocol string ('http' or 'https')
        """
        # Check X-Forwarded-Proto header (common with reverse proxies)
        forwarded_proto = request.headers.get('X-Forwarded-Proto')
        if forwarded_proto:
            return forwarded_proto.lower()
        
        # Check X-Forwarded-SSL header
        forwarded_ssl = request.headers.get('X-Forwarded-SSL')
        if forwarded_ssl and forwarded_ssl.lower() == 'on':
            return 'https'
        
        # Check WSGI environment for URL scheme
        if hasattr(request, 'environ'):
            url_scheme = request.environ.get('wsgi.url_scheme')
            if url_scheme:
                return url_scheme.lower()
        
        # Check if request is secure
        if request.is_secure:
            return 'https'
        
        # Default to HTTP
        return 'http'
    
    def get_dynamic_origin_for_client(self) -> str:
        """
        Get dynamic origin for client-side WebSocket connections
        
        Returns:
            Origin URL for client connections
        """
        protocol = self.detect_protocol_from_request()
        host = request.headers.get('Host', os.getenv('FLASK_HOST', '127.0.0.1'))
        
        # Handle port in host header
        if ':' in host:
            return f"{protocol}://{host}"
        else:
            # Add default port if needed
            flask_port = int(os.getenv('FLASK_PORT', '5000'))
            if (protocol == 'http' and flask_port != 80) or (protocol == 'https' and flask_port != 443):
                return f"{protocol}://{host}:{flask_port}"
            else:
                return f"{protocol}://{host}"
    
    def validate_websocket_origin(self, origin: str, namespace: str = None) -> Tuple[bool, str]:
        """
        Validate WebSocket connection origin with detailed error information
        
        Args:
            origin: Origin header from WebSocket connection
            namespace: WebSocket namespace (optional)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not origin:
            return False, "No origin header provided"
        
        # Validate origin format
        try:
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc:
                return False, f"Invalid origin format: {origin}"
        except Exception as e:
            return False, f"Failed to parse origin: {e}"
        
        # Check if origin is allowed
        if not self.validate_origin(origin):
            allowed_origins = self.get_allowed_origins()
            return False, f"Origin {origin} not in allowed origins: {allowed_origins}"
        
        # Namespace-specific validation (if needed)
        if namespace:
            namespace_valid, namespace_error = self._validate_namespace_origin(origin, namespace)
            if not namespace_valid:
                return False, namespace_error
        
        return True, "Origin validated successfully"
    
    def _validate_namespace_origin(self, origin: str, namespace: str) -> Tuple[bool, str]:
        """
        Validate origin for specific WebSocket namespace
        
        Args:
            origin: Origin to validate
            namespace: WebSocket namespace
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Admin namespace might have stricter requirements
        if namespace == '/admin':
            # Could add additional validation for admin namespace
            # For now, use same validation as regular namespaces
            pass
        
        return True, "Namespace origin validation passed"
    
    def get_cors_debug_info(self) -> Dict[str, Any]:
        """
        Get CORS configuration debug information
        
        Returns:
            Dictionary containing CORS debug information
        """
        return {
            'allowed_origins': self.get_allowed_origins(),
            'origin_patterns': [pattern.pattern for pattern in self._origin_patterns],
            'environment': {
                'FLASK_HOST': os.getenv('FLASK_HOST', '127.0.0.1'),
                'FLASK_PORT': os.getenv('FLASK_PORT', '5000'),
                'FLASK_ENV': os.getenv('FLASK_ENV', 'production'),
                'SOCKETIO_CORS_ORIGINS': os.getenv('SOCKETIO_CORS_ORIGINS'),
            },
            'request_info': {
                'origin': request.headers.get('Origin') if request else None,
                'host': request.headers.get('Host') if request else None,
                'protocol': self.detect_protocol_from_request() if request else None,
            } if request else None
        }
    
    def clear_cache(self) -> None:
        """Clear cached allowed origins to force recalculation"""
        self._allowed_origins_cache = None
        self.logger.debug("CORS origins cache cleared")
    
    def reload_configuration(self) -> None:
        """Reload CORS configuration from config manager"""
        self.clear_cache()
        self.config_manager.reload_configuration()
        self._setup_origin_patterns()
        self.logger.info("CORS configuration reloaded")