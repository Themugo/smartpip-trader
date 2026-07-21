FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r smartpip && useradd -r -g smartpip smartpip

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements
COPY requirements.txt .

# Install Python dependencies with security best practices
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir scikit-learn numpy

# Copy application
COPY . .

# Create data directory with proper permissions
RUN mkdir -p /app/data && \
    mkdir -p /app/logs && \
    chown -R smartpip:smartpip /app

# Security: Set ownership to non-root user
USER smartpip

# Security: Make filesystem read-only where possible
# Only /app/data and /tmp should be writable
RUN chmod -R 755 /app && \
    chmod -R 777 /app/data && \
    chmod -R 777 /app/logs

# Expose port (standardized to 8080 for containerized deployments)
EXPOSE 8080

# Security: Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run application with security considerations
# PORT is read from environment, defaults to 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --limit-concurrency 100"]
