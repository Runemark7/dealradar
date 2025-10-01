FROM python:3.12-slim

# Install only essential runtime dependencies for headless chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv package manager and clean pip cache
RUN pip install --no-cache-dir uv

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    uv sync --frozen && \
    find /app/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Install Playwright chromium and remove unnecessary files
RUN .venv/bin/python -m playwright install chromium && \
    find /root/.cache/ms-playwright -type f -name "*.log" -delete && \
    find /root/.cache/ms-playwright -type f -name "*.dmp" -delete

# Copy application files
COPY scraper.py app.py main.py ./

# Expose Flask port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run Flask app by default
CMD [".venv/bin/python", "app.py"]