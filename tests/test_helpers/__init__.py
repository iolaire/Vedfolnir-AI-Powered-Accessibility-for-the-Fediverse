# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Helpers Package

This package contains utilities and helpers for testing the Alt Text Bot application.
Includes standardized mock configurations, async helpers, database mocks, and platform-specific mocks.
"""

# Mock User Helper (existing)
from .mock_user_helper import (
    MockUserHelper,
    create_test_user_with_platforms,
    cleanup_test_user,
    TEST_USER_DEFAULTS,
    TEST_PLATFORM_DEFAULTS
)

# Standardized Mock Configurations
from .mock_configurations import (
    StandardizedMockFactory,
    MockConfiguration,
    MockConfigurationPresets,
    create_mock_with_unpacking,
    create_async_context_manager_mock,
    patch_database_session,
    patch_async_http_client
)

# Async Mock Helpers
from .async_mock_helpers import (
    AsyncMockHelper,
    AsyncTestHelper,
    mock_async_http_success,
    mock_async_http_error,
    mock_async_connection_error,
    patch_httpx_client,
    patch_ollama_client
)

# Database Mock Helpers
from .database_mock_helpers import (
    DatabaseMockHelper,
    QueryMockBuilder,
    create_user_query_mock,
    create_platform_query_mock,
    create_task_query_mock,
    patch_database_manager,
    patch_session_scope
)

# Platform Mock Helpers
from .platform_mock_helpers import (
    PlatformMockHelper,
    PlatformTestDataFactory,
    create_pixelfed_test_setup,
    create_mastodon_test_setup,
    create_multi_platform_test_setup,
    patch_platform_context_manager,
    patch_activitypub_client
)

__all__ = [
    # Mock User Helper
    'MockUserHelper',
    'create_test_user_with_platforms', 
    'cleanup_test_user',
    'TEST_USER_DEFAULTS',
    'TEST_PLATFORM_DEFAULTS',
    
    # Standardized Mock Configurations
    'StandardizedMockFactory',
    'MockConfiguration',
    'MockConfigurationPresets',
    'create_mock_with_unpacking',
    'create_async_context_manager_mock',
    'patch_database_session',
    'patch_async_http_client',
    
    # Async Mock Helpers
    'AsyncMockHelper',
    'AsyncTestHelper',
    'mock_async_http_success',
    'mock_async_http_error',
    'mock_async_connection_error',
    'patch_httpx_client',
    'patch_ollama_client',
    
    # Database Mock Helpers
    'DatabaseMockHelper',
    'QueryMockBuilder',
    'create_user_query_mock',
    'create_platform_query_mock',
    'create_task_query_mock',
    'patch_database_manager',
    'patch_session_scope',
    
    # Platform Mock Helpers
    'PlatformMockHelper',
    'PlatformTestDataFactory',
    'create_pixelfed_test_setup',
    'create_mastodon_test_setup',
    'create_multi_platform_test_setup',
    'patch_platform_context_manager',
    'patch_activitypub_client'
]