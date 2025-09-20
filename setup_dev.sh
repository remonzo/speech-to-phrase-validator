#!/bin/bash
# Script per setup ambiente di sviluppo

set -e

echo "🚀 Setup Speech-to-Phrase Validator Development Environment"
echo "=========================================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo "🐍 Python version: $python_version"

if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
    echo "❌ Python 3.8+ richiesto"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creazione virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Attivazione virtual environment..."
source venv/bin/activate || source venv/Scripts/activate

# Upgrade pip
echo "⬆️  Aggiornamento pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installazione dipendenze..."
pip install -r requirements.txt

# Create test directories
echo "📁 Creazione directory di test..."
mkdir -p test_data/models
mkdir -p test_data/train
mkdir -p test_data/tools

# Set environment variables
echo "🔧 Configurazione variabili ambiente..."
export STP_MODELS_PATH="$(pwd)/../speech-to-phrase"
export STP_TRAIN_PATH="$(pwd)/test_data/train"
export STP_TOOLS_PATH="$(pwd)/test_data/tools"
export STP_LOG_LEVEL="DEBUG"

# Test basic functionality
echo "🧪 Test funzionalità base..."
python3 test_local.py

echo ""
echo "✅ Setup completato!"
echo ""
echo "📋 Comandi utili:"
echo "  - Attiva ambiente: source venv/bin/activate"
echo "  - Avvia server: python -m src.api.app"
echo "  - Test: python test_local.py"
echo "  - URL locale: http://localhost:8099"
echo ""
echo "🔧 Variabili ambiente (aggiungi al tuo .bashrc/.zshrc):"
echo "  export STP_MODELS_PATH=\"$(pwd)/../speech-to-phrase\""
echo "  export STP_TRAIN_PATH=\"$(pwd)/test_data/train\""
echo "  export STP_TOOLS_PATH=\"$(pwd)/test_data/tools\""