#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Configuration validation script for Vedfolnir.

This script validates your configuration and provides helpful error messages
for common configuration issues.
"""

import os
import sys
from dotenv import load_dotenv

def main():
    """Validate configuration and provide helpful feedback"""
    print("Vedfolnir Configuration Validator")
    print("=" * 40)
    
    # Load environment variables
    if os.path.exists('.env'):
        load_dotenv()
        print("✓ Found .env file")
    else:
        print("⚠ No .env file found. Using environment variables only.")
    
    try:
        from config import Config, ConfigurationError
        
        print("\nValidating configuration...")
        config = Config()
        
        print("✓ Configuration loaded successfully!")
        print(f"✓ Platform: {config.activitypub.api_type}")
        print(f"✓ Instance: {config.activitypub.instance_url}")
        print(f"✓ Username: {config.activitypub.username}")
        
        # Platform-specific validation feedback
        if config.activitypub.api_type == 'mastodon':
            if config.activitypub.client_key and config.activitypub.client_secret:
                print("✓ Mastodon OAuth2 credentials configured")
            else:
                print("⚠ Mastodon OAuth2 credentials missing")
        elif config.activitypub.api_type == 'pixelfed':
            print("✓ Pixelfed configuration valid")
        
        # Check Ollama configuration
        print(f"✓ Ollama URL: {config.ollama.url}")
        print(f"✓ Ollama Model: {config.ollama.model_name}")
        
        # Check optional configurations
        print(f"✓ Max posts per run: {config.max_posts_per_run}")
        print(f"✓ Log level: {config.log_level}")
        print(f"✓ Dry run mode: {config.dry_run}")
        
        print("\n🎉 Configuration validation successful!")
        print("\nYou can now run the Vedfolnir with:")
        print("  python main.py --users your_username")
        
        return 0
        
    except ConfigurationError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nCommon solutions:")
        
        error_msg = str(e).lower()
        
        if 'mastodon_client_key' in error_msg:
            print("- Create a Mastodon application at your instance's settings")
            print("- Copy the client key and secret to your .env file")
            print("- Ensure ACTIVITYPUB_API_TYPE=mastodon")
        elif 'mastodon_client_secret' in error_msg:
            print("- Create a Mastodon application at your instance's settings")
            print("- Copy the client key and secret to your .env file")
        elif 'instance_url' in error_msg:
            print("- Set ACTIVITYPUB_INSTANCE_URL to your full instance URL")
            print("- Example: ACTIVITYPUB_INSTANCE_URL=https://mastodon.social")
        elif 'access_token' in error_msg:
            print("- Set ACTIVITYPUB_ACCESS_TOKEN to your API access token")
            print("- For Mastodon: Get this from your application settings")
            print("- For Pixelfed: Generate this in your account settings")
        elif 'unsupported' in error_msg and 'api_type' in error_msg:
            print("- Set ACTIVITYPUB_API_TYPE to either 'pixelfed' or 'mastodon'")
        
        print(f"\nFor more help, see the configuration section in README.md")
        return 1
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("Make sure you have installed all dependencies:")
        print("  pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("Please check your configuration and try again.")
        return 1

if __name__ == '__main__':
    sys.exit(main())