import joblib
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.audio_utils import load_audio
from src.features import extract_features
from src.risk_engine import calculate_risk
from src.reporting import generate_report

def run_pipeline(scenario_name, otp_success, identity_fails, intent, audio_path):
    print(f"\n>>> RUNNING SCENARIO: {scenario_name}")
    print("-" * 40)
    
    # --- 1. Load Artifacts (Mandatory Pattern) ---
    try:
        scaler = joblib.load("scaler.pkl")
        model = joblib.load("audio_classifier.pkl")
    except FileNotFoundError:
        print("Error: Artifacts not found. Please ensure scaler.pkl and audio_classifier.pkl are in the current directory.")
        return

    # --- 2. Process Audio (Mandatory Pattern) ---
    audio = load_audio(audio_path)
    features = extract_features(audio).reshape(1, -1)
    
    # VERY IMPORTANT STEP
    features_scaled = scaler.transform(features)
    
    # Prediction
    prob_ai = model.predict_proba(features_scaled)[0][1]
    label = "AI" if prob_ai > 0.5 else "Human"
    
    print(f"[DEBUG] Model Output: Prob={prob_ai:.4f}, Label={label}")
    
    # --- 3. Risk Mapping ---
    if label == "Human":
        voice_risk = "LOW"
    else:
        voice_risk = "HIGH"
        
    # --- 4. Risk Engine ---
    risk_data = calculate_risk(
        otp_success=otp_success, 
        identity_fails=identity_fails, 
        voice_risk=voice_risk, 
        intent=intent
    )
    
    # --- 5. Report Generation ---
    report = generate_report(risk_data)
    print(report)

def main():
    print("Initializing VoiceSentinel Demo...\n")
    
    # Scenario 1: Legit Refund Caller
    # - OTP Pass
    # - Identity Correct
    # - Human Voice (simulated by filename "legit.wav")
    run_pipeline(
        scenario_name="Legit Refund Caller",
        otp_success=True,
        identity_fails=0,
        intent="REFUND",
        audio_path="legit.wav"
    )
    
    # Scenario 2: Fraud Refund Caller (AI Voice)
    # - OTP Fail (Simulating high risk start) or maybe OTP Pass but Voice fail?
    # Requirement: "Fraud refund caller (AI voice) -> High risk"
    # To demonstrate risk aggregation, let's say OTP passed but voice is AI.
    # PROMPT: "Legit refund caller -> Low / Medium risk", "Fraud refund caller (AI voice) -> High risk"
    # Even if OTP passed, AI voice should trigger HIGH base risk.
    # Let's add a small identity fail to make it interesting, or keep it strict on voice.
    # "OTP status (pass / fail)" is an input.
    # Let's say the fraudster passed OTP (sim swap?) but failed voice.
    run_pipeline(
        scenario_name="Fraud Refund Caller (AI Voice)",
        otp_success=True, 
        identity_fails=0, 
        intent="REFUND", 
        audio_path="fraud_ai.wav" 
    )

if __name__ == "__main__":
    main()
