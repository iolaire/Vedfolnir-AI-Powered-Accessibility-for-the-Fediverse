#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
User Management Migration Runner

This script runs the user management database migration to add email verification,
password reset, GDPR compliance, and audit trail functionality.
"""

import sys
import os
import logging

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from migrations.user_management_migration import run_migration

def main():
    """Main entry point for the migration runner"""
    print("Starting User Management Database Migration...")
    print("=" * 50)
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        result = run_migration()
        
        if result == 0:
            print("\n" + "=" * 50)
            print("✅ User Management Migration Completed Successfully!")
            print("\nNew features added:")
            print("- Email verification system")
            print("- Password reset functionality")
            print("- GDPR compliance fields")
            print("- Account security (lockout protection)")
            print("- User audit trail logging")
            print("\nYou can now implement the user management services and web interface.")
        else:
            print("\n" + "=" * 50)
            print("❌ User Management Migration Failed!")
            print("Check the logs above for error details.")
        
        return result
        
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())