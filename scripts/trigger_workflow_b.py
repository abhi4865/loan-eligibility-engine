# scripts/trigger_workflow_b.py
# Sends the "users processed" webhook to n8n Workflow B, the same way the parser Lambda does.
# Why: lets you test Workflow B without uploading a CSV again.
# Use: python scripts/trigger_workflow_b.py <batch_id> [--test] [--wrong-secret]
import argparse, json, os, urllib.error, urllib.request


def load_env(path=".env"):
    """Read KEY=VALUE lines from .env into a dict (no extra library needed)."""
    values = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def main():
    parser = argparse.ArgumentParser(description="Call n8n Workflow B webhook")
    parser.add_argument("batch_id", help="batch_id from the upload_batches table")
    parser.add_argument("--test", action="store_true", help="use /webhook-test/ (workflow not active)")
    parser.add_argument("--wrong-secret", action="store_true", help="send a bad secret, expect 401")
    parser.add_argument("--host", default="http://localhost:5678")
    args = parser.parse_args()

    env = load_env()
    secret = "wrong-secret" if args.wrong_secret else os.environ.get("N8N_WEBHOOK_SECRET", env.get("N8N_WEBHOOK_SECRET", ""))
    path = "webhook-test" if args.test else "webhook"
    url = f"{args.host}/{path}/users-processed"
    body = json.dumps({"batch_id": args.batch_id, "valid_rows": 0, "s3_key": f"uploads/{args.batch_id}/users.csv"}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-Webhook-Secret": secret})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(resp.status, resp.read().decode())
    except urllib.error.HTTPError as err:  # 401 and 404 land here
        print(err.code, err.read().decode())


if __name__ == "__main__":
    main()
