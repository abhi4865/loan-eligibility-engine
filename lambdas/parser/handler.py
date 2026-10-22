"""Stream uploaded CSVs, validate rows, save them, then notify n8n."""

import csv
import json
import logging
import os
import urllib.request
import uuid
from urllib.parse import unquote_plus

from psycopg2.extras import execute_values

from lambdas.common.aws_clients import get_s3_client
from lambdas.common.db import get_connection
from lambdas.common.validators import REQUIRED_COLUMNS, validate_row

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CHUNK_SIZE = 1000
MAX_LOGGED_ERRORS = 5
UPSERT_SQL = """
    INSERT INTO users
        (user_id, name, email, monthly_income, credit_score, employment_status, age, batch_id)
    VALUES %s
    ON CONFLICT (user_id) DO UPDATE SET
        name = EXCLUDED.name,
        email = EXCLUDED.email,
        monthly_income = EXCLUDED.monthly_income,
        credit_score = EXCLUDED.credit_score,
        employment_status = EXCLUDED.employment_status,
        age = EXCLUDED.age,
        batch_id = EXCLUDED.batch_id
"""


def _batch_id_from_key(key):
    """Extract and validate the UUID in uploads/<batch_id>/<filename>."""
    parts = key.split("/")
    if len(parts) < 3 or parts[0] != "uploads":
        raise ValueError(f"Unexpected S3 key: {key}")
    return str(uuid.UUID(parts[1]))


def _decoded_lines(body):
    """Yield decoded S3 lines without buffering the complete object in memory."""
    first = True
    for raw_line in body.iter_lines():
        encoding = "utf-8-sig" if first else "utf-8"
        yield raw_line.decode(encoding)
        first = False


def _claim_batch(conn, batch_id):
    """Atomically claim a new or failed batch; duplicate deliveries return False."""
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE upload_batches SET status = 'processing', error = NULL
               WHERE batch_id = %s AND status IN ('uploaded', 'failed')
               RETURNING batch_id""",
            (batch_id,),
        )
        claimed = cur.fetchone() is not None
    conn.commit()
    return claimed


def _flush(conn, rows):
    """Insert or update one bounded chunk of users in a single database call."""
    with conn.cursor() as cur:
        execute_values(cur, UPSERT_SQL, list(rows.values()), page_size=len(rows))
    conn.commit()


def _mark_processed(conn, batch_id, total, valid, invalid):
    """Save import counters and mark the batch processed."""
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE upload_batches
               SET status = 'processed', total_rows = %s, valid_rows = %s,
                   invalid_rows = %s, processed_at = now()
               WHERE batch_id = %s""",
            (total, valid, invalid, batch_id),
        )
    conn.commit()


def _mark_failed(conn, batch_id, message):
    """Store a short failure reason on the batch record."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE upload_batches SET status = 'failed', error = %s WHERE batch_id = %s",
            (message[:500], batch_id),
        )
    conn.commit()


def _import_csv(conn, bucket, key, batch_id):
    """Validate a streamed CSV and save valid rows in chunks of at most 1,000."""
    body = get_s3_client().get_object(Bucket=bucket, Key=key)["Body"]
    try:
        reader = csv.DictReader(_decoded_lines(body))
        if reader.fieldnames is None:
            raise ValueError("The file is empty")
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")

        total = valid = invalid = 0
        chunk = {}
        for row in reader:
            total += 1
            clean, error = validate_row(row)
            if error:
                invalid += 1
                if invalid <= MAX_LOGGED_ERRORS:
                    logger.warning("Skipped row %d: %s", total + 1, error)
                continue

            valid += 1
            chunk[clean["user_id"]] = (
                clean["user_id"], clean["name"], clean["email"],
                clean["monthly_income"], clean["credit_score"],
                clean["employment_status"], clean["age"], batch_id,
            )
            if len(chunk) >= CHUNK_SIZE:
                _flush(conn, chunk)
                chunk.clear()

        if chunk:
            _flush(conn, chunk)
        return total, valid, invalid
    finally:
        body.close()


def _notify_n8n(batch_id, valid_rows, s3_key):
    """Notify n8n after a successful import; a missing workflow is only a warning."""
    url = os.environ.get("N8N_WEBHOOK_URL")
    if not url:
        logger.info("N8N_WEBHOOK_URL is empty, skipping the n8n call")
        return False

    payload = json.dumps(
        {"batch_id": batch_id, "valid_rows": valid_rows, "s3_key": s3_key}
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Secret": os.environ.get("N8N_WEBHOOK_SECRET", ""),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception as exc:
        logger.warning("Could not reach n8n: %s", exc)
        return False


def _process_record(bucket, key):
    """Claim and process one S3 object, recording success or failure."""
    batch_id = _batch_id_from_key(key)
    conn = get_connection()
    try:
        if not _claim_batch(conn, batch_id):
            return {"batch_id": batch_id, "status": "skipped"}
        try:
            total, valid, invalid = _import_csv(conn, bucket, key, batch_id)
            _mark_processed(conn, batch_id, total, valid, invalid)
        except Exception as exc:
            conn.rollback()
            logger.exception("Batch %s failed", batch_id)
            _mark_failed(conn, batch_id, str(exc))
            return {"batch_id": batch_id, "status": "failed", "error": str(exc)}
    finally:
        conn.close()

    webhook_sent = _notify_n8n(batch_id, valid, key) if valid else False
    return {
        "batch_id": batch_id,
        "status": "processed",
        "total_rows": total,
        "valid_rows": valid,
        "invalid_rows": invalid,
        "webhook_sent": webhook_sent,
    }


def handler(event, context):
    """Process each S3 object record and return its per-file result."""
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        results.append(_process_record(bucket, key))
    return {"results": results}
