#!/bin/bash

set -e  # Exit on any error

# Logging function
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

log_debug() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEBUG] $1"
}

log_info "=== Speech-to-Phrase Validator Starting ==="

# Read configuration from options.json (Home Assistant addon config)
CONFIG_PATH="/data/options.json"
log_debug "Looking for config at: $CONFIG_PATH"

# Parse configuration with fallback defaults
if [ -f "$CONFIG_PATH" ]; then
    log_info "Found configuration file"
    log_debug "Config content: $(cat $CONFIG_PATH)"

    LOG_LEVEL=$(jq -r '.log_level // "info"' "$CONFIG_PATH" 2>/dev/null || echo "info")
    MODELS_PATH=$(jq -r '.speech_to_phrase_models_path // "/share/speech-to-phrase/models"' "$CONFIG_PATH" 2>/dev/null || echo "/share/speech-to-phrase/models")
    TRAIN_PATH=$(jq -r '.speech_to_phrase_train_path // "/share/speech-to-phrase/train"' "$CONFIG_PATH" 2>/dev/null || echo "/share/speech-to-phrase/train")
    TOOLS_PATH=$(jq -r '.speech_to_phrase_tools_path // "/share/speech-to-phrase/tools"' "$CONFIG_PATH" 2>/dev/null || echo "/share/speech-to-phrase/tools")
    ENABLE_CLI=$(jq -r '.enable_cli // false' "$CONFIG_PATH" 2>/dev/null || echo "false")
else
    log_info "No config file found, using defaults"
    LOG_LEVEL="info"
    MODELS_PATH="/share/speech-to-phrase/models"
    TRAIN_PATH="/share/speech-to-phrase/train"
    TOOLS_PATH="/share/speech-to-phrase/tools"
    ENABLE_CLI="false"
fi

log_info "Configuration loaded successfully:"
log_info "  Log Level: ${LOG_LEVEL}"
log_info "  Models path: ${MODELS_PATH}"
log_info "  Train path: ${TRAIN_PATH}"
log_info "  Tools path: ${TOOLS_PATH}"
log_info "  CLI enabled: ${ENABLE_CLI}"

# Check if speech-to-phrase directories exist
log_info "Checking Speech-to-Phrase directories..."
if [ -d "${MODELS_PATH}" ]; then
    log_info "✓ Found Speech-to-Phrase models directory"
    MODEL_COUNT=$(find "${MODELS_PATH}" -maxdepth 1 -type d | wc -l)
    log_info "  Found $((MODEL_COUNT - 1)) model directories"
else
    log_error "✗ Speech-to-Phrase models directory not found at ${MODELS_PATH}"
    log_error "  Make sure Speech-to-Phrase addon is installed and configured"
fi

if [ -d "${TRAIN_PATH}" ]; then
    log_info "✓ Found Speech-to-Phrase train directory"
else
    log_info "! Train directory not found (will be created if needed): ${TRAIN_PATH}"
fi

if [ -d "${TOOLS_PATH}" ]; then
    log_info "✓ Found Speech-to-Phrase tools directory"
else
    log_info "! Tools directory not found: ${TOOLS_PATH}"
fi

# Set environment variables
log_info "Setting environment variables..."
export STP_MODELS_PATH="${MODELS_PATH}"
export STP_TRAIN_PATH="${TRAIN_PATH}"
export STP_TOOLS_PATH="${TOOLS_PATH}"
export STP_LOG_LEVEL="${LOG_LEVEL}"
export STP_ENABLE_CLI="${ENABLE_CLI}"

# Change to app directory
log_info "Changing to application directory: /app"
cd /app || {
    log_error "Failed to change to /app directory"
    exit 1
}

# Check Python and dependencies
log_info "Checking Python environment..."
python --version || {
    log_error "Python not found"
    exit 1
}

log_info "Checking application structure..."
if [ ! -d "src" ]; then
    log_error "src directory not found"
    exit 1
fi

if [ ! -f "src/api/app.py" ]; then
    log_error "app.py not found"
    exit 1
fi

# Test import
log_info "Testing application import..."
python -c "import src.api.app" 2>&1 || {
    log_error "Failed to import application"
    log_error "Python path contents:"
    python -c "import sys; print('\n'.join(sys.path))"
    exit 1
}

# Start the application
log_info "=== Starting Speech-to-Phrase Validator Web Interface ==="
log_info "Server will be available on port 8099"

# Use exec to replace the shell process with Python
exec python -m src.api.app 2>&1 || {
    log_error "Failed to start application"
    exit 1
}