import requests
import os
import sys
import time

# Default URL
SERVER_URL = "http://localhost:5001"

def gen_test_wav(filename):
    """
    Generate a simple valid WAV file using gTTS if possible, 
    or write a minimal valid header if gTTS fails.
    """
    try:
        from gtts import gTTS
        from pydub import AudioSegment
        import tempfile
        
        tts = gTTS("Hello this is a test.", lang='en')
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            tts.save(fp.name)
            mp3_path = fp.name
            
        sound = AudioSegment.from_mp3(mp3_path)
        sound.export(filename, format="wav")
        os.remove(mp3_path)
        print(f"Generated valid test audio: {filename}")
    except Exception as e:
        print(f"Failed to generate real wav: {e}")
        # Write a minimal valid 1-second silent WAV if strict generation fails
        # This byte sequence is a valid 44100Hz mono 16-bit PCM WAV (header only mostly)
        # Actually simplest is to write nothing or handle failure. 
        # But server uses 'wave' module which requires valid header.
        print("Ensure 'calling_agent/legit.wav' is a valid WAV file manually.")

def run_test(target_url):
    print(f"Testing against: {target_url}")
    
    # 1. Health Check
    print("Checking Health...")
    try:
        resp = requests.get(f"{target_url}/health", timeout=60)
        print(f"Health: {resp.status_code} - {resp.text}")
        if resp.status_code != 200:
            print("Health check failed!")
            return
    except Exception as e:
        print(f"Health check error: {e}")
        return

    # 2. Start Call
    print("\n[Test] Starting Call...")
    payload = {"phone": "+919876543210", "country": "IN", "account_id": "CLOUD_TEST_USER"}
    try:
        resp = requests.post(f"{target_url}/start-call", json=payload, timeout=10)
        print("Start Response:", resp.json())
        if resp.status_code != 200:
            print("Failed to start call")
            return
        session_id = resp.json()['session_id']
    except Exception as e:
        print(f"Start call error: {e}")
        return
        
    # 3. Submit Response (Loop)
    # Ensure audio exists
    audio_file = "calling_agent/test_audio.wav"
    if not os.path.exists(audio_file):
        gen_test_wav(audio_file)
    
    if not os.path.exists(audio_file):
        print("No audio file to send.")
        return

    step = 0
    while step < 4:
        print(f"\n[Test] Sending Answer for Step {step}...")
        try:
            with open(audio_file, "rb") as f:
                files = {'file': f}
                data = {'session_id': session_id}
                resp = requests.post(f"{target_url}/submit-response", files=files, data=data, timeout=30)
                
            json_resp = resp.json()
            print(f"Step {step} Response: {json_resp}")
            
            if json_resp.get("status") == "completed":
                print("IVR Flow Completed!")
                report = json_resp.get("report")
                print("Final Report Risk:", report.get("final_risk"))
                print("Full Report:", report)
                break
            step += 1
            time.sleep(1)
        except Exception as e:
            print(f"Step {step} error: {e}")
            break

if __name__ == "__main__":
    url = SERVER_URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    run_test(url)
