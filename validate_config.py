#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Configuration validation script for Vedfolnir.

This script validates the configuration to ensure all required settings are present
and properly formatted. Since platform-specific configurations are now managed
via the web interface and stored in the database, this script focuses on validating
the core application configuration.
"""

import os
import sys
from dotenv import load_dotenv

def validate_core_config():
    """Validate core application configuration"""
    errors = []
    warnings = []
    
    # Load environment variables
    load_dotenv()
    
    # Required core configuration
    required_vars = {
        'FLASK_SECRET_KEY': 'Flask secret key for session security',
        'PLATFORM_ENCRYPTION_KEY': 'Encryption key for platform credentials'
    }
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or not value.strip():
            errors.append(f"Missing required variable: {var} ({description})")
        elif var == 'FLASK_SECRET_KEY' and ('CHANGE_ME' in value or len(value.strip()) < 16):
            errors.append(f"Please set a secure value for {var} (minimum 16 characters)")
        elif var == 'PLATFORM_ENCRYPTION_KEY' and ('CHANGE_ME' in value or len(value.strip()) < 16):
            errors.append(f"Please set a secure value for {var} (minimum 16 characters)")
    
    # Optional but recommended configuration
    recommended_vars = {
        'OLLAMA_URL': 'http://localhost:11434',
        'OLLAMA_MODEL': 'llava:7b',
        'LOG_LEVEL': 'INFO',
        'DATABASE_URL': 'mysql+pymysql://vedfolnir_user:vedfolnir_password@localhost/vedfolnir?charset=utf8mb4',
        'STORAGE_WARNING_THRESHOLD': '80',
        'STORAGE_MONITORING_ENABLED': 'true'
    }
    
    for var, default in recommended_vars.items():
        value = os.getenv(var)
        if not value:
            warnings.append(f"Using default value for {var}: {default}")
    
    # Validate specific values
    flask_port = os.getenv('FLASK_PORT', '5000')
    try:
        port = int(flask_port)
        if port < 1 or port > 65535:
            errors.append(f"FLASK_PORT must be between 1 and 65535, got: {port}")
    except ValueError:
        errors.append(f"FLASK_PORT must be a valid integer, got: {flask_port}")
    
    # Check database URL format
    database_url = os.getenv('DATABASE_URL')
    if database_url and not database_url.startswith('MySQL://'):
        warnings.append("Only MySQL databases are currently supported")
    
    # Validate numeric configuration values
    numeric_configs = {
        'OLLAMA_TIMEOUT': (1, 300, 'Ollama timeout in seconds'),
        'MAX_POSTS_PER_RUN': (1, 1000, 'Maximum posts per run'),
        'MAX_USERS_PER_RUN': (1, 100, 'Maximum users per run'),
        'USER_PROCESSING_DELAY': (0, 60, 'User processing delay in seconds'),
        'CAPTION_MAX_STORAGE_GB': (0.1, 1000, 'Maximum storage for images in GB'),
        'STORAGE_WARNING_THRESHOLD': (1, 100, 'Storage warning threshold percentage')
    }
    
    for var, (min_val, max_val, description) in numeric_configs.items():
        value = os.getenv(var)
        if value:
            try:
                # Try float first, then convert to int for validation
                float_val = float(value)
                num_val = int(float_val)
                if num_val < min_val or num_val > max_val:
                    errors.append(f"{var} must be between {min_val} and {max_val}, got: {num_val}")
            except ValueError:
                errors.append(f"{var} must be a valid number, got: {value}")
    
    return errors, warnings

def validate_platform_config():
    """Validate platform-specific configuration if present"""
    errors = []
    warnings = []
    
    # Check if platform configuration is present
    api_type = os.getenv('ACTIVITYPUB_API_TYPE')
    instance_url = os.getenv('ACTIVITYPUB_INSTANCE_URL')
    access_token = os.getenv('ACTIVITYPUB_ACCESS_TOKEN')
    
    if api_type or instance_url or access_token:
        # Platform configuration is present, validate it
        if not instance_url or not instance_url.strip():
            errors.append("ACTIVITYPUB_INSTANCE_URL is required when platform configuration is provided")
        
        if not access_token or not access_token.strip():
            errors.append("ACTIVITYPUB_ACCESS_TOKEN is required when platform configuration is provided")
        
        if api_type:
            api_type = api_type.lower().strip()
            if api_type not in ['pixelfed', 'mastodon']:
                errors.append(f"ACTIVITYPUB_API_TYPE must be 'pixelfed' or 'mastodon', got: {api_type}")
            
            # Validate Mastodon-specific configuration
            if api_type == 'mastodon':
                # For Mastodon, only access token is required
                # Client credentials are optional and only needed for certain OAuth2 flows
                client_key = os.getenv('MASTODON_CLIENT_KEY')
                client_secret = os.getenv('MASTODON_CLIENT_SECRET')
                
                if client_key and not client_secret:
                    warnings.append("MASTODON_CLIENT_KEY provided but MASTODON_CLIENT_SECRET is missing")
                elif client_secret and not client_key:
                    warnings.append("MASTODON_CLIENT_SECRET provided but MASTODON_CLIENT_KEY is missing")
        
        # Validate instance URL format
        if instance_url:
            if not instance_url.startswith(('http://', 'https://')):
                errors.append("ACTIVITYPUB_INSTANCE_URL must start with http:// or https://")
    else:
        warnings.append("No platform configuration found in environment variables.")
        warnings.append("Platform connections will be managed via the web interface.")
    
    return errors, warnings

def validate_deprecated_platform_config():
    """Check for deprecated platform configuration patterns"""
    warnings = []
    
    # Check for legacy configuration patterns
    legacy_vars = [
        'ACTIVITYPUB_PLATFORM_TYPE',
        'PIXELFED_API'
    ]
    
    found_legacy = []
    for var in legacy_vars:
        if os.getenv(var):
            found_legacy.append(var)
    
    if found_legacy:
        warnings.append("Found legacy platform configuration variables:")
        for var in found_legacy:
            warnings.append(f"  - {var}")
        warnings.append("Please update to use ACTIVITYPUB_API_TYPE instead.")
    
    # Check if platform configuration is present but incomplete
    api_type = os.getenv('ACTIVITYPUB_API_TYPE')
    instance_url = os.getenv('ACTIVITYPUB_INSTANCE_URL')
    access_token = os.getenv('ACTIVITYPUB_ACCESS_TOKEN')
    
    if (api_type or instance_url or access_token):
        # Platform configuration is present
        if api_type == 'mastodon':
            client_key = os.getenv('MASTODON_CLIENT_KEY')
            client_secret = os.getenv('MASTODON_CLIENT_SECRET')
            
            if not client_key or not client_secret:
                warnings.append("Found deprecated platform configuration approach:")
                warnings.append("Platform configuration in environment variables is deprecated.")
                warnings.append("Please configure platforms via the web interface instead.")
    
    return warnings

def main():
    """Main validation function"""
    print("Validating Vedfolnir configuration...")
    print("=" * 50)
    
    all_errors = []
    all_warnings = []
    
    # Validate core configuration
    core_errors, core_warnings = validate_core_config()
    all_errors.extend(core_errors)
    all_warnings.extend(core_warnings)
    
    # Validate platform configuration if present
    platform_errors, platform_warnings = validate_platform_config()
    all_errors.extend(platform_errors)
    all_warnings.extend(platform_warnings)
    
    # Check for deprecated platform configuration
    deprecated_warnings = validate_deprecated_platform_config()
    all_warnings.extend(deprecated_warnings)
    
    # Test configuration loading
    try:
        from config import Config
        config = Config()
        config_status = config.get_configuration_status()
        
        if not config_status['valid']:
            all_errors.extend([f"Configuration validation: {error}" for error in config_status['errors']])
        
        print("Configuration Status:")
        print(f"  • ActivityPub: {'✅ Configured' if config_status['activitypub']['configured'] else '⚠️  Not configured'}")
        print(f"  • Web App: {'✅ Configured' if config_status['webapp']['configured'] else '❌ Missing secret key'}")
        print(f"  • Ollama: {config_status['ollama']['url']} ({config_status['ollama']['model']})")
        print()
        
    except Exception as e:
        all_errors.append(f"Failed to load configuration: {str(e)}")
    
    # Display results
    if all_errors:
        print("❌ Configuration Errors:")
        for error in all_errors:
            print(f"  • {error}")
        print()
    
    if all_warnings:
        print("⚠️  Configuration Warnings:")
        for warning in all_warnings:
            print(f"  • {warning}")
        print()
    
    if not all_errors and not all_warnings:
        print("✅ Configuration validation successful!")
        print("All required configuration is present and valid.")
    elif not all_errors:
        print("✅ Configuration validation successful!")
        print("Core configuration is valid, but there are some warnings above.")
    else:
        print("❌ Configuration validation failed!")
        print("Please fix the errors above before running the application.")
        return 1
    
    print()
    print("Next Steps:")
    if not all_errors:
        print("• Start the web application: python web_app.py")
        print("• Configure platform connections via the web interface")
        print("• Run the bot: python main.py --users <username>")
    else:
        print("• Fix the configuration errors listed above")
        print("• Copy .env.example to .env and configure your settings")
        print("• Run this validation script again to verify fixes")
    
    return 1 if all_errors else 0

if __name__ == '__main__':
    sys.exit(main())