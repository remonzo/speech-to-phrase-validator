#!/usr/bin/with-contenv bashio

# Get configuration
LOG_LEVEL=$(bashio::config 'log_level')
MODELS_PATH=$(bashio::config 'speech_to_phrase_models_path')
TRAIN_PATH=$(bashio::config 'speech_to_phrase_train_path')
TOOLS_PATH=$(bashio::config 'speech_to_phrase_tools_path')
ENABLE_CLI=$(bashio::config 'enable_cli')

# Set log level
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "Starting Speech-to-Phrase Validator..."
bashio::log.info "Models path: ${MODELS_PATH}"
bashio::log.info "Train path: ${TRAIN_PATH}"
bashio::log.info "Tools path: ${TOOLS_PATH}"

# Check if speech-to-phrase directories exist
if bashio::fs.directory_exists "${MODELS_PATH}"; then
    bashio::log.info "Found Speech-to-Phrase models directory"
else
    bashio::log.warning "Speech-to-Phrase models directory not found at ${MODELS_PATH}"
    bashio::log.warning "Make sure Speech-to-Phrase addon is installed and configured"
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
bashio::log.info "Starting Speech-to-Phrase Validator web interface..."
exec python -m src.api.app