"""Model downloader per Speech-to-Phrase Predictor.

Scarica gli stessi modelli che usa Speech-to-Phrase per predizioni accurate.
"""

import os
import sqlite3
import logging
import aiohttp
import asyncio
import gzip
from pathlib import Path
from typing import Dict, Optional, Any
import json
import hashlib

_LOGGER = logging.getLogger(__name__)


class SpeechToPhraseModelDownloader:
    """Downloader per modelli Speech-to-Phrase da HuggingFace."""

    # Base URLs per i modelli Rhasspy su GitHub
    GITHUB_BASE = "https://github.com/rhasspy"

    # Modelli disponibili e loro file (aggiornati con URL corretti)
    AVAILABLE_MODELS = {
        "it_IT-rhasspy": {
            "lexicon_txt": f"{GITHUB_BASE}/it_kaldi-rhasspy/raw/master/base_dictionary.txt.gz",
            "g2p.fst": f"{GITHUB_BASE}/it_kaldi-rhasspy/raw/master/g2p.fst.gz",
            "language": "Italian",
            "description": "Italian Rhasspy Kaldi Model"
        },
        "en_US-rhasspy": {
            "lexicon_txt": f"{GITHUB_BASE}/en_kaldi-rhasspy/raw/master/base_dictionary.txt.gz",
            "g2p.fst": f"{GITHUB_BASE}/en_kaldi-rhasspy/raw/master/g2p.fst.gz",
            "language": "English",
            "description": "English Rhasspy Kaldi Model"
        }
    }

    def __init__(self, models_dir: str = "/data/speech_to_phrase_validator/models"):
        """Inizializza il downloader."""
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_id: str) -> Path:
        """Ottieni il percorso di un modello."""
        return self.models_dir / model_id

    def is_model_downloaded(self, model_id: str) -> bool:
        """Verifica se un modello è già scaricato."""
        if model_id not in self.AVAILABLE_MODELS:
            return False

        model_path = self.get_model_path(model_id)
        if not model_path.exists():
            return False

        # Verifica che tutti i file necessari esistano
        required_files = ["lexicon.db", "model_info.json"]
        for file_name in required_files:
            if not (model_path / file_name).exists():
                return False

        return True

    async def download_file(self, url: str, destination: Path, expected_size: Optional[int] = None) -> bool:
        """Scarica un file da URL."""
        try:
            _LOGGER.info(f"Downloading {url} to {destination}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        _LOGGER.error(f"Failed to download {url}: HTTP {response.status}")
                        return False

                    # Crea directory padre se non exists
                    destination.parent.mkdir(parents=True, exist_ok=True)

                    # Scarica con progress tracking
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(destination, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                if downloaded % (1024 * 1024) == 0:  # Log ogni MB
                                    _LOGGER.info(f"Download progress: {progress:.1f}%")

                    _LOGGER.info(f"Successfully downloaded {destination}")
                    return True

        except Exception as e:
            _LOGGER.error(f"Error downloading {url}: {e}")
            return False

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calcola hash MD5 di un file per verifica integrità."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    def verify_lexicon_db(self, db_path: Path) -> bool:
        """Verifica che il database lessico sia valido."""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Verifica struttura tabelle
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            if 'lexicon' not in tables:
                _LOGGER.error("Lexicon table not found in database")
                return False

            # Verifica che ci siano dati
            cursor.execute("SELECT COUNT(*) FROM lexicon")
            word_count = cursor.fetchone()[0]

            if word_count < 1000:  # Sanity check
                _LOGGER.error(f"Too few words in lexicon: {word_count}")
                return False

            _LOGGER.info(f"Lexicon database verified: {word_count} words")
            conn.close()
            return True

        except Exception as e:
            _LOGGER.error(f"Error verifying lexicon database: {e}")
            return False

    def create_lexicon_db_from_txt(self, txt_path: Path, db_path: Path) -> bool:
        """Crea database SQLite dal file di testo del lessico."""
        try:
            _LOGGER.info(f"Creating SQLite database from {txt_path}")

            # Apri file (potrebbe essere compresso)
            if txt_path.suffix == '.gz':
                file_opener = lambda: gzip.open(txt_path, 'rt', encoding='utf-8')
            else:
                file_opener = lambda: open(txt_path, 'r', encoding='utf-8')

            # Crea database SQLite
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Crea tabella lessico
            cursor.execute('''
                CREATE TABLE lexicon (
                    word TEXT,
                    pronunciation TEXT
                )
            ''')

            # Leggi file di testo e inserisci nel database
            word_count = 0
            with file_opener() as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse formato: parola [tab] pronuncia_fonetica
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        word = parts[0].strip()
                        pronunciation = parts[1].strip()

                        cursor.execute(
                            "INSERT INTO lexicon (word, pronunciation) VALUES (?, ?)",
                            (word, pronunciation)
                        )
                        word_count += 1

            # Crea indice per performance
            cursor.execute("CREATE INDEX idx_word ON lexicon(word)")

            conn.commit()
            conn.close()

            _LOGGER.info(f"Created lexicon database with {word_count} words")
            return word_count > 100  # Sanity check

        except Exception as e:
            _LOGGER.error(f"Error creating lexicon database: {e}")
            return False

    async def download_model(self, model_id: str, force_redownload: bool = False) -> bool:
        """Scarica un modello completo."""
        if model_id not in self.AVAILABLE_MODELS:
            _LOGGER.error(f"Unknown model: {model_id}")
            return False

        if self.is_model_downloaded(model_id) and not force_redownload:
            _LOGGER.info(f"Model {model_id} already downloaded")
            return True

        model_info = self.AVAILABLE_MODELS[model_id]
        model_path = self.get_model_path(model_id)

        _LOGGER.info(f"Downloading model {model_id} to {model_path}")

        # Scarica lexicon text file (compresso)
        lexicon_url = model_info["lexicon_txt"]
        lexicon_txt_path = model_path / "base_dictionary.txt.gz"

        if not await self.download_file(lexicon_url, lexicon_txt_path):
            _LOGGER.error(f"Failed to download lexicon text for {model_id}")
            return False

        # Converti in database SQLite
        lexicon_db_path = model_path / "lexicon.db"
        if not self.create_lexicon_db_from_txt(lexicon_txt_path, lexicon_db_path):
            _LOGGER.error(f"Failed to create lexicon database for {model_id}")
            return False

        # Verifica database creato
        if not self.verify_lexicon_db(lexicon_db_path):
            _LOGGER.error(f"Lexicon database verification failed for {model_id}")
            return False

        # Scarica G2P model (opzionale)
        if "g2p.fst" in model_info:
            g2p_url = model_info["g2p.fst"]
            g2p_path = model_path / "g2p.fst.gz"

            if await self.download_file(g2p_url, g2p_path):
                _LOGGER.info(f"G2P model downloaded for {model_id}")
            else:
                _LOGGER.warning(f"G2P model download failed for {model_id} (non-critical)")

        # Cleanup file temporaneo
        if lexicon_txt_path.exists():
            lexicon_txt_path.unlink()

        # Crea file info del modello
        model_info_data = {
            "model_id": model_id,
            "language": model_info["language"],
            "description": model_info["description"],
            "download_date": asyncio.get_event_loop().time(),
            "files": {
                "lexicon.db": {
                    "size": lexicon_db_path.stat().st_size,
                    "hash": self.calculate_file_hash(lexicon_db_path)
                }
            }
        }

        # Aggiungi info G2P se disponibile
        g2p_path = model_path / "g2p.fst.gz"
        if g2p_path.exists():
            model_info_data["files"]["g2p.fst.gz"] = {
                "size": g2p_path.stat().st_size,
                "hash": self.calculate_file_hash(g2p_path)
            }

        info_path = model_path / "model_info.json"
        with open(info_path, 'w') as f:
            json.dump(model_info_data, f, indent=2)

        _LOGGER.info(f"Successfully downloaded and verified model {model_id}")
        return True

    def get_downloaded_models(self) -> Dict[str, Dict[str, Any]]:
        """Ottieni lista dei modelli scaricati."""
        downloaded = {}

        for model_id in self.AVAILABLE_MODELS:
            if self.is_model_downloaded(model_id):
                info_path = self.get_model_path(model_id) / "model_info.json"
                try:
                    with open(info_path) as f:
                        model_info = json.load(f)
                    downloaded[model_id] = model_info
                except Exception as e:
                    _LOGGER.warning(f"Could not read model info for {model_id}: {e}")

        return downloaded

    async def ensure_model_available(self, model_id: str = "it_IT-rhasspy") -> bool:
        """Assicura che un modello sia disponibile, scaricandolo se necessario."""
        if self.is_model_downloaded(model_id):
            return True

        _LOGGER.info(f"Model {model_id} not found, downloading...")
        return await self.download_model(model_id)


# Utility function per ottenere downloader globale
_downloader_instance: Optional[SpeechToPhraseModelDownloader] = None

def get_model_downloader() -> SpeechToPhraseModelDownloader:
    """Ottieni istanza singleton del model downloader."""
    global _downloader_instance
    if _downloader_instance is None:
        _downloader_instance = SpeechToPhraseModelDownloader()
    return _downloader_instance