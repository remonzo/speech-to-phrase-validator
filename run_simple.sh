#!/bin/bash

echo "=========================================="
echo "Speech-to-Phrase Validator Starting v0.2.0"
echo "=========================================="

# Always output to console so we can see logs
exec > >(tee /proc/1/fd/1) 2>&1

echo "Current working directory: $(pwd)"
echo "Contents of /app:"
ls -la /app/

echo "Contents of /app/src:"
ls -la /app/src/ || echo "src directory not found"

echo "Python version:"
python --version

echo "Python path:"
python -c "import sys; print('\n'.join(sys.path))"

# Test basic imports
echo "Testing basic imports..."
python -c "import fastapi; print('FastAPI OK')" || echo "FastAPI import failed"
python -c "import uvicorn; print('Uvicorn OK')" || echo "Uvicorn import failed"

# Set simple environment variables
export STP_MODELS_PATH="/share/speech-to-phrase/models"
export STP_TRAIN_PATH="/share/speech-to-phrase/train"
export STP_TOOLS_PATH="/share/speech-to-phrase/tools"
export STP_LOG_LEVEL="DEBUG"

echo "Environment variables set:"
echo "  STP_MODELS_PATH: $STP_MODELS_PATH"
echo "  STP_TRAIN_PATH: $STP_TRAIN_PATH"
echo "  STP_TOOLS_PATH: $STP_TOOLS_PATH"

echo "Checking directories:"
echo "  Models: $(ls -d $STP_MODELS_PATH 2>/dev/null && echo 'EXISTS' || echo 'NOT FOUND')"
echo "  Train: $(ls -d $STP_TRAIN_PATH 2>/dev/null && echo 'EXISTS' || echo 'NOT FOUND')"
echo "  Tools: $(ls -d $STP_TOOLS_PATH 2>/dev/null && echo 'EXISTS' || echo 'NOT FOUND')"

cd /app

echo "Attempting to start test application first..."
echo "Command: python test_app.py"

# Try the simple test app first
python test_app.py