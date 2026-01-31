import sys
import os
import time
import joblib
import threading
import shutil
import argparse
import wave
import contextlib

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.identity_processor import validate_identity, extract_details_from_transcript
from src.audio_utils import load_audio
from src.features import extract_features
from src.risk_engine import calculate_risk
from src.reporting import generate_report
from src.mic_utils import listen_and_transcribe
from src.tts_utils import speak, generate_wav
from src.asr_utils import transcribe_audio
from src.database import get_db, get_account_history, save_call_record, init_db, get_user_embedding, save_user_embedding
from src.history import analyze_history
from src.voice_auth import VoiceAuthenticator

# Global state
CALL_STATE = {
    "otp": None,
    "name": None,
    "dob": None,
    "intent": None,
    "audio_file": "session_accumulated.wav",
    "voice_prob": 0.0,
    "voice_risk": "LOW",
    "voice_match_score": 0.0
}

# Initialize Authenticator (Global to load model once)
authenticator = None

def clear_screen():
    print("\033[H\033[J", end="")

def ensure_dummy_audio_files():
    if not os.path.exists("legit.wav"):
        generate_wav("Hi, I want to request a refund.", "legit.wav")
    if not os.path.exists("fraud_ai.wav"):
        generate_wav("I need to swap my SIM card.", "fraud_ai.wav")
    # Reset accumulated file
    if os.path.exists("session_accumulated.wav"):
        os.remove("session_accumulated.wav")

def get_wav_duration(filename):
    if not os.path.exists(filename):
        return 0
    try:
        with contextlib.closing(wave.open(filename, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception:
        return 0

def analyze_audio_file(filepath):
    """
    Runs the AI Model on the given filepath.
    Updates CALL_STATE with risk results.
    """
    print(f"\n[AI Analysis] Processing features from {filepath}...")
    try:
        # Check filename for mock logic (hackathon constraint)
        target_path = filepath
        if "fraud" in filepath or "ai" in filepath:
             # Mock Hack: The feature extractor looks for 'fraud' in path
             pass
        else:
             pass 

        scaler = joblib.load("scaler.pkl")
        model = joblib.load("audio_classifier.pkl")
        
        audio = load_audio(target_path)
        features = extract_features(audio).reshape(1, -1)
        features_scaled = scaler.transform(features)
        
        probs = model.predict_proba(features_scaled)[0]
        prob_ai = probs[1]
        
        CALL_STATE["voice_prob"] = prob_ai
        CALL_STATE["voice_risk"] = "HIGH" if prob_ai > 0.5 else "LOW"
        print(f"[AI Analysis] Result: {prob_ai:.2%} Match to AI")
        
    except Exception as e:
        print(f"[Analysis Error] {e}")
        CALL_STATE["voice_prob"] = 0.0
        CALL_STATE["voice_risk"] = "LOW"

def verify_voice_identity(filepath, account_id):
    """
    Verifies if the voice matches the enrolled user in MongoDB.
    If new user, enrolls them.
    Updates CALL_STATE["voice_match_score"].
    """
    global authenticator
    if not authenticator:
        authenticator = VoiceAuthenticator()
        
    print(f"\n[Voice Auth] Extracting embedding for Verification...")
    embedding = authenticator.extract_embedding_from_file(filepath)
    
    if embedding is None:
        print("[Voice Auth] Failed to extract embedding. Skipping verification.")
        CALL_STATE["voice_match_score"] = 0.0
        return

    db = next(get_db())
    stored_embedding = get_user_embedding(db, account_id)
    
    if stored_embedding:
        print(f"[Voice Auth] User {account_id} found. Verifying...")
        score = authenticator.compare_embeddings(embedding, stored_embedding)
        CALL_STATE["voice_match_score"] = score
        print(f"[Voice Auth] Match Score: {score:.2%}")
    else:
        print(f"[Voice Auth] User {account_id} not found. Enrolling new voice...")
        save_user_embedding(db, account_id, embedding.tobytes())
        CALL_STATE["voice_match_score"] = 1.0 # First time always matches self
        print(f"[Voice Auth] Enrollment Complete.")


# -------------------------------------------------------------
# MODE 1: FILE PROCESSING (No User Interaction)
# -------------------------------------------------------------
def process_file_mode(input_file):
    print(f"[System] Mode: Offline Analysis of {input_file}")
    
    # 1. Transcribe Full File
    print("[System] Transcribing audio...")
    transcript = transcribe_audio(input_file, "UNKNOWN") # Using Whisper
    print(f"[Transcript]: \"{transcript}\"")
    
    # 2. Extract Details (NLP/Regex)
    details = extract_details_from_transcript(transcript)
    CALL_STATE.update(details)
    print(f"[Extracted]: OTP={CALL_STATE['otp']}, Name={CALL_STATE['name']}, Intent={CALL_STATE['intent']}")
    
    # 3. Analyze Audio Risk (AI Spoofing)
    analyze_audio_file(input_file)
    
    # 4. Generate Report setup
    otp_success, identity_fails, _ = validate_identity(CALL_STATE["otp"], CALL_STATE["name"], CALL_STATE["dob"])
    
    # --- HISTORY & VOICE AUTH CHECK ---
    init_db()
    account_id = "12345" # Default for demo
    print(f"[System] analyzing history for Account: {account_id}...")
    
    db = next(get_db())
    history = get_account_history(db, account_id)
    mod, explanations = analyze_history(history)
    print(f"[History] Modifier: {mod}, Reasons: {explanations}")
    
    # --- VOICE AUTH ---
    verify_voice_identity(input_file, account_id)
    
    # 5. Risk Calculation
    otp_success, identity_fails, _ = validate_identity(details["otp"], details["name"], details["dob"])
    
    risk_data = calculate_risk(
        otp_success=otp_success,
        identity_fails=identity_fails,
        voice_risk=CALL_STATE.get("voice_risk", "LOW"),
        intent=details["intent"],
        voice_prob=CALL_STATE.get("voice_prob", 0.0),
        history_modifier=mod
    )
    risk_data["history_explanations"] = explanations
    risk_data["voice_match_score"] = CALL_STATE["voice_match_score"]
    
    # 6. Save Record
    save_call_record(db, {
        "account_id": account_id,
        "otp_success": otp_success,
        "identity_fails": identity_fails,
        "voice_risk_level": CALL_STATE.get("voice_risk", "LOW"),
        "intent": details["intent"],
        "final_risk_level": risk_data["final_risk"],
        "risk_percentage": risk_data["risk_percentage"],
        "agent_decision": "PENDING"
    })
    
    # 7. Generate Report
    report = generate_report(risk_data)
    print(report)
    
    final_risk = risk_data["final_risk"]
    risk_pct = risk_data["risk_percentage"]
    final_score = risk_data["signals"]["voice_prob"] * 100
    
    speak_msg = f"Analysis Complete. Total Risk is {risk_pct:.0f} percent ({final_risk}). Voice match to AI is {final_score:.0f} percent."
    speak(speak_msg)

# -------------------------------------------------------------
# MODE 2: INTERACTIVE LIVE ACCUMULATION
# -------------------------------------------------------------
def periodic_risk_monitor():
    """
    Background thread that checks if accumulated audio is long enough > 10s.
    If so, it runs analysis (once).
    """
    analyzed = False
    while True:
        if CALL_STATE.get("finished", False):
            break
            
        duration = get_wav_duration(CALL_STATE["audio_file"])
        if duration > 8.0 and not analyzed:
            # Trigger Analysis
            print(f"\n[System Monitor] Accumulated {duration:.1f}s audio. Running Analysis...")
            analyze_audio_file(CALL_STATE["audio_file"])
            analyzed = True
            
        time.sleep(1)

def live_interactive_mode():
    print("[System] Mode: Live Interactive Session")
    speak("Voice Sentinel Secure Line. Please answer the security questions.")
    
    # --- HISTORY & DB ---
    init_db()
    
    # Ask for Account ID
    speak("Please say your 5 digit Account Number.")
    acc_text = listen_and_transcribe("Please say your account number.")
    
    import re
    digits = re.findall(r"\d+", acc_text)
    account_id = "".join(digits)
    if not account_id: 
        account_id = "UNKNOWN"
        print(f"[System] Could not hear account number. Using {account_id}")
    else:
        print(f"[System] Account ID: {account_id}")
    
    db = next(get_db())
    history = get_account_history(db, account_id)
    mod, explanations = analyze_history(history)
    print(f"[History] Modifier: {mod}, Reasons: {explanations}")
    
    # Start Monitor Thread
    monitor_thread = threading.Thread(target=periodic_risk_monitor)
    monitor_thread.start()
    
    # Q&A Loop
    session_file = CALL_STATE["audio_file"]
    
    # 1. OTP
    resp_otp = listen_and_transcribe("Please provided your OTP for verification.", save_to_file=session_file)
    CALL_STATE["otp"] = resp_otp.strip() if resp_otp else "0000"
    
    # 2. Name
    resp_name = listen_and_transcribe("Please tell me your full name.", save_to_file=session_file)
    CALL_STATE["name"] = resp_name.strip() if resp_name else "Guest"
    
    # 3. DOB
    resp_dob = listen_and_transcribe("What is your date of birth?", save_to_file=session_file)
    CALL_STATE["dob"] = resp_dob.strip() if resp_dob else "01 Jan 2000"
    
    # 4. Intent
    resp_intent = listen_and_transcribe("How can I help you today?", save_to_file=session_file)
    
    # Process Intent
    intent_map = {"refund": "REFUND", "sim": "SIM_SWAP", "recovery": "ACCOUNT_RECOVERY"}
    CALL_STATE["intent"] = "REFUND"
    if resp_intent:
        for key, val in intent_map.items():
            if key in resp_intent.lower(): 
                CALL_STATE["intent"] = val
                break
                
    # Stop Monitor
    CALL_STATE["finished"] = True
    monitor_thread.join()
    
    # Final Analysis if not triggered yet (AI Spoofing)
    if CALL_STATE["voice_risk"] == "LOW" and CALL_STATE["voice_prob"] == 0.0:
        if get_wav_duration(session_file) > 0.5:
             analyze_audio_file(session_file)
             
    # --- VOICE AUTH VERIFICATION ---
    if get_wav_duration(session_file) > 0.5 and account_id != "UNKNOWN":
        verify_voice_identity(session_file, account_id)
    
    # Report
    otp_success, identity_fails, _ = validate_identity(CALL_STATE["otp"], CALL_STATE["name"], CALL_STATE["dob"])
    
    risk_data = calculate_risk(
        otp_success=otp_success,
        identity_fails=identity_fails,
        voice_risk=CALL_STATE["voice_risk"],
        intent=CALL_STATE["intent"],
        voice_prob=CALL_STATE["voice_prob"],
        history_modifier=mod
    )
    risk_data["history_explanations"] = explanations
    risk_data["voice_match_score"] = CALL_STATE["voice_match_score"]
    
    # SAVE History
    save_call_record(db, {
        "account_id": account_id,
        "otp_success": otp_success,
        "identity_fails": identity_fails,
        "voice_risk_level": CALL_STATE["voice_risk"],
        "intent": CALL_STATE["intent"],
        "final_risk_level": risk_data["final_risk"],
        "risk_percentage": risk_data["risk_percentage"],
        "agent_decision": "PENDING"
    })
    
    report = generate_report(risk_data)
    print(report)
    
    final_risk = risk_data["final_risk"]
    risk_pct = risk_data["risk_percentage"]
    final_score = risk_data["signals"]["voice_prob"] * 100
    
    speak_msg = f"Analysis Complete. Total Risk is {risk_pct:.0f} percent ({final_risk}). Voice match to AI is {final_score:.0f} percent."
    speak(speak_msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-input", type=str, help="Skip Interaction. Process this audio file directly.")
    parser.add_argument("--fraud", action="store_true", help="Hint for simulation (Mock Features logic)")
    args = parser.parse_args()
    
    clear_screen()
    ensure_dummy_audio_files()
    
    print("========================================")
    print("   VOICESENTINEL RISK MONITORING SYSTEM ")
    print("========================================")
    
    if args.audio_input:
        if not os.path.exists(args.audio_input):
            print("File not found.")
            return
        
        process_file_mode(args.audio_input)
        
    else:
        live_interactive_mode()

if __name__ == "__main__":
    main()
