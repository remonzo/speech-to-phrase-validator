#!/usr/bin/with-bashio

# ==============================================================================
# Speech-to-Phrase Validator Add-on for Home Assistant
# ==============================================================================

bashio::log.info "Starting Speech-to-Phrase Validator..."

# Check if virtual environment exists
if [[ ! -d "/app/venv" ]]; then
    bashio::log.error "Virtual environment not found at /app/venv"
    exit 1
fi

# Activate virtual environment
bashio::log.info "Activating Python virtual environment..."
source /app/venv/bin/activate

# Check if startup script exists
if [[ ! -f "/app/startup.py" ]]; then
    bashio::log.error "Startup script not found at /app/startup.py"
    exit 1
fi

# Log environment information
bashio::log.info "Python version: $(python --version)"
bashio::log.info "Current directory: $(pwd)"
bashio::log.info "Virtual environment: $VIRTUAL_ENV"

# Add application directory to Python path
export PYTHONPATH="/app/src:$PYTHONPATH"

# Start the application
bashio::log.info "Starting Speech-to-Phrase Validator application..."
cd /app
exec python startup.py