"""FastAPI application per Speech-to-Phrase Validator."""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Handle both standalone and addon import scenarios
try:
    from ..validator import SpeechToPhraseValidator
    from ..validator.predictor import get_predictor
except ImportError:
    # Standalone mode - adjust path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from validator import SpeechToPhraseValidator
    from validator.predictor import get_predictor

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("STP_LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
_LOGGER = logging.getLogger(__name__)

# Configurazione da variabili d'ambiente
MODELS_PATH = os.getenv("STP_MODELS_PATH", "/share/speech-to-phrase/models")
TRAIN_PATH = os.getenv("STP_TRAIN_PATH", "/share/speech-to-phrase/train")
TOOLS_PATH = os.getenv("STP_TOOLS_PATH", "/share/speech-to-phrase/tools")

# Initialize FastAPI app
app = FastAPI(
    title="Speech-to-Phrase Validator",
    description="Tool di validazione e ottimizzazione per Speech-to-Phrase",
    version="0.1.0",
)

# Setup templates and static files
BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

# Handle Home Assistant Ingress paths
def get_ingress_path(request: Request) -> str:
    """Get the ingress path prefix if available."""
    # Check for Home Assistant ingress headers
    ingress_path = request.headers.get("X-Ingress-Path", "")
    if not ingress_path:
        # Fallback: check if we're behind a proxy
        forwarded_prefix = request.headers.get("X-Forwarded-Prefix", "")
        if forwarded_prefix:
            ingress_path = forwarded_prefix
    return ingress_path.rstrip("/")

# Mount static files with proper path handling
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")

# Initialize validator and predictor
validator = None
predictor = None

# Pydantic models for API
class WordValidationRequest(BaseModel):
    word: str
    model_id: Optional[str] = None

class EntityListRequest(BaseModel):
    entities: List[str]
    model_id: Optional[str] = None

class SuggestionsRequest(BaseModel):
    word: str
    max_suggestions: int = 5
    model_id: Optional[str] = None

# New Pydantic models for Predictor
class WordPredictionRequest(BaseModel):
    word: str

class EntityPredictionRequest(BaseModel):
    entity_name: str


@app.on_event("startup")
async def startup_event():
    """Inizializza il validatore e predictor all'avvio."""
    global validator, predictor

    _LOGGER.info("Starting Speech-to-Phrase Validator...")
    _LOGGER.info(f"Models path: {MODELS_PATH}")
    _LOGGER.info(f"Train path: {TRAIN_PATH}")
    _LOGGER.info(f"Tools path: {TOOLS_PATH}")

    try:
        validator = SpeechToPhraseValidator(MODELS_PATH, TRAIN_PATH, TOOLS_PATH)
        available_models = validator.get_available_models()
        _LOGGER.info(f"Initialized validator with {len(available_models)} models")

        if available_models:
            _LOGGER.info(f"Available models: {[m['id'] for m in available_models]}")
        else:
            _LOGGER.warning("No models found! Check Speech-to-Phrase installation.")

    except Exception as e:
        _LOGGER.error(f"Failed to initialize validator: {e}")
        validator = None

    # Initialize predictor
    try:
        _LOGGER.info("Initializing Speech-to-Phrase Predictor...")
        predictor = await get_predictor()
        if predictor.is_initialized():
            _LOGGER.info("Predictor initialized successfully")
        else:
            _LOGGER.warning("Predictor initialization incomplete")
    except Exception as e:
        _LOGGER.error(f"Failed to initialize predictor: {e}")
        predictor = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Pagina principale dell'interfaccia web."""
    models = []
    current_model = None

    if validator:
        models = validator.get_available_models()
        current_model = next((m for m in models if m["is_current"]), None)

    ingress_path = get_ingress_path(request)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "models": models,
        "current_model": current_model,
        "has_validator": validator is not None,
        "ingress_path": ingress_path
    })


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok" if validator else "error",
        "message": "Validator initialized" if validator else "Validator not initialized",
        "models_available": len(validator.get_available_models()) if validator else 0
    }


@app.get("/api/models")
async def get_models():
    """Ottiene la lista dei modelli disponibili."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    return validator.get_available_models()


@app.post("/api/models/{model_id}/select")
async def select_model(model_id: str):
    """Seleziona un modello per la validazione."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    success = validator.set_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    return {"status": "success", "model_id": model_id}


@app.post("/api/validate/word")
async def validate_word(request: WordValidationRequest):
    """Valida una singola parola."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    # Cambia modello se specificato
    if request.model_id:
        success = validator.set_model(request.model_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")

    result = validator.validate_word(request.word)

    # Converte il risultato in un dict JSON-serializable
    return {
        "word": result.word,
        "status": result.status.value,
        "is_known": result.is_known,
        "pronunciations": result.pronunciations,
        "guessed_pronunciation": result.guessed_pronunciation,
        "similar_words": [{"word": w, "score": s} for w, s in result.similar_words],
        "model_id": result.model_id,
        "confidence": result.confidence,
        "notes": result.notes
    }


@app.post("/api/validate/entity")
async def validate_entity(entity_name: str, model_id: Optional[str] = None):
    """Valida il nome di un'entità."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    # Cambia modello se specificato
    if model_id:
        success = validator.set_model(model_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    result = validator.validate_entity_name(entity_name)

    return {
        "entity_id": result.entity_id,
        "friendly_name": result.friendly_name,
        "words_results": [
            {
                "word": wr.word,
                "status": wr.status.value,
                "is_known": wr.is_known,
                "pronunciations": wr.pronunciations,
                "guessed_pronunciation": wr.guessed_pronunciation,
                "similar_words": [{"word": w, "score": s} for w, s in wr.similar_words],
                "confidence": wr.confidence,
                "notes": wr.notes
            }
            for wr in result.words_results
        ],
        "overall_status": result.overall_status.value,
        "recommendations": result.recommendations
    }


@app.post("/api/validate/entities")
async def validate_entities(request: EntityListRequest):
    """Valida una lista di entità."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    # Cambia modello se specificato
    if request.model_id:
        success = validator.set_model(request.model_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")

    report = validator.validate_entities_list(request.entities)

    return {
        "model_id": report.model_id,
        "total_entities": report.total_entities,
        "known_entities": report.known_entities,
        "unknown_entities": report.unknown_entities,
        "partially_known_entities": report.partially_known_entities,
        "overall_score": report.overall_score,
        "recommendations": report.recommendations,
        "entity_results": [
            {
                "entity_id": er.entity_id,
                "friendly_name": er.friendly_name,
                "overall_status": er.overall_status.value,
                "recommendations": er.recommendations,
                "words_count": len(er.words_results),
                "known_words": sum(1 for wr in er.words_results if wr.is_known),
            }
            for er in report.entity_results
        ]
    }


@app.post("/api/suggest")
async def suggest_alternatives(request: SuggestionsRequest):
    """Suggerisce alternative per una parola."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    # Cambia modello se specificato
    if request.model_id:
        success = validator.set_model(request.model_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")

    suggestions = validator.suggest_alternatives(request.word, request.max_suggestions)
    return {"word": request.word, "suggestions": suggestions}


@app.get("/api/stats")
async def get_statistics():
    """Ottiene statistiche sul modello corrente."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    stats = validator.get_model_statistics()
    if not stats:
        raise HTTPException(status_code=400, detail="No model selected")

    return stats


# NEW: Predictor API Endpoints

@app.post("/api/predict/word")
async def predict_word_recognition(request: WordPredictionRequest):
    """Predici la riconoscibilità di una parola prima di aggiungerla ad Assist."""
    if not predictor:
        raise HTTPException(status_code=503, detail="Predictor not initialized")

    if not predictor.is_initialized():
        raise HTTPException(status_code=503, detail="Predictor not ready")

    try:
        prediction = predictor.predict_word(request.word)

        return {
            "word": prediction.word,
            "confidence": prediction.confidence.value,
            "confidence_score": prediction.confidence_score,
            "in_lexicon": prediction.in_lexicon,
            "lexicon_pronunciations": prediction.lexicon_pronunciations,
            "g2p_available": prediction.g2p_available,
            "g2p_pronunciation": prediction.g2p_pronunciation,
            "g2p_confidence": prediction.g2p_confidence,
            "similar_words": [{"word": w[0], "similarity": w[1]} for w in prediction.similar_words],
            "recommendation": prediction.recommendation,
            "notes": prediction.notes
        }
    except Exception as e:
        _LOGGER.error(f"Error predicting word '{request.word}': {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/api/predict/entity")
async def predict_entity_recognition(request: EntityPredictionRequest):
    """Predici la riconoscibilità di un'entità completa prima di aggiungerla ad Assist."""
    if not predictor:
        raise HTTPException(status_code=503, detail="Predictor not initialized")

    if not predictor.is_initialized():
        raise HTTPException(status_code=503, detail="Predictor not ready")

    try:
        prediction = predictor.predict_entity(request.entity_name)

        return {
            "entity_name": prediction.entity_name,
            "overall_confidence": prediction.overall_confidence.value,
            "overall_score": prediction.overall_score,
            "recognition_percentage": prediction.recognition_percentage,
            "word_predictions": [
                {
                    "word": wp.word,
                    "confidence": wp.confidence.value,
                    "confidence_score": wp.confidence_score,
                    "in_lexicon": wp.in_lexicon,
                    "lexicon_pronunciations": wp.lexicon_pronunciations,
                    "g2p_available": wp.g2p_available,
                    "g2p_pronunciation": wp.g2p_pronunciation,
                    "g2p_confidence": wp.g2p_confidence,
                    "similar_words": [{"word": w[0], "similarity": w[1]} for w in wp.similar_words],
                    "recommendation": wp.recommendation,
                    "notes": wp.notes
                }
                for wp in prediction.word_predictions
            ],
            "recommendations": prediction.recommendations,
            "suggested_alternatives": prediction.suggested_alternatives
        }
    except Exception as e:
        _LOGGER.error(f"Error predicting entity '{request.entity_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/api/predict/stats")
async def get_predictor_statistics():
    """Ottiene statistiche sul predictor e modelli disponibili."""
    if not predictor:
        raise HTTPException(status_code=503, detail="Predictor not initialized")

    try:
        stats = await predictor.get_predictor_statistics()
        return stats
    except Exception as e:
        _LOGGER.error(f"Error getting predictor statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Statistics error: {str(e)}")


@app.get("/api/predict/health")
async def predictor_health_check():
    """Health check specifico per il predictor."""
    return {
        "predictor_available": predictor is not None,
        "predictor_initialized": predictor.is_initialized() if predictor else False,
        "current_model": predictor._current_model if predictor and predictor.is_initialized() else None,
        "status": "ready" if (predictor and predictor.is_initialized()) else "not_ready"
    }


if __name__ == "__main__":
    import uvicorn

    # Configurazione per il run
    port = int(os.getenv("PORT", "8099"))
    host = os.getenv("HOST", "0.0.0.0")

    _LOGGER.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        log_level=os.getenv("STP_LOG_LEVEL", "info").lower(),
        reload=False
    )