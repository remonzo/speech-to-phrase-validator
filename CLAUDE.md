# Speech-to-Phrase Validator Development Summary

## Project Overview
Home Assistant add-on for validating and optimizing Speech-to-Phrase word and entity recognition. Successfully evolved from critical startup failures to a fully functional validation tool with Speech-to-Phrase integration.

## Current Status: STABLE VERSION RESTORED ✅
- **Version**: 1.5.8 (stable, commit 267f80a)
- **Status**: Restored to working version after fixing compatibility issues
- **Functionality**: Model detection, word/entity validation, statistics, web UI
- **State**: Stable baseline - optimizations available but not active

## Environment Setup
- **Home Assistant**: Running on separate physical hardware (HA OS)
- **Development**: Local development on Windows
- **Git Management**: Claude handles all git commands and GitHub pushes automatically
- **Testing**: User executes HA commands manually and provides output

## Key Technical Architecture
- **Base**: Home Assistant add-on using s6-overlay v3 process management
- **Runtime**: Python 3 with FastAPI web interface
- **Platform**: Alpine Linux containers (multi-arch support)
- **Security**: Uses docker-default AppArmor profile
- **Integration**: Direct Speech-to-Phrase model structure support

## Critical Configuration Files

### config.yaml
```yaml
name: "Speech-to-Phrase Validator"
version: "1.5.7"
init: false  # CRITICAL: Allows s6-overlay to be PID 1
speech_to_phrase_models_path: "/share/speech-to-phrase/train"  # FIXED: Correct path
```

### Key Integration Points
- **Model Detection**: `/share/speech-to-phrase/train/it_IT-rhasspy/`
- **Lexicon Source**: `data/local/dict/lexicon.txt` (262 words - correct for S2P)
- **Model Structure**: Kaldi format with `graph/HCLG.fst` + `data/lang/`

## Development Journey & Major Issues Resolved

### Phase 1: Critical Startup Failures (v1.3.0 → v1.5.2)
**Problem**: Add-on wouldn't start - permission denied, s6-overlay conflicts
**Solutions Applied**:
- Added `init: false` to config.yaml
- Fixed shebang: `#!/command/with-contenv bashio`
- Removed custom AppArmor profile (use docker-default)
- Fixed PYTHONPATH variable: `${PYTHONPATH:-}`

### Phase 2: Model Detection Issues (v1.5.3 → v1.5.4)
**Problem**: Validator couldn't find Speech-to-Phrase models
**Root Cause**: Wrong path - S2P saves in `/train` not `/models`
**Solutions Applied**:
- Updated path: `/share/speech-to-phrase/models` → `/share/speech-to-phrase/train`
- Added Speech-to-Phrase structure detection (`graph/HCLG.fst` + `data/lang/`)
- Extended lexicon support for text files vs SQLite databases

### Phase 3: Frontend Failures (v1.5.5 → v1.5.7)
**Problem**: JavaScript functions undefined, API calls failing (404 errors)
**Root Cause**: Home Assistant Ingress path issues - static files not loading
**Solutions Applied**:
- Added Ingress path detection via `X-Ingress-Path` header
- Updated template static file paths: `{{ ingress_path }}/static/...`
- Fixed API calls to use proper ingress prefix
- Added JavaScript debugging and error logging

### Phase 4: Model Integration Deep Dive (v1.5.7 → v1.5.8)
**Discovery**: Speech-to-Phrase architecture understood
- **Limited Vocabulary**: 259 words is CORRECT (only trained phrases)
- **No G2P/Phonetisaurus**: S2P uses different approach
- **Validation Purpose**: Check if words are in user's specific model

### Phase 5: Optimization Attempts & Reset (v1.5.8 → v1.5.12 → v1.5.8)
**Problem**: Optimization attempts introduced compatibility issues
- **v1.5.8-v1.5.12**: Multiple attempts to improve architecture
- **Issues**: API incompatibilities, validation errors, statistics failures
- **Solution**: Reset to stable v1.5.8 (267f80a) baseline
**Learning**: Stable baseline more valuable than problematic optimizations

## Technical Implementations

### Speech-to-Phrase Model Support
```python
# Model detection logic
speech_to_phrase_graph = model_dir / "graph" / "HCLG.fst"
speech_to_phrase_lang = model_dir / "data" / "lang"
if speech_to_phrase_graph.exists() and speech_to_phrase_lang.exists():
    return ModelType.KALDI

# Lexicon loading from text files
speech_to_phrase_lexicon = model_dir / "data" / "local" / "dict" / "lexicon.txt"
```

### Home Assistant Ingress Support
```python
def get_ingress_path(request: Request) -> str:
    ingress_path = request.headers.get("X-Ingress-Path", "")
    return ingress_path.rstrip("/")
```

### Frontend Integration
```javascript
const ingressPath = window.INGRESS_PATH || '';
const url = `${ingressPath}/api${endpoint}`;
```

## Current Functionality Status

### ✅ Working Features
- **Model Detection**: Finds it_IT-rhasspy model correctly
- **Word Validation**: Tests if words exist in Speech-to-Phrase lexicon
- **Entity Validation**: Checks entity word components
- **Statistics**: Shows 259 words (correct for S2P), model info
- **Web Interface**: Fully functional with dark theme
- **API Integration**: All endpoints working through HA Ingress

### 🔧 Minor Issues Remaining
- **Theme Toggle**: Button present but not switching themes properly
- **G2P Status**: Shows "not available" (correct - S2P doesn't use it)

## Development Methodology Established
1. **Systematic Analysis**: Always compare with working HA add-ons first
2. **Methodical Testing**: Each change committed and tagged separately
3. **User-Led Testing**: User provides HA command outputs, Claude analyzes
4. **Git Automation**: Claude handles all commits, tags, and GitHub pushes
5. **Version Increments**: Each significant change gets new version

## Working Reference Add-ons Analyzed
- **core_speech-to-phrase**: Primary reference for S2P integration
- **core_openwakeword**: s6-overlay configuration reference
- **Key Learning**: Use standard configurations, avoid customization

## File Structure Understanding
```
/share/speech-to-phrase/train/it_IT-rhasspy/
├── data/
│   ├── lang/          # Compiled language model files
│   └── local/dict/    # lexicon.txt (262 words) ← VALIDATOR SOURCE
├── graph/             # HCLG.fst ← MODEL DETECTION
├── sentences.yaml     # Training sentences (30K lines)
└── training_info.json # Model metadata
```

## Commands for Development Workflow

### Home Assistant (User Executes)
```bash
# Add-on management
ha addon logs aa6099a0_stp_validator
ha addon list | grep speech
ha addon rebuild aa6099a0_stp_validator

# File system exploration
find /share/speech-to-phrase -name "*.fst" | head -10
ls -la /share/speech-to-phrase/train/it_IT-rhasspy/
wc -l /share/speech-to-phrase/train/it_IT-rhasspy/data/local/dict/lexicon.txt
```

### Development (Claude Executes)
```bash
# Version management
git add . && git commit -m "message" && git tag v1.5.x && git push origin main --tags

# Testing
docker build -t stp-validator .
docker run -p 8099:8099 stp-validator
```

## ARCHITETTURA HOME ASSISTANT ADD-ON vs STANDALONE

### 🏗️ **Differenze Architetturali Fondamentali**

**Home Assistant Add-on Environment:**
- **Modelli**: Privati e interni al container (`/data/models/`)
- **Training Output**: Solo artifacts esposti all'host (`/share/speech-to-phrase/train/`)
- **Lessico**: File di testo con parole specifiche del training (259 parole)
- **G2P/Phonetisaurus**: Gestiti internamente, non accessibili dall'esterno
- **Struttura**: Ottimizzata per re-training automatico

**Standalone Installation:**
- **Modelli**: Completi e accessibili (`/models/`)
- **Lessico**: Database SQLite completo (migliaia di parole)
- **G2P/Phonetisaurus**: Binari e modelli accessibili
- **Struttura**: Installation tradizionale Kaldi/Speech-to-Phrase

### 📊 **Principi di Funzionamento Speech-to-Phrase**

**Speech-to-Phrase NON è un ASR tradizionale:**
1. **Template-Based**: Riconosce solo frasi specifiche pre-addestrate
2. **Finite State Transducers**: Usa FST per pattern matching efficiente
3. **Wyoming Protocol**: Comunicazione con Home Assistant
4. **Re-training Automatico**: Si aggiorna quando cambiano entità/aree HA
5. **Lessico Limitato**: Solo parole presenti nei template attivi

**Processo di Training:**
1. Home Assistant invia templates (sentences.yaml)
2. Speech-to-Phrase estrae vocabolario dai templates
3. Crea FST ottimizzato per i pattern specifici
4. Salva lessico minimal in `lexicon.txt` (259 parole)
5. Container mantiene modelli base privati

**Validator Purpose:**
- Verifica se parole/entità sono nel lessico attivo dell'utente
- NON valida pronunciabilità generale
- Indica se Speech-to-Phrase riconoscerà quella specifica parola

### 🔍 **Architettura File Speech-to-Phrase Add-on HA**

```
Container (/data/):           Host (/share/speech-to-phrase/):
├── models/ (PRIVATE)         └── train/ (EXPOSED)
│   ├── acoustic/                 └── it_IT-rhasspy/
│   ├── language/                     ├── data/
│   └── base_lexicon/                 │   ├── lang/      # Compiled
└── tools/ (PRIVATE)                  │   └── local/dict/
    ├── kaldi/                        │       └── lexicon.txt ← 259 words
    └── phonetisaurus/                ├── graph/
                                      │   └── HCLG.fst   ← Model
                                      ├── sentences.yaml  ← Templates
                                      └── training_info.json
```

**Validator Accede Solo a:**
- `/share/speech-to-phrase/train/` (training output)
- `lexicon.txt` con parole specifiche utente
- NON ha accesso a modelli base o tools

## Important Technical Notes
- **Speech-to-Phrase Reality**: NOT a general ASR - only recognizes trained phrases
- **Validator Purpose**: Verify if words/entities are in user's specific model
- **Normal Statistics**: 259 words is expected for S2P (not thousands)
- **No G2P Needed**: S2P handles unknown words differently
- **HA Ingress**: Critical for proper static file serving in HA environment
- **Container Isolation**: Models/tools private, only training artifacts exposed

## Next Session Priorities
1. **Minor**: Fix theme toggle button functionality
2. **Feature**: Potentially add bulk entity import/validation
3. **Enhancement**: Better error handling for edge cases
4. **Documentation**: User guide for effective validator usage

## Key Lessons for Future Development
- **Don't assume**: Speech-to-Phrase != traditional ASR systems
- **Test in HA**: Local Docker testing doesn't catch Ingress issues
- **Follow HA patterns**: Use existing add-on structures as templates
- **Small iterations**: Frequent commits with clear version progression
- **Stable baseline first**: Ensure working version before optimizations
- **Container isolation**: Understand HA add-on vs standalone differences
- **Architecture matters**: Document real implementation vs theoretical design

## Version History Summary
- **v1.3.0-v1.5.2**: Startup and configuration fixes
- **v1.5.3-v1.5.4**: Model detection and path corrections
- **v1.5.5-v1.5.7**: Frontend fixes and HA Ingress support
- **v1.5.8 (267f80a)**: Stable version with HA optimizations (CURRENT)
- **v1.5.8-v1.5.12**: Optimization attempts with compatibility issues (REVERTED)

## Current Repository State
- **Local & GitHub**: v1.5.8 (267f80a) stable baseline
- **Status**: Working version restored, optimizations available but not active
- **Files**: Original working codebase + optimization files present but unused

This project successfully demonstrates Home Assistant add-on development, debugging complex integration issues, creating a functional validation tool for Speech-to-Phrase systems, and the importance of maintaining stable baselines during development.