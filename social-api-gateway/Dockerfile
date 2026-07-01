FROM python:3.11-slim AS builder
WORKDIR /app
COPY social-common/ social-common/
COPY social-api-gateway/ social-api-gateway/
RUN pip install --no-cache-dir -e social-common -e social-api-gateway

FROM python:3.11-slim
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/social-api-gateway/src /app/social-api-gateway/src
COPY --from=builder /app/social-api-gateway/migrations /app/social-api-gateway/migrations
COPY --from=builder /app/social-api-gateway/alembic.ini /app/social-api-gateway/alembic.ini
ENV PYTHONPATH=/app/social-api-gateway/src:$PYTHONPATH
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health')" || exit 1
CMD ["uvicorn", "social_api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
