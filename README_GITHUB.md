# Speech-to-Phrase Validator - Home Assistant Add-on

[![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)
[![GitHub release](https://img.shields.io/github/release/remonzo/speech-to-phrase-validator.svg)](https://github.com/remonzo/speech-to-phrase-validator/releases)

Strumento di validazione e ottimizzazione per Speech-to-Phrase che aiuta a verificare la riconoscibilità di parole ed entità Home Assistant.

![Screenshot](https://via.placeholder.com/800x400/4285f4/ffffff?text=Speech-to-Phrase+Validator)

## ✨ Funzionalità

- 🔍 **Validazione Parole** - Verifica se parole specifiche sono riconoscibili
- 🏠 **Validazione Entità** - Controlla nomi di entità Home Assistant
- 📋 **Validazione Multipla** - Analizza liste complete di entità
- 💡 **Suggerimenti** - Alternative intelligenti per parole sconosciute
- 📊 **Statistiche** - Informazioni dettagliate sui modelli
- 🌐 **Interfaccia Web** - UI integrata in Home Assistant

## 🚀 Installazione

### Metodo 1: Repository Add-on (Consigliato)

1. In Home Assistant, vai su **Settings → Add-ons → Add-on Store**
2. Clicca **⋮** (menu) → **Repositories**
3. Aggiungi questo URL:
   ```
   https://github.com/remonzo/speech-to-phrase-validator
   ```
4. Cerca "Speech-to-Phrase Validator" e clicca **INSTALL**
5. Configura e avvia l'add-on

### Metodo 2: Installazione Manuale

1. Clona questo repository nella directory `/addons/` di Home Assistant
2. Riavvia Home Assistant
3. L'add-on apparirà nella lista

## ⚙️ Configurazione

```yaml
log_level: info
speech_to_phrase_models_path: "/share/speech-to-phrase/models"
speech_to_phrase_train_path: "/share/speech-to-phrase/train"
speech_to_phrase_tools_path: "/share/speech-to-phrase/tools"
enable_cli: false
```

## 📋 Prerequisiti

- Home Assistant OS/Supervised
- Add-on **Speech-to-Phrase** installato e configurato
- Almeno un modello Speech-to-Phrase scaricato

## 📖 Utilizzo

1. Avvia l'add-on
2. Clicca **"APRI INTERFACCIA WEB"**
3. Seleziona il modello linguistico
4. Testa le funzionalità:
   - Validazione singola parola
   - Validazione entità Home Assistant
   - Validazione multipla con report completo

## 🌍 Lingue Supportate

Supporta tutti i modelli Speech-to-Phrase disponibili:
- 🇮🇹 Italiano
- 🇬🇧 Inglese
- 🇫🇷 Francese
- 🇩🇪 Tedesco
- 🇪🇸 Spagnolo
- E molte altre...

## 📸 Screenshots

### Validazione Parola
![Validazione Parola](https://via.placeholder.com/600x300/28a745/ffffff?text=Validazione+Parola)

### Validazione Entità
![Validazione Entità](https://via.placeholder.com/600x300/17a2b8/ffffff?text=Validazione+Entità)

### Report Multiplo
![Report Multiplo](https://via.placeholder.com/600x300/ffc107/000000?text=Report+Multiplo)

## 🔧 Sviluppo

Questo add-on è basato su:
- **Backend**: FastAPI + Python
- **Frontend**: HTML/CSS/JS
- **Integration**: Speech-to-Phrase APIs

### Test Locale

```bash
git clone https://github.com/remonzo/speech-to-phrase-validator.git
cd speech-to-phrase-validator
pip install -r requirements.txt
python run_server.py
```

## 🐛 Supporto

- 📖 [Documentazione](./DOCS.md)
- 🐛 [Segnala Bug](https://github.com/remonzo/speech-to-phrase-validator/issues)
- 💬 [Discussioni](https://github.com/remonzo/speech-to-phrase-validator/discussions)

## 🤝 Contributi

Contributi benvenuti! Leggi la [guida per contribuire](./CONTRIBUTING.md).

## 📄 Licenza

Questo progetto è licenziato sotto [Apache License 2.0](./LICENSE).

---

**Made with ❤️ for the Home Assistant community**