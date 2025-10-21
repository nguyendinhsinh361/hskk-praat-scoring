// Biến toàn cục
let selectedFile = null;
let selectedLevel = 'intermediate';

// Các phần tử DOM
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingEl = document.getElementById('loading');
const resultsEl = document.getElementById('results');
const errorEl = document.getElementById('error');

// Định nghĩa chi tiết cho các features
const featureDescriptions = {
    // Basic Info
    'duration': 'Tổng thời lượng file audio',
    
    // Pitch Features
    'pitch_mean': 'Cao độ trung bình (Nam: 85-180 Hz, Nữ: 165-255 Hz)',
    'pitch_std': 'Độ biến thiên cao độ (>40: giàu cảm xúc, <20: đơn điệu)',
    'pitch_range': 'Phạm vi cao độ (<50: đơn điệu, 50-100: bình thường, >100: sinh động)',
    'pitch_min': 'Cao độ thấp nhất trong phát biểu',
    'pitch_max': 'Cao độ cao nhất trong phát biểu',
    'pitch_median': 'Cao độ trung vị (50% giá trị)',
    'pitch_q25': 'Phân vị 25 - 25% thời gian pitch thấp hơn',
    'pitch_q75': 'Phân vị 75 - 75% thời gian pitch thấp hơn',
    
    // Formants
    'f1_mean': 'Formant 1 - Độ mở miệng (300-1000 Hz)',
    'f1_std': 'Độ biến thiên F1 (cao: nhiều nguyên âm khác nhau)',
    'f2_mean': 'Formant 2 - Vị trí lưỡi (800-3000 Hz)',
    'f2_std': 'Độ biến thiên F2',
    'f3_mean': 'Formant 3 - Phụ âm /r/, chất lượng giọng (1500-4000 Hz)',
    'f3_std': 'Độ biến thiên F3',
    'f4_mean': 'Formant 4 - Đặc điểm cá nhân (2500-5000 Hz)',
    'f4_std': 'Độ biến thiên F4',
    
    // Intensity
    'intensity_mean': 'Độ to trung bình (<50: quá nhỏ, 60-70: lý tưởng, >80: quá to)',
    'intensity_std': 'Biến thiên độ to (>7: năng động, <4: thiếu trọng âm)',
    'intensity_min': 'Độ to nhỏ nhất - điểm yếu nhất',
    'intensity_max': 'Độ to lớn nhất - điểm nhấn mạnh',
    
    // Spectral
    'spectral_centroid': 'Trọng tâm năng lượng tần số (>2000: giọng sáng, <1000: giọng trầm)',
    'spectral_std': 'Độ rộng phổ (cao: phong phú, thấp: đơn điệu)',
    'spectral_skewness': 'Hình dạng phân phối phổ (>0: lệch phải, <0: lệch trái)',
    'spectral_kurtosis': 'Độ tập trung năng lượng (>3: đơn điệu, <3: phong phú)',
    
    // Voice Quality
    'hnr_mean': 'Tỷ lệ hài/nhiễu (<10: khàn, 15-25: tốt, >25: rất trong)',
    'hnr_std': 'Độ ổn định chất lượng giọng (<2: ổn định, >5: không đều)',
    
    // Jitter
    'jitter_local': 'Dao động pitch cục bộ (<0.5%: rất tốt, 0.5-1%: bình thường, >2%: vấn đề)',
    'jitter_rap': 'Jitter TB 3 chu kỳ (<0.68%: tốt) - nhạy hơn jitter_local',
    'jitter_ppq5': 'Jitter TB 5 chu kỳ (<0.84%: tốt) - ổn định dài hạn',
    
    // Shimmer
    'shimmer_local': 'Dao động biên độ (<3%: tốt, 3-6%: bình thường, >10%: vấn đề)',
    'shimmer_apq3': 'Shimmer TB 3 chu kỳ (<1.65%: tốt)',
    'shimmer_apq5': 'Shimmer TB 5 chu kỳ (<2.07%: tốt)',
    'shimmer_apq11': 'Shimmer TB 11 chu kỳ (<3.07%: tốt) - ổn định dài hạn',
    
    // Speech Timing
    'speech_rate': 'Tốc độ nói tổng thể (<120: chậm, 120-180: bình thường, >250: rất nhanh)',
    'articulation_rate': 'Tốc độ phát âm thực (không tính nghỉ)',
    'speech_duration': 'Thời gian thực sự có âm thanh',
    'pause_duration': 'Tổng thời gian im lặng/nghỉ',
    'pause_ratio': 'Tỷ lệ im lặng (<0.2: lưu loát, 0.2-0.3: bình thường, >0.4: quá nhiều nghỉ)',
    'num_pauses': 'Số lần dừng/nghỉ (chỉ tính >0.1 giây)',
    'mean_pause': 'TB thời gian nghỉ (<0.3s: ngắn, 0.3-0.5s: bình thường, >1s: quá lâu)',
    
    // Additional
    'cog': 'Tâm trọng lực phổ - phân biệt phụ âm',
    'slope': 'Độ dốc phổ (dương: sáng, âm: trầm, ~0: cân bằng)',
    'spread': 'Độ chênh lệch năng lượng cao-thấp'
};

// Đánh giá giá trị feature
function evaluateFeature(name, value) {
    const evaluations = {
        'pitch_std': value > 40 ? '🟢 Giàu cảm xúc' : value < 20 ? '🔴 Đơn điệu' : '🟡 Bình thường',
        'pitch_range': value < 50 ? '🔴 Rất đơn điệu' : value < 100 ? '🟡 Bình thường' : '🟢 Sinh động',
        'intensity_mean': value < 50 ? '🔴 Quá nhỏ' : value > 80 ? '🔴 Quá to' : '🟢 Lý tưởng',
        'intensity_std': value > 7 ? '🟢 Năng động' : value < 4 ? '🟡 Thiếu trọng âm' : '🟢 Tốt',
        'hnr_mean': value < 10 ? '🔴 Giọng khàn' : value > 25 ? '🟢 Rất trong' : '🟢 Tốt',
        'jitter_local': (value * 100) < 0.5 ? '🟢 Rất tốt' : (value * 100) < 1 ? '🟡 Bình thường' : '🔴 Vấn đề',
        'shimmer_local': (value * 100) < 3 ? '🟢 Tốt' : (value * 100) < 6 ? '🟡 Bình thường' : '🔴 Vấn đề',
        'speech_rate': value < 120 ? '🟡 Chậm' : value > 250 ? '🔴 Rất nhanh' : '🟢 Bình thường',
        'pause_ratio': value < 0.2 ? '🟢 Lưu loát' : value < 0.3 ? '🟢 Bình thường' : '🔴 Nhiều nghỉ'
    };
    return evaluations[name] || '';
}

// Khởi tạo event listeners
function initializeEventListeners() {
    uploadBox.addEventListener('click', () => fileInput.click());
    uploadBox.addEventListener('dragover', handleDragOver);
    uploadBox.addEventListener('dragleave', handleDragLeave);
    uploadBox.addEventListener('drop', handleDrop);
    fileInput.addEventListener('change', handleFileInputChange);
    
    document.querySelectorAll('.level-btn').forEach(btn => {
        btn.addEventListener('click', handleLevelSelection);
    });
    
    analyzeBtn.addEventListener('click', handleAnalyze);
}

// Xử lý kéo thả
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

// Xử lý chọn file
function handleFileSelect(file) {
    const validExtensions = ['.wav', '.mp3', '.m4a', '.flac'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(fileExtension)) {
        showError('Định dạng file không hợp lệ. Vui lòng tải lên file WAV, MP3, M4A hoặc FLAC.');
        return;
    }

    selectedFile = file;
    document.getElementById('selectedFile').innerHTML = `
        ✅ Đã chọn: <strong>${file.name}</strong> (${(file.size / 1024 / 1024).toFixed(2)} MB)
    `;
    analyzeBtn.disabled = false;
    hideError();
}

// Xử lý chọn cấp độ
function handleLevelSelection(e) {
    document.querySelectorAll('.level-btn').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    selectedLevel = e.target.dataset.level;
}

// Xử lý phân tích
async function handleAnalyze() {
    if (!selectedFile) {
        showError('Vui lòng chọn file âm thanh trước.');
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
            showError(data.error_message || 'Phân tích thất bại. Vui lòng thử lại.');
        }
    } catch (error) {
        hideLoading();
        showError('Lỗi kết nối: ' + error.message + '. Đảm bảo server đang chạy.');
    }
}

// Hiển thị kết quả
function displayResults(data) {
    showResults();

    // Điểm tổng thể
    document.getElementById('overallScore').textContent = data.score.overall_score.toFixed(1);
    const levelNames = {
        'elementary': 'SƠ CẤP (初级 Elementary)',
        'intermediate': 'TRUNG CẤP (中级 Intermediate)',
        'advanced': 'CAO CẤP (高级 Advanced)'
    };
    document.getElementById('levelAchieved').textContent = `Cấp độ đạt được: ${levelNames[data.score.level_achieved]}`;

    // Điểm chi tiết
    document.getElementById('pronunciationScore').textContent = data.score.pronunciation.toFixed(1);
    document.getElementById('fluencyScore').textContent = data.score.fluency.toFixed(1);
    document.getElementById('grammarScore').textContent = data.score.grammar.toFixed(1);
    document.getElementById('vocabularyScore').textContent = data.score.vocabulary.toFixed(1);

    // Thông tin âm thanh
    const features = data.features;
    document.getElementById('audioInfo').innerHTML = `
        <h3 style="margin-bottom: 15px;">📁 Thông Tin Âm Thanh</h3>
        <p><strong>Thời lượng tổng (Total Duration):</strong> ${features.duration.toFixed(2)} giây</p>
        <p><strong>Thời gian nói (Speech Duration):</strong> ${features.speech_duration.toFixed(2)} giây (${((features.speech_duration/features.duration)*100).toFixed(1)}%)</p>
        <p><strong>Thời gian dừng (Pause Duration):</strong> ${features.pause_duration.toFixed(2)} giây (${(features.pause_ratio*100).toFixed(1)}%)</p>
        <p><strong>Thời gian xử lý (Processing Time):</strong> ${data.processing_time.toFixed(2)} giây</p>
    `;

    // Hiển thị 43 đặc trưng với chú thích
    displayFeatureCategory('basicFeatures', [
        ['Thời lượng (Duration)', features.duration, 'giây', 'duration']
    ]);

    displayFeatureCategory('pitchFeatures', [
        ['Cao độ TB (Mean Pitch)', features.pitch_mean, 'Hz', 'pitch_mean'],
        ['Độ lệch chuẩn (Std Dev)', features.pitch_std, 'Hz', 'pitch_std'],
        ['Khoảng cao độ (Range)', features.pitch_range, 'Hz', 'pitch_range'],
        ['Cao độ tối thiểu (Min)', features.pitch_min, 'Hz', 'pitch_min'],
        ['Cao độ tối đa (Max)', features.pitch_max, 'Hz', 'pitch_max'],
        ['Cao độ trung vị (Median)', features.pitch_median, 'Hz', 'pitch_median'],
        ['Phân vị 25 (Q25)', features.pitch_quantile_25, 'Hz', 'pitch_q25'],
        ['Phân vị 75 (Q75)', features.pitch_quantile_75, 'Hz', 'pitch_q75']
    ]);

    displayFeatureCategory('formantFeatures', [
        ['F1 TB - Độ mở miệng', features.f1_mean, 'Hz', 'f1_mean'],
        ['F1 Độ lệch (Std)', features.f1_std, 'Hz', 'f1_std'],
        ['F2 TB - Vị trí lưỡi', features.f2_mean, 'Hz', 'f2_mean'],
        ['F2 Độ lệch (Std)', features.f2_std, 'Hz', 'f2_std'],
        ['F3 TB - Chất lượng giọng', features.f3_mean, 'Hz', 'f3_mean'],
        ['F3 Độ lệch (Std)', features.f3_std, 'Hz', 'f3_std'],
        ['F4 TB - Đặc điểm cá nhân', features.f4_mean, 'Hz', 'f4_mean'],
        ['F4 Độ lệch (Std)', features.f4_std, 'Hz', 'f4_std']
    ]);

    displayFeatureCategory('intensityFeatures', [
        ['Cường độ TB (Mean)', features.intensity_mean, 'dB', 'intensity_mean'],
        ['Độ lệch chuẩn (Std)', features.intensity_std, 'dB', 'intensity_std'],
        ['Cường độ tối thiểu (Min)', features.intensity_min, 'dB', 'intensity_min'],
        ['Cường độ tối đa (Max)', features.intensity_max, 'dB', 'intensity_max']
    ]);

    displayFeatureCategory('spectralFeatures', [
        ['Trọng tâm phổ (Centroid)', features.spectral_centroid, 'Hz', 'spectral_centroid'],
        ['Độ lệch chuẩn phổ (Std)', features.spectral_std, 'Hz', 'spectral_std'],
        ['Độ lệch phổ (Skewness)', features.spectral_skewness, '', 'spectral_skewness'],
        ['Độ nhọn phổ (Kurtosis)', features.spectral_kurtosis, '', 'spectral_kurtosis']
    ]);

    displayFeatureCategory('voiceQualityFeatures', [
        ['HNR TB - Tỷ lệ hài/nhiễu', features.hnr_mean, 'dB', 'hnr_mean'],
        ['HNR Độ lệch (Std)', features.hnr_std, 'dB', 'hnr_std'],
        ['Jitter Cục bộ (Local)', (features.jitter_local * 100).toFixed(3), '%', 'jitter_local'],
        ['Jitter RAP - 3 chu kỳ', (features.jitter_rap * 100).toFixed(3), '%', 'jitter_rap'],
        ['Jitter PPQ5 - 5 chu kỳ', (features.jitter_ppq5 * 100).toFixed(3), '%', 'jitter_ppq5'],
        ['Shimmer Cục bộ (Local)', (features.shimmer_local * 100).toFixed(2), '%', 'shimmer_local'],
        ['Shimmer APQ3 - 3 chu kỳ', (features.shimmer_apq3 * 100).toFixed(2), '%', 'shimmer_apq3'],
        ['Shimmer APQ5 - 5 chu kỳ', (features.shimmer_apq5 * 100).toFixed(2), '%', 'shimmer_apq5'],
        ['Shimmer APQ11 - 11 chu kỳ', (features.shimmer_apq11 * 100).toFixed(2), '%', 'shimmer_apq11'],
        ['Độ hài hòa (Harmonicity)', features.hnr_mean, 'dB', 'hnr_mean']
    ]);

    displayFeatureCategory('timingFeatures', [
        ['Tốc độ nói (Speech Rate)', features.speech_rate, 'âm tiết/phút', 'speech_rate'],
        ['Tốc độ phát âm (Articulation)', features.articulation_rate, 'âm tiết/phút', 'articulation_rate'],
        ['Thời gian nói (Speech Dur)', features.speech_duration, 'giây', 'speech_duration'],
        ['Thời gian dừng (Pause Dur)', features.pause_duration, 'giây', 'pause_duration'],
        ['Tỷ lệ dừng (Pause Ratio)', (features.pause_ratio * 100).toFixed(1), '%', 'pause_ratio'],
        ['Số lần dừng (Num Pauses)', features.num_pauses, 'lần', 'num_pauses'],
        ['TB thời gian dừng (Mean)', features.mean_pause_duration, 'giây', 'mean_pause']
    ]);

    displayFeatureCategory('additionalFeatures', [
        ['Tâm trọng lực (COG)', features.cog, 'Hz', 'cog'],
        ['Độ dốc phổ (Slope)', features.slope, '', 'slope'],
        ['Độ phân tán phổ (Spread)', features.spread, 'Hz', 'spread']
    ]);

    // Phản hồi phát âm
    if (data.pronunciation && data.pronunciation.detailed_feedback) {
        displayFeedback(data.pronunciation.detailed_feedback);
    }
}

// Hiển thị danh mục đặc trưng với tooltip
function displayFeatureCategory(elementId, features) {
    const html = features.map(([name, value, unit, key]) => {
        const description = featureDescriptions[key] || '';
        const evaluation = evaluateFeature(key, typeof value === 'number' ? value : parseFloat(value));
        const displayValue = typeof value === 'number' ? value.toFixed(2) : value;
        
        return `
            <div class="feature-row" title="${description}">
                <span class="feature-name">
                    ${name}
                    ${evaluation ? `<span style="margin-left: 5px;">${evaluation}</span>` : ''}
                </span>
                <span class="feature-value">${displayValue} ${unit}</span>
            </div>
            ${description ? `<div style="font-size: 0.85em; color: #888; padding: 5px 0; font-style: italic;">💡 ${description}</div>` : ''}
        `;
    }).join('');
    document.getElementById(elementId).innerHTML = html;
}

// Hiển thị phản hồi phát âm
function displayFeedback(feedback) {
    const feedbackSection = document.getElementById('feedbackSection');
    
    if (Object.keys(feedback).length === 0) {
        feedbackSection.style.display = 'none';
        return;
    }
    
    let html = '<h3>💬 Phản Hồi Phát Âm (Pronunciation Feedback)</h3>';
    
    for (const [key, value] of Object.entries(feedback)) {
        const keyMapping = {
            'speech_rate': '⚡ Tốc độ nói',
            'pauses': '⏸️ Khoảng dừng',
            'voice_quality': '🎙️ Chất lượng giọng',
            'prosody': '🎵 Ngữ điệu'
        };
        const displayKey = keyMapping[key] || key;
        html += `<div class="feedback-item"><strong>${displayKey}:</strong> ${value}</div>`;
    }
    
    feedbackSection.innerHTML = html;
    feedbackSection.style.display = 'block';
}

// Các hàm trợ giúp UI
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
    errorEl.textContent = '❌ Lỗi: ' + message;
    errorEl.classList.add('show');
}

function hideError() {
    errorEl.classList.remove('show');
}

// Khởi tạo khi trang được tải
document.addEventListener('DOMContentLoaded', initializeEventListeners);