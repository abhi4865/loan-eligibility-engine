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

## AWS deployment configuration (Phase 7)

The Serverless Framework stack provisions two Python 3.11 Lambdas, an HTTP API `GET /presign`, and a private S3 bucket. S3 CORS allows the browser upload, and objects created under `uploads/` invoke the parser. The Lambda role is scoped to read and write objects in that prefix and includes SES send actions. AWS SDK credentials are supplied by the Lambda execution role; do not put AWS access keys in `.env` for deployment.

### Database and networking

This stack **does not create RDS**. Create a PostgreSQL database separately, apply `db/schema.sql` and `db/seed_products.sql`, then set `AWS_POSTGRES_HOST`, `AWS_POSTGRES_PORT`, `AWS_POSTGRES_DB`, `AWS_POSTGRES_USER`, and `AWS_POSTGRES_PASSWORD` in the deployment environment. Set `AWS_N8N_WEBHOOK_URL` and `AWS_N8N_WEBHOOK_SECRET` for the parser-to-n8n call. These AWS-specific names keep local `.env` credentials out of the deployment artifact. The Lambda security group must be allowed to connect to the database security group on TCP 5432. For private RDS, set `USE_VPC=on`, `VPC_SECURITY_GROUP_ID`, `VPC_SUBNET_ID_1`, and `VPC_SUBNET_ID_2`. A Lambda in private subnets also needs outbound routing (such as a NAT gateway) to call an external n8n webhook; alternatively make the webhook privately reachable.

### Package and deploy

Install Node.js, npm, Python 3.11, and configure AWS CLI credentials with permission to create Lambda, IAM, API Gateway, and S3 resources. Copy `.env.example` to `.env` for local configuration; set the AWS deployment values above and `AWS_REGION`. Set a globally unique `AWS_S3_BUCKET` name before deployment; the default placeholder exists only so packaging can run without AWS account lookup. Set `AWS_ACCOUNT_ID` to scope SES permissions to your account. Restrict `AWS_UI_ORIGIN` to the HTTPS origin serving the UI before deployment. The packaging config downloads the Python 3.11 manylinux x86_64 wheel for `psycopg2-binary`, so it does not need Docker on Windows.

```powershell
npm install
npm run package
npm run deploy
```

`serverless package` creates the deployment artifacts under `.serverless/` without deploying. After deployment, copy the `PresignUrl` output into the UI API base URL setting and upload only test data. AWS-specific database passwords and webhook secrets passed through the `AWS_*` variables are embedded in the Lambda environment configuration; for production, store them in AWS Systems Manager Parameter Store/Secrets Manager and inject them through the deployment configuration. SES identities and the n8n workflows remain separately configured; SES permissions on the Lambda role do not configure n8n's own SES credential.
