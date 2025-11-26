#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
# Vedfolnir Complete Teardown Script
#
# This script completely removes Vedfolnir from your system including:
# - launchd services (macOS)
# - Docker containers and volumes
# - MySQL database and user
# - Redis data
# - Application files and configurations
# - Logs and temporary files
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
DRY_RUN=false
KEEP_DATABASE=false
KEEP_REDIS=false
KEEP_FILES=false
INTERACTIVE=true

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Complete teardown and uninstallation of Vedfolnir application.

OPTIONS:
    -h, --help              Show this help message
    -d, --dry-run           Show what would be removed without actually removing
    -y, --yes               Non-interactive mode (skip confirmations)
    --keep-database         Keep MySQL database and user
    --keep-redis            Keep Redis data
    --keep-files            Keep application files (only remove services/data)
    --all                   Remove everything (default)

EXAMPLES:
    # Preview what would be removed
    $0 --dry-run

    # Remove everything with confirmation prompts
    $0

    # Remove everything without prompts
    $0 --yes

    # Remove services but keep database
    $0 --keep-database

    # Remove only services, keep all data
    $0 --keep-database --keep-redis --keep-files

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -y|--yes)
            INTERACTIVE=false
            shift
            ;;
        --keep-database)
            KEEP_DATABASE=true
            shift
            ;;
        --keep-redis)
            KEEP_REDIS=true
            shift
            ;;
        --keep-files)
            KEEP_FILES=true
            shift
            ;;
        --all)
            KEEP_DATABASE=false
            KEEP_REDIS=false
            KEEP_FILES=false
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Print header
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}Vedfolnir Complete Teardown Script${NC}                      ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}⚠️  DRY RUN MODE - No changes will be made${NC}"
        echo ""
    fi
}

# Print section header
print_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

# Confirm action
confirm() {
    if [ "$INTERACTIVE" = false ]; then
        return 0
    fi
    
    local message="$1"
    echo -e "${YELLOW}$message${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Cancelled by user${NC}"
        exit 1
    fi
}

# Execute or preview command
execute() {
    local description="$1"
    shift
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN]${NC} $description"
        echo -e "${YELLOW}  Command: $*${NC}"
    else
        echo -e "${GREEN}✓${NC} $description"
        "$@" 2>&1 | sed 's/^/  /'
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Load environment variables
load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    fi
}

# Stop launchd service (macOS)
stop_launchd_service() {
    print_section "Stopping launchd Service"
    
    local plist_file="$PROJECT_ROOT/com.vedfolnir.gunicorn.plist"
    local plist_dest="$HOME/Library/LaunchAgents/com.vedfolnir.gunicorn.plist"
    
    if [ -f "$plist_dest" ]; then
        execute "Unloading launchd service" launchctl unload "$plist_dest" || true
        execute "Removing launchd plist" rm -f "$plist_dest"
    else
        echo -e "${BLUE}ℹ${NC}  No launchd service found"
    fi
}

# Stop Docker containers
stop_docker() {
    print_section "Stopping Docker Containers"
    
    if ! command_exists docker; then
        echo -e "${BLUE}ℹ${NC}  Docker not installed, skipping"
        return
    fi
    
    cd "$PROJECT_ROOT"
    
    # Check for running containers
    if docker-compose ps -q 2>/dev/null | grep -q .; then
        execute "Stopping Docker Compose services" docker-compose down
        execute "Removing Docker volumes" docker-compose down -v
    else
        echo -e "${BLUE}ℹ${NC}  No Docker containers running"
    fi
}

# Stop running processes
stop_processes() {
    print_section "Stopping Running Processes"
    
    # Stop web_app.py
    if pgrep -f "python.*web_app.py" > /dev/null; then
        execute "Stopping web_app.py" pkill -f "python.*web_app.py" || true
    fi
    
    # Stop main.py
    if pgrep -f "python.*main.py" > /dev/null; then
        execute "Stopping main.py" pkill -f "python.*main.py" || true
    fi
    
    # Stop gunicorn
    if pgrep -f "gunicorn" > /dev/null; then
        execute "Stopping gunicorn" pkill -f "gunicorn" || true
    fi
    
    # Stop caption workers
    if pgrep -f "caption_worker" > /dev/null; then
        execute "Stopping caption workers" pkill -f "caption_worker" || true
    fi
    
    echo -e "${GREEN}✓${NC} All processes stopped"
}

# Clear Redis data
clear_redis() {
    if [ "$KEEP_REDIS" = true ]; then
        echo -e "${BLUE}ℹ${NC}  Keeping Redis data (--keep-redis specified)"
        return
    fi
    
    print_section "Clearing Redis Data"
    
    load_env
    
    # Get Redis configuration from .env
    local redis_host="${REDIS_HOST:-localhost}"
    local redis_port="${REDIS_PORT:-6379}"
    local redis_password="${REDIS_PASSWORD:-}"
    local redis_db="${REDIS_DB:-0}"
    
    if ! command_exists redis-cli; then
        echo -e "${YELLOW}⚠${NC}  redis-cli not found, skipping Redis cleanup"
        return
    fi
    
    echo -e "${BLUE}Redis Host:${NC} $redis_host"
    echo -e "${BLUE}Redis Port:${NC} $redis_port"
    echo -e "${BLUE}Redis DB:${NC} $redis_db"
    if [ -n "$redis_password" ]; then
        echo -e "${BLUE}Redis Auth:${NC} Enabled (using password from .env)"
    fi
    echo ""
    
    # Build redis-cli command with credentials from .env
    local redis_cmd="redis-cli -h $redis_host -p $redis_port -n $redis_db"
    if [ -n "$redis_password" ]; then
        redis_cmd="$redis_cmd -a $redis_password"
    fi
    
    # Test Redis connection
    if $redis_cmd ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Connected to Redis"
        
        # Clear Vedfolnir-specific keys
        execute "Clearing session keys" bash -c "$redis_cmd --scan --pattern 'vedfolnir:session:*' | xargs -r $redis_cmd DEL" || true
        execute "Clearing platform keys" bash -c "$redis_cmd --scan --pattern 'user_platforms:*' | xargs -r $redis_cmd DEL" || true
        execute "Clearing platform cache" bash -c "$redis_cmd --scan --pattern 'platform:*' | xargs -r $redis_cmd DEL" || true
        execute "Clearing platform stats" bash -c "$redis_cmd --scan --pattern 'platform_stats:*' | xargs -r $redis_cmd DEL" || true
        execute "Clearing other app keys" bash -c "$redis_cmd --scan --pattern 'vedfolnir:*' | xargs -r $redis_cmd DEL" || true
    else
        echo -e "${YELLOW}⚠${NC}  Cannot connect to Redis at $redis_host:$redis_port"
        echo -e "${YELLOW}⚠${NC}  Check REDIS_HOST, REDIS_PORT, and REDIS_PASSWORD in .env"
    fi
}

# Remove MySQL database
remove_database() {
    if [ "$KEEP_DATABASE" = true ]; then
        echo -e "${BLUE}ℹ${NC}  Keeping MySQL database (--keep-database specified)"
        return
    fi
    
    print_section "Removing MySQL Database"
    
    load_env
    
    if ! command_exists mysql; then
        echo -e "${YELLOW}⚠${NC}  mysql command not found, skipping database removal"
        echo -e "${YELLOW}⚠${NC}  You may need to manually remove the database"
        return
    fi
    
    # Extract database info from DATABASE_URL
    # Format: mysql+pymysql://user:password@host/database
    if [ -n "$DATABASE_URL" ]; then
        local db_user=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
        local db_password=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
        local db_name=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
        local db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:\/]*\).*/\1/p' | cut -d: -f1)
        
        echo -e "${BLUE}Database:${NC} $db_name"
        echo -e "${BLUE}User:${NC} $db_user"
        echo -e "${BLUE}Host:${NC} $db_host"
        echo ""
        
        # Check if running in Docker
        if [ "$db_host" = "mysql" ] || [ "$db_host" = "localhost" ] || [ "$db_host" = "127.0.0.1" ]; then
            if [ "$INTERACTIVE" = true ]; then
                echo -e "${YELLOW}⚠️  This will permanently delete the database and user!${NC}"
                confirm "Proceed with database removal?"
            fi
            
            # Try to use credentials from .env first
            if [ -n "$db_password" ]; then
                echo -e "${BLUE}ℹ${NC}  Using credentials from .env"
                
                # Drop database and user using credentials from .env
                execute "Dropping database $db_name" mysql -u "$db_user" -p"$db_password" -h "$db_host" -e "DROP DATABASE IF EXISTS $db_name;" 2>/dev/null || {
                    echo -e "${YELLOW}⚠${NC}  Could not drop database with user credentials, trying root..."
                    
                    # Try with root if available in .env
                    if [ -n "$DB_ROOT_PASSWORD" ]; then
                        execute "Dropping database $db_name (as root)" mysql -u root -p"$DB_ROOT_PASSWORD" -h "$db_host" -e "DROP DATABASE IF EXISTS $db_name;" || true
                        execute "Dropping user $db_user (as root)" mysql -u root -p"$DB_ROOT_PASSWORD" -h "$db_host" -e "DROP USER IF EXISTS '$db_user'@'%'; DROP USER IF EXISTS '$db_user'@'localhost';" || true
                        execute "Flushing privileges" mysql -u root -p"$DB_ROOT_PASSWORD" -h "$db_host" -e "FLUSH PRIVILEGES;" || true
                    else
                        echo -e "${YELLOW}⚠${NC}  DB_ROOT_PASSWORD not found in .env"
                        if [ "$INTERACTIVE" = true ]; then
                            read -p "Enter MySQL root password (or press Enter to skip): " -s mysql_root_password
                            echo ""
                            
                            if [ -n "$mysql_root_password" ]; then
                                execute "Dropping database $db_name" mysql -u root -p"$mysql_root_password" -h "$db_host" -e "DROP DATABASE IF EXISTS $db_name;" || true
                                execute "Dropping user $db_user" mysql -u root -p"$mysql_root_password" -h "$db_host" -e "DROP USER IF EXISTS '$db_user'@'%'; DROP USER IF EXISTS '$db_user'@'localhost';" || true
                                execute "Flushing privileges" mysql -u root -p"$mysql_root_password" -h "$db_host" -e "FLUSH PRIVILEGES;" || true
                            else
                                echo -e "${BLUE}ℹ${NC}  Skipping database removal"
                            fi
                        else
                            echo -e "${YELLOW}⚠${NC}  Non-interactive mode: skipping database removal"
                            echo -e "${YELLOW}⚠${NC}  Run manually: DROP DATABASE $db_name; DROP USER '$db_user'@'%';"
                        fi
                    fi
                }
            else
                echo -e "${YELLOW}⚠${NC}  Could not extract password from DATABASE_URL"
                if [ "$INTERACTIVE" = true ]; then
                    read -p "Enter MySQL root password (or press Enter to skip): " -s mysql_root_password
                    echo ""
                    
                    if [ -n "$mysql_root_password" ]; then
                        execute "Dropping database $db_name" mysql -u root -p"$mysql_root_password" -h "$db_host" -e "DROP DATABASE IF EXISTS $db_name;" || true
                        execute "Dropping user $db_user" mysql -u root -p"$mysql_root_password" -h "$db_host" -e "DROP USER IF EXISTS '$db_user'@'%'; DROP USER IF EXISTS '$db_user'@'localhost';" || true
                        execute "Flushing privileges" mysql -u root -p"$mysql_root_password" -h "$db_host" -e "FLUSH PRIVILEGES;" || true
                    else
                        echo -e "${BLUE}ℹ${NC}  Skipping database removal"
                    fi
                else
                    echo -e "${YELLOW}⚠${NC}  Non-interactive mode: skipping database removal"
                fi
            fi
        else
            echo -e "${YELLOW}⚠${NC}  Remote database host detected: $db_host"
            echo -e "${YELLOW}⚠${NC}  Skipping automatic removal for safety"
            echo -e "${YELLOW}⚠${NC}  Run manually: DROP DATABASE $db_name; DROP USER '$db_user'@'%';"
        fi
    else
        echo -e "${YELLOW}⚠${NC}  DATABASE_URL not found in .env"
    fi
}

# Remove application files
remove_files() {
    if [ "$KEEP_FILES" = true ]; then
        echo -e "${BLUE}ℹ${NC}  Keeping application files (--keep-files specified)"
        return
    fi
    
    print_section "Removing Application Files"
    
    cd "$PROJECT_ROOT"
    
    # Remove storage directories
    execute "Removing storage/images" rm -rf storage/images/*
    execute "Removing storage/temp" rm -rf storage/temp/*
    execute "Removing storage/backups" rm -rf storage/backups/*
    
    # Remove logs
    execute "Removing logs" rm -rf logs/*
    
    # Remove cache
    execute "Removing Python cache" find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    execute "Removing .pytest_cache" rm -rf .pytest_cache
    
    # Remove database file (if SQLite was used)
    if [ -f "vedfolnir.db" ]; then
        execute "Removing SQLite database" rm -f vedfolnir.db
    fi
    
    # Remove environment files
    execute "Removing .env" rm -f .env
    execute "Removing .env.development" rm -f .env.development
    execute "Removing .env.production" rm -f .env.production
    
    # Remove virtual environment
    if [ -d "venv" ]; then
        execute "Removing virtual environment" rm -rf venv
    fi
    
    # Remove node_modules
    if [ -d "node_modules" ]; then
        execute "Removing node_modules" rm -rf node_modules
    fi
}

# Print summary
print_summary() {
    print_section "Teardown Summary"
    
    echo -e "${GREEN}✓${NC} Services stopped"
    
    if [ "$KEEP_REDIS" = false ]; then
        echo -e "${GREEN}✓${NC} Redis data cleared"
    else
        echo -e "${BLUE}ℹ${NC}  Redis data kept"
    fi
    
    if [ "$KEEP_DATABASE" = false ]; then
        echo -e "${GREEN}✓${NC} MySQL database removed"
    else
        echo -e "${BLUE}ℹ${NC}  MySQL database kept"
    fi
    
    if [ "$KEEP_FILES" = false ]; then
        echo -e "${GREEN}✓${NC} Application files removed"
    else
        echo -e "${BLUE}ℹ${NC}  Application files kept"
    fi
    
    echo ""
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
        echo -e "${YELLOW}Run without --dry-run to perform actual teardown.${NC}"
    else
        echo -e "${GREEN}🎉 Vedfolnir teardown complete!${NC}"
        
        if [ "$KEEP_FILES" = false ]; then
            echo ""
            echo -e "${BLUE}To completely remove the application directory:${NC}"
            echo -e "  cd .."
            echo -e "  rm -rf $(basename "$PROJECT_ROOT")"
        fi
    fi
}

# Main execution
main() {
    print_header
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Show what will be done
    echo -e "${BLUE}Configuration:${NC}"
    echo -e "  Dry Run: ${DRY_RUN}"
    echo -e "  Interactive: ${INTERACTIVE}"
    echo -e "  Keep Database: ${KEEP_DATABASE}"
    echo -e "  Keep Redis: ${KEEP_REDIS}"
    echo -e "  Keep Files: ${KEEP_FILES}"
    echo ""
    
    # Confirm if interactive
    if [ "$INTERACTIVE" = true ] && [ "$DRY_RUN" = false ]; then
        confirm "⚠️  This will remove Vedfolnir from your system!"
    fi
    
    # Execute teardown steps
    stop_processes
    stop_launchd_service
    stop_docker
    clear_redis
    remove_database
    remove_files
    
    # Print summary
    print_summary
}

# Run main function
main
