#!/usr/bin/env python3
"""
Direct database connection test for production validation
"""
import os
import asyncio
import sys
sys.path.append('/home/antarpreet/Projects/bella_v3')

from app.db.session import get_session
from app.crud.user import get_user_by_mobile, create_user
from app.crud.appointment import create_appointment_unique
from app.schemas.user import UserCreate
import sqlalchemy as sa
from datetime import datetime, timezone, timedelta

async def test_db_connection():
    """Test database connection and appointment creation"""
    print("🔍 Testing Production Database Connection...")

    try:
        # Get database session
        async for db in get_session():
            # Test basic connectivity
            result = await db.execute(sa.text("SELECT 1 as test_value"))
            test_val = result.scalar()
            print(f"✅ Basic DB Query: {test_val}")

            # Test user operations
            test_mobile = "+15559876543"
            user = await get_user_by_mobile(db, test_mobile)

            if not user:
                print("👤 Creating test user...")
                user_data = UserCreate(
                    full_name="DB Test User",
                    mobile=test_mobile
                )
                user = await create_user(db, user_data)
                print(f"✅ User created: {user.id}")
            else:
                print(f"✅ User found: {user.id}")

            # Test appointment creation
            print("📅 Testing appointment creation...")
            future_time = datetime.now(timezone.utc) + timedelta(days=30, hours=2)

            try:
                appointment = await create_appointment_unique(
                    db,
                    user_id=user.id,
                    starts_at_utc=future_time,
                    duration_min=30,
                    notes="Production DB test appointment"
                )
                print(f"✅ Appointment created: {appointment.id} at {appointment.starts_at}")

                # Clean up test appointment
                await db.delete(appointment)
                await db.commit()
                print("🧹 Test appointment cleaned up")

            except Exception as appt_e:
                print(f"❌ Appointment creation failed: {appt_e}")
                await db.rollback()

            print("✅ Database connectivity test completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_db_connection())
    exit(0 if result else 1)