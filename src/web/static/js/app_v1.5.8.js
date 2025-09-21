/**
 * Speech-to-Phrase Validator Frontend v1.5.8
 * Ottimizzato per Add-on Home Assistant
 */

console.log('🎤 Speech-to-Phrase Validator v1.5.8 - HA Add-on Optimized');

// Configuration
const CONFIG = {
    API_TIMEOUT: 10000,
    INGRESS_PATH: window.INGRESS_PATH || '',
    VERSION: '1.5.8'
};

// API Helper
async function apiCall(endpoint, options = {}) {
    const url = `${CONFIG.INGRESS_PATH}/api${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);

    try {
        console.log(`🔗 API Call: ${url}`);
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('✅ API Response:', data);
        return data;
    } catch (error) {
        clearTimeout(timeoutId);
        console.error('❌ API Error:', error);
        throw error;
    }
}

// Model Management
async function loadModels() {
    try {
        const data = await apiCall('/models');
        updateModelDisplay(data);
    } catch (error) {
        showError('Errore nel caricamento dei modelli: ' + error.message);
    }
}

function updateModelDisplay(data) {
    if (data.models && data.models.length > 0) {
        const model = data.models[0]; // Primo modello disponibile
        const statusDiv = document.getElementById('model-status');

        if (statusDiv) {
            let statusHtml = `
                <div class="model-info-card">
                    <h3>📊 Modello Attivo: ${model.id}</h3>
                    <div class="model-details">
                        <span class="badge badge-success">${model.type}</span>
                        <span class="badge">${model.language}</span>
                        ${model.is_ha_addon_optimized ? '<span class="badge badge-info">HA Add-on</span>' : ''}
                    </div>
                    <div class="model-stats">
                        <p><strong>Lessico:</strong> ${model.lexicon_words || 'N/A'} parole
                           ${model.is_ha_addon_optimized ? '(template personalizzati)' : '(database completo)'}</p>
                        <p><strong>Tipo Lessico:</strong> ${model.lexicon_type || 'N/A'}</p>
                        <p><strong>G2P:</strong> ${model.g2p_available ?
                            '✅ Disponibile' :
                            '⚠️ Gestito internamente (normale per add-on HA)'}</p>
                    </div>
                </div>
            `;
            statusDiv.innerHTML = statusHtml;
        }
    }
}

// Word Validation
async function validateWord() {
    const input = document.getElementById('word-input');
    const resultDiv = document.getElementById('word-result');

    if (!input || !resultDiv) return;

    const word = input.value.trim();
    if (!word) {
        showResult(resultDiv, '⚠️ Inserisci una parola da validare', 'warning');
        return;
    }

    showResult(resultDiv, '🔄 Validazione in corso...', 'info');

    try {
        const data = await apiCall('/validate/word', {
            method: 'POST',
            body: JSON.stringify({ word: word })
        });

        if (data.exists) {
            let message = `✅ <strong>${word}</strong> è riconosciuta nel modello attivo`;
            if (data.pronunciations && data.pronunciations.length > 0) {
                message += `<br><small>Pronuncie: ${data.pronunciations.map(p => p.join(' ')).join(', ')}</small>`;
            }
            showResult(resultDiv, message, 'success');
        } else {
            let message = `❌ <strong>${word}</strong> non è riconosciuta nel modello attivo`;
            if (data.suggestions && data.suggestions.length > 0) {
                message += `<br><small>Suggerimenti: ${data.suggestions.join(', ')}</small>`;
            }
            message += `<br><small>💡 Aggiungi entità/aree con questo nome in Home Assistant per renderla riconoscibile</small>`;
            showResult(resultDiv, message, 'error');
        }
    } catch (error) {
        showResult(resultDiv, `❌ Errore: ${error.message}`, 'error');
    }
}

// Entity Validation
async function validateEntity() {
    const input = document.getElementById('entity-input');
    const resultDiv = document.getElementById('entity-result');

    if (!input || !resultDiv) return;

    const entity = input.value.trim();
    if (!entity) {
        showResult(resultDiv, '⚠️ Inserisci il nome di un\'entità da validare', 'warning');
        return;
    }

    showResult(resultDiv, '🔄 Validazione entità in corso...', 'info');

    try {
        const data = await apiCall('/validate/entity', {
            method: 'POST',
            body: JSON.stringify({ entity_name: entity })
        });

        let message = `<strong>Entità:</strong> ${entity}<br>`;

        if (data.validation_results && data.validation_results.length > 0) {
            message += '<div class="entity-breakdown">';
            data.validation_results.forEach(result => {
                const icon = result.exists ? '✅' : '❌';
                const status = result.exists ? 'riconosciuta' : 'non riconosciuta';
                message += `<div class="word-status">${icon} <code>${result.word}</code> - ${status}</div>`;
            });
            message += '</div>';

            const recognized = data.validation_results.filter(r => r.exists).length;
            const total = data.validation_results.length;
            const percentage = Math.round((recognized / total) * 100);

            message += `<br><strong>Riconoscimento:</strong> ${recognized}/${total} parole (${percentage}%)`;

            if (percentage === 100) {
                message += '<br>🎉 Entità completamente riconoscibile!';
                showResult(resultDiv, message, 'success');
            } else if (percentage >= 50) {
                message += '<br>⚠️ Entità parzialmente riconoscibile';
                showResult(resultDiv, message, 'warning');
            } else {
                message += '<br>❌ Entità difficilmente riconoscibile';
                showResult(resultDiv, message, 'error');
            }
        } else {
            showResult(resultDiv, '❌ Impossibile validare l\'entità', 'error');
        }
    } catch (error) {
        showResult(resultDiv, `❌ Errore: ${error.message}`, 'error');
    }
}

// Statistics Loading
async function loadStatistics() {
    try {
        const data = await apiCall('/statistics');
        updateStatisticsDisplay(data);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

function updateStatisticsDisplay(data) {
    const statsDiv = document.getElementById('statistics-content');
    if (!statsDiv) return;

    let html = `
        <div class="stats-grid">
            <div class="stat-card">
                <h4>📚 Lessico Attivo</h4>
                <div class="stat-value">${data.lexicon_words || 0}</div>
                <div class="stat-label">parole riconoscibili</div>
                ${data.is_ha_addon ? '<small>Template personalizzati HA</small>' : '<small>Database completo</small>'}
            </div>
            <div class="stat-card">
                <h4>🏠 Modelli</h4>
                <div class="stat-value">${data.model_count || 0}</div>
                <div class="stat-label">modelli disponibili</div>
                ${data.is_ha_addon ? '<small>Add-on ottimizzato</small>' : '<small>Installazione standalone</small>'}
            </div>
            <div class="stat-card">
                <h4>🔧 Stato</h4>
                <div class="stat-value">${data.model_type || 'N/A'}</div>
                <div class="stat-label">tipo modello</div>
                <small>${data.model_language || 'Lingua sconosciuta'}</small>
            </div>
        </div>
    `;

    if (data.ha_addon_info) {
        html += `
            <div class="ha-addon-info">
                <h4>ℹ️ Informazioni Add-on Home Assistant</h4>
                <ul>
                    <li><strong>Configurazione:</strong> I modelli base sono gestiti internamente</li>
                    <li><strong>Lessico:</strong> Contiene solo parole dai template addestrati</li>
                    <li><strong>G2P:</strong> Gestione automatica parole sconosciute</li>
                    <li><strong>Re-training:</strong> Automatico al cambio configurazione HA</li>
                </ul>
            </div>
        `;
    }

    statsDiv.innerHTML = html;
}

// UI Helpers
function showResult(element, message, type) {
    if (!element) return;

    element.className = `result-area alert alert-${type}`;
    element.innerHTML = message;
    element.style.display = 'block';
}

function showError(message) {
    console.error('💥 Error:', message);
    // Could add toast notification here
}

// Theme Management
function toggleTheme() {
    const body = document.body;
    const isDark = body.classList.contains('dark-theme');

    if (isDark) {
        body.classList.remove('dark-theme');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
    }
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.body.classList.add('dark-theme');
    }
}

// Initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Speech-to-Phrase Validator v1.5.8');

    initializeTheme();
    loadModels();
    loadStatistics();

    // Auto-refresh statistics every 30 seconds
    setInterval(loadStatistics, 30000);

    console.log('✅ Speech-to-Phrase Validator ready!');
});

// Export for global access
window.STPValidator = {
    validateWord,
    validateEntity,
    loadModels,
    loadStatistics,
    toggleTheme,
    version: CONFIG.VERSION
};