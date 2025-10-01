#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Setup script for generating secure secrets for Vedfolnir Docker deployment

set -e

echo "=== Vedfolnir Docker Secrets Setup ==="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required for secret generation"
    exit 1
fi

# Create secrets directory if it doesn't exist
mkdir -p secrets

echo "Generating secure secrets..."

# Generate Flask secret key
echo "Generating Flask secret key..."
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/flask_secret_key.txt
echo "✅ Flask secret key generated"

# Generate platform encryption key (Fernet key)
echo "Generating platform encryption key..."
python3 -c "
try:
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())
except ImportError:
    print('ERROR: cryptography package not installed')
    print('Install with: pip install cryptography')
    exit(1)
" > secrets/platform_encryption_key.txt

if [ $? -eq 0 ]; then
    echo "✅ Platform encryption key generated"
else
    echo "❌ Failed to generate platform encryption key"
    echo "Install cryptography package: pip install cryptography"
    exit 1
fi

# Generate database passwords
echo "Generating MySQL root password..."
python3 -c "import secrets; print(secrets.token_urlsafe(24))" > secrets/mysql_root_password.txt
echo "✅ MySQL root password generated"

echo "Generating MySQL user password..."
python3 -c "import secrets; print(secrets.token_urlsafe(24))" > secrets/mysql_password.txt
echo "✅ MySQL user password generated"

# Generate Redis password
echo "Generating Redis password..."
python3 -c "import secrets; print(secrets.token_urlsafe(24))" > secrets/redis_password.txt
echo "✅ Redis password generated"

# Generate Vault token
echo "Generating Vault root token..."
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > secrets/vault_token.txt
echo "✅ Vault root token generated"

# Set secure permissions
echo "Setting secure file permissions..."
chmod 600 secrets/*.txt
echo "✅ File permissions set to 600"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.docker .env
    
    # Update .env with generated passwords
    MYSQL_PASSWORD=$(cat secrets/mysql_password.txt)
    MYSQL_ROOT_PASSWORD=$(cat secrets/mysql_root_password.txt)
    REDIS_PASSWORD=$(cat secrets/redis_password.txt)
    VAULT_ROOT_TOKEN=$(cat secrets/vault_token.txt)
    
    # Replace placeholders in .env
    sed -i.bak "s/your_secure_mysql_password_here/$MYSQL_PASSWORD/g" .env
    sed -i.bak "s/your_secure_mysql_root_password_here/$MYSQL_ROOT_PASSWORD/g" .env
    sed -i.bak "s/your_secure_redis_password_here/$REDIS_PASSWORD/g" .env
    sed -i.bak "s/your_vault_root_token_here/$VAULT_ROOT_TOKEN/g" .env
    
    # Generate Grafana admin password
    GRAFANA_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
    sed -i.bak "s/your_grafana_admin_password_here/$GRAFANA_PASSWORD/g" .env
    
    # Remove backup file
    rm .env.bak
    
    echo "✅ .env file created and configured"
    echo "📝 Grafana admin password: $GRAFANA_PASSWORD"
else
    echo "⚠️  .env file already exists - not overwriting"
fi

echo ""
echo "=== Setup Complete ==="
echo "✅ All secrets have been generated"
echo "✅ File permissions have been secured"
echo "✅ Environment configuration is ready"
echo ""
echo "Next steps:"
echo "1. Review and customize .env file if needed"
echo "2. Generate SSL certificates (see DOCKER_SETUP.md)"
echo "3. Run: docker-compose up -d"
echo ""
echo "⚠️  IMPORTANT: Keep the secrets/ directory secure and backed up!"
echo "⚠️  Do not commit secrets to version control!"