import requests
import json
import time
import os
import sys
import threading

# Audio Dependencies (Local Client Only)
try:
    import pyaudio
    import wave
    # from pydub import AudioSegment
    # from pydub.playback import play
    # Pydub playback can be tricky cross-platform without pyaudio installed correctly?
    # actually pydub uses simpleaudio or pyaudio.
    # Let's use a simple playback function associated with OS or pydub if acts well.
    # import simpleaudio as sa # Disabled due to Segfault on Linux
    pass
except ImportError as e:
    # print(f"❌ Missing Audio Dependencies: {e}")
    pass

SERVER_URL = "http://localhost:5001" # Default fallback

def get_server_url():
    """
    Asks user for the Server IP to connect over Wi-Fi.
    """
    print("\n[Setup] Connect to Agent Server")
    print("1. Cloud (https://voicesentinel-2.onrender.com)")
    print("2. Localhost (http://localhost:5001)")
    print("3. Custom IP / Wi-Fi (e.g., http://192.168.1.5:5001)")
    
    choice = input("Enter Choice (1/2/3): ").strip()
    
    if choice == "1":
        return "https://voicesentinel-2.onrender.com"
    elif choice == "2":
        return "http://localhost:5001"
    else:
        ip = input("Enter Server IP (e.g. 192.168.1.x): ").strip()
        if not ip.startswith("http"):
            ip = f"http://{ip}:5001"
        return ip

def play_audio_from_url(url):
    """
    Fetches audio from URL and plays it locally.
    """
    full_url = f"{SERVER_URL}{url}" if url.startswith("/") else url
    print(f"[Client] Playing: {full_url}")
    
    try:
        r = requests.get(full_url)
        with open("temp_playback.wav", "wb") as f:
            f.write(r.content)
            
        # Play using aplay (Linux Safe)
        import subprocess
        subprocess.run(["aplay", "-q", "temp_playback.wav"], check=False)
        
    except Exception as e:
        print(f"[Playback Error] {e}")

def record_audio(filename, duration=5):
    """
    Records audio from the microphone for `duration` seconds.
    """
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    
    p = pyaudio.PyAudio()
    
    print(f"\n[Client] Recording for {duration} seconds... GO!")
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    frames = []
    
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        
    print("[Client] Recording Finished.")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def main():
    global SESSION_ID
    
    print("=== Voice Sentinel User Client ===")
    
    # Combined Input
    raw_input = input("Enter Phone (Format: +Code Number, e.g. +91 9876543210): ").strip()
    
    # Parsing Logic
    if " " in raw_input:
        parts = raw_input.split(" ", 1)
        country = parts[0].replace("+", "").strip() or "IN"
        phone = parts[1].replace(" ", "").strip()
        # Ensure country code format for server if needed, e.g., just "IN" or "91"?
        # Server expects ISO code "IN" usually, but let's assume +91 maps to IN logic or just pass it.
        # If user types +91, we might want to map it? For now, let's keep it simple.
        # Actually server code checks `country != registered_country` where registered is "IN".
        # Let's default to "IN" if +91 is used, or just pass the code if the server handles it.
        # The prompt implies split. Let's send raw components.
        # Actually, standard ISO 2 char code is better for "Country Code". 
        # But if user types +91, that's a calling code.
        # Let's infer: If starts with +, it's a calling code.
        # For this hackathon demo, let's just default country to "IN" if +91 is detected.
        if country == "91" or country == "+91":
            country = "IN"
    else:
        # Fallback
        phone = raw_input
        country = "IN"

    account_id = input("Enter Account ID (Registered User): ").strip() or "TEST_USER_CLIENT"
    
    # 1. Start Call
    print("\n[Client] Connecting to Agent...")
    try:
        resp = requests.post(f"{SERVER_URL}/start-call", json={
            "phone": phone,
            "country": country, 
            "account_id": account_id
        })
        data = resp.json()
        if resp.status_code != 200:
            print(f"[Error] {data}")
            return
            
        SESSION_ID = data['session_id']
        print(f"[Client] Call Started (Session: {SESSION_ID})")
        
        # Play First Question
        if 'audio_url' in data:
            play_audio_from_url(data['audio_url'])
            
    except Exception as e:
        print(f"[Connection Failed] {e}")
        return

    # 2. Interaction Loop
    while True:
        # Record Answer
        record_file = "client_response.wav"
        try:
            input("[Press Enter to Start Recording]")
            record_audio(record_file, duration=5) # Fixed 5s for now, can be dynamic
        except NameError: 
             # Mock if imports failed
             print("[Mock] Recording...")
             time.sleep(2)
             # Write dummy wav
             import wave
             with wave.open(record_file, 'wb') as w:
                 w.setnchannels(1)
                 w.setsampwidth(2)
                 w.setframerate(44100)
                 w.writeframes(b'\x00' * 44100 * 2) # 1 sec silence
        
        # Send
        print("[Client] Sending Response...")
        try:
            with open(record_file, "rb") as f:
                files = {'file': f}
                payload = {'session_id': SESSION_ID}
                resp = requests.post(f"{SERVER_URL}/submit-response", files=files, data=payload)
                
            data = resp.json()
            
            if data.get("status") == "completed":
                print("\n[Client] IVR Completed. Connecting you to a human agent...")
                print("... (Music Playing) ...")
                # Wait loop or simple hold
                print(f"\n[Client] Entering Handover Mode...")
                break
                
            elif data.get("status") == "continued":
                # Play Next Question
                if 'audio_url' in data:
                    play_audio_from_url(data['audio_url'])
            else:
                print(f"[Client] Unknown Status: {data}")
                break
                
        except Exception as e:
            print(f"[Error Sending] {e}")
            break

    # --- Handover Phase ---
    print("\n" + "="*40)
    print("📞 CONNECTED TO HUMAN AGENT")
    print("System is listening for Agent Voice...")
    print("To Speak: Press Enter at any time.")
    print("="*40 + "\n")
    
    # Start Polling Thread
    def polling_loop():
        while True:
            try:
                poll_resp = requests.get(f"{SERVER_URL}/client/poll_agent/{SESSION_ID}")
                if poll_resp.status_code == 200:
                    poll_data = poll_resp.json()
                    if poll_data.get('has_audio'):
                        print("\n[Agent] Speaking...")
                        play_audio_from_url(poll_data['audio_url'])
                        print("\n[You] Press Enter to Reply >> ", end="", flush=True)
            except:
                pass
            time.sleep(1.5)

    poll_thread = threading.Thread(target=polling_loop, daemon=True)
    poll_thread.start()

    # Main Input Loop for User Reply
    while True:
        try:
            input("[You] Press Enter to Reply >> ")
            record_file = "client_handover_response.wav"
            record_audio(record_file, duration=5)
            
            # For now, we don't really have an 'agent listen' endpoint other than submit-response
            # But submit-response expects IVR flow. We might need a generic /client/speak endpoint too?
            # Or just reuse submit-response and ignore the IVR logic if completed?
            # Server side: If status is completed, just log/ignore or append to history.
            
            # Let's send to submit-response, server handles it implicitly or we ignore result.
            with open(record_file, "rb") as f:
                files = {'file': f}
                payload = {'session_id': SESSION_ID}
                requests.post(f"{SERVER_URL}/submit-response", files=files, data=payload)
            print("[Sent]")
            
            # Cleanup
            try:
                os.remove(record_file)
            except:
                pass
            
        except KeyboardInterrupt:
            print("Call Ended.")
            break

if __name__ == "__main__":
    main()
