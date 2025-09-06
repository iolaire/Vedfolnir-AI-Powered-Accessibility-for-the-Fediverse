# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Asset Optimization Utilities

This module provides utilities for optimizing asset loading and minimizing
HTTP requests for better performance.
"""

import logging
from typing import Dict, List, Optional, Set
from flask import current_app, url_for
import hashlib
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class AssetOptimizer:
    """
    Asset optimization manager for Flask applications.
    
    Provides utilities for optimizing CSS, JavaScript, and image loading
    to minimize HTTP requests and improve page load performance.
    """
    
    def __init__(self):
        self._asset_cache = {}
        self._critical_css_cache = {}
        self._preload_assets = set()
    
    def get_critical_css(self, page_type: str = 'landing') -> str:
        """
        Get critical CSS for above-the-fold content.
        
        Args:
            page_type: Type of page (landing, dashboard, etc.)
        
        Returns:
            Critical CSS content as string
        """
        if page_type in self._critical_css_cache:
            return self._critical_css_cache[page_type]
        
        critical_css = self._generate_critical_css(page_type)
        self._critical_css_cache[page_type] = critical_css
        return critical_css
    
    def _generate_critical_css(self, page_type: str) -> str:
        """
        Generate critical CSS for a specific page type.
        
        Args:
            page_type: Type of page
        
        Returns:
            Critical CSS content
        """
        if page_type == 'landing':
            return """
/* Critical CSS for Landing Page */
:root {
    --primary-color: #0d6efd;
    --primary-dark: #0b5ed7;
    --primary-light: #6ea8fe;
    --bg-secondary: #f8f9fa;
    --text-primary: #212529;
    --text-secondary: #6c757d;
    --border-color: #dee2e6;
    --border-radius-lg: 0.5rem;
    --shadow-sm: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    --shadow-lg: 0 1rem 3rem rgba(0, 0, 0, 0.175);
    --transition-normal: all 0.15s ease-in-out;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.5;
    color: var(--text-primary);
    background-color: #fff;
    margin: 0;
    padding: 0;
}

.container {
    width: 100%;
    padding-right: 15px;
    padding-left: 15px;
    margin-right: auto;
    margin-left: auto;
    max-width: 1140px;
}

.landing-hero {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
    color: white;
    padding: 4rem 0;
    margin-top: -1.5rem;
    margin-left: -15px;
    margin-right: -15px;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.landing-hero h1 {
    font-size: 3.5rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
    line-height: 1.2;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.landing-hero .lead {
    font-size: 1.25rem;
    margin-bottom: 2.5rem;
    opacity: 0.95;
    max-width: 650px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.6;
}

.cta-button {
    background-color: white;
    color: var(--primary-color);
    border: none;
    padding: 1.25rem 2.5rem;
    font-size: 1.1rem;
    font-weight: 600;
    border-radius: var(--border-radius-lg);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: var(--transition-normal);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    min-height: 48px;
    min-width: 120px;
    box-sizing: border-box;
}

@media (max-width: 767px) {
    .landing-hero h1 {
        font-size: 2.5rem;
    }
    .landing-hero .lead {
        font-size: 1.1rem;
    }
    .cta-button {
        padding: 1rem 1.75rem;
        font-size: 1rem;
    }
}
"""
        
        return ""
    
    def get_preload_assets(self, page_type: str = 'landing') -> List[Dict[str, str]]:
        """
        Get list of assets to preload for better performance.
        
        Args:
            page_type: Type of page
        
        Returns:
            List of asset dictionaries with href, as, and type
        """
        preload_assets = []
        
        if page_type == 'landing':
            # Preload critical fonts
            preload_assets.extend([
                {
                    'href': 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
                    'as': 'style',
                    'type': 'text/css'
                }
            ])
            
            # Preload critical images
            try:
                logo_url = url_for('static', filename='images/Logo.png')
                preload_assets.append({
                    'href': logo_url,
                    'as': 'image',
                    'type': 'image/png'
                })
            except Exception:
                pass  # Skip if static files not available
        
        return preload_assets
    
    def get_dns_prefetch_domains(self) -> List[str]:
        """
        Get list of domains to DNS prefetch.
        
        Returns:
            List of domain names
        """
        return [
            'fonts.googleapis.com',
            'fonts.gstatic.com'
        ]
    
    def get_preconnect_domains(self) -> List[str]:
        """
        Get list of domains to preconnect.
        
        Returns:
            List of domain names with connection hints
        """
        return [
            'https://fonts.googleapis.com',
            'https://fonts.gstatic.com'
        ]
    
    def generate_asset_hash(self, asset_path: str) -> Optional[str]:
        """
        Generate hash for asset versioning.
        
        Args:
            asset_path: Path to the asset file
        
        Returns:
            Hash string for cache busting or None if file not found
        """
        try:
            if current_app:
                static_folder = current_app.static_folder
                if static_folder:
                    full_path = Path(static_folder) / asset_path
                    if full_path.exists():
                        with open(full_path, 'rb') as f:
                            content = f.read()
                            return hashlib.md5(content).hexdigest()[:8]
            return None
        except Exception as e:
            logger.debug(f"Could not generate hash for asset {asset_path}: {e}")
            return None
    
    def get_versioned_asset_url(self, asset_path: str) -> str:
        """
        Get versioned URL for an asset.
        
        Args:
            asset_path: Path to the asset
        
        Returns:
            Versioned asset URL
        """
        try:
            base_url = url_for('static', filename=asset_path)
            asset_hash = self.generate_asset_hash(asset_path)
            
            if asset_hash:
                separator = '&' if '?' in base_url else '?'
                return f"{base_url}{separator}v={asset_hash}"
            
            return base_url
        except Exception as e:
            logger.debug(f"Could not generate versioned URL for {asset_path}: {e}")
            return asset_path
    
    def get_resource_hints(self, page_type: str = 'landing') -> Dict[str, List]:
        """
        Get all resource hints for a page type.
        
        Args:
            page_type: Type of page
        
        Returns:
            Dictionary with preload, dns-prefetch, and preconnect lists
        """
        return {
            'preload': self.get_preload_assets(page_type),
            'dns_prefetch': self.get_dns_prefetch_domains(),
            'preconnect': self.get_preconnect_domains()
        }

# Global asset optimizer instance
_asset_optimizer = None

def get_asset_optimizer() -> AssetOptimizer:
    """
    Get the global asset optimizer instance.
    
    Returns:
        AssetOptimizer instance
    """
    global _asset_optimizer
    if _asset_optimizer is None:
        _asset_optimizer = AssetOptimizer()
        logger.debug("Initialized asset optimizer")
    
    return _asset_optimizer

def get_critical_css(page_type: str = 'landing') -> str:
    """
    Get critical CSS for a page type.
    
    Args:
        page_type: Type of page
    
    Returns:
        Critical CSS content
    """
    optimizer = get_asset_optimizer()
    return optimizer.get_critical_css(page_type)

def get_resource_hints(page_type: str = 'landing') -> Dict[str, List]:
    """
    Get resource hints for a page type.
    
    Args:
        page_type: Type of page
    
    Returns:
        Dictionary with resource hints
    """
    optimizer = get_asset_optimizer()
    return optimizer.get_resource_hints(page_type)

def get_versioned_asset_url(asset_path: str) -> str:
    """
    Get versioned URL for an asset.
    
    Args:
        asset_path: Path to the asset
    
    Returns:
        Versioned asset URL
    """
    optimizer = get_asset_optimizer()
    return optimizer.get_versioned_asset_url(asset_path)