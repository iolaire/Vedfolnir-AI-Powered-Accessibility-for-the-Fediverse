# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Static Asset Caching Middleware

Implements comprehensive caching headers for static assets to improve performance
while maintaining proper cache invalidation strategies.
"""

import os
import re
import hashlib
import logging
from datetime import datetime, timedelta
from flask import request, Response, current_app, g
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class StaticAssetCacheMiddleware:
    """Comprehensive static asset caching middleware"""
    
    def __init__(self, app=None):
        """Initialize the caching middleware"""
        self.app = app
        self.etag_cache = {}  # Simple ETag cache (in production, use Redis)
        
        # Cache configuration by file type
        self.cache_config = {
            # Images - long cache, immutable
            'images': {
                'extensions': {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp'},
                'max_age': 31536000,  # 1 year
                'immutable': True,
                'public': True
            },
            # JavaScript - long cache with versioning
            'javascript': {
                'extensions': {'.js'},
                'max_age': 31536000,  # 1 year
                'immutable': True,
                'public': True
            },
            # CSS - long cache with versioning
            'stylesheets': {
                'extensions': {'.css'},
                'max_age': 31536000,  # 1 year
                'immutable': True,
                'public': True
            },
            # Fonts - long cache
            'fonts': {
                'extensions': {'.woff', '.woff2', '.ttf', '.eot', '.otf'},
                'max_age': 31536000,  # 1 year
                'immutable': True,
                'public': True
            },
            # Media files - medium cache
            'media': {
                'extensions': {'.mp4', '.webm', '.mp3', '.wav', '.ogg'},
                'max_age': 604800,  # 1 week
                'immutable': False,
                'public': True
            },
            # Documents - medium cache
            'documents': {
                'extensions': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'},
                'max_age': 86400,  # 1 day
                'immutable': False,
                'public': True
            },
            # Other static files - short cache
            'default': {
                'extensions': set(),
                'max_age': 3600,  # 1 hour
                'immutable': False,
                'public': True
            }
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Add caching utility functions to app context
        app.context_processor(self.inject_cache_vars)
        
        logger.info("Static Asset Cache Middleware initialized")
    
    def before_request(self):
        """Process request before handling"""
        # Only process static file requests
        if not self._is_static_request(request):
            return
        
        # Generate ETag for the requested file
        etag = self._generate_etag(request.path)
        
        # Check If-None-Match header for conditional requests
        if_none_match = request.headers.get('If-None-Match')
        if if_none_match and if_none_match == etag:
            return Response(status=304)  # Not Modified
    
    def after_request(self, response: Response):
        """Add caching headers to response"""
        # Only process static file responses
        if not self._is_static_request(request):
            return response
        
        # Skip if response already has cache control headers
        if 'Cache-Control' in response.headers:
            return response
        
        # Get file extension and determine cache configuration
        file_ext = self._get_file_extension(request.path)
        cache_config = self._get_cache_config(file_ext)
        
        # Add caching headers
        self._add_cache_headers(response, cache_config)
        
        # Add ETag
        etag = self._generate_etag(request.path)
        response.headers['ETag'] = etag
        
        # Add Last-Modified header
        last_modified = self._get_last_modified(request.path)
        if last_modified:
            response.headers['Last-Modified'] = last_modified
        
        # Add Content-Type if not present
        if 'Content-Type' not in response.headers:
            content_type = self._get_content_type(file_ext)
            if content_type:
                response.headers['Content-Type'] = content_type
        
        logger.debug(f"Added cache headers for {request.path}: {cache_config['max_age']}s")
        
        return response
    
    def _is_static_request(self, request) -> bool:
        """Check if the request is for a static file"""
        static_url = current_app.static_url_path
        return request.path.startswith(static_url)
    
    def _get_file_extension(self, path: str) -> str:
        """Get file extension from path"""
        return Path(path).suffix.lower()
    
    def _get_cache_config(self, file_ext: str) -> Dict[str, Any]:
        """Get cache configuration for file extension"""
        for category, config in self.cache_config.items():
            if file_ext in config['extensions']:
                return config
        return self.cache_config['default']
    
    def _add_cache_headers(self, response: Response, config: Dict[str, Any]):
        """Add cache control headers to response"""
        cache_directives = []
        
        # Public cache
        if config['public']:
            cache_directives.append('public')
        else:
            cache_directives.append('private')
        
        # Max age
        cache_directives.append(f'max-age={config["max_age"]}')
        
        # Immutable flag
        if config['immutable']:
            cache_directives.append('immutable')
        
        # Add cache control header
        response.headers['Cache-Control'] = ', '.join(cache_directives)
        
        # Add Expires header for older browsers
        expires_date = datetime.utcnow() + timedelta(seconds=config['max_age'])
        response.headers['Expires'] = expires_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    def _generate_etag(self, path: str) -> str:
        """Generate ETag for static file"""
        # Simple ETag generation based on file path and modification time
        try:
            file_path = self._get_file_path(path)
            if file_path and os.path.exists(file_path):
                stat = os.stat(file_path)
                etag_data = f"{path}-{stat.st_mtime}-{stat.st_size}"
                return hashlib.md5(etag_data.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to generate ETag for {path}: {e}")
        
        # Fallback ETag
        return hashlib.md5(path.encode()).hexdigest()
    
    def _get_file_path(self, path: str) -> Optional[str]:
        """Get actual file path for request path"""
        try:
            # Remove static URL prefix
            static_prefix = current_app.static_url_path
            if path.startswith(static_prefix):
                relative_path = path[len(static_prefix):]
                # Remove leading slash
                if relative_path.startswith('/'):
                    relative_path = relative_path[1:]
                
                # Construct full file path
                file_path = os.path.join(current_app.static_folder, relative_path)
                return file_path
        except Exception as e:
            logger.warning(f"Failed to get file path for {path}: {e}")
        
        return None
    
    def _get_last_modified(self, path: str) -> Optional[str]:
        """Get Last-Modified date for file"""
        try:
            file_path = self._get_file_path(path)
            if file_path and os.path.exists(file_path):
                stat = os.stat(file_path)
                last_modified = datetime.fromtimestamp(stat.st_mtime, tz=None)
                return last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
        except Exception as e:
            logger.warning(f"Failed to get Last-Modified for {path}: {e}")
        
        return None
    
    def _get_content_type(self, file_ext: str) -> Optional[str]:
        """Get Content-Type for file extension"""
        content_types = {
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
            '.otf': 'font/otf',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.pdf': 'application/pdf'
        }
        
        return content_types.get(file_ext)
    
    def inject_cache_vars(self):
        """Inject caching variables into template context"""
        return {
            'CACHE_BUSTER': self._get_cache_buster(),
            'STATIC_VERSION': self._get_static_version()
        }
    
    def _get_cache_buster(self) -> str:
        """Generate cache buster string"""
        # Use timestamp for development, version hash for production
        if current_app.debug:
            return str(int(datetime.utcnow().timestamp()))
        else:
            return hashlib.md5(str(datetime.utcnow().date()).encode()).hexdigest()[:8]
    
    def _get_static_version(self) -> str:
        """Get static version string for versioned URLs"""
        return "1.0.0"  # This could be from environment or version file
    
    def clear_cache(self):
        """Clear the ETag cache"""
        self.etag_cache.clear()
        logger.info("ETag cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'etag_cache_size': len(self.etag_cache),
            'cache_config': self.cache_config,
            'cache_buster': self._get_cache_buster(),
            'static_version': self._get_static_version()
        }