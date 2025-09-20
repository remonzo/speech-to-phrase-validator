FROM python:3.11-alpine

# Install minimal system dependencies
RUN apk add --no-cache \
    bash \
    curl \
    jq

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run.sh ./
COPY run_simple.sh ./
COPY test_app.py ./
RUN chmod +x run.sh run_simple.sh

# Create directories
RUN mkdir -p /data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8099/api/health || exit 1

# Expose port
EXPOSE 8099

# Run
CMD ["./run_simple.sh"]