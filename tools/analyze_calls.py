#!/usr/bin/env python3
"""
Call Analytics Tool for Bella Voice Assistant
Analyzes call patterns, conversion rates, and provides insights
"""

import asyncio
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import sqlite3
from collections import defaultdict

class CallAnalyzer:
    def __init__(self, db_path: str = "data/bella.db"):
        self.db_path = db_path
        self.logs_dir = Path("logs/calls")

    async def analyze_daily_calls(self, date: str = None) -> Dict[str, Any]:
        """Analyze call patterns for a specific date"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        print(f"📊 Analyzing calls for {date}")

        # Read call logs
        call_data = self._read_call_logs(date)

        # Read database appointments
        db_bookings = self._read_db_appointments(date)

        # Calculate metrics
        metrics = self._calculate_metrics(call_data, db_bookings)

        return {
            "date": date,
            "summary": metrics,
            "call_details": call_data,
            "recommendations": self._generate_recommendations(metrics)
        }

    def _read_call_logs(self, date: str) -> Dict[str, Any]:
        """Read and parse call logs from JSONL files"""
        log_file = self.logs_dir / f"calls_{date}.jsonl"

        calls = {}
        if not log_file.exists():
            print(f"⚠️  No call logs found for {date}")
            return calls

        with open(log_file, "r") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    call_sid = event.get('call_sid', 'unknown')

                    if call_sid not in calls:
                        calls[call_sid] = {
                            "events": [],
                            "start_time": None,
                            "end_time": None,
                            "success": False,
                            "errors": [],
                            "steps_completed": [],
                            "total_duration": 0
                        }

                    calls[call_sid]["events"].append(event)

                    # Track specific events
                    if event['event_type'] == 'call_started':
                        calls[call_sid]["start_time"] = event['timestamp']
                    elif 'error' in event['event_type']:
                        calls[call_sid]["errors"].append(event)
                    elif event['event_type'] == 'appointment_booked':
                        calls[call_sid]["success"] = True
                        calls[call_sid]["end_time"] = event['timestamp']
                    elif '_complete' in event['event_type']:
                        step = event['event_type'].replace('_complete', '')
                        calls[call_sid]["steps_completed"].append(step)

                except json.JSONDecodeError:
                    continue

        return calls

    def _read_db_appointments(self, date: str) -> List[Dict]:
        """Read appointments from database for the date"""
        if not Path(self.db_path).exists():
            print(f"⚠️  Database not found: {self.db_path}")
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Query appointments for the date
            query = """
            SELECT
                a.id,
                a.starts_at,
                a.duration_min,
                a.status,
                a.created_at,
                u.full_name,
                u.mobile
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE DATE(a.created_at) = ?
            ORDER BY a.created_at
            """

            cursor = conn.execute(query, (date,))
            appointments = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return appointments

        except Exception as e:
            print(f"❌ Database error: {e}")
            return []

    def _calculate_metrics(self, calls: Dict, appointments: List) -> Dict[str, Any]:
        """Calculate key performance metrics"""
        total_calls = len(calls)
        successful_bookings = len(appointments)

        # Call flow analysis
        drop_off_points = defaultdict(int)
        avg_call_duration = 0
        error_count = 0

        for call_sid, call_data in calls.items():
            # Count drop-off points
            last_step = "start"
            for step in call_data["steps_completed"]:
                last_step = step

            if not call_data["success"]:
                drop_off_points[last_step] += 1

            # Count errors
            error_count += len(call_data["errors"])

            # Calculate duration if we have start/end times
            if call_data["start_time"] and call_data["end_time"]:
                start = datetime.fromisoformat(call_data["start_time"])
                end = datetime.fromisoformat(call_data["end_time"])
                duration = (end - start).total_seconds()
                call_data["total_duration"] = duration

        # Calculate averages
        successful_calls = [c for c in calls.values() if c["success"]]
        avg_call_duration = sum(c["total_duration"] for c in successful_calls) / len(successful_calls) if successful_calls else 0

        conversion_rate = (successful_bookings / total_calls * 100) if total_calls > 0 else 0

        return {
            "total_calls": total_calls,
            "successful_bookings": successful_bookings,
            "conversion_rate": round(conversion_rate, 1),
            "avg_call_duration": round(avg_call_duration, 1),
            "error_count": error_count,
            "drop_off_points": dict(drop_off_points),
            "appointments_by_hour": self._appointments_by_hour(appointments)
        }

    def _appointments_by_hour(self, appointments: List) -> Dict[int, int]:
        """Analyze appointment distribution by hour"""
        by_hour = defaultdict(int)

        for apt in appointments:
            try:
                # Parse the timestamp
                created_dt = datetime.fromisoformat(apt['created_at'].replace('Z', '+00:00'))
                hour = created_dt.hour
                by_hour[hour] += 1
            except:
                continue

        return dict(by_hour)

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []

        # Conversion rate recommendations
        if metrics["conversion_rate"] < 50:
            recommendations.append("🔧 Low conversion rate - consider improving call flow or speech recognition")

        # Drop-off analysis
        drop_offs = metrics.get("drop_off_points", {})
        max_drop_off = max(drop_offs.values()) if drop_offs else 0

        if max_drop_off > metrics["total_calls"] * 0.3:  # More than 30% dropping at one point
            worst_step = max(drop_offs, key=drop_offs.get)
            recommendations.append(f"📞 High drop-off at '{worst_step}' step - review prompts and flow")

        # Error rate
        if metrics["error_count"] > metrics["total_calls"] * 0.1:  # More than 10% error rate
            recommendations.append("⚠️  High error rate - check speech recognition and validation logic")

        # Call duration
        if metrics["avg_call_duration"] > 180:  # More than 3 minutes
            recommendations.append("⏱️  Long average call time - consider streamlining the booking process")

        # Peak hours
        by_hour = metrics.get("appointments_by_hour", {})
        if by_hour:
            peak_hour = max(by_hour, key=by_hour.get)
            recommendations.append(f"📈 Peak booking hour: {peak_hour}:00 - ensure adequate capacity")

        return recommendations

    async def weekly_summary(self, days: int = 7) -> Dict[str, Any]:
        """Generate a weekly summary report"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days-1)

        weekly_data = {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "daily_metrics": [],
            "trends": {},
            "total_summary": {
                "total_calls": 0,
                "total_bookings": 0,
                "avg_conversion_rate": 0
            }
        }

        daily_conversions = []

        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            daily_analysis = await self.analyze_daily_calls(date)

            weekly_data["daily_metrics"].append(daily_analysis)

            # Accumulate totals
            summary = daily_analysis["summary"]
            weekly_data["total_summary"]["total_calls"] += summary["total_calls"]
            weekly_data["total_summary"]["total_bookings"] += summary["successful_bookings"]

            if summary["total_calls"] > 0:
                daily_conversions.append(summary["conversion_rate"])

        # Calculate averages
        if daily_conversions:
            weekly_data["total_summary"]["avg_conversion_rate"] = round(
                sum(daily_conversions) / len(daily_conversions), 1
            )

        return weekly_data

    def print_daily_report(self, analysis: Dict):
        """Print a formatted daily report"""
        summary = analysis["summary"]

        print(f"\n📅 Daily Report - {analysis['date']}")
        print("=" * 50)
        print(f"📞 Total Calls: {summary['total_calls']}")
        print(f"✅ Successful Bookings: {summary['successful_bookings']}")
        print(f"📊 Conversion Rate: {summary['conversion_rate']}%")
        print(f"⏱️  Avg Call Duration: {summary['avg_call_duration']}s")
        print(f"❌ Errors: {summary['error_count']}")

        # Drop-off analysis
        if summary.get("drop_off_points"):
            print(f"\n📉 Drop-off Points:")
            for step, count in summary["drop_off_points"].items():
                print(f"  • {step}: {count} calls")

        # Peak hours
        if summary.get("appointments_by_hour"):
            print(f"\n📈 Bookings by Hour:")
            for hour, count in sorted(summary["appointments_by_hour"].items()):
                print(f"  • {hour:02d}:00 - {count} bookings")

        # Recommendations
        if analysis.get("recommendations"):
            print(f"\n💡 Recommendations:")
            for rec in analysis["recommendations"]:
                print(f"  {rec}")

        print("\n" + "=" * 50)

async def main():
    parser = argparse.ArgumentParser(description="Analyze voice assistant call data")
    parser.add_argument("--date", help="Date to analyze (YYYY-MM-DD), defaults to today")
    parser.add_argument("--weekly", action="store_true", help="Generate weekly summary")
    parser.add_argument("--days", type=int, default=7, help="Number of days for weekly summary")
    parser.add_argument("--db", default="data/bella.db", help="Path to SQLite database")

    args = parser.parse_args()

    analyzer = CallAnalyzer(db_path=args.db)

    if args.weekly:
        print("📊 Generating Weekly Summary...")
        weekly_data = await analyzer.weekly_summary(args.days)

        print(f"\n📈 Weekly Summary - {weekly_data['period']}")
        print("=" * 60)
        print(f"📞 Total Calls: {weekly_data['total_summary']['total_calls']}")
        print(f"✅ Total Bookings: {weekly_data['total_summary']['total_bookings']}")
        print(f"📊 Avg Conversion Rate: {weekly_data['total_summary']['avg_conversion_rate']}%")

        print(f"\n📅 Daily Breakdown:")
        for daily in weekly_data["daily_metrics"]:
            summary = daily["summary"]
            print(f"  {daily['date']}: {summary['total_calls']} calls, {summary['successful_bookings']} bookings ({summary['conversion_rate']}%)")

    else:
        # Daily analysis
        analysis = await analyzer.analyze_daily_calls(args.date)
        analyzer.print_daily_report(analysis)

if __name__ == "__main__":
    asyncio.run(main())