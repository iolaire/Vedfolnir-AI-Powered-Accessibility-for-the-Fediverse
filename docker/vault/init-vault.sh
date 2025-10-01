#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vault Initialization Script for Vedfolnir
# This script initializes and configures Vault with necessary secrets engines and policies

set -e

VAULT_ADDR="http://vault:8200"
VAULT_INIT_FILE="/vault/data/vault-init.json"
VAULT_UNSEAL_KEYS_FILE="/vault/data/unseal-keys.json"

echo "=== Vault Initialization Script ==="

# Wait for Vault to be ready
echo "Waiting for Vault to be ready..."
until curl -s "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; do
    echo "Waiting for Vault..."
    sleep 2
done

echo "Vault is ready!"

# Check if Vault is already initialized
if [ -f "$VAULT_INIT_FILE" ]; then
    echo "Vault already initialized. Loading existing configuration..."
    export VAULT_TOKEN=$(cat "$VAULT_INIT_FILE" | jq -r '.root_token')
else
    echo "Initializing Vault..."
    
    # Initialize Vault with 5 key shares and threshold of 3
    vault operator init \
        -key-shares=5 \
        -key-threshold=3 \
        -format=json > "$VAULT_INIT_FILE"
    
    echo "Vault initialized successfully!"
    
    # Extract unseal keys and root token
    cat "$VAULT_INIT_FILE" | jq -r '.unseal_keys_b64[]' > "$VAULT_UNSEAL_KEYS_FILE"
    export VAULT_TOKEN=$(cat "$VAULT_INIT_FILE" | jq -r '.root_token')
    
    echo "Root token and unseal keys saved securely."
fi

# Unseal Vault
echo "Unsealing Vault..."
UNSEAL_KEY_1=$(cat "$VAULT_INIT_FILE" | jq -r '.unseal_keys_b64[0]')
UNSEAL_KEY_2=$(cat "$VAULT_INIT_FILE" | jq -r '.unseal_keys_b64[1]')
UNSEAL_KEY_3=$(cat "$VAULT_INIT_FILE" | jq -r '.unseal_keys_b64[2]')

vault operator unseal "$UNSEAL_KEY_1"
vault operator unseal "$UNSEAL_KEY_2"
vault operator unseal "$UNSEAL_KEY_3"

echo "Vault unsealed successfully!"

# Authenticate with root token
vault auth "$VAULT_TOKEN"

# Enable audit logging
echo "Enabling audit logging..."
vault audit enable file file_path=/vault/logs/audit.log || echo "Audit logging already enabled"

# Enable secrets engines
echo "Enabling secrets engines..."

# Enable KV v2 secrets engine for application secrets
vault secrets enable -path=vedfolnir kv-v2 || echo "KV secrets engine already enabled"

# Enable database secrets engine for dynamic credentials
vault secrets enable database || echo "Database secrets engine already enabled"

# Enable transit secrets engine for encryption
vault secrets enable transit || echo "Transit secrets engine already enabled"

# Configure database secrets engine for MySQL
echo "Configuring database secrets engine..."
vault write database/config/mysql \
    plugin_name=mysql-database-plugin \
    connection_url="{{username}}:{{password}}@tcp(mysql:3306)/" \
    allowed_roles="vedfolnir-role" \
    username="root" \
    password="$MYSQL_ROOT_PASSWORD" || echo "Database config already exists"

# Create database role for Vedfolnir
vault write database/roles/vedfolnir-role \
    db_name=mysql \
    creation_statements="CREATE USER '{{name}}'@'%' IDENTIFIED BY '{{password}}';GRANT ALL PRIVILEGES ON vedfolnir.* TO '{{name}}'@'%';" \
    default_ttl="1h" \
    max_ttl="24h" || echo "Database role already exists"

# Configure transit encryption key
echo "Creating encryption keys..."
vault write -f transit/keys/vedfolnir-encryption || echo "Encryption key already exists"

# Create policies
echo "Creating Vault policies..."

# Application policy for Vedfolnir
vault policy write vedfolnir-policy - <<EOF
# Read application secrets
path "vedfolnir/data/*" {
  capabilities = ["read"]
}

# Read database credentials
path "database/creds/vedfolnir-role" {
  capabilities = ["read"]
}

# Use transit encryption
path "transit/encrypt/vedfolnir-encryption" {
  capabilities = ["update"]
}

path "transit/decrypt/vedfolnir-encryption" {
  capabilities = ["update"]
}

# Read own token info
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

# Renew own token
path "auth/token/renew-self" {
  capabilities = ["update"]
}
EOF

# Admin policy for secret management
vault policy write vedfolnir-admin-policy - <<EOF
# Full access to application secrets
path "vedfolnir/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage database secrets
path "database/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage transit encryption
path "transit/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage policies
path "sys/policies/acl/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage auth methods
path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

# System administration
path "sys/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
EOF

# Create application token
echo "Creating application token..."
VEDFOLNIR_TOKEN=$(vault write -field=token auth/token/create \
    policies="vedfolnir-policy" \
    ttl="720h" \
    renewable=true \
    display_name="vedfolnir-app")

# Save application token
echo "$VEDFOLNIR_TOKEN" > /vault/data/vedfolnir-token.txt
chmod 600 /vault/data/vedfolnir-token.txt

# Store initial secrets
echo "Storing initial application secrets..."

# Generate and store Flask secret key
FLASK_SECRET=$(openssl rand -base64 32)
vault kv put vedfolnir/flask secret_key="$FLASK_SECRET"

# Generate and store platform encryption key
PLATFORM_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
vault kv put vedfolnir/platform encryption_key="$PLATFORM_KEY"

# Store Redis password
vault kv put vedfolnir/redis password="$REDIS_PASSWORD"

# Store Ollama configuration
vault kv put vedfolnir/ollama \
    url="http://ollama:11434" \
    model="llava:7b" \
    timeout="300"

# Store monitoring configuration
vault kv put vedfolnir/monitoring \
    prometheus_url="http://prometheus:9090" \
    grafana_url="http://grafana:3000" \
    loki_url="http://loki:3100"

echo "=== Vault initialization completed successfully! ==="
echo "Root token: $VAULT_TOKEN"
echo "Application token saved to: /vault/data/vedfolnir-token.txt"
echo "Unseal keys saved to: $VAULT_INIT_FILE"
echo ""
echo "IMPORTANT: Save the root token and unseal keys in a secure location!"
echo "The application token will be used by Vedfolnir containers."