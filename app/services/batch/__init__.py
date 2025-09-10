# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Batch Processing Framework

This module provides comprehensive batch processing capabilities including
batch update services, concurrent operation management, CLI tools, and
multi-tenant control services.
"""

from .components import BatchUpdateService, MultiTenantControlService
from .concurrent import (
    ConcurrentOperationManager,
    OperationType,
    LockScope,
    OperationLock,
    with_operation_lock,
    initialize_concurrent_operation_manager,
    get_concurrent_operation_manager
)

__all__ = [
    # Components
    'BatchUpdateService',
    'MultiTenantControlService',
    
    # Concurrent Operations
    'ConcurrentOperationManager',
    'OperationType',
    'LockScope', 
    'OperationLock',
    'with_operation_lock',
    'initialize_concurrent_operation_manager',
    'get_concurrent_operation_manager'
]