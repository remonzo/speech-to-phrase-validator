"""Core validation functionality per Speech-to-Phrase."""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .model_manager import ModelManager, ModelInfo
from .lexicon_wrapper import LexiconWrapper

_LOGGER = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Status di validazione per una parola."""
    KNOWN = "known"
    UNKNOWN = "unknown"
    GUESSED = "guessed"
    ERROR = "error"


@dataclass
class WordValidationResult:
    """Risultato della validazione di una parola."""
    word: str
    status: ValidationStatus
    is_known: bool
    pronunciations: List[List[str]]
    guessed_pronunciation: Optional[List[str]]
    similar_words: List[tuple]
    model_id: str
    confidence: float = 0.0
    notes: List[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


@dataclass
class EntityValidationResult:
    """Risultato della validazione di un'entità."""
    entity_id: str
    friendly_name: str
    words_results: List[WordValidationResult]
    overall_status: ValidationStatus
    recommendations: List[str]


@dataclass
class ValidationReport:
    """Report completo di validazione."""
    model_id: str
    total_entities: int
    known_entities: int
    unknown_entities: int
    partially_known_entities: int
    entity_results: List[EntityValidationResult]
    overall_score: float
    recommendations: List[str]


class SpeechToPhraseValidator:
    """Validatore principale per Speech-to-Phrase."""

    def __init__(self, models_path: str, train_path: str, tools_path: str):
        """Inizializza il validatore."""
        self.model_manager = ModelManager(models_path, train_path, tools_path)
        self._current_model: Optional[ModelInfo] = None
        self._current_lexicon: Optional[LexiconWrapper] = None

        # Carica il primo modello disponibile
        available_models = self.model_manager.get_models()
        if available_models:
            first_model_id = next(iter(available_models.keys()))
            self.set_model(first_model_id)

    def set_model(self, model_id: str) -> bool:
        """Imposta il modello corrente per la validazione."""
        model = self.model_manager.get_model(model_id)
        if not model:
            _LOGGER.error(f"Model not found: {model_id}")
            return False

        self._current_model = model

        # Inizializza il wrapper del lessico v1.5.9
        phonetisaurus_binary = None  # Gestito internamente per add-on HA
        self._current_lexicon = LexiconWrapper(model, phonetisaurus_binary)

        _LOGGER.info(f"Set current model to: {model_id}")
        return True

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Ottiene la lista dei modelli disponibili."""
        models = self.model_manager.get_models()
        return [
            {
                "id": model.id,
                "type": model.type.value,
                "language": model.language,
                "language_family": model.language_family,
                "description": model.description,
                "is_current": self._current_model and model.id == self._current_model.id,
                "is_ha_addon_optimized": getattr(model, 'is_ha_addon_optimized', False),
            }
            for model in models.values()
        ]

    def validate_word(self, word: str) -> WordValidationResult:
        """Valida una singola parola."""
        if not self._current_lexicon:
            return WordValidationResult(
                word=word,
                status=ValidationStatus.ERROR,
                is_known=False,
                pronunciations=[],
                guessed_pronunciation=None,
                similar_words=[],
                model_id="none",
                notes=["No model selected"]
            )

        try:
            # Verifica se la parola esiste nel lessico
            pronunciations = self._current_lexicon.lookup(word)
            is_known = len(pronunciations) > 0  # Se ha pronuncie, è conosciuta

            # Per ora non abbiamo G2P nell'add-on HA
            guessed_pronunciation = None
            similar_words = []

            # Determina lo status di validazione
            if is_known:
                status = ValidationStatus.KNOWN
                confidence = 1.0
            else:
                status = ValidationStatus.UNKNOWN
                confidence = 0.0

            # Genera note
            notes = []
            if status == ValidationStatus.KNOWN:
                if pronunciations:
                    notes.append(f"Parola riconosciuta con {len(pronunciations)} pronuncia/e")
                else:
                    notes.append("Parola presente nel lessico (pronuncie non disponibili)")
            else:
                notes.append("Parola non riconosciuta nel lessico attivo")

            return WordValidationResult(
                word=word,
                status=status,
                is_known=is_known,
                pronunciations=pronunciations,
                guessed_pronunciation=guessed_pronunciation,
                similar_words=similar_words,
                model_id=self._current_model.id if self._current_model else "unknown",
                confidence=confidence,
                notes=notes
            )

        except Exception as e:
            _LOGGER.error(f"Error validating word '{word}': {e}")
            return WordValidationResult(
                word=word,
                status=ValidationStatus.ERROR,
                is_known=False,
                pronunciations=[],
                guessed_pronunciation=None,
                similar_words=[],
                model_id=self._current_model.id if self._current_model else "unknown",
                notes=[f"Validation error: {str(e)}"]
            )

    def validate_entity_name(self, entity_name: str) -> EntityValidationResult:
        """Valida il nome di un'entità (che può contenere più parole)."""
        # Divide il nome dell'entità in parole
        words = entity_name.lower().replace("_", " ").replace("-", " ").split()

        word_results = []
        for word in words:
            if word:  # Salta parole vuote
                result = self.validate_word(word)
                word_results.append(result)

        # Determina lo status complessivo
        if not word_results:
            overall_status = ValidationStatus.ERROR
        elif all(r.status == ValidationStatus.KNOWN for r in word_results):
            overall_status = ValidationStatus.KNOWN
        elif any(r.status == ValidationStatus.UNKNOWN for r in word_results):
            overall_status = ValidationStatus.UNKNOWN
        else:
            overall_status = ValidationStatus.GUESSED

        # Genera raccomandazioni
        recommendations = []
        unknown_words = [r for r in word_results if r.status == ValidationStatus.UNKNOWN]

        if unknown_words:
            recommendations.append(f"Considera di sostituire: {', '.join(r.word for r in unknown_words)}")

            # Suggerisci alternative
            for word_result in unknown_words:
                if word_result.similar_words:
                    best_similar = word_result.similar_words[0]
                    recommendations.append(f"'{word_result.word}' → '{best_similar[0]}' (similarità: {best_similar[1]:.2f})")

        if overall_status == ValidationStatus.GUESSED:
            recommendations.append("Alcune parole usano pronunce stimate - testa accuratezza vocale")

        return EntityValidationResult(
            entity_id=entity_name,
            friendly_name=entity_name,
            words_results=word_results,
            overall_status=overall_status,
            recommendations=recommendations
        )

    def validate_entities_list(self, entities: List[str]) -> ValidationReport:
        """Valida una lista di entità."""
        if not self._current_model:
            return ValidationReport(
                model_id="none",
                total_entities=0,
                known_entities=0,
                unknown_entities=0,
                partially_known_entities=0,
                entity_results=[],
                overall_score=0.0,
                recommendations=["No model selected"]
            )

        entity_results = []
        known_count = 0
        unknown_count = 0
        partially_known_count = 0

        for entity in entities:
            result = self.validate_entity_name(entity)
            entity_results.append(result)

            if result.overall_status == ValidationStatus.KNOWN:
                known_count += 1
            elif result.overall_status == ValidationStatus.UNKNOWN:
                unknown_count += 1
            else:
                partially_known_count += 1

        total_entities = len(entities)
        overall_score = known_count / total_entities if total_entities > 0 else 0.0

        # Genera raccomandazioni generali
        recommendations = []
        if unknown_count > 0:
            recommendations.append(f"{unknown_count} entità contengono parole non riconosciute")

        if partially_known_count > 0:
            recommendations.append(f"{partially_known_count} entità usano pronunce stimate")

        if overall_score < 0.8:
            recommendations.append("Considera di rinominare entità con parole più comuni")

        return ValidationReport(
            model_id=self._current_model.id,
            total_entities=total_entities,
            known_entities=known_count,
            unknown_entities=unknown_count,
            partially_known_entities=partially_known_count,
            entity_results=entity_results,
            overall_score=overall_score,
            recommendations=recommendations
        )

    def get_model_statistics(self) -> Optional[Dict[str, Any]]:
        """Ottiene statistiche sul modello corrente."""
        if not self._current_lexicon:
            return None

        return self._current_lexicon.get_statistics()

    def suggest_alternatives(self, word: str, max_suggestions: int = 5) -> List[Dict[str, Any]]:
        """Suggerisce alternative per una parola (limitato nell'add-on HA)."""
        if not self._current_lexicon:
            return []

        # Per add-on HA: funzionalità limitata, nessun suggerimento avanzato
        return []