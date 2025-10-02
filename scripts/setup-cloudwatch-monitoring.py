#!/usr/bin/env python3
"""
CloudWatch Monitoring Setup Script for Bella V3
Automatically creates dashboards, alarms, and log groups for package-level monitoring.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

# Add app to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from monitoring.cloudwatch_config import cloudwatch_monitor, package_metrics_collector
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)

async def setup_log_groups():
    """Setup CloudWatch log groups for all packages"""
    logger.info("🗂️  Setting up CloudWatch log groups...")

    try:
        await cloudwatch_monitor.setup_log_groups()
        logger.info("✅ Log groups created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to setup log groups: {e}")
        return False

async def create_alarms():
    """Create all CloudWatch alarms"""
    logger.info("🚨 Creating CloudWatch alarms...")

    try:
        await cloudwatch_monitor.create_alarms()
        logger.info("✅ CloudWatch alarms created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create alarms: {e}")
        return False

async def create_dashboard():
    """Create CloudWatch dashboard"""
    logger.info("📊 Creating CloudWatch dashboard...")

    try:
        dashboard_name = await cloudwatch_monitor.create_dashboard()
        if dashboard_name:
            logger.info(f"✅ Dashboard created successfully: {dashboard_name}")
            dashboard_url = f"https://ca-central-1.console.aws.amazon.com/cloudwatch/home?region=ca-central-1#dashboards:name={dashboard_name}"
            logger.info(f"🔗 Dashboard URL: {dashboard_url}")
            return True
        else:
            logger.error("❌ Failed to create dashboard")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to create dashboard: {e}")
        return False

async def test_metrics_collection():
    """Test metrics collection and publishing"""
    logger.info("🧪 Testing metrics collection...")

    try:
        # Collect and publish test metrics
        await package_metrics_collector.collect_all_package_metrics()
        logger.info("✅ Metrics collection test successful")

        # Get package metrics summary
        summary = await cloudwatch_monitor.get_package_metrics_summary()
        logger.info(f"📈 Package metrics summary: {json.dumps(summary, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"❌ Metrics collection test failed: {e}")
        return False

async def verify_setup():
    """Verify that all monitoring components are working"""
    logger.info("🔍 Verifying monitoring setup...")

    verification_results = {
        'log_groups': False,
        'alarms': False,
        'dashboard': False,
        'metrics': False
    }

    try:
        # Check if log groups exist
        log_groups = cloudwatch_monitor.logs_client.describe_log_groups(
            logGroupNamePrefix='/bella/'
        )
        verification_results['log_groups'] = len(log_groups['logGroups']) > 0

        # Check if alarms exist
        alarms = cloudwatch_monitor.cloudwatch.describe_alarms(
            AlarmNamePrefix='Bella-'
        )
        verification_results['alarms'] = len(alarms['MetricAlarms']) > 0

        # Check if dashboard exists
        dashboards = cloudwatch_monitor.cloudwatch.list_dashboards(
            DashboardNamePrefix='Bella-V3-Package-Monitoring'
        )
        verification_results['dashboard'] = len(dashboards['DashboardEntries']) > 0

        # Test metrics publishing
        await cloudwatch_monitor.send_metric_to_cloudwatch(
            'api', 'SetupVerification', 1.0, 'Count'
        )
        verification_results['metrics'] = True

        logger.info(f"✅ Verification results: {json.dumps(verification_results, indent=2)}")
        return all(verification_results.values())

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

async def cleanup_monitoring():
    """Cleanup monitoring resources (for development/testing)"""
    logger.info("🧹 Cleaning up monitoring resources...")

    try:
        # Delete alarms
        alarms = cloudwatch_monitor.cloudwatch.describe_alarms(
            AlarmNamePrefix='Bella-'
        )

        for alarm in alarms['MetricAlarms']:
            cloudwatch_monitor.cloudwatch.delete_alarms(
                AlarmNames=[alarm['AlarmName']]
            )
            logger.info(f"🗑️  Deleted alarm: {alarm['AlarmName']}")

        # Delete dashboards
        dashboards = cloudwatch_monitor.cloudwatch.list_dashboards(
            DashboardNamePrefix='Bella-V3-Package-Monitoring'
        )

        for dashboard in dashboards['DashboardEntries']:
            cloudwatch_monitor.cloudwatch.delete_dashboards(
                DashboardNames=[dashboard['DashboardName']]
            )
            logger.info(f"🗑️  Deleted dashboard: {dashboard['DashboardName']}")

        # Note: We don't delete log groups as they may contain important data
        logger.info("⚠️  Log groups preserved to retain historical data")

        logger.info("✅ Cleanup completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return False

async def export_dashboard_config():
    """Export dashboard configuration for version control"""
    logger.info("💾 Exporting dashboard configuration...")

    try:
        # Get existing dashboards
        dashboards = cloudwatch_monitor.cloudwatch.list_dashboards(
            DashboardNamePrefix='Bella-V3-Package-Monitoring'
        )

        if not dashboards['DashboardEntries']:
            logger.warning("⚠️  No dashboards found to export")
            return False

        # Export each dashboard
        for dashboard_entry in dashboards['DashboardEntries']:
            dashboard_name = dashboard_entry['DashboardName']

            response = cloudwatch_monitor.cloudwatch.get_dashboard(
                DashboardName=dashboard_name
            )

            # Save dashboard config
            config_path = f"monitoring/dashboards/{dashboard_name}.json"
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w') as f:
                json.dump(json.loads(response['DashboardBody']), f, indent=2)

            logger.info(f"💾 Exported dashboard config: {config_path}")

        return True

    except Exception as e:
        logger.error(f"❌ Dashboard export failed: {e}")
        return False

async def main():
    """Main setup orchestration"""
    parser = argparse.ArgumentParser(description='Bella V3 CloudWatch Monitoring Setup')
    parser.add_argument('--environment', '-e', default='development',
                       choices=['development', 'staging', 'production'],
                       help='Target environment')
    parser.add_argument('--action', '-a', default='setup',
                       choices=['setup', 'verify', 'cleanup', 'export', 'test'],
                       help='Action to perform')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.verbose)

    logger.info(f"🚀 Starting CloudWatch monitoring {args.action} for {args.environment}")

    success = False

    if args.action == 'setup':
        logger.info("📋 Performing full monitoring setup...")

        steps = [
            ("Log Groups", setup_log_groups),
            ("Alarms", create_alarms),
            ("Dashboard", create_dashboard),
            ("Metrics Test", test_metrics_collection)
        ]

        results = []
        for step_name, step_func in steps:
            logger.info(f"🔄 Executing step: {step_name}")
            result = await step_func()
            results.append(result)

            if result:
                logger.info(f"✅ {step_name} completed successfully")
            else:
                logger.error(f"❌ {step_name} failed")

        success = all(results)

        if success:
            logger.info("🎉 Full monitoring setup completed successfully!")
            logger.info("📊 You can now view metrics in the AWS CloudWatch console")
        else:
            logger.error("💥 Setup encountered errors. Check logs above.")

    elif args.action == 'verify':
        success = await verify_setup()
        if success:
            logger.info("✅ All monitoring components verified successfully")
        else:
            logger.error("❌ Monitoring verification failed")

    elif args.action == 'cleanup':
        if args.environment == 'production':
            logger.error("❌ Cleanup not allowed in production environment")
            sys.exit(1)

        confirm = input("⚠️  This will delete monitoring resources. Continue? (y/N): ")
        if confirm.lower() == 'y':
            success = await cleanup_monitoring()
        else:
            logger.info("🚫 Cleanup cancelled")
            success = True

    elif args.action == 'export':
        success = await export_dashboard_config()

    elif args.action == 'test':
        success = await test_metrics_collection()

    if success:
        logger.info("🎊 Operation completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Operation failed!")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())