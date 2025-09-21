"""Model downloader per Speech-to-Phrase Predictor.

Scarica gli stessi modelli che usa Speech-to-Phrase per predizioni accurate.
"""

import os
import sqlite3
import logging
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
import json
import hashlib

_LOGGER = logging.getLogger(__name__)


class SpeechToPhraseModelDownloader:
    """Downloader per modelli Speech-to-Phrase da HuggingFace."""

    # Base URLs per i modelli Speech-to-Phrase
    HUGGINGFACE_BASE = "https://huggingface.co/rhasspy/rhasspy-models/resolve/main"

    # Modelli disponibili e loro file
    AVAILABLE_MODELS = {
        "it_IT-rhasspy": {
            "lexicon.db": f"{HUGGINGFACE_BASE}/it_IT-rhasspy/lexicon.db",
            "g2p.fst": f"{HUGGINGFACE_BASE}/it_IT-rhasspy/g2p.fst",
            "language": "Italian",
            "description": "Italian Speech-to-Phrase Model"
        },
        "en_US-rhasspy": {
            "lexicon.db": f"{HUGGINGFACE_BASE}/en_US-rhasspy/lexicon.db",
            "g2p.fst": f"{HUGGINGFACE_BASE}/en_US-rhasspy/g2p.fst",
            "language": "English",
            "description": "English Speech-to-Phrase Model"
        },
        "de_DE-rhasspy": {
            "lexicon.db": f"{HUGGINGFACE_BASE}/de_DE-rhasspy/lexicon.db",
            "g2p.fst": f"{HUGGINGFACE_BASE}/de_DE-rhasspy/g2p.fst",
            "language": "German",
            "description": "German Speech-to-Phrase Model"
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
        required_files = ["lexicon.db", "g2p.fst", "model_info.json"]
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

    def verify_g2p_model(self, g2p_path: Path) -> bool:
        """Verifica che il modello G2P sia valido."""
        try:
            # Verifica che il file esista e abbia dimensione ragionevole
            if not g2p_path.exists():
                return False

            file_size = g2p_path.stat().st_size
            if file_size < 1000:  # Troppo piccolo
                _LOGGER.error(f"G2P model file too small: {file_size} bytes")
                return False

            # TODO: Aggiungere verifica OpenFST quando implementiamo G2P
            _LOGGER.info(f"G2P model verified: {file_size} bytes")
            return True

        except Exception as e:
            _LOGGER.error(f"Error verifying G2P model: {e}")
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

        # Scarica lexicon database
        lexicon_url = model_info["lexicon.db"]
        lexicon_path = model_path / "lexicon.db"

        if not await self.download_file(lexicon_url, lexicon_path):
            _LOGGER.error(f"Failed to download lexicon for {model_id}")
            return False

        # Verifica lexicon
        if not self.verify_lexicon_db(lexicon_path):
            _LOGGER.error(f"Lexicon verification failed for {model_id}")
            return False

        # Scarica G2P model
        g2p_url = model_info["g2p.fst"]
        g2p_path = model_path / "g2p.fst"

        if not await self.download_file(g2p_url, g2p_path):
            _LOGGER.error(f"Failed to download G2P model for {model_id}")
            return False

        # Verifica G2P
        if not self.verify_g2p_model(g2p_path):
            _LOGGER.error(f"G2P model verification failed for {model_id}")
            return False

        # Crea file info del modello
        model_info_data = {
            "model_id": model_id,
            "language": model_info["language"],
            "description": model_info["description"],
            "download_date": asyncio.get_event_loop().time(),
            "files": {
                "lexicon.db": {
                    "size": lexicon_path.stat().st_size,
                    "hash": self.calculate_file_hash(lexicon_path)
                },
                "g2p.fst": {
                    "size": g2p_path.stat().st_size,
                    "hash": self.calculate_file_hash(g2p_path)
                }
            }
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