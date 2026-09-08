FROM python:3.11-slim

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY static/ ./static/

# Install dependencies via uv
RUN uv sync --frozen || uv sync

# Expose port
EXPOSE 8000

# Environment defaults
ENV AGENT_MODE=fallback
ENV PYTHONUNBUFFERED=1

# Command to run server
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
