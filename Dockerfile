ARG BUILD_FROM=ghcr.io/home-assistant/base:3.18
FROM $BUILD_FROM

# Force rebuild by changing this arg when needed
ARG BUILD_DATE=2024-09-20-v4
ARG BUILD_VERSION=1.0.2

# Set working directory
WORKDIR /app

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    curl \
    jq \
    bash \
    && rm -rf /var/cache/apk/*

# Create symlinks for compatibility
RUN ln -sf /usr/bin/python3 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY startup.py ./
COPY simple_server.py ./

# Create required directories
RUN mkdir -p /data /share

# Test installation
RUN python --version \
    && python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')" \
    && python -c "import uvicorn; print('Uvicorn OK')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1

# Expose port
EXPOSE 8099

# Use the startup script directly
CMD ["python", "/app/startup.py"]