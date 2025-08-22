# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Async Mock Helpers for Testing

This module provides specialized helpers for creating and configuring async mocks
to address common issues with async operations in tests.
"""

import asyncio
from typing import Any, Callable, List, Optional, Union
from unittest.mock import AsyncMock, Mock, patch
import httpx

class AsyncMockHelper:
    """Helper class for creating and configuring async mocks"""
    
    @staticmethod
    def create_async_http_response(status_code: int = 200,
                                  json_data: Optional[dict] = None,
                                  text_data: Optional[str] = None,
                                  headers: Optional[dict] = None) -> AsyncMock:
        """
        Create a mock HTTP response for async HTTP clients.
        
        Args:
            status_code: HTTP status code
            json_data: JSON response data
            text_data: Text response data
            headers: Response headers
            
        Returns:
            AsyncMock configured as HTTP response
        """
        response_mock = AsyncMock()
        response_mock.status_code = status_code
        response_mock.headers = headers or {}
        
        # Configure async methods
        response_mock.raise_for_status = AsyncMock()
        
        if json_data is not None:
            response_mock.json = AsyncMock(return_value=json_data)
        
        if text_data is not None:
            response_mock.text = AsyncMock(return_value=text_data)
        
        # Configure status checking
        if status_code >= 400:
            response_mock.raise_for_status.side_effect = httpx.HTTPStatusError(
                f"HTTP {status_code}", request=Mock(), response=response_mock
            )
        
        return response_mock
    
    @staticmethod
    def create_async_http_client(responses: Optional[List[AsyncMock]] = None,
                               side_effects: Optional[List[Union[Exception, AsyncMock]]] = None) -> AsyncMock:
        """
        Create a mock async HTTP client.
        
        Args:
            responses: List of response mocks to return
            side_effects: List of side effects (exceptions or responses)
            
        Returns:
            AsyncMock configured as HTTP client
        """
        client_mock = AsyncMock()
        
        # Configure context manager
        client_mock.__aenter__ = AsyncMock(return_value=client_mock)
        client_mock.__aexit__ = AsyncMock(return_value=None)
        
        # Configure HTTP methods
        for method in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
            method_mock = AsyncMock()
            
            if responses:
                if len(responses) == 1:
                    method_mock.return_value = responses[0]
                else:
                    method_mock.side_effect = responses
            
            if side_effects:
                method_mock.side_effect = side_effects
            
            setattr(client_mock, method, method_mock)
        
        return client_mock
    
    @staticmethod
    def create_ollama_api_mock(success: bool = True,
                              model_name: str = 'llava',
                              response_text: str = 'Test caption') -> AsyncMock:
        """
        Create a mock for Ollama API interactions.
        
        Args:
            success: Whether to simulate successful responses
            model_name: Name of the model to simulate
            response_text: Text response from the model
            
        Returns:
            AsyncMock configured for Ollama API
        """
        if success:
            # Mock successful model list response
            models_response = AsyncMockHelper.create_async_http_response(
                status_code=200,
                json_data={
                    "models": [
                        {"name": model_name, "size": 123456789}
                    ]
                }
            )
            
            # Mock successful generation response
            generate_response = AsyncMockHelper.create_async_http_response(
                status_code=200,
                json_data={
                    "model": model_name,
                    "response": response_text,
                    "eval_count": 100,
                    "eval_duration": 1000000000
                }
            )
            
            client_mock = AsyncMockHelper.create_async_http_client()
            client_mock.get.return_value = models_response
            client_mock.post.return_value = generate_response
            
        else:
            # Mock failed responses
            client_mock = AsyncMockHelper.create_async_http_client()
            client_mock.get.side_effect = httpx.ConnectError("Connection refused")
            client_mock.post.side_effect = httpx.ConnectError("Connection refused")
        
        return client_mock
    
    @staticmethod
    def create_mastodon_api_mock(success: bool = True) -> AsyncMock:
        """
        Create a mock for Mastodon API interactions.
        
        Args:
            success: Whether to simulate successful responses
            
        Returns:
            AsyncMock configured for Mastodon API
        """
        api_mock = AsyncMock()
        
        if success:
            # Mock successful credential verification
            api_mock.account_verify_credentials = AsyncMock(return_value={
                'id': '123',
                'username': 'testuser',
                'display_name': 'Test User'
            })
            
            # Mock successful media update
            api_mock.media_update = AsyncMock(return_value={
                'id': '456',
                'description': 'Updated description'
            })
            
            # Mock successful timeline fetch
            api_mock.timeline_home = AsyncMock(return_value=[
                {
                    'id': '789',
                    'content': 'Test post',
                    'media_attachments': [
                        {'id': '456', 'description': None}
                    ]
                }
            ])
        else:
            # Mock failed responses
            from mastodon import MastodonAPIError
            api_mock.account_verify_credentials.side_effect = MastodonAPIError("API Error")
            api_mock.media_update.side_effect = MastodonAPIError("API Error")
            api_mock.timeline_home.side_effect = MastodonAPIError("API Error")
        
        return api_mock
    
    @staticmethod
    def create_pixelfed_api_mock(success: bool = True) -> AsyncMock:
        """
        Create a mock for Pixelfed API interactions.
        
        Args:
            success: Whether to simulate successful responses
            
        Returns:
            AsyncMock configured for Pixelfed API
        """
        if success:
            # Mock successful responses
            verify_response = AsyncMockHelper.create_async_http_response(
                status_code=200,
                json_data={
                    'id': '123',
                    'username': 'testuser',
                    'display_name': 'Test User'
                }
            )
            
            posts_response = AsyncMockHelper.create_async_http_response(
                status_code=200,
                json_data={
                    'data': [
                        {
                            'id': '789',
                            'content': 'Test post',
                            'media_attachments': [
                                {'id': '456', 'description': None}
                            ]
                        }
                    ]
                }
            )
            
            update_response = AsyncMockHelper.create_async_http_response(
                status_code=200,
                json_data={'success': True}
            )
            
            client_mock = AsyncMockHelper.create_async_http_client()
            
            # Configure specific endpoints
            def get_side_effect(url, **kwargs):
                if 'verify_credentials' in url:
                    return verify_response
                elif 'statuses' in url:
                    return posts_response
                else:
                    return AsyncMockHelper.create_async_http_response()
            
            def put_side_effect(url, **kwargs):
                if 'media' in url:
                    return update_response
                else:
                    return AsyncMockHelper.create_async_http_response()
            
            client_mock.get.side_effect = get_side_effect
            client_mock.put.side_effect = put_side_effect
            
        else:
            # Mock failed responses
            client_mock = AsyncMockHelper.create_async_http_client()
            client_mock.get.side_effect = httpx.HTTPStatusError(
                "HTTP 401", request=Mock(), response=Mock()
            )
            client_mock.put.side_effect = httpx.HTTPStatusError(
                "HTTP 401", request=Mock(), response=Mock()
            )
        
        return client_mock

class AsyncTestHelper:
    """Helper class for running async tests"""
    
    @staticmethod
    def run_async_test(async_func: Callable, *args, **kwargs) -> Any:
        """
        Run an async function in a test context.
        
        Args:
            async_func: Async function to run
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the async function
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    
    @staticmethod
    def create_async_test_decorator(func: Callable) -> Callable:
        """
        Create a decorator to run async test methods.
        
        Args:
            func: Async test method
            
        Returns:
            Decorated sync test method
        """
        def wrapper(self, *args, **kwargs):
            return AsyncTestHelper.run_async_test(func, self, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

# Convenience functions for common async mock patterns
def mock_async_http_success(json_data: dict) -> AsyncMock:
    """Create a successful async HTTP response mock"""
    return AsyncMockHelper.create_async_http_response(
        status_code=200,
        json_data=json_data
    )

def mock_async_http_error(status_code: int = 500, error_message: str = "Server Error") -> AsyncMock:
    """Create a failed async HTTP response mock"""
    return AsyncMockHelper.create_async_http_response(
        status_code=status_code,
        json_data={'error': error_message}
    )

def mock_async_connection_error() -> Exception:
    """Create a connection error for async HTTP mocks"""
    return httpx.ConnectError("Connection refused")

def patch_httpx_client(client_mock: AsyncMock) -> patch:
    """Create a patch for httpx.AsyncClient"""
    return patch('httpx.AsyncClient', return_value=client_mock)

def patch_ollama_client(success: bool = True, response_text: str = 'Test caption') -> patch:
    """Create a patch for Ollama client with standardized responses"""
    client_mock = AsyncMockHelper.create_ollama_api_mock(
        success=success,
        response_text=response_text
    )
    return patch('httpx.AsyncClient', return_value=client_mock)