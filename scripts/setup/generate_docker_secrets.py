#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Generate Docker secrets for Vedfolnir Docker Compose deployment.
This script creates secure random values for all required secrets.
"""

import os
import secrets
import string
from pathlib import Path
from cryptography.fernet import Fernet

def generate_password(length=32, include_symbols=True):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits
    if include_symbols:
        alphabet += "!@#$%^&*"
    
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def generate_flask_secret_key():
    """Generate a Flask secret key."""
    return secrets.token_urlsafe(32)

def generate_platform_encryption_key():
    """Generate a Fernet encryption key for platform credentials."""
    return Fernet.generate_key().decode()

def generate_vault_token():
    """Generate a Vault root token."""
    return secrets.token_urlsafe(32)

def create_secrets_directory():
    """Create the secrets directory if it doesn't exist."""
    secrets_dir = Path("secrets")
    secrets_dir.mkdir(exist_ok=True)
    
    # Set restrictive permissions on secrets directory
    os.chmod(secrets_dir, 0o700)
    
    return secrets_dir

def write_secret_file(secrets_dir, filename, content):
    """Write a secret to a file with secure permissions."""
    secret_file = secrets_dir / filename
    
    with open(secret_file, 'w') as f:
        f.write(content)
    
    # Set restrictive permissions on secret file
    os.chmod(secret_file, 0o600)
    
    print(f"✅ Generated {filename}")

def main():
    """Generate all Docker secrets."""
    print("🔐 Generating Docker secrets for Vedfolnir...")
    print()
    
    # Create secrets directory
    secrets_dir = create_secrets_directory()
    
    # Generate Flask secret key
    flask_secret = generate_flask_secret_key()
    write_secret_file(secrets_dir, "flask_secret_key.txt", flask_secret)
    
    # Generate platform encryption key
    platform_key = generate_platform_encryption_key()
    write_secret_file(secrets_dir, "platform_encryption_key.txt", platform_key)
    
    # Generate MySQL passwords
    mysql_root_password = generate_password(32)
    write_secret_file(secrets_dir, "mysql_root_password.txt", mysql_root_password)
    
    mysql_password = generate_password(32)
    write_secret_file(secrets_dir, "mysql_password.txt", mysql_password)
    
    # Generate Redis password
    redis_password = generate_password(32)
    write_secret_file(secrets_dir, "redis_password.txt", redis_password)
    
    # Generate Vault token
    vault_token = generate_vault_token()
    write_secret_file(secrets_dir, "vault_token.txt", vault_token)
    
    print()
    print("🎉 All Docker secrets generated successfully!")
    print()
    print("📋 Next steps:")
    print("1. Copy .env.docker to .env: cp .env.docker .env")
    print("2. Update .env with the following values:")
    print()
    print(f"MYSQL_ROOT_PASSWORD={mysql_root_password}")
    print(f"MYSQL_PASSWORD={mysql_password}")
    print(f"REDIS_PASSWORD={redis_password}")
    print(f"FLASK_SECRET_KEY={flask_secret}")
    print(f"PLATFORM_ENCRYPTION_KEY={platform_key}")
    print(f"VAULT_ROOT_TOKEN={vault_token}")
    print()
    print("3. Start Docker Compose: docker-compose up -d")
    print("4. Check service health: docker-compose ps")
    print()
    print("⚠️  SECURITY WARNING:")
    print("- Keep the secrets/ directory secure (permissions: 700)")
    print("- Never commit secrets to version control")
    print("- Rotate secrets regularly in production")
    print("- Use external secret management for production deployments")

if __name__ == "__main__":
    main()