"""Standalone Lexicon Manager per Speech-to-Phrase Predictor.

Gestisce accesso diretto ai database lessicali e modelli G2P senza dipendenze da S2P.
"""

import sqlite3
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass
import json

_LOGGER = logging.getLogger(__name__)


@dataclass
class LexiconEntry:
    """Rappresenta una entry nel lessico."""
    word: str
    pronunciations: List[List[str]]
    frequency: int = 0


@dataclass
class G2PResult:
    """Risultato predizione G2P."""
    word: str
    pronunciation: List[str]
    confidence: float


class StandaloneLexicon:
    """Manager autonomo per database lessicali Speech-to-Phrase."""

    def __init__(self, model_path: Path):
        """Inizializza il lexicon manager."""
        self.model_path = model_path
        self.lexicon_db_path = model_path / "lexicon.db"
        self.g2p_model_path = model_path / "g2p.fst"

        # Cache per performance
        self._word_cache: Dict[str, LexiconEntry] = {}
        self._g2p_cache: Dict[str, G2PResult] = {}

        # Connessione database
        self._conn: Optional[sqlite3.Connection] = None

        # Verifica files
        if not self.lexicon_db_path.exists():
            raise FileNotFoundError(f"Lexicon database not found: {self.lexicon_db_path}")

        # G2P è opzionale per ora
        self._g2p_available = self.g2p_model_path.exists()
        if not self._g2p_available:
            _LOGGER.warning(f"G2P model not found: {self.g2p_model_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Ottieni connessione database (lazy loading)."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.lexicon_db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """Chiudi connessione database."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def normalize_word(self, word: str) -> str:
        """Normalizza una parola per lookup nel lessico."""
        # Converti in lowercase
        word = word.lower()

        # Rimuovi caratteri speciali comuni
        word = re.sub(r'[_\-\s]+', '', word)

        # Gestisci numeri (converti in lettere se necessario)
        # Per ora manteniamo semplice
        return word

    def exists_in_lexicon(self, word: str) -> bool:
        """Verifica se una parola esiste nel lessico completo."""
        normalized_word = self.normalize_word(word)

        # Controlla cache
        if normalized_word in self._word_cache:
            return True

        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT COUNT(*) FROM lexicon WHERE word = ? COLLATE NOCASE",
                (normalized_word,)
            )
            exists = cursor.fetchone()[0] > 0

            # Se esiste, carica in cache
            if exists:
                self._load_word_to_cache(normalized_word)

            return exists

        except Exception as e:
            _LOGGER.error(f"Error checking word existence '{word}': {e}")
            return False

    def _load_word_to_cache(self, word: str) -> Optional[LexiconEntry]:
        """Carica una parola nel cache."""
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT word, pronunciation FROM lexicon WHERE word = ? COLLATE NOCASE",
                (word,)
            )

            pronunciations = []
            actual_word = word

            for row in cursor.fetchall():
                actual_word = row['word']
                # Le pronunce sono separate da spazi
                pronunciation = row['pronunciation'].split()
                pronunciations.append(pronunciation)

            if pronunciations:
                entry = LexiconEntry(
                    word=actual_word,
                    pronunciations=pronunciations
                )
                self._word_cache[word] = entry
                return entry

        except Exception as e:
            _LOGGER.error(f"Error loading word '{word}' to cache: {e}")

        return None

    def get_pronunciations(self, word: str) -> List[List[str]]:
        """Ottieni tutte le pronunce di una parola dal lessico."""
        normalized_word = self.normalize_word(word)

        # Controlla cache
        if normalized_word in self._word_cache:
            return self._word_cache[normalized_word].pronunciations

        # Carica dal database
        entry = self._load_word_to_cache(normalized_word)
        return entry.pronunciations if entry else []

    def predict_with_g2p(self, word: str) -> Optional[G2PResult]:
        """Predici pronuncia usando modello G2P Phonetisaurus."""
        if not self._g2p_available:
            return None

        normalized_word = self.normalize_word(word)

        # Controlla cache G2P
        if normalized_word in self._g2p_cache:
            return self._g2p_cache[normalized_word]

        # Per ora simuliamo G2P (implementazione completa richiede OpenFST)
        # Aggiungeremo implementazione reale in seguito
        return self._simulate_g2p(normalized_word)

    def _simulate_g2p(self, word: str) -> Optional[G2PResult]:
        """Simulazione semplice di G2P per testing."""
        try:
            # Simulazione basica: converte lettere in fonemi italiani
            phoneme_map = {
                'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u',
                'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'g',
                'h': '', 'l': 'l', 'm': 'm', 'n': 'n', 'p': 'p',
                'q': 'k', 'r': 'r', 's': 's', 't': 't', 'v': 'v',
                'w': 'w', 'x': 'k s', 'y': 'i', 'z': 'z'
            }

            phonemes = []
            for char in word.lower():
                if char in phoneme_map:
                    phoneme = phoneme_map[char]
                    if phoneme:  # Salta caratteri vuoti come 'h'
                        phonemes.extend(phoneme.split())

            if phonemes:
                result = G2PResult(
                    word=word,
                    pronunciation=phonemes,
                    confidence=0.7  # Simulazione, confidence media
                )
                self._g2p_cache[word] = result
                return result

        except Exception as e:
            _LOGGER.error(f"Error in G2P simulation for '{word}': {e}")

        return None

    def find_similar_words(self, target_word: str, max_results: int = 5) -> List[Tuple[str, float]]:
        """Trova parole simili nel lessico usando distance algorithm."""
        target_normalized = self.normalize_word(target_word)

        if len(target_normalized) < 2:
            return []

        try:
            conn = self._get_connection()

            # Cerca parole che iniziano con le stesse lettere
            prefix_query = f"{target_normalized[:2]}%"
            cursor = conn.execute(
                "SELECT DISTINCT word FROM lexicon WHERE word LIKE ? COLLATE NOCASE LIMIT 100",
                (prefix_query,)
            )

            candidates = [row['word'] for row in cursor.fetchall()]

            # Calcola similarity usando Levenshtein distance semplificato
            similar_words = []
            for candidate in candidates:
                if candidate.lower() != target_normalized:
                    similarity = self._calculate_similarity(target_normalized, candidate.lower())
                    if similarity > 0.5:  # Soglia minima
                        similar_words.append((candidate, similarity))

            # Ordina per similarity decrescente
            similar_words.sort(key=lambda x: x[1], reverse=True)
            return similar_words[:max_results]

        except Exception as e:
            _LOGGER.error(f"Error finding similar words for '{target_word}': {e}")
            return []

    def _calculate_similarity(self, word1: str, word2: str) -> float:
        """Calcola similarity tra due parole (0-1)."""
        # Implementazione semplificata di Levenshtein distance
        if len(word1) == 0:
            return 0.0 if len(word2) == 0 else 0.0
        if len(word2) == 0:
            return 0.0

        # Matrice per dynamic programming
        matrix = [[0] * (len(word2) + 1) for _ in range(len(word1) + 1)]

        # Inizializza prima riga e colonna
        for i in range(len(word1) + 1):
            matrix[i][0] = i
        for j in range(len(word2) + 1):
            matrix[0][j] = j

        # Calcola distanze
        for i in range(1, len(word1) + 1):
            for j in range(1, len(word2) + 1):
                cost = 0 if word1[i-1] == word2[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )

        # Converti distance in similarity
        max_len = max(len(word1), len(word2))
        if max_len == 0:
            return 1.0

        distance = matrix[len(word1)][len(word2)]
        similarity = 1.0 - (distance / max_len)
        return max(0.0, similarity)

    def get_lexicon_statistics(self) -> Dict[str, Any]:
        """Ottieni statistiche sul lessico."""
        try:
            conn = self._get_connection()

            # Conta parole totali
            cursor = conn.execute("SELECT COUNT(DISTINCT word) FROM lexicon")
            total_words = cursor.fetchone()[0]

            # Conta pronunce totali
            cursor = conn.execute("SELECT COUNT(*) FROM lexicon")
            total_pronunciations = cursor.fetchone()[0]

            # Esempi di parole
            cursor = conn.execute("SELECT word FROM lexicon LIMIT 10")
            sample_words = [row['word'] for row in cursor.fetchall()]

            return {
                "total_words": total_words,
                "total_pronunciations": total_pronunciations,
                "avg_pronunciations_per_word": round(total_pronunciations / total_words, 2) if total_words > 0 else 0,
                "sample_words": sample_words,
                "g2p_available": self._g2p_available,
                "cache_size": len(self._word_cache)
            }

        except Exception as e:
            _LOGGER.error(f"Error getting lexicon statistics: {e}")
            return {
                "total_words": 0,
                "total_pronunciations": 0,
                "avg_pronunciations_per_word": 0,
                "sample_words": [],
                "g2p_available": self._g2p_available,
                "cache_size": len(self._word_cache)
            }

    def validate_word_components(self, entity_name: str) -> List[Dict[str, Any]]:
        """Valida i componenti di un nome entità."""
        # Dividi nome entità in parole
        # Gestisci separatori comuni: underscore, trattini, spazi
        words = re.split(r'[_\-\s]+', entity_name.lower())
        words = [w for w in words if w]  # Rimuovi stringhe vuote

        results = []
        for word in words:
            word_info = {
                "word": word,
                "in_lexicon": self.exists_in_lexicon(word),
                "pronunciations": [],
                "g2p_result": None,
                "similar_words": []
            }

            if word_info["in_lexicon"]:
                word_info["pronunciations"] = self.get_pronunciations(word)
            else:
                # Prova G2P
                g2p_result = self.predict_with_g2p(word)
                if g2p_result:
                    word_info["g2p_result"] = {
                        "pronunciation": g2p_result.pronunciation,
                        "confidence": g2p_result.confidence
                    }

                # Trova parole simili
                word_info["similar_words"] = self.find_similar_words(word)

            results.append(word_info)

        return results


# Cache globale per evitare multiple istanze
_lexicon_instances: Dict[str, StandaloneLexicon] = {}

def get_standalone_lexicon(model_path: Path) -> StandaloneLexicon:
    """Ottieni istanza singleton di StandaloneLexicon per un modello."""
    model_key = str(model_path)
    if model_key not in _lexicon_instances:
        _lexicon_instances[model_key] = StandaloneLexicon(model_path)
    return _lexicon_instances[model_key]