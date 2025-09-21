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
            "description": "Italian Rhasspy Kaldi Model",
            "fallback_urls": [
                # Prova anche senza 'it_' prefix
                f"{GITHUB_BASE}/it-kaldi-rhasspy/raw/master/base_dictionary.txt.gz",
                # Prova repo alternativo
                f"{GITHUB_BASE}/rhasspy-profiles/raw/master/it/kaldi/base_dictionary.txt.gz"
            ]
        },
        "en_US-rhasspy": {
            "lexicon_txt": f"{GITHUB_BASE}/en-us_kaldi-rhasspy/raw/master/base_dictionary.txt.gz",
            "g2p.fst": f"{GITHUB_BASE}/en-us_kaldi-rhasspy/raw/master/g2p.fst.gz",
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

            # Verifica che il file esista
            if not txt_path.exists():
                _LOGGER.error(f"Dictionary file not found: {txt_path}")
                return False

            # Controlla dimensione file
            file_size = txt_path.stat().st_size
            _LOGGER.info(f"Dictionary file size: {file_size} bytes")

            # Apri file (potrebbe essere compresso)
            if txt_path.suffix == '.gz':
                file_opener = lambda: gzip.open(txt_path, 'rt', encoding='utf-8')
            else:
                file_opener = lambda: open(txt_path, 'r', encoding='utf-8')

            # Debug: Leggi prime 10 righe per capire il formato
            _LOGGER.info("Analyzing dictionary file format...")
            sample_lines = []
            try:
                with file_opener() as f:
                    for i, line in enumerate(f):
                        if i >= 10:
                            break
                        sample_lines.append(repr(line.strip()))

                _LOGGER.info(f"Sample lines from dictionary:")
                for i, line in enumerate(sample_lines):
                    _LOGGER.info(f"  Line {i}: {line}")
            except Exception as e:
                _LOGGER.error(f"Error reading sample lines: {e}")

            # Crea database SQLite (rimuovi esistente se necessario)
            if db_path.exists():
                _LOGGER.info(f"Removing existing database: {db_path}")
                db_path.unlink()

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
            line_count = 0
            skipped_lines = 0

            with file_opener() as f:
                for line in f:
                    line_count += 1
                    line = line.strip()

                    if not line or line.startswith('#'):
                        skipped_lines += 1
                        continue

                    # Prova diversi formati di separazione
                    parts = None

                    # Formato principale: Single space (basato sui sample logs)
                    # Esempi dal log: 'abaco ˈa b a k o', 'casa k a s a'
                    space_idx = line.find(' ')
                    if space_idx > 0:
                        word = line[:space_idx].strip()
                        pronunciation = line[space_idx+1:].strip()

                        # Salta righe con simboli speciali o entries non standard
                        if (not word.startswith('<') and
                            not word.startswith('!') and
                            not word.startswith('-') and
                            word and pronunciation and
                            len(word) > 1):
                            parts = [word, pronunciation]

                    if parts and len(parts) >= 2:
                        final_word = parts[0].strip()
                        final_pronunciation = parts[1].strip()

                        if final_word and final_pronunciation:
                            cursor.execute(
                                "INSERT INTO lexicon (word, pronunciation) VALUES (?, ?)",
                                (final_word, final_pronunciation)
                            )
                            word_count += 1

                            # Log prima entry come esempio
                            if word_count == 1:
                                _LOGGER.info(f"First entry example: '{final_word}' -> '{final_pronunciation}'")
                    else:
                        if line_count <= 20:  # Log prime righe problematiche
                            _LOGGER.warning(f"Could not parse line {line_count}: {repr(line)}")

            # Crea indice per performance
            cursor.execute("CREATE INDEX idx_word ON lexicon(word)")

            conn.commit()
            conn.close()

            _LOGGER.info(f"Dictionary parsing complete:")
            _LOGGER.info(f"  Total lines processed: {line_count}")
            _LOGGER.info(f"  Lines skipped: {skipped_lines}")
            _LOGGER.info(f"  Words extracted: {word_count}")

            return word_count > 100  # Sanity check

        except Exception as e:
            _LOGGER.error(f"Error creating lexicon database: {e}")
            import traceback
            _LOGGER.error(f"Traceback: {traceback.format_exc()}")
            return False

    def create_minimal_test_database(self, db_path: Path) -> bool:
        """Crea database minimale per test quando download fallisce."""
        try:
            _LOGGER.info(f"Creating minimal test database at {db_path}")

            # Rimuovi database esistente se presente
            if db_path.exists():
                _LOGGER.info(f"Removing existing database for fresh creation: {db_path}")
                db_path.unlink()

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Crea tabella lessico
            cursor.execute('''
                CREATE TABLE lexicon (
                    word TEXT,
                    pronunciation TEXT
                )
            ''')

            # Parole italiane comuni per test
            test_words = [
                ("casa", "k a s a"),
                ("ciao", "tʃ a o"),
                ("buongiorno", "b u o n dʒ o r n o"),
                ("accendi", "a tʃ e n d i"),
                ("spegni", "s p e ɲ i"),
                ("luce", "l u tʃ e"),
                ("luci", "l u tʃ i"),
                ("condizionatore", "k o n d i t s i o n a t o r e"),
                ("soggiorno", "s o dʒ o r n o"),
                ("cucina", "k u tʃ i n a"),
                ("bagno", "b a ɲ o"),
                ("camera", "k a m e r a"),
                ("termostato", "t e r m o s t a t o"),
                ("temperatura", "t e m p e r a t u r a"),
                ("volume", "v o l u m e"),
                ("alto", "a l t o"),
                ("basso", "b a s s o"),
                ("gradi", "g r a d i"),
                ("ventilatore", "v e n t i l a t o r e"),
                ("climatizzatore", "k l i m a t i d z a t o r e"),
                ("riscaldamento", "r i s k a l d a m e n t o"),
                ("raffredda", "r a f r e d d a"),
                ("alza", "a l t s a"),
                ("abbassa", "a b b a s s a"),
                ("chiudi", "k i u d i"),
                ("apri", "a p r i"),
                ("finestra", "f i n e s t r a"),
                ("porta", "p o r t a"),
                ("tapparella", "t a p p a r e l l a"),
                ("persiana", "p e r s i a n a"),
                ("televisore", "t e l e v i z o r e"),
                ("tv", "t i v u"),
                ("canale", "k a n a l e"),
                ("musica", "m u z i k a"),
                ("radio", "r a d i o"),
                ("suona", "s u o n a"),
                ("ferma", "f e r m a"),
                ("pausa", "p a u z a"),
                ("avanti", "a v a n t i"),
                ("indietro", "i n d i e t r o"),
                ("bianco", "b i a n k o"),
                ("nero", "n e r o"),
                ("rosso", "r o s s o"),
                ("blu", "b l u"),
                ("verde", "v e r d e"),
                ("giallo", "dʒ a l l o"),
                ("colore", "k o l o r e"),
                ("luminosità", "l u m i n o z i t a"),
                ("dimmer", "d i m m e r"),
                ("interruttore", "i n t e r u t t o r e"),
                ("sensore", "s e n s o r e"),
                ("movimento", "m o v i m e n t o"),
                ("presenza", "p r e z e n t s a"),
                ("allarme", "a l l a r m e"),
                ("sicurezza", "s i k u r e t s a"),
                ("giardino", "dʒ a r d i n o"),
                ("terrazzo", "t e r r a t s o"),
                ("balcone", "b a l k o n e"),
                ("mansarda", "m a n s a r d a"),
                ("soffitta", "s o f f i t t a"),
                ("cantina", "k a n t i n a"),
                ("garage", "g a r a ʒ"),
                ("ingresso", "i n g r e s s o"),
                ("corridoio", "k o r r i d o i o"),
                ("scala", "s k a l a"),
                ("tavolo", "t a v o l o"),
                ("sedia", "s e d i a"),
                ("divano", "d i v a n o"),
                ("letto", "l e t t o"),
                ("armadio", "a r m a d i o"),
                ("frigorifero", "f r i g o r i f e r o"),
                ("forno", "f o r n o"),
                ("lavastoviglie", "l a v a s t o v i ʎ e"),
                ("lavatrice", "l a v a t r i tʃ e"),
                ("asciugatrice", "a ʃ u g a t r i tʃ e"),
                ("doccia", "d o tʃ a"),
                ("vasca", "v a s k a"),
                ("specchio", "s p e k k i o"),
                ("rubinetto", "r u b i n e t t o"),
                ("acqua", "a k w a"),
                ("calda", "k a l d a"),
                ("fredda", "f r e d d a"),
                ("timer", "t a i m e r"),
                ("automatico", "a u t o m a t i k o"),
                ("manuale", "m a n u a l e"),
                ("modalità", "m o d a l i t a"),
                ("programma", "p r o g r a m m a"),
                ("velocità", "v e l o tʃ i t a"),
                ("potenza", "p o t e n t s a"),
                ("energia", "e n e r dʒ i a"),
                ("consumo", "k o n s u m o"),
                ("risparmio", "r i s p a r m i o"),
                ("ecologia", "e k o l o dʒ i a"),
                ("ambiente", "a m b i e n t e"),
                ("comfort", "k o m f o r t"),
                ("relax", "r e l a k s"),
                ("sonno", "s o n n o"),
                ("sveglia", "z v e ʎ a"),
                ("ora", "o r a"),
                ("ore", "o r e"),
                ("minuto", "m i n u t o"),
                ("minuti", "m i n u t i"),
                ("secondo", "s e k o n d o"),
                ("secondi", "s e k o n d i"),
                ("mattina", "m a t t i n a"),
                ("sera", "s e r a"),
                ("notte", "n o t t e"),
                ("giorno", "dʒ o r n o"),
                ("oggi", "o dʒ i"),
                ("domani", "d o m a n i"),
                ("ieri", "i e r i"),
                ("sempre", "s e m p r e"),
                ("mai", "m a i"),
                ("tutto", "t u t t o"),
                ("niente", "n i e n t e"),
                ("bene", "b e n e"),
                ("male", "m a l e"),
                ("perfetto", "p e r f e t t o"),
                ("ok", "o k"),
                ("grazie", "g r a t s i e"),
                ("prego", "p r e g o"),
                ("scusa", "s k u z a"),
                ("aiuto", "a i u t o"),
                ("assistente", "a s s i s t e n t e"),
                ("comando", "k o m a n d o"),
                ("controllo", "k o n t r o l l o"),
                ("gestione", "dʒ e s t i o n e"),
                ("sistema", "s i s t e m a"),
                ("dispositivo", "d i s p o z i t i v o"),
                ("domotica", "d o m o t i k a"),
                ("smart", "s m a r t"),
                ("casa", "k a s a"),
                ("intelligente", "i n t e l l i dʒ e n t e")
            ]

            # Inserisci parole nel database
            for word, pronunciation in test_words:
                cursor.execute(
                    "INSERT INTO lexicon (word, pronunciation) VALUES (?, ?)",
                    (word, pronunciation)
                )

            # Crea indice
            cursor.execute("CREATE INDEX idx_word ON lexicon(word)")

            conn.commit()
            conn.close()

            _LOGGER.info(f"Created test database with {len(test_words)} Italian words")
            return True

        except Exception as e:
            _LOGGER.error(f"Error creating minimal test database: {e}")
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

        # Scarica lexicon text file (compresso) con fallback URLs
        lexicon_url = model_info["lexicon_txt"]
        lexicon_txt_path = model_path / "base_dictionary.txt.gz"

        # Lista di URL da provare
        urls_to_try = [lexicon_url]
        if "fallback_urls" in model_info:
            urls_to_try.extend(model_info["fallback_urls"])

        download_success = False
        for i, url in enumerate(urls_to_try):
            _LOGGER.info(f"Trying URL {i+1}/{len(urls_to_try)}: {url}")
            if await self.download_file(url, lexicon_txt_path):
                download_success = True
                _LOGGER.info(f"Successfully downloaded from URL {i+1}")
                break
            else:
                _LOGGER.warning(f"Download failed from URL {i+1}, trying next...")

        if not download_success:
            _LOGGER.error(f"Failed to download lexicon text for {model_id} from all URLs")
            return False

        # Converti in database SQLite
        lexicon_db_path = model_path / "lexicon.db"
        if not self.create_lexicon_db_from_txt(lexicon_txt_path, lexicon_db_path):
            _LOGGER.error(f"Failed to create lexicon database for {model_id}")

            # Fallback: crea database minimo per test
            _LOGGER.info("Creating minimal test database as fallback...")
            if self.create_minimal_test_database(lexicon_db_path):
                _LOGGER.info("Minimal test database created successfully")
            else:
                _LOGGER.error("Failed to create even minimal database")
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