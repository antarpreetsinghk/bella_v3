#!/usr/bin/env python3
"""
Cost tracking and monitoring utilities for Bella V3.
Provides real-time cost tracking and optimization recommendations.
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class CostMetric:
    """Cost metric data structure"""
    service: str
    amount: Decimal
    unit: str
    timestamp: datetime
    resource_id: Optional[str] = None


@dataclass
class CostAlert:
    """Cost alert data structure"""
    service: str
    current_cost: Decimal
    threshold: Decimal
    period: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL


class AWSCostTracker:
    """Track AWS costs using Cost Explorer API"""

    def __init__(self):
        try:
            self.cost_explorer = boto3.client('ce')
            self.cloudwatch = boto3.client('cloudwatch')

            # Test if Cost Explorer is actually available
            test_end = datetime.now()
            test_start = test_end - timedelta(days=1)
            self.cost_explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': test_start.strftime('%Y-%m-%d'),
                    'End': test_end.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost']
            )
            self.aws_available = True
            logger.info("AWS Cost Explorer access verified")
        except Exception as e:
            logger.warning(f"AWS Cost Explorer not available: {e}")
            self.cost_explorer = None
            self.cloudwatch = None
            self.aws_available = False

    def get_monthly_costs(self, start_date: datetime = None) -> Dict[str, Decimal]:
        """Get current month costs by service"""
        if not self.aws_available:
            logger.info("AWS Cost Explorer not available, returning mock data")
            return {
                'Amazon Elastic Compute Cloud - Compute': Decimal('45.00'),
                'Amazon Relational Database Service': Decimal('20.00'),
                'Amazon ElastiCache': Decimal('15.00'),
                'Amazon Elastic Load Balancing': Decimal('25.00'),
                'Data Transfer': Decimal('5.00')
            }

        if start_date is None:
            start_date = datetime.now().replace(day=1)

        end_date = datetime.now()

        try:
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )

            costs = {}
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    amount = Decimal(group['Metrics']['BlendedCost']['Amount'])
                    costs[service] = amount

            return costs

        except Exception as e:
            logger.error(f"Failed to fetch AWS costs: {e}")
            return {}

    def get_daily_costs(self, days: int = 7) -> List[CostMetric]:
        """Get daily costs for the last N days"""
        if not self.aws_available:
            logger.info("AWS Cost Explorer not available, returning mock daily costs")
            costs = []
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                costs.append(CostMetric(
                    service='Total',
                    amount=Decimal(str(3.5 + (i * 0.2))),  # Mock varying daily costs
                    unit='USD',
                    timestamp=date
                ))
            return costs

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        try:
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost']
            )

            costs = []
            for result in response['ResultsByTime']:
                date = datetime.strptime(result['TimePeriod']['Start'], '%Y-%m-%d')
                amount = Decimal(result['Total']['BlendedCost']['Amount'])
                costs.append(CostMetric(
                    service='Total',
                    amount=amount,
                    unit='USD',
                    timestamp=date
                ))

            return costs

        except Exception as e:
            logger.error(f"Failed to fetch daily costs: {e}")
            return []

    def get_service_costs(self, service_name: str, days: int = 30) -> List[CostMetric]:
        """Get costs for a specific service"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        try:
            response = self.cost_explorer.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service_name]
                    }
                }
            )

            costs = []
            for result in response['ResultsByTime']:
                date = datetime.strptime(result['TimePeriod']['Start'], '%Y-%m-%d')
                for group in result['Groups']:
                    if group['Keys'][0] == service_name:
                        amount = Decimal(group['Metrics']['BlendedCost']['Amount'])
                        costs.append(CostMetric(
                            service=service_name,
                            amount=amount,
                            unit='USD',
                            timestamp=date
                        ))

            return costs

        except Exception as e:
            logger.error(f"Failed to fetch service costs: {e}")
            return []


class CostAlertManager:
    """Manage cost alerts and thresholds"""

    def __init__(self):
        self.cost_tracker = AWSCostTracker()
        self.thresholds = {
            'daily_total': Decimal('10.00'),
            'monthly_total': Decimal('150.00'),
            'monthly_compute': Decimal('50.00'),
            'monthly_database': Decimal('25.00'),
            'monthly_networking': Decimal('30.00')
        }

    def check_cost_alerts(self) -> List[CostAlert]:
        """Check for cost threshold violations"""
        alerts = []

        # Check monthly costs
        monthly_costs = self.cost_tracker.get_monthly_costs()
        total_monthly = sum(monthly_costs.values())

        if total_monthly > self.thresholds['monthly_total']:
            alerts.append(CostAlert(
                service='Total',
                current_cost=total_monthly,
                threshold=self.thresholds['monthly_total'],
                period='monthly',
                severity='HIGH' if total_monthly > self.thresholds['monthly_total'] * Decimal('1.2') else 'MEDIUM'
            ))

        # Check specific services
        service_mappings = {
            'Amazon Elastic Compute Cloud - Compute': 'monthly_compute',
            'Amazon Relational Database Service': 'monthly_database',
            'Amazon Elastic Load Balancing': 'monthly_networking'
        }

        for aws_service, threshold_key in service_mappings.items():
            if aws_service in monthly_costs:
                cost = monthly_costs[aws_service]
                threshold = self.thresholds[threshold_key]

                if cost > threshold:
                    alerts.append(CostAlert(
                        service=aws_service,
                        current_cost=cost,
                        threshold=threshold,
                        period='monthly',
                        severity='MEDIUM'
                    ))

        # Check daily costs
        daily_costs = self.cost_tracker.get_daily_costs(days=1)
        if daily_costs:
            today_cost = daily_costs[0].amount
            if today_cost > self.thresholds['daily_total']:
                alerts.append(CostAlert(
                    service='Total',
                    current_cost=today_cost,
                    threshold=self.thresholds['daily_total'],
                    period='daily',
                    severity='HIGH'
                ))

        return alerts

    def send_cost_alerts(self, alerts: List[CostAlert]):
        """Send cost alerts via CloudWatch metrics and logs"""
        for alert in alerts:
            # Send CloudWatch metric (if available)
            if self.cost_tracker.cloudwatch:
                try:
                    self.cost_tracker.cloudwatch.put_metric_data(
                        Namespace='BellaV3/CostAlerts',
                        MetricData=[
                            {
                                'MetricName': f'CostAlert_{alert.service}',
                                'Value': float(alert.current_cost),
                                'Unit': 'None',
                                'Dimensions': [
                                    {
                                        'Name': 'Service',
                                        'Value': alert.service
                                    },
                                    {
                                        'Name': 'Severity',
                                        'Value': alert.severity
                                    }
                                ]
                            }
                        ]
                    )
                except Exception as e:
                    logger.warning(f"Failed to send CloudWatch metric: {e}")
            else:
                logger.info("CloudWatch not available, skipping metric")

            # Log alert
            logger.warning(
                f"Cost Alert: {alert.service} - "
                f"Current: ${alert.current_cost:.2f}, "
                f"Threshold: ${alert.threshold:.2f}, "
                f"Period: {alert.period}, "
                f"Severity: {alert.severity}"
            )


class UsageCostTracker:
    """Track costs per feature/endpoint usage"""

    def __init__(self):
        self.usage_costs = {}
        self.api_costs = {
            'openai_gpt4o_mini': Decimal('0.000015'),  # per 1K tokens
            'twilio_voice_inbound': Decimal('0.0175'),  # per minute
            'whisper_api': Decimal('0.006'),  # per minute
        }

    def track_api_usage(self, api_name: str, units: int, endpoint: str = None):
        """Track API usage and associated costs"""
        if api_name not in self.api_costs:
            logger.warning(f"Unknown API cost for: {api_name}")
            return

        cost = self.api_costs[api_name] * Decimal(str(units))

        key = f"{endpoint or 'unknown'}_{api_name}"
        if key not in self.usage_costs:
            self.usage_costs[key] = {'total_cost': Decimal('0'), 'call_count': 0}

        self.usage_costs[key]['total_cost'] += cost
        self.usage_costs[key]['call_count'] += 1

        logger.info(f"API usage tracked: {api_name} - {units} units - ${cost:.6f}")

    def get_cost_per_call(self, endpoint: str) -> Dict[str, Decimal]:
        """Get average cost per call for an endpoint"""
        endpoint_costs = {}

        for key, data in self.usage_costs.items():
            if key.startswith(endpoint):
                api_name = key.replace(f"{endpoint}_", "")
                if data['call_count'] > 0:
                    endpoint_costs[api_name] = data['total_cost'] / Decimal(str(data['call_count']))

        return endpoint_costs

    def get_usage_report(self) -> Dict[str, Dict]:
        """Generate usage and cost report"""
        report = {
            'total_cost': Decimal('0'),
            'by_endpoint': {},
            'by_api': {}
        }

        for key, data in self.usage_costs.items():
            parts = key.split('_', 1)
            if len(parts) == 2:
                endpoint, api = parts

                # By endpoint
                if endpoint not in report['by_endpoint']:
                    report['by_endpoint'][endpoint] = {'total_cost': Decimal('0'), 'call_count': 0}
                report['by_endpoint'][endpoint]['total_cost'] += data['total_cost']
                report['by_endpoint'][endpoint]['call_count'] += data['call_count']

                # By API
                if api not in report['by_api']:
                    report['by_api'][api] = {'total_cost': Decimal('0'), 'call_count': 0}
                report['by_api'][api]['total_cost'] += data['total_cost']
                report['by_api'][api]['call_count'] += data['call_count']

                report['total_cost'] += data['total_cost']

        return report


class CostOptimizationRecommendations:
    """Generate cost optimization recommendations"""

    def __init__(self):
        self.cost_tracker = AWSCostTracker()
        self.usage_tracker = UsageCostTracker()

    def analyze_costs(self) -> Dict[str, List[str]]:
        """Analyze costs and provide recommendations"""
        recommendations = {
            'immediate': [],
            'short_term': [],
            'long_term': []
        }

        # Get current costs
        monthly_costs = self.cost_tracker.get_monthly_costs()
        usage_report = self.usage_tracker.get_usage_report()

        # Add general recommendations if AWS data is not available
        if not self.cost_tracker.aws_available:
            recommendations['immediate'].extend([
                "Enable AWS Cost Explorer to get real cost data and personalized recommendations",
                "Set up cost monitoring dashboard with proper AWS permissions",
                "Implement caching for LLM responses to reduce API costs"
            ])
            recommendations['short_term'].extend([
                "Configure AWS Cost and Billing alerts for budget monitoring",
                "Evaluate reserved instances for consistent workloads (potential 30-40% savings)",
                "Set up auto-scaling to optimize compute costs"
            ])
            recommendations['long_term'].extend([
                "Consider Aurora Serverless for variable database workloads",
                "Implement intelligent cost-aware feature flags",
                "Evaluate spot instances for development environments"
            ])
            return recommendations

        # Analyze infrastructure costs
        total_monthly = sum(monthly_costs.values())

        if total_monthly > Decimal('100'):
            recommendations['immediate'].append(
                "Consider implementing auto-scaling to reduce compute costs during low usage"
            )
            recommendations['short_term'].append(
                "Evaluate reserved instances for RDS and ElastiCache (potential 30-40% savings)"
            )

        # Analyze API costs
        if 'openai_gpt4o_mini' in usage_report.get('by_api', {}):
            openai_usage = usage_report['by_api']['openai_gpt4o_mini']
            if openai_usage['total_cost'] > Decimal('10'):
                recommendations['immediate'].append(
                    "Implement caching for LLM responses to reduce OpenAI API costs"
                )
                recommendations['long_term'].append(
                    "Consider local lightweight models for simple extractions"
                )

        # Analyze database costs
        if 'Amazon Relational Database Service' in monthly_costs:
            db_cost = monthly_costs['Amazon Relational Database Service']
            if db_cost > Decimal('20'):
                recommendations['short_term'].append(
                    "Consider Aurora Serverless for variable workloads (potential 25-40% savings)"
                )

        # Analyze compute costs
        if 'Amazon Elastic Compute Cloud - Compute' in monthly_costs:
            compute_cost = monthly_costs['Amazon Elastic Compute Cloud - Compute']
            if compute_cost > Decimal('40'):
                recommendations['immediate'].append(
                    "Right-size ECS containers based on actual usage patterns"
                )

        return recommendations

    def generate_cost_report(self) -> Dict:
        """Generate comprehensive cost report"""
        monthly_costs = self.cost_tracker.get_monthly_costs()
        daily_costs = self.cost_tracker.get_daily_costs(days=7)
        usage_report = self.usage_tracker.get_usage_report()
        recommendations = self.analyze_costs()

        # Add note about AWS availability
        aws_status = "connected" if self.cost_tracker.aws_available else "not_available"

        return {
            'timestamp': datetime.now().isoformat(),
            'aws_status': aws_status,
            'monthly_costs': {k: float(v) for k, v in monthly_costs.items()},
            'daily_costs': [
                {
                    'date': cost.timestamp.isoformat(),
                    'amount': float(cost.amount)
                }
                for cost in daily_costs
            ],
            'usage_costs': {
                'total': float(usage_report.get('total_cost', 0)),
                'by_endpoint': {
                    k: {
                        'total_cost': float(v['total_cost']),
                        'call_count': v['call_count']
                    }
                    for k, v in usage_report.get('by_endpoint', {}).items()
                },
                'by_api': {
                    k: {
                        'total_cost': float(v['total_cost']),
                        'call_count': v['call_count']
                    }
                    for k, v in usage_report.get('by_api', {}).items()
                }
            },
            'recommendations': recommendations,
            'summary': {
                'total_monthly_aws': float(sum(monthly_costs.values())),
                'average_daily': float(sum(cost.amount for cost in daily_costs) / len(daily_costs)) if daily_costs else 0,
                'total_api_costs': float(usage_report.get('total_cost', 0))
            }
        }


# CLI interface for cost monitoring
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Bella V3 Cost Monitoring')
    parser.add_argument('--report', action='store_true', help='Generate cost report')
    parser.add_argument('--alerts', action='store_true', help='Check cost alerts')
    parser.add_argument('--recommendations', action='store_true', help='Get optimization recommendations')

    args = parser.parse_args()

    if args.report:
        optimizer = CostOptimizationRecommendations()
        report = optimizer.generate_cost_report()
        print(json.dumps(report, indent=2))

    if args.alerts:
        alert_manager = CostAlertManager()
        alerts = alert_manager.check_cost_alerts()

        if alerts:
            print("Cost Alerts:")
            for alert in alerts:
                print(f"- {alert.service}: ${alert.current_cost:.2f} > ${alert.threshold:.2f} ({alert.severity})")
        else:
            print("No cost alerts")

    if args.recommendations:
        optimizer = CostOptimizationRecommendations()
        recommendations = optimizer.analyze_costs()

        print("Cost Optimization Recommendations:")
        for category, items in recommendations.items():
            if items:
                print(f"\n{category.title()}:")
                for item in items:
                    print(f"- {item}")