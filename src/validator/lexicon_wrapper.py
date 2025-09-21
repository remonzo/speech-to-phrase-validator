"""Wrapper per LexiconDatabase di Speech-to-Phrase - Ottimizzato per Add-on HA v1.5.8."""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import re

_LOGGER = logging.getLogger(__name__)


class LexiconWrapper:
    """Wrapper per gestire il lessico di Speech-to-Phrase - Ottimizzato per Add-on HA."""

    def __init__(self, model_info, phonetisaurus_binary: Optional[Path] = None):
        """Inizializza il wrapper del lessico."""
        self.model_info = model_info
        self.phonetisaurus_binary = phonetisaurus_binary
        self._cache: Dict[str, Optional[List[List[str]]]] = {}
        self._word_set: Optional[Set[str]] = None
        self._db_connection: Optional[sqlite3.Connection] = None
        self._text_pronunciations: Dict[str, List[List[str]]] = {}
        self._is_text_lexicon = False

        # Inizializza la connessione appropriata
        if model_info.lexicon_db_path and model_info.lexicon_db_path.exists():
            self._initialize_lexicon()

    def _initialize_lexicon(self) -> None:
        """Inizializza la connessione al lessico appropriato."""
        lexicon_path = self.model_info.lexicon_db_path

        if lexicon_path.suffix == '.txt':
            # File di testo Speech-to-Phrase (add-on HA)
            self._is_text_lexicon = True
            _LOGGER.info(f"Using text lexicon: {lexicon_path}")
            self._load_text_lexicon()
        else:
            # Database SQLite tradizionale
            self._is_text_lexicon = False
            try:
                self._db_connection = sqlite3.connect(str(lexicon_path))
                _LOGGER.info(f"Connected to SQLite lexicon: {lexicon_path}")
            except Exception as e:
                _LOGGER.warning(f"Could not connect to lexicon database: {e}")

    def _load_text_lexicon(self) -> None:
        """Carica lessico da file di testo ottimizzato per add-on HA."""
        if not self.model_info.lexicon_db_path.exists():
            _LOGGER.error(f"Lexicon file not found: {self.model_info.lexicon_db_path}")
            return

        word_count = 0
        error_lines = 0

        try:
            with open(self.model_info.lexicon_db_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Salta righe vuote e commenti
                    if not line or line.startswith('#'):
                        continue

                    # Parse formato Kaldi: word phoneme1 phoneme2 ...
                    parts = line.split()
                    if len(parts) < 1:
                        error_lines += 1
                        continue

                    word = parts[0]
                    phonemes = parts[1:] if len(parts) > 1 else []

                    # Aggiungi a pronuncie di testo
                    if word not in self._text_pronunciations:
                        self._text_pronunciations[word] = []

                    if phonemes:
                        self._text_pronunciations[word].append(phonemes)

                    word_count += 1

        except Exception as e:
            _LOGGER.error(f"Could not load text lexicon {self.model_info.lexicon_db_path}: {e}")
            return

        _LOGGER.info(f"Loaded {word_count} words from text lexicon (HA add-on optimized)")
        if error_lines > 0:
            _LOGGER.warning(f"Skipped {error_lines} malformed lines")

    def __del__(self):
        """Chiude la connessione al database."""
        if self._db_connection:
            self._db_connection.close()

    def exists(self, word: str) -> bool:
        """Verifica se una parola esiste nel lessico."""
        if self._word_set is None:
            self._load_word_set()

        # Controlla le variazioni della parola
        for word_var in self._word_variations(word):
            if word_var in self._word_set:
                return True

        return False

    def lookup(self, word: str) -> List[List[str]]:
        """Ottiene le pronunce per una parola."""
        # Controlla prima la cache
        if word in self._cache:
            cached_result = self._cache[word]
            return cached_result if cached_result is not None else []

        # Cerca nelle variazioni della parola
        word_vars = list(self._word_variations(word))

        # Per lessico di testo (add-on HA)
        if self._is_text_lexicon:
            return self._lookup_text_lexicon(word, word_vars)

        # Per database SQLite tradizionale
        return self._lookup_sqlite_lexicon(word, word_vars)

    def _lookup_text_lexicon(self, word: str, word_vars: List[str]) -> List[List[str]]:
        """Cerca nel lessico di testo ottimizzato."""
        for word_var in word_vars:
            if word_var in self._text_pronunciations:
                pronunciations = self._text_pronunciations[word_var]
                self._cache[word] = pronunciations
                return pronunciations

        # Non trovato
        self._cache[word] = []
        return []

    def _lookup_sqlite_lexicon(self, word: str, word_vars: List[str]) -> List[List[str]]:
        """Cerca nel database SQLite tradizionale."""
        if not self._db_connection:
            self._cache[word] = []
            return []

        db_prons: List[List[str]] = []

        for word_var in word_vars:
            try:
                cursor = self._db_connection.execute(
                    "SELECT phonemes FROM word_phonemes WHERE word = ? ORDER BY pron_order",
                    (word_var,),
                )
                for row in cursor:
                    db_prons.append(row[0].split())

                if db_prons:
                    self._cache[word_var] = db_prons
                    self._cache[word] = db_prons
                    return db_prons

            except Exception as e:
                _LOGGER.debug(f"Database lookup failed for {word_var}: {e}")

        # Non trovato
        self._cache[word] = []
        return []

    def _load_word_set(self) -> None:
        """Carica l'elenco di tutte le parole disponibili."""
        if self._is_text_lexicon:
            # Usa le parole già caricate dal lessico di testo
            self._word_set = set(self._text_pronunciations.keys())
        else:
            # Carica dal database SQLite
            self._load_sqlite_word_set()

    def _load_sqlite_word_set(self) -> None:
        """Carica parole dal database SQLite."""
        if not self._db_connection:
            self._word_set = set()
            return

        try:
            cursor = self._db_connection.execute("SELECT DISTINCT word FROM word_phonemes")
            self._word_set = {row[0] for row in cursor}
        except Exception as e:
            _LOGGER.error(f"Could not load word set from database: {e}")
            self._word_set = set()

    def _word_variations(self, word: str) -> List[str]:
        """Genera variazioni di una parola per migliorare la ricerca."""
        variations = [word]

        # Variazioni di caso
        if word != word.lower():
            variations.append(word.lower())
        if word != word.upper():
            variations.append(word.upper())
        if word != word.title():
            variations.append(word.title())

        # Rimuovi duplicati mantenendo l'ordine
        seen = set()
        result = []
        for var in variations:
            if var not in seen:
                seen.add(var)
                result.append(var)

        return result

    def get_statistics(self) -> Dict[str, Union[int, str, bool]]:
        """Restituisce statistiche sul lessico."""
        if self._word_set is None:
            self._load_word_set()

        return {
            "total_words": len(self._word_set) if self._word_set else 0,
            "lexicon_type": "text_file" if self._is_text_lexicon else "sqlite_database",
            "lexicon_path": str(self.model_info.lexicon_db_path) if self.model_info.lexicon_db_path else "",
            "is_ha_addon_optimized": self._is_text_lexicon,
            "phonetisaurus_available": self.phonetisaurus_binary is not None and self.phonetisaurus_binary.exists() if self.phonetisaurus_binary else False,
            "cache_entries": len(self._cache)
        }

    def clear_cache(self) -> None:
        """Svuota la cache delle pronunce."""
        self._cache.clear()
        _LOGGER.debug("Cleared pronunciation cache")

    def get_word_count(self) -> int:
        """Restituisce il numero totale di parole nel lessico."""
        if self._word_set is None:
            self._load_word_set()
        return len(self._word_set) if self._word_set else 0