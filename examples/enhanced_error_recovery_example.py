# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Enhanced Error Recovery System Example

Demonstrates the enhanced error handling and recovery capabilities
for multi-tenant caption management.
"""

import asyncio
import json
from enhanced_error_recovery_manager import (
    EnhancedErrorRecoveryManager,
    handle_enhanced_caption_error
)

async def main():
    """Demonstrate enhanced error recovery functionality"""
    print("Enhanced Error Recovery System Demo")
    print("=" * 50)
    
    # Create enhanced error recovery manager
    manager = EnhancedErrorRecoveryManager()
    
    # Example context for a caption generation task
    context = {
        'user_id': 1,
        'task_id': 'demo-task-123',
        'platform_connection_id': 1
    }
    
    # Demo 1: User error with recovery suggestions
    print("\n1. User Error Example:")
    try:
        error = Exception("Invalid input provided by user")
        error_info = manager.create_enhanced_error_info(error, context)
        print(f"   Category: {error_info.category.value}")
        print(f"   Escalation Level: {error_info.escalation_level.value}")
        print(f"   Recovery Suggestions: {error_info.recovery_suggestions}")
        print(f"   User Message: {manager._generate_user_friendly_message(error_info)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Demo 2: System error with admin escalation
    print("\n2. System Error with Escalation:")
    try:
        error = Exception("Database connection error")
        error_info = manager.create_enhanced_error_info(error, context)
        print(f"   Category: {error_info.category.value}")
        print(f"   Escalation Level: {error_info.escalation_level.value}")
        print(f"   Pattern Matched: {error_info.pattern_matched}")
        print(f"   Recovery Suggestions: {error_info.recovery_suggestions}")
        
        # Trigger escalation
        await manager._handle_escalation(error_info)
        print(f"   Admin Notifications: {len(manager.admin_notifications)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Demo 3: Platform error with retry logic
    print("\n3. Platform Error with Retry:")
    retry_count = 0
    
    @handle_enhanced_caption_error(context=context)
    async def failing_operation():
        nonlocal retry_count
        retry_count += 1
        if retry_count < 3:
            raise Exception("Rate limit exceeded")
        return f"Success after {retry_count} attempts"
    
    try:
        # This will demonstrate retry logic (mocked for demo)
        error = Exception("Rate limit exceeded")
        error_info = manager.create_enhanced_error_info(error, context)
        print(f"   Category: {error_info.category.value}")
        print(f"   Recoverable: {error_info.recoverable}")
        print(f"   Pattern Matched: {error_info.pattern_matched}")
        print(f"   Recovery Suggestions: {error_info.recovery_suggestions}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Demo 4: Pattern frequency escalation
    print("\n4. Pattern Frequency Escalation:")
    # Simulate multiple occurrences of the same error pattern
    for i in range(3):
        error = Exception("Authentication failed")
        error_info = manager.create_enhanced_error_info(error, context)
        manager.error_history.append(error_info)
        print(f"   Occurrence {i+1}: Escalation Level = {error_info.escalation_level.value}")
    
    # Demo 5: Enhanced error statistics
    print("\n5. Enhanced Error Statistics:")
    stats = manager.get_enhanced_error_statistics()
    print(f"   Total Errors: {stats['total_errors']}")
    print(f"   Category Breakdown: {stats['category_breakdown']}")
    print(f"   Escalation Breakdown: {stats['escalation_breakdown']}")
    print(f"   Admin Notifications: {stats['admin_notifications']}")
    print(f"   Critical Errors: {stats['critical_errors']}")
    
    # Demo 6: Admin notifications
    print("\n6. Admin Notifications:")
    notifications = manager.get_admin_notifications()
    for i, notification in enumerate(notifications):
        print(f"   Notification {i+1}:")
        print(f"     Type: {notification['type']}")
        print(f"     Severity: {notification['severity']}")
        print(f"     Message: {notification['message']}")
        print(f"     Requires Attention: {notification['requires_attention']}")
    
    print("\n" + "=" * 50)
    print("Enhanced Error Recovery Demo Complete!")

if __name__ == "__main__":
    asyncio.run(main())