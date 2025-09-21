"""Gestione modelli Speech-to-Phrase - Ottimizzato per Add-on Home Assistant v1.5.8."""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

_LOGGER = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Tipo di modello."""
    KALDI = "kaldi"
    COQUI_STT = "coqui-stt"


@dataclass
class ModelInfo:
    """Informazioni su un modello."""
    id: str
    type: ModelType
    language: str
    language_family: str
    description: str
    model_path: Path
    g2p_path: Optional[Path] = None
    lexicon_db_path: Optional[Path] = None
    is_available: bool = False
    is_ha_addon_optimized: bool = False


class ModelManager:
    """Gestisce i modelli Speech-to-Phrase disponibili - Ottimizzato per Add-on HA."""

    def __init__(self, models_path: str, train_path: str, tools_path: str):
        """Inizializza il manager dei modelli."""
        self.models_path = Path(models_path)
        self.train_path = Path(train_path)
        self.tools_path = Path(tools_path) if tools_path else None
        self._models: Dict[str, ModelInfo] = {}
        self._scan_models()

    def _scan_models(self) -> None:
        """Scansiona la directory dei modelli per trovare quelli disponibili."""
        # Per add-on Home Assistant, usa la directory train esposta
        search_path = self.train_path if self.train_path.exists() else self.models_path
        _LOGGER.info(f"Scanning models in {search_path} (HA add-on optimized)")

        if not search_path.exists():
            _LOGGER.warning(f"Models directory does not exist: {search_path}")
            return

        for model_dir in search_path.iterdir():
            if not model_dir.is_dir():
                continue

            model_id = model_dir.name
            _LOGGER.debug(f"Found potential model: {model_id}")

            # Determina il tipo di modello
            model_type = self._detect_model_type(model_dir)
            if model_type is None:
                _LOGGER.debug(f"Could not determine model type for {model_id}")
                continue

            # Estrae informazioni dal nome del modello
            language, language_family = self._parse_model_language(model_id)

            # Ottimizzazione per add-on HA: cerca solo lessico di testo
            lexicon_db_path = self._find_lexicon_file(model_dir, model_type)

            # G2P non disponibile nell'add-on HA (gestito internamente)
            g2p_path = None
            is_ha_addon = search_path == self.train_path

            model_info = ModelInfo(
                id=model_id,
                type=model_type,
                language=language,
                language_family=language_family,
                description=f"{language.title()} {model_type.value} model (HA add-on)",
                model_path=model_dir,
                g2p_path=g2p_path,
                lexicon_db_path=lexicon_db_path,
                is_available=True,
                is_ha_addon_optimized=is_ha_addon
            )

            self._models[model_id] = model_info
            status = "HA add-on optimized" if is_ha_addon else "standalone"
            _LOGGER.info(f"Registered model: {model_id} ({model_type.value}, {status})")

    def _find_lexicon_file(self, model_dir: Path, model_type: ModelType) -> Optional[Path]:
        """Trova il file del lessico con priorità per formato add-on HA."""
        if model_type == ModelType.KALDI:
            # Prima priorità: lessico di testo Speech-to-Phrase (add-on HA)
            stp_lexicon = model_dir / "data" / "local" / "dict" / "lexicon.txt"
            if stp_lexicon.exists():
                return stp_lexicon

            # Seconda priorità: database SQLite tradizionale (standalone)
            phones_dir = model_dir / "model" / "phones"
            if phones_dir.exists():
                for lexicon_file in ["lexicon.db", "lexicon.sqlite", "word_phonemes.db"]:
                    potential_db = phones_dir / lexicon_file
                    if potential_db.exists():
                        return potential_db

        return None

    def _detect_model_type(self, model_dir: Path) -> Optional[ModelType]:
        """Rileva il tipo di modello dalla struttura delle directory."""
        # Prima priorità: Speech-to-Phrase add-on HA structure
        stp_graph = model_dir / "graph" / "HCLG.fst"
        stp_lang = model_dir / "data" / "lang"
        if stp_graph.exists() and stp_lang.exists():
            return ModelType.KALDI

        # Seconda priorità: Kaldi tradizionale
        kaldi_model = model_dir / "model" / "model" / "final.mdl"
        if kaldi_model.exists():
            return ModelType.KALDI

        # Terza priorità: Coqui STT
        for coqui_file in model_dir.glob("*.pbmm"):
            return ModelType.COQUI_STT
        for coqui_file in model_dir.glob("*.tflite"):
            return ModelType.COQUI_STT

        return None

    def _parse_model_language(self, model_id: str) -> Tuple[str, str]:
        """Estrae informazioni sulla lingua dal nome del modello."""
        # Esempi: it_IT-rhasspy, en_US-kaldi, fr_FR-coqui
        if '_' in model_id and '-' in model_id:
            lang_part = model_id.split('-')[0]
            if '_' in lang_part:
                language = lang_part.split('_')[0]
                language_family = lang_part
            else:
                language = lang_part
                language_family = lang_part
        else:
            language = "unknown"
            language_family = "unknown"

        return language, language_family

    def get_models(self) -> Dict[str, ModelInfo]:
        """Restituisce tutti i modelli disponibili."""
        return self._models.copy()

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Restituisce informazioni su un modello specifico."""
        return self._models.get(model_id)

    def has_models(self) -> bool:
        """Verifica se ci sono modelli disponibili."""
        return len(self._models) > 0

    def get_ha_addon_models(self) -> Dict[str, ModelInfo]:
        """Restituisce solo i modelli ottimizzati per add-on HA."""
        return {
            model_id: model_info
            for model_id, model_info in self._models.items()
            if model_info.is_ha_addon_optimized
        }

    def get_model_statistics(self) -> Dict[str, int]:
        """Restituisce statistiche sui modelli."""
        total = len(self._models)
        ha_addon = len(self.get_ha_addon_models())
        standalone = total - ha_addon

        return {
            "total": total,
            "ha_addon_optimized": ha_addon,
            "standalone": standalone,
            "kaldi": len([m for m in self._models.values() if m.type == ModelType.KALDI]),
            "coqui_stt": len([m for m in self._models.values() if m.type == ModelType.COQUI_STT])
        }