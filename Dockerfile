ARG BUILD_FROM=ghcr.io/home-assistant/base:3.18
FROM $BUILD_FROM

# Force rebuild by changing this arg when needed
ARG BUILD_DATE=2024-09-20-v8
ARG BUILD_VERSION=1.0.7

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    curl \
    jq \
    bash \
    && rm -rf /var/cache/apk/*

# Create symlinks for Python
RUN ln -sf /usr/bin/python3 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY startup.py ./
COPY simple_server.py ./

# Create required directories
RUN mkdir -p /data /share

# Create a simple wrapper script that bypasses tini issues
RUN echo '#!/bin/bash' > /app/run.sh \
    && echo 'exec python3 /app/startup.py "$@"' >> /app/run.sh \
    && chmod +x /app/run.sh

# Test installation
RUN python3 --version \
    && python3 -c "import fastapi; print('FastAPI OK')" \
    && python3 -c "import uvicorn; print('Uvicorn OK')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1

# Expose port
EXPOSE 8099

# Use bash directly to avoid tini issues
CMD ["/bin/bash", "/app/run.sh"]