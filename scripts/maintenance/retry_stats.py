# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Type, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class RetryStats:
    """Track retry statistics for monitoring and reporting"""
    
    def __init__(self):
        self.total_operations = 0
        self.retried_operations = 0
        self.retry_attempts = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.retry_by_exception: Dict[str, int] = {}
        self.retry_by_status_code: Dict[int, int] = {}
        self.retry_by_function: Dict[str, int] = {}
        self.retry_by_endpoint: Dict[str, int] = {}
        self.total_retry_time = 0.0
        self.max_retry_time = 0.0
        self.min_retry_time = float('inf')
        self.avg_retry_time = 0.0
        self.retry_time_distribution = {
            '0-1s': 0,
            '1-5s': 0,
            '5-15s': 0,
            '15-30s': 0,
            '30s+': 0
        }
        self.consecutive_retries = 0
        self.max_consecutive_retries = 0
        self.retry_timestamps: List[datetime] = []
        self.last_minute_retries = 0
        self.last_five_minute_retries = 0
        self.last_hour_retries = 0
        
    def record_operation(self, retried: bool = False, attempts: int = 1, success: bool = True, 
                        exception_type: Optional[Type[Exception]] = None, status_code: Optional[int] = None, 
                        retry_time: float = 0.0, function_name: Optional[str] = None, 
                        endpoint: Optional[str] = None) -> None:
        """
        Record statistics for an operation
        
        Args:
            retried: Whether the operation was retried
            attempts: Number of attempts made (including the first attempt)
            success: Whether the operation was ultimately successful
            exception_type: Type of exception that triggered retries
            status_code: HTTP status code that triggered retries
            retry_time: Total time spent in retries
            function_name: Name of the function being retried
            endpoint: API endpoint or URL path being accessed
        """
        self.total_operations += 1
        
        if retried:
            self.retried_operations += 1
            retry_count = attempts - 1  # Don't count the first attempt
            self.retry_attempts += retry_count
            self.total_retry_time += retry_time
            
            # Update consecutive retries tracking
            self.consecutive_retries += 1
            self.max_consecutive_retries = max(self.max_consecutive_retries, self.consecutive_retries)
            
            # Record timestamp for rate analysis
            current_time = datetime.now()
            self.retry_timestamps.append(current_time)
            
            # Clean up old timestamps (older than 1 hour)
            one_hour_ago = current_time.timestamp() - 3600
            self.retry_timestamps = [ts for ts in self.retry_timestamps 
                                    if ts.timestamp() > one_hour_ago]
            
            # Calculate time-based metrics
            self.last_minute_retries = sum(1 for ts in self.retry_timestamps 
                                         if (current_time - ts).total_seconds() <= 60)
            self.last_five_minute_retries = sum(1 for ts in self.retry_timestamps 
                                              if (current_time - ts).total_seconds() <= 300)
            self.last_hour_retries = len(self.retry_timestamps)
            
            # Update retry time statistics
            if retry_time > 0:
                self.max_retry_time = max(self.max_retry_time, retry_time)
                self.min_retry_time = min(self.min_retry_time, retry_time)
                self.avg_retry_time = self.total_retry_time / self.retry_attempts
                
                # Update retry time distribution
                if retry_time < 1:
                    self.retry_time_distribution['0-1s'] += 1
                elif retry_time < 5:
                    self.retry_time_distribution['1-5s'] += 1
                elif retry_time < 15:
                    self.retry_time_distribution['5-15s'] += 1
                elif retry_time < 30:
                    self.retry_time_distribution['15-30s'] += 1
                else:
                    self.retry_time_distribution['30s+'] += 1
            
            if success:
                self.successful_retries += 1
            else:
                self.failed_retries += 1
                
            if exception_type:
                exception_name = exception_type.__name__
                self.retry_by_exception[exception_name] = self.retry_by_exception.get(exception_name, 0) + 1
                
            if status_code:
                self.retry_by_status_code[status_code] = self.retry_by_status_code.get(status_code, 0) + 1
                
            if function_name:
                self.retry_by_function[function_name] = self.retry_by_function.get(function_name, 0) + 1
                
            if endpoint:
                self.retry_by_endpoint[endpoint] = self.retry_by_endpoint.get(endpoint, 0) + 1
        else:
            # Reset consecutive retries counter on successful operation without retries
            self.consecutive_retries = 0
    
    def get_summary(self) -> str:
        """
        Get a summary of retry statistics
        
        Returns:
            A formatted string with retry statistics summary
        """
        if self.total_operations == 0:
            return "No operations recorded"
            
        retry_rate = (self.retried_operations / self.total_operations) * 100 if self.total_operations > 0 else 0
        success_rate = (self.successful_retries / self.retried_operations) * 100 if self.retried_operations > 0 else 0
        
        summary = [
            f"=== Retry Statistics Summary ===",
            f"Total operations: {self.total_operations}",
            f"Operations with retries: {self.retried_operations} ({retry_rate:.1f}%)",
            f"Total retry attempts: {self.retry_attempts}",
            f"Successful retries: {self.successful_retries} ({success_rate:.1f}%)",
            f"Failed retries: {self.failed_retries}",
            f"Maximum consecutive retries: {self.max_consecutive_retries}",
            f"",
            f"=== Retry Timing ===",
            f"Total time spent in retries: {self.total_retry_time:.2f}s",
            f"Average retry time: {self.avg_retry_time:.2f}s",
            f"Min/Max retry time: {self.min_retry_time if self.min_retry_time != float('inf') else 0:.2f}s / {self.max_retry_time:.2f}s",
            f"",
            f"=== Recent Activity ===",
            f"Retries in last minute: {self.last_minute_retries}",
            f"Retries in last 5 minutes: {self.last_five_minute_retries}",
            f"Retries in last hour: {self.last_hour_retries}"
        ]
        
        if any(self.retry_time_distribution.values()):
            summary.append("")
            summary.append("=== Retry Time Distribution ===")
            for time_range, count in self.retry_time_distribution.items():
                if count > 0:
                    percentage = (count / self.retry_attempts) * 100 if self.retry_attempts > 0 else 0
                    summary.append(f"  {time_range}: {count} ({percentage:.1f}%)")
        
        if self.retry_by_exception:
            summary.append("")
            summary.append("=== Retries by Exception Type ===")
            for exc_type, count in sorted(self.retry_by_exception.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.retried_operations) * 100 if self.retried_operations > 0 else 0
                summary.append(f"  {exc_type}: {count} ({percentage:.1f}%)")
                
        if self.retry_by_status_code:
            summary.append("")
            summary.append("=== Retries by Status Code ===")
            for status_code, count in sorted(self.retry_by_status_code.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.retried_operations) * 100 if self.retried_operations > 0 else 0
                summary.append(f"  {status_code}: {count} ({percentage:.1f}%)")
                
        if self.retry_by_function:
            summary.append("")
            summary.append("=== Retries by Function ===")
            for func_name, count in sorted(self.retry_by_function.items(), key=lambda x: x[1], reverse=True)[:10]:  # Top 10
                percentage = (count / self.retried_operations) * 100 if self.retried_operations > 0 else 0
                summary.append(f"  {func_name}: {count} ({percentage:.1f}%)")
                
        if self.retry_by_endpoint:
            summary.append("")
            summary.append("=== Retries by Endpoint ===")
            for endpoint, count in sorted(self.retry_by_endpoint.items(), key=lambda x: x[1], reverse=True)[:10]:  # Top 10
                percentage = (count / self.retried_operations) * 100 if self.retried_operations > 0 else 0
                summary.append(f"  {endpoint}: {count} ({percentage:.1f}%)")
                
        return "\n".join(summary)
        
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        Get a detailed report of retry statistics in dictionary format
        
        Returns:
            A dictionary with detailed retry statistics
        """
        return {
            "summary": {
                "total_operations": self.total_operations,
                "retried_operations": self.retried_operations,
                "retry_attempts": self.retry_attempts,
                "successful_retries": self.successful_retries,
                "failed_retries": self.failed_retries,
                "retry_rate": (self.retried_operations / self.total_operations) * 100 if self.total_operations > 0 else 0,
                "success_rate": (self.successful_retries / self.retried_operations) * 100 if self.retried_operations > 0 else 0,
                "max_consecutive_retries": self.max_consecutive_retries
            },
            "timing": {
                "total_retry_time": self.total_retry_time,
                "avg_retry_time": self.avg_retry_time,
                "min_retry_time": self.min_retry_time if self.min_retry_time != float('inf') else 0,
                "max_retry_time": self.max_retry_time,
                "distribution": self.retry_time_distribution
            },
            "recent_activity": {
                "last_minute": self.last_minute_retries,
                "last_five_minutes": self.last_five_minute_retries,
                "last_hour": self.last_hour_retries
            },
            "by_exception": self.retry_by_exception,
            "by_status_code": self.retry_by_status_code,
            "by_function": self.retry_by_function,
            "by_endpoint": self.retry_by_endpoint
        }
    
    def reset(self) -> None:
        """Reset all statistics"""
        self.__init__()

# Global retry statistics tracker
retry_stats = RetryStats()

def extract_endpoint_from_args(args, kwargs) -> Optional[str]:
    """
    Extract endpoint information from function arguments
    
    Args:
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Endpoint string or None if not found
    """
    # Try to extract URL from httpx requests
    if kwargs.get('url'):
        url = kwargs['url']
        parsed_url = urlparse(url) if isinstance(url, str) else None
        if parsed_url and parsed_url.path:
            return parsed_url.path
    
    # If first arg is self and has a config attribute with instance_url
    if args and hasattr(args[0], 'config') and hasattr(args[0].config, 'instance_url'):
        instance = args[0].config.instance_url
        if instance:
            parsed_instance = urlparse(instance) if isinstance(instance, str) else None
            if parsed_instance and parsed_instance.path:
                return parsed_instance.path
    
    return None

def get_retry_stats_summary() -> str:
    """
    Get a summary of retry statistics
    
    Returns:
        A formatted string with retry statistics summary
    """
    return retry_stats.get_summary()

def get_retry_stats_detailed() -> Dict[str, Any]:
    """
    Get detailed retry statistics in dictionary format
    
    Returns:
        A dictionary with detailed retry statistics
    """
    return retry_stats.get_detailed_report()

def reset_retry_stats() -> None:
    """Reset all retry statistics"""
    retry_stats.reset()