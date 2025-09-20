#!/usr/bin/env python3
"""Script per testare Speech-to-Phrase Validator in locale."""

import os
import sys
import logging
from pathlib import Path

# Aggiungi il percorso src al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_functionality():
    """Test delle funzionalità base."""
    print("🧪 Testing Speech-to-Phrase Validator...")

    # Configura percorsi di test (usa percorsi del progetto speech-to-phrase)
    MODELS_PATH = os.getenv("STP_MODELS_PATH", "../speech-to-phrase")
    TRAIN_PATH = os.getenv("STP_TRAIN_PATH", "/tmp/stp-train")
    TOOLS_PATH = os.getenv("STP_TOOLS_PATH", "/tmp/stp-tools")

    print(f"📁 Models path: {MODELS_PATH}")
    print(f"📁 Train path: {TRAIN_PATH}")
    print(f"📁 Tools path: {TOOLS_PATH}")

    # Crea directory temporanee se necessarie
    Path(TRAIN_PATH).mkdir(exist_ok=True)
    Path(TOOLS_PATH).mkdir(exist_ok=True)

    try:
        from validator import SpeechToPhraseValidator

        print("✅ Importazione moduli riuscita")

        # Inizializza il validator
        validator = SpeechToPhraseValidator(MODELS_PATH, TRAIN_PATH, TOOLS_PATH)

        print("✅ Validator inizializzato")

        # Test modelli disponibili
        models = validator.get_available_models()
        print(f"📊 Modelli trovati: {len(models)}")

        for model in models:
            print(f"  - {model['id']} ({model['type']}, {model['language']})")

        if models:
            # Test validazione parola
            print("\n🔍 Test validazione parola...")
            result = validator.validate_word("test")
            print(f"  Parola 'test': {result.status.value}")
            print(f"  Riconosciuta: {result.is_known}")
            if result.pronunciations:
                print(f"  Pronuncia: {result.pronunciations[0]}")

            # Test validazione entità
            print("\n🏠 Test validazione entità...")
            entity_result = validator.validate_entity_name("test_entity")
            print(f"  Entità 'test_entity': {entity_result.overall_status.value}")
            print(f"  Parole analizzate: {len(entity_result.words_results)}")

            # Test statistiche
            print("\n📊 Test statistiche...")
            stats = validator.get_model_statistics()
            if stats:
                print(f"  Parole nel lessico: {stats.get('total_words', 'N/A')}")
                print(f"  Tipo modello: {stats.get('model_type', 'N/A')}")

        print("\n✅ Test completato con successo!")
        return True

    except ImportError as e:
        print(f"❌ Errore importazione: {e}")
        print("💡 Verifica che le dipendenze siano installate")
        return False
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        print(f"📍 Tipo errore: {type(e).__name__}")
        return False

def test_api_server():
    """Test del server API."""
    print("\n🌐 Test server API...")

    try:
        # Set environment variables
        os.environ.setdefault("STP_MODELS_PATH", "../speech-to-phrase")
        os.environ.setdefault("STP_TRAIN_PATH", "/tmp/stp-train")
        os.environ.setdefault("STP_TOOLS_PATH", "/tmp/stp-tools")
        os.environ.setdefault("STP_LOG_LEVEL", "INFO")

        from api.app import app

        print("✅ Server API importato correttamente")
        print("💡 Per avviare il server: python -m src.api.app")
        print("💡 Poi accedi a: http://localhost:8099")

        return True

    except Exception as e:
        print(f"❌ Errore server API: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("🚀 Speech-to-Phrase Validator - Test Suite")
    print("=" * 50)

    success = True

    # Test funzionalità base
    if not test_basic_functionality():
        success = False

    # Test server API
    if not test_api_server():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("🎉 Tutti i test sono passati!")
        print("\n📋 Prossimi passi:")
        print("1. Installa dipendenze: pip install -r requirements.txt")
        print("2. Avvia server: python -m src.api.app")
        print("3. Testa interfaccia web: http://localhost:8099")
    else:
        print("⚠️  Alcuni test sono falliti. Verifica la configurazione.")

    sys.exit(0 if success else 1)