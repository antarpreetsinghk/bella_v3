import os
import sys
import logging
import json

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from mangum import Mangum
    from app.main import app

    # Lambda handler with proper error handling
    mangum_handler = Mangum(app, lifespan="off")

    def lambda_handler(event, context):
        """AWS Lambda handler with comprehensive error handling"""
        try:
            logger.info(f"Processing event type: {event.get('httpMethod', 'unknown')}")
            logger.info(f"Path: {event.get('path', 'unknown')}")

            # Call the mangum handler
            response = mangum_handler(event, context)
            logger.info(f"Response status: {response.get('statusCode', 'unknown')}")
            return response

        except Exception as handler_error:
            logger.error(f"Handler error: {str(handler_error)}", exc_info=True)
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Internal server error: {str(handler_error)}"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }

except ImportError as import_error:
    logger.error(f"Import error: {str(import_error)}")

    def lambda_handler(event, context):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Import error: {str(import_error)}"}),
            "headers": {"Content-Type": "application/json"}
        }

except Exception as general_error:
    logger.error(f"General error during import: {str(general_error)}")

    def lambda_handler(event, context):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Startup error: {str(general_error)}"}),
            "headers": {"Content-Type": "application/json"}
        }
