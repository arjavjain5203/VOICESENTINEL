FROM python:3.12-slim

# Install system dependencies required for audio processing and build tools
# ffmpeg: Audio conversion
# libsndfile1: For soundfile/librosa
# portaudio19-dev: For PyAudio
# build-essential: For compiling C extensions (webrtcvad, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the Flask port
EXPOSE 5001

# Set environment variables if needed
# ENV FLASK_ENV=production

# Run the application
CMD ["python", "server.py"]
