# M3 Docker Guide

This guide explains how to run M3 (MIMIC-IV + MCP + Models) in Docker containers for both SQLite and BigQuery backends.

## Quick Start

### Build the Docker Image

```bash
docker build -t m3:latest .
```

**Image Size**: ~936MB (optimized multi-stage build)

### Run with SQLite Backend (Demo Data)

```bash
# Create a data volume
docker volume create m3-data

# Run M3 CLI to initialize demo database
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 init mimic-iv-demo

# Start MCP server
docker run -d \
  --name m3-sqlite \
  -v m3-data:/home/m3user/m3_data \
  -p 8080:8080 \
  -e M3_BACKEND=sqlite \
  m3:latest m3-mcp-server
```

### Run with BigQuery Backend

```bash
# Create credentials directory
mkdir -p ./gcp-credentials

# Copy your service account key
cp /path/to/your/service-account.json ./gcp-credentials/

# Start MCP server
docker run -d \
  --name m3-bigquery \
  -v ./gcp-credentials:/app/credentials:ro \
  -p 8081:8080 \
  -e M3_BACKEND=bigquery \
  -e M3_PROJECT_ID=your-gcp-project-id \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json \
  m3:latest m3-mcp-server
```

## Using Docker Compose

### Setup

```bash
# Copy the environment file
cp .env.example .env

# Edit .env file
export GCP_PROJECT_ID=your-gcp-project-id
```

### Run Services

```bash
# Start SQLite service
docker-compose up -d m3-sqlite

# Start BigQuery service (requires GCP credentials)
docker-compose up -d m3-bigquery

# View logs
docker-compose logs -f m3-sqlite
```

## Common Commands

### CLI Operations

```bash
# Check version
docker run --rm m3:latest m3 --version

# View help
docker run --rm m3:latest m3 --help

# Initialize demo database
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 init mimic-iv-demo

# Configure MCP client
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 config --quick
```

### MCP Server Operations

```bash
# Start server with SQLite
docker run -d \
  --name m3-server \
  -v m3-data:/home/m3user/m3_data \
  -p 8080:8080 \
  m3:latest m3-mcp-server

# View server logs
docker logs -f m3-server

# Stop server
docker stop m3-server
```

## Environment Variables

### Common Variables

- `M3_BACKEND`: Backend type (`sqlite` or `bigquery`)
- `M3_PROJECT_ID`: Google Cloud project ID (BigQuery only)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON (BigQuery only)

### OAuth2 Variables (Optional)

- `M3_OAUTH2_ENABLED`: Enable OAuth2 authentication (`true`/`false`)
- `M3_OAUTH2_ISSUER_URL`: OAuth2 issuer URL
- `M3_OAUTH2_AUDIENCE`: JWT audience claim
- `M3_OAUTH2_TOKEN`: Bearer token for authentication

## Volume Mounts

### Data Persistence

```bash
# Named volume (recommended)
-v m3-data:/home/m3user/m3_data

# Bind mount
-v /host/path/to/data:/home/m3user/m3_data
```

### Configuration Files

```bash
# GCP credentials
-v ./gcp-credentials:/app/credentials:ro

# Custom configuration
-v ./config:/home/m3user/.config:ro
```

## Troubleshooting

### Common Issues

**Database not found error:**
```bash
# Initialize database first
docker run --rm -v m3-data:/home/m3user/m3_data m3:latest m3 init mimic-iv-demo
```

**SSL certificate issues:**
```bash
# Add trusted certificates
docker run --rm -v /etc/ssl/certs:/etc/ssl/certs:ro m3:latest m3 init mimic-iv-demo
```

**BigQuery authentication failure:**
```bash
# Check credentials mount
docker run --rm -v ./gcp-credentials:/app/credentials:ro m3:latest ls -la /app/credentials/

# Verify service account key
docker run --rm -v ./gcp-credentials:/app/credentials:ro m3:latest cat /app/credentials/service-account.json
```

### Health Checks

```bash
# Check container health
docker exec m3-server m3 --version

# Test MCP server endpoint
curl -f http://localhost:8080/health || echo "Server not responding"
```

## Security Considerations

### Non-Root User

The Docker image runs as a non-root user (`m3user`) for security:

```dockerfile
RUN useradd --create-home --shell /bin/bash m3user
USER m3user
```

### Read-Only Mounts

Mount sensitive files as read-only:

```bash
-v ./gcp-credentials:/app/credentials:ro
```

### Network Security

Use custom networks for production:

```bash
docker network create m3-network
docker run --network m3-network --name m3-server m3:latest
```

## Production Deployment

### Multi-Stage Build Optimization

The Dockerfile uses multi-stage builds to minimize image size:

- **Builder stage**: Installs build dependencies and compiles M3
- **Runtime stage**: Contains only runtime dependencies and M3 binaries
- **Final size**: ~936MB (includes Python 3.11 + all dependencies)

### Resource Limits

```bash
docker run \
  --memory=2g \
  --cpus=2 \
  --name m3-server \
  m3:latest m3-mcp-server
```

### Health Monitoring

```bash
# Built-in health check
docker run --health-cmd="m3 --version" m3:latest

# External monitoring
docker run -d \
  --name m3-server \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  m3:latest m3-mcp-server
```

## Development

### Building Custom Images

```bash
# Build with custom tag
docker build -t m3:dev .

# Build with build args
docker build --build-arg PYTHON_VERSION=3.12 -t m3:py312 .
```

### Development Mount

```bash
# Mount source code for development
docker run --rm \
  -v $(pwd)/src:/app/src \
  -v m3-data:/home/m3user/m3_data \
  m3:latest m3 --version
```