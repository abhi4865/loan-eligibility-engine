# Loan Eligibility Engine

## Local browser upload (Phase 6)

Start Docker services from the repository root:

```powershell
docker compose up -d
```

In a second terminal, start the local upload server and open the shown URL:

```powershell
.venv\Scripts\python.exe scripts\local_server.py
```

Open `http://localhost:8000`, choose `data/users.csv`, and click **Upload**. The browser asks the presign handler for a short-lived PUT URL, sends the CSV directly to MinIO, then asks the local server to invoke the parser because MinIO does not emit a Lambda event locally. The page polls batch status while parsing runs. After parsing, the handler calls Workflow B; Workflow B calls Workflow C.

The local server binds to `127.0.0.1` and reads `.env` from the repository root. Do not expose it to a public network. For AWS, serve the page over HTTPS, set the API Gateway base URL in Settings, turn off Local mode, and configure S3 CORS for that exact page origin:

```powershell
.venv\Scripts\python.exe scripts\set_bucket_cors.py --origin https://your-page.example
```

The S3 PUT bypasses Lambda so large files do not pass through API Gateway or Lambda request handling. CORS lets the browser authorize the cross-origin PUT from the page to S3 or MinIO.
