# Fly.io Integration Plan for Electric

This document outlines a cost-optimized deployment strategy for the Electric FastAPI application on Fly.io.

## Executive Summary

**Estimated Monthly Cost: $2-5/month** (minimal usage scenario)

Fly.io offers a pay-as-you-go model with no free tier. This plan prioritizes cost minimization while maintaining production readiness through:
- Smallest viable machine configuration
- Auto-stop for idle periods
- SQLite with Fly Volumes (no external database costs)
- Shared IPv4 (avoiding $2/month dedicated IP fee)
- Single-region deployment

---

## Cost Analysis

### Fly.io Pricing Model (2025)

| Resource | Cost | Notes |
|----------|------|-------|
| Shared CPU (1x, 256MB) | ~$2.32/month | Full-time running |
| Shared CPU (1x, 256MB) | <$1/month | With auto-stop |
| Fly Volume (1GB) | $0.15/month | SQLite storage |
| Outbound Bandwidth | $0.02/GB | First 100GB |
| Dedicated IPv4 | $2/month | **Avoid** - use shared |
| Shared IPv4 | Free | Recommended |

### Cost Comparison: Fly.io vs Alternatives

| Provider | Estimated Monthly Cost | Notes |
|----------|----------------------|-------|
| **Fly.io (this plan)** | **$2-5** | Auto-stop + SQLite + shared IP |
| Fly.io (always-on + Postgres) | $15-25 | Managed Postgres adds ~$15 |
| Railway | $5-20 | Usage-based, no free tier |
| Render | $7+ | Cheapest paid plan |
| Heroku | $7+ | Basic dyno |
| DigitalOcean App Platform | $5+ | Basic tier |

### Cost Optimization Strategies

1. **Auto-stop/Auto-start**: Machines automatically stop when idle (no requests for ~5 minutes). Billing is per-second, so a staging/low-traffic app pays only for active time.

2. **SQLite + Fly Volumes**: Eliminates managed database costs ($15-20/month saved). Suitable for single-instance deployments with low-medium traffic.

3. **Shared IPv4**: Fly.io provides free shared IPv4 via anycast. Dedicated IPv4 costs $2/month - avoid unless specifically needed.

4. **Single Region**: Start with one region (e.g., `iad` - Virginia, US). Multi-region adds cost without benefit for low-traffic apps.

5. **Right-sized Machine**: Start with `shared-cpu-1x` and 256MB RAM. FastAPI/Uvicorn is lightweight and handles this well.

---

## Implementation Plan

### Phase 1: Core Deployment Files

#### 1.1 Dockerfile (Multi-stage with uv)

```dockerfile
# syntax=docker/dockerfile:1

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (production only)
RUN uv sync --frozen --no-dev --no-editable

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key optimizations:**
- Multi-stage build reduces image size
- `python:3.11-slim` base (smaller than full image)
- Uses `uv` for fast dependency installation
- Non-root user for security
- Built-in health check

#### 1.2 .dockerignore

```
# Git
.git/
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
.uv/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/

# Local database
*.db
*.sqlite
*.sqlite3

# Environment files
.env
.env.*

# Documentation
docs/
*.md
!README.md

# CI/CD
.github/

# Misc
*.log
logs/
```

#### 1.3 fly.toml Configuration

```toml
# fly.toml - Fly.io application configuration

app = "electric-api"
primary_region = "iad"  # US East (Virginia) - good latency, competitive pricing

[build]
  dockerfile = "Dockerfile"

[env]
  # Non-sensitive environment variables
  PROJECT_NAME = "Electric"
  HOST = "0.0.0.0"
  PORT = "8000"
  DEBUG = "false"
  # DATABASE_URL is set dynamically based on volume mount
  # SECRET_KEY must be set via `fly secrets set`

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"      # Key cost optimization
  auto_start_machines = true
  min_machines_running = 0         # Allow all machines to stop
  processes = ["app"]

  [http_service.concurrency]
    type = "requests"
    hard_limit = 250
    soft_limit = 200

[http_service.checks]
  [http_service.checks.health]
    interval = "30s"
    timeout = "5s"
    grace_period = "10s"
    method = "GET"
    path = "/api/health"

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
  cpus = 1

[mounts]
  source = "electric_data"
  destination = "/data"
  initial_size = "1gb"

# Processes (single process for now)
[processes]
  app = "uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

**Cost-saving configurations:**
- `auto_stop_machines = "stop"` - Stops idle machines
- `min_machines_running = 0` - All machines can stop when idle
- `size = "shared-cpu-1x"` - Smallest machine type
- `memory = "256mb"` - Minimal memory
- Single region (`iad`)
- 1GB volume (expandable later)

### Phase 2: Application Modifications

#### 2.1 Database Configuration Update

Update `app/core/config.py` to support Fly Volumes:

```python
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with Fly.io support."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    PROJECT_NAME: str = "Electric"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database - defaults to Fly Volume path if /data exists
    DATABASE_URL: str = (
        "sqlite:////data/electric.db"
        if os.path.isdir("/data")
        else "sqlite:///./electric.db"
    )

    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()
```

#### 2.2 Production-Ready Uvicorn Settings

For production, consider adding `app/core/server.py`:

```python
"""Uvicorn server configuration for production."""

import os


def get_uvicorn_config() -> dict:
    """Get Uvicorn configuration based on environment."""
    is_production = os.getenv("DEBUG", "true").lower() == "false"

    config = {
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", 8000)),
        "workers": 1,  # Single worker for shared-cpu-1x
    }

    if is_production:
        config.update({
            "access_log": True,
            "log_level": "info",
        })
    else:
        config.update({
            "reload": True,
            "log_level": "debug",
        })

    return config
```

### Phase 3: CI/CD Deployment

#### 3.1 GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Fly.io

on:
  push:
    branches:
      - main
  workflow_dispatch:  # Allow manual deployment

env:
  FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync

      - name: Run checks
        run: uv run poe check

  deploy:
    name: Deploy to Fly.io
    runs-on: ubuntu-latest
    needs: test
    # Only deploy on main branch
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Setup Fly.io CLI
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy to Fly.io
        run: flyctl deploy --remote-only
```

#### 3.2 Required GitHub Secrets

| Secret | Description | How to Obtain |
|--------|-------------|---------------|
| `FLY_API_TOKEN` | Fly.io API token | `flyctl tokens create deploy` |

---

## Deployment Instructions

### Initial Setup (One-time)

```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. Login to Fly.io
fly auth login

# 3. Create the application (from project root)
fly launch --no-deploy
# Answer prompts:
# - App name: electric-api (or your choice)
# - Region: iad (or nearest)
# - Postgres: No
# - Redis: No

# 4. Create the volume for SQLite
fly volumes create electric_data --region iad --size 1

# 5. Set production secrets
fly secrets set SECRET_KEY="$(openssl rand -hex 32)"

# 6. Deploy
fly deploy

# 7. Check deployment
fly status
fly logs
```

### Subsequent Deployments

```bash
# Manual deployment
fly deploy

# Or push to main branch for automatic deployment via GitHub Actions
git push origin main
```

### Useful Commands

```bash
# View logs
fly logs

# SSH into machine
fly ssh console

# Check app status
fly status

# Scale (if needed later)
fly scale count 2  # Add second instance
fly scale memory 512  # Increase memory

# View costs
fly billing  # Requires billing configured

# Open app in browser
fly open
```

---

## Security Considerations

### Required for Production

1. **SECRET_KEY**: Generate a strong secret key
   ```bash
   fly secrets set SECRET_KEY="$(openssl rand -hex 32)"
   ```

2. **HTTPS**: Enforced by `force_https = true` in fly.toml

3. **Non-root User**: Dockerfile creates `appuser`

4. **Secrets Management**: Use `fly secrets` for sensitive data, never commit to git

### Recommended Additions

1. **Rate Limiting**: Add slowapi or similar
2. **CORS**: Configure for your frontend domain
3. **Logging**: Consider Fly.io's log shipping to external service
4. **Monitoring**: Fly.io provides basic metrics; consider adding Sentry for errors

---

## Scaling Strategy

### When to Scale

| Metric | Action |
|--------|--------|
| Response time > 500ms | Increase memory to 512MB |
| CPU consistently > 80% | Upgrade to `shared-cpu-2x` |
| Need high availability | Add second machine (`fly scale count 2`) |
| Need multi-region | Add regions (`fly scale count 2 --region lhr`) |
| SQLite write contention | Migrate to Fly Postgres |

### Cost Impact of Scaling

| Configuration | Estimated Monthly Cost |
|--------------|----------------------|
| 1x shared-cpu-1x, 256MB, auto-stop | $2-5 |
| 1x shared-cpu-1x, 512MB, always-on | $5-7 |
| 2x shared-cpu-1x, 256MB, always-on | $5-10 |
| 1x shared-cpu-2x, 512MB | $8-12 |
| + Fly Postgres (1GB) | +$15-20 |

---

## Migration Path: SQLite to Postgres

If/when the application outgrows SQLite:

```bash
# 1. Create Fly Postgres cluster
fly postgres create --name electric-db --region iad --vm-size shared-cpu-1x

# 2. Attach to app (sets DATABASE_URL automatically)
fly postgres attach electric-db

# 3. Export data from SQLite and import to Postgres
# (Custom migration script needed)

# 4. Update DATABASE_URL or remove SQLite config
fly secrets set DATABASE_URL="postgres://..."

# 5. Deploy
fly deploy
```

---

## File Checklist

Files to create for Fly.io deployment:

| File | Status | Purpose |
|------|--------|---------|
| `Dockerfile` | To create | Multi-stage build for production |
| `.dockerignore` | To create | Exclude unnecessary files from image |
| `fly.toml` | To create | Fly.io app configuration |
| `.github/workflows/deploy.yml` | To create | Automated deployment |
| `app/core/config.py` | To modify | Fly Volumes database path |

---

## Implementation Tasks

### Priority 1: Core Deployment (Estimated effort: 2-3 hours)
- [ ] Create Dockerfile
- [ ] Create .dockerignore
- [ ] Create fly.toml
- [ ] Modify config.py for Fly Volumes support
- [ ] Test local Docker build

### Priority 2: CI/CD (Estimated effort: 1-2 hours)
- [ ] Create deploy.yml workflow
- [ ] Configure FLY_API_TOKEN secret in GitHub
- [ ] Test deployment pipeline

### Priority 3: Production Hardening (Estimated effort: 1-2 hours)
- [ ] Add rate limiting
- [ ] Configure CORS
- [ ] Set up error monitoring (Sentry)
- [ ] Add request logging

### Priority 4: Documentation (Estimated effort: 30 minutes)
- [ ] Update README with deployment instructions
- [ ] Document environment variables
- [ ] Add troubleshooting guide

---

## References

- [Fly.io Pricing](https://fly.io/pricing/)
- [Fly.io FastAPI Guide](https://fly.io/docs/python/frameworks/fastapi/)
- [Fly.io Cost Management](https://fly.io/docs/about/cost-management/)
- [Fly.io Volumes](https://fly.io/docs/volumes/)
- [FastAPI Docker Best Practices](https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/)

---

## Summary

This plan provides a **$2-5/month** deployment strategy for Electric on Fly.io by:

1. Using the smallest viable machine (`shared-cpu-1x`, 256MB)
2. Enabling auto-stop for idle periods
3. Using SQLite with Fly Volumes instead of managed Postgres
4. Using shared IPv4 (free) instead of dedicated ($2/month)
5. Single-region deployment
6. Automated CI/CD via GitHub Actions

The architecture is designed to scale when needed while keeping costs minimal for low-to-medium traffic scenarios.
