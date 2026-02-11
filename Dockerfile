FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Install dependencies first (cached unless lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

# Copy source and install the project itself
COPY README.md ./
COPY src/ src/
RUN uv sync --no-dev --frozen --no-editable


FROM python:3.13-slim-bookworm

# Real-time log output
ENV PYTHONUNBUFFERED=1

# Non-root user
RUN groupadd --system appuser && useradd --system --gid appuser appuser

# Copy the virtualenv from the builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import varaosabotti"]

USER appuser

ENTRYPOINT ["varaosabotti"]
