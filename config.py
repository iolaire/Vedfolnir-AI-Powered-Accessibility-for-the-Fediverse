# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import logging
from logger import setup_logging

# Set up logging to file before loading config
setup_logging(log_file="logs/webapp.log")
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Log the value of DB_POOL_SIZE immediately after loading .env
db_pool_size_from_env = os.getenv("DB_POOL_SIZE")
logging.info(f"DB_POOL_SIZE from environment after load_dotenv: {db_pool_size_from_env}")

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_on_server_error: bool = True
    retry_on_rate_limit: bool = True
    retry_specific_errors: list = None
    
    @classmethod
    def from_env(cls):
        # Parse comma-separated list of specific error strings to retry on
        retry_specific_errors_str = os.getenv("RETRY_SPECIFIC_ERRORS", "")
        retry_specific_errors = [err.strip() for err in retry_specific_errors_str.split(",")] if retry_specific_errors_str else None
        
        return cls(
            max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
            base_delay=float(os.getenv("RETRY_BASE_DELAY", "1.0")),
            max_delay=float(os.getenv("RETRY_MAX_DELAY", "30.0")),
            backoff_factor=float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0")),
            jitter=os.getenv("RETRY_USE_JITTER", "true").lower() == "true",
            jitter_factor=float(os.getenv("RETRY_JITTER_FACTOR", "0.1")),
            retry_on_timeout=os.getenv("RETRY_ON_TIMEOUT", "true").lower() == "true",
            retry_on_connection_error=os.getenv("RETRY_ON_CONNECTION_ERROR", "true").lower() == "true",
            retry_on_server_error=os.getenv("RETRY_ON_SERVER_ERROR", "true").lower() == "true",
            retry_on_rate_limit=os.getenv("RETRY_ON_RATE_LIMIT", "true").lower() == "true",
            retry_specific_errors=retry_specific_errors,
        )

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting behavior"""
    requests_per_minute: int = 60  # Default: 60 requests per minute
    requests_per_hour: int = 1000  # Default: 1000 requests per hour
    requests_per_day: int = 10000  # Default: 10000 requests per day
    max_burst: int = 10  # Maximum burst size for token bucket
    
    # Per-endpoint rate limits (overrides global limits)
    endpoint_limits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Platform-specific rate limits
    platform_limits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Platform-specific endpoint rate limits
    platform_endpoint_limits: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls):
        """Create a RateLimitConfig from environment variables"""
        # Get global rate limits
        requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
        requests_per_hour = int(os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR", "1000"))
        requests_per_day = int(os.getenv("RATE_LIMIT_REQUESTS_PER_DAY", "10000"))
        max_burst = int(os.getenv("RATE_LIMIT_MAX_BURST", "10"))
        
        # Create config with global limits
        config = cls(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
            max_burst=max_burst
        )
        
        # Look for endpoint-specific limits
        # Format: RATE_LIMIT_ENDPOINT_<endpoint>_<timeframe>=<limit>
        # Example: RATE_LIMIT_ENDPOINT_MEDIA_MINUTE=30
        endpoint_prefix = "RATE_LIMIT_ENDPOINT_"
        for key, value in os.environ.items():
            if key.startswith(endpoint_prefix):
                parts = key[len(endpoint_prefix):].split("_")
                if len(parts) >= 2:
                    endpoint = parts[0].lower()
                    timeframe = parts[1].lower()
                    
                    if endpoint not in config.endpoint_limits:
                        config.endpoint_limits[endpoint] = {}
                    
                    try:
                        limit = int(value)
                        if timeframe in ("minute", "hour", "day"):
                            config.endpoint_limits[endpoint][timeframe] = limit
                    except ValueError:
                        pass  # Ignore invalid values
        
        # Look for platform-specific limits
        # Format: RATE_LIMIT_<platform>_<timeframe>=<limit>
        # Example: RATE_LIMIT_MASTODON_MINUTE=300
        platform_prefix = "RATE_LIMIT_"
        for key, value in os.environ.items():
            if key.startswith(platform_prefix) and not key.startswith(endpoint_prefix):
                parts = key[len(platform_prefix):].split("_")
                if len(parts) >= 2:
                    platform = parts[0].lower()
                    timeframe = parts[1].lower()
                    
                    # Skip global settings and endpoint settings
                    if platform in ("requests", "max", "endpoint"):
                        continue
                    
                    if platform not in config.platform_limits:
                        config.platform_limits[platform] = {}
                    
                    try:
                        limit = int(value)
                        if timeframe in ("minute", "hour", "day"):
                            config.platform_limits[platform][timeframe] = limit
                    except ValueError:
                        pass  # Ignore invalid values
        
        # Look for platform-specific endpoint limits
        # Format: RATE_LIMIT_<platform>_ENDPOINT_<endpoint>_<timeframe>=<limit>
        # Example: RATE_LIMIT_MASTODON_ENDPOINT_MEDIA_MINUTE=100
        platform_endpoint_prefix = "RATE_LIMIT_"
        for key, value in os.environ.items():
            if key.startswith(platform_endpoint_prefix) and "_ENDPOINT_" in key:
                # Split on the first occurrence of _ENDPOINT_
                prefix_part, endpoint_part = key.split("_ENDPOINT_", 1)
                platform = prefix_part[len(platform_endpoint_prefix):].lower()
                
                endpoint_parts = endpoint_part.split("_")
                if len(endpoint_parts) >= 2:
                    endpoint = endpoint_parts[0].lower()
                    timeframe = endpoint_parts[1].lower()
                    
                    if platform not in config.platform_endpoint_limits:
                        config.platform_endpoint_limits[platform] = {}
                    if endpoint not in config.platform_endpoint_limits[platform]:
                        config.platform_endpoint_limits[platform][endpoint] = {}
                    
                    try:
                        limit = int(value)
                        if timeframe in ("minute", "hour", "day"):
                            config.platform_endpoint_limits[platform][endpoint][timeframe] = limit
                    except ValueError:
                        pass  # Ignore invalid values
        
        return config

class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete"""
    pass

@dataclass
class ActivityPubConfig:
    """Configuration for ActivityPub client"""
    instance_url: str
    access_token: str
    api_type: str = "pixelfed"  # 'pixelfed' or 'mastodon'
    username: Optional[str] = None
    
    # Pixelfed-specific configuration
    private_key_path: Optional[str] = None
    public_key_path: Optional[str] = None
    
    # Mastodon-specific configuration
    client_key: Optional[str] = None
    client_secret: Optional[str] = None
    
    # Common configuration
    user_agent: str = "Vedfolnir/1.0"
    platform_type: Optional[str] = None  # Legacy field for backward compatibility
    is_pixelfed: bool = False  # Legacy flag for backward compatibility
    retry: RetryConfig = None
    rate_limit: RateLimitConfig = None
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate platform-specific configuration requirements"""
        # Skip validation if both instance_url and access_token are empty
        # This allows the app to work with database-stored platform connections
        if not self.instance_url and not self.access_token:
            return  # Platform connections will be loaded from database
        
        if not self.instance_url:
            raise ConfigurationError("ACTIVITYPUB_INSTANCE_URL is required")
        
        if not self.access_token:
            raise ConfigurationError("ACTIVITYPUB_ACCESS_TOKEN is required")
        
        if self.api_type == "mastodon":
            # Mastodon now only requires access token - client credentials are optional
            pass
        elif self.api_type == "pixelfed":
            # Pixelfed doesn't require additional credentials beyond access_token
            pass
        else:
            raise ConfigurationError(f"Unsupported ACTIVITYPUB_API_TYPE: {self.api_type}. Supported types: 'pixelfed', 'mastodon'")

    @classmethod
    def from_env(cls):
        # Get API type from environment variable, default to 'pixelfed' for backward compatibility
        api_type = os.getenv("ACTIVITYPUB_API_TYPE", "pixelfed").lower()
        
        # For backward compatibility, check legacy environment variables
        platform_type = os.getenv("ACTIVITYPUB_PLATFORM_TYPE")
        is_pixelfed = os.getenv("PIXELFED_API", "false").lower() == "true"
        
        # Handle backward compatibility for platform_type
        if platform_type and not os.getenv("ACTIVITYPUB_API_TYPE"):
            api_type = platform_type.lower()
        elif is_pixelfed and not os.getenv("ACTIVITYPUB_API_TYPE") and not platform_type:
            api_type = "pixelfed"
        
        # Validate api_type
        if api_type not in ["pixelfed", "mastodon"]:
            api_type = "pixelfed"  # Default fallback
        
        return cls(
            instance_url=os.getenv("ACTIVITYPUB_INSTANCE_URL", ""),
            access_token=os.getenv("ACTIVITYPUB_ACCESS_TOKEN", ""),
            api_type=api_type,
            username=os.getenv("ACTIVITYPUB_USERNAME"),
            
            # Pixelfed-specific
            private_key_path=os.getenv("PRIVATE_KEY_PATH"),
            public_key_path=os.getenv("PUBLIC_KEY_PATH"),
            
            # Mastodon-specific (optional)
            client_key=os.getenv("MASTODON_CLIENT_KEY"),
            client_secret=os.getenv("MASTODON_CLIENT_SECRET"),
            
            # Legacy fields for backward compatibility
            platform_type=platform_type,
            is_pixelfed=is_pixelfed,
            
            retry=RetryConfig.from_env(),
            rate_limit=RateLimitConfig.from_env(),
        )

@dataclass
class CaptionConfig:
    """Configuration for caption generation and formatting"""
    max_length: int = 500  # Maximum caption length in characters
    optimal_min_length: int = 80  # Minimum length for optimal captions
    optimal_max_length: int = 200  # Maximum length for optimal captions
    
    @classmethod
    def from_env(cls):
        """Create a CaptionConfig from environment variables"""
        return cls(
            max_length=int(os.getenv("CAPTION_MAX_LENGTH", "500")),
            optimal_min_length=int(os.getenv("CAPTION_OPTIMAL_MIN_LENGTH", "80")),
            optimal_max_length=int(os.getenv("CAPTION_OPTIMAL_MAX_LENGTH", "200")),
        )

@dataclass
class FallbackConfig:
    """Configuration for caption generation fallback mechanisms"""
    enabled: bool = True
    max_fallback_attempts: int = 2
    use_simplified_prompts: bool = True
    use_backup_model: bool = True
    backup_model_name: str = "llava:13b-v1.6"  # Default backup model
    
    @classmethod
    def from_env(cls):
        """Create a FallbackConfig from environment variables"""
        return cls(
            enabled=os.getenv("FALLBACK_ENABLED", "true").lower() == "true",
            max_fallback_attempts=int(os.getenv("FALLBACK_MAX_ATTEMPTS", "2")),
            use_simplified_prompts=os.getenv("FALLBACK_USE_SIMPLIFIED_PROMPTS", "true").lower() == "true",
            use_backup_model=os.getenv("FALLBACK_USE_BACKUP_MODEL", "true").lower() == "true",
            backup_model_name=os.getenv("FALLBACK_BACKUP_MODEL", "llava:13b-v1.6"),
        )

@dataclass
class OllamaConfig:
    """Configuration for Ollama with llava model"""
    url: str = "http://localhost:11434"
    model_name: str = "llava:7b"
    timeout: float = 60.0
    retry: RetryConfig = None
    fallback: FallbackConfig = None
    caption: CaptionConfig = None
    
    @classmethod
    def from_env(cls):
        return cls(
            url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name=os.getenv("OLLAMA_MODEL", "llava:7b"),
            timeout=float(os.getenv("OLLAMA_TIMEOUT", "60.0")),
            retry=RetryConfig.from_env(),
            fallback=FallbackConfig.from_env(),
            caption=CaptionConfig.from_env(),
        )

@dataclass
class DatabaseConfig:
    """Configuration for MySQL database connection and performance"""
    pool_size: int = 20
    max_overflow: int = 50
    pool_timeout: int = 30
    pool_recycle: int = 3600  # 1 hour - MySQL optimized
    query_logging: bool = False
    
    @classmethod
    def from_env(cls):
        pool_size=int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "50"))
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30"))
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600"))
        query_logging=os.getenv("DB_QUERY_LOGGING", "false").lower() == "true"
        
        logging.info(f"MySQL database pool size loaded from environment: {pool_size}")
        logging.info(f"MySQL database max overflow loaded from environment: {max_overflow}")

        return cls(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            query_logging=query_logging,
        )

@dataclass
class StorageConfig:
    """Configuration for storage paths and MySQL database"""
    def __init__(self, base_dir="storage", images_dir="storage/images", logs_dir="logs", 
                 database_url="mysql+pymysql://vedfolnir_user:vedfolnir_password@localhost/vedfolnir?charset=utf8mb4",
                 db_config=None):
        self.base_dir = base_dir
        self.images_dir = images_dir
        self.logs_dir = logs_dir
        self.database_url = database_url
        self.db_config = db_config
        
        # Create directories if they don't exist (MySQL doesn't need database_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Initialize database config if not provided
        if self.db_config is None:
            self.db_config = DatabaseConfig.from_env()
        
        # Initialize storage limit management service
        try:
            from storage_configuration_service import StorageConfigurationService
            self.limit_service = StorageConfigurationService()
        except ImportError as e:
            logging.warning(f"Could not import StorageConfigurationService: {e}")
            self.limit_service = None
    
    @classmethod
    def from_env(cls):
        return cls(
            base_dir=os.getenv("STORAGE_BASE_DIR", "storage"),
            images_dir=os.getenv("STORAGE_IMAGES_DIR", "storage/images"),
            logs_dir=os.getenv("LOGS_DIR", "logs"),
            database_url=os.getenv("DATABASE_URL", "mysql+pymysql://vedfolnir_user:vedfolnir_password@localhost/vedfolnir?charset=utf8mb4")
        )

@dataclass
class AuthConfig:
    """Configuration for authentication"""
    session_lifetime: int = 86400  # 24 hours in seconds
    remember_cookie_duration: int = 2592000  # 30 days in seconds
    require_auth: bool = True
    
    @classmethod
    def from_env(cls):
        return cls(
            session_lifetime=int(os.getenv("AUTH_SESSION_LIFETIME", "86400")),
            remember_cookie_duration=int(os.getenv("AUTH_REMEMBER_COOKIE_DURATION", "2592000")),
            require_auth=os.getenv("AUTH_REQUIRE_AUTH", "true").lower() == "true",
        )

@dataclass
class RedisConfig:
    """Configuration for Redis session storage"""
    url: str = "redis://localhost:6379/0"
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    
    # Session-specific Redis settings
    session_prefix: str = "vedfolnir:session:"
    session_timeout: int = 7200  # 2 hours
    cleanup_interval: int = 3600  # 1 hour
    
    @classmethod
    def from_env(cls):
        """Create a RedisConfig from environment variables"""
        return cls(
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD") or None,
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
            session_prefix=os.getenv("REDIS_SESSION_PREFIX", "vedfolnir:session:"),
            session_timeout=int(os.getenv("REDIS_SESSION_TIMEOUT", "7200")),
            cleanup_interval=int(os.getenv("REDIS_SESSION_CLEANUP_INTERVAL", "3600")),
        )

@dataclass
class BatchUpdateConfig:
    """Configuration for batch update functionality"""
    enabled: bool = True
    batch_size: int = 5
    max_concurrent_batches: int = 2
    verification_delay: int = 2  # Delay in seconds before verification
    rollback_on_failure: bool = True
    
    @classmethod
    def from_env(cls):
        return cls(
            enabled=os.getenv("BATCH_UPDATE_ENABLED", "true").lower() == "true",
            batch_size=int(os.getenv("BATCH_UPDATE_SIZE", "5")),
            max_concurrent_batches=int(os.getenv("BATCH_UPDATE_MAX_CONCURRENT", "2")),
            verification_delay=int(os.getenv("BATCH_UPDATE_VERIFICATION_DELAY", "2")),
            rollback_on_failure=os.getenv("BATCH_UPDATE_ROLLBACK_ON_FAILURE", "true").lower() == "true",
        )

@dataclass
class WebAppConfig:
    """Configuration for Flask web app"""
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    secret_key: str = None  # Will be set from environment
    
    @classmethod
    def from_env(cls):
        secret_key = os.getenv("FLASK_SECRET_KEY")
        if not secret_key:
            raise ConfigurationError(
                "FLASK_SECRET_KEY is required in .env file. "
                "Please copy .env.example to .env and configure your security settings. "
                "See docs/security/environment-setup.md for secure value generation."
            )
        
        return cls(
            host=os.getenv("FLASK_HOST", "127.0.0.1"),
            port=int(os.getenv("FLASK_PORT", "5000")),
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
            secret_key=secret_key,
        )
        
class Config:
    """Main configuration class"""
    def __init__(self):
        # Initialize ActivityPub config but allow it to be empty if using database-stored connections
        try:
            self.activitypub = ActivityPubConfig.from_env()
        except ConfigurationError as e:
            # If ActivityPub config is missing, create a minimal config
            # Platform connections will be loaded from database instead
            if "ACTIVITYPUB_INSTANCE_URL is required" in str(e) or "ACTIVITYPUB_ACCESS_TOKEN is required" in str(e):
                self.activitypub = ActivityPubConfig(
                    instance_url="",
                    access_token="",
                    api_type="pixelfed",  # Default type
                    retry=RetryConfig.from_env(),
                    rate_limit=RateLimitConfig.from_env()
                )
            else:
                raise  # Re-raise other configuration errors
        
        self.ollama = OllamaConfig.from_env()
        self.caption = CaptionConfig.from_env()  # Add caption config at top level for easy access
        self.storage = StorageConfig.from_env()
        self.webapp = WebAppConfig.from_env()
        self.auth = AuthConfig.from_env()
        self.redis = RedisConfig.from_env()
        self.batch_update = BatchUpdateConfig.from_env()
        
        # Initialize session configuration (lazy loading to avoid circular imports)
        self._session_config = None
        
        self.use_batch_updates = self.batch_update.enabled
        self.batch_size = self.batch_update.batch_size
        self.max_concurrent_batches = self.batch_update.max_concurrent_batches
        self.verification_delay = self.batch_update.verification_delay
        self.rollback_on_failure = self.batch_update.rollback_on_failure
        self.max_posts_per_run = int(os.getenv("MAX_POSTS_PER_RUN", "50"))
        self.max_users_per_run = int(os.getenv("MAX_USERS_PER_RUN", "10"))
        self.user_processing_delay = int(os.getenv("USER_PROCESSING_DELAY", "5"))  # Delay in seconds between processing users
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def session(self):
        """Get session configuration (lazy loading)"""
        if self._session_config is None:
            try:
                from session_config import get_session_config
                self._session_config = get_session_config()
            except ImportError:
                # Fallback if session_config is not available
                self._session_config = None
        return self._session_config
    
    def validate_configuration(self) -> List[str]:
        """
        Validate all configuration components and return list of validation errors.
        
        Returns:
            List of validation error messages. Empty list if all valid.
        """
        errors = []
        
        try:
            # Validate ActivityPub configuration
            self.activitypub._validate_configuration()
        except ConfigurationError as e:
            errors.append(f"ActivityPub configuration: {str(e)}")
        
        try:
            # Validate WebApp configuration
            if not self.webapp.secret_key:
                errors.append("FLASK_SECRET_KEY is required")
        except ConfigurationError as e:
            errors.append(f"WebApp configuration: {str(e)}")
        
        # Validate MySQL database configuration
        try:
            database_url = self.storage.database_url
            if not database_url:
                errors.append("DATABASE_URL is required")
            elif not database_url.startswith("mysql+pymysql://"):
                if database_url.startswith("MySQL://"):
                    errors.append("MySQL is deprecated. Please use MySQL database. Set DATABASE_URL to a MySQL connection string.")
                else:
                    errors.append("DATABASE_URL must be a MySQL connection string starting with 'mysql+pymysql://'")
            else:
                # Validate MySQL URL format
                if "charset=utf8mb4" not in database_url:
                    logging.warning("MySQL DATABASE_URL should include 'charset=utf8mb4' for proper Unicode support")
                
                # Check for required MySQL connection parameters
                if "@" not in database_url or "/" not in database_url.split("@")[-1]:
                    errors.append("DATABASE_URL must include host and database name in format: mysql+pymysql://user:password@host/database")
        except Exception as e:
            errors.append(f"MySQL database configuration: {str(e)}")
        
        # Validate other critical configuration
        try:
            if not os.getenv("PLATFORM_ENCRYPTION_KEY"):
                errors.append("PLATFORM_ENCRYPTION_KEY is required for platform credential encryption")
        except Exception as e:
            errors.append(f"Platform encryption configuration: {str(e)}")
        
        return errors
    
    def reload_configuration(self):
        """
        Reload configuration from environment variables and re-validate.
        
        Raises:
            ConfigurationError: If configuration is invalid after reload
        """
        # Reload environment variables
        load_dotenv(override=True)
        
        # Reinitialize configuration components
        try:
            self.activitypub = ActivityPubConfig.from_env()
        except ConfigurationError as e:
            # Allow empty config for database-stored connections
            if "ACTIVITYPUB_INSTANCE_URL is required" in str(e) or "ACTIVITYPUB_ACCESS_TOKEN is required" in str(e):
                self.activitypub = ActivityPubConfig(
                    instance_url="",
                    access_token="",
                    api_type="pixelfed",
                    retry=RetryConfig.from_env(),
                    rate_limit=RateLimitConfig.from_env()
                )
            else:
                raise
        
        self.ollama = OllamaConfig.from_env()
        self.caption = CaptionConfig.from_env()
        self.storage = StorageConfig.from_env()
        self.webapp = WebAppConfig.from_env()
        self.auth = AuthConfig.from_env()
        self.batch_update = BatchUpdateConfig.from_env()
        
        # Update derived configuration
        self.use_batch_updates = self.batch_update.enabled
        self.batch_size = self.batch_update.batch_size
        self.max_concurrent_batches = self.batch_update.max_concurrent_batches
        self.verification_delay = self.batch_update.verification_delay
        self.rollback_on_failure = self.batch_update.rollback_on_failure
        self.max_posts_per_run = int(os.getenv("MAX_POSTS_PER_RUN", "50"))
        self.max_users_per_run = int(os.getenv("MAX_USERS_PER_RUN", "10"))
        self.user_processing_delay = int(os.getenv("USER_PROCESSING_DELAY", "5"))
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Reset session config to force reload
        self._session_config = None
        
        # Validate the reloaded configuration
        validation_errors = self.validate_configuration()
        if validation_errors:
            raise ConfigurationError(f"Configuration validation failed after reload: {'; '.join(validation_errors)}")
    
    def get_configuration_status(self) -> dict:
        """
        Get comprehensive configuration status information.
        
        Returns:
            Dictionary containing configuration status and validation results
        """
        validation_errors = self.validate_configuration()
        
        return {
            'valid': len(validation_errors) == 0,
            'errors': validation_errors,
            'activitypub': {
                'configured': bool(self.activitypub.instance_url and self.activitypub.access_token),
                'api_type': self.activitypub.api_type,
                'instance_url': self.activitypub.instance_url or 'Not configured',
                'has_access_token': bool(self.activitypub.access_token),
                'mastodon_credentials': {
                    'has_client_key': bool(self.activitypub.client_key),
                    'has_client_secret': bool(self.activitypub.client_secret)
                } if self.activitypub.api_type == 'mastodon' else None
            },
            'webapp': {
                'configured': bool(self.webapp.secret_key),
                'host': self.webapp.host,
                'port': self.webapp.port,
                'debug': self.webapp.debug
            },
            'ollama': {
                'url': self.ollama.url,
                'model': self.ollama.model_name,
                'timeout': self.ollama.timeout
            },
            'storage': {
                'base_dir': self.storage.base_dir,
                'database_url': self.storage.database_url
            }
        }