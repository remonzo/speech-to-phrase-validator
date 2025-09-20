ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.11-alpine3.18
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    sqlite \
    sqlite-dev \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY run.sh ./

# Make run script executable
RUN chmod a+x /app/run.sh

# Labels
LABEL \
  io.hass.version="VERSION" \
  io.hass.type="addon" \
  io.hass.name="Speech-to-Phrase Validator" \
  io.hass.description="Tool di validazione e ottimizzazione per Speech-to-Phrase" \
  io.hass.arch="armhf|aarch64|amd64|armv7|i386"

# Expose port
EXPOSE 8099

CMD ["/app/run.sh"]