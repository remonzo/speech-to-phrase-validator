#!/usr/bin/env python3
"""Script per avviare il server in modalità standalone."""

import os
import sys
import sqlite3
from pathlib import Path

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

    # Crea un database SQLite mock con parole italiane e inglesi
    db_path = phones_dir / "lexicon.db"
    if not db_path.exists():
        conn = sqlite3.connect(str(db_path))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS word_phonemes (
                word TEXT,
                phonemes TEXT,
                pron_order INTEGER DEFAULT 0
            )
        """)

        # Parole italiane e inglesi per test
        mock_words = [
            # Parole inglesi base
            ("hello", "HH AH L OW", 0),
            ("world", "W ER L D", 0),
            ("test", "T EH S T", 0),
            ("light", "L AY T", 0),
            ("air", "EH R", 0),

            # Parole italiane comuni per domotica
            ("casa", "K AA Z AH", 0),
            ("luce", "L UW CH EH", 0),
            ("luci", "L UW CH IY", 0),
            ("cucina", "K UW CH IH N AH", 0),
            ("bagno", "B AA N Y OW", 0),
            ("soggiorno", "S OW JH OW R N OW", 0),
            ("camera", "K AH M EH R AH", 0),
            ("salotto", "S AH L OW T T OW", 0),
            ("corridoio", "K OW R R IH D OY OW", 0),
            ("giardino", "JH AH R D IY N OW", 0),

            # Dispositivi comuni
            ("climatizzatore", "K L IY M AH T IH Z AH T OW R EH", 0),
            ("condizionatore", "K OW N D IH T S IY OW N AH T OW R EH", 0),
            ("termostato", "T EH R M OW S T AH T OW", 0),
            ("ventilatore", "V EH N T IH L AH T OW R EH", 0),
            ("riscaldamento", "R IH S K AH L D AH M EH N T OW", 0),
            ("televisore", "T EH L EH V IH Z OW R EH", 0),
            ("televisione", "T EH L EH V IH Z IY OW N EH", 0),
            ("stereo", "S T EH R EH OW", 0),
            ("speaker", "S P IY K ER", 0),
            ("altoparlante", "AH L T OW P AH R L AH N T EH", 0),

            # Verbi comuni
            ("accendi", "AH CH EH N D IY", 0),
            ("spegni", "S P EH N Y IY", 0),
            ("apri", "AA P R IY", 0),
            ("chiudi", "K IY UW D IY", 0),
            ("aumenta", "AH UW M EH N T AH", 0),
            ("diminuisci", "D IH M IH N UW IH SH IY", 0),
            ("regola", "R EH G OW L AH", 0),
        ]

        for word, phonemes, order in mock_words:
            conn.execute("INSERT INTO word_phonemes (word, phonemes, pron_order) VALUES (?, ?, ?)",
                        (word, phonemes, order))

        conn.commit()
        conn.close()
        print(f"✅ Database mock creato con {len(mock_words)} parole")

    print(f"📁 Struttura mock creata in: {base_dir.absolute()}")
    return str(models_dir.parent), str(train_dir.parent), str(tools_dir)

def main():
    """Avvia il server standalone."""
    print("🚀 Speech-to-Phrase Validator - Server Standalone")
    print("=" * 60)

    # Aggiungi src al path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))

    # Crea dati mock
    models_path, train_path, tools_path = create_mock_data()

    # Configura environment
    os.environ["STP_MODELS_PATH"] = models_path
    os.environ["STP_TRAIN_PATH"] = train_path
    os.environ["STP_TOOLS_PATH"] = tools_path
    os.environ["STP_LOG_LEVEL"] = "INFO"

    print(f"\n🔧 Configurazione:")
    print(f"  Models: {models_path}")
    print(f"  Train: {train_path}")
    print(f"  Tools: {tools_path}")

    try:
        import uvicorn

        print("\n🚀 Avvio server su http://localhost:8099")
        print("📋 Test disponibili:")
        print("  - Pagina principale: http://localhost:8099")
        print("  - Health check: http://localhost:8099/api/health")
        print("  - API docs: http://localhost:8099/docs")
        print("\n⏹️  Premi Ctrl+C per fermare")

        # Import dell'app dopo aver configurato l'ambiente
        from api.app import app

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8099,
            log_level="info",
            reload=False
        )

    except KeyboardInterrupt:
        print("\n👋 Server fermato")
    except Exception as e:
        print(f"❌ Errore server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()