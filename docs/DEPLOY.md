# Deploying hakigains to AWS (SAM)

Runs hakigains serverless: a **scheduled briefing** (EventBridge → Lambda) and an
**interactive bot** (Telegram webhook → Lambda Function URL). Both use a container image
(garminconnect + openai deps are too chunky for a clean zip) and share the same code as the
local scripts. Target region: **ap-southeast-1**.

> Status: scaffolding. The template + handler are written to be deployable but should be
> validated on first `sam deploy`. Nothing here runs your Garmin creds until you deploy.

## Prerequisites
- AWS CLI configured (`aws sts get-caller-identity` works), Docker running, AWS SAM CLI.
- A `config.yaml` present at the repo root (the Dockerfile bundles it).

## 1. Store secrets in Secrets Manager
One JSON secret holds everything the app reads from the environment:
```bash
aws secretsmanager create-secret --name hakigains/prod --region ap-southeast-1 \
  --secret-string '{
    "GARMIN_EMAIL": "...",
    "GARMIN_PASSWORD": "...",
    "AZURE_OPENAI_API_KEY": "...",
    "AZURE_OPENAI_ENDPOINT": "https://....openai.azure.com/",
    "AZURE_OPENAI_API_VERSION": "2024-12-01-preview",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "...",
    "TELEGRAM_BOT_TOKEN": "..."
  }'
```
The handler loads these into the environment at cold start.

## 2. Build & deploy
```bash
cd deploy/sam
sam build
sam deploy --guided \
  --region ap-southeast-1 \
  --parameter-overrides SecretName=hakigains/prod TelegramChatId=<your-chat-id>
```
`--guided` creates the ECR repo and saves choices to `samconfig.toml` (gitignored). Outputs
include **WebhookUrl** and **StateBucketName**.

## 3. Point Telegram at the webhook
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WebhookUrl>"
```
Now messages to the bot invoke `telegram_webhook` (still chat-ID gated).

## 4. First-run token note
The first briefing invocation logs into Garmin and writes the auth token; the handler then
uploads it to the **state S3 bucket** (`garth_token`). Subsequent invocations reuse it, so we
don't re-login every run (Garmin rate-limits logins). `settings.json` (from `/set`) is synced
the same way, so knob changes persist across cold starts.

## What the template provisions
- 2× Lambda (image): `ScheduledBriefingFunction` (EventBridge schedule, default 07:00 SGT)
  and `WebhookFunction` (Function URL, `AuthType: NONE` — the chat-ID gate is the guard).
- `StateBucket` (S3, all public access blocked) for the Garmin token + settings.
- IAM scoped to: read the one secret, read/write the state bucket.

## Switching the LLM to Bedrock later
The provider abstraction (`src/hakigains/llm/`) means moving off the temporary Azure key to
**Bedrock/Claude in this account** is a new `llm/` implementation + an IAM `bedrock:InvokeModel`
grant — closing the external egress. Set `LLM_PROVIDER=bedrock` once implemented.
