import os
import sys
import requests
import joblib
import numpy as np
import uuid
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.identity_processor import validate_identity, extract_details_from_transcript
from src.audio_utils import load_audio
from src.features import extract_features
# from src.risk_engine import calculate_risk # We will use the logic directly or import
from src.risk_engine import calculate_risk
from src.asr_utils import transcribe_audio

app = Flask(__name__)

# Load Models (Global load for performance)
SCALER = None
MODEL = None

def load_models():
    global SCALER, MODEL
    try:
        if os.path.exists("scaler.pkl"):
            SCALER = joblib.load("scaler.pkl")
        if os.path.exists("audio_classifier.pkl"):
            MODEL = joblib.load("audio_classifier.pkl")
        print("[System] Models loaded successfully.")
    except Exception as e:
        print(f"[Error] loading models: {e}")

load_models()

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Incoming Call Handler"""
    resp = VoiceResponse()
    resp.say("Welcome to Voice Sentinel. Please state your name, date of birth, and the reason for your call, then press hash.", voice='alice')
    # Record the user's response
    # maxLength=10 seconds (enough for short answers)
    resp.record(action='/process_input', method='POST', maxLength=10, finishOnKey='#')
    resp.say("I did not receive a recording. Goodbye.")
    return (str(resp), 200, {'Content-Type': 'text/xml'})

@app.route("/process_input", methods=['GET', 'POST'])
def process_input():
    """Process the recorded audio from Twilio"""
    recording_url = request.values.get('RecordingUrl', None)
    
    if not recording_url:
        resp = VoiceResponse()
        resp.say("Sorry, I could not find the recording.", voice='alice')
        return (str(resp), 200, {'Content-Type': 'text/xml'})
    
    # 1. Download Audio
    print(f"[System] Downloading audio from {recording_url}")
    filename = f"twilio_{uuid.uuid4()}.wav"
    try:
        # Twilio recordings are usually .wav if extension specified or .mp3
        # append .wav to url to ask for wav
        download_url = f"{recording_url}.wav"
        doc = requests.get(download_url)
        with open(filename, 'wb') as f:
            f.write(doc.content)
            
        # 2. Transcribe
        print(f"[System] Transcribing {filename}...")
        transcript = transcribe_audio(filename, "UNKNOWN")
        print(f"[Transcript] {transcript}")
        
        # 3. Extract Details
        details = extract_details_from_transcript(transcript)
        
        # 4. Analyze Voice Risk
        prob_ai = 0.0
        voice_risk = "LOW"
        
        if MODEL and SCALER:
            try:
                # Mock propagation for filename (if needed? Twilio filenames are UUIDs)
                # We can't use filename-based mock logic here unless we force it.
                # So we rely on real feature extraction logic (which uses 'legit.wav' mock if file read fails, etc, 
                # or calculates real features if pydub/librosa works).
                # NOTE: src/features.py uses filename checks!
                # "if 'fraud' in path or 'ai' in path..."
                # Twilio paths won't have that.
                # We need a fallback or real model usage.
                # Since this is a demo, we might want to check if the transcript says "I am a robot" to force it?
                # Or just assume "Low Risk" for random calls unless we specificially demo with a 'fraud' file inject.
                
                # Let's use the extractor.
                audio = load_audio(filename)
                features = extract_features(audio).reshape(1, -1)
                features_scaled = SCALER.transform(features)
                probs = MODEL.predict_proba(features_scaled)[0]
                prob_ai = probs[1]
                voice_risk = "HIGH" if prob_ai > 0.5 else "LOW"
            except Exception as e:
                print(f"[Feature Error] {e}")
        
        # 5. Risk Calculation
        # Validate Identity (Mock Truth: 15 July 2005)
        otp_success, identity_fails, _ = validate_identity(details["otp"], details["name"], details["dob"])
        
        risk_data = calculate_risk(
            otp_success=otp_success,
            identity_fails=identity_fails,
            voice_risk=voice_risk,
            intent=details["intent"],
            voice_prob=prob_ai
        )
        
        risk_pct = risk_data["risk_percentage"]
        final_risk = risk_data["final_risk"]
        
        # 6. Response
        resp = VoiceResponse()
        msg = f"Thank you. We analyzed your call. Your Identity Check status is: {identity_fails} discrepancies. " \
              f"Your Voice AI Probability is {prob_ai*100:.0f} percent. " \
              f"Total Risk Score is {risk_pct:.0f} percent, which is {final_risk}."
        
        print(f"[Report] {msg}")
        resp.say(msg, voice='alice')
        
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
            
        return (str(resp), 200, {'Content-Type': 'text/xml'})

    except Exception as e:
        print(f"[Processing Error] {e}")
        resp = VoiceResponse()
        resp.say("An error occurred processing your request.", voice='alice')
        return (str(resp), 200, {'Content-Type': 'text/xml'})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
