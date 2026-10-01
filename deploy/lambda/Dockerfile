# Container image for both Lambda functions (garminconnect + anthropic deps are
# chunky, so a container beats a zip). The handler is selected per-function by
# SAM (handler.scheduled_briefing / handler.telegram_webhook).
FROM public.ecr.aws/lambda/python:3.12

# Deps (the runtime's bundled boto3 predates the AgentCore Memory API we use, so
# requirements.txt pins a newer one).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App package (src/hakigains -> /var/task/hakigains) + handler + profile.
COPY src/ ${LAMBDA_TASK_ROOT}/
COPY deploy/lambda/handler.py ${LAMBDA_TASK_ROOT}/
# Requires config.yaml to exist at build time (create it from config.example.yaml).
COPY config.yaml ${LAMBDA_TASK_ROOT}/config.yaml

CMD ["handler.scheduled_briefing"]
