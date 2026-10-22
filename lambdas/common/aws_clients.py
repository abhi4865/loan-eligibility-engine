"""Create an S3 client for local MinIO or AWS using environment settings."""

import os

import boto3
from botocore.config import Config


def get_s3_client():
    """Return an S3 client configured for path-style S3 and SigV4 signing."""
    endpoint_url = os.environ.get("S3_ENDPOINT_URL") or None
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        endpoint_url=endpoint_url,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )
