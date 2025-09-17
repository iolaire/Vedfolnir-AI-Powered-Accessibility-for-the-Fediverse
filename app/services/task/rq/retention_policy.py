# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Retention Policy Data Classes

Defines data structures for RQ retention policies to avoid circular imports.
"""

from dataclasses import dataclass


@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    name: str
    description: str
    completed_tasks_ttl: int  # seconds
    failed_tasks_ttl: int     # seconds
    cancelled_tasks_ttl: int  # seconds
    progress_data_ttl: int    # seconds
    security_logs_ttl: int    # seconds
    max_memory_usage_mb: int  # MB
    cleanup_threshold_mb: int # MB
    cleanup_batch_size: int   # number of items per cleanup batch
    enabled: bool = True