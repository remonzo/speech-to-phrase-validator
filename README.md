# Speech-to-Phrase Validator

Un add-on per Home Assistant che fornisce strumenti di validazione e ottimizzazione per il sistema Speech-to-Phrase.

## 🎯 Funzionalità

- **Validazione Parole**: Verifica se parole specifiche sono riconoscibili da Speech-to-Phrase
- **Visualizzazione Pronunce**: Mostra le pronunce fonetiche attese dal modello Kaldi
- **Suggerimenti**: Propone alternative per parole non riconosciute
- **Validazione Entità**: Controlla nomi di entità Home Assistant
- **Validazione Multipla**: Analizza liste complete di entità
- **Statistiche**: Informazioni dettagliate sui modelli disponibili

## 🔧 Installazione

### Prerequisiti

1. Home Assistant OS/Supervised
2. Add-on Speech-to-Phrase installato e configurato
3. Almeno un modello Speech-to-Phrase scaricato

### Installazione Add-on

1. Aggiungi questo repository agli add-on di Home Assistant:
   ```
   Settings → Add-ons → Add-on Store → ⋮ → Repositories
   ```

2. Installa l'add-on "Speech-to-Phrase Validator"

3. Configura le opzioni (i valori di default dovrebbero funzionare):
   ```yaml
   log_level: info
   speech_to_phrase_models_path: "/share/speech-to-phrase/models"
   speech_to_phrase_train_path: "/share/speech-to-phrase/train"
   speech_to_phrase_tools_path: "/share/speech-to-phrase/tools"
   enable_cli: false
   ```

4. Avvia l'add-on

5. Accedi all'interfaccia web tramite "APRI INTERFACCIA WEB"

## 📱 Utilizzo

### Interfaccia Web

L'interfaccia principale offre diverse sezioni:

#### 🔧 Configurazione Modello
- Seleziona il modello Speech-to-Phrase da utilizzare
- Visualizza informazioni sul modello corrente

#### 🔍 Validazione Parola
- Inserisci una parola per verificare se è riconoscibile
- Visualizza pronunce fonetiche e alternative

#### 🏠 Validazione Entità
- Controlla nomi di entità Home Assistant
- Analizza ogni parola componente

#### 📋 Validazione Multipla
- Inserisci una lista di entità (una per riga)
- Ottieni un report completo con statistiche e raccomandazioni

#### 📊 Statistiche Modello
- Informazioni sul lessico e sui tool disponibili

### API REST

L'add-on espone anche un'API REST per integrazione programmatica:

```bash
# Validazione singola parola
POST /api/validate/word
{
  "word": "condizionatore"
}

# Validazione entità
POST /api/validate/entity?entity_name=condizionatore_soggiorno

# Validazione multipla
POST /api/validate/entities
{
  "entities": ["luce_cucina", "termostato_bagno"]
}

# Suggerimenti
POST /api/suggest
{
  "word": "climatizzatore",
  "max_suggestions": 5
}
```

## 🎮 Esempi d'Uso

### Scenario 1: Verifica Nome Entità

Hai un'entità chiamata `climatizzatore_soggiorno` e vuoi verificare se sarà riconosciuta:

1. Vai su "Validazione Entità"
2. Inserisci `climatizzatore_soggiorno`
3. Analizza i risultati:
   - ✅ `climatizzatore` riconosciuto
   - ✅ `soggiorno` riconosciuto
   - **Risultato**: Entità ottimizzata per il riconoscimento vocale

### Scenario 2: Ottimizzazione Lista Entità

Hai una lista di entità e vuoi ottimizzarla:

1. Vai su "Validazione Multipla"
2. Incolla la lista:
   ```
   condizionatore_camera
   luci_bagno
   termostato_principale
   alexa_echo
   ```
3. Analizza il report e segui le raccomandazioni

### Scenario 3: Ricerca Alternative

La parola "condizionatore" non è riconosciuta:

1. Vai su "Validazione Parola"
2. Inserisci `condizionatore`
3. Se mostrata come sconosciuta, guarda i suggerimenti
4. Considera alternative come `climatizzatore` o `aria`

## 🔍 Risoluzione Problemi

### L'add-on non trova i modelli

1. Verifica che Speech-to-Phrase sia installato e avviato
2. Controlla che almeno un modello sia stato scaricato
3. Verifica i percorsi nella configurazione:
   ```yaml
   speech_to_phrase_models_path: "/share/speech-to-phrase/models"
   ```

### Errori di pronuncia

1. Controlla che il modello G2P sia presente
2. Verifica che Phonetisaurus sia installato negli strumenti Speech-to-Phrase
3. Controlla i log dell'add-on per errori specifici

### Performance lente

1. Usa modelli Kaldi invece di Coqui STT quando possibile
2. Limita il numero di entità nella validazione multipla
3. Verifica le risorse disponibili del sistema

## 🏗️ Sviluppo

### Struttura del Progetto

```
speech-to-phrase-validator/
├── src/
│   ├── validator/          # Core validation logic
│   ├── api/               # FastAPI web server
│   └── web/               # Frontend templates e assets
├── config.yaml            # Add-on configuration
├── Dockerfile             # Container definition
└── run.sh                 # Startup script
```

### Build Locale

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
cd src && python -m api.app

# Run tests
pytest tests/
```

## 📄 Licenza

Questo progetto è rilasciato sotto licenza Apache 2.0.

## 🤝 Contributi

Contributi, issue e feature request sono benvenuti!

1. Fork del progetto
2. Crea un feature branch
3. Commit delle modifiche
4. Push al branch
5. Apri una Pull Request

## 🐛 Bug e Supporto

Per segnalare bug o richiedere supporto:

1. Controlla i [problemi noti](https://github.com/yourusername/speech-to-phrase-validator/issues)
2. Apri un nuovo issue con:
   - Versione Home Assistant
   - Versione Speech-to-Phrase
   - Log dell'add-on
   - Passi per riprodurre il problema

## 📚 Documentazione Correlata

- [Speech-to-Phrase](https://github.com/rhasspy/speech-to-phrase)
- [Home Assistant Add-on Development](https://developers.home-assistant.io/docs/add-ons/)
- [Kaldi ASR](https://kaldi-asr.org/)
- [Phonetisaurus](https://github.com/AdolfVonKleist/Phonetisaurus)