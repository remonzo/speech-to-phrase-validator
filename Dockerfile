ARG BUILD_FROM
FROM $BUILD_FROM

# Force rebuild by changing this arg when needed
ARG BUILD_DATE=2025-09-21-v28
ARG BUILD_VERSION=1.5.3

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

# Copy requirements and create virtual environment
COPY requirements.txt ./
RUN python3 -m venv /app/venv \
    && . /app/venv/bin/activate \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY startup.py ./
COPY simple_server.py ./

# Create required directories
RUN mkdir -p /data /share

# Test installation in virtual environment
RUN . /app/venv/bin/activate \
    && python --version \
    && python -c "import fastapi; print('FastAPI OK')" \
    && python -c "import uvicorn; print('Uvicorn OK')"

# Copy rootfs for s6 services with correct permissions
COPY rootfs /
RUN chmod +x /etc/services.d/speech-to-phrase-validator/run

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8099/api/health || exit 1

# Expose port
EXPOSE 8099

# Home Assistant manages the startup - no CMD needed