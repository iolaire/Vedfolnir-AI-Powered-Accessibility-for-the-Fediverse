#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify the confirmation function works correctly
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class MockUser:
    def __init__(self, username, email, role):
        self.username = username
        self.email = email
        self.role = MockRole(role)

class MockRole:
    def __init__(self, value):
        self.value = value

def confirm_deletion(user):
    """Get confirmation for deletion"""
    print(f"\n⚠️  FINAL CONFIRMATION")
    print("=" * 30)
    print(f"User to delete: {user.username} ({user.email}) - {user.role.value}")
    print("\n🚨 WARNING: This action is IRREVERSIBLE!")
    print("This will permanently delete:")
    print("  • User account")
    print("  • All posts and images")
    print("  • All processing runs")
    print("  • All platform connections")
    print("  • All sessions and cached data")
    print("  • All audit logs")
    print("  • All associated files and directories")
    
    # First, simple yes/no confirmation
    print(f"\nAre you absolutely sure you want to delete user '{user.username}'?")
    simple_confirm = input("Type 'yes' to continue or anything else to cancel: ").strip().lower()
    
    if simple_confirm != 'yes':
        print("❌ Deletion cancelled.")
        return False
    
    # Second, more specific confirmation
    print(f"\nFinal confirmation required.")
    print(f"To proceed, type exactly: DELETE {user.username}")
    print(f"(You must include the username '{user.username}' after DELETE)")
    confirmation = input("Final confirmation: ").strip()
    
    expected = f"DELETE {user.username}"
    if confirmation == expected:
        return True
    else:
        print(f"❌ Confirmation text did not match.")
        print(f"   Expected: DELETE {user.username}")
        print(f"   You typed: {confirmation}")
        print("   Deletion cancelled.")
        return False

def main():
    print("🧪 Testing User Deletion Confirmation")
    print("=" * 40)
    
    # Create a mock user
    test_user = MockUser("testuser", "test@example.com", "admin")
    
    print("This will test the confirmation process without actually deleting anything.")
    print("Try different inputs to see how the confirmation works:")
    print("1. First prompt: type 'yes' to continue")
    print("2. Second prompt: type 'DELETE testuser' to confirm")
    
    result = confirm_deletion(test_user)
    
    if result:
        print("\n✅ Confirmation successful! (In real script, deletion would proceed)")
    else:
        print("\n❌ Confirmation failed or cancelled.")

if __name__ == "__main__":
    main()