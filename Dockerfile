# ── NewsLet v3.0 — Production Dockerfile ─────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Let <newslet@app>"
LABEL description="NewsLet — Professional news aggregation & distribution system"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create required directories
RUN mkdir -p logs data seeds

# Make DB directory writable
RUN chmod -R 755 /app

EXPOSE 8000

# Health check (uses $PORT with fallback)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import httpx,os; httpx.get(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/api/v1/stats', timeout=5)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
