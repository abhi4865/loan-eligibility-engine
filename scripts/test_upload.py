"""Exercise the presign, MinIO upload, and parser flow without the web UI."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from lambdas.common.db import get_connection  # noqa: E402
from lambdas.parser.handler import handler as parser_handler  # noqa: E402
from lambdas.presign.handler import handler as presign_handler  # noqa: E402


def make_s3_event(key):
    """Build the minimal S3 event shape expected by the parser Lambda."""
    return {
        "Records": [{
            "s3": {
                "bucket": {"name": os.environ["S3_BUCKET"]},
                "object": {"key": quote_plus(key)},
            }
        }]
    }


def upload_file(path, upload_url):
    """PUT a CSV directly to the presigned URL with its required content type."""
    request = urllib.request.Request(
        upload_url,
        data=Path(path).read_bytes(),
        method="PUT",
        headers={"Content-Type": "text/csv"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Upload failed: HTTP {exc.code} {exc.read().decode()[:300]}") from exc


def show_batch(batch_id):
    """Print the batch counters and rows assigned to the upload batch."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, total_rows, valid_rows, invalid_rows, error "
                "FROM upload_batches WHERE batch_id = %s",
                (batch_id,),
            )
            row = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM users WHERE batch_id = %s", (batch_id,))
            users_in_batch = cur.fetchone()[0]
    finally:
        conn.close()
    if row is None:
        raise RuntimeError(f"Unknown batch_id: {batch_id}")
    print("\n--- Database check ---")
    print(f"batch_id          : {batch_id}")
    print(f"status            : {row[0]}")
    print(f"total/valid/invalid: {row[1]} / {row[2]} / {row[3]}")
    print(f"error             : {row[4]}")
    print(f"users saved with this batch_id: {users_in_batch}")


def replay(batch_id):
    """Deliver the same stored object event again to demonstrate idempotency."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT s3_key FROM upload_batches WHERE batch_id = %s", (batch_id,))
            found = cur.fetchone()
    finally:
        conn.close()
    if not found:
        raise RuntimeError(f"Unknown batch_id: {batch_id}")
    print(json.dumps(parser_handler(make_s3_event(found[0]), None), indent=2))
    show_batch(batch_id)


def main():
    """Run a new CSV upload or replay a previously processed batch."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "csv_path", nargs="?", default=str(ROOT / "data" / "users.csv")
    )
    arg_parser.add_argument("--replay", metavar="BATCH_ID")
    args = arg_parser.parse_args()
    if args.replay:
        replay(args.replay)
        return

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        raise RuntimeError(f"CSV file is missing or empty: {csv_path}")

    reply = presign_handler(
        {"queryStringParameters": {"filename": csv_path.name}}, None
    )
    body = json.loads(reply["body"])
    if reply["statusCode"] != 200:
        raise RuntimeError(f"Presign failed: {body}")
    print("1) presign ok, batch_id =", body["batch_id"])

    status = upload_file(csv_path, body["upload_url"])
    print("2) upload ok, HTTP", status)

    result = parser_handler(make_s3_event(body["s3_key"]), None)
    print("3) parser result:")
    print(json.dumps(result, indent=2))
    show_batch(body["batch_id"])


if __name__ == "__main__":
    main()
