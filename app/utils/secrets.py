"""
AWS Secrets Manager utility for loading configuration.
Provides a fallback mechanism to load secrets when environment variables are not available.
"""
import json
import os
import boto3
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_secrets_manager_client():
    """Get cached Secrets Manager client"""
    return boto3.client('secretsmanager', region_name=os.getenv('AWS_DEFAULT_REGION', 'ca-central-1'))


@lru_cache(maxsize=1)
def load_secrets_from_aws() -> Dict[str, str]:
    """
    Load secrets from AWS Secrets Manager.
    This is used as a fallback when environment variables are not available.
    """
    try:
        secret_id = os.getenv('SECRETS_MANAGER_SECRET_ID', 'bella-env-82YlZa')

        client = get_secrets_manager_client()
        response = client.get_secret_value(SecretId=secret_id)
        secrets = json.loads(response['SecretString'])

        logger.info(f"Successfully loaded {len(secrets)} secrets from AWS Secrets Manager")
        return secrets

    except Exception as e:
        logger.warning(f"Failed to load secrets from AWS Secrets Manager: {e}")
        return {}


def get_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get configuration value with fallback priority:
    1. Environment variable
    2. AWS Secrets Manager
    3. Default value
    """
    # First try environment variable
    value = os.getenv(key)
    if value is not None:
        return value

    # Fall back to AWS Secrets Manager
    try:
        secrets = load_secrets_from_aws()
        value = secrets.get(key)
        if value is not None:
            return value
    except Exception as e:
        logger.debug(f"Could not load {key} from secrets: {e}")

    # Return default
    return default


def is_feature_enabled(feature_key: str) -> bool:
    """
    Check if a feature is enabled via configuration.
    Returns True if the value is 'true', '1', or 'yes' (case insensitive).
    """
    value = get_config_value(feature_key, "false")
    return value.lower() in ("true", "1", "yes")