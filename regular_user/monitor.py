import os
import sys
import time
import argparse
import numpy as np
import joblib
import soundfile as sf
import soundcard as sc
from datetime import datetime
from plyer import notification

# Add src to path
sys.path.append(os.getcwd())
# Also append src if running from root
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.audio_utils import load_audio
from src.features import extract_features

# Constants
MODEL_PATH = "audio_classifier.pkl"
SCALER_PATH = "scaler.pkl"
LOG_DIR = "regular_user/logs"
DURATION = 10.0 # Seconds
SAMPLE_RATE = 16000

def notify(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='VoiceSentinel',
            timeout=10
        )
    except Exception as e:
        print(f"[Fallback Notification] {title}: {message}")
        # Linux fallback if plyer fails (e.g. no notification daemon)
        if sys.platform.startswith("linux"):
            os.system(f'notify-send "{title}" "{message}"')

def record_system_audio(duration=10.0, samplerate=16000):
    """
    Records audio from the default speaker (loopback).
    """
    print(f"[System] Recording {duration}s of System Audio...")
    
    # Get Default Speaker
    speaker = sc.default_speaker()
    print(f"[Device] capturing from: {speaker.name}")
    
    # Record
    # soundcard returns numpy array (frames, channels)
    data = speaker.record(samplerate=samplerate, numframes=int(duration*samplerate))
    
    # Convert to mono if stereo
    if data.ndim > 1 and data.shape[1] > 1:
        data = np.mean(data, axis=1)
        
    # Save to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(LOG_DIR, f"capture_{timestamp}.wav")
    sf.write(filename, data, samplerate)
    print(f"[Saved] {filename}")
    return filename

def analyze_file(filepath):
    print(f"[Analysis] Processing {filepath}...")
    try:
        if not os.path.exists(MODEL_PATH):
            print("[Error] Model not found. Run training first.")
            return None, 0.0
            
        scaler = joblib.load(SCALER_PATH)
        model = joblib.load(MODEL_PATH)
        
        # Load audio using librosa/pydub logic in src/audio_utils
        audio = load_audio(filepath)
        features = extract_features(audio).reshape(1, -1)
        features_scaled = scaler.transform(features)
        
        probs = model.predict_proba(features_scaled)[0]
        prob_ai = probs[1]
        
        return "AI" if prob_ai > 0.5 else "HUMAN", prob_ai
        
    except Exception as e:
        print(f"[Error] Analysis Failed: {e}")
        return "ERROR", 0.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Analyze specific file")
    parser.add_argument("--monitor", action="store_true", help="Start monitoring immediately")
    args = parser.parse_args()

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    print("========================================")
    print("   VOICESENTINEL - PERSONAL MONITOR     ")
    print("========================================")
    
    target_file = None
    
    if args.file:
        if os.path.exists(args.file):
            target_file = args.file
        else:
            print("File not found.")
            return
    elif args.monitor:
        print("Starting Recording in 3 seconds... (Play your audio now)")
        time.sleep(3)
        target_file = record_system_audio(DURATION, SAMPLE_RATE)
    else:
        print("1. Start Monitoring (Record 10s)")
        print("2. Analyze Existing File")
        
        choice = input("Select Option (1/2): ").strip()
        
        if choice == "1":
            print("Starting Recording in 3 seconds... (Play your audio now)")
            time.sleep(3)
            target_file = record_system_audio(DURATION, SAMPLE_RATE)
            
        elif choice == "2":
            fpath = input("Enter file path: ").strip()
            if os.path.exists(fpath):
                target_file = fpath
            else:
                print("File not found.")
                return
            
    if target_file:
        label, prob = analyze_file(target_file)
        print(f"\n[RESULT] {label} Voice detected ({prob:.1%} confidence)")
        
        if label == "AI":
            notify("⚠️ AI Voice Detected!", f"Warning: The caller is likely AI ({prob:.0%}). Be careful.")
        else:
            notify("✅ Human Voice", f"The caller seems to be Human ({prob:.0%}).")
            
        print("[Done] Check notification.")

if __name__ == "__main__":
    main()
