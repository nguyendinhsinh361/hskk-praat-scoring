# HSKK Speech Assessment System

🎤 **Automated Chinese Speaking Proficiency Assessment** using Multi-Model STT + Praat + AI

---

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository>
cd hskk-praat-scoring
cp .env.example .env

# 2. Edit .env with your API keys
# OPENAI_API_KEY=your_key
# GEMINI_API_KEY=your_key

# 3. Build and run
docker-compose build
docker-compose up -d

# 4. Test API
curl http://localhost:8000/docs
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      /api/v1/score/full                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           STEP 1: Multi-Model STT (Parallel)            │   │
│  ├───────────────┬───────────────┬─────────────────────────┤   │
│  │ OpenAI        │ FunASR        │ Gemini STT              │   │
│  │ Whisper       │ paraformer-zh │ Multimodal              │   │
│  │ (Cloud)       │ (Local CPU)   │ (Cloud)                 │   │
│  └───────────────┴───────────────┴─────────────────────────┘   │
│                            +                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           STEP 1: Praat Features (Parallel)             │   │
│  │              43 Acoustic Features from Praat            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ↓                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           STEP 2: Scoring Engine                        │   │
│  ├─────────────────────────┬───────────────────────────────┤   │
│  │ PRAAT CRITERIA          │ AI CRITERIA (GPT)             │   │
│  │ - Pronunciation         │ - Task Achievement            │   │
│  │ - Fluency               │ - Grammar                     │   │
│  │                         │ - Vocabulary                  │   │
│  │                         │ - Coherence                   │   │
│  └─────────────────────────┴───────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Scoring Criteria

### 🔊 PRAAT Criteria (Acoustic Analysis)

#### 1. Pronunciation (Phát âm)
Đánh giá chất lượng phát âm dựa trên các thông số âm học:

| Thông số | Mô tả | Ngưỡng tốt | Ý nghĩa |
|----------|-------|------------|---------|
| `hnr_mean` | Harmonics-to-Noise Ratio | ≥ 20 dB | Độ trong của giọng nói |
| `jitter_local` | Frequency perturbation | ≤ 0.01 | Độ ổn định tần số |
| `shimmer_local` | Amplitude perturbation | ≤ 0.05 | Độ ổn định âm lượng |
| `f1_mean`, `f2_mean` | Formant frequencies | - | Chất lượng nguyên âm |
| `pitch_range` | Pitch variation | - | Ngữ điệu |

**Scoring Logic:**
```
HNR ≥ 20: Excellent (0% deduction)
HNR 15-20: Good (-15%)
HNR 10-15: Acceptable (-30%)
HNR < 10: Poor (-50%)

Jitter ≤ 0.01: Excellent (0%)
Jitter 0.01-0.015: Acceptable (-15%)
Jitter 0.015-0.02: Poor (-25%)
Jitter > 0.02: Very Poor (-35%)
```

#### 2. Fluency (Độ trôi chảy)
Đánh giá mạch lời nói dựa trên thời gian:

| Thông số | Mô tả | Ngưỡng lý tưởng | Ý nghĩa |
|----------|-------|-----------------|---------|
| `speech_rate` | Syllables/minute | 150-220 | Tốc độ nói tổng thể |
| `pause_ratio` | Pause time / Total time | ≤ 0.15 | Tỉ lệ ngắt nghỉ |
| `num_pauses` | Số lần ngắt nghỉ | < 10/30s | Mức độ ngập ngừng |
| `mean_pause_duration` | Thời gian ngắt trung bình | ≤ 0.3s | Độ dài pause |
| `articulation_rate` | Tốc độ nói (không tính pause) | - | Tốc độ phát âm thực |

**Scoring Logic:**
- 0 issues → 100% max score
- 1 issue → 75% max score  
- 2 issues → 50% max score
- 3+ issues → 25% max score

---

### 🤖 AI Criteria (GPT Analysis)

Sử dụng **Multi-Model STT** làm input, GPT phân tích:

#### 3. Task Achievement (Hoàn thành nhiệm vụ)
- So sánh với reference text (nếu có)
- Đánh giá độ đầy đủ nội dung
- Kiểm tra độ liên quan với câu hỏi

#### 4. Grammar (Ngữ pháp)
- So sánh 3 phiên bản STT với nhau
- Nếu STT nhất quán nhưng khác Gemini intent → Lỗi ngữ pháp
- Nếu STT không nhất quán → Phát âm không rõ

#### 5. Vocabulary (Từ vựng)
- Đánh giá độ phong phú từ vựng
- Kiểm tra sử dụng từ đúng ngữ cảnh
- Đánh giá mức độ phù hợp với level

#### 6. Coherence (Mạch lạc)
- Đánh giá tính logic của câu trả lời
- Kiểm tra sự kết nối giữa các ý
- Đánh giá cấu trúc bài nói

---

## 🌐 API Endpoint

### POST `/api/v1/score/full`

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `audio_file` | File | required | Audio file (wav, mp3, m4a, flac) |
| `exam_level` | Enum | 101 | 101=Beginner, 102=Intermediate, 103=Advanced |
| `task_code` | Enum | HSKKSC1 | Task identifier |
| `reference_text` | String | null | Expected answer text |
| `openai_model` | Enum | gpt-4.1-mini | GPT model for scoring |
| `gemini_model` | Enum | gemini-2.5-flash | Gemini model for STT |

**Response:**
```json
{
  "success": true,
  "task_info": {
    "task_code": "HSKKSC1",
    "task_name": "Sơ cấp - Bài 1",
    "criteria_count": 4
  },
  "stt": {
    "whisper": "我叫小明",
    "fun_asr": "我叫小明",
    "gemini": "我叫小明"
  },
  "scores": {
    "pronunciation": {
      "score": 3.5,
      "max_score": 4.0,
      "percentage": 87.5,
      "feedback": "Phát âm rõ ràng..."
    },
    "fluency": {...},
    "grammar": {...},
    "task_achievement": {...}
  },
  "total_score": 18.5,
  "max_total_score": 20.0,
  "total_percentage": 92.5,
  "processing_time": 8.5
}
```

---

## 🔄 Multi-Language Prompts

Hệ thống hỗ trợ prompts đa ngôn ngữ:

```python
# Trong app/services/prompts.py
PROMPTS = PROMPTS_EN  # English (default)
PROMPTS = PROMPTS_ZH  # Chinese
PROMPTS = PROMPTS_VI  # Vietnamese
```

---

## 📁 Project Structure

```
hskk-praat-scoring/
├── app/
│   ├── api/v1/
│   │   └── scoring.py          # API endpoint
│   ├── services/
│   │   ├── tri_core_service.py # Multi-Model STT + AI Scoring
│   │   ├── prompts.py          # Multi-language prompts
│   │   └── assessment_service.py
│   ├── scorers/
│   │   ├── praat_scorers/
│   │   │   ├── pronunciation_scorer.py  # HNR, Jitter, Shimmer
│   │   │   └── fluency_scorer.py        # Speech rate, Pauses
│   │   └── ai_scorers/
│   │       └── ...             # Legacy (replaced by tri_core)
│   └── models/
├── docker/
│   └── Dockerfile
├── praat_scripts/
│   └── extract_features.praat
└── docker-compose.yml
```

---

## ⚡ Performance Optimization

| Optimization | Impact |
|--------------|--------|
| FunASR pre-loaded at startup | -20s first request |
| STT + Praat run in parallel | -10s per request |
| soundfile instead of librosa | -3s audio loading |
| Fast numpy trim (< 60s audio) | -1.5s preprocessing |

**Target:** ~8-12s per request (from 58s)

---

## 🔧 Environment Variables

```env
OPENAI_API_KEY=sk-...          # Required for Whisper + GPT
GEMINI_API_KEY=AI...           # Required for Gemini STT
OPENAI_MODEL=gpt-4.1-mini      # GPT model for scoring
GEMINI_MODEL=gemini-2.5-flash  # Gemini model for STT
```

---

## 📝 License

MIT License