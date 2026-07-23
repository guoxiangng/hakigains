# Container image for both Lambda functions (garminconnect + openai deps are
# chunky, so a container beats a zip). The handler is selected per-function by
# SAM (handler.scheduled_briefing / handler.telegram_webhook).
FROM public.ecr.aws/lambda/python:3.12

# Deps (boto3 is present in the Lambda runtime, but pin it for local `sam` parity).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt boto3

# App package (src/hakigains -> /var/task/hakigains) + handler + profile.
COPY src/ ${LAMBDA_TASK_ROOT}/
COPY deploy/lambda/handler.py ${LAMBDA_TASK_ROOT}/
# Requires config.yaml to exist at build time (create it from config.example.yaml).
COPY config.yaml ${LAMBDA_TASK_ROOT}/config.yaml

CMD ["handler.scheduled_briefing"]
