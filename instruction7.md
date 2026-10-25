<!-- instruction7.md : how to run Phase 7 (serverless.yml, AWS deployment config) -->
# instruction7.md — Phase 7: AWS deployment config (`serverless.yml`)

Goal: describe the AWS version of the pipeline as code. **Required:** `serverless package` succeeds. **Bonus:** `serverless deploy` works and the page uploads a CSV to real S3.

## 1. Files in this phase

| File | Where to put it in your repo |
|------|------------------------------|
| `serverless.yml` | repo root |
| `package.json` | repo root (Serverless Framework v3 and one plugin) |
| `requirements-lambda.txt` | repo root (only what the Lambdas need) |
| `instruction7.md` | repo root (or `docs/`) |

Add these lines to `.gitignore`:

```
node_modules/
.serverless/
.env.*
```

## 2. What `serverless.yml` creates

| Resource | Details |
|----------|---------|
| Lambda `presign` | `GET /presign` through an HTTP API (CORS on). 10 s, 256 MB. |
| Lambda `parser` | Started by S3 for every new object under `uploads/`. 300 s, 512 MB. |
| S3 bucket (`S3_BUCKET`) | Public access blocked, CORS for browser `PUT`, event to `parser`, uploads expire after 30 days. |
| Lambda permission | Lets S3 start `parser`. |
| IAM role | `s3:GetObject` and `s3:PutObject` on `uploads/*` of this bucket only. SES send (not used by the Lambdas; n8n sends mail with its own credential. Kept because the spec lists it). |
| Environment variables | Same names as `.env`. No `AWS_*` and no `S3_ENDPOINT_URL` (Lambda provides credentials; empty endpoint means real S3). |
| Outputs | `PresignUrl` (put it in the page Settings) and `UploadBucketName`. |
| Optional VPC | Off by default. Turn on with `USE_VPC=on` (see section 6). |

**Not created: RDS.** The database is documented, not provisioned (allowed by project.md). Say this clearly in the README.

## 3. Part A: make `serverless package` succeed (the acceptance test)

### Step 1: install the tools

Needs Node.js 18+ and Python 3.11 compatible manylinux wheels. The configured pip options select the Linux x86_64 wheels directly, so packaging does not need Docker on Windows.

```powershell
npm install
```

**What this does:** It installs Serverless Framework v3 and the `serverless-python-requirements` plugin into `node_modules/`. v3 is used on purpose: it needs no Serverless login. One thing that can go wrong: if you run `npx serverless` without `npm install`, npm may fetch v4, which asks you to log in.

### Step 2: check the handler names

```powershell
Select-String -Path lambdas/presign/handler.py, lambdas/parser/handler.py -Pattern "^def "
```

At the top of `serverless.yml`, `custom.presignHandler` and `custom.parserHandler` end with `.lambda_handler`. If your function is called `handler`, change that word (example: `lambdas/presign/handler.handler`).

### Step 3: create the deploy env file `.env.dev`

Serverless v3 reads **`.env.dev` instead of `.env`** when the stage is `dev` (the default). Use that to keep your real AWS keys away from the MinIO keys in `.env`. Create `.env.dev` in the repo root (it is git-ignored):

```
AWS_REGION=ap-south-1
S3_BUCKET=<a globally unique name, example: loan-uploads-abhishek-2026>
POSTGRES_HOST=<RDS endpoint, or any reachable Postgres host>
POSTGRES_PORT=5432
POSTGRES_DB=loan_db
POSTGRES_USER=loan_user
POSTGRES_PASSWORD=<password>
N8N_WEBHOOK_URL=https://<public-url>/webhook/users-processed
N8N_WEBHOOK_SECRET=<same secret as in n8n>
```

For `package` only, any dummy values work (for example `POSTGRES_HOST=dummy.example.com`), but they must exist, or Serverless says "Cannot resolve variable".

**What this does:** `${env:NAME}` in `serverless.yml` is filled from this file. The bucket name must be unique in all of AWS, and the same name is used for the bucket, the IAM rule and the S3 permission. Things that can go wrong: a missing value (clear error naming it), or a `.env.dev` that contains the MinIO access key (then `deploy` fails with an invalid-key error).

### Step 4: package

```powershell
npx serverless package
```

Expected: `✔ Service packaged`. Then check:

```powershell
dir .serverless
```

You should see `loan-eligibility-engine.zip` and `cloudformation-template-update-stack.json`.

**What this does:** It builds the zip (your `lambdas/` folder plus `psycopg2-binary` and `python-dotenv` from `requirements-lambda.txt`) and the CloudFormation template, without touching AWS. The pip options select the Linux x86_64 Python 3.11 wheels while running on Windows. Things that can go wrong: a missing compatible wheel or a network failure while pip downloads it.

**Phase 7 acceptance is done when this step succeeds.**

## 4. Part B (bonus): deploy to AWS

### Step 1: AWS access

Create an IAM user (or use SSO) with permissions for CloudFormation, Lambda, S3, API Gateway, IAM roles and logs, and run once:

```powershell
aws configure --profile loan
```

Then:

```powershell
$env:AWS_PROFILE = "loan"
```

Make sure `.env.dev` does **not** contain `AWS_ACCESS_KEY_ID` (it would override the profile).

### Step 2: database

Make a small RDS PostgreSQL instance (console: RDS → Create database → PostgreSQL → Free tier template, **Public access: Yes**, security group allows inbound 5432 from your IP and from n8n). Load the schema once:

```powershell
psql -h <rds-endpoint> -U loan_user -d loan_db -f db/schema.sql
psql -h <rds-endpoint> -U loan_user -d loan_db -f db/seed_products.sql
```

Put the endpoint in `.env.dev` as `POSTGRES_HOST`.

### Step 3: n8n must be reachable

The parser Lambda calls n8n from the internet, so `N8N_WEBHOOK_URL` must be a public address (for example a tunnel to `localhost:5678`, or n8n on a server). In n8n, change the **Postgres credential** to the same RDS host, so the workflows read the users the Lambda saved.

### Step 4: deploy

```powershell
npx serverless deploy
```

Copy `PresignUrl` and the bucket name from the output.

### Step 5: test

1. Open `ui/index.html` through `python scripts/local_server.py` (or any web host), expand **Settings**, paste `PresignUrl` into **API URL** and **untick Local mode**.
2. Upload `data/users.csv`.
3. The page says "Uploaded" and then "No status endpoint. Watch the n8n Executions page instead." (expected on AWS).
4. Check CloudWatch logs of the `parser` function, then `SELECT count(*) FROM users;` on RDS, then n8n Executions.

### Step 6: clean up (avoids cost)

```powershell
npx serverless remove
```

(Empty the bucket first if it contains files.) Delete the RDS instance in the console when finished.

## 5. Design choices

- **Bucket in `resources`, not in the S3 event shortcut:** it lets us set CORS, public-access block, lifecycle and the `uploads/` filter in one place.
- **`DependsOn` the permission:** S3 refuses to save the event setting if it is not allowed to call the Lambda yet.
- **Least privilege:** the role can touch only `uploads/*` of one bucket.
- **Secrets come from `.env.dev`:** simple, but values are visible in the Lambda settings. A stricter setup uses SSM Parameter Store (`${ssm:/loan-engine/postgres-password}`).
- **No VPC by default:** the Lambdas need internet access (S3, n8n webhook). A VPC would need a NAT gateway or endpoints.
- **Only two Lambdas:** the page's `/status` call has no AWS version. That is why the page falls back to "watch n8n".
- **`requirements-lambda.txt`:** keeps pytest and boto3 out of the zip (boto3 is already in the Lambda runtime).

## 6. Optional: VPC mode

Use it only if RDS is private. Add to `.env.dev`:

```
USE_VPC=on
VPC_SECURITY_GROUP_ID=sg-...
VPC_SUBNET_ID_1=subnet-...
VPC_SUBNET_ID_2=subnet-...
```

Then the Lambdas need a NAT gateway (to reach the n8n URL) and an S3 gateway endpoint (or the same NAT) to read S3.

## 7. Troubleshooting

| Problem | Likely cause and fix |
|---------|----------------------|
| "Cannot resolve variable ... env" | A value is missing in `.env.dev`. The message names it. |
| `.env` values are ignored | Stage is `dev`, so v3 reads `.env.dev` only. Put everything there (or deploy with `--stage prod` and a `.env.prod`). |
| Asked to log in to Serverless | You are on v4. Run `npm install` and use `npx serverless` from this folder (v3). |
| `spawn python ENOENT` / `python3.11 ENOENT` | Set `PYTHON_BIN=python3` (or `python`) in `.env.dev`. |
| Python requirements packaging error | Check Python 3.11 compatibility and network access to the Python package index. The config selects Linux x86_64 wheels directly. |
| Deploy: "InvalidClientTokenId" | Wrong keys. `.env.dev` must not hold the MinIO keys. Use `AWS_PROFILE`. |
| Deploy: bucket already exists | The name is taken in AWS. Pick a different `S3_BUCKET`. |
| Browser upload blocked (CORS) | Check the bucket CORS in the S3 console, and that the page sends `Content-Type: text/csv`. |
| `ImportModuleError` / `No module named 'psycopg2'` in logs | Inspect the zip to confirm the manylinux `psycopg2` package is present; rebuild with the configured Linux wheel options. |
| Parser runs but `webhook` fails | `N8N_WEBHOOK_URL` is not public. The batch is still saved (only a warning). |
| Parser times out connecting to RDS | RDS is not public or the security group blocks the Lambda. |

## 8. Acceptance test (from project.md)

- [ ] `npx serverless package` ends with `✔ Service packaged`.
- [ ] `.serverless/cloudformation-template-update-stack.json` contains `UploadBucket`, `ParserS3Permission`, `PresignLambdaFunction` and `ParserLambdaFunction`.
- [ ] `serverless.yml`, `package.json`, `requirements-lambda.txt` committed; `.gitignore` has `node_modules/`, `.serverless/`, `.env.*`.
- [ ] README (phase 8) will state that RDS is documented, not created.
- [ ] Bonus: `serverless deploy` works and a browser upload reaches RDS.

## 9. Three explain-it questions

1. **Why does S3 need a Lambda permission?** S3 is another AWS service calling your function. A Lambda only accepts calls from principals it allows. The permission names `s3.amazonaws.com` and one bucket ARN, so no other bucket or account can start the parser.
2. **Why is the IAM role limited to `uploads/*`?** Least privilege. If the Lambda code or its credentials leak, the damage is limited to one prefix of one bucket, not all your S3 data.
3. **Why are the Lambdas not in a VPC by default, and what does RDS need?** They must reach S3 and the public n8n URL; inside a VPC that needs a NAT gateway (cost and setup). For a demo, a public RDS with a restricted security group is simpler. A private RDS needs the optional VPC mode plus NAT.

## 10. Decisions to log (paste into `memory.md` → "Decisions")

- Serverless Framework **v3** (`frameworkVersion: '3'`, no login) plus `serverless-python-requirements`. `package.json` added at repo root.
- Deploy values come from **`.env.dev`** (v3 reads `.env.{stage}` instead of `.env` when it exists). This keeps real AWS keys away from the MinIO keys in `.env`. `.env.*` is git-ignored.
- `requirements-lambda.txt` (psycopg2-binary, python-dotenv only) is used for the Lambda zip; pip selects manylinux x86_64 wheels for Python 3.11 without Docker.
- Bucket, CORS, `uploads/` event, lifecycle (30 days) and the Lambda permission are in `resources`, not the `s3` event shortcut.
- Lambda env uses the same names as `.env`, without `AWS_*` and with `S3_ENDPOINT_URL` empty.
- RDS is NOT provisioned (documented). Optional VPC switch via `USE_VPC=on`.
- Handler names are set in `custom.presignHandler` / `custom.parserHandler` (`.lambda_handler` assumed; check them).
- New optional env names for deploy only: `PYTHON_BIN`, `DOCKERIZE_PIP`, `USE_VPC`, `VPC_SECURITY_GROUP_ID`, `VPC_SUBNET_ID_1`, `VPC_SUBNET_ID_2`.

## 11. Text to paste into `memory.md`

```
## Phase 7 — DONE (serverless.yml)   [mark DONE only after `npx serverless package` succeeds on your machine]
- Files: serverless.yml, package.json, requirements-lambda.txt, instruction7.md
- Creates: presign Lambda (HTTP API GET /presign), parser Lambda (S3 event on uploads/), S3 bucket with CORS, IAM role, outputs
- RDS: documented, not created
- Result: `npx serverless package` → ✔ Service packaged; deploy <done / not tried>
- Decisions: see instruction7.md section 10
- NEXT: Phase 8 — README with Mermaid diagram, real funnel numbers, limitations
```
