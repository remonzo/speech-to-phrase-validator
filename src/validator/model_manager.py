"""Gestione modelli Speech-to-Phrase."""

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


class ModelManager:
    """Gestisce i modelli Speech-to-Phrase disponibili."""

    def __init__(self, models_path: str, train_path: str, tools_path: str):
        """Inizializza il manager dei modelli."""
        self.models_path = Path(models_path)
        self.train_path = Path(train_path)
        self.tools_path = Path(tools_path)
        self._models: Dict[str, ModelInfo] = {}
        self._scan_models()

    def _scan_models(self) -> None:
        """Scansiona la directory dei modelli per trovare quelli disponibili."""
        _LOGGER.info(f"Scanning models in {self.models_path}")

        if not self.models_path.exists():
            _LOGGER.warning(f"Models directory does not exist: {self.models_path}")
            return

        for model_dir in self.models_path.iterdir():
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

            # Costruisce percorsi importanti
            g2p_path = model_dir / "g2p.fst"
            lexicon_db_path = None

            if model_type == ModelType.KALDI:
                # Per Kaldi, cerca il database del lessico
                phones_dir = model_dir / "model" / "phones"
                if phones_dir.exists():
                    # Il lessico potrebbe essere in diversi formati
                    for lexicon_file in ["lexicon.db", "lexicon.sqlite", "word_phonemes.db"]:
                        potential_db = phones_dir / lexicon_file
                        if potential_db.exists():
                            lexicon_db_path = potential_db
                            break

            model_info = ModelInfo(
                id=model_id,
                type=model_type,
                language=language,
                language_family=language_family,
                description=f"{language.title()} {model_type.value} model",
                model_path=model_dir,
                g2p_path=g2p_path if g2p_path.exists() else None,
                lexicon_db_path=lexicon_db_path,
                is_available=True
            )

            self._models[model_id] = model_info
            _LOGGER.info(f"Registered model: {model_id} ({model_type.value})")

    def _detect_model_type(self, model_dir: Path) -> Optional[ModelType]:
        """Rileva il tipo di modello dalla struttura delle directory."""
        # Kaldi ha una struttura specifica con model/final.mdl
        kaldi_model = model_dir / "model" / "model" / "final.mdl"
        if kaldi_model.exists():
            return ModelType.KALDI

        # Coqui STT ha file .pbmm o .tflite
        for coqui_file in model_dir.glob("*.pbmm"):
            return ModelType.COQUI_STT
        for coqui_file in model_dir.glob("*.tflite"):
            return ModelType.COQUI_STT

        return None

    def _parse_model_language(self, model_id: str) -> Tuple[str, str]:
        """Estrae lingua e famiglia linguistica dal nome del modello."""
        # Formato tipico: en_US-rhasspy, de_DE-zamia, etc.
        parts = model_id.split("-")[0].split("_")
        if len(parts) >= 2:
            language = model_id.split("-")[0]  # es: en_US
            language_family = parts[0]  # es: en
        else:
            language = model_id
            language_family = model_id.split("_")[0] if "_" in model_id else model_id

        return language, language_family

    def get_available_models(self) -> List[ModelInfo]:
        """Restituisce la lista dei modelli disponibili."""
        return [model for model in self._models.values() if model.is_available]

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Ottiene informazioni su un modello specifico."""
        return self._models.get(model_id)

    def get_models_by_language(self, language: str) -> List[ModelInfo]:
        """Ottiene modelli per una lingua specifica."""
        return [
            model for model in self._models.values()
            if model.language == language or model.language_family == language
        ]

    def get_default_model(self) -> Optional[ModelInfo]:
        """Ottiene il modello di default (preferisce inglese Kaldi)."""
        # Prova prima inglese Kaldi
        for model in self._models.values():
            if (model.language_family == "en" and
                model.type == ModelType.KALDI and
                model.is_available):
                return model

        # Poi qualsiasi modello Kaldi disponibile
        for model in self._models.values():
            if model.type == ModelType.KALDI and model.is_available:
                return model

        # Infine qualsiasi modello disponibile
        available_models = self.get_available_models()
        return available_models[0] if available_models else None

    def refresh_models(self) -> None:
        """Aggiorna la lista dei modelli disponibili."""
        self._models.clear()
        self._scan_models()

    def get_phonetisaurus_binary(self) -> Optional[Path]:
        """Ottiene il percorso del binario Phonetisaurus."""
        # Cerca negli strumenti Speech-to-Phrase
        possible_paths = [
            self.tools_path / "bin" / "phonetisaurus-apply",
            self.tools_path / "phonetisaurus-apply",
            Path("/usr/local/bin/phonetisaurus-apply"),
            Path("/usr/bin/phonetisaurus-apply"),
        ]

        for path in possible_paths:
            if path.exists() and path.is_file():
                return path

        # Cerca in PATH
        import shutil
        phonetisaurus_bin = shutil.which("phonetisaurus-apply")
        if phonetisaurus_bin:
            return Path(phonetisaurus_bin)

        return None