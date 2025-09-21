"""Wrapper per LexiconDatabase di Speech-to-Phrase."""

import sqlite3
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import sys
import os

# Aggiungi il percorso di speech-to-phrase al PYTHONPATH per importare i moduli
_SPEECH_TO_PHRASE_PATH = Path(__file__).parent.parent.parent.parent / "speech-to-phrase"
if _SPEECH_TO_PHRASE_PATH.exists():
    sys.path.insert(0, str(_SPEECH_TO_PHRASE_PATH))

_LOGGER = logging.getLogger(__name__)


class LexiconWrapper:
    """Wrapper per gestire il lessico di Speech-to-Phrase."""

    def __init__(self, model_info, phonetisaurus_binary: Optional[Path] = None):
        """Inizializza il wrapper del lessico."""
        self.model_info = model_info
        self.phonetisaurus_binary = phonetisaurus_binary
        self._cache: Dict[str, Optional[List[List[str]]]] = {}
        self._word_set: Optional[Set[str]] = None
        self._db_connection: Optional[sqlite3.Connection] = None
        self._text_pronunciations: Dict[str, List[List[str]]] = {}

        # Inizializza la connessione al database se disponibile
        if model_info.lexicon_db_path and model_info.lexicon_db_path.exists():
            try:
                self._db_connection = sqlite3.connect(str(model_info.lexicon_db_path))
                _LOGGER.info(f"Connected to lexicon database: {model_info.lexicon_db_path}")
            except Exception as e:
                _LOGGER.warning(f"Could not connect to lexicon database: {e}")

    def __del__(self):
        """Chiude la connessione al database."""
        if self._db_connection:
            self._db_connection.close()

    def exists(self, word: str) -> bool:
        """Verifica se una parola esiste nel lessico."""
        # Carica l'elenco delle parole se non già fatto
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
        for word_var in word_vars:
            cached_prons = self._cache.get(word_var)
            if cached_prons is not None:
                self._cache[word] = cached_prons
                return cached_prons

        # Cerca nei file di testo prima
        text_prons: List[List[str]] = []
        for word_var in word_vars:
            if word_var in self._text_pronunciations:
                text_prons.extend(self._text_pronunciations[word_var])
                if text_prons:
                    self._cache[word] = text_prons
                    return text_prons

        # Cerca nel database se non trovato nei file di testo
        db_prons: List[List[str]] = []
        if self._db_connection:
            for word_var in word_vars:
                try:
                    cursor = self._db_connection.execute(
                        "SELECT phonemes FROM word_phonemes WHERE word = ? ORDER BY pron_order",
                        (word_var,),
                    )
                    for row in cursor:
                        db_prons.append(row[0].split())

                    if db_prons:
                        # Memorizza nella cache e restituisce
                        self._cache[word_var] = db_prons
                        self._cache[word] = db_prons
                        return db_prons
                except Exception as e:
                    _LOGGER.debug(f"Database lookup failed for {word_var}: {e}")

        # Nessuna pronuncia trovata
        self._cache[word] = []
        return []

    def guess_pronunciation(self, word: str) -> Optional[List[str]]:
        """Indovina la pronuncia di una parola usando Phonetisaurus."""
        if not self.phonetisaurus_binary or not self.model_info.g2p_path:
            return None

        try:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", encoding="utf-8") as wordlist_file:
                wordlist_file.write(word + "\n")
                wordlist_file.flush()

                result = subprocess.run(
                    [
                        str(self.phonetisaurus_binary),
                        f"--model={self.model_info.g2p_path}",
                        f"--wordlist={wordlist_file.name}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            parts = line.split()
                            if len(parts) >= 3 and parts[0] == word:
                                phonemes = parts[2:]
                                return phonemes

        except Exception as e:
            _LOGGER.warning(f"Failed to guess pronunciation for '{word}': {e}")

        return None

    def get_word_status(self, word: str) -> Dict[str, any]:
        """Ottiene lo status completo di una parola."""
        is_known = self.exists(word)
        pronunciations = self.lookup(word) if is_known else []
        guessed_pronunciation = None

        if not is_known:
            guessed_pronunciation = self.guess_pronunciation(word)

        return {
            "word": word,
            "is_known": is_known,
            "pronunciations": pronunciations,
            "guessed_pronunciation": guessed_pronunciation,
            "model_id": self.model_info.id,
            "model_type": self.model_info.type.value,
        }

    def find_similar_words(self, word: str, max_results: int = 5) -> List[Tuple[str, float]]:
        """Trova parole simili nel lessico."""
        if self._word_set is None:
            self._load_word_set()

        similar_words = []
        word_lower = word.lower()

        # Semplice ricerca per similarità basata su substring e lunghezza
        for known_word in self._word_set:
            if known_word == word_lower:
                continue

            score = self._calculate_similarity(word_lower, known_word.lower())
            if score > 0.5:  # Soglia di similarità
                similar_words.append((known_word, score))

        # Ordina per score decrescente e prendi i primi max_results
        similar_words.sort(key=lambda x: x[1], reverse=True)
        return similar_words[:max_results]

    def _load_word_set(self) -> None:
        """Carica l'elenco delle parole dal database o file di testo."""
        self._word_set = set()

        if self.model_info.lexicon_db_path and self.model_info.lexicon_db_path.exists():
            if str(self.model_info.lexicon_db_path).endswith('.txt'):
                # Carica da file di testo (Speech-to-Phrase format)
                self._load_from_text_file()
            else:
                # Carica da database SQLite
                self._load_from_database()
        else:
            _LOGGER.warning("No lexicon source available for loading words")

    def _load_from_text_file(self) -> None:
        """Carica parole da file di testo (formato Speech-to-Phrase)."""
        try:
            with open(self.model_info.lexicon_db_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Formato: word phone1 phone2 ...
                        parts = line.split()
                        if parts:
                            word = parts[0]
                            phones = parts[1:] if len(parts) > 1 else []
                            self._word_set.add(word)

                            # Memorizza la pronuncia
                            if word not in self._text_pronunciations:
                                self._text_pronunciations[word] = []
                            self._text_pronunciations[word].append(phones)

            _LOGGER.info(f"Loaded {len(self._word_set)} words from lexicon text file")

        except Exception as e:
            _LOGGER.error(f"Failed to load words from text file: {e}")
            self._word_set = set()

    def _load_from_database(self) -> None:
        """Carica parole da database SQLite."""
        if not self._db_connection:
            _LOGGER.warning("No database connection available for loading words")
            return

        try:
            cursor = self._db_connection.execute("SELECT DISTINCT word FROM word_phonemes")
            for row in cursor:
                self._word_set.add(row[0])

            _LOGGER.info(f"Loaded {len(self._word_set)} words from lexicon database")

        except Exception as e:
            _LOGGER.error(f"Failed to load words from database: {e}")
            self._word_set = set()

    def _word_variations(self, word: str) -> List[str]:
        """Genera variazioni di una parola (case variations)."""
        variations = [word]

        word_lower = word.lower()
        if word_lower != word:
            variations.append(word_lower)

        word_casefold = word.casefold()
        if word_casefold != word_lower:
            variations.append(word_casefold)

        word_upper = word.upper()
        if word_upper != word:
            variations.append(word_upper)

        return variations

    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """Calcola la similarità tra due parole (semplice implementazione)."""
        # Implementazione base usando Levenshtein distance
        len1, len2 = len(word1), len(word2)
        if len1 == 0:
            return 0.0 if len2 > 0 else 1.0
        if len2 == 0:
            return 0.0

        # Matrice per dynamic programming
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        # Inizializzazione
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j

        # Riempimento della matrice
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if word1[i - 1] == word2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        # Conversione in score di similarità (0-1)
        max_len = max(len1, len2)
        distance = dp[len1][len2]
        return 1.0 - (distance / max_len)

    def get_statistics(self) -> Dict[str, any]:
        """Ottiene statistiche sul lessico."""
        if self._word_set is None:
            self._load_word_set()

        stats = {
            "total_words": len(self._word_set) if self._word_set else 0,
            "model_id": self.model_info.id,
            "model_type": self.model_info.type.value,
            "has_g2p_model": self.model_info.g2p_path is not None,
            "has_phonetisaurus": self.phonetisaurus_binary is not None,
            "database_path": str(self.model_info.lexicon_db_path) if self.model_info.lexicon_db_path else None,
        }

        return stats