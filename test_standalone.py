#!/usr/bin/env python3
"""Test standalone per Speech-to-Phrase Validator senza Home Assistant."""

import os
import sys
import logging
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def create_mock_data():
    """Crea dati mock per il test."""
    print("📋 Creazione dati mock per test...")

    # Crea struttura directory mock
    base_dir = Path("mock_data")
    models_dir = base_dir / "models" / "en_US-rhasspy"
    train_dir = base_dir / "train" / "en_US-rhasspy"
    tools_dir = base_dir / "tools"

    # Crea directories
    for dir_path in [models_dir, train_dir, tools_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Crea file mock del modello Kaldi
    (models_dir / "model" / "model").mkdir(parents=True, exist_ok=True)
    (models_dir / "model" / "model" / "final.mdl").touch()
    (models_dir / "g2p.fst").touch()

    # Crea database lessico mock
    phones_dir = models_dir / "model" / "phones"
    phones_dir.mkdir(parents=True, exist_ok=True)

    # Crea un database SQLite mock con alcune parole
    import sqlite3
    db_path = phones_dir / "lexicon.db"
    conn = sqlite3.connect(str(db_path))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS word_phonemes (
            word TEXT,
            phonemes TEXT,
            pron_order INTEGER DEFAULT 0
        )
    """)

    # Inserisci alcune parole di esempio
    mock_words = [
        ("hello", "HH AH L OW", 0),
        ("world", "W ER L D", 0),
        ("test", "T EH S T", 0),
        ("casa", "K AA Z AH", 0),
        ("luce", "L UW CH EH", 0),
        ("cucina", "K UW CH IH N AH", 0),
        ("bagno", "B AA N Y OW", 0),
        ("soggiorno", "S OW JH OW R N OW", 0),
        ("camera", "K AH M EH R AH", 0),
        ("climatizzatore", "K L IY M AH T IH Z AH T OW R EH", 0),
    ]

    for word, phonemes, order in mock_words:
        conn.execute("INSERT INTO word_phonemes (word, phonemes, pron_order) VALUES (?, ?, ?)",
                    (word, phonemes, order))

    conn.commit()
    conn.close()

    print(f"✅ Database mock creato con {len(mock_words)} parole")
    print(f"📁 Struttura mock creata in: {base_dir.absolute()}")

    return str(models_dir.parent), str(train_dir.parent), str(tools_dir)

def test_validator():
    """Test del validator con dati mock."""
    try:
        from validator import SpeechToPhraseValidator

        # Crea dati mock
        models_path, train_path, tools_path = create_mock_data()

        print("\n🧪 Inizializzazione validator...")
        validator = SpeechToPhraseValidator(models_path, train_path, tools_path)

        # Test modelli
        models = validator.get_available_models()
        print(f"📊 Modelli trovati: {len(models)}")

        if not models:
            print("❌ Nessun modello trovato")
            return False

        # Test validazione parole
        test_words = ["hello", "test", "condizionatore", "climatizzatore", "luce"]

        print("\n🔍 Test validazione parole:")
        for word in test_words:
            result = validator.validate_word(word)
            status_icon = "✅" if result.is_known else "❌"
            print(f"  {status_icon} {word}: {result.status.value}")
            if result.pronunciations:
                print(f"    Pronuncia: [{' '.join(result.pronunciations[0])}]")
            if result.similar_words:
                similar = result.similar_words[0]
                print(f"    Simile: {similar[0]} ({similar[1]:.2f})")

        # Test entità
        print("\n🏠 Test validazione entità:")
        test_entities = ["luce_cucina", "climatizzatore_soggiorno", "test_device"]

        for entity in test_entities:
            result = validator.validate_entity_name(entity)
            status_icon = "✅" if result.overall_status.value == "known" else "⚠️" if result.overall_status.value == "guessed" else "❌"
            print(f"  {status_icon} {entity}: {result.overall_status.value}")
            print(f"    Parole: {len(result.words_results)} | Raccomandazioni: {len(result.recommendations)}")

        # Test statistiche
        print("\n📊 Statistiche modello:")
        stats = validator.get_model_statistics()
        if stats:
            print(f"  Parole nel lessico: {stats.get('total_words', 'N/A')}")
            print(f"  Tipo modello: {stats.get('model_type', 'N/A')}")
            print(f"  G2P disponibile: {stats.get('has_g2p_model', False)}")

        return True

    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_server():
    """Avvia il server per test."""
    print("\n🌐 Avvio server di test...")

    # Configura environment
    models_path, train_path, tools_path = create_mock_data()

    os.environ["STP_MODELS_PATH"] = models_path
    os.environ["STP_TRAIN_PATH"] = train_path
    os.environ["STP_TOOLS_PATH"] = tools_path
    os.environ["STP_LOG_LEVEL"] = "INFO"

    print(f"🔧 Models: {models_path}")
    print(f"🔧 Train: {train_path}")
    print(f"🔧 Tools: {tools_path}")

    try:
        import uvicorn
        from api.app import app

        print("\n🚀 Avvio server su http://localhost:8099")
        print("📋 Test in browser:")
        print("  - Pagina principale: http://localhost:8099")
        print("  - Health check: http://localhost:8099/api/health")
        print("  - Modelli: http://localhost:8099/api/models")
        print("\n⏹️  Premi Ctrl+C per fermare")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8099,
            log_level="info"
        )

    except KeyboardInterrupt:
        print("\n👋 Server fermato")
    except Exception as e:
        print(f"❌ Errore server: {e}")

if __name__ == "__main__":
    print("🚀 Speech-to-Phrase Validator - Test Standalone")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        start_server()
    else:
        print("📋 Opzioni:")
        print("  python test_standalone.py        - Test funzionalità")
        print("  python test_standalone.py server - Avvia server web")
        print()

        success = test_validator()

        if success:
            print("\n🎉 Test completato con successo!")
            print("\n📋 Prossimi passi:")
            print("1. Test interfaccia web: python test_standalone.py server")
            print("2. Crea repository GitHub")
            print("3. Aggiungi repository in Home Assistant")
        else:
            print("\n⚠️ Test fallito - verifica la configurazione")