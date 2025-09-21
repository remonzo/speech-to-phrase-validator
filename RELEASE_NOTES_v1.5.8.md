# Speech-to-Phrase Validator v1.5.8 - Home Assistant Add-on Optimizations

## 🎯 **Release Overview**
Aggiornamento di ottimizzazione specifico per l'architettura add-on Home Assistant, basato su comprensione approfondita del funzionamento interno di Speech-to-Phrase.

## 🔥 **Major Changes**

### **1. Ottimizzazione Architettura Add-on HA**
- **Rimozione path tools non necessario**: `speech_to_phrase_tools_path` ora vuoto (gestito internamente)
- **Unificazione percorsi modelli**: Usa solo `/share/speech-to-phrase/train` (realtà add-on HA)
- **Riconoscimento automatico**: Distingue modelli add-on HA vs standalone

### **2. Model Manager Ottimizzato (`model_manager_v1.5.8.py`)**
- **Priorità directory train**: Cerca prima in `/train` poi fallback a `/models`
- **Rilevamento struttura HA**: Identifica modelli Speech-to-Phrase add-on
- **Gestione lessico migliorata**: Priorità file di testo vs database SQLite
- **Nuovo campo**: `is_ha_addon_optimized` in `ModelInfo`

### **3. Lexicon Wrapper Migliorato (`lexicon_wrapper_v1.5.8.py`)**
- **Gestione file di testo ottimizzata**: Parser robusto per `lexicon.txt`
- **Auto-rilevamento formato**: Distingue file di testo vs database SQLite
- **Statistiche avanzate**: Include tipo lessico e stato ottimizzazione HA
- **Error handling migliorato**: Gestione linee malformate nel lessico

### **4. Frontend UI Aggiornato (`app_v1.5.8.js`)**
- **Messaggi HA-aware**: Spiega comportamenti specifici add-on
- **Status G2P chiarificato**: "Gestito internamente" invece di "non disponibile"
- **Info lessico contestuale**: Specifica "template personalizzati" vs "database completo"
- **Statistiche add-on**: Sezione informativa per utenti HA

## 📋 **Technical Improvements**

### **Configuration Changes**
```yaml
# config.yaml v1.5.8
version: "1.5.8"
description: "...Ottimizzato per add-on Home Assistant."
options:
  speech_to_phrase_tools_path: ""  # Vuoto invece di path inesistente
schema:
  speech_to_phrase_tools_path: str?  # Opzionale
```

### **Model Detection Logic**
```python
# Priorità ottimizzata per add-on HA
search_path = self.train_path if self.train_path.exists() else self.models_path

# Rilevamento Speech-to-Phrase specifico
stp_graph = model_dir / "graph" / "HCLG.fst"
stp_lang = model_dir / "data" / "lang"
stp_lexicon = model_dir / "data" / "local" / "dict" / "lexicon.txt"
```

### **Lexicon Handling**
```python
# Auto-rilevamento formato
if lexicon_path.suffix == '.txt':
    self._is_text_lexicon = True  # Add-on HA
else:
    self._is_text_lexicon = False  # Standalone
```

## 🎯 **User Experience Improvements**

### **Messaggi Chiarificatori**
- ✅ **G2P Status**: "Gestito internamente (normale per add-on HA)" invece di errore
- ✅ **Lessico Count**: "259 parole (template personalizzati)" con contesto
- ✅ **Tipo Modello**: Badge "HA Add-on" per distinguere da standalone
- ✅ **Info Section**: Spiegazione comportamenti specifici add-on

### **Performance Optimization**
- ✅ **Meno ricerche inutili**: Non cerca file che non esistono nell'add-on
- ✅ **Cache ottimizzata**: Gestione separata file di testo vs database
- ✅ **Error reduction**: Meno warning per comportamenti normali add-on

## 🔧 **Breaking Changes**
**Nessuna** - Tutte le modifiche sono backward-compatible.

## 🐛 **Bug Fixes**
- **Tools path warning**: Eliminato warning per path tools inesistente
- **G2P error messaging**: Non mostra più come errore il G2P non accessibile
- **Lexicon format detection**: Migliorata robustezza parser file di testo

## 📚 **Documentation Updates**
- Aggiunta sezione "ARCHITETTURA HOME ASSISTANT ADD-ON vs STANDALONE" in CLAUDE.md
- Documentazione completa differenze implementative
- Esempi di configurazione ottimale per add-on HA

## 🚀 **Next Steps**
1. **Theme toggle fix**: Completare funzionalità cambio tema (minor issue)
2. **Bulk validation**: Possibile aggiunta validazione entità multiple
3. **Performance monitoring**: Metriche specifiche add-on HA
4. **User guide**: Documentazione utente finale

## 🔍 **Validation Status**
- ✅ **Configurazione corretta**: Path ottimizzati per add-on HA
- ✅ **Model detection**: Funziona con struttura reale Speech-to-Phrase
- ✅ **Lexicon reading**: Gestisce file di testo 259 parole correttamente
- ✅ **UI messaging**: Chiarisce comportamenti normali add-on
- ✅ **Error reduction**: Elimina warning/errori inappropriati

---

**Developed with deep understanding of Speech-to-Phrase architecture and Home Assistant add-on ecosystem.**