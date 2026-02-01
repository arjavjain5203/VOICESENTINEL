
import requests
import os
import sys
import time
import json

SERVER_URL = "http://localhost:5001"
TEST_AUDIO_FILE = "test_latency.wav"

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
from tts_utils import generate_wav

def test_latency():
    print("[Test] Generating Audio...")
    generate_wav("My name is John Doe and I am delayed.", TEST_AUDIO_FILE)
    
    print("[Test] Starting Call Session...")
    res = requests.post(f"{SERVER_URL}/start-call", json={"phone": "9999999999", "country": "IN"})
    if res.status_code != 200:
        print(f"Failed to start call: {res.text}")
        return
        
    session_id = res.json()["session_id"]
    print(f"[Test] Session ID: {session_id}")
    
    # Simulate Hesitation: Wait 15 seconds 
    # (Prompt is ~8.35s, so 15s wait = ~6.65s hesitation)
    delay = 15
    print(f"[Test] Simulate Hesitation: Waiting {delay}s...")
    time.sleep(delay)
    
    print("[Test] Sending Audio Chunk...")
    with open(TEST_AUDIO_FILE, 'rb') as f:
        res = requests.post(
            f"{SERVER_URL}/submit-response",
            data={"session_id": session_id},
            files={"file": f} 
        )
        
    print(f"[Test] Response Code: {res.status_code}")
    print(res.text)
    
    # Cleanup
    if os.path.exists(TEST_AUDIO_FILE):
        os.remove(TEST_AUDIO_FILE)

if __name__ == "__main__":
    test_latency()
