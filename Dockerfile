FROM python:3.11-alpine

# Force rebuild by changing this arg when needed
ARG BUILD_DATE=2024-09-20-v2
ARG BUILD_VERSION=1.0.0

# Set working directory early
WORKDIR /app

# Debug info
RUN echo "Building Speech-to-Phrase Validator v${BUILD_VERSION} on ${BUILD_DATE}"

# Install system dependencies
RUN apk add --no-cache \
    bash \
    curl \
    jq \
    && rm -rf /var/cache/apk/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY startup.py ./
COPY simple_server.py ./

# Create required directories
RUN mkdir -p /data /share

# Test Python execution
RUN python --version \
    && which python \
    && ls -la $(which python)

# Test our startup script
RUN python -c "print('Python test successful')"

# Set proper ownership and permissions
RUN chmod -R 755 /app \
    && chown -R root:root /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8099/health || exit 1

# Expose port
EXPOSE 8099

# Use absolute path for Python
CMD ["/usr/local/bin/python", "/app/startup.py"]