# scripts/local_server.py
# Small local web server for demos on a laptop. It does what API Gateway + the S3 event do on AWS:
#   GET  /            -> serves ui/index.html
#   GET  /presign     -> runs the presign Lambda code
#   POST /process     -> runs the parser Lambda code in the background (MinIO cannot trigger a Lambda)
#   GET  /status      -> reads one row of upload_batches, so the page can show progress
# Use: python scripts/local_server.py   then open http://localhost:8000
import argparse
import importlib
import json
import os
import re
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def get_lambda(module_name):
    """Import a handler module and return its entry function (lambda_handler or handler)."""
    module = importlib.import_module(module_name)
    for name in ("lambda_handler", "handler"):
        if hasattr(module, name):
            return getattr(module, name)
    raise RuntimeError(f"{module_name} has no lambda_handler/handler function")


def call_presign(filename):
    """Run the presign Lambda with a fake API event. Returns (status_code, json_body)."""
    result = get_lambda("lambdas.presign.handler")({"queryStringParameters": {"filename": filename}}, None)
    if isinstance(result, dict) and "statusCode" in result:
        body = result.get("body")
        return result["statusCode"], (json.loads(body) if isinstance(body, str) and body else body)
    return 200, result


def run_parser(batch_id, key):
    """Run the parser Lambda with the same event shape S3 sends. Runs in a thread."""
    event = {"Records": [{"s3": {"bucket": {"name": os.environ.get("S3_BUCKET", "loan-uploads")}, "object": {"key": key}}}]}
    try:
        get_lambda("lambdas.parser.handler")(event, None)
    except Exception:
        traceback.print_exc()   # the parser also writes status=failed in the database


def read_status(batch_id):
    """Return one upload_batches row as a dict, or None when the batch does not exist."""
    import psycopg2
    conn = psycopg2.connect(host=os.environ.get("POSTGRES_HOST", "localhost"), port=os.environ.get("POSTGRES_PORT", "5432"),
                            dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT status, total_rows, valid_rows, invalid_rows, error FROM upload_batches WHERE batch_id = %s", (batch_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    return None if row is None else dict(zip(("status", "total_rows", "valid_rows", "invalid_rows", "error"), row))


def get_batch_for_processing(batch_id):
    """Return the stored S3 key only for a valid batch that has not started yet."""
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT s3_key, status FROM upload_batches WHERE batch_id = %s",
                (batch_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, payload, ctype="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        origin = self.headers.get("Origin")
        if origin in {f"http://localhost:{self.server.server_port}", f"http://127.0.0.1:{self.server.server_port}"}:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.reply(204, b"")

    def do_GET(self):
        url, query = urlparse(self.path), parse_qs(urlparse(self.path).query)
        try:
            if url.path in ("/", "/index.html"):
                self.reply(200, (ROOT / "ui" / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/presign":
                code, body = call_presign(query.get("filename", ["users.csv"])[0])
                self.reply(code, body)
            elif url.path == "/status":
                batch_id = query.get("batch_id", [""])[0]
                row = read_status(batch_id) if UUID_RE.match(batch_id) else None
                self.reply(200 if row else 404, row or {"error": "batch not found"})
            else:
                self.reply(404, {"error": "not found"})
        except Exception as err:
            traceback.print_exc()
            self.reply(500, {"error": str(err)})

    def do_POST(self):
        url, query = urlparse(self.path), parse_qs(urlparse(self.path).query)
        batch_id = query.get("batch_id", [""])[0]
        if url.path != "/process" or not UUID_RE.match(batch_id):
            return self.reply(400, {"error": "POST /process?batch_id=<uuid>"})
        batch = get_batch_for_processing(batch_id)
        if batch is None:
            return self.reply(404, {"error": "batch not found"})
        key, status = batch
        if status not in {"uploaded", "failed"}:
            return self.reply(409, {"error": f"batch is {status}"})
        threading.Thread(target=run_parser, args=(batch_id, key), daemon=True).start()
        self.reply(202, {"status": "started", "batch_id": batch_id})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Open http://localhost:{args.port}  (Ctrl+C to stop)")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local upload server.")
    finally:
        server.server_close()
