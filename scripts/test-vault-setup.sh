#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Test Script for Vault Integration
# Comprehensive testing of HashiCorp Vault setup and integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Test result functions
test_start() {
    ((TESTS_RUN++))
    log_info "Test $TESTS_RUN: $1"
}

test_pass() {
    ((TESTS_PASSED++))
    log_success "✅ PASS: $1"
}

test_fail() {
    ((TESTS_FAILED++))
    log_error "❌ FAIL: $1"
}

# Test Vault connectivity
test_vault_connectivity() {
    test_start "Vault Connectivity"
    
    if curl -s "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        test_pass "Vault is accessible at $VAULT_ADDR"
    else
        test_fail "Cannot connect to Vault at $VAULT_ADDR"
        return 1
    fi
    
    # Check if Vault is unsealed
    local health_status=$(curl -s "$VAULT_ADDR/v1/sys/health" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('sealed', True))" 2>/dev/null || echo "true")
    
    if [ "$health_status" = "False" ] || [ "$health_status" = "false" ]; then
        test_pass "Vault is unsealed and ready"
    else
        test_fail "Vault is sealed or not properly initialized"
        return 1
    fi
}

# Test Vault authentication
test_vault_authentication() {
    test_start "Vault Authentication"
    
    local token_file="$PROJECT_ROOT/data/vault/vedfolnir-token.txt"
    
    if [ -f "$token_file" ]; then
        local token=$(cat "$token_file")
        
        # Test token validity
        local auth_test=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/auth/token/lookup-self" | python3 -c "import sys, json; data=json.load(sys.stdin); print('success' if 'data' in data else 'fail')" 2>/dev/null || echo "fail")
        
        if [ "$auth_test" = "success" ]; then
            test_pass "Application token is valid"
        else
            test_fail "Application token is invalid or expired"
            return 1
        fi
    else
        test_fail "Application token file not found: $token_file"
        return 1
    fi
}

# Test secrets engines
test_secrets_engines() {
    test_start "Secrets Engines"
    
    local token=$(cat "$PROJECT_ROOT/data/vault/vedfolnir-token.txt" 2>/dev/null || echo "")
    
    if [ -z "$token" ]; then
        test_fail "No token available for testing"
        return 1
    fi
    
    # Test KV v2 engine
    local kv_test=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/vedfolnir/metadata" | python3 -c "import sys, json; data=json.load(sys.stdin); print('success' if 'data' in data else 'fail')" 2>/dev/null || echo "fail")
    
    if [ "$kv_test" = "success" ]; then
        test_pass "KV v2 secrets engine is accessible"
    else
        test_fail "KV v2 secrets engine is not accessible"
    fi
    
    # Test database engine
    local db_test=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/database/config" | python3 -c "import sys, json; data=json.load(sys.stdin); print('success' if 'data' in data else 'fail')" 2>/dev/null || echo "fail")
    
    if [ "$db_test" = "success" ]; then
        test_pass "Database secrets engine is accessible"
    else
        test_fail "Database secrets engine is not accessible"
    fi
    
    # Test transit engine
    local transit_test=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/transit/keys" | python3 -c "import sys, json; data=json.load(sys.stdin); print('success' if 'data' in data else 'fail')" 2>/dev/null || echo "fail")
    
    if [ "$transit_test" = "success" ]; then
        test_pass "Transit secrets engine is accessible"
    else
        test_fail "Transit secrets engine is not accessible"
    fi
}

# Test application secrets
test_application_secrets() {
    test_start "Application Secrets"
    
    local token=$(cat "$PROJECT_ROOT/data/vault/vedfolnir-token.txt" 2>/dev/null || echo "")
    
    if [ -z "$token" ]; then
        test_fail "No token available for testing"
        return 1
    fi
    
    # Test Flask secret
    local flask_test=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/vedfolnir/data/flask" | python3 -c "import sys, json; data=json.load(sys.stdin); print('success' if 'data' in data and 'data' in data['data'] and 'secret_key' in data['data']['data'] else 'fail')" 2>/dev/null || echo "fail")
    
    if [ "$flask_test" = "success" ]; then
        test_pass "Flask secret key is stored in Vault"
    else
        test_fail "Flask secret key is missing from Vault"
    fi
    
    # Test platform encryption key
    local platform_test=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/vedfolnir/data/platform" | python3 -c "import sys, json; data=json.load(sys.stdin); print('success' if 'data' in data and 'data' in data['data'] and 'encryption_key' in data['data']['data'] else 'fail')" 2>/dev/null || echo "fail")
    
    if [ "$platform_test" = "success" ]; then
        test_pass "Platform encryption key is stored in Vault"
    else
        test_fail "Platform encryption key is missing from Vault"
    fi
    
    # Test Redis password
    local redis_test=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/vedfolnir/data/redis" | python3 -c "import sys, json; data=json.load(sys.stdin); print('success' if 'data' in data and 'data' in data['data'] and 'password' in data['data']['data'] else 'fail')" 2>/dev/null || echo "fail")
    
    if [ "$redis_test" = "success" ]; then
        test_pass "Redis password is stored in Vault"
    else
        test_fail "Redis password is missing from Vault"
    fi
}

# Test dynamic database credentials
test_database_credentials() {
    test_start "Dynamic Database Credentials"
    
    local token=$(cat "$PROJECT_ROOT/data/vault/vedfolnir-token.txt" 2>/dev/null || echo "")
    
    if [ -z "$token" ]; then
        test_fail "No token available for testing"
        return 1
    fi
    
    # Get database credentials
    local db_creds=$(curl -s -H "X-Vault-Token: $token" "$VAULT_ADDR/v1/database/creds/vedfolnir-role" 2>/dev/null || echo "")
    
    if [ -n "$db_creds" ]; then
        local username=$(echo "$db_creds" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('username', ''))" 2>/dev/null || echo "")
        local password=$(echo "$db_creds" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('password', ''))" 2>/dev/null || echo "")
        
        if [ -n "$username" ] && [ -n "$password" ]; then
            test_pass "Dynamic database credentials generated: $username"
        else
            test_fail "Dynamic database credentials are incomplete"
        fi
    else
        test_fail "Failed to generate dynamic database credentials"
    fi
}

# Test encryption/decryption
test_encryption() {
    test_start "Transit Encryption/Decryption"
    
    local token=$(cat "$PROJECT_ROOT/data/vault/vedfolnir-token.txt" 2>/dev/null || echo "")
    
    if [ -z "$token" ]; then
        test_fail "No token available for testing"
        return 1
    fi
    
    # Test data
    local test_data="This is a test message for encryption"
    local encoded_data=$(echo -n "$test_data" | base64)
    
    # Encrypt data
    local encrypt_response=$(curl -s -H "X-Vault-Token: $token" -X POST -d "{\"plaintext\":\"$encoded_data\"}" "$VAULT_ADDR/v1/transit/encrypt/vedfolnir-encryption" 2>/dev/null || echo "")
    local ciphertext=$(echo "$encrypt_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('ciphertext', ''))" 2>/dev/null || echo "")
    
    if [ -n "$ciphertext" ] && [[ "$ciphertext" == vault:v* ]]; then
        test_pass "Data encryption successful"
        
        # Decrypt data
        local decrypt_response=$(curl -s -H "X-Vault-Token: $token" -X POST -d "{\"ciphertext\":\"$ciphertext\"}" "$VAULT_ADDR/v1/transit/decrypt/vedfolnir-encryption" 2>/dev/null || echo "")
        local decrypted_encoded=$(echo "$decrypt_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('plaintext', ''))" 2>/dev/null || echo "")
        local decrypted_data=$(echo "$decrypted_encoded" | base64 -d 2>/dev/null || echo "")
        
        if [ "$decrypted_data" = "$test_data" ]; then
            test_pass "Data decryption successful"
        else
            test_fail "Data decryption failed or data mismatch"
        fi
    else
        test_fail "Data encryption failed"
    fi
}

# Test Docker secrets files
test_docker_secrets() {
    test_start "Docker Secrets Files"
    
    local secrets_dir="$PROJECT_ROOT/data/vault/secrets"
    local secrets_found=0
    local secrets_total=0
    
    # Check Flask secret file
    ((secrets_total++))
    if [ -f "$secrets_dir/flask_secret_key.txt" ] && [ -s "$secrets_dir/flask_secret_key.txt" ]; then
        ((secrets_found++))
        test_pass "Flask secret file exists and has content"
    else
        test_fail "Flask secret file is missing or empty"
    fi
    
    # Check platform encryption key file
    ((secrets_total++))
    if [ -f "$secrets_dir/platform_encryption_key.txt" ] && [ -s "$secrets_dir/platform_encryption_key.txt" ]; then
        ((secrets_found++))
        test_pass "Platform encryption key file exists and has content"
    else
        test_fail "Platform encryption key file is missing or empty"
    fi
    
    # Check Redis password file
    ((secrets_total++))
    if [ -f "$secrets_dir/redis_password.txt" ] && [ -s "$secrets_dir/redis_password.txt" ]; then
        ((secrets_found++))
        test_pass "Redis password file exists and has content"
    else
        test_fail "Redis password file is missing or empty"
    fi
    
    # Check database URL file
    ((secrets_total++))
    if [ -f "$secrets_dir/database_url.txt" ] && [ -s "$secrets_dir/database_url.txt" ]; then
        ((secrets_found++))
        test_pass "Database URL file exists and has content"
    else
        test_fail "Database URL file is missing or empty"
    fi
    
    # Overall Docker secrets test
    if [ $secrets_found -eq $secrets_total ]; then
        test_pass "All Docker secret files are present"
    else
        test_fail "Some Docker secret files are missing ($secrets_found/$secrets_total found)"
    fi
}

# Test file permissions
test_file_permissions() {
    test_start "File Permissions"
    
    local secrets_dir="$PROJECT_ROOT/data/vault/secrets"
    local permission_issues=0
    
    # Check secrets directory permissions
    if [ -d "$secrets_dir" ]; then
        local dir_perms=$(stat -c "%a" "$secrets_dir" 2>/dev/null || stat -f "%A" "$secrets_dir" 2>/dev/null || echo "unknown")
        if [ "$dir_perms" = "700" ]; then
            test_pass "Secrets directory has correct permissions (700)"
        else
            test_fail "Secrets directory has incorrect permissions ($dir_perms, should be 700)"
            ((permission_issues++))
        fi
    else
        test_fail "Secrets directory does not exist"
        ((permission_issues++))
    fi
    
    # Check individual secret file permissions
    for secret_file in "$secrets_dir"/*.txt; do
        if [ -f "$secret_file" ]; then
            local file_perms=$(stat -c "%a" "$secret_file" 2>/dev/null || stat -f "%A" "$secret_file" 2>/dev/null || echo "unknown")
            if [ "$file_perms" = "600" ]; then
                test_pass "$(basename "$secret_file") has correct permissions (600)"
            else
                test_fail "$(basename "$secret_file") has incorrect permissions ($file_perms, should be 600)"
                ((permission_issues++))
            fi
        fi
    done
    
    if [ $permission_issues -eq 0 ]; then
        test_pass "All file permissions are correct"
    else
        test_fail "$permission_issues file permission issues found"
    fi
}

# Test Docker services
test_docker_services() {
    test_start "Docker Services"
    
    cd "$PROJECT_ROOT/docker"
    
    # Check if Docker Compose is available
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        test_fail "Docker Compose not available"
        return 1
    fi
    
    # Check Vault service
    local vault_status=$($DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml ps -q vault 2>/dev/null || echo "")
    if [ -n "$vault_status" ]; then
        test_pass "Vault Docker service is running"
    else
        test_fail "Vault Docker service is not running"
    fi
    
    # Check vault-secrets service
    local secrets_status=$($DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml ps -q vault-secrets 2>/dev/null || echo "")
    if [ -n "$secrets_status" ]; then
        test_pass "Vault secrets service is running"
    else
        test_fail "Vault secrets service is not running"
    fi
    
    # Check vault-rotation service
    local rotation_status=$($DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml ps -q vault-rotation 2>/dev/null || echo "")
    if [ -n "$rotation_status" ]; then
        test_pass "Vault rotation service is running"
    else
        test_fail "Vault rotation service is not running"
    fi
}

# Test secret rotation functionality
test_secret_rotation() {
    test_start "Secret Rotation"
    
    cd "$PROJECT_ROOT/docker"
    
    # Check if Docker Compose is available
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        test_fail "Docker Compose not available"
        return 1
    fi
    
    # Test rotation status check
    local rotation_check=$($DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec -T vault-rotation python /app/secret-rotation.py --check 2>/dev/null || echo "failed")
    
    if [[ "$rotation_check" == *"secrets"* ]]; then
        test_pass "Secret rotation status check works"
    else
        test_fail "Secret rotation status check failed"
    fi
    
    # Test secrets validation
    local validation_check=$($DOCKER_COMPOSE -f docker-compose.yml -f docker-compose.vault.yml exec -T vault-secrets python /app/docker-secrets-integration.py --validate 2>/dev/null || echo "failed")
    
    if [[ "$validation_check" == *"VALID"* ]]; then
        test_pass "Secrets validation works"
    else
        test_fail "Secrets validation failed"
    fi
}

# Run all tests
run_all_tests() {
    echo "=== Vedfolnir Vault Integration Test Suite ==="
    echo "Vault Address: $VAULT_ADDR"
    echo "Project Root: $PROJECT_ROOT"
    echo ""
    
    # Run tests
    test_vault_connectivity || true
    test_vault_authentication || true
    test_secrets_engines || true
    test_application_secrets || true
    test_database_credentials || true
    test_encryption || true
    test_docker_secrets || true
    test_file_permissions || true
    test_docker_services || true
    test_secret_rotation || true
    
    # Print summary
    echo ""
    echo "=== Test Summary ==="
    echo "Tests Run: $TESTS_RUN"
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "All tests passed! ✅"
        echo ""
        echo "Vault integration is working correctly."
        echo "You can now use Vault for secure secrets management."
        return 0
    else
        log_error "Some tests failed! ❌"
        echo ""
        echo "Please check the failed tests and fix any issues."
        echo "Run individual tests or check logs for more details."
        return 1
    fi
}

# Show help
show_help() {
    echo "Vault Integration Test Script"
    echo ""
    echo "Usage: $0 [test_name]"
    echo ""
    echo "Available tests:"
    echo "  connectivity      - Test Vault connectivity"
    echo "  authentication    - Test Vault authentication"
    echo "  secrets-engines   - Test secrets engines"
    echo "  app-secrets       - Test application secrets"
    echo "  db-credentials    - Test database credentials"
    echo "  encryption        - Test encryption/decryption"
    echo "  docker-secrets    - Test Docker secrets files"
    echo "  permissions       - Test file permissions"
    echo "  docker-services   - Test Docker services"
    echo "  rotation          - Test secret rotation"
    echo "  all               - Run all tests (default)"
    echo ""
    echo "Examples:"
    echo "  $0                - Run all tests"
    echo "  $0 connectivity   - Test only Vault connectivity"
    echo "  $0 app-secrets    - Test only application secrets"
}

# Main function
main() {
    case "${1:-all}" in
        connectivity)
            test_vault_connectivity
            ;;
        authentication)
            test_vault_authentication
            ;;
        secrets-engines)
            test_secrets_engines
            ;;
        app-secrets)
            test_application_secrets
            ;;
        db-credentials)
            test_database_credentials
            ;;
        encryption)
            test_encryption
            ;;
        docker-secrets)
            test_docker_secrets
            ;;
        permissions)
            test_file_permissions
            ;;
        docker-services)
            test_docker_services
            ;;
        rotation)
            test_secret_rotation
            ;;
        all)
            run_all_tests
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown test: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"