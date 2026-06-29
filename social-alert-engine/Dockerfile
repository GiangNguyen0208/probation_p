FROM python:3.11-slim AS builder
WORKDIR /app
COPY social-common/ social-common/
COPY social-alert-engine/ social-alert-engine/
RUN pip install --no-cache-dir -e social-common -e social-alert-engine

FROM python:3.11-slim
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/social-alert-engine/src /app/social-alert-engine/src
ENV PYTHONPATH=/app/social-alert-engine/src:$PYTHONPATH
USER app
CMD ["social-alert-engine", "run-worker"]
