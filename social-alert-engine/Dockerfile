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
COPY --from=builder /app/social-alert-engine/migrations /app/social-alert-engine/migrations
COPY --from=builder /app/social-alert-engine/alembic.ini /app/social-alert-engine/alembic.ini
ENV PYTHONPATH=/app/social-alert-engine/src:$PYTHONPATH
USER app
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000')" || exit 1
CMD ["celery", "-A", "social_alert_engine.celery_app", "worker", "-l", "info"]
