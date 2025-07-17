# Multi-stage build for minimal M3 Docker image
FROM python:slim AS builder

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install build dependencies and M3
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Production stage - minimal runtime image
FROM python:slim

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash m3user

# Copy installed package from builder
COPY --from=builder /usr/local/lib/python*/site-packages /tmp/builder-packages
COPY --from=builder /usr/local/bin/m3 /usr/local/bin/m3
COPY --from=builder /usr/local/bin/m3-mcp-server /usr/local/bin/m3-mcp-server

# Move packages to correct Python version directory
RUN PYTHON_VERSION=$(python3 -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')") && \
    mkdir -p /usr/local/lib/$PYTHON_VERSION/site-packages && \
    cp -r /tmp/builder-packages/* /usr/local/lib/$PYTHON_VERSION/site-packages/ && \
    rm -rf /tmp/builder-packages

# Switch to non-root user
USER m3user
WORKDIR /home/m3user

# Create data directory
RUN mkdir -p /home/m3user/m3_data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD m3 --version || exit 1

# Default command
CMD ["m3", "--help"]