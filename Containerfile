FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv package manager
RUN pip install uv

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    uv sync --frozen

# Install Playwright browsers
RUN .venv/bin/python -m playwright install --with-deps chromium

# Copy application files
COPY scraper.py app.py main.py ./

# Expose Flask port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run Flask app by default
CMD [".venv/bin/python", "app.py"]