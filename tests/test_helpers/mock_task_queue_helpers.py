# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Mock Task Queue Helpers

Standardized mock configurations for task queue manager tests.
"""

from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
import uuid
from typing import Optional, List, Any

from models import CaptionGenerationTask, TaskStatus, CaptionGenerationSettings

class MockTaskQueueHelper:
    """Helper class for creating standardized mock configurations for task queue tests"""
    
    @staticmethod
    def create_mock_task(
        task_id: str = None,
        user_id: int = 1,
        platform_connection_id: int = 1,
        status: TaskStatus = TaskStatus.QUEUED,
        can_be_cancelled: bool = True
    ) -> Mock:
        """
        Create a mock CaptionGenerationTask with proper configuration
        
        Args:
            task_id: Task ID (auto-generated if None)
            user_id: User ID for the task
            platform_connection_id: Platform connection ID
            status: Task status
            can_be_cancelled: Whether task can be cancelled
            
        Returns:
            Mock object configured as a CaptionGenerationTask
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        mock_task = Mock()
        mock_task.id = task_id
        mock_task.user_id = user_id
        mock_task.platform_connection_id = platform_connection_id
        mock_task.status = status
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.started_at = None if status == TaskStatus.QUEUED else datetime.now(timezone.utc)
        mock_task.completed_at = None if status in [TaskStatus.QUEUED, TaskStatus.RUNNING] else datetime.now(timezone.utc)
        mock_task.error_message = None
        mock_task.settings = CaptionGenerationSettings()
        mock_task.can_be_cancelled.return_value = can_be_cancelled
        
        return mock_task
    
    @staticmethod
    def configure_database_query_chain(
        session_mock: Mock,
        return_value: Any = None,
        side_effect: Any = None,
        chain_methods: List[str] = None
    ) -> Mock:
        """
        Configure a database query chain mock
        
        Args:
            session_mock: Mock session object
            return_value: Value to return from the final method
            side_effect: Side effect for the final method
            chain_methods: List of method names in the chain (default: ['query', 'filter_by', 'first'])
            
        Returns:
            The final mock in the chain
        """
        if chain_methods is None:
            chain_methods = ['query', 'filter_by', 'first']
        
        current_mock = session_mock
        mocks = []
        
        for method_name in chain_methods[:-1]:
            next_mock = Mock()
            setattr(current_mock, method_name, Mock(return_value=next_mock))
            mocks.append(next_mock)
            current_mock = next_mock
        
        # Configure the final method
        final_method = chain_methods[-1]
        final_mock = Mock()
        
        if return_value is not None:
            final_mock.return_value = return_value
        if side_effect is not None:
            final_mock.side_effect = side_effect
            
        setattr(current_mock, final_method, final_mock)
        
        return final_mock
    
    @staticmethod
    def configure_count_query(session_mock: Mock, count: int) -> None:
        """
        Configure a query chain that ends with count()
        
        Args:
            session_mock: Mock session object
            count: Count value to return
        """
        MockTaskQueueHelper.configure_database_query_chain(
            session_mock,
            return_value=count,
            chain_methods=['query', 'filter_by', 'count']
        )
    
    @staticmethod
    def configure_find_task_query(session_mock: Mock, task: Optional[Mock] = None) -> None:
        """
        Configure a query chain for finding a single task
        
        Args:
            session_mock: Mock session object
            task: Mock task to return (None for not found)
        """
        MockTaskQueueHelper.configure_database_query_chain(
            session_mock,
            return_value=task,
            chain_methods=['query', 'filter_by', 'first']
        )
    
    @staticmethod
    def configure_find_tasks_with_filter_query(session_mock: Mock, task: Optional[Mock] = None) -> None:
        """
        Configure a query chain for finding tasks with additional filter
        
        Args:
            session_mock: Mock session object
            task: Mock task to return (None for not found)
        """
        MockTaskQueueHelper.configure_database_query_chain(
            session_mock,
            return_value=task,
            chain_methods=['query', 'filter_by', 'filter', 'first']
        )
    
    @staticmethod
    def configure_complex_query_chain(
        session_mock: Mock,
        running_count: int = 0,
        queued_task: Optional[Mock] = None
    ) -> None:
        """
        Configure complex query chain for get_next_task scenarios
        
        Args:
            session_mock: Mock session object
            running_count: Number of running tasks
            queued_task: Mock queued task to return
        """
        # Configure the mock to handle multiple query calls
        query_call_count = 0
        
        def query_side_effect(*args):
            nonlocal query_call_count
            query_call_count += 1
            
            if query_call_count == 1:
                # First call for counting running tasks
                count_query_mock = Mock()
                filter_by_mock = Mock()
                filter_by_mock.count.return_value = running_count
                count_query_mock.filter_by.return_value = filter_by_mock
                return count_query_mock
            else:
                # Second call for finding queued tasks
                task_query_mock = Mock()
                join_mock = Mock()
                filter_mock = Mock()
                order_by_mock = Mock()
                first_mock = Mock()
                
                task_query_mock.join.return_value = join_mock
                join_mock.filter.return_value = filter_mock
                filter_mock.order_by.return_value = order_by_mock
                order_by_mock.first.return_value = queued_task
                
                return task_query_mock
        
        session_mock.query.side_effect = query_side_effect
    
    @staticmethod
    def configure_task_history_query(session_mock: Mock, tasks: List[Mock]) -> None:
        """
        Configure query chain for getting task history
        
        Args:
            session_mock: Mock session object
            tasks: List of mock tasks to return
        """
        MockTaskQueueHelper.configure_database_query_chain(
            session_mock,
            return_value=tasks,
            chain_methods=['query', 'filter_by', 'order_by', 'limit', 'all']
        )
    
    @staticmethod
    def configure_cleanup_query(session_mock: Mock, tasks: List[Mock]) -> None:
        """
        Configure query chain for cleanup operations
        
        Args:
            session_mock: Mock session object
            tasks: List of mock tasks to return for cleanup
        """
        MockTaskQueueHelper.configure_database_query_chain(
            session_mock,
            return_value=tasks,
            chain_methods=['query', 'filter', 'all']
        )
    
    @staticmethod
    def configure_stats_query(session_mock: Mock, status_counts: dict) -> None:
        """
        Configure query chain for getting queue statistics
        
        Args:
            session_mock: Mock session object
            status_counts: Dictionary mapping status values to counts
        """
        def count_side_effect(*args, **kwargs):
            # Extract status from filter_by call
            if 'status' in kwargs:
                status = kwargs['status']
                return status_counts.get(status.value, 0)
            return 0
        
        query_mock = Mock()
        filter_by_mock = Mock()
        filter_by_mock.count.side_effect = count_side_effect
        query_mock.filter_by.return_value = filter_by_mock
        session_mock.query.return_value = query_mock

class MockDatabaseErrorHelper:
    """Helper class for testing database error scenarios"""
    
    @staticmethod
    def configure_database_error(session_mock: Mock, error_message: str = "Database connection failed") -> None:
        """
        Configure session mock to raise SQLAlchemyError
        
        Args:
            session_mock: Mock session object
            error_message: Error message for the exception
        """
        from sqlalchemy.exc import SQLAlchemyError
        session_mock.query.side_effect = SQLAlchemyError(error_message)
    
    @staticmethod
    def configure_add_error(session_mock: Mock, error_message: str = "Database connection failed") -> None:
        """
        Configure session mock to raise error on add()
        
        Args:
            session_mock: Mock session object
            error_message: Error message for the exception
        """
        from sqlalchemy.exc import SQLAlchemyError
        session_mock.add.side_effect = SQLAlchemyError(error_message)
    
    @staticmethod
    def configure_commit_error(session_mock: Mock, error_message: str = "Database connection failed") -> None:
        """
        Configure session mock to raise error on commit()
        
        Args:
            session_mock: Mock session object
            error_message: Error message for the exception
        """
        from sqlalchemy.exc import SQLAlchemyError
        session_mock.commit.side_effect = SQLAlchemyError(error_message)

# Convenience functions for common test scenarios
def create_successful_task_mock(task_id: str = "test-task-id", user_id: int = 1) -> Mock:
    """Create a mock task that can be successfully processed"""
    return MockTaskQueueHelper.create_mock_task(
        task_id=task_id,
        user_id=user_id,
        status=TaskStatus.QUEUED,
        can_be_cancelled=True
    )

def create_completed_task_mock(task_id: str = "completed-task-id", user_id: int = 1) -> Mock:
    """Create a mock task that is already completed"""
    return MockTaskQueueHelper.create_mock_task(
        task_id=task_id,
        user_id=user_id,
        status=TaskStatus.COMPLETED,
        can_be_cancelled=False
    )

def create_running_task_mock(task_id: str = "running-task-id", user_id: int = 1) -> Mock:
    """Create a mock task that is currently running"""
    return MockTaskQueueHelper.create_mock_task(
        task_id=task_id,
        user_id=user_id,
        status=TaskStatus.RUNNING,
        can_be_cancelled=True
    )