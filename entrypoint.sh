#!/bin/sh

echo "=== Speech-to-Phrase Validator Entrypoint ==="
echo "Checking environment..."

# Debug info
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Python executable: $(which python)"
echo "Python permissions: $(ls -la $(which python))"

# Try to fix Python permissions if needed
if [ ! -x "$(which python)" ]; then
    echo "Python not executable, trying to fix..."
    chmod +x $(which python) || echo "Failed to fix Python permissions"
fi

# Try different ways to start Python
echo "Attempting to start application..."

if command -v python3 >/dev/null 2>&1; then
    echo "Using python3..."
    exec python3 /app/startup.py
elif command -v python >/dev/null 2>&1; then
    echo "Using python..."
    exec python /app/startup.py
else
    echo "No Python found, trying direct execution..."
    exec /usr/local/bin/python /app/startup.py
fi