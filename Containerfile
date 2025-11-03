FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install uv package manager and clean pip cache
RUN pip install --no-cache-dir uv

# Copy application source before installing
COPY src/ ./src/
COPY web_server.py ./

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    uv sync --frozen && \
    find /app/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /home/appuser /app

USER appuser

# Expose Flask port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Run Flask app with gunicorn production server
CMD [".venv/bin/gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "dealradar.web.app:create_app()"]