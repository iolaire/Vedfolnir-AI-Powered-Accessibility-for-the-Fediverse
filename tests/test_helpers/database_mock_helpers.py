# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Database Mock Helpers for Testing

This module provides specialized helpers for creating and configuring database mocks
to address common issues with database query chains and session management in tests.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from models import User, PlatformConnection, CaptionGenerationTask, TaskStatus, UserRole


class DatabaseMockHelper:
    """Helper class for creating and configuring database mocks"""
    
    @staticmethod
    def create_query_chain_mock(final_result: Any = None,
                               supports_all_methods: bool = True) -> Mock:
        """
        Create a mock that supports SQLAlchemy query method chaining.
        
        Args:
            final_result: The final result to return from terminal methods
            supports_all_methods: Whether to support all query methods
            
        Returns:
            Mock configured for query chaining
        """
        # Create the main query mock
        query_mock = Mock()
        
        # Create intermediate mocks for chaining
        intermediate_mock = Mock()
        
        # Configure all query methods to return the intermediate mock for chaining
        query_methods = [
            'filter', 'filter_by', 'join', 'outerjoin', 'order_by', 
            'group_by', 'having', 'limit', 'offset', 'distinct'
        ]
        
        for method in query_methods:
            setattr(query_mock, method, Mock(return_value=intermediate_mock))
            setattr(intermediate_mock, method, Mock(return_value=intermediate_mock))
        
        # Configure terminal methods
        terminal_methods = {
            'first': final_result,
            'one': final_result,
            'one_or_none': final_result,
            'scalar': final_result if not isinstance(final_result, list) else (final_result[0] if final_result else None),
            'all': final_result if isinstance(final_result, list) else ([final_result] if final_result else []),
            'count': len(final_result) if isinstance(final_result, list) else (1 if final_result else 0)
        }
        
        for method, return_value in terminal_methods.items():
            setattr(query_mock, method, Mock(return_value=return_value))
            setattr(intermediate_mock, method, Mock(return_value=return_value))
        
        return query_mock
    
    @staticmethod
    def create_session_mock(query_results: Optional[Dict[str, Any]] = None,
                           auto_commit: bool = True,
                           raise_on_error: bool = False) -> Mock:
        """
        Create a mock database session.
        
        Args:
            query_results: Dictionary mapping model names to query results
            auto_commit: Whether to automatically handle commits
            raise_on_error: Whether to raise exceptions on operations
            
        Returns:
            Mock configured as database session
        """
        session_mock = Mock()
        
        # Configure basic session methods
        session_mock.add = Mock()
        session_mock.delete = Mock()
        session_mock.commit = Mock()
        session_mock.rollback = Mock()
        session_mock.flush = Mock()
        session_mock.refresh = Mock()
        session_mock.expunge = Mock()
        session_mock.close = Mock()
        session_mock.get = Mock()
        
        # Configure context manager support
        session_mock.__enter__ = Mock(return_value=session_mock)
        session_mock.__exit__ = Mock(return_value=None)
        
        # Configure query method
        if query_results:
            def query_side_effect(model):
                model_name = model.__name__ if hasattr(model, '__name__') else str(model)
                result = query_results.get(model_name, None)
                return DatabaseMockHelper.create_query_chain_mock(result)
            
            session_mock.query.side_effect = query_side_effect
        else:
            session_mock.query.return_value = DatabaseMockHelper.create_query_chain_mock()
        
        # Configure error handling
        if raise_on_error:
            from sqlalchemy.exc import SQLAlchemyError
            session_mock.commit.side_effect = SQLAlchemyError("Mock database error")
        
        return session_mock
    
    @staticmethod
    def create_database_manager_mock(session_mock: Optional[Mock] = None) -> Mock:
        """
        Create a mock database manager.
        
        Args:
            session_mock: Optional session mock to use
            
        Returns:
            Mock configured as database manager
        """
        db_manager_mock = Mock()
        
        if session_mock is None:
            session_mock = DatabaseMockHelper.create_session_mock()
        
        db_manager_mock.get_session.return_value = session_mock
        db_manager_mock.session_scope.return_value.__enter__ = Mock(return_value=session_mock)
        db_manager_mock.session_scope.return_value.__exit__ = Mock(return_value=None)
        
        return db_manager_mock
    
    @staticmethod
    def create_model_mock(model_class: type,
                         **attributes) -> Mock:
        """
        Create a mock model instance.
        
        Args:
            model_class: The model class to mock
            **attributes: Attributes to set on the mock
            
        Returns:
            Mock configured as model instance
        """
        model_mock = Mock(spec=model_class)
        
        # Set default attributes based on model type
        if model_class == User:
            defaults = {
                'id': 1,
                'username': 'testuser',
                'email': 'test@example.com',
                'role': UserRole.REVIEWER,
                'is_active': True,
                'created_at': datetime.now(timezone.utc),
                'platform_connections': [],
                'sessions': []
            }
        elif model_class == PlatformConnection:
            defaults = {
                'id': 1,
                'user_id': 1,
                'name': 'Test Platform',
                'platform_type': 'pixelfed',
                'instance_url': 'https://test.example.com',
                'username': 'testuser',
                'is_active': True,
                'is_default': True,
                'created_at': datetime.now(timezone.utc)
            }
        elif model_class == CaptionGenerationTask:
            defaults = {
                'id': 'test-task-id',
                'user_id': 1,
                'platform_connection_id': 1,
                'status': TaskStatus.QUEUED,
                'created_at': datetime.now(timezone.utc),
                'started_at': None,
                'completed_at': None,
                'error_message': None
            }
        else:
            defaults = {}
        
        # Apply defaults and overrides
        for key, value in {**defaults, **attributes}.items():
            setattr(model_mock, key, value)
        
        return model_mock


class QueryMockBuilder:
    """Builder class for creating complex query mocks"""
    
    def __init__(self):
        self.query_mock = Mock()
        self.current_mock = self.query_mock
        self.final_result = None
    
    def filter(self, result: Any = None) -> 'QueryMockBuilder':
        """Add filter method to the chain"""
        filter_mock = Mock()
        self.current_mock.filter.return_value = filter_mock
        self.current_mock = filter_mock
        if result is not None:
            self.final_result = result
        return self
    
    def filter_by(self, result: Any = None) -> 'QueryMockBuilder':
        """Add filter_by method to the chain"""
        filter_by_mock = Mock()
        self.current_mock.filter_by.return_value = filter_by_mock
        self.current_mock = filter_by_mock
        if result is not None:
            self.final_result = result
        return self
    
    def join(self, result: Any = None) -> 'QueryMockBuilder':
        """Add join method to the chain"""
        join_mock = Mock()
        self.current_mock.join.return_value = join_mock
        self.current_mock = join_mock
        if result is not None:
            self.final_result = result
        return self
    
    def order_by(self, result: Any = None) -> 'QueryMockBuilder':
        """Add order_by method to the chain"""
        order_by_mock = Mock()
        self.current_mock.order_by.return_value = order_by_mock
        self.current_mock = order_by_mock
        if result is not None:
            self.final_result = result
        return self
    
    def limit(self, result: Any = None) -> 'QueryMockBuilder':
        """Add limit method to the chain"""
        limit_mock = Mock()
        self.current_mock.limit.return_value = limit_mock
        self.current_mock = limit_mock
        if result is not None:
            self.final_result = result
        return self
    
    def first(self, result: Any = None) -> Mock:
        """Set the first() method result and return the query mock"""
        final_result = result if result is not None else self.final_result
        self.current_mock.first.return_value = final_result
        # Also set first() on the original query mock for direct calls
        self.query_mock.first.return_value = final_result
        return self.query_mock
    
    def all(self, result: List[Any] = None) -> Mock:
        """Set the all() method result and return the query mock"""
        if result is None:
            result = [self.final_result] if self.final_result else []
        self.current_mock.all.return_value = result
        # Also set all() on the original query mock for direct calls
        self.query_mock.all.return_value = result
        return self.query_mock
    
    def count(self, result: int = None) -> Mock:
        """Set the count() method result and return the query mock"""
        if result is None:
            if isinstance(self.final_result, list):
                result = len(self.final_result)
            else:
                result = 1 if self.final_result else 0
        self.current_mock.count.return_value = result
        # Also set count() on the original query mock for direct calls
        self.query_mock.count.return_value = result
        return self.query_mock


# Convenience functions for common database mock patterns
def create_user_query_mock(users: Union[User, List[User], None] = None) -> Mock:
    """Create a query mock for User model queries"""
    if users is None:
        users = []
    elif not isinstance(users, list):
        users = [users]
    
    return DatabaseMockHelper.create_query_chain_mock(users)


def create_platform_query_mock(platforms: Union[PlatformConnection, List[PlatformConnection], None] = None) -> Mock:
    """Create a query mock for PlatformConnection model queries"""
    if platforms is None:
        platforms = []
    elif not isinstance(platforms, list):
        platforms = [platforms]
    
    return DatabaseMockHelper.create_query_chain_mock(platforms)


def create_task_query_mock(tasks: Union[CaptionGenerationTask, List[CaptionGenerationTask], None] = None) -> Mock:
    """Create a query mock for CaptionGenerationTask model queries"""
    if tasks is None:
        tasks = []
    elif not isinstance(tasks, list):
        tasks = [tasks]
    
    return DatabaseMockHelper.create_query_chain_mock(tasks)


def patch_database_manager(session_mock: Optional[Mock] = None) -> patch:
    """Create a patch for DatabaseManager with standardized configuration"""
    if session_mock is None:
        session_mock = DatabaseMockHelper.create_session_mock()
    
    db_manager_mock = DatabaseMockHelper.create_database_manager_mock(session_mock)
    return patch('database.DatabaseManager', return_value=db_manager_mock)


def patch_session_scope(session_mock: Optional[Mock] = None) -> patch:
    """Create a patch for session_scope context manager"""
    if session_mock is None:
        session_mock = DatabaseMockHelper.create_session_mock()
    
    context_mock = Mock()
    context_mock.__enter__ = Mock(return_value=session_mock)
    context_mock.__exit__ = Mock(return_value=None)
    
    return patch('database.DatabaseManager.session_scope', return_value=context_mock)