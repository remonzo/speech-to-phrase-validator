FROM python:3.11-alpine

# Force rebuild by changing this arg when needed
ARG BUILD_DATE=2024-09-20-v6
ARG BUILD_VERSION=1.0.4

# Install system dependencies
RUN apk add --no-cache \
    curl \
    jq \
    bash \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY startup.py ./
COPY simple_server.py ./

# Create required directories with proper permissions
RUN mkdir -p /data /share \
    && chmod 755 /data /share

# Test installation
RUN python --version \
    && python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')" \
    && python -c "import uvicorn; print('Uvicorn OK')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1

# Expose port
EXPOSE 8099

# Start the application
CMD ["python", "/app/startup.py"]