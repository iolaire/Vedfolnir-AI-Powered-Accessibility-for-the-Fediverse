# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Test thread safety of PlatformContextManager

This module tests that the PlatformContextManager correctly handles
concurrent operations from multiple threads without context interference.
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from platform_context import PlatformContextManager, PlatformContext, PlatformContextError
from models import User, PlatformConnection

class TestPlatformContextThreadSafety(unittest.TestCase):
    """Test thread safety of PlatformContextManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.session = Mock(spec=Session)
        self.context_manager = PlatformContextManager(self.session)
        
        # Create mock users
        self.user1 = Mock(spec=User)
        self.user1.id = 1
        self.user1.username = "user1"
        self.user1.is_active = True
        
        self.user2 = Mock(spec=User)
        self.user2.id = 2
        self.user2.username = "user2"
        self.user2.is_active = True
        
        # Create mock platform connections
        self.platform1 = Mock(spec=PlatformConnection)
        self.platform1.id = 1
        self.platform1.name = "Platform 1"
        self.platform1.platform_type = "pixelfed"
        self.platform1.instance_url = "https://pixelfed1.example.com"
        self.platform1.username = "user1"
        self.platform1.is_active = True
        self.platform1.is_default = True
        
        self.platform2 = Mock(spec=PlatformConnection)
        self.platform2.id = 2
        self.platform2.name = "Platform 2"
        self.platform2.platform_type = "mastodon"
        self.platform2.instance_url = "https://mastodon2.example.com"
        self.platform2.username = "user2"
        self.platform2.is_active = True
        self.platform2.is_default = True
        
        # Configure user methods
        self.user1.get_default_platform.return_value = self.platform1
        self.user1.get_active_platforms.return_value = [self.platform1]
        
        self.user2.get_default_platform.return_value = self.platform2
        self.user2.get_active_platforms.return_value = [self.platform2]
    
    def test_concurrent_context_setting(self):
        """Test that multiple threads can set context concurrently without interference"""
        results = {}
        errors = {}
        
        def set_context_thread(user_id, platform_id, thread_name):
            """Thread function to set context"""
            try:
                # Mock database queries for this thread
                if user_id == 1:
                    self.session.query.return_value.get.return_value = self.user1
                    self.session.query.return_value.filter_by.return_value.first.return_value = self.platform1
                else:
                    self.session.query.return_value.get.return_value = self.user2
                    self.session.query.return_value.filter_by.return_value.first.return_value = self.platform2
                
                # Set context
                context = self.context_manager.set_context(user_id, platform_id)
                
                # Verify context is correct for this thread
                current_context = self.context_manager.current_context
                
                results[thread_name] = {
                    'user_id': current_context.user_id,
                    'platform_id': current_context.platform_connection_id,
                    'user_name': current_context.user.username,
                    'platform_name': current_context.platform_connection.name
                }
                
                # Sleep to allow other threads to potentially interfere
                time.sleep(0.1)
                
                # Verify context is still correct after sleep
                current_context = self.context_manager.current_context
                if (current_context.user_id != user_id or 
                    current_context.platform_connection_id != platform_id):
                    errors[thread_name] = "Context was modified by another thread"
                
            except Exception as e:
                errors[thread_name] = str(e)
        
        # Create and start multiple threads
        threads = []
        for i in range(5):
            # Alternate between user1 and user2
            user_id = 1 if i % 2 == 0 else 2
            platform_id = 1 if i % 2 == 0 else 2
            thread_name = f"thread_{i}"
            
            thread = threading.Thread(
                target=set_context_thread,
                args=(user_id, platform_id, thread_name)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
        
        # Verify each thread got the correct context
        self.assertEqual(len(results), 5)
        for thread_name, result in results.items():
            thread_num = int(thread_name.split('_')[1])
            expected_user_id = 1 if thread_num % 2 == 0 else 2
            expected_platform_id = 1 if thread_num % 2 == 0 else 2
            
            self.assertEqual(result['user_id'], expected_user_id)
            self.assertEqual(result['platform_id'], expected_platform_id)
    
    def test_context_isolation_between_threads(self):
        """Test that context in one thread doesn't affect context in another thread"""
        context1_set = threading.Event()
        context2_set = threading.Event()
        verification_complete = threading.Event()
        
        results = {}
        
        def thread1_function():
            """Thread 1: Set context for user1/platform1"""
            try:
                self.session.query.return_value.get.return_value = self.user1
                self.session.query.return_value.filter_by.return_value.first.return_value = self.platform1
                
                # Set context
                self.context_manager.set_context(1, 1)
                context1_set.set()
                
                # Wait for thread2 to set its context
                context2_set.wait(timeout=5)
                
                # Verify our context is still correct
                current_context = self.context_manager.current_context
                results['thread1'] = {
                    'user_id': current_context.user_id,
                    'platform_id': current_context.platform_connection_id,
                    'user_name': current_context.user.username
                }
                
                verification_complete.set()
                
            except Exception as e:
                results['thread1_error'] = str(e)
                context1_set.set()
                verification_complete.set()
        
        def thread2_function():
            """Thread 2: Set context for user2/platform2"""
            try:
                # Wait for thread1 to set its context
                context1_set.wait(timeout=5)
                
                self.session.query.return_value.get.return_value = self.user2
                self.session.query.return_value.filter_by.return_value.first.return_value = self.platform2
                
                # Set context
                self.context_manager.set_context(2, 2)
                context2_set.set()
                
                # Wait for thread1 to verify its context
                verification_complete.wait(timeout=5)
                
                # Verify our context is correct
                current_context = self.context_manager.current_context
                results['thread2'] = {
                    'user_id': current_context.user_id,
                    'platform_id': current_context.platform_connection_id,
                    'user_name': current_context.user.username
                }
                
            except Exception as e:
                results['thread2_error'] = str(e)
                context2_set.set()
        
        # Start both threads
        thread1 = threading.Thread(target=thread1_function)
        thread2 = threading.Thread(target=thread2_function)
        
        thread1.start()
        thread2.start()
        
        # Wait for completion
        thread1.join(timeout=10)
        thread2.join(timeout=10)
        
        # Verify results
        self.assertNotIn('thread1_error', results, f"Thread 1 error: {results.get('thread1_error')}")
        self.assertNotIn('thread2_error', results, f"Thread 2 error: {results.get('thread2_error')}")
        
        # Verify each thread maintained its own context
        self.assertEqual(results['thread1']['user_id'], 1)
        self.assertEqual(results['thread1']['platform_id'], 1)
        self.assertEqual(results['thread1']['user_name'], 'user1')
        
        self.assertEqual(results['thread2']['user_id'], 2)
        self.assertEqual(results['thread2']['platform_id'], 2)
        self.assertEqual(results['thread2']['user_name'], 'user2')
    
    def test_context_scope_thread_safety(self):
        """Test that context_scope works correctly in multi-threaded environment"""
        results = {}
        
        def thread_with_context_scope(user_id, platform_id, thread_name):
            """Thread function using context_scope"""
            try:
                # Mock database queries
                if user_id == 1:
                    self.session.query.return_value.get.return_value = self.user1
                    self.session.query.return_value.filter_by.return_value.first.return_value = self.platform1
                else:
                    self.session.query.return_value.get.return_value = self.user2
                    self.session.query.return_value.filter_by.return_value.first.return_value = self.platform2
                
                # Use context scope
                with self.context_manager.context_scope(user_id, platform_id) as context:
                    results[f"{thread_name}_inside"] = {
                        'user_id': context.user_id,
                        'platform_id': context.platform_connection_id
                    }
                    
                    # Sleep to allow potential interference
                    time.sleep(0.1)
                    
                    # Verify context is still correct
                    current_context = self.context_manager.current_context
                    if (current_context.user_id != user_id or 
                        current_context.platform_connection_id != platform_id):
                        results[f"{thread_name}_error"] = "Context changed during scope"
                
                # Verify context is cleared after scope
                current_context = self.context_manager.current_context
                results[f"{thread_name}_after"] = current_context is None
                
            except Exception as e:
                results[f"{thread_name}_error"] = str(e)
        
        # Create multiple threads using context_scope
        threads = []
        for i in range(3):
            user_id = 1 if i % 2 == 0 else 2
            platform_id = 1 if i % 2 == 0 else 2
            thread_name = f"scope_thread_{i}"
            
            thread = threading.Thread(
                target=thread_with_context_scope,
                args=(user_id, platform_id, thread_name)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors
        error_keys = [k for k in results.keys() if k.endswith('_error')]
        self.assertEqual(len(error_keys), 0, f"Context scope errors: {[results[k] for k in error_keys]}")
        
        # Verify each thread had correct context inside scope
        for i in range(3):
            thread_name = f"scope_thread_{i}"
            expected_user_id = 1 if i % 2 == 0 else 2
            expected_platform_id = 1 if i % 2 == 0 else 2
            
            inside_result = results[f"{thread_name}_inside"]
            self.assertEqual(inside_result['user_id'], expected_user_id)
            self.assertEqual(inside_result['platform_id'], expected_platform_id)
            
            # Verify context was cleared after scope
            self.assertTrue(results[f"{thread_name}_after"])
    
    def test_concurrent_platform_operations(self):
        """Test concurrent platform operations don't interfere with each other"""
        results = {}
        
        def platform_operations_thread(user_id, platform_id, thread_name):
            """Thread performing various platform operations"""
            try:
                # Mock database queries
                if user_id == 1:
                    self.session.query.return_value.get.return_value = self.user1
                    self.session.query.return_value.filter_by.return_value.first.return_value = self.platform1
                    expected_platform = self.platform1
                else:
                    self.session.query.return_value.get.return_value = self.user2
                    self.session.query.return_value.filter_by.return_value.first.return_value = self.platform2
                    expected_platform = self.platform2
                
                # Set context
                self.context_manager.set_context(user_id, platform_id)
                
                # Perform various operations
                context_info = self.context_manager.get_context_info()
                validation_errors = self.context_manager.validate_context()
                
                # Mock platform filtering
                from models import Post
                mock_query = Mock()
                filtered_query = self.context_manager.apply_platform_filter(mock_query, Post)
                
                # Mock data injection
                test_data = {'test_field': 'test_value'}
                injected_data = self.context_manager.inject_platform_data(test_data)
                
                results[thread_name] = {
                    'context_info': context_info,
                    'validation_errors': validation_errors,
                    'injected_platform_id': injected_data.get('platform_connection_id'),
                    'injected_platform_type': injected_data.get('platform_type'),
                    'expected_platform_id': platform_id,
                    'expected_platform_type': expected_platform.platform_type
                }
                
            except Exception as e:
                results[f"{thread_name}_error"] = str(e)
        
        # Create multiple threads performing operations
        threads = []
        for i in range(4):
            user_id = 1 if i % 2 == 0 else 2
            platform_id = 1 if i % 2 == 0 else 2
            thread_name = f"ops_thread_{i}"
            
            thread = threading.Thread(
                target=platform_operations_thread,
                args=(user_id, platform_id, thread_name)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors
        error_keys = [k for k in results.keys() if k.endswith('_error')]
        self.assertEqual(len(error_keys), 0, f"Operation errors: {[results[k] for k in error_keys]}")
        
        # Verify each thread got correct results
        for i in range(4):
            thread_name = f"ops_thread_{i}"
            result = results[thread_name]
            
            # Verify context info is correct
            self.assertTrue(result['context_info']['has_context'])
            self.assertTrue(result['context_info']['is_valid'])
            
            # Verify no validation errors
            self.assertEqual(len(result['validation_errors']), 0)
            
            # Verify data injection used correct platform
            self.assertEqual(result['injected_platform_id'], result['expected_platform_id'])
            self.assertEqual(result['injected_platform_type'], result['expected_platform_type'])

if __name__ == '__main__':
    unittest.main()