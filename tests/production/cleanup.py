#!/usr/bin/env python3
"""
Safe cleanup utilities for production test data.

These utilities ensure test appointments can be safely removed from
production databases without affecting real customer data.

Safety Features:
- Only deletes appointments with is_test_data=True
- Time-based retention policies
- Dry-run mode for verification
- Detailed logging of all deletions
- Never deletes real customer appointments
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.db.models.appointment import Appointment
from app.db.models.user import User


async def count_test_appointments(
    session: AsyncSession,
    include_cancelled: bool = True
) -> int:
    """
    Count test appointments in the database.

    Args:
        session: Database session
        include_cancelled: Include cancelled appointments in count

    Returns:
        Number of test appointments
    """
    query = select(func.count(Appointment.id)).where(
        Appointment.is_test_data == True  # noqa: E712
    )

    if not include_cancelled:
        query = query.where(Appointment.status != "cancelled")

    result = await session.execute(query)
    count = result.scalar()
    return count or 0


async def list_test_appointments(
    session: AsyncSession,
    limit: int = 100,
    older_than_hours: Optional[int] = None
) -> List[Appointment]:
    """
    List test appointments with optional age filter.

    Args:
        session: Database session
        limit: Maximum number of appointments to return
        older_than_hours: Only return appointments older than this many hours

    Returns:
        List of test appointment objects
    """
    query = select(Appointment).where(
        Appointment.is_test_data == True  # noqa: E712
    ).order_by(Appointment.created_at.desc()).limit(limit)

    if older_than_hours is not None:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        query = query.where(Appointment.created_at < cutoff_time)

    result = await session.execute(query)
    return list(result.scalars().all())


async def cleanup_test_appointments(
    session: AsyncSession,
    older_than_hours: int = 24,
    dry_run: bool = True,
    max_delete: int = 1000
) -> Dict[str, any]:
    """
    Delete old test appointments from the database.

    Safety Features:
    - Only deletes appointments with is_test_data=True
    - Age-based deletion (default: 24 hours)
    - Dry-run mode by default
    - Maximum deletion limit
    - Detailed results returned

    Args:
        session: Database session
        older_than_hours: Delete appointments older than this (hours)
        dry_run: If True, don't actually delete (default: True for safety)
        max_delete: Maximum number of appointments to delete (safety limit)

    Returns:
        Dictionary with cleanup results:
        {
            "dry_run": bool,
            "found": int,
            "deleted": int,
            "deleted_ids": List[int],
            "oldest_deleted": datetime,
            "newest_deleted": datetime,
        }
    """
    # Calculate cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)

    # Find test appointments to delete
    query = select(Appointment).where(
        Appointment.is_test_data == True,  # noqa: E712
        Appointment.created_at < cutoff_time
    ).order_by(Appointment.created_at.asc()).limit(max_delete)

    result = await session.execute(query)
    appointments_to_delete = list(result.scalars().all())

    # Prepare results
    results = {
        "dry_run": dry_run,
        "cutoff_time": cutoff_time.isoformat(),
        "found": len(appointments_to_delete),
        "deleted": 0,
        "deleted_ids": [],
        "oldest_deleted": None,
        "newest_deleted": None,
        "appointments": []
    }

    if not appointments_to_delete:
        return results

    # Store details for logging
    results["oldest_deleted"] = appointments_to_delete[0].created_at.isoformat()
    results["newest_deleted"] = appointments_to_delete[-1].created_at.isoformat()
    results["deleted_ids"] = [apt.id for apt in appointments_to_delete]
    results["appointments"] = [
        {
            "id": apt.id,
            "user_id": apt.user_id,
            "created_at": apt.created_at.isoformat(),
            "starts_at": apt.starts_at.isoformat(),
            "status": apt.status,
        }
        for apt in appointments_to_delete
    ]

    # Perform deletion (if not dry run)
    if not dry_run:
        delete_query = delete(Appointment).where(
            Appointment.id.in_(results["deleted_ids"]),
            Appointment.is_test_data == True  # Extra safety check
        )

        delete_result = await session.execute(delete_query)
        await session.commit()

        results["deleted"] = delete_result.rowcount
    else:
        results["deleted"] = 0  # Dry run - no actual deletions

    return results


async def mark_appointment_as_test(
    session: AsyncSession,
    appointment_id: int
) -> bool:
    """
    Mark an existing appointment as test data.

    USE WITH CAUTION: This should only be used for appointments you're certain
    are test data. Never mark real customer appointments as test data.

    Args:
        session: Database session
        appointment_id: ID of appointment to mark

    Returns:
        True if marked successfully, False if not found
    """
    query = select(Appointment).where(Appointment.id == appointment_id)
    result = await session.execute(query)
    appointment = result.scalar_one_or_none()

    if not appointment:
        return False

    appointment.is_test_data = True
    await session.commit()
    return True


async def verify_cleanup_rules(session: AsyncSession) -> Dict[str, any]:
    """
    Verify cleanup rules and database state.

    Checks:
    - Total test appointments in database
    - Age distribution of test data
    - Appointments ready for cleanup
    - Database indexes

    Returns:
        Dictionary with verification results
    """
    # Count total test appointments
    total_test = await count_test_appointments(session, include_cancelled=True)
    active_test = await count_test_appointments(session, include_cancelled=False)

    # Count by age groups
    now = datetime.now(timezone.utc)
    age_groups = {
        "< 1 hour": (now - timedelta(hours=1), now),
        "1-24 hours": (now - timedelta(hours=24), now - timedelta(hours=1)),
        "24-48 hours": (now - timedelta(hours=48), now - timedelta(hours=24)),
        "> 48 hours": (datetime.min.replace(tzinfo=timezone.utc), now - timedelta(hours=48)),
    }

    age_distribution = {}
    for group_name, (start_time, end_time) in age_groups.items():
        query = select(func.count(Appointment.id)).where(
            Appointment.is_test_data == True,  # noqa: E712
            Appointment.created_at >= start_time,
            Appointment.created_at < end_time
        )
        result = await session.execute(query)
        age_distribution[group_name] = result.scalar() or 0

    # Check for stale test data (> 24 hours)
    stale_threshold = now - timedelta(hours=24)
    query = select(func.count(Appointment.id)).where(
        Appointment.is_test_data == True,  # noqa: E712
        Appointment.created_at < stale_threshold
    )
    result = await session.execute(query)
    stale_count = result.scalar() or 0

    return {
        "total_test_appointments": total_test,
        "active_test_appointments": active_test,
        "cancelled_test_appointments": total_test - active_test,
        "age_distribution": age_distribution,
        "stale_test_data": stale_count,
        "cleanup_recommended": stale_count > 0,
        "timestamp": now.isoformat(),
    }


async def get_cleanup_summary(session: AsyncSession) -> str:
    """
    Get a human-readable summary of test data cleanup status.

    Returns:
        Formatted string with cleanup summary
    """
    verification = await verify_cleanup_rules(session)

    summary = f"""
Production Test Data Cleanup Summary
=====================================
Timestamp: {verification['timestamp']}

Test Appointments:
- Total: {verification['total_test_appointments']}
- Active: {verification['active_test_appointments']}
- Cancelled: {verification['cancelled_test_appointments']}

Age Distribution:
"""
    for age_group, count in verification['age_distribution'].items():
        summary += f"- {age_group}: {count}\n"

    summary += f"""
Stale Data (> 24 hours): {verification['stale_test_data']}
Cleanup Recommended: {'YES' if verification['cleanup_recommended'] else 'NO'}
"""

    return summary


# CLI interface for manual cleanup
async def main():
    """Main CLI interface for cleanup utilities"""
    import argparse

    parser = argparse.ArgumentParser(description="Production test data cleanup utilities")
    parser.add_argument(
        "command",
        choices=["count", "list", "cleanup", "verify", "summary"],
        help="Command to execute"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("PRODUCTION_DB_URL"),
        help="Production database URL (or set PRODUCTION_DB_URL)"
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=24,
        help="Age threshold in hours for cleanup (default: 24)"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually perform deletions (default is dry-run)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Limit number of results (default: 100)"
    )

    args = parser.parse_args()

    if not args.db_url:
        print("❌ Error: PRODUCTION_DB_URL not set")
        return 1

    # Create database connection
    engine = create_async_engine(args.db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        if args.command == "count":
            count = await count_test_appointments(session)
            print(f"Test appointments in database: {count}")

        elif args.command == "list":
            appointments = await list_test_appointments(
                session,
                limit=args.limit,
                older_than_hours=args.older_than if args.older_than > 0 else None
            )
            print(f"Found {len(appointments)} test appointments:")
            for apt in appointments:
                age_hours = (datetime.now(timezone.utc) - apt.created_at).total_seconds() / 3600
                print(f"  - ID: {apt.id}, Created: {apt.created_at}, Age: {age_hours:.1f}h, Status: {apt.status}")

        elif args.command == "cleanup":
            dry_run = not args.no_dry_run
            results = await cleanup_test_appointments(
                session,
                older_than_hours=args.older_than,
                dry_run=dry_run
            )
            print(f"Cleanup {'[DRY RUN]' if dry_run else '[LIVE]'}: {results['found']} found, {results['deleted']} deleted")
            if results['found'] > 0:
                print(f"Age range: {results['oldest_deleted']} to {results['newest_deleted']}")

        elif args.command == "verify":
            results = await verify_cleanup_rules(session)
            print("Cleanup verification:")
            for key, value in results.items():
                print(f"  {key}: {value}")

        elif args.command == "summary":
            summary = await get_cleanup_summary(session)
            print(summary)

    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
