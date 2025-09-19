#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vedfolnir Mac Setup Validation Script
# Validates that all components are properly configured and running

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_NAME="gunicorn-host"

echo -e "${BLUE}=== Vedfolnir Mac Setup Validation ===${NC}"
echo "Project directory: $PROJECT_DIR"
echo

# Function to print status
print_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_fail() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Track validation results
VALIDATION_ERRORS=0

# Function to increment error count
fail_check() {
    print_fail "$1"
    ((VALIDATION_ERRORS++))
}

# Check if running on macOS
echo -e "\n${BLUE}=== System Validation ===${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    print_pass "Running on macOS"
else
    fail_check "Not running on macOS"
fi

# Check Homebrew
if command -v brew &> /dev/null; then
    print_pass "Homebrew installed"
    
    # Check Homebrew path
    if [[ $(uname -m) == "arm64" ]] && [[ -d "/opt/homebrew" ]]; then
        print_pass "Homebrew path correct for Apple Silicon"
    elif [[ $(uname -m) == "x86_64" ]] && [[ -d "/usr/local" ]]; then
        print_pass "Homebrew path correct for Intel Mac"
    else
        print_warning "Homebrew path may not be in shell PATH"
    fi
else
    fail_check "Homebrew not installed"
fi

# Check pyenv
echo -e "\n${BLUE}=== Python Environment Validation ===${NC}"
if command -v pyenv &> /dev/null; then
    print_pass "pyenv installed"
    
    # Check if virtual environment exists
    if pyenv versions | grep -q "$VENV_NAME"; then
        print_pass "Virtual environment '$VENV_NAME' exists"
        
        # Try to activate and check Python version
        if pyenv activate "$VENV_NAME" 2>/dev/null; then
            PYTHON_VERSION=$(python --version 2>&1)
            print_pass "Virtual environment activates successfully ($PYTHON_VERSION)"
        else
            fail_check "Cannot activate virtual environment '$VENV_NAME'"
        fi
    else
        fail_check "Virtual environment '$VENV_NAME' not found"
    fi
else
    fail_check "pyenv not installed"
fi

# Check system services
echo -e "\n${BLUE}=== System Services Validation ===${NC}"

# MySQL
if brew services list | grep mysql | grep -q started; then
    print_pass "MySQL service running"
    
    # Test MySQL connection
    if mysql -u root -e "SELECT 1;" &>/dev/null; then
        print_pass "MySQL connection successful"
    else
        print_warning "MySQL running but connection failed (may need authentication)"
    fi
else
    fail_check "MySQL service not running"
fi

# Redis
if brew services list | grep redis | grep -q started; then
    print_pass "Redis service running"
    
    # Test Redis connection
    if redis-cli ping | grep -q PONG; then
        print_pass "Redis connection successful"
    else
        fail_check "Redis running but connection failed"
    fi
else
    fail_check "Redis service not running"
fi

# Nginx (optional)
if brew services list | grep nginx | grep -q started; then
    print_pass "Nginx service running"
else
    print_info "Nginx service not running (optional)"
fi

# Check project files
echo -e "\n${BLUE}=== Project Files Validation ===${NC}"

cd "$PROJECT_DIR"

# Check essential files
REQUIRED_FILES=(
    ".env"
    "requirements.txt"
    "web_app.py"
    "start_gunicorn.sh"
    "com.vedfolnir.gunicorn.plist"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        print_pass "Required file exists: $file"
    else
        fail_check "Missing required file: $file"
    fi
done

# Check directories
REQUIRED_DIRS=(
    "logs"
    "storage"
    "storage/images"
    "storage/temp"
    "storage/backups"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        print_pass "Required directory exists: $dir"
    else
        fail_check "Missing required directory: $dir"
    fi
done

# Check Python dependencies
echo -e "\n${BLUE}=== Python Dependencies Validation ===${NC}"

if pyenv activate "$VENV_NAME" 2>/dev/null; then
    # Check key dependencies
    REQUIRED_PACKAGES=(
        "flask"
        "gunicorn"
        "eventlet"
        "redis"
        "sqlalchemy"
        "pymysql"
    )
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if python -c "import $package" 2>/dev/null; then
            print_pass "Python package available: $package"
        else
            fail_check "Missing Python package: $package"
        fi
    done
else
    fail_check "Cannot activate virtual environment for dependency check"
fi

# Check Gunicorn service
echo -e "\n${BLUE}=== Gunicorn Service Validation ===${NC}"

# Check if service is installed
if [[ -f ~/Library/LaunchAgents/com.vedfolnir.gunicorn.plist ]]; then
    print_pass "Gunicorn service installed"
    
    # Check if service is loaded
    if launchctl list | grep -q com.vedfolnir.gunicorn; then
        print_pass "Gunicorn service loaded"
        
        # Test HTTP response
        sleep 2  # Give service time to start
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 2>/dev/null || echo "000")
        
        if [[ "$HTTP_CODE" =~ ^(200|302)$ ]]; then
            print_pass "Gunicorn service responding (HTTP $HTTP_CODE)"
        else
            fail_check "Gunicorn service not responding (HTTP $HTTP_CODE)"
        fi
    else
        fail_check "Gunicorn service not loaded"
    fi
else
    fail_check "Gunicorn service not installed"
fi

# Check database configuration
echo -e "\n${BLUE}=== Database Configuration Validation ===${NC}"

if [[ -f ".env" ]]; then
    # Check for required environment variables
    source .env
    
    if [[ -n "$DATABASE_URL" ]]; then
        print_pass "DATABASE_URL configured"
        
        # Test database connection
        if python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
try:
    config = Config()
    db_manager = DatabaseManager(config)
    with db_manager.get_session() as session:
        session.execute('SELECT 1')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" 2>/dev/null; then
            print_pass "Database connection successful"
        else
            fail_check "Database connection failed"
        fi
    else
        fail_check "DATABASE_URL not configured in .env"
    fi
    
    if [[ -n "$REDIS_URL" ]]; then
        print_pass "REDIS_URL configured"
    else
        fail_check "REDIS_URL not configured in .env"
    fi
    
    if [[ -n "$FLASK_SECRET_KEY" ]]; then
        print_pass "FLASK_SECRET_KEY configured"
    else
        fail_check "FLASK_SECRET_KEY not configured in .env"
    fi
else
    fail_check ".env file not found"
fi

# Check log files
echo -e "\n${BLUE}=== Log Files Validation ===${NC}"

LOG_FILES=(
    "logs/vedfolnir.log"
    "logs/vedfolnir.err"
)

for log_file in "${LOG_FILES[@]}"; do
    if [[ -f "$log_file" ]]; then
        print_pass "Log file exists: $log_file"
        
        # Check if log file has recent entries (within last hour)
        if [[ $(find "$log_file" -mmin -60 2>/dev/null) ]]; then
            print_pass "Log file has recent entries: $log_file"
        else
            print_warning "Log file exists but no recent entries: $log_file"
        fi
    else
        print_warning "Log file not found: $log_file (will be created on first run)"
    fi
done

# Performance check
echo -e "\n${BLUE}=== Performance Validation ===${NC}"

# Check available memory
AVAILABLE_MEMORY=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
AVAILABLE_MB=$((AVAILABLE_MEMORY * 4096 / 1024 / 1024))

if [[ $AVAILABLE_MB -gt 1000 ]]; then
    print_pass "Sufficient memory available (${AVAILABLE_MB}MB)"
elif [[ $AVAILABLE_MB -gt 500 ]]; then
    print_warning "Limited memory available (${AVAILABLE_MB}MB)"
else
    print_warning "Low memory available (${AVAILABLE_MB}MB) - may affect performance"
fi

# Check CPU cores
CPU_CORES=$(sysctl -n hw.ncpu)
print_pass "CPU cores available: $CPU_CORES"

# Final summary
echo -e "\n${BLUE}=== Validation Summary ===${NC}"

if [[ $VALIDATION_ERRORS -eq 0 ]]; then
    echo -e "${GREEN}🎉 All validations passed! Vedfolnir is properly configured.${NC}"
    echo
    echo "✅ Your Mac hosting setup is ready for production use."
    echo
    echo "🔗 Access your application:"
    if brew services list | grep nginx | grep -q started; then
        echo "  • Web interface: http://localhost"
    fi
    echo "  • Direct access: http://127.0.0.1:8000"
    echo
    echo "🛠️  Management commands:"
    echo "  • ./scripts/manage_services.sh status"
    echo "  • ./scripts/manage_services.sh restart"
    echo "  • ./scripts/manage_services.sh logs"
    
    exit 0
else
    echo -e "${RED}❌ Validation failed with $VALIDATION_ERRORS error(s).${NC}"
    echo
    echo "🔧 Please fix the issues above and run the validation again."
    echo
    echo "💡 Common fixes:"
    echo "  • Run setup script: ./scripts/setup/setup_mac_hosting.sh"
    echo "  • Start services: ./scripts/manage_services.sh start"
    echo "  • Check logs: ./scripts/manage_services.sh logs"
    
    exit 1
fi