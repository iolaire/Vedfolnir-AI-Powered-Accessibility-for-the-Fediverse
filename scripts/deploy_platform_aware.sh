#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# Platform-aware deployment script

set -e

echo "🚀 Starting platform-aware deployment..."

# Configuration
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="logs/deployment.log"

# Create directories
mkdir -p "$BACKUP_DIR" logs

# Functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

backup_database() {
    log "📦 Creating database backup..."
    if [ -f "storage/database/vedfolnir.db" ]; then
        cp "storage/database/vedfolnir.db" "$BACKUP_DIR/vedfolnir.db.backup"
        log "✅ Database backed up to $BACKUP_DIR"
    else
        log "ℹ️ No existing database found"
    fi
}

validate_config() {
    log "🔍 Validating configuration..."
    if python validate_config.py; then
        log "✅ Configuration valid"
    else
        log "❌ Configuration validation failed"
        exit 1
    fi
}

run_migration() {
    log "🔄 Running platform-aware migration..."
    if python migrate_to_platform_aware.py; then
        log "✅ Migration completed successfully"
    else
        log "❌ Migration failed"
        restore_backup
        exit 1
    fi
}

validate_migration() {
    log "🔍 Validating migration..."
    if python validate_migration.py; then
        log "✅ Migration validation passed"
    else
        log "❌ Migration validation failed"
        restore_backup
        exit 1
    fi
}

restore_backup() {
    log "🔄 Restoring from backup..."
    if [ -f "$BACKUP_DIR/vedfolnir.db.backup" ]; then
        cp "$BACKUP_DIR/vedfolnir.db.backup" "storage/database/vedfolnir.db"
        log "✅ Database restored from backup"
    fi
}

test_platform_operations() {
    log "🧪 Testing platform operations..."
    if python test_platform_operations.py; then
        log "✅ Platform operations test passed"
    else
        log "⚠️ Platform operations test failed (non-critical)"
    fi
}

# Main deployment process
main() {
    log "Starting deployment process..."
    
    # Pre-deployment
    backup_database
    validate_config
    
    # Deployment
    run_migration
    validate_migration
    
    # Post-deployment
    test_platform_operations
    
    log "🎉 Platform-aware deployment completed successfully!"
    log "📁 Backup stored in: $BACKUP_DIR"
}

# Handle interruption
trap 'log "❌ Deployment interrupted"; restore_backup; exit 1' INT TERM

# Run deployment
main "$@"