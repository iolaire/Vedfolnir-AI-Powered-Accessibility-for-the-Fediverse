#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# CSS Security Enhancement Deployment Script
# This script automates the deployment of CSS security enhancements

set -e  # Exit on any error

# Configuration
BASE_URL="http://127.0.0.1:5000"
BACKUP_DIR="backups/css-security-$(date +%Y%m%d_%H%M%S)"
LOG_FILE="logs/css_deployment_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}❌ Error: $1${NC}"
    log "${YELLOW}Check log file: $LOG_FILE${NC}"
    exit 1
}

# Success message
success() {
    log "${GREEN}✅ $1${NC}"
}

# Warning message
warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

# Info message
info() {
    log "${BLUE}ℹ️  $1${NC}"
}

# Check if running from project root
check_project_root() {
    if [[ ! -f "web_app.py" ]] || [[ ! -d "templates" ]]; then
        error_exit "Please run this script from the project root directory"
    fi
}

# Pre-deployment validation
pre_deployment_validation() {
    log "\n${BLUE}=== Pre-Deployment Validation ===${NC}"
    
    # Check CSS files exist
    css_files=(
        "static/css/security-extracted.css"
        "static/css/components.css"
        "admin/static/css/admin-extracted.css"
    )
    
    for css_file in "${css_files[@]}"; do
        if [[ -f "$css_file" ]]; then
            size=$(wc -l < "$css_file")
            success "$css_file exists ($size lines)"
        else
            error_exit "$css_file does not exist"
        fi
    done
    
    # Run inline style detection
    info "Checking for inline styles..."
    if python tests/scripts/css_extraction_helper.py > /dev/null 2>&1; then
        success "Inline style check passed"
    else
        warning "Inline style check returned warnings - review output"
    fi
    
    # Validate template syntax
    info "Validating template syntax..."
    python -c "
import os
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

def validate_templates():
    template_dirs = ['templates', 'admin/templates']
    errors = []
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            env = Environment(loader=FileSystemLoader(template_dir))
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        template_path = os.path.relpath(os.path.join(root, file), template_dir)
                        try:
                            env.get_template(template_path)
                        except TemplateSyntaxError as e:
                            errors.append(f'{template_path}: {e}')
    
    if errors:
        print(f'Template errors found: {len(errors)}')
        for error in errors:
            print(f'  {error}')
        exit(1)
    else:
        print('All templates validated successfully')

validate_templates()
" || error_exit "Template validation failed"
    
    success "Pre-deployment validation completed"
}

# Create backup
create_backup() {
    log "\n${BLUE}=== Creating Backup ===${NC}"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup templates
    cp -r templates "$BACKUP_DIR/" || error_exit "Failed to backup templates"
    cp -r admin/templates "$BACKUP_DIR/admin_templates" || error_exit "Failed to backup admin templates"
    
    # Backup CSS files
    cp -r static/css "$BACKUP_DIR/static_css" || error_exit "Failed to backup static CSS"
    cp -r admin/static/css "$BACKUP_DIR/admin_static_css" || error_exit "Failed to backup admin CSS"
    
    # Backup configuration files
    cp config.py "$BACKUP_DIR/" || error_exit "Failed to backup config.py"
    cp web_app.py "$BACKUP_DIR/" || error_exit "Failed to backup web_app.py"
    
    # Create backup manifest
    {
        echo "CSS Security Enhancement Backup - $(date)"
        echo "Templates: $(find templates -name '*.html' | wc -l) files"
        echo "Admin Templates: $(find admin/templates -name '*.html' | wc -l) files"
        echo "CSS Files: $(find static/css -name '*.css' | wc -l) files"
        echo "Admin CSS Files: $(find admin/static/css -name '*.css' | wc -l) files"
    } > "$BACKUP_DIR/MANIFEST.txt"
    
    success "Backup created in: $BACKUP_DIR"
}

# Deploy CSS files
deploy_css_files() {
    log "\n${BLUE}=== Deploying CSS Files ===${NC}"
    
    # Set correct permissions
    chmod 644 static/css/*.css || error_exit "Failed to set permissions on static CSS files"
    chmod 644 admin/static/css/*.css || error_exit "Failed to set permissions on admin CSS files"
    
    # Verify CSS file integrity
    css_files=(
        "static/css/security-extracted.css"
        "static/css/components.css"
        "admin/static/css/admin-extracted.css"
    )
    
    for css_file in "${css_files[@]}"; do
        if [[ -f "$css_file" ]]; then
            lines=$(wc -l < "$css_file")
            success "$css_file deployed ($lines lines)"
        else
            error_exit "$css_file missing during deployment"
        fi
    done
}

# Clear caches
clear_caches() {
    log "\n${BLUE}=== Clearing Caches ===${NC}"
    
    # Clear Python cache
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # Clear any Flask template cache
    if [[ -d "flask_cache" ]]; then
        rm -rf flask_cache
        success "Cleared Flask cache"
    fi
    
    success "Caches cleared"
}

# Restart application
restart_application() {
    log "\n${BLUE}=== Restarting Application ===${NC}"
    
    # Kill existing process
    pkill -f "python web_app.py" || true
    sleep 2
    
    # Start application in background
    python web_app.py & sleep 10
    
    # Check if application started
    if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL" | grep -q "200"; then
        success "Application restarted successfully"
    else
        error_exit "Application failed to start properly"
    fi
}

# Post-deployment verification
post_deployment_verification() {
    log "\n${BLUE}=== Post-Deployment Verification ===${NC}"
    
    # Application health check
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL")
    if [[ "$status" == "200" ]]; then
        success "Application health check passed (HTTP $status)"
    else
        error_exit "Application health check failed (HTTP $status)"
    fi
    
    # CSS file accessibility
    css_urls=(
        "$BASE_URL/static/css/security-extracted.css"
        "$BASE_URL/static/css/components.css"
        "$BASE_URL/admin/static/css/admin-extracted.css"
    )
    
    for css_url in "${css_urls[@]}"; do
        status=$(curl -s -o /dev/null -w "%{http_code}" "$css_url")
        if [[ "$status" == "200" ]]; then
            success "$(basename "$css_url") accessible via HTTP"
        else
            error_exit "$(basename "$css_url") returned HTTP $status"
        fi
    done
    
    # Check for inline styles
    info "Verifying no inline styles remain..."
    if python tests/scripts/css_extraction_helper.py | grep -q "No inline styles found"; then
        success "No inline styles detected"
    else
        warning "Inline styles may still be present - review output"
    fi
    
    # Test key pages
    test_pages=(
        "$BASE_URL/"
        "$BASE_URL/login"
        "$BASE_URL/caption_generation"
    )
    
    for page in "${test_pages[@]}"; do
        status=$(curl -s -o /dev/null -w "%{http_code}" "$page")
        if [[ "$status" == "200" ]]; then
            success "$(basename "$page") page loads correctly"
        else
            warning "$(basename "$page") page returned HTTP $status"
        fi
    done
    
    success "Post-deployment verification completed"
}

# Run monitoring check
run_monitoring_check() {
    log "\n${BLUE}=== Running Monitoring Check ===${NC}"
    
    if [[ -f "scripts/monitoring/css_security_monitor.py" ]]; then
        python scripts/monitoring/css_security_monitor.py || warning "Monitoring check completed with warnings"
        success "Monitoring check completed"
    else
        warning "Monitoring script not found - skipping"
    fi
}

# Main deployment function
deploy() {
    log "${GREEN}=== CSS Security Enhancement Deployment ===${NC}"
    log "Started at: $(date)"
    log "Backup directory: $BACKUP_DIR"
    log "Log file: $LOG_FILE"
    
    check_project_root
    pre_deployment_validation
    create_backup
    deploy_css_files
    clear_caches
    restart_application
    post_deployment_verification
    run_monitoring_check
    
    log "\n${GREEN}=== Deployment Completed Successfully ===${NC}"
    log "Completed at: $(date)"
    log "Backup location: $BACKUP_DIR"
    log "Log file: $LOG_FILE"
    
    info "Next steps:"
    info "1. Monitor application for 30 minutes"
    info "2. Run extended testing"
    info "3. Enable CSP headers if not already enabled"
    info "4. Update documentation"
}

# Rollback function
rollback() {
    if [[ -z "$1" ]]; then
        # Find latest backup
        LATEST_BACKUP=$(ls -1t backups/css-security-* 2>/dev/null | head -1)
        if [[ -z "$LATEST_BACKUP" ]]; then
            error_exit "No backup found for rollback"
        fi
    else
        LATEST_BACKUP="$1"
    fi
    
    log "${YELLOW}=== Emergency Rollback ===${NC}"
    log "Rolling back to: $LATEST_BACKUP"
    
    # Stop application
    pkill -f "python web_app.py" || true
    sleep 2
    
    # Restore files
    cp -r "$LATEST_BACKUP/templates" . || error_exit "Failed to restore templates"
    cp -r "$LATEST_BACKUP/admin_templates" admin/templates || error_exit "Failed to restore admin templates"
    cp -r "$LATEST_BACKUP/static_css" static/css || error_exit "Failed to restore static CSS"
    cp -r "$LATEST_BACKUP/admin_static_css" admin/static/css || error_exit "Failed to restore admin CSS"
    cp "$LATEST_BACKUP/config.py" . || error_exit "Failed to restore config.py"
    cp "$LATEST_BACKUP/web_app.py" . || error_exit "Failed to restore web_app.py"
    
    # Restart application
    python web_app.py & sleep 10
    
    # Verify rollback
    status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL")
    if [[ "$status" == "200" ]]; then
        success "Rollback completed successfully"
    else
        error_exit "Rollback failed - application not responding"
    fi
    
    log "${GREEN}Emergency rollback completed${NC}"
}

# Help function
show_help() {
    echo "CSS Security Enhancement Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     - Run full deployment (default)"
    echo "  rollback   - Emergency rollback to latest backup"
    echo "  rollback [backup_dir] - Rollback to specific backup"
    echo "  validate   - Run pre-deployment validation only"
    echo "  monitor    - Run monitoring check only"
    echo "  help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run full deployment"
    echo "  $0 deploy            # Run full deployment"
    echo "  $0 rollback          # Emergency rollback"
    echo "  $0 validate          # Validation only"
    echo "  $0 monitor           # Monitoring check only"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "rollback")
        rollback "$2"
        ;;
    "validate")
        check_project_root
        pre_deployment_validation
        ;;
    "monitor")
        run_monitoring_check
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac