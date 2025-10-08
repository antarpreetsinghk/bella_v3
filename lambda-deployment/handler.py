import os
import sys
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from mangum import Mangum
from app.main import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lambda handler
handler = Mangum(app, lifespan="off")

def lambda_handler(event, context):
    """AWS Lambda handler"""
    try:
        logger.info(f"Processing event: {event}")
        return handler(event, context)
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": f'{{"error": "Internal server error: {str(e)}"}}',
            "headers": {"Content-Type": "application/json"}
        }
