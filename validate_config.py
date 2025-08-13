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
        'PLATFORM_ENCRYPTION_KEY': 'Encryption key for platform credentials',
        'DATABASE_URL': 'Database connection URL'
    }
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            errors.append(f"Missing required variable: {var} ({description})")
        elif var == 'FLASK_SECRET_KEY' and 'CHANGE_ME' in value:
            errors.append(f"Please change the default value for {var}")
        elif var == 'PLATFORM_ENCRYPTION_KEY' and 'CHANGE_ME' in value:
            errors.append(f"Please change the default value for {var}")
    
    # Optional but recommended configuration
    recommended_vars = {
        'OLLAMA_URL': 'http://localhost:11434',
        'OLLAMA_MODEL': 'llava:7b',
        'LOG_LEVEL': 'INFO'
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
    if database_url and not database_url.startswith('sqlite://'):
        warnings.append("Only SQLite databases are currently supported")
    
    return errors, warnings

def validate_deprecated_platform_config():
    """Check for deprecated platform configuration in environment"""
    warnings = []
    
    deprecated_vars = [
        'ACTIVITYPUB_API_TYPE',
        'ACTIVITYPUB_INSTANCE_URL',
        'ACTIVITYPUB_USERNAME', 
        'ACTIVITYPUB_ACCESS_TOKEN',
        'MASTODON_CLIENT_KEY',
        'MASTODON_CLIENT_SECRET'
    ]
    
    found_deprecated = []
    for var in deprecated_vars:
        if os.getenv(var):
            found_deprecated.append(var)
    
    if found_deprecated:
        warnings.append("Found deprecated platform configuration variables in environment:")
        for var in found_deprecated:
            warnings.append(f"  - {var}")
        warnings.append("Platform configuration is now managed via the web interface.")
        warnings.append("Please remove these variables from your .env file and configure")
        warnings.append("platforms through the web interface instead.")
    
    return warnings

def main():
    """Main validation function"""
    print("Validating Vedfolnir configuration...")
    print("=" * 50)
    
    # Validate core configuration
    errors, warnings = validate_core_config()
    
    # Check for deprecated platform configuration
    deprecated_warnings = validate_deprecated_platform_config()
    warnings.extend(deprecated_warnings)
    
    # Display results
    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"  • {error}")
        print()
    
    if warnings:
        print("⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"  • {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ Configuration validation successful!")
        print("All required configuration is present and valid.")
    elif not errors:
        print("✅ Configuration validation successful!")
        print("Core configuration is valid, but there are some warnings above.")
    else:
        print("❌ Configuration validation failed!")
        print("Please fix the errors above before running the application.")
        return 1
    
    print()
    print("Platform Configuration:")
    print("Platform connections (Pixelfed, Mastodon) are now managed via the web interface.")
    print("Start the web application and go to Platform Management to configure your connections.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())