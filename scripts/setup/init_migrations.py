#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import sys
import logging
import subprocess
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command_args):
    """Run a command safely without shell injection"""
    from security.core.security_utils import sanitize_for_log
    logger.info(f"Running command: {sanitize_for_log(' '.join(command_args))}")
    try:
        result = subprocess.run(command_args, shell=False, check=True, capture_output=True, text=True)
        logger.info(f"Command output: {sanitize_for_log(result.stdout)}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {sanitize_for_log(str(e))}")
        logger.error(f"Error output: {sanitize_for_log(e.stderr)}")
        return False

def init_migrations():
    """Initialize Alembic migrations"""
    # MySQL doesn't require local database directory creation
    config = Config()
    
    # Check if migrations/versions directory exists
    if not os.path.exists("migrations/versions"):
        logger.info("Creating migrations/versions directory")
        os.makedirs("migrations/versions", exist_ok=True)
    
    # Create initial migration
    logger.info("Creating initial migration")
    if not run_command(["alembic", "revision", "--autogenerate", "-m", "Initial migration"]):
        return False
    
    # Apply the migration
    logger.info("Applying migration")
    if not run_command(["alembic", "upgrade", "head"]):
        return False
    
    logger.info("Migration initialization completed successfully")
    return True

if __name__ == "__main__":
    success = init_migrations()
    sys.exit(0 if success else 1)