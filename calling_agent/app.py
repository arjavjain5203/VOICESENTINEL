import os
import sys
import requests
import numpy as np
import uuid
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.identity_processor import validate_identity, extract_details_from_transcript
from src.audio_utils import load_audio
# from src.risk_engine import calculate_risk # We will use the logic directly or import
from src.risk_engine import calculate_risk
from src.asr_utils import transcribe_audio

app = Flask(__name__)

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Incoming Call Handler"""
    resp = VoiceResponse()
    
    # 1. Ask for Account Number first
    gather = resp.gather(numDigits=5, action='/handle_account', method='POST')
    gather.say("Welcome to Voice Sentinel. Please enter your 5 digit account number.", voice='alice')
    resp.say("We did not receive your input. Goodbye.")
    
    return (str(resp), 200, {'Content-Type': 'text/xml'})

@app.route("/handle_account", methods=['POST'])
def handle_account():
    """Handle Account Number Input"""
    account_id = request.values.get('Digits', None)
    
    resp = VoiceResponse()
    resp.say("Thank you. Please state your name, date of birth, and the reason for your call, then press hash.", voice='alice')
    # Use URL query param to pass account_id to the recording action? 
    # Or cleaner: session/cookies. Flask sessions work with Twilio if cookies enabled.
    # Alternatively, append key to action URL.
    resp.record(action=f'/process_input?account_id={account_id}', method='POST', maxLength=10, finishOnKey='#')
    return (str(resp), 200, {'Content-Type': 'text/xml'})

@app.route("/process_input", methods=['GET', 'POST'])
def process_input():
    """Process the recorded audio"""
    recording_url = request.values.get('RecordingUrl', None)
    account_id = request.args.get('account_id', 'UNKNOWN')
    
    # Imports
    from src.database import get_db, get_account_history, save_call_record, init_db
    from src.history import analyze_history
    init_db()
    
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
        
        # 4. History Analysis
        db = next(get_db())
        history = get_account_history(db, account_id)
        mod, explanations = analyze_history(history)
        print(f"[History] Account: {account_id}, Modifier: {mod}, Reasons: {explanations}")
        
        # 5. Analyze Voice Risk
        prob_ai = 0.0
        voice_risk = "LOW"
        
        try:
            # New AI Detection Model (Transformers)
            from src.ai_detector import detect_ai_audio
            prob_ai = detect_ai_audio(filename)
            voice_risk = "HIGH" if prob_ai > 0.5 else "LOW"
            print(f"[AI Check] Probability: {prob_ai:.4f}, Risk: {voice_risk}")
            
        except Exception as e:
            print(f"[AI Detection Error] {e}")
        
        # 6. Risk Calculation
        otp_success, identity_fails, _ = validate_identity(details["otp"], details["name"], details["dob"])
        
        risk_data = calculate_risk(
            otp_success=otp_success,
            identity_fails=identity_fails,
            voice_risk=voice_risk,
            intent=details["intent"],
            voice_prob=prob_ai,
            history_modifier=mod
        )
        
        risk_pct = risk_data["risk_percentage"]
        final_risk = risk_data["final_risk"]
        
        # 7. Save Record
        save_call_record(db, {
            "account_id": account_id,
            "otp_success": otp_success,
            "identity_fails": identity_fails,
            "voice_risk_level": voice_risk,
            "intent": details["intent"],
            "final_risk_level": final_risk,
            "risk_percentage": risk_pct,
            "agent_decision": "PENDING"
        })

        
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
