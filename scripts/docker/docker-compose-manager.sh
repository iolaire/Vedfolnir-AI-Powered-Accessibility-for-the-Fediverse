#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -euo pipefail

# Docker Compose Master Management Script
# Unified interface for all Docker Compose management operations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

log_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

# Show main menu
show_menu() {
    log_header "Vedfolnir Docker Compose Manager"
    echo ""
    echo "Available Commands:"
    echo ""
    echo "  🚀 Deployment:"
    echo "    deploy                  Initial Docker Compose deployment"
    echo "    start [--build]         Start services"
    echo "    stop [--remove]         Stop services"
    echo "    restart [SERVICE]       Restart services"
    echo ""
    echo "  📊 Monitoring:"
    echo "    status                  Show service status"
    echo "    logs [SERVICE] [--follow] Show logs"
    echo "    health                  Health check"
    echo ""
    echo "  🔄 Maintenance:"
    echo "    update                  Update all services"
    echo "    maintenance             System maintenance"
    echo "    performance             Performance tuning"
    echo ""
    echo "  💾 Backup & Restore:"
    echo "    backup [TYPE]           Create backup"
    echo "    restore BACKUP          Restore from backup"
    echo "    list-backups            List available backups"
    echo ""
    echo "  🔐 Security:"
    echo "    rotate-secrets [TYPE]   Rotate secrets"
    echo "    security-update         Security updates"
    echo "    check-secrets           Check secret age"
    echo ""
    echo "  🧹 Cleanup:"
    echo "    cleanup                 Clean Docker resources"
    echo "    cleanup-backups         Remove old backups"
    echo ""
    echo "  🆘 Emergency:"
    echo "    recovery                Emergency recovery"
    echo "    reset-secrets           Emergency secret reset"
    echo ""
    echo "  ℹ️  Information:"
    echo "    help                    Show this help"
    echo "    version                 Show version info"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                 Initial deployment"
    echo "  $0 start --build          Start with rebuild"
    echo "  $0 logs vedfolnir --follow Follow app logs"
    echo "  $0 backup full            Create full backup"
    echo "  $0 rotate-secrets mysql   Rotate MySQL passwords"
}

# Show version information
show_version() {
    log_header "Version Information"
    echo ""
    echo "Docker Compose Manager for Vedfolnir"
    echo "Version: 1.0.0"
    echo "Project: Vedfolnir Docker Compose Migration"
    echo ""
    echo "System Information:"
    echo "  Docker: $(docker --version 2>/dev/null || echo 'Not installed')"
    echo "  Docker Compose: $(docker-compose --version 2>/dev/null || echo 'Not installed')"
    echo "  OS: $(uname -s) $(uname -r)"
    echo "  Architecture: $(uname -m)"
    echo ""
    echo "Project Root: $PROJECT_ROOT"
    echo "Script Directory: $SCRIPT_DIR"
}

# Check prerequisites
check_prerequisites() {
    local missing=0
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        ((missing++))
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        ((missing++))
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        ((missing++))
    fi
    
    if [[ $missing -gt 0 ]]; then
        log_error "Prerequisites check failed. Please install missing components."
        return 1
    fi
    
    return 0
}

# Execute command with proper error handling
execute_command() {
    local script="$1"
    shift
    local args=("$@")
    
    local script_path="$SCRIPT_DIR/$script.sh"
    
    if [[ ! -f "$script_path" ]]; then
        log_error "Script not found: $script_path"
        return 1
    fi
    
    if [[ ! -x "$script_path" ]]; then
        chmod +x "$script_path"
    fi
    
    log_info "Executing: $script ${args[*]}"
    "$script_path" "${args[@]}"
}

# Main command handling
main() {
    local command="${1:-help}"
    
    # Check prerequisites for most commands
    case "$command" in
        help|version)
            # Skip prerequisite check for help commands
            ;;
        *)
            if ! check_prerequisites; then
                exit 1
            fi
            ;;
    esac
    
    case "$command" in
        # Deployment commands
        deploy)
            execute_command "deploy" "${@:2}"
            ;;
        start)
            execute_command "manage" "start" "${@:2}"
            ;;
        stop)
            execute_command "manage" "stop" "${@:2}"
            ;;
        restart)
            execute_command "manage" "restart" "${@:2}"
            ;;
        
        # Monitoring commands
        status)
            execute_command "manage" "status"
            ;;
        logs)
            execute_command "manage" "logs" "${@:2}"
            ;;
        health)
            execute_command "manage" "health"
            ;;
        
        # Maintenance commands
        update)
            execute_command "maintenance" "update"
            ;;
        maintenance)
            execute_command "maintenance" "maintenance"
            ;;
        performance)
            execute_command "maintenance" "performance"
            ;;
        
        # Backup commands
        backup)
            execute_command "backup" "backup" "${@:2}"
            ;;
        restore)
            execute_command "backup" "restore" "${@:2}"
            ;;
        list-backups)
            execute_command "backup" "list"
            ;;
        
        # Security commands
        rotate-secrets)
            execute_command "secrets" "rotate" "${@:2}"
            ;;
        security-update)
            execute_command "maintenance" "security"
            ;;
        check-secrets)
            execute_command "secrets" "check"
            ;;
        
        # Cleanup commands
        cleanup)
            execute_command "manage" "cleanup"
            ;;
        cleanup-backups)
            execute_command "backup" "cleanup"
            ;;
        
        # Emergency commands
        recovery)
            execute_command "maintenance" "recovery"
            ;;
        reset-secrets)
            execute_command "secrets" "emergency"
            ;;
        
        # Information commands
        help|--help|-h)
            show_menu
            ;;
        version|--version|-v)
            show_version
            ;;
        
        # Interactive mode
        interactive|menu)
            interactive_mode
            ;;
        
        *)
            log_error "Unknown command: $command"
            echo ""
            show_menu
            exit 1
            ;;
    esac
}

# Interactive mode
interactive_mode() {
    while true; do
        clear
        show_menu
        echo ""
        read -p "Enter command (or 'quit' to exit): " -r command
        
        case "$command" in
            quit|exit|q)
                log_info "Goodbye!"
                break
                ;;
            "")
                continue
                ;;
            *)
                echo ""
                log_info "Executing: $command"
                echo ""
                
                # Parse command and execute
                read -ra cmd_array <<< "$command"
                main "${cmd_array[@]}"
                
                echo ""
                read -p "Press Enter to continue..." -r
                ;;
        esac
    done
}

# Make scripts executable
make_scripts_executable() {
    local scripts=("deploy.sh" "manage.sh" "backup.sh" "maintenance.sh" "secrets.sh")
    
    for script in "${scripts[@]}"; do
        local script_path="$SCRIPT_DIR/$script"
        if [[ -f "$script_path" && ! -x "$script_path" ]]; then
            chmod +x "$script_path"
        fi
    done
}

# Initialize
make_scripts_executable

# Execute main function
main "$@"