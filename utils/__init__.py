# Utils package initialization
# Import key functions from utils.py for backward compatibility
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from .utils import async_retry, RetryConfig, get_retry_stats_summary, get_retry_stats_detailed
    __all__ = ['async_retry', 'RetryConfig', 'get_retry_stats_summary', 'get_retry_stats_detailed']
except ImportError:
    try:
        from utils import async_retry, RetryConfig, get_retry_stats_summary, get_retry_stats_detailed
        __all__ = ['async_retry', 'RetryConfig', 'get_retry_stats_summary', 'get_retry_stats_detailed']
    except ImportError:
        # Fallback stubs
        def async_retry(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        
        class RetryConfig:
            def __init__(self, *args, **kwargs):
                pass
        
        def get_retry_stats_summary():
            return {}
        
        def get_retry_stats_detailed():
            return {}
        
        __all__ = ['async_retry', 'RetryConfig', 'get_retry_stats_summary', 'get_retry_stats_detailed']
    pass
