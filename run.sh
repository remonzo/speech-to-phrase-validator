#!/bin/bash

# Get configuration from bashio if available, otherwise use defaults
if command -v bashio >/dev/null 2>&1; then
    LOG_LEVEL=$(bashio::config 'log_level' 'info')
    MODELS_PATH=$(bashio::config 'speech_to_phrase_models_path' '/share/speech-to-phrase/models')
    TRAIN_PATH=$(bashio::config 'speech_to_phrase_train_path' '/share/speech-to-phrase/train')
    TOOLS_PATH=$(bashio::config 'speech_to_phrase_tools_path' '/share/speech-to-phrase/tools')
    ENABLE_CLI=$(bashio::config 'enable_cli' 'false')
else
    # Fallback defaults if bashio not available
    LOG_LEVEL="${LOG_LEVEL:-info}"
    MODELS_PATH="${MODELS_PATH:-/share/speech-to-phrase/models}"
    TRAIN_PATH="${TRAIN_PATH:-/share/speech-to-phrase/train}"
    TOOLS_PATH="${TOOLS_PATH:-/share/speech-to-phrase/tools}"
    ENABLE_CLI="${ENABLE_CLI:-false}"
fi

# Logging function
log_info() {
    echo "[INFO] $1"
}

log_warning() {
    echo "[WARNING] $1"
}

log_info "Starting Speech-to-Phrase Validator..."
log_info "Models path: ${MODELS_PATH}"
log_info "Train path: ${TRAIN_PATH}"
log_info "Tools path: ${TOOLS_PATH}"

# Check if speech-to-phrase directories exist
if [ -d "${MODELS_PATH}" ]; then
    log_info "Found Speech-to-Phrase models directory"
else
    log_warning "Speech-to-Phrase models directory not found at ${MODELS_PATH}"
    log_warning "Make sure Speech-to-Phrase addon is installed and configured"
fi

# Set environment variables
export STP_MODELS_PATH="${MODELS_PATH}"
export STP_TRAIN_PATH="${TRAIN_PATH}"
export STP_TOOLS_PATH="${TOOLS_PATH}"
export STP_LOG_LEVEL="${LOG_LEVEL}"
export STP_ENABLE_CLI="${ENABLE_CLI}"

# Change to app directory
cd /app

# Start the application
log_info "Starting Speech-to-Phrase Validator web interface..."
exec python -m src.api.app