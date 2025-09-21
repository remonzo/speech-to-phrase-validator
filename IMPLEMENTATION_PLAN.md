# Predictor Implementation Plan - Standalone Approach

## SOLUZIONE 1: Standalone Database + G2P

### Fase 1: Download Resources (stesso modello di S2P)
```python
# src/validator/model_downloader.py
class SpeechToPhraseModelDownloader:
    def download_lexicon_db(self, language="it_IT-rhasspy"):
        # Download from HuggingFace stesso DB che usa S2P
        url = f"https://huggingface.co/rhasspy/rhasspy-models/resolve/main/{language}/lexicon.db"
        return download_file(url, "models/lexicon.db")

    def download_g2p_model(self, language="it_IT-rhasspy"):
        # Download Phonetisaurus FST
        url = f"https://huggingface.co/rhasspy/rhasspy-models/resolve/main/{language}/g2p.fst"
        return download_file(url, "models/g2p.fst")
```

### Fase 2: Standalone Lexicon Manager
```python
# src/validator/standalone_lexicon.py
class StandaloneLexicon:
    def __init__(self, db_path: str, g2p_path: str):
        self.conn = sqlite3.connect(db_path)
        self.g2p_fst = load_fst(g2p_path)

    def exists_in_lexicon(self, word: str) -> bool:
        # Query diretto su database completo
        cursor = self.conn.execute("SELECT COUNT(*) FROM lexicon WHERE word = ?", (word,))
        return cursor.fetchone()[0] > 0

    def get_pronunciations(self, word: str) -> List[List[str]]:
        # Estrai pronunce dal database completo
        cursor = self.conn.execute("SELECT pronunciation FROM lexicon WHERE word = ?", (word,))
        return [row[0].split() for row in cursor.fetchall()]

    def predict_with_g2p(self, word: str) -> Optional[List[str]]:
        # Usa Phonetisaurus per parole sconosciute
        return phonetisaurus_predict(word, self.g2p_fst)
```

### Fase 3: Predictor Core
```python
# src/validator/predictor.py
@dataclass
class PredictionResult:
    word: str
    in_lexicon: bool
    lexicon_pronunciations: List[List[str]]
    g2p_pronunciation: Optional[List[str]]
    confidence: float
    recommendation: str

class SpeechToPhrasePredictor:
    def __init__(self, models_path: str):
        self.lexicon = StandaloneLexicon(
            db_path=f"{models_path}/lexicon.db",
            g2p_path=f"{models_path}/g2p.fst"
        )

    def predict_word(self, word: str) -> PredictionResult:
        # Logica identica a S2P
        in_lexicon = self.lexicon.exists_in_lexicon(word)

        if in_lexicon:
            pronunciations = self.lexicon.get_pronunciations(word)
            confidence = 1.0
            recommendation = "✅ Ottimale per Speech-to-Phrase"
        else:
            pronunciations = []
            g2p_result = self.lexicon.predict_with_g2p(word)
            if g2p_result:
                confidence = 0.7
                recommendation = "🔍 Riconoscibile via G2P - testare accuratezza"
            else:
                confidence = 0.0
                recommendation = "❌ Non riconoscibile - considera rinominare"

        return PredictionResult(...)
```

### Fase 4: UI Integration
```html
<!-- Nuova sezione in index.html -->
<section class="card">
    <h2>🔮 Predictor Pre-Aggiunta</h2>
    <div class="predictor-form">
        <input type="text" id="predict-input" placeholder="Test device/entity name before adding to Assist">
        <button onclick="predictWord()">🎯 Predict Recognition</button>
    </div>
    <div id="predict-result"></div>
</section>
```

### Fase 5: API Endpoints
```python
# src/api/app.py
@app.post("/api/predict/word")
async def predict_word_endpoint(request: WordPredictionRequest):
    result = predictor.predict_word(request.word)
    return result

@app.post("/api/predict/entity")
async def predict_entity_endpoint(request: EntityPredictionRequest):
    # Split entity in words and predict each
    words = split_entity_name(request.entity_name)
    results = [predictor.predict_word(word) for word in words]
    return EntityPredictionResult(words=results, overall=calculate_overall(results))
```

## Storage Structure
```
/data/speech_to_phrase_validator/
├── models/
│   ├── lexicon.db          # 50K parole complete (stesso di S2P)
│   ├── g2p.fst            # Modello Phonetisaurus
│   └── model_info.json    # Metadata versioni
└── cache/
    └── predictions.json    # Cache predizioni per performance
```

## Performance Optimizations
- SQLite in-memory per lookup veloci
- Cache predizioni G2P (costose computazionalmente)
- Async download modelli al primo avvio
- Batch prediction per multiple entities

## Timeline
- Fase 1-2: 1 ora (download + database manager)
- Fase 3: 45 min (predictor core)
- Fase 4-5: 45 min (UI + API)
- Testing: 30 min
- **Total: 3 ore**