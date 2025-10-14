# 🚀 HSKK Praat Scoring - Frontend Setup Instructions

## 📁 Project Structure

```
hskk-praat-scoring/
├── app/                          # Backend FastAPI application
│   ├── __init__.py
│   ├── config.py
│   ├── main.py                   # ✨ UPDATED - Added templates support
│   ├── models/
│   │   ├── __init__.py
│   │   └── hskk_models.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_service.py
│   │   ├── praat_service.py
│   │   └── scoring_service.py
│   └── utils/
│       └── __init__.py
│
├── frontend/                     # 🆕 NEW Frontend directory
│   ├── static/                   # Static assets
│   │   ├── css/
│   │   │   └── features.css     # 🆕 Styles for features tester
│   │   ├── js/
│   │   │   └── features.js      # 🆕 JavaScript functionality
│   │   └── images/
│   │       └── logo.png         # (Optional)
│   ├── templates/                # HTML templates
│   │   ├── index.html           # 🆕 Main landing page
│   │   └── features_tester.html # 🆕 Features test page
│   └── README.md                 # 🆕 Frontend documentation
│
├── data/                         # Data directories
│   ├── audio_input/
│   ├── audio_output/
│   ├── praat_output/
│   └── models/
│
├── docker/                       # Docker configurations
│   ├── Dockerfile
│   └── Dockerfile.praat
│
├── praat_scripts/               # Praat analysis scripts
│   └── extract_features.praat
│
├── tests/                       # Unit tests
│   └── __init__.py
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt             # ✨ UPDATED - Added jinja2, aiofiles
├── setup_frontend.sh            # 🆕 Setup script
└── README.md
```

## 🛠️ Setup Steps

### Step 1: Create Frontend Directory Structure

```bash
# Run from project root
chmod +x setup_frontend.sh
./setup_frontend.sh
```

Or manually:
```bash
mkdir -p frontend/static/css
mkdir -p frontend/static/js
mkdir -p frontend/static/images
mkdir -p frontend/templates
```

### Step 2: Copy Frontend Files

#### 2.1 Copy CSS File
Create `frontend/static/css/features.css` and paste the CSS content from the artifact.

#### 2.2 Copy JavaScript File
Create `frontend/static/js/features.js` and paste the JavaScript content from the artifact.

#### 2.3 Copy HTML Templates
Create the following files:
- `frontend/templates/index.html` - Main landing page
- `frontend/templates/features_tester.html` - Features testing interface

### Step 3: Update Backend Files

#### 3.1 Update `app/main.py`
Replace the existing `app/main.py` with the updated version that includes:
- StaticFiles mounting
- Jinja2Templates configuration
- Template routes for `/` and `/features-tester`

#### 3.2 Update `requirements.txt`
Add the following dependencies:
```
jinja2==3.1.2
aiofiles==23.2.1
```

### Step 4: Install Dependencies

```bash
# If using Docker
docker-compose down
docker-compose build
docker-compose up -d

# If using local Python
pip install -r requirements.txt
```

### Step 5: Verify Setup

1. **Check directory structure:**
```bash
ls -la frontend/
ls -la frontend/static/
ls -la frontend/templates/
```

2. **Start the server:**
```bash
# Using Docker
docker-compose up

# Or locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. **Test the pages:**
- Main page: http://localhost:8000/
- Features tester: http://localhost:8000/features-tester
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 🌐 Available Pages

### 1. Main Landing Page (`/`)
- System overview
- Feature highlights
- Quick start guide
- Links to all features

**Screenshot elements:**
- Welcome header
- Key features grid
- HSKK scoring breakdown
- Navigation links

### 2. Features Tester (`/features-tester`)
- Drag & drop audio upload
- HSKK level selection
- Real-time analysis
- 43 acoustic features display
- Score breakdown
- Pronunciation feedback

**Features:**
- ✅ Upload WAV, MP3, M4A, FLAC
- ✅ Visual loading indicator
- ✅ Organized feature categories
- ✅ Responsive design
- ✅ Error handling

## 🎨 Features Tester Components

### Upload Section
- Drag & drop zone
- File browser
- Level selector (Elementary/Intermediate/Advanced)
- Analyze button

### Results Display
- Overall HSKK score card
- Score breakdown (Pronunciation, Fluency, Grammar, Vocabulary)
- Audio information panel

### 43 Acoustic Features (8 Categories)

1. **⏱️ Basic Information (1)**
   - Duration

2. **🎵 Pitch Features (8)**
   - Mean, Std, Range, Min, Max, Median, Quantiles

3. **📊 Formants F1-F4 (8)**
   - Mean and Std for each formant

4. **🔊 Intensity (4)**
   - Mean, Std, Min, Max

5. **🌊 Spectral Features (4)**
   - Centroid, Std, Skewness, Kurtosis

6. **🎙️ Voice Quality (10)**
   - HNR, Jitter (3 types), Shimmer (4 types)

7. **⏰ Speech Timing (7)**
   - Rates, durations, pauses

8. **➕ Additional Measures (3)**
   - COG, Slope, Spread

## 🔧 Troubleshooting

### Issue: Templates not found
**Solution:**
```python
# Verify paths in app/main.py
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
print(f"Templates directory: {TEMPLATES_DIR}")
print(f"Templates exist: {TEMPLATES_DIR.exists()}")
```

### Issue: Static files not loading
**Solution:**
```python
# Check static files mounting
STATIC_DIR = FRONTEND_DIR / "static"
print(f"Static directory: {STATIC_DIR}")
print(f"Static files: {list(STATIC_DIR.glob('**/*'))}")
```

### Issue: CORS errors
**Solution:** Already configured in `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: 404 on /features-tester
**Solution:** Ensure the route is registered:
```python
@app.get("/features-tester", response_class=HTMLResponse)
async def features_tester(request: Request):
    return templates.TemplateResponse("features_tester.html", {"request": request})
```

## 📊 Testing the Features

### 1. Upload Test Audio
```bash
# Download sample audio or use your own
curl -X POST "http://localhost:8000/assess" \
  -F "audio_file=@test.wav" \
  -F "target_level=intermediate"
```

### 2. Test via UI
1. Go to http://localhost:8000/features-tester
2. Drag & drop or select an audio file
3. Choose HSKK level
4. Click "Analyze Audio Features"
5. View results with 43 features

### 3. Expected Output
- Overall score (0-100)
- Level achieved (Elementary/Intermediate/Advanced)
- Individual scores (Pronunciation, Fluency, Grammar, Vocabulary)
- 43 acoustic features organized in 8 categories
- Pronunciation feedback in Chinese and English

## 🎯 Next Steps

1. **Add authentication** (if needed)
2. **Implement file history** tracking
3. **Add export functionality** (PDF/JSON)
4. **Create comparison view** for multiple recordings
5. **Add visualization charts** using Chart.js
6. **Implement batch processing**

## 📝 Notes

- The frontend is pure HTML/CSS/JS - no build process required
- All API calls go to the same FastAPI server
- Static files are served by FastAPI
- Templates use Jinja2 for server-side rendering
- No localStorage/sessionStorage used (not supported in artifacts)

## 🤝 Contributing

When adding new features:
1. Update HTML templates in `frontend/templates/`
2. Add styles to `frontend/static/css/`
3. Add JavaScript to `frontend/static/js/`
4. Update routes in `app/main.py`
5. Test all endpoints

## 📚 Resources

- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)
- [Praat Documentation](http://www.fon.hum.uva.nl/praat/)
- [HSKK Official](http://www.chinesetest.cn/)

---

**Happy Testing! 🎉**