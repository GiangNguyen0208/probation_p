FROM python:3.11-slim AS builder
WORKDIR /app
COPY social-common/ social-common/
COPY social-data-collector/ social-data-collector/
RUN pip install --no-cache-dir -e social-common -e social-data-collector

FROM python:3.11-slim
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/social-data-collector/src /app/social-data-collector/src
ENV PYTHONPATH=/app/social-data-collector/src:$PYTHONPATH
USER app
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -m social_data_collector.main health || exit 1
CMD ["celery", "-A", "social_data_collector.scheduler.celery_app", "worker", "--beat", "-l", "info"]
