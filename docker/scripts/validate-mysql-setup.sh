#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# MySQL container setup validation script
# Validates that all MySQL container components are properly configured

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check file exists
check_file() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        log "${GREEN}✓ $description: $file${NC}"
        return 0
    else
        log "${RED}✗ $description: $file (missing)${NC}"
        return 1
    fi
}

# Function to check directory exists
check_directory() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$dir" ]; then
        log "${GREEN}✓ $description: $dir${NC}"
        return 0
    else
        log "${RED}✗ $description: $dir (missing)${NC}"
        return 1
    fi
}

# Function to check script is executable
check_executable() {
    local script="$1"
    local description="$2"
    
    if [ -x "$script" ]; then
        log "${GREEN}✓ $description: $script (executable)${NC}"
        return 0
    else
        log "${RED}✗ $description: $script (not executable)${NC}"
        return 1
    fi
}

# Function to validate MySQL configuration
validate_mysql_config() {
    local config_file="config/mysql/vedfolnir.cnf"
    
    log "${BLUE}=== Validating MySQL Configuration ===${NC}"
    
    if ! check_file "$config_file" "MySQL configuration file"; then
        return 1
    fi
    
    # Check for required configuration sections
    local required_configs=(
        "character-set-server = utf8mb4"
        "collation-server = utf8mb4_unicode_ci"
        "innodb_buffer_pool_size = 2G"
        "max_connections = 200"
        "slow_query_log = 1"
    )
    
    local config_errors=0
    
    for config in "${required_configs[@]}"; do
        if grep -q "$config" "$config_file"; then
            log "${GREEN}✓ Configuration found: $config${NC}"
        else
            log "${RED}✗ Configuration missing: $config${NC}"
            ((config_errors++))
        fi
    done
    
    if [ $config_errors -eq 0 ]; then
        log "${GREEN}✓ MySQL configuration validation passed${NC}"
        return 0
    else
        log "${RED}✗ MySQL configuration validation failed ($config_errors errors)${NC}"
        return 1
    fi
}

# Function to validate initialization scripts
validate_init_scripts() {
    log "${BLUE}=== Validating MySQL Initialization Scripts ===${NC}"
    
    local init_dir="docker/mysql/init"
    local init_scripts=(
        "01-init-vedfolnir.sql"
        "02-health-check-setup.sql"
        "03-performance-optimization.sql"
    )
    
    if ! check_directory "$init_dir" "MySQL initialization directory"; then
        return 1
    fi
    
    local script_errors=0
    
    for script in "${init_scripts[@]}"; do
        local script_path="$init_dir/$script"
        if ! check_file "$script_path" "Initialization script"; then
            ((script_errors++))
        fi
    done
    
    if [ $script_errors -eq 0 ]; then
        log "${GREEN}✓ MySQL initialization scripts validation passed${NC}"
        return 0
    else
        log "${RED}✗ MySQL initialization scripts validation failed ($script_errors errors)${NC}"
        return 1
    fi
}

# Function to validate management scripts
validate_management_scripts() {
    log "${BLUE}=== Validating MySQL Management Scripts ===${NC}"
    
    local scripts_dir="docker/scripts"
    local management_scripts=(
        "mysql-health-check.sh"
        "mysql-performance-monitor.sh"
        "mysql-backup.sh"
        "mysql-management.sh"
    )
    
    if ! check_directory "$scripts_dir" "MySQL scripts directory"; then
        return 1
    fi
    
    local script_errors=0
    
    for script in "${management_scripts[@]}"; do
        local script_path="$scripts_dir/$script"
        if ! check_executable "$script_path" "Management script"; then
            ((script_errors++))
        fi
    done
    
    if [ $script_errors -eq 0 ]; then
        log "${GREEN}✓ MySQL management scripts validation passed${NC}"
        return 0
    else
        log "${RED}✗ MySQL management scripts validation failed ($script_errors errors)${NC}"
        return 1
    fi
}

# Function to validate secrets
validate_secrets() {
    log "${BLUE}=== Validating MySQL Secrets ===${NC}"
    
    local secrets_dir="secrets"
    local secret_files=(
        "mysql_root_password.txt"
        "mysql_password.txt"
    )
    
    if ! check_directory "$secrets_dir" "Secrets directory"; then
        return 1
    fi
    
    local secret_errors=0
    
    for secret in "${secret_files[@]}"; do
        local secret_path="$secrets_dir/$secret"
        if ! check_file "$secret_path" "Secret file"; then
            ((secret_errors++))
        else
            # Check if secret file is not empty
            if [ -s "$secret_path" ]; then
                log "${GREEN}✓ Secret file has content: $secret${NC}"
            else
                log "${RED}✗ Secret file is empty: $secret${NC}"
                ((secret_errors++))
            fi
        fi
    done
    
    if [ $secret_errors -eq 0 ]; then
        log "${GREEN}✓ MySQL secrets validation passed${NC}"
        return 0
    else
        log "${RED}✗ MySQL secrets validation failed ($secret_errors errors)${NC}"
        return 1
    fi
}

# Function to validate Docker Compose configuration
validate_docker_compose() {
    log "${BLUE}=== Validating Docker Compose MySQL Configuration ===${NC}"
    
    local compose_file="docker-compose.yml"
    
    if ! check_file "$compose_file" "Docker Compose file"; then
        return 1
    fi
    
    # Check for required MySQL service configuration
    local required_configs=(
        "image: mysql:8.0"
        "container_name: vedfolnir_mysql"
        "MYSQL_DATABASE: vedfolnir"
        "MYSQL_CHARSET: utf8mb4"
        "MYSQL_COLLATION: utf8mb4_unicode_ci"
        "mysql_data:/var/lib/mysql"
        "vedfolnir_internal"
    )
    
    local compose_errors=0
    
    for config in "${required_configs[@]}"; do
        if grep -q "$config" "$compose_file"; then
            log "${GREEN}✓ Docker Compose config found: $config${NC}"
        else
            log "${RED}✗ Docker Compose config missing: $config${NC}"
            ((compose_errors++))
        fi
    done
    
    if [ $compose_errors -eq 0 ]; then
        log "${GREEN}✓ Docker Compose MySQL configuration validation passed${NC}"
        return 0
    else
        log "${RED}✗ Docker Compose MySQL configuration validation failed ($compose_errors errors)${NC}"
        return 1
    fi
}

# Function to validate directory structure
validate_directory_structure() {
    log "${BLUE}=== Validating Directory Structure ===${NC}"
    
    local required_dirs=(
        "config/mysql"
        "docker/mysql/init"
        "docker/mysql/conf.d"
        "docker/mysql/dev-init"
        "docker/scripts"
        "secrets"
        "storage/backups/mysql"
        "logs/mysql"
    )
    
    local dir_errors=0
    
    for dir in "${required_dirs[@]}"; do
        if ! check_directory "$dir" "Required directory"; then
            # Create missing directories
            log "${YELLOW}Creating missing directory: $dir${NC}"
            mkdir -p "$dir"
            if [ -d "$dir" ]; then
                log "${GREEN}✓ Directory created: $dir${NC}"
            else
                log "${RED}✗ Failed to create directory: $dir${NC}"
                ((dir_errors++))
            fi
        fi
    done
    
    if [ $dir_errors -eq 0 ]; then
        log "${GREEN}✓ Directory structure validation passed${NC}"
        return 0
    else
        log "${RED}✗ Directory structure validation failed ($dir_errors errors)${NC}"
        return 1
    fi
}

# Function to run comprehensive validation
run_validation() {
    log "${BLUE}=== MySQL Container Setup Validation ===${NC}"
    log "Validating MySQL container configuration for Vedfolnir Docker deployment"
    echo
    
    local validation_errors=0
    
    # Run all validation checks
    validate_directory_structure || ((validation_errors++))
    echo
    validate_mysql_config || ((validation_errors++))
    echo
    validate_init_scripts || ((validation_errors++))
    echo
    validate_management_scripts || ((validation_errors++))
    echo
    validate_secrets || ((validation_errors++))
    echo
    validate_docker_compose || ((validation_errors++))
    echo
    
    # Summary
    log "${BLUE}=== Validation Summary ===${NC}"
    
    if [ $validation_errors -eq 0 ]; then
        log "${GREEN}✅ All MySQL container validations passed!${NC}"
        log "${GREEN}✅ MySQL container is ready for deployment${NC}"
        return 0
    else
        log "${RED}❌ MySQL container validation failed with $validation_errors error(s)${NC}"
        log "${RED}❌ Please fix the errors before deploying${NC}"
        return 1
    fi
}

# Function to show validation help
show_help() {
    echo "MySQL Container Setup Validation Script"
    echo
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  validate    - Run comprehensive validation (default)"
    echo "  config      - Validate MySQL configuration only"
    echo "  scripts     - Validate management scripts only"
    echo "  secrets     - Validate secrets only"
    echo "  compose     - Validate Docker Compose configuration only"
    echo "  structure   - Validate directory structure only"
    echo "  help        - Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Run full validation"
    echo "  $0 validate           # Run full validation"
    echo "  $0 config             # Validate MySQL config only"
    echo "  $0 scripts            # Validate scripts only"
}

# Main function
main() {
    case "${1:-validate}" in
        "validate")
            run_validation
            ;;
        "config")
            validate_mysql_config
            ;;
        "scripts")
            validate_management_scripts
            ;;
        "secrets")
            validate_secrets
            ;;
        "compose")
            validate_docker_compose
            ;;
        "structure")
            validate_directory_structure
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log "${RED}ERROR: Unknown command: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"