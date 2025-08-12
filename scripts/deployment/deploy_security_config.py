#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Deploy Security Configuration

Script to deploy and validate production security configuration.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from security.config.production_security_config import ProductionSecurityConfig
from security.monitoring.security_alerting import get_security_alert_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def validate_environment_variables():
    """Validate required environment variables"""
    required_vars = [
        'FLASK_SECRET_KEY',
        'PLATFORM_ENCRYPTION_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("All required environment variables are set")
    return True


def deploy_security_configuration():
    """Deploy production security configuration"""
    logger.info("Starting security configuration deployment")
    
    # Validate environment
    if not validate_environment_variables():
        return False
    
    # Initialize security configuration
    config = ProductionSecurityConfig()
    
    # Validate configuration
    validation_results = config.validate_configuration()
    
    if not all(validation_results.values()):
        logger.error("Security configuration validation failed:")
        for check, result in validation_results.items():
            if not result:
                logger.error(f"  - {check}: FAILED")
        return False
    
    logger.info("Security configuration validation passed")
    
    # Get security status
    status = config.get_security_status()
    
    logger.info("Security Configuration Status:")
    logger.info(f"  CSRF Protection: {'✓' if status['csrf_protection']['enabled'] else '✗'}")
    logger.info(f"  Security Headers: {'✓' if status['security_headers']['configured'] else '✗'}")
    logger.info(f"  Monitoring: {'✓' if status['monitoring']['enabled'] else '✗'}")
    logger.info(f"  Overall Status: {'✓' if status['overall_status'] else '✗'}")
    
    # Initialize security alerting
    alert_manager = get_security_alert_manager()
    logger.info("Security alerting system initialized")
    
    logger.info("Security configuration deployment completed successfully")
    return True


def main():
    """Main deployment function"""
    try:
        success = deploy_security_configuration()
        
        if success:
            logger.info("✓ Security configuration deployment successful")
            sys.exit(0)
        else:
            logger.error("✗ Security configuration deployment failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()