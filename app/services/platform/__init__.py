# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Consolidated Platform Framework

This module provides the single consolidated platform framework for all platform-related functionality.
All platform operations should use this framework to ensure consistency and avoid duplication.
"""

# Core platform components
from .components.platform_identification import (
    PlatformIdentificationResult,
    PlatformObj,
    identify_user_platform,
    require_platform_selection,
    get_platform_redirect_message
)

# from .components.platform_health import PlatformHealthMonitor  # Import on demand to avoid circular dependencies
from .components.platform_service import PlatformService

# Platform detection
from .detection.detect_platform import detect_platform_type

# Platform adapters - Import on demand to avoid circular dependencies
# from .adapters.platform_aware_caption_adapter import PlatformAwareCaptionAdapter

# Platform utilities - Import on demand to avoid circular dependencies  
# from .utils.platform_context_utils import (
#     get_platform_context,
#     update_platform_context,
#     clear_platform_context
# )

__all__ = [
    # Platform identification
    'PlatformIdentificationResult',
    'PlatformObj',
    'identify_user_platform', 
    'require_platform_selection',
    'get_platform_redirect_message',
    
    # Platform services
    # 'PlatformHealthMonitor',  # Available via direct import
    'PlatformService',
    
    # Platform detection
    'detect_platform_type',
    
    # Platform adapters - Available via direct import
    # 'PlatformAwareCaptionAdapter',
    
    # Platform utilities - Available via direct import
    # 'get_platform_context',
    # 'update_platform_context', 
    # 'clear_platform_context'
]