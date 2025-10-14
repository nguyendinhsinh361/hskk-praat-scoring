// Global variables
let selectedFile = null;
let selectedLevel = 'intermediate';

// DOM elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingEl = document.getElementById('loading');
const resultsEl = document.getElementById('results');
const errorEl = document.getElementById('error');

// Initialize event listeners
function initializeEventListeners() {
    // Upload box click
    uploadBox.addEventListener('click', () => fileInput.click());

    // Drag and drop
    uploadBox.addEventListener('dragover', handleDragOver);
    uploadBox.addEventListener('dragleave', handleDragLeave);
    uploadBox.addEventListener('drop', handleDrop);

    // File input change
    fileInput.addEventListener('change', handleFileInputChange);

    // Level selection buttons
    document.querySelectorAll('.level-btn').forEach(btn => {
        btn.addEventListener('click', handleLevelSelection);
    });

    // Analyze button
    analyzeBtn.addEventListener('click', handleAnalyze);
}

// Drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    uploadBox.classList.add('dragover');
}

function handleDragLeave() {
    uploadBox.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
}

function handleFileInputChange(e) {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
}

// File selection handler
function handleFileSelect(file) {
    // Validate file type
    const validExtensions = ['.wav', '.mp3', '.m4a', '.flac'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(fileExtension)) {
        showError('Invalid file type. Please upload WAV, MP3, M4A, or FLAC file.');
        return;
    }

    selectedFile = file;
    document.getElementById('selectedFile').innerHTML = `
        ✅ Selected: <strong>${file.name}</strong> (${(file.size / 1024 / 1024).toFixed(2)} MB)
    `;
    analyzeBtn.disabled = false;
    hideError();
}

// Level selection handler
function handleLevelSelection(e) {
    document.querySelectorAll('.level-btn').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    selectedLevel = e.target.dataset.level;
}

// Analyze button handler
async function handleAnalyze() {
    if (!selectedFile) {
        showError('Please select an audio file first.');
        return;
    }

    const formData = new FormData();
    formData.append('audio_file', selectedFile);
    formData.append('target_level', selectedLevel);

    showLoading();
    hideResults();
    hideError();

    try {
        const response = await fetch('/assess', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        hideLoading();

        if (data.success) {
            displayResults(data);
        } else {
            showError(data.error_message || 'Analysis failed. Please try again.');
        }
    } catch (error) {
        hideLoading();
        showError('Connection error: ' + error.message + '. Make sure the server is running.');
    }
}

// Display results
function displayResults(data) {
    showResults();

    // Overall score
    document.getElementById('overallScore').textContent = data.score.overall_score.toFixed(1);
    document.getElementById('levelAchieved').textContent = `Level: ${data.score.level_achieved.toUpperCase()}`;

    // Score breakdown
    document.getElementById('pronunciationScore').textContent = data.score.pronunciation.toFixed(1);
    document.getElementById('fluencyScore').textContent = data.score.fluency.toFixed(1);
    document.getElementById('grammarScore').textContent = data.score.grammar.toFixed(1);
    document.getElementById('vocabularyScore').textContent = data.score.vocabulary.toFixed(1);

    // Audio info
    const features = data.features;
    document.getElementById('audioInfo').innerHTML = `
        <h3 style="margin-bottom: 15px;">📁 Audio Information</h3>
        <p><strong>Duration:</strong> ${features.duration.toFixed(2)} seconds</p>
        <p><strong>Speech Duration:</strong> ${features.speech_duration.toFixed(2)} seconds</p>
        <p><strong>Pause Duration:</strong> ${features.pause_duration.toFixed(2)} seconds</p>
        <p><strong>Processing Time:</strong> ${data.processing_time.toFixed(2)} seconds</p>
    `;

    // Display all 43 features
    displayFeatureCategory('basicFeatures', [
        ['Duration', features.duration, 's']
    ]);

    displayFeatureCategory('pitchFeatures', [
        ['Mean Pitch', features.pitch_mean, 'Hz'],
        ['Std Deviation', features.pitch_std, 'Hz'],
        ['Pitch Range', features.pitch_range, 'Hz'],
        ['Min Pitch', features.pitch_min, 'Hz'],
        ['Max Pitch', features.pitch_max, 'Hz'],
        ['Median Pitch', features.pitch_median, 'Hz'],
        ['25th Percentile', features.pitch_quantile_25, 'Hz'],
        ['75th Percentile', features.pitch_quantile_75, 'Hz']
    ]);

    displayFeatureCategory('formantFeatures', [
        ['F1 Mean', features.f1_mean, 'Hz'],
        ['F1 Std', features.f1_std, 'Hz'],
        ['F2 Mean', features.f2_mean, 'Hz'],
        ['F2 Std', features.f2_std, 'Hz'],
        ['F3 Mean', features.f3_mean, 'Hz'],
        ['F3 Std', features.f3_std, 'Hz'],
        ['F4 Mean', features.f4_mean, 'Hz'],
        ['F4 Std', features.f4_std, 'Hz']
    ]);

    displayFeatureCategory('intensityFeatures', [
        ['Mean Intensity', features.intensity_mean, 'dB'],
        ['Std Deviation', features.intensity_std, 'dB'],
        ['Min Intensity', features.intensity_min, 'dB'],
        ['Max Intensity', features.intensity_max, 'dB']
    ]);

    displayFeatureCategory('spectralFeatures', [
        ['Spectral Centroid', features.spectral_centroid, 'Hz'],
        ['Spectral Std', features.spectral_std, 'Hz'],
        ['Spectral Skewness', features.spectral_skewness, ''],
        ['Spectral Kurtosis', features.spectral_kurtosis, '']
    ]);

    displayFeatureCategory('voiceQualityFeatures', [
        ['HNR Mean', features.hnr_mean, 'dB'],
        ['HNR Std', features.hnr_std, 'dB'],
        ['Jitter Local', (features.jitter_local * 100).toFixed(3), '%'],
        ['Jitter RAP', (features.jitter_rap * 100).toFixed(3), '%'],
        ['Jitter PPQ5', (features.jitter_ppq5 * 100).toFixed(3), '%'],
        ['Shimmer Local', (features.shimmer_local * 100).toFixed(2), '%'],
        ['Shimmer APQ3', (features.shimmer_apq3 * 100).toFixed(2), '%'],
        ['Shimmer APQ5', (features.shimmer_apq5 * 100).toFixed(2), '%'],
        ['Shimmer APQ11', (features.shimmer_apq11 * 100).toFixed(2), '%'],
        ['Harmonicity', features.hnr_mean, 'dB']
    ]);

    displayFeatureCategory('timingFeatures', [
        ['Speech Rate', features.speech_rate, 'syl/min'],
        ['Articulation Rate', features.articulation_rate, 'syl/min'],
        ['Speech Duration', features.speech_duration, 's'],
        ['Pause Duration', features.pause_duration, 's'],
        ['Pause Ratio', (features.pause_ratio * 100).toFixed(1), '%'],
        ['Number of Pauses', features.num_pauses, ''],
        ['Mean Pause Duration', features.mean_pause_duration, 's']
    ]);

    displayFeatureCategory('additionalFeatures', [
        ['Center of Gravity', features.cog, 'Hz'],
        ['Spectral Slope', features.slope, ''],
        ['Spectral Spread', features.spread, 'Hz']
    ]);

    // Pronunciation feedback
    if (data.pronunciation && data.pronunciation.detailed_feedback) {
        displayFeedback(data.pronunciation.detailed_feedback);
    }
}

// Display feature category
function displayFeatureCategory(elementId, features) {
    const html = features.map(([name, value, unit]) => `
        <div class="feature-row">
            <span class="feature-name">${name}</span>
            <span class="feature-value">${typeof value === 'number' ? value.toFixed(2) : value} ${unit}</span>
        </div>
    `).join('');
    document.getElementById(elementId).innerHTML = html;
}

// Display pronunciation feedback
function displayFeedback(feedback) {
    const feedbackSection = document.getElementById('feedbackSection');
    
    if (Object.keys(feedback).length === 0) {
        feedbackSection.style.display = 'none';
        return;
    }
    
    let html = '<h3>💬 Pronunciation Feedback</h3>';
    
    for (const [key, value] of Object.entries(feedback)) {
        html += `<div class="feedback-item"><strong>${key}:</strong> ${value}</div>`;
    }
    
    feedbackSection.innerHTML = html;
    feedbackSection.style.display = 'block';
}

// UI state helpers
function showLoading() {
    loadingEl.classList.add('show');
}

function hideLoading() {
    loadingEl.classList.remove('show');
}

function showResults() {
    resultsEl.classList.add('show');
}

function hideResults() {
    resultsEl.classList.remove('show');
}

function showError(message) {
    errorEl.textContent = '❌ Error: ' + message;
    errorEl.classList.add('show');
}

function hideError() {
    errorEl.classList.remove('show');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeEventListeners);