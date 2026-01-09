FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing and Docker CLI
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    && curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh get-docker.sh \
    && rm get-docker.sh \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download FunASR model during build (cached in image)
RUN python -c "from funasr import AutoModel; AutoModel(model='paraformer-zh', model_revision='v2.0.4', disable_update=True, device='cpu')" \
    && echo "FunASR model downloaded successfully"

# Copy application code
COPY app/ ./app/

# Create data directories
RUN mkdir -p data/audio_input data/audio_output data/praat_output

# Copy environment file if exists
COPY .env* ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]