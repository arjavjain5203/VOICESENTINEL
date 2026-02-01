
import requests
import os
import sys
import time
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
from tts_utils import generate_wav

SERVER_URL = "http://localhost:5001"
TEST_AUDIO_FILE = "test_ai_audio.wav"

def verify_ai_fraud_detection():
    print("[Test] Generating AI Audio Sample...")
    # Generate a phrase that includes OTP and Name
    text = "The OTP is 1234. My name is Robot."
    generate_wav(text, TEST_AUDIO_FILE)
    
    if not os.path.exists(TEST_AUDIO_FILE):
        print("❌ Failed to generate test audio.")
        return

    # 1. Start Call
    try:
        print("[Test] Starting Call Session...")
        start_payload = {
            "phone": "9999999999", # Test Number
            "account_id": "test_ai_user"
        }
        resp = requests.post(f"{SERVER_URL}/start-call", json=start_payload)
        resp.raise_for_status()
        data = resp.json()
        session_id = data.get('session_id')
        print(f"[Test] Session ID: {session_id}")
        
    except Exception as e:
        print(f"❌ Failed to start call: {e}")
        return

    # 2. Submit AI Audio
    print("[Test] Submitting AI Audio Chunk...")
    try:
        with open(TEST_AUDIO_FILE, 'rb') as f:
            files = {'file': f}
            data = {'session_id': session_id}
            # We assume the first response might ask for OTP/Name.
            # We just send the audio. In the real flow, we might need multiple steps, 
            # but the server analyzes chunks in background.
            # We need to loop until finished or explicitly check the report.
            
            # The server flow usually has 3-4 steps. 
            # Let's send the same file multiple times to simulate a conversation 
            # and ensure we get a final report.
            
            # Step 1 Response
            requests.post(f"{SERVER_URL}/submit-response", files=files, data=data)
            time.sleep(1) # Wait for processing
            
            # Reset file pointer or re-open
            f.seek(0)
            
            # Step 2
            resp = requests.post(f"{SERVER_URL}/submit-response", files={'file': f}, data=data)
            
            # The server usually returns the report only at the END of the flow.
            # If we want the report, we might need to go through all steps.
            # Let's check the response next_step.
            
            # Simplified: Just grab the session status from dashboard API or force end?
            # Or just persist until "completed".
            
            while resp.json().get('status') == 'continued':
                print(f"[Test] Next Step: {resp.json().get('next_step')}")
                f.seek(0)
                resp = requests.post(f"{SERVER_URL}/submit-response", files={'file': f}, data=data)
                time.sleep(0.5)
            
            result = resp.json()
            report = result.get('report', {})
            
            print("\n" + "="*30)
            print("TEST REPORT")
            print("="*30)
            print(json.dumps(report, indent=2))
            
            # Validation
            voice_prob = report.get('voice_prob', 0.0)
            is_high_risk = voice_prob > 0.5
            
            print("-" * 30)
            if is_high_risk:
                print(f"✅ SUCCESS: System detected AI Audio (Prob: {voice_prob:.2f})")
            else:
                print(f"❌ FAILURE: System thought this was Human (Prob: {voice_prob:.2f})")
                
    except Exception as e:
        print(f"❌ Error during submission: {e}")
    finally:
        if os.path.exists(TEST_AUDIO_FILE):
            os.remove(TEST_AUDIO_FILE)

if __name__ == "__main__":
    # Ensure server is reachable
    try:
        requests.get(f"{SERVER_URL}/health")
    except:
        print("❌ Server is not running. Please run server.py first.")
        sys.exit(1)
        
    verify_ai_fraud_detection()
