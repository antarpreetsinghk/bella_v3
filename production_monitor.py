#!/usr/bin/env python3
"""
Production Monitoring Script for Bella V3
=========================================

This script provides continuous monitoring of the voice-to-database flow in production.
It runs lightweight health checks and can be used for:
- Cron job monitoring
- CI/CD pipeline validation
- Production health dashboards
- Alert systems

Usage:
    python production_monitor.py --url https://your-domain.com
    python production_monitor.py --url https://your-domain.com --alert-webhook https://hooks.slack.com/...
    python production_monitor.py --url https://your-domain.com --continuous --interval 300
"""

import asyncio
import argparse
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProductionMonitor:
    """Production monitoring for voice-to-database flow"""

    def __init__(self, base_url: str, alert_webhook: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.alert_webhook = alert_webhook
        self.session = httpx.AsyncClient(timeout=10.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()

    async def check_health_endpoint(self) -> Dict[str, any]:
        """Check basic health endpoint"""
        try:
            response = await self.session.get(f"{self.base_url}/healthz")
            return {
                "endpoint": "health",
                "status": "ok" if response.status_code == 200 else "error",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "endpoint": "health",
                "status": "error",
                "error": str(e)
            }

    async def check_voice_endpoint(self) -> Dict[str, any]:
        """Check Twilio voice endpoint with minimal request"""
        try:
            data = {"CallSid": "HEALTH_CHECK"}
            response = await self.session.post(f"{self.base_url}/twilio/voice", data=data)

            # Should return TwiML even for health check
            is_twiml = "<?xml" in response.text and "Response" in response.text

            return {
                "endpoint": "voice",
                "status": "ok" if response.status_code == 200 and is_twiml else "error",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code,
                "is_twiml": is_twiml
            }
        except Exception as e:
            return {
                "endpoint": "voice",
                "status": "error",
                "error": str(e)
            }

    async def test_simple_voice_flow(self) -> Dict[str, any]:
        """Test a simple voice interaction flow"""
        try:
            # Step 1: Initialize call
            init_data = {"CallSid": "MONITOR_TEST_001"}
            init_response = await self.session.post(f"{self.base_url}/twilio/voice", data=init_data)

            if init_response.status_code != 200:
                return {
                    "endpoint": "voice_flow",
                    "status": "error",
                    "error": f"Init failed: {init_response.status_code}"
                }

            # Step 2: Test speech processing
            speech_data = {
                "CallSid": "MONITOR_TEST_001",
                "From": "+15551234567",
                "SpeechResult": "My name is Test User"
            }
            speech_response = await self.session.post(f"{self.base_url}/twilio/voice/collect", data=speech_data)

            # Should return TwiML asking for next step
            is_valid_flow = (speech_response.status_code == 200 and
                           "<?xml" in speech_response.text and
                           ("phone" in speech_response.text.lower() or "number" in speech_response.text.lower()))

            return {
                "endpoint": "voice_flow",
                "status": "ok" if is_valid_flow else "warning",
                "response_time": speech_response.elapsed.total_seconds(),
                "flow_working": is_valid_flow
            }

        except Exception as e:
            return {
                "endpoint": "voice_flow",
                "status": "error",
                "error": str(e)
            }

    async def run_health_check(self) -> Dict[str, any]:
        """Run comprehensive health check"""
        start_time = time.time()

        logger.info(f"🔍 Running health check on {self.base_url}")

        # Run all checks
        checks = await asyncio.gather(
            self.check_health_endpoint(),
            self.check_voice_endpoint(),
            self.test_simple_voice_flow(),
            return_exceptions=True
        )

        # Process results
        results = []
        for check in checks:
            if isinstance(check, Exception):
                results.append({
                    "endpoint": "unknown",
                    "status": "error",
                    "error": str(check)
                })
            else:
                results.append(check)

        # Calculate overall status
        statuses = [r["status"] for r in results]
        overall_status = "ok"
        if "error" in statuses:
            overall_status = "error"
        elif "warning" in statuses:
            overall_status = "warning"

        health_report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "overall_status": overall_status,
            "total_time": time.time() - start_time,
            "checks": results
        }

        # Log summary
        status_emoji = {"ok": "✅", "warning": "⚠️", "error": "❌"}[overall_status]
        logger.info(f"{status_emoji} Health check complete: {overall_status} ({health_report['total_time']:.2f}s)")

        # Alert if needed
        if overall_status in ["error", "warning"] and self.alert_webhook:
            await self.send_alert(health_report)

        return health_report

    async def send_alert(self, health_report: Dict[str, any]):
        """Send alert webhook for issues"""
        try:
            alert_data = {
                "text": f"🚨 Bella V3 Health Alert - {health_report['overall_status'].upper()}",
                "attachments": [
                    {
                        "color": "danger" if health_report['overall_status'] == "error" else "warning",
                        "fields": [
                            {
                                "title": "Environment",
                                "value": health_report['base_url'],
                                "short": True
                            },
                            {
                                "title": "Status",
                                "value": health_report['overall_status'],
                                "short": True
                            },
                            {
                                "title": "Issues",
                                "value": "\n".join([
                                    f"• {check['endpoint']}: {check.get('error', check['status'])}"
                                    for check in health_report['checks']
                                    if check['status'] != 'ok'
                                ]),
                                "short": False
                            }
                        ]
                    }
                ]
            }

            await self.session.post(self.alert_webhook, json=alert_data)
            logger.info("📬 Alert sent successfully")

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    async def continuous_monitoring(self, interval: int = 300):
        """Run continuous monitoring with specified interval (seconds)"""
        logger.info(f"🔄 Starting continuous monitoring (interval: {interval}s)")

        while True:
            try:
                health_report = await self.run_health_check()

                # Save report
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"health_check_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump(health_report, f, indent=2)

                logger.info(f"💾 Report saved: {filename}")

            except Exception as e:
                logger.error(f"Monitoring error: {e}")

            logger.info(f"😴 Waiting {interval}s until next check...")
            await asyncio.sleep(interval)


async def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description='Production monitoring for Bella V3')
    parser.add_argument('--url', required=True, help='Base URL to monitor')
    parser.add_argument('--alert-webhook', help='Webhook URL for alerts (e.g., Slack)')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=300, help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--save-report', action='store_true', help='Save health report to file')

    args = parser.parse_args()

    async with ProductionMonitor(args.url, args.alert_webhook) as monitor:

        if args.continuous:
            await monitor.continuous_monitoring(args.interval)
        else:
            # Single health check
            health_report = await monitor.run_health_check()

            # Print report
            print(json.dumps(health_report, indent=2))

            # Save if requested
            if args.save_report:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"health_check_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump(health_report, f, indent=2)
                print(f"\n💾 Report saved to: {filename}")

            # Exit with error code if issues found
            if health_report['overall_status'] == 'error':
                exit(1)
            elif health_report['overall_status'] == 'warning':
                exit(2)


if __name__ == "__main__":
    asyncio.run(main())