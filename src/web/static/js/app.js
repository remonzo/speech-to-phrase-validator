// Speech-to-Phrase Validator JavaScript

// Theme management
function toggleTheme() {
    console.log('Toggle theme function called');
    const body = document.body;
    const isLight = body.classList.contains('light-theme');

    console.log('Current light theme:', isLight);

    if (isLight) {
        // Switch to dark (default)
        body.classList.remove('light-theme');
        localStorage.setItem('theme', 'dark');
        console.log('Switched to dark theme (default)');
    } else {
        // Switch to light
        body.classList.add('light-theme');
        localStorage.setItem('theme', 'light');
        console.log('Switched to light theme');
    }

    // Update button text
    const button = document.getElementById('theme-toggle');
    if (button) {
        button.textContent = isLight ? '🌙 Scuro' : '☀️ Chiaro';
    }
}

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Speech-to-Phrase Validator JavaScript loaded!');
    console.log('DOM loaded, setting up theme');
    const savedTheme = localStorage.getItem('theme');

    console.log('Saved theme:', savedTheme);

    // Dark theme is now default, only apply light theme if explicitly requested
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        console.log('Applied light theme on load');
    } else {
        console.log('Using default dark theme');
    }

    // Update button text based on current theme
    const button = document.getElementById('theme-toggle');
    if (button) {
        const isLight = document.body.classList.contains('light-theme');
        button.textContent = isLight ? '🌙 Scuro' : '☀️ Chiaro';
    }

    // Set up theme toggle button
    const themeButton = document.getElementById('theme-toggle');
    if (themeButton) {
        console.log('Theme button found, adding click listener');
        themeButton.addEventListener('click', function(e) {
            e.preventDefault();
            toggleTheme();
        });
    } else {
        console.error('Theme toggle button not found');
    }

    // Test if all functions exist
    console.log('Functions available:');
    console.log('- validateWord:', typeof validateWord);
    console.log('- validateEntity:', typeof validateEntity);
    console.log('- validateEntities:', typeof validateEntities);
    console.log('- loadStats:', typeof loadStats);
    console.log('- predictWord:', typeof predictWord);
    console.log('- predictEntity:', typeof predictEntity);
    console.log('- loadPredictorStats:', typeof loadPredictorStats);

    // Auto-load stats if validator is available
    if (document.querySelector('.card')) {
        console.log('Starting auto stats load...');
        setTimeout(function() {
            console.log('Calling loadStats...');
            loadStats();
        }, 2000);
    }
});

// Utility functions
function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showError(message) {
    console.error(message);
    // Could implement toast notifications here
}

// API calls
async function apiCall(endpoint, options = {}) {
    showLoading();
    try {
        const ingressPath = window.INGRESS_PATH || '';
        const url = `${ingressPath}/api${endpoint}`;
        console.log('API call to:', url);

        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        showError(`API Error: ${error.message}`);
        throw error;
    } finally {
        hideLoading();
    }
}

// Model selection
async function selectModel(modelId) {
    try {
        await apiCall(`/models/${modelId}/select`, { method: 'POST' });
        // Refresh the page to update the current model display
        location.reload();
    } catch (error) {
        showError(`Failed to select model: ${error.message}`);
    }
}

// Word validation
async function validateWord() {
    console.log('🔍 validateWord function called');
    const wordInput = document.getElementById('word-input');
    const word = wordInput.value.trim();
    console.log('Word to validate:', word);

    if (!word) {
        console.log('No word provided, returning');
        return;
    }

    try {
        const result = await apiCall('/validate/word', {
            method: 'POST',
            body: JSON.stringify({ word })
        });

        displayWordResult(result);
    } catch (error) {
        document.getElementById('word-result').innerHTML =
            `<div class="alert alert-error">Errore nella validazione: ${error.message}</div>`;
    }
}

function displayWordResult(result) {
    const resultDiv = document.getElementById('word-result');

    const statusClass = result.status;
    const statusIcon = getStatusIcon(result.status);

    let pronunciationsHtml = '';
    if (result.pronunciations && result.pronunciations.length > 0) {
        pronunciationsHtml = result.pronunciations.map(pron =>
            `<span class="pronunciation">[${pron.join(' ')}]</span>`
        ).join(' ');
    }

    let guessedHtml = '';
    if (result.guessed_pronunciation) {
        guessedHtml = `<div><strong>Pronuncia stimata:</strong> <span class="pronunciation">[${result.guessed_pronunciation.join(' ')}]</span></div>`;
    }

    let similarWordsHtml = '';
    if (result.similar_words && result.similar_words.length > 0) {
        similarWordsHtml = `
            <div class="similar-words">
                <strong>Parole simili:</strong>
                ${result.similar_words.map(w =>
                    `<span class="similar-word" onclick="document.getElementById('word-input').value='${w.word}'; validateWord();">
                        ${w.word} (${(w.score * 100).toFixed(0)}%)
                    </span>`
                ).join('')}
            </div>
        `;
    }

    let notesHtml = '';
    if (result.notes && result.notes.length > 0) {
        notesHtml = `<div class="notes">${result.notes.join('. ')}</div>`;
    }

    resultDiv.innerHTML = `
        <div class="result-card ${statusClass}">
            <div class="result-header">
                <span class="result-word">${statusIcon} ${result.word}</span>
                <span class="badge badge-${getStatusBadgeClass(result.status)}">
                    ${getStatusText(result.status)}
                </span>
            </div>
            ${pronunciationsHtml ? `<div><strong>Pronuncia:</strong> ${pronunciationsHtml}</div>` : ''}
            ${guessedHtml}
            ${similarWordsHtml}
            ${notesHtml}
            <div style="margin-top: 10px; font-size: 12px; color: #6c757d;">
                Confidenza: ${(result.confidence * 100).toFixed(0)}% | Modello: ${result.model_id}
            </div>
        </div>
    `;
}

// Entity validation
async function validateEntity() {
    const entityInput = document.getElementById('entity-input');
    const entityName = entityInput.value.trim();

    if (!entityName) {
        return;
    }

    try {
        const result = await apiCall(`/validate/entity?entity_name=${encodeURIComponent(entityName)}`, {
            method: 'POST'
        });

        displayEntityResult(result);
    } catch (error) {
        document.getElementById('entity-result').innerHTML =
            `<div class="alert alert-error">Errore nella validazione: ${error.message}</div>`;
    }
}

function displayEntityResult(result) {
    const resultDiv = document.getElementById('entity-result');

    const statusIcon = getStatusIcon(result.overall_status);
    const knownWords = result.words_results.filter(w => w.is_known).length;
    const totalWords = result.words_results.length;

    let wordsHtml = result.words_results.map(wordResult => `
        <div class="word-result ${wordResult.status}">
            <strong>${wordResult.word}</strong> ${getStatusIcon(wordResult.status)}
            <br>
            <small>
                ${wordResult.is_known ?
                    `Pronuncia: [${wordResult.pronunciations[0]?.join(' ') || 'N/A'}]` :
                    `${wordResult.guessed_pronunciation ?
                        `Stimata: [${wordResult.guessed_pronunciation.join(' ')}]` :
                        'Pronuncia non disponibile'}`
                }
            </small>
        </div>
    `).join('');

    let recommendationsHtml = '';
    if (result.recommendations && result.recommendations.length > 0) {
        recommendationsHtml = `
            <div class="recommendations">
                <h4>💡 Raccomandazioni</h4>
                <ul>
                    ${result.recommendations.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    resultDiv.innerHTML = `
        <div class="result-card ${result.overall_status}">
            <div class="entity-summary">
                <div>
                    <span class="result-word">${statusIcon} ${result.entity_id}</span>
                    <br>
                    <small>Parole riconosciute: ${knownWords}/${totalWords}</small>
                </div>
                <span class="badge badge-${getStatusBadgeClass(result.overall_status)}">
                    ${getStatusText(result.overall_status)}
                </span>
            </div>

            <div class="word-results">
                ${wordsHtml}
            </div>

            ${recommendationsHtml}
        </div>
    `;
}

// Bulk entity validation
async function validateEntities() {
    const entitiesInput = document.getElementById('entities-input');
    const entitiesText = entitiesInput.value.trim();

    if (!entitiesText) {
        return;
    }

    const entities = entitiesText.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    if (entities.length === 0) {
        return;
    }

    try {
        const result = await apiCall('/validate/entities', {
            method: 'POST',
            body: JSON.stringify({ entities })
        });

        displayBulkResult(result);
    } catch (error) {
        document.getElementById('bulk-result').innerHTML =
            `<div class="alert alert-error">Errore nella validazione: ${error.message}</div>`;
    }
}

function displayBulkResult(result) {
    const resultDiv = document.getElementById('bulk-result');

    const score = (result.overall_score * 100).toFixed(1);
    const scoreClass = result.overall_score >= 0.8 ? 'success' :
                     result.overall_score >= 0.6 ? 'warning' : 'danger';

    let entitiesHtml = result.entity_results.map(entity => `
        <div class="result-card ${entity.overall_status}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>${getStatusIcon(entity.overall_status)} ${entity.entity_id}</span>
                <span class="badge badge-${getStatusBadgeClass(entity.overall_status)}">
                    ${entity.known_words}/${entity.words_count} parole
                </span>
            </div>
            ${entity.recommendations.length > 0 ?
                `<div class="notes">${entity.recommendations.slice(0, 2).join('. ')}</div>` : ''
            }
        </div>
    `).join('');

    let recommendationsHtml = '';
    if (result.recommendations && result.recommendations.length > 0) {
        recommendationsHtml = `
            <div class="recommendations">
                <h4>📊 Raccomandazioni Generali</h4>
                <ul>
                    ${result.recommendations.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    resultDiv.innerHTML = `
        <div class="stats-grid" style="margin-bottom: 20px;">
            <div class="stat-item">
                <div class="stat-value">${score}%</div>
                <div class="stat-label">Punteggio Complessivo</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${result.known_entities}</div>
                <div class="stat-label">Entità Riconosciute</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${result.unknown_entities}</div>
                <div class="stat-label">Entità Sconosciute</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${result.partially_known_entities}</div>
                <div class="stat-label">Parzialmente Note</div>
            </div>
        </div>

        ${recommendationsHtml}

        <h4>Risultati Dettagliati</h4>
        <div style="max-height: 400px; overflow-y: auto;">
            ${entitiesHtml}
        </div>
    `;
}

// Statistics
async function loadStats() {
    console.log('📊 loadStats function called');
    try {
        console.log('Calling /stats API...');
        const stats = await apiCall('/stats');
        console.log('Stats received:', stats);
        displayStats(stats);
    } catch (error) {
        console.error('Error loading stats:', error);
        const statsResult = document.getElementById('stats-result');
        if (statsResult) {
            statsResult.innerHTML = `<div class="alert alert-error">Errore nel caricamento: ${error.message}</div>`;
        }
    }
}

function displayStats(stats) {
    const statsDiv = document.getElementById('stats-result');

    statsDiv.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">${stats.total_words?.toLocaleString() || 'N/A'}</div>
                <div class="stat-label">Parole nel Lessico</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.model_type || 'N/A'}</div>
                <div class="stat-label">Tipo Modello</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.has_g2p_model ? '✅' : '❌'}</div>
                <div class="stat-label">Modello G2P</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.has_phonetisaurus ? '✅' : '❌'}</div>
                <div class="stat-label">Phonetisaurus</div>
            </div>
        </div>

        <div style="margin-top: 20px; font-size: 14px; color: #6c757d;">
            <strong>Modello:</strong> ${stats.model_id}<br>
            ${stats.database_path ? `<strong>Database:</strong> ${stats.database_path}` : ''}
        </div>
    `;
}

// Helper functions
function getStatusIcon(status) {
    switch (status) {
        case 'known': return '✅';
        case 'unknown': return '❌';
        case 'guessed': return '🔍';
        case 'error': return '⚠️';
        default: return '❓';
    }
}

function getStatusText(status) {
    switch (status) {
        case 'known': return 'Riconosciuta';
        case 'unknown': return 'Sconosciuta';
        case 'guessed': return 'Stimata';
        case 'error': return 'Errore';
        default: return 'Sconosciuto';
    }
}

function getStatusBadgeClass(status) {
    switch (status) {
        case 'known': return 'success';
        case 'unknown': return 'danger';
        case 'guessed': return 'warning';
        case 'error': return 'danger';
        default: return 'secondary';
    }
}

// PREDICTOR FUNCTIONS

// Word prediction
window.predictWord = async function() {
    console.log('🔮 predictWord function called');
    const wordInput = document.getElementById('predict-word-input');
    const word = wordInput.value.trim();
    console.log('Word to predict:', word);

    if (!word) {
        console.log('No word provided, returning');
        return;
    }

    try {
        const result = await apiCall('/predict/word', {
            method: 'POST',
            body: JSON.stringify({ word })
        });

        displayWordPrediction(result);
    } catch (error) {
        document.getElementById('predict-word-result').innerHTML =
            `<div class="alert alert-error">Errore nella predizione: ${error.message}</div>`;
    }
}

function displayWordPrediction(result) {
    const resultDiv = document.getElementById('predict-word-result');

    const confidenceIcon = getPredictionIcon(result.confidence);
    const confidenceClass = getPredictionClass(result.confidence);

    let pronunciationsHtml = '';
    if (result.in_lexicon && result.lexicon_pronunciations && result.lexicon_pronunciations.length > 0) {
        pronunciationsHtml = `
            <div class="prediction-detail">
                <strong>📚 Lessico Completo:</strong>
                ${result.lexicon_pronunciations.map(pron =>
                    `<span class="pronunciation">[${pron.join(' ')}]</span>`
                ).join(' ')}
            </div>
        `;
    }

    let g2pHtml = '';
    if (result.g2p_available && result.g2p_pronunciation) {
        g2pHtml = `
            <div class="prediction-detail">
                <strong>🔍 Phonetisaurus G2P:</strong>
                <span class="pronunciation">[${result.g2p_pronunciation.join(' ')}]</span>
                <small>(confidenza: ${(result.g2p_confidence * 100).toFixed(0)}%)</small>
            </div>
        `;
    }

    let similarWordsHtml = '';
    if (result.similar_words && result.similar_words.length > 0) {
        similarWordsHtml = `
            <div class="prediction-detail">
                <strong>🔗 Parole Simili:</strong>
                ${result.similar_words.map(w =>
                    `<span class="similar-word" onclick="document.getElementById('predict-word-input').value='${w.word}'; predictWord();">
                        ${w.word} (${(w.similarity * 100).toFixed(0)}%)
                    </span>`
                ).join('')}
            </div>
        `;
    }

    let notesHtml = '';
    if (result.notes && result.notes.length > 0) {
        notesHtml = `<div class="notes">${result.notes.join(' • ')}</div>`;
    }

    resultDiv.innerHTML = `
        <div class="prediction-card ${confidenceClass}">
            <div class="prediction-header">
                <span class="prediction-word">${confidenceIcon} ${result.word}</span>
                <span class="badge badge-prediction-${confidenceClass}">
                    ${getPredictionText(result.confidence)} (${(result.confidence_score * 100).toFixed(0)}%)
                </span>
            </div>

            ${pronunciationsHtml}
            ${g2pHtml}
            ${similarWordsHtml}

            <div class="prediction-recommendation">
                💡 ${result.recommendation}
            </div>

            ${notesHtml}
        </div>
    `;
}

// Entity prediction
window.predictEntity = async function() {
    console.log('🏠 predictEntity function called');
    const entityInput = document.getElementById('predict-entity-input');
    const entityName = entityInput.value.trim();
    console.log('Entity to predict:', entityName);

    if (!entityName) {
        console.log('No entity provided, returning');
        return;
    }

    try {
        const result = await apiCall('/predict/entity', {
            method: 'POST',
            body: JSON.stringify({ entity_name: entityName })
        });

        displayEntityPrediction(result);
    } catch (error) {
        document.getElementById('predict-entity-result').innerHTML =
            `<div class="alert alert-error">Errore nella predizione: ${error.message}</div>`;
    }
}

function displayEntityPrediction(result) {
    const resultDiv = document.getElementById('predict-entity-result');

    const overallIcon = getPredictionIcon(result.overall_confidence);
    const overallClass = getPredictionClass(result.overall_confidence);

    // Word breakdown
    let wordsHtml = result.word_predictions.map(wordPred => `
        <div class="word-prediction ${getPredictionClass(wordPred.confidence)}">
            <div class="word-prediction-header">
                <strong>${wordPred.word}</strong> ${getPredictionIcon(wordPred.confidence)}
                <span class="confidence-score">${(wordPred.confidence_score * 100).toFixed(0)}%</span>
            </div>
            <div class="word-prediction-details">
                ${wordPred.in_lexicon ?
                    `📚 Nel lessico (${wordPred.lexicon_pronunciations.length} pronuncie)` :
                    (wordPred.g2p_available ?
                        `🔍 G2P disponibile [${wordPred.g2p_pronunciation?.join(' ') || 'N/A'}]` :
                        '❌ Non riconoscibile'
                    )
                }
            </div>
        </div>
    `).join('');

    // Recommendations
    let recommendationsHtml = '';
    if (result.recommendations && result.recommendations.length > 0) {
        recommendationsHtml = `
            <div class="prediction-recommendations">
                <h4>💡 Raccomandazioni</h4>
                <ul>
                    ${result.recommendations.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    // Alternative suggestions
    let alternativesHtml = '';
    if (result.suggested_alternatives && result.suggested_alternatives.length > 0) {
        alternativesHtml = `
            <div class="prediction-alternatives">
                <h4>🔄 Alternative Suggerite</h4>
                <ul>
                    ${result.suggested_alternatives.map(alt => `<li>${alt}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    resultDiv.innerHTML = `
        <div class="prediction-card ${overallClass}">
            <div class="prediction-summary">
                <div>
                    <span class="prediction-entity">${overallIcon} ${result.entity_name}</span>
                    <br>
                    <small>Riconoscimento: ${result.recognition_percentage.toFixed(0)}% delle parole</small>
                </div>
                <span class="badge badge-prediction-${overallClass}">
                    ${getPredictionText(result.overall_confidence)} (${(result.overall_score * 100).toFixed(0)}%)
                </span>
            </div>

            <div class="word-predictions">
                <h4>📝 Analisi Parole</h4>
                ${wordsHtml}
            </div>

            ${recommendationsHtml}
            ${alternativesHtml}
        </div>
    `;
}

// Predictor statistics
window.loadPredictorStats = async function() {
    console.log('📊 loadPredictorStats function called');
    try {
        console.log('Calling /predict/stats API...');
        const stats = await apiCall('/predict/stats');
        console.log('Predictor stats received:', stats);
        displayPredictorStats(stats);
    } catch (error) {
        console.error('Error loading predictor stats:', error);
        const statsDiv = document.getElementById('predictor-stats');
        if (statsDiv) {
            statsDiv.innerHTML = `<div class="alert alert-error">Errore nel caricamento: ${error.message}</div>`;
        }
    }
}

function displayPredictorStats(stats) {
    const statsDiv = document.getElementById('predictor-stats');

    if (stats.error) {
        statsDiv.innerHTML = `<div class="alert alert-error">${stats.error}</div>`;
        return;
    }

    statsDiv.innerHTML = `
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">${stats.current_model || 'N/A'}</div>
                <div class="stat-label">Modello Corrente</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.lexicon?.total_words?.toLocaleString() || 'N/A'}</div>
                <div class="stat-label">Parole nel Lessico Completo</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.lexicon?.g2p_available ? '✅' : '❌'}</div>
                <div class="stat-label">G2P Disponibile</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.downloaded_models?.length || 0}</div>
                <div class="stat-label">Modelli Scaricati</div>
            </div>
        </div>

        <div style="margin-top: 20px; font-size: 14px; color: #6c757d;">
            <strong>Cache:</strong> ${stats.lexicon?.cache_size || 0} parole •
            <strong>Esempi:</strong> ${stats.lexicon?.sample_words?.join(', ') || 'N/A'}
        </div>
    `;
}

// Helper functions for predictions
function getPredictionIcon(confidence) {
    switch (confidence) {
        case 'excellent': return '🌟';
        case 'good': return '✅';
        case 'moderate': return '🔶';
        case 'poor': return '⚠️';
        case 'unknown': return '❌';
        default: return '❓';
    }
}

function getPredictionText(confidence) {
    switch (confidence) {
        case 'excellent': return 'Eccellente';
        case 'good': return 'Buono';
        case 'moderate': return 'Discreto';
        case 'poor': return 'Scarso';
        case 'unknown': return 'Sconosciuto';
        default: return 'N/A';
    }
}

function getPredictionClass(confidence) {
    switch (confidence) {
        case 'excellent': return 'excellent';
        case 'good': return 'good';
        case 'moderate': return 'moderate';
        case 'poor': return 'poor';
        case 'unknown': return 'unknown';
        default: return 'unknown';
    }
}

// Initialize (removed duplicate DOMContentLoaded listener)