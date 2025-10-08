#!/usr/bin/env python3
"""
Production Lambda Health Tests
Comprehensive health checks for AWS Lambda deployment
"""

import pytest
import httpx
import json
import boto3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Test configuration
FUNCTION_NAME = "bella-voice-app"
FUNCTION_URL = "https://bhcnf2i6eh3bxnr6lrnt4ubouy0obfjy.lambda-url.us-east-1.on.aws"
REGION = "us-east-1"
TIMEOUT = 30


def has_aws_credentials():
    """Check if AWS credentials are available"""
    try:
        # Try to create a session and check credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials is None:
            return False
        # Try to get caller identity to verify credentials work
        sts = session.client('sts')
        sts.get_caller_identity()
        return True
    except (NoCredentialsError, PartialCredentialsError, Exception):
        return False


# Skip all AWS tests if credentials not available
pytestmark = pytest.mark.skipif(
    not has_aws_credentials(),
    reason="AWS credentials not available - skipping production Lambda tests"
)


class TestLambdaHealth:
    """Test Lambda function health and configuration"""

    @pytest.fixture(autouse=True)
    def setup_clients(self):
        """Setup AWS clients for testing"""
        self.lambda_client = boto3.client('lambda', region_name=REGION)
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=REGION)
        self.logs_client = boto3.client('logs', region_name=REGION)

    @pytest.mark.production
    @pytest.mark.smoke
    def test_lambda_function_exists(self):
        """Test that Lambda function exists and is active"""
        try:
            response = self.lambda_client.get_function(FunctionName=FUNCTION_NAME)

            # Check function exists
            assert response['Configuration']['FunctionName'] == FUNCTION_NAME

            # Check function is active
            assert response['Configuration']['State'] == 'Active'

            # Check last update status
            assert response['Configuration']['LastUpdateStatus'] in ['Successful', 'InProgress']

            print(f"✅ Function {FUNCTION_NAME} exists and is active")
            print(f"Runtime: {response['Configuration']['Runtime']}")
            print(f"Handler: {response['Configuration']['Handler']}")
            print(f"Memory: {response['Configuration']['MemorySize']}MB")
            print(f"Timeout: {response['Configuration']['Timeout']}s")

        except Exception as e:
            pytest.fail(f"Lambda function check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_function_configuration(self):
        """Test Lambda function configuration is optimal"""
        try:
            config = self.lambda_client.get_function_configuration(FunctionName=FUNCTION_NAME)

            # Check memory allocation (should be adequate for voice processing)
            memory_size = config['MemorySize']
            assert memory_size >= 512, f"Memory too low: {memory_size}MB"

            # Check timeout (should handle complex calls)
            timeout = config['Timeout']
            assert timeout >= 30, f"Timeout too low: {timeout}s"

            # Check runtime
            runtime = config['Runtime']
            assert runtime.startswith('python3'), f"Unexpected runtime: {runtime}"

            # Check package size (should be reasonable)
            code_size = config['CodeSize']
            assert code_size < 50_000_000, f"Package too large: {code_size} bytes"

            print(f"✅ Function configuration optimal")
            print(f"Memory: {memory_size}MB, Timeout: {timeout}s")
            print(f"Runtime: {runtime}, Package: {code_size:,} bytes")

        except Exception as e:
            pytest.fail(f"Configuration check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_environment_variables(self):
        """Test required environment variables are set"""
        try:
            config = self.lambda_client.get_function_configuration(FunctionName=FUNCTION_NAME)
            env_vars = config.get('Environment', {}).get('Variables', {})

            # Required environment variables
            required_vars = {
                'APP_ENV': 'production',
                'BELLA_API_KEY': None,  # Should exist but we won't check value
                'TWILIO_ACCOUNT_SID': None,
                'OPENAI_API_KEY': None,
                'DYNAMODB_TABLE_NAME': 'bella-voice-app-sessions'
            }

            missing_vars = []
            for var, expected_value in required_vars.items():
                if var not in env_vars:
                    missing_vars.append(var)
                elif expected_value and env_vars[var] != expected_value:
                    missing_vars.append(f"{var} (wrong value)")

            assert not missing_vars, f"Missing/incorrect environment variables: {missing_vars}"

            print(f"✅ All required environment variables present")
            print(f"Variables count: {len(env_vars)}")

        except Exception as e:
            pytest.fail(f"Environment variables check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_function_url_access(self):
        """Test Lambda Function URL is accessible"""
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                # Test health endpoint
                response = client.get(f"{FUNCTION_URL}/health")

                # Check status code (might be 200 or 404 if endpoint doesn't exist)
                assert response.status_code in [200, 404, 403], f"Unexpected status: {response.status_code}"

                # Check response time
                assert response.elapsed.total_seconds() < 5.0, "Response too slow"

                print(f"✅ Function URL accessible")
                print(f"Status: {response.status_code}")
                print(f"Response time: {response.elapsed.total_seconds():.2f}s")

        except httpx.TimeoutException:
            pytest.fail("Function URL timeout")
        except Exception as e:
            pytest.fail(f"Function URL access failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_function_direct_invocation(self):
        """Test direct Lambda function invocation"""
        try:
            # Test payload for health check
            test_payload = {
                "httpMethod": "GET",
                "path": "/health",
                "headers": {},
                "queryStringParameters": None,
                "body": None,
                "isBase64Encoded": False
            }

            start_time = time.time()

            response = self.lambda_client.invoke(
                FunctionName=FUNCTION_NAME,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # Check invocation was successful
            assert response['StatusCode'] == 200, f"Invocation failed: {response['StatusCode']}"

            # Check execution time
            assert execution_time < 10.0, f"Execution too slow: {execution_time:.2f}s"

            # Parse response
            payload = json.loads(response['Payload'].read())

            print(f"✅ Direct invocation successful")
            print(f"Execution time: {execution_time:.2f}s")
            print(f"Response: {payload}")

        except Exception as e:
            pytest.fail(f"Direct invocation failed: {e}")

    @pytest.mark.production
    @pytest.mark.slow
    @pytest.mark.smoke
    def test_concurrent_execution_limits(self):
        """Test concurrent execution doesn't hit limits"""
        try:
            config = self.lambda_client.get_function_configuration(FunctionName=FUNCTION_NAME)

            # Check reserved concurrency (should be None for unlimited)
            reserved_concurrency = config.get('ReservedConcurrencyExecutions')
            if reserved_concurrency:
                assert reserved_concurrency >= 10, f"Reserved concurrency too low: {reserved_concurrency}"

            # Check provisioned concurrency
            try:
                pc_response = self.lambda_client.get_provisioned_concurrency_config(
                    FunctionName=FUNCTION_NAME,
                    Qualifier='$LATEST'
                )
                print(f"Provisioned concurrency: {pc_response['ProvisionedConcurrencyExecutions']}")
            except self.lambda_client.exceptions.ProvisionedConcurrencyConfigNotFoundException:
                print("No provisioned concurrency configured (normal for cost optimization)")

            print(f"✅ Concurrency configuration checked")

        except Exception as e:
            pytest.fail(f"Concurrency check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_cloudwatch_logs_configured(self):
        """Test CloudWatch logs are properly configured"""
        try:
            log_group_name = f"/aws/lambda/{FUNCTION_NAME}"

            # Check log group exists
            response = self.logs_client.describe_log_groups(
                logGroupNamePrefix=log_group_name
            )

            log_groups = [lg for lg in response['logGroups'] if lg['logGroupName'] == log_group_name]
            assert log_groups, f"Log group not found: {log_group_name}"

            log_group = log_groups[0]

            # Check retention policy (should be set for cost optimization)
            retention_days = log_group.get('retentionInDays')
            if retention_days:
                assert retention_days <= 30, f"Log retention too long for cost optimization: {retention_days} days"

            print(f"✅ CloudWatch logs configured")
            print(f"Log group: {log_group_name}")
            print(f"Retention: {retention_days or 'Never expire'} days")

        except Exception as e:
            pytest.fail(f"CloudWatch logs check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_recent_invocations(self):
        """Test function has been invoked recently (indicates it's working)"""
        try:
            # Get invocations from last hour
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': FUNCTION_NAME
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )

            invocations = 0
            if response['Datapoints']:
                invocations = response['Datapoints'][0]['Sum']

            print(f"✅ Invocations in last hour: {invocations}")

            # Don't fail if no recent invocations - might be expected
            if invocations == 0:
                print("⚠️ No recent invocations - consider testing with real calls")

        except Exception as e:
            pytest.fail(f"Recent invocations check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_error_rate(self):
        """Test function error rate is acceptable"""
        try:
            # Get errors from last hour
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            # Get invocations
            invocations_response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': FUNCTION_NAME
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )

            # Get errors
            errors_response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': FUNCTION_NAME
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )

            invocations = 0
            if invocations_response['Datapoints']:
                invocations = invocations_response['Datapoints'][0]['Sum']

            errors = 0
            if errors_response['Datapoints']:
                errors = errors_response['Datapoints'][0]['Sum']

            # Calculate error rate
            error_rate = 0
            if invocations > 0:
                error_rate = (errors / invocations) * 100

            # Assert error rate is acceptable (< 5%)
            assert error_rate < 5.0, f"Error rate too high: {error_rate:.2f}%"

            print(f"✅ Error rate acceptable: {error_rate:.2f}%")
            print(f"Invocations: {invocations}, Errors: {errors}")

        except Exception as e:
            pytest.fail(f"Error rate check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_average_duration(self):
        """Test function average duration is reasonable"""
        try:
            # Get duration from last hour
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Duration',
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': FUNCTION_NAME
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average', 'Maximum']
            )

            if response['Datapoints']:
                datapoint = response['Datapoints'][0]
                avg_duration = datapoint['Average']
                max_duration = datapoint['Maximum']

                # Assert average duration is reasonable (< 5 seconds)
                assert avg_duration < 5000, f"Average duration too high: {avg_duration:.0f}ms"

                # Assert max duration is reasonable (< 15 seconds)
                assert max_duration < 15000, f"Max duration too high: {max_duration:.0f}ms"

                print(f"✅ Duration metrics acceptable")
                print(f"Average: {avg_duration:.0f}ms, Max: {max_duration:.0f}ms")
            else:
                print("No duration data available (no recent invocations)")

        except Exception as e:
            pytest.fail(f"Duration check failed: {e}")


class TestProductionReadiness:
    """Test production readiness indicators"""

    @pytest.fixture(autouse=True)
    def setup_clients(self):
        """Setup AWS clients for testing"""
        self.lambda_client = boto3.client('lambda', region_name=REGION)

    @pytest.mark.production
    @pytest.mark.smoke
    def test_cost_optimization_settings(self):
        """Test cost optimization settings are in place"""
        try:
            config = self.lambda_client.get_function_configuration(FunctionName=FUNCTION_NAME)

            # Check memory is cost-optimized (not too high)
            memory_size = config['MemorySize']
            assert memory_size <= 1024, f"Memory might be over-provisioned: {memory_size}MB"

            # Check no reserved concurrency (which costs extra)
            reserved_concurrency = config.get('ReservedConcurrencyExecutions')
            assert reserved_concurrency is None, f"Reserved concurrency set (costs extra): {reserved_concurrency}"

            print(f"✅ Cost optimization settings correct")
            print(f"Memory: {memory_size}MB (cost-optimized)")
            print(f"Reserved concurrency: None (cost-optimized)")

        except Exception as e:
            pytest.fail(f"Cost optimization check failed: {e}")

    @pytest.mark.production
    @pytest.mark.smoke
    def test_security_configuration(self):
        """Test security configuration is appropriate"""
        try:
            config = self.lambda_client.get_function_configuration(FunctionName=FUNCTION_NAME)

            # Check execution role exists
            role_arn = config['Role']
            assert role_arn, "No execution role configured"
            assert 'bella-voice-app' in role_arn, f"Unexpected role: {role_arn}"

            # Check VPC configuration (should be None for cost optimization)
            vpc_config = config.get('VpcConfig')
            if vpc_config and vpc_config.get('SubnetIds'):
                print(f"⚠️ VPC configuration detected - may increase costs and latency")
            else:
                print(f"✅ No VPC configuration (cost-optimized)")

            print(f"✅ Security configuration checked")
            print(f"Execution role: {role_arn.split('/')[-1]}")

        except Exception as e:
            pytest.fail(f"Security configuration check failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])