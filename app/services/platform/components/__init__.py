# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Platform Components Module

This module contains consolidated platform framework components.
"""

from .platform_identification import (
    PlatformIdentificationResult,
    PlatformObj,
    identify_user_platform,
    require_platform_selection,
    get_platform_redirect_message
)

# from .platform_health import PlatformHealthMonitor  # Import on demand to avoid circular dependencies

from .platform_service import PlatformService

__all__ = [
    'PlatformIdentificationResult',
    'PlatformObj', 
    'identify_user_platform',
    'require_platform_selection',
    'get_platform_redirect_message',
    # 'PlatformHealthMonitor',  # Available via direct import
    'PlatformService'
]