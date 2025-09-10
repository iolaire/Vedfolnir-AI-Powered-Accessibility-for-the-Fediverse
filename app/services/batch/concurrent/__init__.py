# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Batch Concurrent Operations Module

This module provides concurrent operation management for batch processing,
including distributed locking, operation tracking, and conflict resolution.
"""

from .concurrent_operation_manager import (
    ConcurrentOperationManager,
    OperationType,
    LockScope,
    OperationLock,
    with_operation_lock,
    initialize_concurrent_operation_manager,
    get_concurrent_operation_manager
)

__all__ = [
    'ConcurrentOperationManager',
    'OperationType', 
    'LockScope',
    'OperationLock',
    'with_operation_lock',
    'initialize_concurrent_operation_manager',
    'get_concurrent_operation_manager'
]