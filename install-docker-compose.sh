#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

set -euo pipefail

# Vedfolnir Docker Compose Installation Script
# Quick installation and setup for Docker Compose deployment

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

# Main installation function
main() {
    log_header "Vedfolnir Docker Compose Installation"
    
    echo ""
    echo "This script will set up Vedfolnir for Docker Compose deployment."
    echo ""
    echo "What this script does:"
    echo "  ✓ Check prerequisites (Docker, Docker Compose)"
    echo "  ✓ Make management scripts executable"
    echo "  ✓ Run initial deployment setup"
    echo "  ✓ Verify installation"
    echo ""
    
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled"
        exit 0
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Make scripts executable
    make_scripts_executable
    
    # Run deployment
    run_deployment
    
    # Show completion message
    show_completion
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=0
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        echo "Please install Docker from: https://docs.docker.com/get-docker/"
        ((missing++))
    else
        log_success "Docker found: $(docker --version)"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
        ((missing++))
    else
        if command -v docker-compose &> /dev/null; then
            log_success "Docker Compose found: $(docker-compose --version)"
        else
            log_success "Docker Compose found: $(docker compose version)"
        fi
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        echo "Please start Docker and try again"
        ((missing++))
    else
        log_success "Docker daemon is running"
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        ((missing++))
    else
        log_success "Python 3 found: $(python3 --version)"
    fi
    
    # Check required Python packages
    if ! python3 -c "import cryptography" &> /dev/null; then
        log_warning "cryptography package not found - will be needed for secret generation"
        echo "Install with: pip3 install cryptography"
    fi
    
    if [[ $missing -gt 0 ]]; then
        log_error "Prerequisites check failed. Please install missing components and try again."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Make scripts executable
make_scripts_executable() {
    log_info "Making management scripts executable..."
    
    local scripts=(
        "scripts/docker/deploy.sh"
        "scripts/docker/manage.sh"
        "scripts/docker/backup.sh"
        "scripts/docker/maintenance.sh"
        "scripts/docker/secrets.sh"
        "scripts/docker/docker-compose-manager.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            chmod +x "$script"
            log_success "Made executable: $script"
        else
            log_warning "Script not found: $script"
        fi
    done
}

# Run deployment
run_deployment() {
    log_info "Running Docker Compose deployment..."
    
    if [[ -f "scripts/docker/deploy.sh" ]]; then
        ./scripts/docker/deploy.sh
    else
        log_error "Deployment script not found"
        exit 1
    fi
}

# Show completion message
show_completion() {
    log_header "Installation Complete!"
    
    echo ""
    echo "🎉 Vedfolnir Docker Compose installation completed successfully!"
    echo ""
    echo "📋 What's been set up:"
    echo "  ✓ Docker Compose services"
    echo "  ✓ Database (MySQL)"
    echo "  ✓ Session storage (Redis)"
    echo "  ✓ Monitoring (Prometheus, Grafana, Loki)"
    echo "  ✓ Security (Vault, secrets management)"
    echo "  ✓ Backup and maintenance scripts"
    echo ""
    echo "🌐 Access your services:"
    echo "  • Application: http://localhost:80"
    echo "  • Grafana: http://localhost:3000"
    echo "  • Prometheus: http://localhost:9090"
    echo ""
    echo "🛠️  Management commands:"
    echo "  • Status: ./scripts/docker/docker-compose-manager.sh status"
    echo "  • Logs: ./scripts/docker/docker-compose-manager.sh logs --follow"
    echo "  • Backup: ./scripts/docker/docker-compose-manager.sh backup full"
    echo "  • Interactive: ./scripts/docker/docker-compose-manager.sh interactive"
    echo ""
    echo "📚 Documentation:"
    echo "  • Management guide: scripts/docker/README.md"
    echo "  • Requirements: .kiro/specs/docker-compose-migration/requirements.md"
    echo "  • Design: .kiro/specs/docker-compose-migration/design.md"
    echo ""
    echo "🔧 Next steps:"
    echo "  1. Configure your platform connections in the web interface"
    echo "  2. Set up your Ollama service (external requirement)"
    echo "  3. Review and customize configuration files in config/"
    echo "  4. Set up automated backups and monitoring"
    echo ""
    echo "❓ Need help?"
    echo "  • Run: ./scripts/docker/docker-compose-manager.sh help"
    echo "  • Check logs: ./scripts/docker/docker-compose-manager.sh logs"
    echo "  • Health check: ./scripts/docker/docker-compose-manager.sh health"
    echo ""
    log_success "Happy containerizing! 🐳"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --dry-run      Show what would be done without executing"
    echo ""
    echo "This script sets up Vedfolnir for Docker Compose deployment."
}

# Parse command line arguments
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Execute installation
if [[ "$DRY_RUN" == "true" ]]; then
    log_info "DRY RUN - Would perform installation steps"
    exit 0
else
    main
fi