# HashiCorp Vault Integration for Vedfolnir

This directory contains the HashiCorp Vault integration for secure secrets management in the Vedfolnir Docker Compose deployment.

## Overview

The Vault integration provides:
- **Secure secrets storage** - All sensitive data stored in Vault
- **Dynamic database credentials** - Auto-rotating MySQL credentials
- **Encryption services** - Transit encryption for sensitive data
- **Secret rotation** - Automated secret rotation without container rebuilds
- **Docker secrets integration** - Seamless integration with Docker secrets

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vault Server  │    │ Secret Rotation │    │ Docker Secrets  │
│                 │    │    Service      │    │  Integration    │
│ - KV v2 Store   │◄──►│                 │◄──►│                 │
│ - Database Eng. │    │ - Auto Rotation │    │ - File Sync     │
│ - Transit Eng.  │    │ - Notifications │    │ - Validation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                        ▲                        ▲
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Vedfolnir Application                        │
│                                                                 │
│ - Reads secrets from Docker secrets files                      │
│ - Uses dynamic database credentials                             │
│ - Encrypts platform credentials with Transit                   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Vault Server (`vault.hcl`)
- File-based storage backend
- HTTP API listener (port 8200)
- Audit logging enabled
- UI interface available

### 2. Vault Client (`vault-client.py`)
- Python client for Vault operations
- Automatic token renewal
- Error handling and retries
- Support for all Vault engines

### 3. Secret Rotation (`secret-rotation.py`)
- Automated secret rotation based on age
- Configurable rotation intervals
- Notification support (webhooks, email)
- Backup before rotation

### 4. Docker Secrets Integration (`docker-secrets-integration.py`)
- Syncs Vault secrets to Docker secret files
- Validates secret availability
- Manages file permissions
- Health monitoring

### 5. Test Suite (`test-vault-integration.py`)
- Comprehensive integration tests
- Connectivity and authentication tests
- Secret operations validation
- End-to-end workflow testing

## Quick Start

### 1. Setup Vault
```bash
# Initialize Vault and create directories
./scripts/vault-management.sh setup

# Start Vault services
./scripts/vault-management.sh start
```

### 2. Verify Installation
```bash
# Run comprehensive tests
./scripts/test-vault-setup.sh

# Check Vault status
./scripts/vault-management.sh status
```

### 3. Check Secrets
```bash
# View secret rotation status
./scripts/vault-management.sh check-secrets

# View logs
./scripts/vault-management.sh logs
```

## Configuration

### Rotation Configuration (`config/vault/rotation-config.json`)
```json
{
  "secrets": {
    "flask": {
      "rotation_interval_days": 90,
      "notify_before_days": 7
    },
    "platform": {
      "rotation_interval_days": 90,
      "notify_before_days": 7
    },
    "redis": {
      "rotation_interval_days": 30,
      "notify_before_days": 3
    }
  },
  "database_credentials": {
    "rotation_interval_hours": 24,
    "notify_before_hours": 2
  }
}
```

### Environment Variables
```bash
# Vault configuration
VAULT_ADDR=http://vault:8200
VAULT_TOKEN_FILE=/vault/data/vedfolnir-token.txt

# Rotation configuration
ROTATION_CONFIG_FILE=/vault/config/rotation-config.json
ROTATION_WEBHOOK_URL=https://hooks.slack.com/...

# Database configuration
MYSQL_ROOT_PASSWORD=<generated>
REDIS_PASSWORD=<generated>
```

## Secrets Management

### Application Secrets
- **Flask Secret Key** (`vedfolnir/flask`)
  - Used for session encryption
  - Rotated every 90 days
  - Automatically synced to Docker secrets

- **Platform Encryption Key** (`vedfolnir/platform`)
  - Used for platform credential encryption
  - Rotated every 90 days
  - Fernet-compatible key format

- **Redis Password** (`vedfolnir/redis`)
  - Used for Redis authentication
  - Rotated every 30 days
  - Automatically applied to Redis container

### Dynamic Database Credentials
- **MySQL Credentials** (`database/creds/vedfolnir-role`)
  - Generated on-demand
  - Rotated every 24 hours
  - Full privileges on vedfolnir database

### Transit Encryption
- **Encryption Key** (`transit/keys/vedfolnir-encryption`)
  - Used for encrypting sensitive data
  - Automatic key rotation
  - Versioned encryption support

## Operations

### Manual Secret Rotation
```bash
# Rotate specific secret
./scripts/vault-management.sh rotate flask

# Rotate all secrets that need it
./scripts/vault-management.sh rotate

# Check what needs rotation
./scripts/vault-management.sh check-secrets
```

### Backup and Restore
```bash
# Create backup
./scripts/vault-management.sh backup

# Restore from backup
./scripts/vault-management.sh restore /path/to/backup.tar.gz
```

### Monitoring
```bash
# Check overall status
./scripts/vault-management.sh status

# View logs
./scripts/vault-management.sh logs

# Run health checks
./scripts/test-vault-setup.sh
```

## Security Features

### Access Control
- **Application Token** - Limited permissions for Vedfolnir
- **Admin Token** - Full access for management operations
- **Policy-based Access** - Granular permission control

### Audit Logging
- All Vault operations logged
- Immutable audit trail
- Structured JSON format
- Retention policies applied

### Encryption
- **Data at Rest** - All secrets encrypted in Vault
- **Data in Transit** - TLS for API communication
- **Transit Encryption** - Application-level encryption service

### Secret Rotation
- **Automated Rotation** - Based on configurable intervals
- **Zero-downtime** - No service interruption during rotation
- **Verification** - Automatic validation after rotation
- **Rollback** - Ability to revert to previous versions

## Troubleshooting

### Common Issues

#### Vault Not Starting
```bash
# Check Vault logs
./scripts/vault-management.sh logs vault

# Verify configuration
docker exec vedfolnir_vault vault status

# Check file permissions
ls -la data/vault/
```

#### Authentication Failures
```bash
# Check token validity
export VAULT_TOKEN=$(cat data/vault/vedfolnir-token.txt)
curl -H "X-Vault-Token: $VAULT_TOKEN" http://localhost:8200/v1/auth/token/lookup-self

# Regenerate token if needed
./scripts/vault-management.sh restart
```

#### Secret Sync Issues
```bash
# Manual secret sync
docker exec vedfolnir_vault_secrets python /app/docker-secrets-integration.py --sync

# Check secret files
ls -la data/vault/secrets/

# Validate secrets
docker exec vedfolnir_vault_secrets python /app/docker-secrets-integration.py --validate
```

#### Database Connection Issues
```bash
# Get new database credentials
docker exec vedfolnir_vault_secrets python /app/docker-secrets-integration.py --sync

# Check database URL
cat data/vault/secrets/database_url.txt

# Test database connection
docker exec vedfolnir_mysql mysql -u $(cat data/vault/secrets/mysql_user.txt) -p$(cat data/vault/secrets/mysql_password.txt) -e "SELECT 1"
```

### Debug Mode
```bash
# Enable debug logging
export VAULT_LOG_LEVEL=debug

# Run tests with verbose output
./scripts/test-vault-setup.sh all

# Check service health
docker exec vedfolnir_vault_secrets python /app/docker-secrets-integration.py --health
```

## Integration with Vedfolnir

### Application Configuration
The Vedfolnir application reads secrets from Docker secret files:

```python
# Example: Reading Flask secret key
def get_flask_secret():
    secret_file = '/run/secrets/flask_secret_key'
    if os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            return f.read().strip()
    return os.getenv('FLASK_SECRET_KEY')  # Fallback
```

### Database Connection
Dynamic database credentials are automatically generated and rotated:

```python
# Example: Database URL from Vault
def get_database_url():
    url_file = '/run/secrets/database_url'
    if os.path.exists(url_file):
        with open(url_file, 'r') as f:
            return f.read().strip()
    return os.getenv('DATABASE_URL')  # Fallback
```

### Platform Encryption
Platform credentials are encrypted using Vault's Transit engine:

```python
# Example: Encrypt platform credentials
from vault_client import VaultClient

client = VaultClient()
encrypted_creds = client.encrypt_data(json.dumps(credentials))
```

## Monitoring and Alerting

### Health Checks
- Vault server health endpoint
- Secret file validation
- Token expiration monitoring
- Service dependency checks

### Metrics
- Secret rotation frequency
- Token renewal success rate
- Database credential usage
- Encryption operation latency

### Notifications
- Secret rotation alerts
- Token expiration warnings
- Service health changes
- Security event notifications

## Best Practices

### Security
1. **Rotate secrets regularly** - Use automated rotation
2. **Monitor access** - Review audit logs regularly
3. **Limit permissions** - Use least-privilege access
4. **Backup regularly** - Maintain secure backups

### Operations
1. **Test rotations** - Verify rotation procedures work
2. **Monitor health** - Use health checks and alerts
3. **Document procedures** - Keep runbooks updated
4. **Plan for disasters** - Have recovery procedures ready

### Development
1. **Use environment-specific tokens** - Different tokens for dev/prod
2. **Test integration** - Run integration tests regularly
3. **Handle failures gracefully** - Implement fallback mechanisms
4. **Log appropriately** - Don't log sensitive data

## Support

For issues with the Vault integration:

1. **Check logs** - `./scripts/vault-management.sh logs`
2. **Run tests** - `./scripts/test-vault-setup.sh`
3. **Verify configuration** - Check environment variables and files
4. **Review documentation** - This README and inline comments
5. **Check Vault status** - `./scripts/vault-management.sh status`

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault API Reference](https://www.vaultproject.io/api-docs)
- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Vedfolnir Docker Compose Migration Spec](.kiro/specs/docker-compose-migration/)