#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Utility script to detect the platform type of an ActivityPub instance
"""

import asyncio
import argparse
import logging
from activitypub_platforms import detect_platform_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Detect ActivityPub platform type')
    parser.add_argument('instance_url', help='URL of the ActivityPub instance')
    args = parser.parse_args()
    
    logger.info(f"Detecting platform type for {args.instance_url}...")
    platform_type = await detect_platform_type(args.instance_url)
    
    if platform_type == 'unknown':
        logger.warning(f"Could not detect platform type for {args.instance_url}")
        print(f"Platform type: unknown")
    else:
        logger.info(f"Detected platform type: {platform_type}")
        print(f"Platform type: {platform_type}")
    
    # Provide configuration hint
    print("\nTo use this platform in your .env file:")
    print(f"ACTIVITYPUB_PLATFORM_TYPE={platform_type}")

if __name__ == "__main__":
    asyncio.run(main())