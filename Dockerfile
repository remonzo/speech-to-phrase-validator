ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.20
FROM $BUILD_FROM

# Force rebuild by changing this arg when needed
ARG BUILD_DATE=2024-09-20-v13
ARG BUILD_VERSION=1.1.2

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

# Fix permissions for init and common binaries
RUN chmod +x /init /usr/bin/python3 /usr/bin/python /bin/bash /bin/sh || true

# Set working directory
WORKDIR /app

# Copy requirements and create virtual environment
COPY requirements.txt ./
RUN python3 -m venv /app/venv \
    && . /app/venv/bin/activate \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Add virtual environment to PATH
ENV PATH="/app/venv/bin:$PATH"

# Copy application files
COPY src/ ./src/
COPY startup.py ./
COPY simple_server.py ./

# Create required directories
RUN mkdir -p /data /share

# Create a simple wrapper script that uses the virtual environment
RUN echo '#!/bin/bash' > /app/run.sh \
    && echo 'source /app/venv/bin/activate' >> /app/run.sh \
    && echo 'exec python /app/startup.py "$@"' >> /app/run.sh \
    && chmod +x /app/run.sh

# Create symlink for HA to find Python in expected location
RUN ln -sf /app/venv/bin/python /usr/local/bin/python \
    && chmod +x /usr/local/bin/python

# Test installation in virtual environment
RUN . /app/venv/bin/activate \
    && python --version \
    && python -c "import fastapi; print('FastAPI OK')" \
    && python -c "import uvicorn; print('Uvicorn OK')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8099/api/health || exit 1

# Expose port
EXPOSE 8099

# Use bash directly to avoid tini issues
CMD ["/bin/bash", "/app/run.sh"]