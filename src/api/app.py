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
except ImportError:
    # Standalone mode - adjust path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from validator import SpeechToPhraseValidator

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

# Import centralized version
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from version import VERSION

# Initialize FastAPI app
app = FastAPI(
    title="Speech-to-Phrase Validator",
    description="Tool di validazione e ottimizzazione per Speech-to-Phrase",
    version=VERSION,
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

# Initialize validator
validator = None

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

class EntityValidationRequest(BaseModel):
    entity_name: str
    model_id: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Inizializza il validatore all'avvio."""
    global validator

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
        "ingress_path": ingress_path,
        "version": VERSION
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
    """Ottiene la lista dei modelli disponibili con informazioni HA add-on."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    models = validator.get_available_models()

    # Aggiungi informazioni specifiche per HA add-on v1.5.8
    enhanced_models = []
    for model in models:
        if hasattr(validator, 'model_manager') and validator.model_manager:
            model_info = validator.model_manager.get_model(model.get('id'))
            if model_info:
                enhanced_model = model.copy()
                enhanced_model['is_ha_addon_optimized'] = getattr(model_info, 'is_ha_addon_optimized', False)
                enhanced_model['lexicon_type'] = 'text_file' if getattr(model_info, 'is_ha_addon_optimized', False) else 'sqlite_database'

                # Aggiungi statistiche lessico
                if hasattr(validator, 'current_lexicon') and validator.current_lexicon:
                    stats = validator.current_lexicon.get_statistics()
                    enhanced_model['lexicon_words'] = stats.get('total_words', 0)
                    enhanced_model['lexicon_type'] = stats.get('lexicon_type', 'unknown')
                    enhanced_model['g2p_available'] = stats.get('phonetisaurus_available', False)

                enhanced_models.append(enhanced_model)
            else:
                enhanced_models.append(model)
        else:
            enhanced_models.append(model)

    return {'models': enhanced_models}


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
    """Valida una singola parola con formato semplificato v1.5.8."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    # Cambia modello se specificato
    if request.model_id:
        success = validator.set_model(request.model_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")

    result = validator.validate_word(request.word)

    # Formato semplificato per compatibilità frontend v1.5.8
    return {
        "word": result.word,
        "exists": result.is_known,
        "pronunciations": result.pronunciations,
        "suggestions": [w for w, s in result.similar_words] if hasattr(result, 'similar_words') else []
    }


@app.post("/api/validate/entity")
async def validate_entity(request: EntityValidationRequest):
    """Valida il nome di un'entità con formato migliorato v1.5.8."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    # Cambia modello se specificato
    if request.model_id:
        success = validator.set_model(request.model_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")

    # Semplifica validazione per compatibilità con frontend v1.5.8
    words = request.entity_name.replace('_', ' ').replace('-', ' ').split()
    validation_results = []

    for word in words:
        if word.strip():
            word_result = validator.validate_word(word.strip())
            validation_results.append({
                'word': word_result.word,
                'exists': word_result.is_known,
                'pronunciations': word_result.pronunciations
            })

    return {
        "entity_name": request.entity_name,
        "validation_results": validation_results
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


@app.get("/api/statistics")
async def get_statistics():
    """Ottiene statistiche avanzate HA add-on v1.5.8."""
    if not validator:
        raise HTTPException(status_code=503, detail="Validator not initialized")

    base_stats = validator.get_model_statistics()

    # Inizializza statistiche di base se None
    if not base_stats:
        base_stats = {
            "total_words": 0,
            "lexicon_type": "unknown",
            "model_path": "",
            "is_ha_addon_optimized": False
        }

    # Aggiungi informazioni specifiche HA add-on
    enhanced_stats = base_stats.copy()

    if hasattr(validator, 'model_manager') and validator.model_manager:
        model_stats = validator.model_manager.get_model_statistics()
        enhanced_stats.update({
            'model_count': model_stats.get('total', 0),
            'ha_addon_models': model_stats.get('ha_addon_optimized', 0),
            'is_ha_addon': model_stats.get('ha_addon_optimized', 0) > 0
        })

        # Aggiungi informazioni modello corrente
        current_models = validator.get_available_models()
        if current_models:
            current_model = current_models[0] if current_models else {}
            model_info = validator.model_manager.get_model(current_model.get('id', ''))
            if model_info:
                enhanced_stats.update({
                    'model_type': model_info.type.value if hasattr(model_info.type, 'value') else str(model_info.type),
                    'model_language': model_info.language,
                    'is_ha_addon_optimized': getattr(model_info, 'is_ha_addon_optimized', False)
                })

    # Aggiungi statistiche lessico dettagliate
    if hasattr(validator, 'current_lexicon') and validator.current_lexicon:
        lexicon_stats = validator.current_lexicon.get_statistics()
        enhanced_stats.update({
            'lexicon_words': lexicon_stats.get('total_words', 0),
            'lexicon_type': lexicon_stats.get('lexicon_type', 'unknown'),
            'ha_addon_info': lexicon_stats.get('is_ha_addon_optimized', False)
        })

    return enhanced_stats


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