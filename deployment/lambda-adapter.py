#!/usr/bin/env python3
"""
Lambda adapter for Bella Voice App
Wraps the FastAPI application for AWS Lambda execution
"""

import os
import sys
import logging
from typing import Dict, Any

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(__file__))

from mangum import Mangum
from app.main import app

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Lambda handler
# lifespan="off" disables startup/shutdown events which can cause issues in Lambda
handler = Mangum(app, lifespan="off")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function

    Args:
        event: Lambda event data
        context: Lambda context object

    Returns:
        Response dictionary for API Gateway/Lambda Function URL
    """
    try:
        # Log incoming request for debugging
        logger.info(f"Lambda event: {event}")

        # Use Mangum to handle the request
        response = handler(event, context)

        # Log response for debugging
        logger.info(f"Lambda response: {response}")

        return response

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)

        # Return a 500 error response
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": f'{{"error": "Internal server error: {str(e)}"}}',
        }

# For local testing
if __name__ == "__main__":
    # Test the handler locally
    test_event = {
        "httpMethod": "GET",
        "path": "/health",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
        "isBase64Encoded": False
    }

    class MockContext:
        def __init__(self):
            self.function_name = "test"
            self.function_version = "1"
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
            self.memory_limit_in_mb = "512"
            self.remaining_time_in_millis = lambda: 30000

    result = lambda_handler(test_event, MockContext())
    print(f"Test result: {result}")