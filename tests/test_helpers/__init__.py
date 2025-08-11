# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Helpers Package

This package contains utilities and helpers for testing the Alt Text Bot application.
"""

from .mock_user_helper import (
    MockUserHelper,
    create_test_user_with_platforms,
    cleanup_test_user,
    TEST_USER_DEFAULTS,
    TEST_PLATFORM_DEFAULTS
)

__all__ = [
    'MockUserHelper',
    'create_test_user_with_platforms', 
    'cleanup_test_user',
    'TEST_USER_DEFAULTS',
    'TEST_PLATFORM_DEFAULTS'
]