#!/usr/bin/env python3
"""
Create CloudWatch Dashboard with widgets for Bella V3 monitoring
"""

import json
import sys
from pathlib import Path

# Add app to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from monitoring.cloudwatch_config import cloudwatch_monitor
from app.core.config import settings

def create_bella_dashboard():
    """Create the Bella V3 monitoring dashboard"""

    dashboard_body = {
        "widgets": [
            # API Package Metrics
            {
                "type": "metric",
                "x": 0, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/API", "RequestCount", "Package", "api", "Environment", "testing"],
                        [".", "ResponseTime", ".", ".", ".", "."],
                        [".", "ErrorRate", ".", ".", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "API Package - Core Metrics",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # Services Package Metrics
            {
                "type": "metric",
                "x": 12, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Services", "OpenAIAPILatency", "Package", "services", "Environment", "testing"],
                        [".", "ExtractionAccuracy", ".", ".", ".", "."],
                        [".", "CacheHitRate", ".", ".", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "Services Package - AI & External APIs",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # Database Package Metrics
            {
                "type": "metric",
                "x": 0, "y": 6, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Database", "ConnectionPoolUsage", "Package", "db", "Environment", "testing"],
                        [".", "QueryLatency", ".", ".", ".", "."],
                        [".", "TransactionCount", ".", ".", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "Database Package - Performance",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # Admin Package Metrics
            {
                "type": "metric",
                "x": 12, "y": 6, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Admin", "DashboardLoadTime", "Package", "admin", "Environment", "testing"],
                        [".", "UserSessionDuration", ".", ".", ".", "."],
                        [".", "SecurityEvents", ".", ".", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "Admin Package - Dashboard & Security",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # System Overview
            {
                "type": "metric",
                "x": 0, "y": 12, "width": 24, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Core", "SystemHealth", "Package", "core", "Environment", "testing"],
                        ["Bella/API", "RequestCount", "Package", "api", "Environment", "testing"],
                        ["Bella/Database", "ConnectionPoolUsage", "Package", "db", "Environment", "testing"]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "System Overview - All Packages",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # Text widget with info
            {
                "type": "text",
                "x": 0, "y": 18, "width": 24, "height": 3,
                "properties": {
                    "markdown": "# Bella V3 Package Monitoring Dashboard\n\n**Environment**: Testing/Development  \n**Metrics Collection**: Every 60 seconds  \n**Retention**: 7 days for development  \n\n📊 **Active Packages**: API, Services, Database, Admin, Core  \n🔄 **Real-time Updates**: Metrics refresh automatically  \n📈 **Custom Period**: 5-minute averages displayed"
                }
            }
        ]
    }

    dashboard_name = f"Bella-V3-Package-Monitoring-{settings.APP_ENV}"

    try:
        response = cloudwatch_monitor.cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )

        print(f"✅ Successfully created dashboard: {dashboard_name}")
        dashboard_url = f"https://ca-central-1.console.aws.amazon.com/cloudwatch/home?region=ca-central-1#dashboards:name={dashboard_name}"
        print(f"🔗 Dashboard URL: {dashboard_url}")

        return dashboard_name

    except Exception as e:
        print(f"❌ Failed to create dashboard: {e}")
        return None

if __name__ == "__main__":
    dashboard_name = create_bella_dashboard()
    if dashboard_name:
        print(f"\n🎉 Dashboard creation completed!")
        print(f"📊 Dashboard Name: {dashboard_name}")
        print(f"⏰ Metrics should start appearing within 5-10 minutes")
    else:
        print(f"\n💥 Dashboard creation failed!")
        sys.exit(1)