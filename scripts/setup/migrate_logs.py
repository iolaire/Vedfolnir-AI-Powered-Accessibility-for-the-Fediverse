#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Migration script to move log files to the logs directory.
"""
import os
import shutil
import glob
from config import Config

def migrate_logs():
    """Move existing log files to the logs directory"""
    print("🔄 Migrating log files to logs directory...")
    
    # Create config to ensure logs directory exists
    config = Config()
    logs_dir = config.storage.logs_dir
    
    print(f"📁 Logs directory: {logs_dir}")
    
    # Find log files in the root directory
    log_patterns = [
        "*.log",
        "*.log.*",
        "vedfolnir.log*",
        "vedfolnir.log*",
        "batch_update.log*",
        "webapp.log*"
    ]
    
    moved_files = 0
    
    for pattern in log_patterns:
        log_files = glob.glob(pattern)
        for log_file in log_files:
            if os.path.isfile(log_file):
                try:
                    # Get just the filename
                    filename = os.path.basename(log_file)
                    destination = os.path.join(logs_dir, filename)
                    
                    # Move the file
                    shutil.move(log_file, destination)
                    print(f"✅ Moved: {log_file} → {destination}")
                    moved_files += 1
                    
                except Exception as e:
                    print(f"❌ Error moving {log_file}: {e}")
    
    if moved_files == 0:
        print("ℹ️  No log files found to migrate")
    else:
        print(f"✅ Successfully migrated {moved_files} log files to {logs_dir}")
    
    print("\n📋 Log file locations after migration:")
    print(f"  • Main application: {os.path.join(logs_dir, 'vedfolnir.log')}")
    print(f"  • Web application: {os.path.join(logs_dir, 'webapp.log')}")
    print(f"  • Batch updates: {os.path.join(logs_dir, 'batch_update.log')}")
    print(f"  • All logs: {logs_dir}/*.log")

if __name__ == "__main__":
    migrate_logs()