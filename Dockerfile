# syntax=docker/dockerfile:1

# Build stage: create wheel
FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Base runtime: install m3 and baked SQLite DB
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    M3_BACKEND=sqlite \
    M3_DB_PATH=/root/m3_data/databases/mimic_iv_demo.db

WORKDIR /app

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Download and initialize demo DB using m3 init
RUN m3 init mimic-iv-demo

# Lite: SQLite only
FROM base AS lite
ENV MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=3000 \
    MCP_PATH=/sse
EXPOSE 3000
CMD ["python", "-m", "m3.mcp_server"]

# BigQuery: add GCP client
FROM base AS bigquery
RUN pip install --no-cache-dir google-cloud-bigquery
ENV MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=3000 \
    MCP_PATH=/sse
EXPOSE 3000
CMD ["python", "-m", "m3.mcp_server"]
