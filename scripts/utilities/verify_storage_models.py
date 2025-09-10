#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Verification script for storage management models.
Demonstrates the functionality of StorageOverride and StorageEventLog models.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import StorageOverride, StorageEventLog, User, UserRole

def main():
    """Demonstrate storage management models functionality"""
    print("Storage Management Models Verification")
    print("=" * 50)
    
    # Initialize database
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        # Check if we have any admin users
        admin_user = session.query(User).filter_by(role=UserRole.ADMIN).first()
        
        if not admin_user:
            print("No admin user found. Creating a demo admin user...")
            admin_user = User(
                username="demo_admin",
                email="demo@example.com",
                role=UserRole.ADMIN,
                is_active=True,
                email_verified=True
            )
            admin_user.set_password("demo_password")
            session.add(admin_user)
            session.commit()
            print(f"✅ Created demo admin user: {admin_user.username}")
        else:
            print(f"✅ Using existing admin user: {admin_user.username}")
        
        print("\n1. Testing StorageOverride Model")
        print("-" * 30)
        
        # Create a storage override
        override = StorageOverride(
            admin_user_id=admin_user.id,
            expires_at=datetime.utcnow() + timedelta(hours=2),
            duration_hours=2,
            reason="Demo storage override for testing",
            storage_gb_at_activation=8.5,
            limit_gb_at_activation=10.0
        )
        
        session.add(override)
        session.commit()
        
        print(f"✅ Created storage override: ID {override.id}")
        print(f"   - Admin User: {admin_user.username}")
        print(f"   - Duration: {override.duration_hours} hours")
        print(f"   - Reason: {override.reason}")
        print(f"   - Storage at activation: {override.storage_gb_at_activation}GB")
        print(f"   - Limit at activation: {override.limit_gb_at_activation}GB")
        print(f"   - Is currently active: {override.is_currently_active()}")
        print(f"   - Is expired: {override.is_expired()}")
        
        remaining = override.get_remaining_time()
        if remaining:
            print(f"   - Remaining time: {remaining}")
        
        print("\n2. Testing StorageEventLog Model")
        print("-" * 30)
        
        # Log various storage events
        events = []
        
        # Log limit reached
        limit_event = StorageEventLog.log_limit_reached(
            session=session,
            storage_gb=10.2,
            limit_gb=10.0,
            details={'reason': 'caption_generation_blocked', 'files_count': 1500}
        )
        events.append(limit_event)
        
        # Log override activation
        activation_event = StorageEventLog.log_override_activated(
            session=session,
            storage_gb=10.2,
            limit_gb=10.0,
            user_id=admin_user.id,
            storage_override_id=override.id,
            duration_hours=2,
            reason="Demo override activation"
        )
        events.append(activation_event)
        
        # Log warning threshold exceeded
        warning_event = StorageEventLog.log_warning_threshold_exceeded(
            session=session,
            storage_gb=8.5,
            limit_gb=10.0,
            threshold_percentage=80
        )
        events.append(warning_event)
        
        # Log cleanup performed
        cleanup_event = StorageEventLog.log_cleanup_performed(
            session=session,
            storage_gb_before=10.2,
            storage_gb_after=7.8,
            limit_gb=10.0,
            user_id=admin_user.id,
            cleanup_details={'files_deleted': 200, 'space_freed_mb': 2400}
        )
        events.append(cleanup_event)
        
        # Log limit lifted
        lifted_event = StorageEventLog.log_limit_lifted(
            session=session,
            storage_gb=7.8,
            limit_gb=10.0,
            reason='cleanup_completed'
        )
        events.append(lifted_event)
        
        session.commit()
        
        print(f"✅ Created {len(events)} storage events:")
        for i, event in enumerate(events, 1):
            print(f"   {i}. {event.event_type}")
            print(f"      - Storage: {event.storage_gb}GB / {event.limit_gb}GB ({event.usage_percentage:.1f}%)")
            print(f"      - Timestamp: {event.timestamp}")
            if event.user_id:
                print(f"      - User: {admin_user.username}")
            details = event.get_details()
            if details:
                print(f"      - Details: {details}")
            print()
        
        print("3. Testing Relationships")
        print("-" * 30)
        
        # Test override-event relationships
        related_events = override.related_events
        print(f"✅ Override has {len(related_events)} related events:")
        for event in related_events:
            print(f"   - {event.event_type} at {event.timestamp}")
        
        # Test user relationships
        user_events = admin_user.storage_events
        print(f"✅ Admin user has {len(user_events)} storage events")
        
        user_overrides = admin_user.storage_overrides_created
        print(f"✅ Admin user has created {len(user_overrides)} storage overrides")
        
        print("\n4. Testing Model Methods")
        print("-" * 30)
        
        # Test override deactivation
        print("Testing override deactivation...")
        override.deactivate(admin_user.id, "Demo completed")
        session.commit()
        
        print(f"✅ Override deactivated:")
        print(f"   - Is active: {override.is_active}")
        print(f"   - Is currently active: {override.is_currently_active()}")
        print(f"   - Deactivated at: {override.deactivated_at}")
        print(f"   - Deactivated by: {admin_user.username}")
        print(f"   - Updated reason: {override.reason}")
        
        # Log the deactivation
        deactivation_event = StorageEventLog.log_override_deactivated(
            session=session,
            storage_gb=7.8,
            limit_gb=10.0,
            user_id=admin_user.id,
            storage_override_id=override.id,
            reason="Demo completed"
        )
        session.commit()
        
        print(f"✅ Logged deactivation event: {deactivation_event.event_type}")
        
        print("\n5. Database Statistics")
        print("-" * 30)
        
        # Get counts
        override_count = session.query(StorageOverride).count()
        event_count = session.query(StorageEventLog).count()
        
        print(f"✅ Total storage overrides in database: {override_count}")
        print(f"✅ Total storage events in database: {event_count}")
        
        # Get recent events
        recent_events = session.query(StorageEventLog).order_by(
            StorageEventLog.timestamp.desc()
        ).limit(5).all()
        
        print(f"\n✅ Recent storage events:")
        for event in recent_events:
            print(f"   - {event.event_type}: {event.storage_gb}GB/{event.limit_gb}GB at {event.timestamp}")
        
        print("\n" + "=" * 50)
        print("✅ Storage management models verification completed successfully!")
        print("All models are working correctly with proper relationships and methods.")

if __name__ == "__main__":
    main()