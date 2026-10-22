"""Create an upload batch and return a short-lived direct-to-S3 upload link."""

import json
import os
import re
import uuid

from lambdas.common.aws_clients import get_s3_client
from lambdas.common.db import run_query

URL_EXPIRY_SECONDS = 900


def _response(status_code, body):
    """Format a JSON response for API Gateway or the local test runner."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def _safe_filename(filename):
    """Keep a single safe filename so caller input cannot alter the S3 path."""
    name = str(filename).replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "users.csv"


def handler(event, context):
    """Create a batch row and return its presigned PUT URL."""
    params = event.get("queryStringParameters") or {}
    filename = _safe_filename(params.get("filename") or "users.csv")
    if not filename.lower().endswith(".csv"):
        return _response(400, {"error": "Only .csv files are accepted"})

    batch_id = str(uuid.uuid4())
    s3_key = f"uploads/{batch_id}/{filename}"
    try:
        upload_url = get_s3_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": os.environ["S3_BUCKET"],
                "Key": s3_key,
                "ContentType": "text/csv",
            },
            ExpiresIn=URL_EXPIRY_SECONDS,
        )
        run_query(
            "INSERT INTO upload_batches (batch_id, s3_key, status) VALUES (%s, %s, 'uploaded')",
            (batch_id, s3_key),
        )
    except Exception:
        return _response(500, {"error": "Could not prepare the upload batch"})

    return _response(
        200,
        {"batch_id": batch_id, "upload_url": upload_url, "s3_key": s3_key},
    )
