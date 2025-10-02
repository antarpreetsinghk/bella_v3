#!/usr/bin/env python3
"""
Create Production CloudWatch Dashboard for Bella V3 monitoring
"""

import json
import sys
import os
from pathlib import Path

# Set production environment
os.environ['APP_ENV'] = 'production'

# Add app to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from monitoring.cloudwatch_config import cloudwatch_monitor

def create_production_dashboard():
    """Create the Bella V3 production monitoring dashboard"""

    dashboard_body = {
        "widgets": [
            # API Package Metrics
            {
                "type": "metric",
                "x": 0, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/API", "RequestCount", "Package", "api", "Environment", "production"],
                        [".", "ResponseTime", ".", ".", ".", "."],
                        [".", "ErrorRate", ".", ".", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "API Package - Core Metrics",
                    "period": 300,
                    "stat": "Average",
                    "yAxis": {
                        "left": {
                            "min": 0
                        }
                    }
                }
            },

            # Services Package Metrics
            {
                "type": "metric",
                "x": 12, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Services", "OpenAIAPILatency", "Package", "services", "Environment", "production"],
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
                        ["Bella/Database", "ConnectionPoolUsage", "Package", "db", "Environment", "production"],
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

            # Voice Package Metrics
            {
                "type": "metric",
                "x": 12, "y": 6, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Voice", "CallVolume", "Package", "voice", "Environment", "production"],
                        [".", "SpeechRecognitionAccuracy", ".", ".", ".", "."],
                        [".", "VoiceProcessingLatency", ".", ".", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "Voice Package - Twilio Integration",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # AI Package Metrics
            {
                "type": "metric",
                "x": 0, "y": 12, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/AI", "NameExtractionAccuracy", "Package", "ai", "Environment", "production"],
                        [".", "ArtifactFilteringEffectiveness", ".", ".", ".", "."],
                        [".", "LLMResponseTime", ".", ".", ".", "."]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "AI Package - Extraction & Processing",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # Admin Package Metrics
            {
                "type": "metric",
                "x": 12, "y": 12, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Admin", "DashboardLoadTime", "Package", "admin", "Environment", "production"],
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
                "x": 0, "y": 18, "width": 24, "height": 6,
                "properties": {
                    "metrics": [
                        ["Bella/Core", "SystemHealth", "Package", "core", "Environment", "production"],
                        ["Bella/API", "RequestCount", "Package", "api", "Environment", "production"],
                        ["Bella/Database", "ConnectionPoolUsage", "Package", "db", "Environment", "production"],
                        ["Bella/Voice", "CallVolume", "Package", "voice", "Environment", "production"]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "ca-central-1",
                    "title": "System Overview - All Packages",
                    "period": 300,
                    "stat": "Average"
                }
            },

            # Production Info Panel
            {
                "type": "text",
                "x": 0, "y": 24, "width": 24, "height": 3,
                "properties": {
                    "markdown": "# 🏭 Bella V3 Production Monitoring Dashboard\n\n**Environment**: 🚀 **PRODUCTION**  \n**Metrics Collection**: Every 60 seconds  \n**Retention**: 30 days for production  \n**Account**: Contact administrator for account details\n\n📊 **Active Packages**: API, Services, Database, Voice, AI, Admin, Core  \n🔄 **Real-time Updates**: Metrics refresh automatically  \n📈 **Custom Period**: 5-minute averages displayed  \n🚨 **Alerting**: Critical thresholds monitored"
                }
            }
        ]
    }

    dashboard_name = "Bella-V3-Package-Monitoring-production"

    try:
        response = cloudwatch_monitor.cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )

        print(f"✅ Successfully created PRODUCTION dashboard: {dashboard_name}")
        dashboard_url = f"https://ca-central-1.console.aws.amazon.com/cloudwatch/home?region=ca-central-1#dashboards:name={dashboard_name}"
        print(f"🔗 Production Dashboard URL: {dashboard_url}")

        return dashboard_name

    except Exception as e:
        print(f"❌ Failed to create production dashboard: {e}")
        return None

if __name__ == "__main__":
    dashboard_name = create_production_dashboard()
    if dashboard_name:
        print(f"\n🎉 PRODUCTION Dashboard creation completed!")
        print(f"📊 Dashboard Name: {dashboard_name}")
        print(f"🏭 Environment: PRODUCTION")
        print(f"⏰ Production metrics will start appearing immediately")
    else:
        print(f"\n💥 Production dashboard creation failed!")
        sys.exit(1)