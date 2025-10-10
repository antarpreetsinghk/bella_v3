#!/usr/bin/env python3
"""
Production Test Data Monitoring

Real-time monitoring dashboard for test data in production databases.
Provides insights into test data accumulation, age distribution, and cleanup needs.

Features:
- Live dashboard with auto-refresh
- Test data statistics and trends
- Age distribution visualization
- Cleanup recommendations
- Stale data alerts
- Export to JSON for automation

Usage:
    # Live dashboard (auto-refresh every 30 seconds)
    python monitor_test_data.py dashboard --db-url=$PRODUCTION_DB_URL

    # One-time snapshot
    python monitor_test_data.py snapshot --db-url=$PRODUCTION_DB_URL

    # Export to JSON
    python monitor_test_data.py export --db-url=$PRODUCTION_DB_URL --output=report.json

    # Continuous monitoring with alerts
    python monitor_test_data.py watch --db-url=$PRODUCTION_DB_URL --alert-threshold=100
"""

import asyncio
import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.db.models.appointment import Appointment
from app.db.models.user import User


class TestDataMonitor:
    """Monitor for production test data"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = None
        self.session_factory = None

    async def connect(self):
        """Establish database connection"""
        self.engine = create_async_engine(
            self.db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def disconnect(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about test data.

        Returns:
            Dictionary with all monitoring metrics
        """
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)

            # Total counts
            total_test = await self._count_test_appointments(session, include_cancelled=True)
            active_test = await self._count_test_appointments(session, include_cancelled=False)
            cancelled_test = total_test - active_test

            # Age distribution
            age_groups = await self._get_age_distribution(session)

            # Stale data (> 24 hours)
            stale_count = await self._count_stale_data(session, hours=24)

            # Recent activity (last hour)
            recent_count = await self._count_recent_data(session, hours=1)

            # Oldest and newest test data
            oldest, newest = await self._get_time_range(session)

            # User statistics
            test_users_count = await self._count_test_users(session)

            # Storage metrics
            total_storage = await self._estimate_storage(session)

            # Trend data (last 24 hours by hour)
            trend_data = await self._get_hourly_trend(session, hours=24)

            return {
                "timestamp": now.isoformat(),
                "summary": {
                    "total_test_appointments": total_test,
                    "active_appointments": active_test,
                    "cancelled_appointments": cancelled_test,
                    "test_users": test_users_count,
                    "stale_data_count": stale_count,
                    "recent_activity": recent_count,
                },
                "age_distribution": age_groups,
                "time_range": {
                    "oldest": oldest.isoformat() if oldest else None,
                    "newest": newest.isoformat() if newest else None,
                },
                "storage": {
                    "estimated_bytes": total_storage,
                    "estimated_mb": round(total_storage / 1024 / 1024, 2),
                },
                "trends": trend_data,
                "alerts": self._generate_alerts(total_test, stale_count, recent_count),
                "recommendations": self._generate_recommendations(total_test, stale_count),
            }

    async def _count_test_appointments(
        self, session: AsyncSession, include_cancelled: bool = True
    ) -> int:
        """Count test appointments"""
        query = select(func.count(Appointment.id)).where(
            Appointment.is_test_data == True  # noqa: E712
        )
        if not include_cancelled:
            query = query.where(Appointment.status != "cancelled")

        result = await session.execute(query)
        return result.scalar() or 0

    async def _get_age_distribution(self, session: AsyncSession) -> Dict[str, int]:
        """Get age distribution of test data"""
        now = datetime.now(timezone.utc)
        age_groups = {
            "< 1 hour": (now - timedelta(hours=1), now),
            "1-6 hours": (now - timedelta(hours=6), now - timedelta(hours=1)),
            "6-12 hours": (now - timedelta(hours=12), now - timedelta(hours=6)),
            "12-24 hours": (now - timedelta(hours=24), now - timedelta(hours=12)),
            "24-48 hours": (now - timedelta(hours=48), now - timedelta(hours=24)),
            "48-72 hours": (now - timedelta(hours=72), now - timedelta(hours=48)),
            "> 72 hours": (datetime.min.replace(tzinfo=timezone.utc), now - timedelta(hours=72)),
        }

        distribution = {}
        for group_name, (start_time, end_time) in age_groups.items():
            query = select(func.count(Appointment.id)).where(
                Appointment.is_test_data == True,  # noqa: E712
                Appointment.created_at >= start_time,
                Appointment.created_at < end_time
            )
            result = await session.execute(query)
            distribution[group_name] = result.scalar() or 0

        return distribution

    async def _count_stale_data(self, session: AsyncSession, hours: int = 24) -> int:
        """Count stale test data"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = select(func.count(Appointment.id)).where(
            Appointment.is_test_data == True,  # noqa: E712
            Appointment.created_at < cutoff_time
        )
        result = await session.execute(query)
        return result.scalar() or 0

    async def _count_recent_data(self, session: AsyncSession, hours: int = 1) -> int:
        """Count recently created test data"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = select(func.count(Appointment.id)).where(
            Appointment.is_test_data == True,  # noqa: E712
            Appointment.created_at >= cutoff_time
        )
        result = await session.execute(query)
        return result.scalar() or 0

    async def _get_time_range(self, session: AsyncSession) -> tuple:
        """Get oldest and newest test data timestamps"""
        query = select(
            func.min(Appointment.created_at),
            func.max(Appointment.created_at)
        ).where(Appointment.is_test_data == True)  # noqa: E712

        result = await session.execute(query)
        oldest, newest = result.one()
        return oldest, newest

    async def _count_test_users(self, session: AsyncSession) -> int:
        """Count users with test appointments"""
        query = select(func.count(func.distinct(Appointment.user_id))).where(
            Appointment.is_test_data == True  # noqa: E712
        )
        result = await session.execute(query)
        return result.scalar() or 0

    async def _estimate_storage(self, session: AsyncSession) -> int:
        """Estimate storage used by test data (rough approximation)"""
        # Rough estimate: 500 bytes per appointment + 200 bytes per user
        appointment_count = await self._count_test_appointments(session)
        user_count = await self._count_test_users(session)

        return (appointment_count * 500) + (user_count * 200)

    async def _get_hourly_trend(self, session: AsyncSession, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly creation trend for last N hours"""
        trend_data = []
        now = datetime.now(timezone.utc)

        for i in range(hours):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)

            query = select(func.count(Appointment.id)).where(
                Appointment.is_test_data == True,  # noqa: E712
                Appointment.created_at >= hour_start,
                Appointment.created_at < hour_end
            )
            result = await session.execute(query)
            count = result.scalar() or 0

            trend_data.append({
                "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                "count": count,
                "hours_ago": i + 1,
            })

        return list(reversed(trend_data))

    def _generate_alerts(
        self, total: int, stale: int, recent: int
    ) -> List[Dict[str, str]]:
        """Generate alerts based on thresholds"""
        alerts = []

        if total > 1000:
            alerts.append({
                "level": "critical",
                "message": f"Very high test data count: {total} appointments",
                "action": "Run immediate cleanup to prevent performance impact"
            })
        elif total > 500:
            alerts.append({
                "level": "warning",
                "message": f"High test data count: {total} appointments",
                "action": "Schedule cleanup soon"
            })

        if stale > 100:
            alerts.append({
                "level": "warning",
                "message": f"Stale test data detected: {stale} appointments > 24 hours",
                "action": "Run cleanup for old test data"
            })
        elif stale > 0:
            alerts.append({
                "level": "info",
                "message": f"Some stale test data: {stale} appointments > 24 hours",
                "action": "Consider running cleanup"
            })

        if recent > 50:
            alerts.append({
                "level": "info",
                "message": f"High recent activity: {recent} appointments in last hour",
                "action": "Tests are running actively"
            })

        if total == 0:
            alerts.append({
                "level": "info",
                "message": "No test data in database",
                "action": "Database is clean"
            })

        return alerts

    def _generate_recommendations(self, total: int, stale: int) -> List[str]:
        """Generate recommendations based on current state"""
        recommendations = []

        if stale > 0:
            recommendations.append(
                f"Run cleanup for {stale} stale appointments: "
                "python cleanup.py cleanup --older-than=24 --no-dry-run"
            )

        if total > 100:
            recommendations.append(
                "Consider reducing test data retention period to keep database lean"
            )

        if total == 0:
            recommendations.append(
                "Database is clean. Good practice!"
            )

        if stale == 0 and total > 0:
            recommendations.append(
                "Test data is fresh. Cleanup is working well."
            )

        return recommendations


def format_dashboard(stats: Dict[str, Any]) -> str:
    """Format statistics as terminal dashboard"""
    output = []

    # Header
    output.append("=" * 80)
    output.append("  PRODUCTION TEST DATA MONITORING DASHBOARD".center(80))
    output.append("=" * 80)
    output.append(f"Timestamp: {stats['timestamp']}")
    output.append("")

    # Summary section
    output.append("📊 SUMMARY")
    output.append("-" * 80)
    summary = stats["summary"]
    output.append(f"  Total Test Appointments:     {summary['total_test_appointments']:>6}")
    output.append(f"  Active Appointments:         {summary['active_appointments']:>6}")
    output.append(f"  Cancelled Appointments:      {summary['cancelled_appointments']:>6}")
    output.append(f"  Test Users:                  {summary['test_users']:>6}")
    output.append(f"  Stale Data (> 24h):          {summary['stale_data_count']:>6}")
    output.append(f"  Recent Activity (< 1h):      {summary['recent_activity']:>6}")
    output.append("")

    # Age distribution
    output.append("⏰ AGE DISTRIBUTION")
    output.append("-" * 80)
    for age_group, count in stats["age_distribution"].items():
        bar = "█" * min(count, 50)
        output.append(f"  {age_group:<15} {count:>5} {bar}")
    output.append("")

    # Storage
    output.append("💾 STORAGE")
    output.append("-" * 80)
    output.append(f"  Estimated Size:              {stats['storage']['estimated_mb']} MB")
    output.append("")

    # Time range
    output.append("📅 TIME RANGE")
    output.append("-" * 80)
    if stats["time_range"]["oldest"]:
        output.append(f"  Oldest Test Data:            {stats['time_range']['oldest']}")
        output.append(f"  Newest Test Data:            {stats['time_range']['newest']}")
    else:
        output.append("  No test data in database")
    output.append("")

    # Alerts
    if stats["alerts"]:
        output.append("🚨 ALERTS")
        output.append("-" * 80)
        for alert in stats["alerts"]:
            level_icon = {
                "critical": "🔴",
                "warning": "🟡",
                "info": "🔵"
            }.get(alert["level"], "⚪")
            output.append(f"  {level_icon} [{alert['level'].upper()}] {alert['message']}")
            output.append(f"     Action: {alert['action']}")
        output.append("")

    # Recommendations
    if stats["recommendations"]:
        output.append("💡 RECOMMENDATIONS")
        output.append("-" * 80)
        for i, rec in enumerate(stats["recommendations"], 1):
            output.append(f"  {i}. {rec}")
        output.append("")

    output.append("=" * 80)

    return "\n".join(output)


async def dashboard_mode(db_url: str, refresh_interval: int = 30):
    """Live dashboard with auto-refresh"""
    monitor = TestDataMonitor(db_url)
    await monitor.connect()

    try:
        while True:
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')

            # Get and display statistics
            stats = await monitor.get_statistics()
            print(format_dashboard(stats))
            print(f"\n🔄 Auto-refresh in {refresh_interval} seconds... (Ctrl+C to exit)")

            # Wait for next refresh
            await asyncio.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped by user")
    finally:
        await monitor.disconnect()


async def snapshot_mode(db_url: str):
    """One-time snapshot"""
    monitor = TestDataMonitor(db_url)
    await monitor.connect()

    try:
        stats = await monitor.get_statistics()
        print(format_dashboard(stats))
    finally:
        await monitor.disconnect()


async def export_mode(db_url: str, output_file: str):
    """Export statistics to JSON file"""
    monitor = TestDataMonitor(db_url)
    await monitor.connect()

    try:
        stats = await monitor.get_statistics()

        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)

        print(f"✅ Statistics exported to {output_file}")
        print(f"Total test appointments: {stats['summary']['total_test_appointments']}")
        print(f"Stale data count: {stats['summary']['stale_data_count']}")

    finally:
        await monitor.disconnect()


async def watch_mode(db_url: str, alert_threshold: int = 100, check_interval: int = 60):
    """Continuous monitoring with alerts"""
    monitor = TestDataMonitor(db_url)
    await monitor.connect()

    try:
        print(f"👁️  Watching test data... (threshold: {alert_threshold}, interval: {check_interval}s)")
        print("Press Ctrl+C to stop\n")

        while True:
            stats = await monitor.get_statistics()
            total = stats["summary"]["total_test_appointments"]
            stale = stats["summary"]["stale_data_count"]

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if total > alert_threshold:
                print(f"🚨 [{timestamp}] ALERT: {total} test appointments (threshold: {alert_threshold})")
            elif stale > 0:
                print(f"⚠️  [{timestamp}] {total} test appointments, {stale} stale")
            else:
                print(f"✅ [{timestamp}] {total} test appointments, all fresh")

            await asyncio.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped by user")
    finally:
        await monitor.disconnect()


async def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Production test data monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live dashboard
  python monitor_test_data.py dashboard --db-url=$PRODUCTION_DB_URL

  # One-time snapshot
  python monitor_test_data.py snapshot --db-url=$PRODUCTION_DB_URL

  # Export to JSON
  python monitor_test_data.py export --db-url=$PRODUCTION_DB_URL --output=report.json

  # Watch mode with alerts
  python monitor_test_data.py watch --db-url=$PRODUCTION_DB_URL --alert-threshold=50
        """
    )

    parser.add_argument(
        "mode",
        choices=["dashboard", "snapshot", "export", "watch"],
        help="Monitoring mode"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("PRODUCTION_DB_URL"),
        help="Production database URL (or set PRODUCTION_DB_URL)"
    )
    parser.add_argument(
        "--refresh-interval",
        type=int,
        default=30,
        help="Dashboard refresh interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--output",
        default="test_data_report.json",
        help="Output file for export mode (default: test_data_report.json)"
    )
    parser.add_argument(
        "--alert-threshold",
        type=int,
        default=100,
        help="Alert threshold for watch mode (default: 100)"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=60,
        help="Check interval for watch mode in seconds (default: 60)"
    )

    args = parser.parse_args()

    if not args.db_url:
        print("❌ Error: PRODUCTION_DB_URL not set")
        return 1

    if args.mode == "dashboard":
        await dashboard_mode(args.db_url, args.refresh_interval)
    elif args.mode == "snapshot":
        await snapshot_mode(args.db_url)
    elif args.mode == "export":
        await export_mode(args.db_url, args.output)
    elif args.mode == "watch":
        await watch_mode(args.db_url, args.alert_threshold, args.check_interval)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
