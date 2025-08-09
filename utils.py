# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import asyncio
import functools
import logging
import time
import json
import random
import traceback
from typing import Callable, TypeVar, Any, Optional, List, Dict, Union, Type, Tuple
import httpx
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Configure a specific logger for retry operations
retry_logger = logging.getLogger("retry")

T = TypeVar('T')

class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(self, 
                 max_attempts: int = 3, 
                 base_delay: float = 1.0,
                 max_delay: float = 30.0,
                 backoff_factor: float = 2.0,
                 retry_exceptions: Optional[List[Type[Exception]]] = None,
                 retry_status_codes: Optional[List[int]] = None,
                 jitter: bool = True,
                 jitter_factor: float = 0.1,
                 retry_on_timeout: bool = True,
                 retry_on_connection_error: bool = True,
                 retry_on_server_error: bool = True,
                 retry_on_rate_limit: bool = True,
                 retry_on_specific_errors: Optional[List[str]] = None):
        """
        Initialize retry configuration
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Multiplier for delay after each retry
            retry_exceptions: List of exception types to retry on
            retry_status_codes: List of HTTP status codes to retry on
            jitter: Whether to add random jitter to delay times
            jitter_factor: Factor to determine jitter amount (0.1 = ±10%)
            retry_on_timeout: Whether to retry on timeout exceptions
            retry_on_connection_error: Whether to retry on connection errors
            retry_on_server_error: Whether to retry on server errors (5xx)
            retry_on_rate_limit: Whether to retry on rate limit errors (429)
            retry_on_specific_errors: List of error message substrings to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retry_on_timeout = retry_on_timeout
        self.retry_on_connection_error = retry_on_connection_error
        self.retry_on_server_error = retry_on_server_error
        self.retry_on_rate_limit = retry_on_rate_limit
        self.retry_on_specific_errors = retry_on_specific_errors or []
        
        # Build default exception list based on configuration
        default_exceptions = []
        if retry_on_timeout:
            default_exceptions.extend([
                httpx.TimeoutException,
                TimeoutError,
                asyncio.TimeoutError
            ])
        if retry_on_connection_error:
            default_exceptions.extend([
                httpx.ConnectError,
                httpx.ReadError,
                httpx.WriteError,
                httpx.NetworkError,
                ConnectionError,
                ConnectionRefusedError,
                ConnectionResetError,
                OSError,  # Covers many network-related errors
                IOError   # General I/O errors
            ])
            
        self.retry_exceptions = retry_exceptions or default_exceptions
        
        # Build default status code list based on configuration
        default_status_codes = []
        if retry_on_timeout:
            default_status_codes.append(408)  # Request Timeout
        if retry_on_server_error:
            default_status_codes.extend([
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
                520,  # Unknown Error (Cloudflare)
                521,  # Web Server Is Down (Cloudflare)
                522,  # Connection Timed Out (Cloudflare)
                523,  # Origin Is Unreachable (Cloudflare)
                524,  # A Timeout Occurred (Cloudflare)
                525,  # SSL Handshake Failed (Cloudflare)
                526,  # Invalid SSL Certificate (Cloudflare)
                527   # Railgun Error (Cloudflare)
            ])
        # Add rate limiting status code
        if retry_on_rate_limit:
            default_status_codes.append(429)  # Too Many Requests
        
        self.retry_status_codes = retry_status_codes or default_status_codes
        
    def should_retry_on_exception(self, exception: Exception) -> bool:
        """
        Check if an exception should trigger a retry
        
        Args:
            exception: The exception to check
            
        Returns:
            True if the exception should trigger a retry, False otherwise
        """
        # Check if exception is in retry_exceptions
        for exc_type in self.retry_exceptions:
            if isinstance(exception, exc_type):
                return True
                
        # Check for specific error messages
        if self.retry_on_specific_errors:
            error_message = str(exception).lower()
            for error_substring in self.retry_on_specific_errors:
                if error_substring.lower() in error_message:
                    return True
                    
        return False
        
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a specific retry attempt with optional jitter
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay time in seconds
        """
        # Calculate base exponential backoff
        delay = min(
            self.base_delay * (self.backoff_factor ** (attempt - 1)),
            self.max_delay
        )
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_factor
            delay = random.uniform(delay - jitter_amount, delay + jitter_amount)
            
        return max(0, delay)  # Ensure delay is not negative

def extract_context_info(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
    """
    Extract useful context information from function arguments
    
    Args:
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        String with context information
    """
    context_parts = []
    
    # Try to extract URL from httpx requests
    if kwargs.get('url'):
        url = kwargs['url']
        parsed_url = urlparse(url) if hasattr(url, 'split') else None
        if parsed_url and parsed_url.netloc:
            context_parts.append(f"URL: {parsed_url.netloc}{parsed_url.path}")
    
    # Extract request method if available
    if kwargs.get('method'):
        context_parts.append(f"Method: {kwargs['method']}")
    
    # If first arg is self and has a config attribute, extract instance info
    if args and hasattr(args[0], 'config') and hasattr(args[0].config, 'instance_url'):
        instance = args[0].config.instance_url
        if instance:
            parsed_instance = urlparse(instance) if hasattr(instance, 'split') else None
            if parsed_instance and parsed_instance.netloc:
                context_parts.append(f"Instance: {parsed_instance.netloc}")
    
    return ", ".join(context_parts)

def async_retry(retry_config: Optional[RetryConfig] = None, context_extractor: Optional[Callable] = None):
    """
    Decorator for retrying async functions with exponential backoff
    
    Args:
        retry_config: Configuration for retry behavior
        context_extractor: Optional function to extract context from args/kwargs
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    # Use the provided context extractor or the default one
    _context_extractor = context_extractor or extract_context_info
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            last_exception = None
            start_time = time.time()
            context = _context_extractor(args, kwargs)
            context_str = f" [{context}]" if context else ""
            
            while attempt <= retry_config.max_attempts:
                try:
                    result = await func(*args, **kwargs)
                    
                    # Check for HTTP status code if result is an httpx.Response
                    if isinstance(result, httpx.Response) and result.status_code in retry_config.retry_status_codes:
                        if attempt < retry_config.max_attempts:
                            delay = retry_config.calculate_delay(attempt)
                            
                            # Get response details for better logging
                            status_reason = result.reason_phrase if hasattr(result, 'reason_phrase') else 'Unknown'
                            response_body = ''
                            try:
                                # Try to get response body for error details, but limit size
                                if result.headers.get('content-type', '').startswith('application/json'):
                                    response_body = result.json()
                                    if isinstance(response_body, dict):
                                        error_msg = response_body.get('error', {}).get('message', '')
                                        if error_msg:
                                            response_body = f" - Error: {error_msg}"
                                        else:
                                            response_body = f" - {json.dumps(response_body)[:100]}"
                            except Exception:
                                # Ignore errors in parsing response
                                pass
                                
                            logger.warning(
                                f"Received status code {result.status_code} ({status_reason}){response_body} "
                                f"from {func.__name__}{context_str}, "
                                f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})"
                            )
                            await asyncio.sleep(delay)
                            attempt += 1
                            continue
                    
                    # If we got here, either the status code is not in retry_status_codes
                    # or we've reached max attempts
                    if attempt > 1:
                        # Log success after retries
                        duration = time.time() - start_time
                        logger.info(
                            f"Operation {func.__name__}{context_str} succeeded after {attempt} attempts "
                            f"in {duration:.2f}s"
                        )
                    return result
                    
                except Exception as e:
                    # Check if exception should trigger a retry
                    should_retry = retry_config.should_retry_on_exception(e)
                    
                    if should_retry and attempt < retry_config.max_attempts:
                        delay = retry_config.calculate_delay(attempt)
                        
                        # Extract more details from specific exception types
                        error_details = ""
                        if isinstance(e, httpx.HTTPStatusError) and hasattr(e, 'response'):
                            status_code = e.response.status_code if hasattr(e.response, 'status_code') else 'Unknown'
                            error_details = f" (Status: {status_code})"
                            
                            # For rate limiting errors, try to extract retry-after header
                            if status_code == 429 and hasattr(e.response, 'headers'):
                                retry_after = e.response.headers.get('retry-after')
                                if retry_after:
                                    try:
                                        # Try to parse retry-after as seconds
                                        retry_seconds = int(retry_after)
                                        # Use the server's retry-after value if it's reasonable
                                        if 0 < retry_seconds <= retry_config.max_delay:
                                            delay = retry_seconds
                                            error_details += f", Retry-After: {retry_seconds}s"
                                    except ValueError:
                                        # If retry-after is a date, ignore it for now
                                        pass
                                        
                        elif isinstance(e, httpx.TimeoutException):
                            try:
                                timeout_type = e.request.extensions.get('timeout_type', 'unknown') if hasattr(e, 'request') and e.request else 'unknown'
                                error_details = f" (Timeout type: {timeout_type})"
                            except (AttributeError, KeyError):
                                error_details = " (Timeout type: unknown)"
                        
                        logger.warning(
                            f"Exception in {func.__name__}{context_str}: {e.__class__.__name__}{error_details}: {str(e)}, "
                            f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})"
                        )
                        await asyncio.sleep(delay)
                        attempt += 1
                        last_exception = e
                    else:
                        # Either not a retryable exception or max attempts reached
                        duration = time.time() - start_time
                        if attempt > 1:
                            logger.error(
                                f"Failed after {attempt} attempts in {func.__name__}{context_str} "
                                f"({duration:.2f}s): {e.__class__.__name__}: {str(e)}"
                            )
                        raise e
            
            # If we've exhausted all retries, raise the last exception
            if last_exception:
                duration = time.time() - start_time
                logger.error(
                    f"Exhausted all {retry_config.max_attempts} retry attempts for {func.__name__}{context_str} "
                    f"in {duration:.2f}s. Last error: {last_exception.__class__.__name__}: {str(last_exception)}"
                )
                raise last_exception
            
            # This should never happen, but just in case
            raise RuntimeError(f"Unexpected error in retry logic for {func.__name__}{context_str}")
        
        return wrapper
    
    return decorator

def retry(retry_config: Optional[RetryConfig] = None, context_extractor: Optional[Callable] = None):
    """
    Decorator for retrying synchronous functions with exponential backoff
    
    Args:
        retry_config: Configuration for retry behavior
        context_extractor: Optional function to extract context from args/kwargs
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    # Use the provided context extractor or the default one
    _context_extractor = context_extractor or extract_context_info
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            last_exception = None
            start_time = time.time()
            context = _context_extractor(args, kwargs)
            context_str = f" [{context}]" if context else ""
            
            while attempt <= retry_config.max_attempts:
                try:
                    result = func(*args, **kwargs)
                    
                    # Check for HTTP status code if result is an httpx.Response
                    if isinstance(result, httpx.Response) and result.status_code in retry_config.retry_status_codes:
                        if attempt < retry_config.max_attempts:
                            delay = retry_config.calculate_delay(attempt)
                            
                            # Get response details for better logging
                            status_reason = result.reason_phrase if hasattr(result, 'reason_phrase') else 'Unknown'
                            response_body = ''
                            try:
                                # Try to get response body for error details, but limit size
                                if result.headers.get('content-type', '').startswith('application/json'):
                                    response_body = result.json()
                                    if isinstance(response_body, dict):
                                        error_msg = response_body.get('error', {}).get('message', '')
                                        if error_msg:
                                            response_body = f" - Error: {error_msg}"
                                        else:
                                            response_body = f" - {json.dumps(response_body)[:100]}"
                            except Exception:
                                # Ignore errors in parsing response
                                pass
                                
                            logger.warning(
                                f"Received status code {result.status_code} ({status_reason}){response_body} "
                                f"from {func.__name__}{context_str}, "
                                f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})"
                            )
                            time.sleep(delay)
                            attempt += 1
                            continue
                    
                    # If we got here, either the status code is not in retry_status_codes
                    # or we've reached max attempts
                    if attempt > 1:
                        # Log success after retries
                        duration = time.time() - start_time
                        logger.info(
                            f"Operation {func.__name__}{context_str} succeeded after {attempt} attempts "
                            f"in {duration:.2f}s"
                        )
                    return result
                    
                except Exception as e:
                    # Check if exception should trigger a retry
                    should_retry = retry_config.should_retry_on_exception(e)
                    
                    if should_retry and attempt < retry_config.max_attempts:
                        delay = retry_config.calculate_delay(attempt)
                        
                        # Extract more details from specific exception types
                        error_details = ""
                        if isinstance(e, httpx.HTTPStatusError) and hasattr(e, 'response'):
                            status_code = e.response.status_code if hasattr(e.response, 'status_code') else 'Unknown'
                            error_details = f" (Status: {status_code})"
                            
                            # For rate limiting errors, try to extract retry-after header
                            if status_code == 429 and hasattr(e.response, 'headers'):
                                retry_after = e.response.headers.get('retry-after')
                                if retry_after:
                                    try:
                                        # Try to parse retry-after as seconds
                                        retry_seconds = int(retry_after)
                                        # Use the server's retry-after value if it's reasonable
                                        if 0 < retry_seconds <= retry_config.max_delay:
                                            delay = retry_seconds
                                            error_details += f", Retry-After: {retry_seconds}s"
                                    except ValueError:
                                        # If retry-after is a date, ignore it for now
                                        pass
                                        
                        elif isinstance(e, httpx.TimeoutException):
                            error_details = f" (Timeout type: {e.request.extensions.get('timeout_type', 'unknown')})"
                        
                        logger.warning(
                            f"Exception in {func.__name__}{context_str}: {e.__class__.__name__}{error_details}: {str(e)}, "
                            f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})"
                        )
                        time.sleep(delay)
                        attempt += 1
                        last_exception = e
                    else:
                        # Either not a retryable exception or max attempts reached
                        duration = time.time() - start_time
                        if attempt > 1:
                            logger.error(
                                f"Failed after {attempt} attempts in {func.__name__}{context_str} "
                                f"({duration:.2f}s): {e.__class__.__name__}: {str(e)}"
                            )
                        raise e
            
            # If we've exhausted all retries, raise the last exception
            if last_exception:
                duration = time.time() - start_time
                logger.error(
                    f"Exhausted all {retry_config.max_attempts} retry attempts for {func.__name__}{context_str} "
                    f"in {duration:.2f}s. Last error: {last_exception.__class__.__name__}: {str(last_exception)}"
                )
                raise last_exception
            
            # This should never happen, but just in case
            raise RuntimeError(f"Unexpected error in retry logic for {func.__name__}{context_str}")
        
        return wrapper
    
    return decorator

# New retry utility functions

def convert_config_retry_to_utils_retry(config_retry):
    """
    Convert a RetryConfig from config.py to a RetryConfig from utils.py
    
    Args:
        config_retry: RetryConfig instance from config.py
        
    Returns:
        RetryConfig instance from utils.py
    """
    return RetryConfig(
        max_attempts=config_retry.max_attempts,
        base_delay=config_retry.base_delay,
        max_delay=config_retry.max_delay,
        backoff_factor=config_retry.backoff_factor,
        jitter=config_retry.jitter,
        jitter_factor=config_retry.jitter_factor,
        retry_on_timeout=config_retry.retry_on_timeout,
        retry_on_connection_error=config_retry.retry_on_connection_error,
        retry_on_server_error=config_retry.retry_on_server_error,
        retry_on_rate_limit=config_retry.retry_on_rate_limit,
        retry_on_specific_errors=config_retry.retry_specific_errors
    )

class RetryStats:
    """Track retry statistics for monitoring and reporting"""
    
    def __init__(self):
        self.total_operations = 0
        self.retried_operations = 0
        self.retry_attempts = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.retry_by_exception = {}
        self.retry_by_status_code = {}
        self.retry_by_function = {}
        self.retry_by_endpoint = {}
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
        self.retry_timestamps = []
        self.last_minute_retries = 0
        self.last_five_minute_retries = 0
        self.last_hour_retries = 0
        
    def record_operation(self, retried=False, attempts=1, success=True, 
                        exception_type=None, status_code=None, retry_time=0.0,
                        function_name=None, endpoint=None):
        """Record statistics for an operation"""
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
    
    def get_summary(self):
        """Get a summary of retry statistics"""
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
        
    def get_detailed_report(self):
        """Get a detailed report of retry statistics in JSON format"""
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

# Global retry statistics tracker
retry_stats = RetryStats()

def async_retry_with_stats(retry_config: Optional[RetryConfig] = None, context_extractor: Optional[Callable] = None):
    """
    Enhanced decorator for retrying async functions with statistics tracking
    
    Args:
        retry_config: Configuration for retry behavior
        context_extractor: Optional function to extract context from args/kwargs
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    # Use the provided context extractor or the default one
    _context_extractor = context_extractor or extract_context_info
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            last_exception = None
            start_time = time.time()
            context = _context_extractor(args, kwargs)
            context_str = f" [{context}]" if context else ""
            retried = False
            exception_type = None
            status_code = None
            endpoint = None
            
            # Extract endpoint from URL if available
            if kwargs.get('url'):
                url = kwargs['url']
                parsed_url = urlparse(url) if isinstance(url, str) else None
                if parsed_url and parsed_url.path:
                    endpoint = parsed_url.path
            
            # Track individual retry timings
            retry_timings = []
            retry_start_time = None
            
            while attempt <= retry_config.max_attempts:
                try:
                    # If this is a retry attempt, record the timing of the previous attempt
                    if retry_start_time is not None:
                        retry_end_time = time.time()
                        retry_duration = retry_end_time - retry_start_time
                        retry_timings.append(retry_duration)
                        retry_start_time = None
                    
                    result = await func(*args, **kwargs)
                    
                    # Check for HTTP status code if result is an httpx.Response
                    if isinstance(result, httpx.Response) and result.status_code in retry_config.retry_status_codes:
                        if attempt < retry_config.max_attempts:
                            retried = True
                            status_code = result.status_code
                            delay = retry_config.calculate_delay(attempt)
                            
                            # Get response details for better logging
                            status_reason = result.reason_phrase if hasattr(result, 'reason_phrase') else 'Unknown'
                            response_body = ''
                            try:
                                # Try to get response body for error details, but limit size
                                if result.headers.get('content-type', '').startswith('application/json'):
                                    response_body = result.json()
                                    if isinstance(response_body, dict):
                                        error_msg = response_body.get('error', {}).get('message', '')
                                        if error_msg:
                                            response_body = f" - Error: {error_msg}"
                                        else:
                                            response_body = f" - {json.dumps(response_body)[:100]}"
                                            
                                # Try to extract endpoint from URL in response
                                if not endpoint and hasattr(result, 'url'):
                                    parsed_url = urlparse(str(result.url))
                                    if parsed_url and parsed_url.path:
                                        endpoint = parsed_url.path
                            except Exception:
                                # Ignore errors in parsing response
                                pass
                                
                            # Include stack trace for better debugging
                            stack_trace = traceback.format_stack()
                            stack_summary = "".join(stack_trace[-3:-1])  # Get the last few frames
                            
                            retry_logger.warning(
                                f"Received status code {result.status_code} ({status_reason}){response_body} "
                                f"from {func.__name__}{context_str}, "
                                f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})\n"
                                f"Stack trace:\n{stack_summary}"
                            )
                            
                            # Set the start time for the next retry attempt
                            retry_start_time = time.time()
                            
                            await asyncio.sleep(delay)
                            attempt += 1
                            continue
                    
                    # If we got here, either the status code is not in retry_status_codes
                    # or we've reached max attempts
                    retry_time = time.time() - start_time
                    
                    if attempt > 1:
                        # Log success after retries
                        retry_logger.info(
                            f"Operation {func.__name__}{context_str} succeeded after {attempt} attempts "
                            f"in {retry_time:.2f}s"
                        )
                    
                    # Record statistics
                    retry_stats.record_operation(
                        retried=retried,
                        attempts=attempt,
                        success=True,
                        exception_type=exception_type,
                        status_code=status_code,
                        retry_time=retry_time if retried else 0.0,
                        function_name=func.__name__,
                        endpoint=endpoint
                    )
                    
                    return result
                    
                except Exception as e:
                    # Check if exception should trigger a retry
                    should_retry = retry_config.should_retry_on_exception(e)
                    exception_type = type(e)
                    
                    if should_retry and attempt < retry_config.max_attempts:
                        retried = True
                        delay = retry_config.calculate_delay(attempt)
                        
                        # Extract more details from specific exception types
                        error_details = ""
                        if isinstance(e, httpx.HTTPStatusError) and hasattr(e, 'response'):
                            status_code = e.response.status_code if hasattr(e.response, 'status_code') else 'Unknown'
                            error_details = f" (Status: {status_code})"
                            
                            # Try to extract endpoint from URL in response
                            if not endpoint and hasattr(e.response, 'url'):
                                parsed_url = urlparse(str(e.response.url))
                                if parsed_url and parsed_url.path:
                                    endpoint = parsed_url.path
                            
                            # For rate limiting errors, try to extract retry-after header
                            if status_code == 429 and hasattr(e.response, 'headers'):
                                retry_after = e.response.headers.get('retry-after')
                                if retry_after:
                                    try:
                                        # Try to parse retry-after as seconds
                                        retry_seconds = int(retry_after)
                                        # Use the server's retry-after value if it's reasonable
                                        if 0 < retry_seconds <= retry_config.max_delay:
                                            delay = retry_seconds
                                            error_details += f", Retry-After: {retry_seconds}s"
                                    except ValueError:
                                        # If retry-after is a date, ignore it for now
                                        pass
                                        
                        elif isinstance(e, httpx.TimeoutException):
                            error_details = f" (Timeout type: {e.request.extensions.get('timeout_type', 'unknown')})"
                        
                        # Include stack trace for better debugging
                        stack_trace = traceback.format_stack()
                        stack_summary = "".join(stack_trace[-3:-1])  # Get the last few frames
                        
                        retry_logger.warning(
                            f"Exception in {func.__name__}{context_str}: {e.__class__.__name__}{error_details}: {str(e)}, "
                            f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})\n"
                            f"Stack trace:\n{stack_summary}"
                        )
                        
                        # Set the start time for the next retry attempt
                        retry_start_time = time.time()
                        
                        await asyncio.sleep(delay)
                        attempt += 1
                        last_exception = e
                    else:
                        # Either not a retryable exception or max attempts reached
                        retry_time = time.time() - start_time
                        
                        if attempt > 1:
                            retry_logger.error(
                                f"Failed after {attempt} attempts in {func.__name__}{context_str} "
                                f"({retry_time:.2f}s): {e.__class__.__name__}: {str(e)}"
                            )
                        
                        # Record statistics
                        retry_stats.record_operation(
                            retried=retried,
                            attempts=attempt,
                            success=False,
                            exception_type=exception_type,
                            status_code=status_code,
                            retry_time=retry_time if retried else 0.0,
                            function_name=func.__name__,
                            endpoint=endpoint
                        )
                        
                        raise e
            
            # If we've exhausted all retries, raise the last exception
            if last_exception:
                retry_time = time.time() - start_time
                
                retry_logger.error(
                    f"Exhausted all {retry_config.max_attempts} retry attempts for {func.__name__}{context_str} "
                    f"in {retry_time:.2f}s. Last error: {last_exception.__class__.__name__}: {str(last_exception)}"
                )
                
                # Record statistics
                retry_stats.record_operation(
                    retried=True,
                    attempts=retry_config.max_attempts,
                    success=False,
                    exception_type=type(last_exception),
                    status_code=status_code,
                    retry_time=retry_time,
                    function_name=func.__name__,
                    endpoint=endpoint
                )
                
                raise last_exception
            
            # This should never happen, but just in case
            raise RuntimeError(f"Unexpected error in retry logic for {func.__name__}{context_str}")
        
        return wrapper
    
    return decorator

def retry_with_stats(retry_config: Optional[RetryConfig] = None, context_extractor: Optional[Callable] = None):
    """
    Enhanced decorator for retrying synchronous functions with statistics tracking
    
    Args:
        retry_config: Configuration for retry behavior
        context_extractor: Optional function to extract context from args/kwargs
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    # Use the provided context extractor or the default one
    _context_extractor = context_extractor or extract_context_info
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            last_exception = None
            start_time = time.time()
            context = _context_extractor(args, kwargs)
            context_str = f" [{context}]" if context else ""
            retried = False
            exception_type = None
            status_code = None
            endpoint = None
            
            # Extract endpoint from URL if available
            if kwargs.get('url'):
                url = kwargs['url']
                parsed_url = urlparse(url) if isinstance(url, str) else None
                if parsed_url and parsed_url.path:
                    endpoint = parsed_url.path
            
            # Track individual retry timings
            retry_timings = []
            retry_start_time = None
            
            while attempt <= retry_config.max_attempts:
                try:
                    # If this is a retry attempt, record the timing of the previous attempt
                    if retry_start_time is not None:
                        retry_end_time = time.time()
                        retry_duration = retry_end_time - retry_start_time
                        retry_timings.append(retry_duration)
                        retry_start_time = None
                    
                    result = func(*args, **kwargs)
                    
                    # Check for HTTP status code if result is an httpx.Response
                    if isinstance(result, httpx.Response) and result.status_code in retry_config.retry_status_codes:
                        if attempt < retry_config.max_attempts:
                            retried = True
                            status_code = result.status_code
                            delay = retry_config.calculate_delay(attempt)
                            
                            # Get response details for better logging
                            status_reason = result.reason_phrase if hasattr(result, 'reason_phrase') else 'Unknown'
                            response_body = ''
                            try:
                                # Try to get response body for error details, but limit size
                                if result.headers.get('content-type', '').startswith('application/json'):
                                    response_body = result.json()
                                    if isinstance(response_body, dict):
                                        error_msg = response_body.get('error', {}).get('message', '')
                                        if error_msg:
                                            response_body = f" - Error: {error_msg}"
                                        else:
                                            response_body = f" - {json.dumps(response_body)[:100]}"
                                            
                                # Try to extract endpoint from URL in response
                                if not endpoint and hasattr(result, 'url'):
                                    parsed_url = urlparse(str(result.url))
                                    if parsed_url and parsed_url.path:
                                        endpoint = parsed_url.path
                            except Exception:
                                # Ignore errors in parsing response
                                pass
                                
                            # Include stack trace for better debugging
                            stack_trace = traceback.format_stack()
                            stack_summary = "".join(stack_trace[-3:-1])  # Get the last few frames
                            
                            retry_logger.warning(
                                f"Received status code {result.status_code} ({status_reason}){response_body} "
                                f"from {func.__name__}{context_str}, "
                                f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})\n"
                                f"Stack trace:\n{stack_summary}"
                            )
                            
                            # Set the start time for the next retry attempt
                            retry_start_time = time.time()
                            
                            time.sleep(delay)
                            attempt += 1
                            continue
                    
                    # If we got here, either the status code is not in retry_status_codes
                    # or we've reached max attempts
                    retry_time = time.time() - start_time
                    
                    if attempt > 1:
                        # Log success after retries
                        retry_logger.info(
                            f"Operation {func.__name__}{context_str} succeeded after {attempt} attempts "
                            f"in {retry_time:.2f}s"
                        )
                    
                    # Record statistics
                    retry_stats.record_operation(
                        retried=retried,
                        attempts=attempt,
                        success=True,
                        exception_type=exception_type,
                        status_code=status_code,
                        retry_time=retry_time if retried else 0.0,
                        function_name=func.__name__,
                        endpoint=endpoint
                    )
                    
                    return result
                    
                except Exception as e:
                    # Check if exception should trigger a retry
                    should_retry = retry_config.should_retry_on_exception(e)
                    exception_type = type(e)
                    
                    if should_retry and attempt < retry_config.max_attempts:
                        retried = True
                        delay = retry_config.calculate_delay(attempt)
                        
                        # Extract more details from specific exception types
                        error_details = ""
                        if isinstance(e, httpx.HTTPStatusError) and hasattr(e, 'response'):
                            status_code = e.response.status_code if hasattr(e.response, 'status_code') else 'Unknown'
                            error_details = f" (Status: {status_code})"
                            
                            # Try to extract endpoint from URL in response
                            if not endpoint and hasattr(e.response, 'url'):
                                parsed_url = urlparse(str(e.response.url))
                                if parsed_url and parsed_url.path:
                                    endpoint = parsed_url.path
                            
                            # For rate limiting errors, try to extract retry-after header
                            if status_code == 429 and hasattr(e.response, 'headers'):
                                retry_after = e.response.headers.get('retry-after')
                                if retry_after:
                                    try:
                                        # Try to parse retry-after as seconds
                                        retry_seconds = int(retry_after)
                                        # Use the server's retry-after value if it's reasonable
                                        if 0 < retry_seconds <= retry_config.max_delay:
                                            delay = retry_seconds
                                            error_details += f", Retry-After: {retry_seconds}s"
                                    except ValueError:
                                        # If retry-after is a date, ignore it for now
                                        pass
                                        
                        elif isinstance(e, httpx.TimeoutException):
                            error_details = f" (Timeout type: {e.request.extensions.get('timeout_type', 'unknown')})"
                        
                        # Include stack trace for better debugging
                        stack_trace = traceback.format_stack()
                        stack_summary = "".join(stack_trace[-3:-1])  # Get the last few frames
                        
                        retry_logger.warning(
                            f"Exception in {func.__name__}{context_str}: {e.__class__.__name__}{error_details}: {str(e)}, "
                            f"retrying in {delay:.2f}s (attempt {attempt}/{retry_config.max_attempts})\n"
                            f"Stack trace:\n{stack_summary}"
                        )
                        
                        # Set the start time for the next retry attempt
                        retry_start_time = time.time()
                        
                        time.sleep(delay)
                        attempt += 1
                        last_exception = e
                    else:
                        # Either not a retryable exception or max attempts reached
                        retry_time = time.time() - start_time
                        
                        if attempt > 1:
                            retry_logger.error(
                                f"Failed after {attempt} attempts in {func.__name__}{context_str} "
                                f"({retry_time:.2f}s): {e.__class__.__name__}: {str(e)}"
                            )
                        
                        # Record statistics
                        retry_stats.record_operation(
                            retried=retried,
                            attempts=attempt,
                            success=False,
                            exception_type=exception_type,
                            status_code=status_code,
                            retry_time=retry_time if retried else 0.0,
                            function_name=func.__name__,
                            endpoint=endpoint
                        )
                        
                        raise e
            
            # If we've exhausted all retries, raise the last exception
            if last_exception:
                retry_time = time.time() - start_time
                
                retry_logger.error(
                    f"Exhausted all {retry_config.max_attempts} retry attempts for {func.__name__}{context_str} "
                    f"in {retry_time:.2f}s. Last error: {last_exception.__class__.__name__}: {str(last_exception)}"
                )
                
                # Record statistics
                retry_stats.record_operation(
                    retried=True,
                    attempts=retry_config.max_attempts,
                    success=False,
                    exception_type=type(last_exception),
                    status_code=status_code,
                    retry_time=retry_time,
                    function_name=func.__name__,
                    endpoint=endpoint
                )
                
                raise last_exception
            
            # This should never happen, but just in case
            raise RuntimeError(f"Unexpected error in retry logic for {func.__name__}{context_str}")
        
        return wrapper
    
    return decorator

def get_retry_stats_summary():
    """Get a summary of retry statistics"""
    return retry_stats.get_summary()

def get_retry_stats_detailed():
    """Get detailed retry statistics in JSON format"""
    return retry_stats.get_detailed_report()

def reset_retry_stats():
    """Reset retry statistics"""
    global retry_stats
    retry_stats = RetryStats()