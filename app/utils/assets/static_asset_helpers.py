# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Static Asset URL Helper

Provides template filters and helpers for cache-busting static asset URLs.
"""

import os
import hashlib
from datetime import datetime
from flask import url_for, current_app
from pathlib import Path

def static_url_with_cache(filename: str, version: str = None) -> str:
    """
    Generate static URL with cache-busting query parameter
    
    Args:
        filename: Static file name (relative to static folder)
        version: Optional version string
        
    Returns:
        URL with cache-busting parameter
    """
    try:
        # Get file path
        static_folder = current_app.static_folder
        file_path = Path(static_folder) / filename.lstrip('/')
        
        # Generate version parameter
        if version is None:
            if current_app.debug:
                # Use file modification time in development
                if file_path.exists():
                    mtime = file_path.stat().st_mtime
                    version = str(int(mtime))
                else:
                    version = str(int(datetime.utcnow().timestamp()))
            else:
                # Use content hash in production
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        version = hashlib.md5(content).hexdigest()[:8]
                else:
                    version = "1.0.0"
        
        # Generate URL with version parameter
        return url_for('static', filename=filename, v=version)
        
    except Exception as e:
        current_app.logger.warning(f"Failed to generate cache-busting URL for {filename}: {e}")
        # Fallback to regular URL
        return url_for('static', filename=filename)

def static_url_with_version(filename: str, version: str = None) -> str:
    """
    Generate static URL with version in filename
    
    Args:
        filename: Static file name (relative to static folder)
        version: Optional version string
        
    Returns:
        URL with version embedded in filename
    """
    try:
        if version is None:
            version = "1.0.0"
        
        # Split filename and extension
        file_path = Path(filename)
        name = file_path.stem
        ext = file_path.suffix
        
        # Create versioned filename
        versioned_filename = f"{name}.v{version}{ext}"
        
        return url_for('static', filename=versioned_filename)
        
    except Exception as e:
        current_app.logger.warning(f"Failed to generate versioned URL for {filename}: {e}")
        return url_for('static', filename=filename)

def get_asset_size(filename: str) -> str:
    """
    Get human-readable file size for asset
    
    Args:
        filename: Static file name (relative to static folder)
        
    Returns:
        Human-readable file size string
    """
    try:
        static_folder = current_app.static_folder
        file_path = Path(static_folder) / filename.lstrip('/')
        
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            
            # Convert to human-readable format
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            
            return f"{size_bytes:.1f} TB"
        else:
            return "Unknown"
            
    except Exception as e:
        current_app.logger.warning(f"Failed to get size for {filename}: {e}")
        return "Unknown"

def get_asset_info(filename: str) -> dict:
    """
    Get comprehensive asset information
    
    Args:
        filename: Static file name (relative to static folder)
        
    Returns:
        Dictionary with asset information
    """
    try:
        static_folder = current_app.static_folder
        file_path = Path(static_folder) / filename.lstrip('/')
        
        info = {
            'filename': filename,
            'exists': file_path.exists(),
            'size': 'Unknown',
            'size_bytes': 0,
            'modified': None,
            'url': url_for('static', filename=filename),
            'cache_busted_url': static_url_with_cache(filename),
            'versioned_url': static_url_with_version(filename)
        }
        
        if file_path.exists():
            stat = file_path.stat()
            info['size'] = get_asset_size(filename)
            info['size_bytes'] = stat.st_size
            info['modified'] = datetime.fromtimestamp(stat.st_mtime)
            
            # Add file type information
            ext = file_path.suffix.lower()
            info['type'] = ext
            
            # Add MIME type
            mime_types = {
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
                '.pdf': 'application/pdf'
            }
            info['mime_type'] = mime_types.get(ext, 'application/octet-stream')
        
        return info
        
    except Exception as e:
        current_app.logger.warning(f"Failed to get info for {filename}: {e}")
        return {
            'filename': filename,
            'exists': False,
            'error': str(e)
        }

def register_template_filters(app):
    """Register template filters for static asset handling"""
    
    @app.template_filter('static_url')
    def static_url_filter(filename: str) -> str:
        """Template filter for cache-busted static URLs"""
        return static_url_with_cache(filename)
    
    @app.template_filter('asset_size')
    def asset_size_filter(filename: str) -> str:
        """Template filter for asset file size"""
        return get_asset_size(filename)
    
    @app.template_filter('asset_info')
    def asset_info_filter(filename: str) -> dict:
        """Template filter for asset information"""
        return get_asset_info(filename)
    
    @app.template_filter('css_url')
    def css_url_filter(filename: str) -> str:
        """Template filter specifically for CSS files"""
        if not filename.endswith('.css'):
            filename += '.css'
        return static_url_with_cache(filename)
    
    @app.template_filter('js_url')
    def js_url_filter(filename: str) -> str:
        """Template filter specifically for JavaScript files"""
        if not filename.endswith('.js'):
            filename += '.js'
        return static_url_with_cache(filename)
    
    @app.template_filter('img_url')
    def img_url_filter(filename: str) -> str:
        """Template filter specifically for image files"""
        return static_url_with_cache(filename)
    
    @app.template_filter('nl2br')
    def nl2br_filter(value):
        """Convert newlines to HTML line breaks"""
        if not value:
            return value
        return value.replace('\n', '<br>\n')
    
    # Add global template functions
    @app.context_processor
    def inject_asset_helpers():
        return {
            'static_url': static_url_with_cache,
            'asset_size': get_asset_size,
            'asset_info': get_asset_info,
            'css_url': lambda f: static_url_with_cache(f if f.endswith('.css') else f + '.css'),
            'js_url': lambda f: static_url_with_cache(f if f.endswith('.js') else f + '.js'),
            'img_url': static_url_with_cache
        }