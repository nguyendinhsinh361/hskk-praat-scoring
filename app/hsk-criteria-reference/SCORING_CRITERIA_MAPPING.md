# HSKK Scoring Criteria Mapping

> Tài liệu hướng dẫn ánh xạ giữa các tiêu chí chấm điểm HSKK và nguồn dữ liệu (Praat vs AI)

---

## 📊 Tổng quan

Hệ thống chấm điểm HSKK sử dụng **2 nguồn dữ liệu chính**:

| Nguồn | Mô tả | Tiêu chí áp dụng |
|-------|-------|------------------|
| **Praat** | Phân tích âm thanh acoustic | Phát âm, Độ trôi chảy |
| **AI/STT** | Speech-to-Text + NLP | Task Achievement, Ngữ pháp, Từ vựng, Mạch lạc |

---

## 🎯 Ánh xạ Tiêu chí → Nguồn dữ liệu

### ✅ Tiêu chí sử dụng PRAAT

#### 1. Phát âm (Pronunciation)

| Thông số Praat | Ý nghĩa | Đánh giá |
|----------------|---------|----------|
| `hnr_mean` | Harmonics-to-Noise Ratio | Độ trong của giọng (cao = giọng trong) |
| `jitter_local` | Biến thiên tần số F0 | Độ ổn định giọng (thấp = ổn định) |
| `shimmer_local` | Biến thiên biên độ | Độ đều âm lượng (thấp = đều) |
| `f1_mean` | Formant 1 | Độ mở nguyên âm |
| `f2_mean` | Formant 2 | Vị trí lưỡi (trước/sau) |
| `pitch_range` | Phạm vi cao độ | Ngữ điệu (cao = có biến thiên) |
| `pitch_std` | Độ lệch chuẩn cao độ | Sự biến thiên ngữ điệu |

**Ngưỡng đánh giá:**

```
HNR (Harmonics-to-Noise Ratio):
  - Excellent: ≥ 20 dB → Giọng rất trong
  - Good: ≥ 15 dB → Giọng tốt
  - Poor: < 15 dB → Giọng khàn, cần cải thiện

Jitter (Voice Stability):
  - Excellent: ≤ 0.01 → Giọng rất ổn định
  - Acceptable: ≤ 0.015 → Chấp nhận được
  - Poor: > 0.015 → Giọng không ổn định

Shimmer (Amplitude Stability):
  - Excellent: ≤ 0.05 → Âm lượng rất đều
  - Acceptable: ≤ 0.08 → Chấp nhận được
  - Poor: > 0.08 → Âm lượng không đều
```

---

#### 2. Độ trôi chảy (Fluency)

| Thông số Praat | Ý nghĩa | Đánh giá |
|----------------|---------|----------|
| `speech_rate` | Tốc độ nói (syllables/min) | Bao gồm cả ngắt nghỉ |
| `articulation_rate` | Tốc độ phát âm | Không tính ngắt nghỉ |
| `pause_ratio` | Tỷ lệ ngắt nghỉ | Thời gian pause/tổng thời gian |
| `num_pauses` | Số lần ngắt nghỉ | Đếm số pause |
| `mean_pause_duration` | Thời lượng TB mỗi pause | Giây |
| `pause_duration` | Tổng thời gian pause | Giây |
| `speech_duration` | Tổng thời gian nói | Giây |

**Ngưỡng đánh giá:**

```
Speech Rate (syllables/minute):
  - Too slow: < 100
  - Slow: 100 - 149
  - Ideal: 150 - 220 ✓
  - Fast: 221 - 280
  - Too fast: > 280

Pause Ratio:
  - Excellent: ≤ 0.15 → Rất trôi chảy
  - Acceptable: ≤ 0.25 → Chấp nhận được
  - Poor: > 0.35 → Quá nhiều ngắt nghỉ

Mean Pause Duration:
  - Excellent: ≤ 0.3s → Ngắt nghỉ tự nhiên
  - Acceptable: ≤ 0.6s → Chấp nhận được
```

**Phát hiện lỗi Fluency:**

| Lỗi | Điều kiện phát hiện (Praat) | Mô tả |
|-----|----------------------------|-------|
| `ngat_nghi_sai` | `pause_ratio > 0.25 OR mean_pause_duration > 0.6` | Ngắt nghỉ sai vị trí/quá dài |
| `ngap_ngung` | `num_pauses > 10 AND mean_pause_duration < 0.5` | Ngập ngừng, nhiều pause ngắn |
| `toc_do_khong_on_dinh` | `|articulation_rate - speech_rate| > 50` | Lúc nhanh lúc chậm |
| `lap_tu` | **Requires STT** | Lặp từ (không phát hiện được bằng Praat) |

---

### ❌ Tiêu chí YÊU CẦU AI/STT

> [!IMPORTANT]
> Các tiêu chí sau **KHÔNG THỂ** đánh giá chỉ bằng Praat, cần tích hợp Speech-to-Text và NLP.

#### 1. Khả năng hoàn thành yêu cầu (Task Achievement)

- **Yêu cầu**: Speech-to-Text để chuyển audio → text
- **Phân tích**: So sánh text similarity với đề bài/câu gốc
- **Đánh giá**: % nội dung được nhắc lại/trả lời chính xác

#### 2. Độ chính xác ngữ pháp (Grammatical Accuracy)

- **Yêu cầu**: STT + Chinese NLP (Jieba, HanLP)
- **Phân tích**: Grammar error detection
- **Đánh giá**: Số lỗi ngữ pháp, mức độ phức tạp câu

#### 3. Vốn từ vựng (Lexical Resource)

- **Yêu cầu**: STT + Vocabulary Level Checker
- **Phân tích**: HSK vocabulary level classification
- **Đánh giá**: Độ đa dạng và chính xác từ vựng

#### 4. Tính mạch lạc (Coherence and Cohesion)

- **Yêu cầu**: STT + Discourse Analysis
- **Phân tích**: Transition words, logical flow
- **Đánh giá**: Sự liên kết logic giữa các ý

#### 5. Phát hiện lặp từ (Word Repetition)

- **Yêu cầu**: STT để phát hiện từ lặp lại
- **Lưu ý**: Praat CHỈ phát hiện pause patterns, không phát hiện được lặp từ

---

## 📁 Cấu trúc JSON Criteria

Mỗi tiêu chí trong file JSON có các trường sau:

```json
{
  "name": "Tên tiêu chí",
  "data_source": "praat | ai | hybrid",
  "data_source_note": "Giải thích nguồn dữ liệu",
  
  // Nếu data_source = "praat"
  "praat_metrics": {
    "primary": ["hnr_mean", "jitter_local"],
    "secondary": ["f1_mean", "f2_mean"],
    "description": { ... },
    "thresholds": { ... },
    "issue_detection": { ... }
  },
  
  // Nếu data_source = "ai"
  "ai_requirements": {
    "stt_needed": true,
    "nlp_needed": true,
    "analysis_type": ["grammar_check", "vocabulary_diversity"],
    "description": "Mô tả yêu cầu AI"
  },
  
  "scoring_rules": [
    {
      "condition": "Mô tả điều kiện",
      "score": 2.0,
      "praat_condition": "hnr_mean >= 20 AND jitter_local <= 0.01"
    }
  ]
}
```

---

## 🔧 Hướng dẫn tích hợp

### Sử dụng Praat Metrics

```python
from app.services.scoring_service import ScoringService

# Khởi tạo service
scoring_service = ScoringService(settings)

# Tính điểm từ Praat features
score = scoring_service.calculate_score(praat_features, transcription=None)

# Phát hiện lỗi fluency
issues = scoring_service.detect_fluency_issues(praat_features)
# Returns: ['ngat_nghi_sai', 'ngap_ngung', ...]
```

### Tích hợp AI/STT (TODO)

```python
# Cần implement:
# 1. Whisper/Azure Speech STT integration
# 2. Chinese NLP pipeline (Jieba, HanLP)
# 3. Grammar checker
# 4. Vocabulary level classifier

transcription = stt_service.transcribe(audio_file)
grammar_score = nlp_service.check_grammar(transcription)
vocab_score = nlp_service.analyze_vocabulary(transcription)
```

---

## 📋 Bảng tổng hợp

| Tiêu chí | Data Source | Praat Metrics | AI Required |
|----------|-------------|---------------|-------------|
| Task Achievement | AI | - | STT + NLP |
| Pronunciation | **Praat** | hnr, jitter, shimmer, formants | - |
| Grammar | AI | - | STT + NLP |
| Fluency | **Praat** | speech_rate, pause_ratio, num_pauses | (STT for lặp từ only) |
| Vocabulary | AI | - | STT + NLP |
| Coherence | AI | - | STT + NLP |

---

## 🎓 Tham khảo

- **Praat**: [https://www.fon.hum.uva.nl/praat/](https://www.fon.hum.uva.nl/praat/)
- **HNR (Harmonics-to-Noise Ratio)**: Đo lường độ trong của giọng nói
- **Jitter/Shimmer**: Các chỉ số đánh giá chất lượng giọng nói
- **Formants (F1, F2)**: Tần số cộng hưởng xác định chất lượng nguyên âm
