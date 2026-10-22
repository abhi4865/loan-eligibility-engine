# scripts/set_bucket_cors.py
# Sets CORS on the upload bucket so a browser page may PUT a file to it.
# Real S3: this call is needed. MinIO: it ignores bucket CORS and uses its own server setting
# (see instruction6.md), so this script only explains that.
# Use: python scripts/set_bucket_cors.py [--origin http://localhost:8000]
import argparse
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(description="Allow browser uploads to the S3 bucket")
    parser.add_argument(
        "--origin",
        default="http://localhost:8000",
        help="page origin allowed to upload (default: local Phase 6 page)",
    )
    args = parser.parse_args()

    bucket = os.environ["S3_BUCKET"]
    s3 = boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION"),
        endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
    )
    rules = {
        "CORSRules": [
            {
                "AllowedOrigins": [args.origin],
                "AllowedMethods": ["PUT", "GET", "HEAD"],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3000,
            }
        ]
    }
    try:
        s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=rules)
        print(f"CORS set on bucket {bucket} for origin {args.origin}")
    except ClientError as err:
        print(f"Could not set bucket CORS: {err.response['Error']['Code']}")
        if os.environ.get("S3_ENDPOINT_URL"):
            print(
                "MinIO uses its server-level CORS setting; it allows all origins by default. "
                "Set MINIO_API_CORS_ALLOW_ORIGIN to the page origin to restrict it."
            )


if __name__ == "__main__":
    main()
