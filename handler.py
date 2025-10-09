#!/usr/bin/env python3
"""
Production Lambda handler for Bella Voice App using full FastAPI application.
This replaces the minimal handler with the complete conversation flow system.
"""
import os
import sys
import logging

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    AWS Lambda handler that wraps the FastAPI application.
    Uses Mangum to convert Lambda events to ASGI format.
    """
    try:
        # Import the FastAPI app with full conversation flow
        from app.main import app
        from mangum import Mangum

        # Create Mangum adapter for Lambda
        asgi_handler = Mangum(app, lifespan="off")

        logger.info(f"Processing Lambda event: {event.get('httpMethod', 'UNKNOWN')} {event.get('path', '/')}")

        # Handle the request
        response = asgi_handler(event, context)

        logger.info(f"Lambda response status: {response.get('statusCode', 'unknown')}")
        return response

    except ImportError as e:
        logger.error(f"Import error - missing dependencies: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': '{"error": "Missing dependencies. Please check Lambda deployment package."}'
        }
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': f'{{"error": "Internal server error: {str(e)}"}}'
        }

# For local testing compatibility
if __name__ == "__main__":
    print("Lambda handler ready for deployment")
    print("To test locally, use: python -m uvicorn app.main:app --reload")