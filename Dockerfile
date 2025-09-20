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
COPY test_app.py ./

# Copy and fix permissions for shell scripts
COPY run.sh ./
COPY run_simple.sh ./
RUN chmod +x /app/run.sh /app/run_simple.sh

# Verify permissions and test execution
RUN ls -la /app/run*.sh
RUN test -x /app/run_simple.sh && echo "run_simple.sh is executable" || echo "run_simple.sh is NOT executable"
RUN test -r /app/run_simple.sh && echo "run_simple.sh is readable" || echo "run_simple.sh is NOT readable"

# Create directories
RUN mkdir -p /data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8099/api/health || exit 1

# Expose port
EXPOSE 8099

# Run with explicit bash to avoid permission issues
CMD ["bash", "/app/run_simple.sh"]