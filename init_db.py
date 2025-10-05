#!/usr/bin/env python3
"""
Database initialization script for cost-optimized SQLite deployment
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

async def init_database():
    """Initialize SQLite database with tables"""
    try:
        # Import after setting up the path
        from app.db.session import engine
        from app.db.models.user import User
        from app.db.models.appointment import Appointment

        print("🗄️  Initializing SQLite database...")

        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Create all tables
        async with engine.begin() as conn:
            # Import the Base from session to get all models
            from app.db.session import Base
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Database tables created successfully!")
        print(f"📍 Database location: {data_dir.absolute()}/bella.db")

        # Test the connection
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # Simple test query
            result = await session.execute("SELECT 1 as test")
            test_value = result.scalar()
            if test_value == 1:
                print("✅ Database connection test passed!")
            else:
                print("❌ Database connection test failed!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

    return True

async def create_sample_data():
    """Create some sample data for testing"""
    try:
        from app.db.session import AsyncSessionLocal
        from app.db.models.user import User
        from app.db.models.appointment import Appointment
        from datetime import datetime, timedelta
        import sqlalchemy as sa

        print("📝 Creating sample data...")

        async with AsyncSessionLocal() as session:
            # Check if we already have users
            result = await session.execute(sa.select(User))
            existing_users = result.scalars().all()

            if existing_users:
                print("📊 Sample data already exists, skipping creation")
                return True

            # Create a sample user
            sample_user = User(
                full_name="John Doe",
                mobile="+15551234567"
            )
            session.add(sample_user)
            await session.flush()  # Get the user ID

            # Create a sample appointment
            sample_appointment = Appointment(
                user_id=sample_user.id,
                starts_at=datetime.utcnow() + timedelta(days=1),
                duration_min=30,
                status="booked",
                notes="Sample appointment created during initialization"
            )
            session.add(sample_appointment)

            await session.commit()
            print("✅ Sample data created successfully!")

    except Exception as e:
        print(f"⚠️  Could not create sample data: {e}")
        # This is not critical, so we return True anyway
        return True

if __name__ == "__main__":
    print("🚀 Bella V3 Database Initialization")
    print("=" * 50)

    # Set environment variable for SQLite
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/bella.db")

    # Run initialization
    success = asyncio.run(init_database())

    if success:
        # Create sample data
        asyncio.run(create_sample_data())

        print("\n🎉 Database initialization complete!")
        print("\nNext steps:")
        print("1. Update your .env file with actual API keys")
        print("2. Run: docker-compose -f docker-compose.cost-optimized.yml up -d")
        print("3. Test: curl http://localhost:8000/healthz")
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)