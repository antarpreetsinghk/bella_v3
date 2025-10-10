#!/usr/bin/env python3
"""
Production test fixtures and configuration.
Provides safe database access for production testing with automatic cleanup.
"""

import pytest
import pytest_asyncio
import os
import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.db.session import Base
from app.db.models.appointment import Appointment
from app.db.models.user import User


# Production database configuration
PRODUCTION_DB_URL = os.getenv("PRODUCTION_DB_URL", "")
PRODUCTION_DB_TEST_MODE = os.getenv("PRODUCTION_DB_TEST_MODE", "false").lower() == "true"
TEST_DATA_AUTO_CLEANUP = os.getenv("TEST_DATA_AUTO_CLEANUP", "true").lower() == "true"


# Skip marker for production database tests
skip_if_no_prod_db = pytest.mark.skipif(
    not PRODUCTION_DB_URL,
    reason="PRODUCTION_DB_URL environment variable not set"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def prod_db_engine():
    """
    Create production database engine for testing.

    Safety checks:
    - Requires PRODUCTION_DB_URL to be set
    - Recommends PRODUCTION_DB_TEST_MODE=true for extra safety
    - Uses connection pooling for performance
    """
    if not PRODUCTION_DB_URL:
        pytest.skip("PRODUCTION_DB_URL not configured")

    # Warn if not in test mode
    if not PRODUCTION_DB_TEST_MODE:
        import warnings
        warnings.warn(
            "PRODUCTION_DB_TEST_MODE is not enabled. "
            "Set PRODUCTION_DB_TEST_MODE=true for extra safety checks.",
            UserWarning
        )

    # Create engine with production-safe settings
    engine = create_async_engine(
        PRODUCTION_DB_URL,
        echo=False,  # Disable SQL logging in production tests
        pool_pre_ping=True,  # Verify connections before use
        pool_size=5,  # Limit concurrent connections
        max_overflow=10,
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Verify connection
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1, "Database connection test failed"

    yield engine

    # Cleanup: close all connections
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def prod_session_factory(prod_db_engine):
    """Create session factory for production database"""
    return async_sessionmaker(
        prod_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def prod_db(prod_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a production database session with automatic cleanup.

    Features:
    - Automatic cleanup of test data after each test
    - Transaction rollback on test failure (where possible)
    - Tracks created test appointments for cleanup
    """
    async with prod_session_factory() as session:
        # Track test data created during this session
        test_appointment_ids = []
        test_user_ids = []

        # Store IDs in session for cleanup tracking
        session.info["test_appointment_ids"] = test_appointment_ids
        session.info["test_user_ids"] = test_user_ids

        yield session

        # Automatic cleanup after test
        if TEST_DATA_AUTO_CLEANUP:
            try:
                # Clean up test appointments
                if test_appointment_ids:
                    await session.execute(
                        text("DELETE FROM appointments WHERE id = ANY(:ids) AND is_test_data = true"),
                        {"ids": test_appointment_ids}
                    )

                # Note: Don't delete users automatically - they might be reused
                # Use manual cleanup for users if needed

                await session.commit()
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
                await session.rollback()


@pytest_asyncio.fixture
async def prod_db_with_rollback(prod_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a production database session with transaction rollback.

    USE WITH CAUTION: This fixture uses transactions and rolls back all changes.
    Best for read-only tests or tests that should not persist data.

    Note: Won't work with tests that require committed data (e.g., cross-transaction tests)
    """
    async with prod_session_factory() as session:
        async with session.begin():
            # Yield session within transaction
            yield session

            # Automatic rollback at end of test
            await session.rollback()


@pytest_asyncio.fixture
async def test_call_context():
    """
    Provide context for a test call with unique identifiers.

    Generates:
    - Unique CallSid for this test
    - Test phone number
    - Test user data
    """
    import time
    import uuid

    call_id = f"TEST_PROD_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    return {
        "call_sid": call_id,
        "from_number": f"+1416555{str(int(time.time()) % 10000).zfill(4)}",
        "test_name": f"Test User {call_id[-8:]}",
        "timestamp": int(time.time()),
    }


@pytest.fixture
def production_test_url():
    """Get production test URL from environment"""
    url = os.getenv("PRODUCTION_TEST_URL", os.getenv("FUNCTION_URL", ""))
    if not url:
        pytest.skip("PRODUCTION_TEST_URL or FUNCTION_URL not configured")
    return url


@pytest.fixture
def production_api_key():
    """Get production API key from environment (optional)"""
    return os.getenv("PRODUCTION_API_KEY", "")


def pytest_configure(config):
    """Configure pytest with production test markers"""
    config.addinivalue_line(
        "markers",
        "prod_db: Tests that require production database access"
    )
    config.addinivalue_line(
        "markers",
        "prod_db_write: Tests that write to production database (use with caution)"
    )
    config.addinivalue_line(
        "markers",
        "prod_e2e: End-to-end tests with production database validation"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip production database tests if DB URL not configured.
    Add safety warnings for write tests.
    """
    for item in items:
        # Skip tests requiring production DB if not configured
        if item.get_closest_marker("prod_db") or item.get_closest_marker("prod_db_write"):
            if not PRODUCTION_DB_URL:
                item.add_marker(pytest.mark.skip(
                    reason="PRODUCTION_DB_URL not configured"
                ))

        # Add extra warning for write tests
        if item.get_closest_marker("prod_db_write"):
            if not PRODUCTION_DB_TEST_MODE:
                import warnings
                warnings.warn(
                    f"Test '{item.name}' will WRITE to production database. "
                    f"Ensure PRODUCTION_DB_URL points to a test/staging database.",
                    UserWarning
                )
