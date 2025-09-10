#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Command-line interface for batch updating approved captions to ActivityPub
"""

import asyncio
import argparse
import logging
import json
import sys
import os
from config import Config
from batch_update_service import BatchUpdateService

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/batch_update.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the batch update CLI"""
    parser = argparse.ArgumentParser(description='Batch update approved captions to ActivityPub')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of images to process')
    parser.add_argument('--batch-size', type=int, help='Number of posts to process in each batch')
    parser.add_argument('--concurrent', type=int, help='Maximum number of concurrent batches')
    parser.add_argument('--verify-delay', type=int, help='Delay in seconds before verification')
    parser.add_argument('--no-rollback', action='store_true', help='Disable rollback on failure')
    parser.add_argument('--dry-run', action='store_true', help='Simulate updates without making changes')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = Config()
    
    # Override configuration with command-line arguments
    if args.batch_size:
        config.batch_size = args.batch_size
    
    if args.concurrent:
        config.max_concurrent_batches = args.concurrent
    
    if args.verify_delay:
        config.verification_delay = args.verify_delay
    
    if args.no_rollback:
        config.rollback_on_failure = False
    
    if args.dry_run:
        config.dry_run = True
    
    # Log configuration
    logger.info(f"Batch update configuration:")
    logger.info(f"  Limit: {args.limit}")
    logger.info(f"  Batch size: {config.batch_size}")
    logger.info(f"  Concurrent batches: {config.max_concurrent_batches}")
    logger.info(f"  Verification delay: {config.verification_delay}s")
    logger.info(f"  Rollback on failure: {config.rollback_on_failure}")
    logger.info(f"  Dry run: {config.dry_run}")
    
    # Create and run the batch update service
    service = BatchUpdateService(config)
    
    try:
        stats = await service.batch_update_captions(args.limit)
        
        # Print results
        print("\nBatch Update Results:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Verified: {stats['verified']}")
        print(f"  Rollbacks: {stats['rollbacks']}")
        
        if stats['errors']:
            print(f"\nErrors ({len(stats['errors'])}):")
            for error in stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            
            if len(stats['errors']) > 5:
                print(f"  ... and {len(stats['errors']) - 5} more errors")
        
        return 0 if stats['failed'] == 0 else 1
    
    except Exception as e:
        logger.error(f"Error running batch update: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))