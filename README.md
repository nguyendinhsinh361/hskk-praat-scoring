# HSKK Praat Scoring System

🎤 Automated Chinese Speaking Proficiency Assessment using Praat and Docker

## Features

- **Acoustic Analysis**: Pitch, formants, voice quality using Praat
- **HSKK Scoring**: Elementary, Intermediate, Advanced levels  
- **Pronunciation Assessment**: Accuracy, fluency, prosody scoring
- **Docker Integration**: Containerized Praat for consistent analysis
- **REST API**: Easy integration with web applications
- **Real-time Processing**: Fast audio analysis and scoring

## Quick Start

### 1. Setup
```bash
git clone <repository>
cd hskk-praat-scoring
cp .env.example .env
```

### 2. Build and Run
```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 3. Test API
```bash
# Upload audio for assessment
curl -X POST "http://localhost:8000/assess" \\
  -F "audio_file=@test_audio.wav" \\
  -F "target_level=intermediate"
```

### 4. Web Interface
Open http://localhost:8000 in your browser

## API Endpoints

- `POST /assess` - Assess HSKK speaking proficiency
- `GET /levels` - Get available HSKK levels
- `GET /health` - Health check
- `GET /docs` - API documentation

## HSKK Scoring Criteria

### Elementary (初级)
- Basic pronunciation accuracy
- Simple sentence structures
- 60-120 syllables/minute speech rate

### Intermediate (中级)  
- Clear pronunciation with good fluency
- Complex sentence patterns
- 120-180 syllables/minute speech rate

### Advanced (高级)
- Near-native pronunciation
- Natural prosody and intonation
- 150-220 syllables/minute speech rate

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│   Praat Docker  │
│                 │    │   Container     │
└─────────────────┘    └─────────────────┘
         │                       │
         │              ┌─────────────────┐
         └──────────────│  Audio Files    │
                        │  & Results      │
                        └─────────────────┘
```

## Development

### Project Structure
```
hskk-praat-scoring/
├── app/                  # FastAPI application
├── docker/              # Docker configurations  
├── praat_scripts/       # Praat analysis scripts
├── data/               # Audio files and results
├── tests/              # Unit tests
└── frontend/           # Optional web interface
```

### Adding New Features
1. Create new Praat scripts in `praat_scripts/`
2. Add service methods in `app/services/`
3. Update scoring logic in `scoring_service.py`
4. Add API endpoints in `main.py`

### Testing
```bash
# Run tests
python -m pytest tests/

# Test specific service
python -m pytest tests/test_praat_service.py
```

## Praat Scripts

- `extract_features.praat` - Core acoustic feature extraction
- `pitch_analysis.praat` - Detailed pitch analysis
- `formant_analysis.praat` - Formant tracking
- `prosody_analysis.praat` - Prosodic feature analysis

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## License

MIT License - see LICENSE file for details