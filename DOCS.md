# Speech-to-Phrase Validator Add-on

## Panoramica

Speech-to-Phrase Validator è un add-on per Home Assistant che fornisce strumenti di validazione e ottimizzazione per il sistema Speech-to-Phrase. Aiuta gli utenti a:

- **Verificare la riconoscibilità** di parole ed entità
- **Ottenere pronunce attese** dal modello Kaldi
- **Suggerire alternative** per parole non riconosciute
- **Validare configurazioni** complete di Home Assistant

## Installazione

1. Installa e configura l'add-on Speech-to-Phrase
2. Aggiungi questo repository agli add-on di Home Assistant
3. Installa l'add-on "Speech-to-Phrase Validator"
4. Configura i percorsi delle directory (dovrebbero essere già corretti di default)
5. Avvia l'add-on

## Configurazione

### Opzioni

- **log_level**: Livello di logging (trace, debug, info, notice, warning, error, fatal)
- **speech_to_phrase_models_path**: Percorso ai modelli Speech-to-Phrase (default: `/share/speech-to-phrase/models`)
- **speech_to_phrase_train_path**: Percorso alle directory di training (default: `/share/speech-to-phrase/train`)
- **speech_to_phrase_tools_path**: Percorso agli strumenti Kaldi (default: `/share/speech-to-phrase/tools`)
- **enable_cli**: Abilita strumenti da riga di comando per utenti avanzati

### Configurazione tipica

```yaml
log_level: info
speech_to_phrase_models_path: "/share/speech-to-phrase/models"
speech_to_phrase_train_path: "/share/speech-to-phrase/train"
speech_to_phrase_tools_path: "/share/speech-to-phrase/tools"
enable_cli: false
```

## Utilizzo

### Interfaccia Web

Accedi all'interfaccia web tramite il pannello Home Assistant:
- Vai su "Impostazioni" → "Add-on" → "Speech-to-Phrase Validator"
- Clicca su "APRI INTERFACCIA WEB"

### Funzionalità principali

1. **Verifica Parola**: Controlla se una parola è presente nel lessico Kaldi
2. **Pronuncia**: Visualizza la pronuncia fonetica attesa
3. **Suggerimenti**: Ottieni alternative per parole non riconosciute
4. **Validazione Entità**: Controlla tutte le entità Home Assistant esposte

## Prerequisiti

- Home Assistant OS/Supervised
- Add-on Speech-to-Phrase installato e configurato
- Almeno un modello Speech-to-Phrase scaricato

## Risoluzione Problemi

### L'add-on non trova i modelli Speech-to-Phrase

1. Verifica che l'add-on Speech-to-Phrase sia installato
2. Assicurati che almeno un modello sia stato scaricato
3. Controlla i percorsi nella configurazione
4. Verifica i log dell'add-on per errori specifici

### Errori di pronuncia

1. Controlla che il modello G2P sia presente
2. Verifica che gli strumenti Phonetisaurus siano installati
3. Controlla i log per errori di percorso

## Supporto

Per supporto e segnalazione bug, visita il repository GitHub del progetto.

## Changelog

### 0.1.0
- Prima versione
- Interfaccia web base
- Validazione parole e pronunce
- Integrazione con Speech-to-Phrase