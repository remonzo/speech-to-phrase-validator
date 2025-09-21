"""Speech-to-Phrase Predictor - Core Logic.

Predice la riconoscibilità di parole ed entità prima dell'aggiunta ad Assist.
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .model_downloader import get_model_downloader
from .standalone_lexicon import get_standalone_lexicon, StandaloneLexicon

_LOGGER = logging.getLogger(__name__)


class RecognitionConfidence(str, Enum):
    """Livelli di confidenza riconoscimento."""
    EXCELLENT = "excellent"    # 95-100% - Parola nel lessico completo
    GOOD = "good"             # 70-94% - G2P disponibile, alta confidenza
    MODERATE = "moderate"     # 50-69% - G2P disponibile, media confidenza
    POOR = "poor"            # 25-49% - Parole simili trovate
    UNKNOWN = "unknown"      # 0-24% - Nessuna informazione disponibile


@dataclass
class WordPrediction:
    """Predizione per singola parola."""
    word: str
    confidence: RecognitionConfidence
    confidence_score: float  # 0.0 - 1.0
    in_lexicon: bool
    lexicon_pronunciations: List[List[str]]
    g2p_available: bool
    g2p_pronunciation: Optional[List[str]]
    g2p_confidence: Optional[float]
    similar_words: List[tuple]
    recommendation: str
    notes: List[str]


@dataclass
class EntityPrediction:
    """Predizione per entità completa."""
    entity_name: str
    word_predictions: List[WordPrediction]
    overall_confidence: RecognitionConfidence
    overall_score: float
    recognition_percentage: float  # Percentuale parole riconoscibili
    recommendations: List[str]
    suggested_alternatives: List[str]


class SpeechToPhrasePredictor:
    """Predictor principale per riconoscibilità Speech-to-Phrase."""

    def __init__(self, models_dir: str = "/data/speech_to_phrase_validator/models"):
        """Inizializza il predictor."""
        self.models_dir = Path(models_dir)
        self.downloader = get_model_downloader()
        self._current_model: Optional[str] = None
        self._lexicon: Optional[StandaloneLexicon] = None

    async def initialize(self, model_id: str = "it_IT-rhasspy") -> bool:
        """Inizializza il predictor con un modello specifico."""
        try:
            # Assicura che il modello sia disponibile
            _LOGGER.info(f"Initializing predictor with model {model_id}")
            if not await self.downloader.ensure_model_available(model_id):
                _LOGGER.error(f"Failed to ensure model {model_id} is available")
                return False

            # Carica lexicon
            model_path = self.downloader.get_model_path(model_id)
            self._lexicon = get_standalone_lexicon(model_path)
            self._current_model = model_id

            _LOGGER.info(f"Predictor initialized successfully with {model_id}")
            return True

        except Exception as e:
            _LOGGER.error(f"Error initializing predictor: {e}")
            return False

    def is_initialized(self) -> bool:
        """Verifica se il predictor è inizializzato."""
        return self._lexicon is not None and self._current_model is not None

    def _calculate_confidence_level(self, score: float) -> RecognitionConfidence:
        """Calcola livello di confidenza da score numerico."""
        if score >= 0.95:
            return RecognitionConfidence.EXCELLENT
        elif score >= 0.70:
            return RecognitionConfidence.GOOD
        elif score >= 0.50:
            return RecognitionConfidence.MODERATE
        elif score >= 0.25:
            return RecognitionConfidence.POOR
        else:
            return RecognitionConfidence.UNKNOWN

    def _generate_word_recommendation(self, prediction: WordPrediction) -> str:
        """Genera raccomandazione per una parola."""
        if prediction.in_lexicon:
            return "✅ Ottimale - Riconosciuta perfettamente da Speech-to-Phrase"

        if prediction.g2p_available and prediction.g2p_confidence and prediction.g2p_confidence > 0.7:
            return "🔍 Buona - Pronuncia stimata con alta confidenza"

        if prediction.g2p_available and prediction.g2p_confidence and prediction.g2p_confidence > 0.5:
            return "⚠️ Media - Pronuncia stimata, testare accuratezza vocale"

        if prediction.similar_words:
            best_similar = prediction.similar_words[0]
            return f"💡 Suggerimento - Considera '{best_similar[0]}' (similarità {best_similar[1]:.0%})"

        return "❌ Problematica - Difficilmente riconoscibile, rinominare consigliato"

    def predict_word(self, word: str) -> WordPrediction:
        """Predici riconoscibilità di una singola parola."""
        if not self.is_initialized():
            raise ValueError("Predictor not initialized")

        try:
            # Verifica nel lessico
            in_lexicon = self._lexicon.exists_in_lexicon(word)
            lexicon_pronunciations = []

            if in_lexicon:
                lexicon_pronunciations = self._lexicon.get_pronunciations(word)
                confidence_score = 1.0
                g2p_available = False
                g2p_pronunciation = None
                g2p_confidence = None
                notes = [f"Parola presente nel lessico con {len(lexicon_pronunciations)} pronuncia/e"]
            else:
                # Prova G2P
                g2p_result = self._lexicon.predict_with_g2p(word)
                g2p_available = g2p_result is not None

                if g2p_available:
                    g2p_pronunciation = g2p_result.pronunciation
                    g2p_confidence = g2p_result.confidence
                    confidence_score = g2p_confidence
                    notes = ["Pronuncia stimata tramite modello G2P"]
                else:
                    g2p_pronunciation = None
                    g2p_confidence = None
                    confidence_score = 0.0
                    notes = ["Parola non trovata nel lessico e G2P non disponibile"]

            # Trova parole simili se non nel lessico
            similar_words = []
            if not in_lexicon:
                similar_words = self._lexicon.find_similar_words(word)
                if similar_words:
                    # Aumenta confidence se ci sono parole simili
                    similarity_boost = similar_words[0][1] * 0.3  # Max 30% boost
                    confidence_score = min(1.0, confidence_score + similarity_boost)
                    notes.append(f"Trovate {len(similar_words)} parole simili")

            confidence_level = self._calculate_confidence_level(confidence_score)

            prediction = WordPrediction(
                word=word,
                confidence=confidence_level,
                confidence_score=confidence_score,
                in_lexicon=in_lexicon,
                lexicon_pronunciations=lexicon_pronunciations,
                g2p_available=g2p_available,
                g2p_pronunciation=g2p_pronunciation,
                g2p_confidence=g2p_confidence,
                similar_words=similar_words,
                recommendation="",  # Sarà calcolato dopo
                notes=notes
            )

            prediction.recommendation = self._generate_word_recommendation(prediction)
            return prediction

        except Exception as e:
            _LOGGER.error(f"Error predicting word '{word}': {e}")
            return WordPrediction(
                word=word,
                confidence=RecognitionConfidence.UNKNOWN,
                confidence_score=0.0,
                in_lexicon=False,
                lexicon_pronunciations=[],
                g2p_available=False,
                g2p_pronunciation=None,
                g2p_confidence=None,
                similar_words=[],
                recommendation="❌ Errore durante analisi",
                notes=[f"Errore: {str(e)}"]
            )

    def predict_entity(self, entity_name: str) -> EntityPrediction:
        """Predici riconoscibilità di un'entità completa."""
        if not self.is_initialized():
            raise ValueError("Predictor not initialized")

        try:
            # Dividi entità in parole
            word_components = self._lexicon.validate_word_components(entity_name)

            # Predici ogni parola
            word_predictions = []
            total_score = 0.0

            for component in word_components:
                word = component["word"]
                word_pred = self.predict_word(word)
                word_predictions.append(word_pred)
                total_score += word_pred.confidence_score

            # Calcola score complessivo
            if word_predictions:
                overall_score = total_score / len(word_predictions)
                recognition_percentage = (sum(1 for wp in word_predictions
                                           if wp.confidence_score >= 0.7) / len(word_predictions)) * 100
            else:
                overall_score = 0.0
                recognition_percentage = 0.0

            overall_confidence = self._calculate_confidence_level(overall_score)

            # Genera raccomandazioni
            recommendations = self._generate_entity_recommendations(word_predictions, overall_score)

            # Suggerisci alternative
            alternatives = self._suggest_entity_alternatives(entity_name, word_predictions)

            return EntityPrediction(
                entity_name=entity_name,
                word_predictions=word_predictions,
                overall_confidence=overall_confidence,
                overall_score=overall_score,
                recognition_percentage=recognition_percentage,
                recommendations=recommendations,
                suggested_alternatives=alternatives
            )

        except Exception as e:
            _LOGGER.error(f"Error predicting entity '{entity_name}': {e}")
            return EntityPrediction(
                entity_name=entity_name,
                word_predictions=[],
                overall_confidence=RecognitionConfidence.UNKNOWN,
                overall_score=0.0,
                recognition_percentage=0.0,
                recommendations=[f"Errore durante analisi: {str(e)}"],
                suggested_alternatives=[]
            )

    def _generate_entity_recommendations(self, word_predictions: List[WordPrediction],
                                       overall_score: float) -> List[str]:
        """Genera raccomandazioni per entità."""
        recommendations = []

        # Analizza problemi specifici
        unknown_words = [wp for wp in word_predictions if wp.confidence == RecognitionConfidence.UNKNOWN]
        poor_words = [wp for wp in word_predictions if wp.confidence == RecognitionConfidence.POOR]
        g2p_words = [wp for wp in word_predictions if wp.g2p_available and not wp.in_lexicon]

        if unknown_words:
            recommendations.append(f"⚠️ {len(unknown_words)} parole non riconoscibili: {', '.join(wp.word for wp in unknown_words)}")

        if poor_words:
            recommendations.append(f"📝 {len(poor_words)} parole problematiche, considera rinominare")

        if g2p_words:
            recommendations.append(f"🧪 {len(g2p_words)} parole usano pronuncia stimata - testare accuratezza")

        if overall_score >= 0.9:
            recommendations.append("✅ Entità eccellente per Speech-to-Phrase")
        elif overall_score >= 0.7:
            recommendations.append("👍 Entità buona, funzionerà bene")
        elif overall_score >= 0.5:
            recommendations.append("⚠️ Entità mediocre, possibili problemi di riconoscimento")
        else:
            recommendations.append("❌ Entità problematica, rinominare fortemente consigliato")

        return recommendations

    def _suggest_entity_alternatives(self, entity_name: str,
                                   word_predictions: List[WordPrediction]) -> List[str]:
        """Suggerisci alternative per entità."""
        alternatives = []

        # Per ogni parola problematica, suggerisci alternative
        for wp in word_predictions:
            if wp.confidence in [RecognitionConfidence.POOR, RecognitionConfidence.UNKNOWN]:
                if wp.similar_words:
                    best_similar = wp.similar_words[0]
                    # Sostituisci parola originale con suggerimento
                    new_entity = entity_name.replace(wp.word, best_similar[0])
                    alternatives.append(f"{new_entity} (sostituisci '{wp.word}' → '{best_similar[0]}')")

        # Suggerimenti comuni per migliorare riconoscibilità
        if len(word_predictions) > 2:  # Entità complesse
            alternatives.append("Considera abbreviazioni: es. 'luce_soggiorno' → 'luce_sala'")

        if any('_' in wp.word for wp in word_predictions):
            alternatives.append("Evita underscore: usa trattini o spazi")

        return alternatives[:3]  # Limita a 3 suggerimenti

    async def get_predictor_statistics(self) -> Dict[str, Any]:
        """Ottieni statistiche sul predictor."""
        if not self.is_initialized():
            return {"error": "Predictor not initialized"}

        try:
            lexicon_stats = self._lexicon.get_lexicon_statistics()
            downloaded_models = self.downloader.get_downloaded_models()

            return {
                "current_model": self._current_model,
                "lexicon": lexicon_stats,
                "downloaded_models": list(downloaded_models.keys()),
                "models_info": downloaded_models
            }

        except Exception as e:
            _LOGGER.error(f"Error getting predictor statistics: {e}")
            return {"error": str(e)}


# Istanza globale singleton
_predictor_instance: Optional[SpeechToPhrasePredictor] = None

async def get_predictor() -> SpeechToPhrasePredictor:
    """Ottieni istanza singleton del predictor."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = SpeechToPhrasePredictor()
        await _predictor_instance.initialize()
    return _predictor_instance