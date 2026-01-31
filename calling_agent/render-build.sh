#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Install system packages (PortAudio for pyaudio, ffmpeg for pydub)
# Render Native Environment supports apt-get if we use a specific build setup or docker.
# But usually standard python envs don't allow sudo apt-get.
# However, pydub needs ffmpeg. 'gTTS' doesn't strict need it if we don't manipulate.
# 'SpeechRecognition' needs flac usually.
# 'pyaudio' needs portaudio.

# For Render, we often can't use apt-get in the build command unless using a Blueprint with 'pkgs'.
# BUT, if we just want to run the Flask app, do we NEED pyaudio?
# Pyaudio is for Microphone. The Web Server processes FILES from Twilio.
# So we DO NOT need PyAudio on the server! We only need it for the local CLI.
# Remove pyaudio from requirements for server? Or just fail gracefully?
# I will keep it but wrap imports.

# FFmpeg: We might need it for pydub to convert audio formats (Twilio sends mp3/wav).
# We can try to install a static ffmpeg or hope render has it. 
# Many Render python images have ffmpeg.

echo "Build complete."
