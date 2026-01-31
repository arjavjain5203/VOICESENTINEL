import requests
import pyaudio
import wave
import sys
import os
import time

SERVER_URL = "http://localhost:5001"

def get_active_sessions():
    try:
        r = requests.get(f"{SERVER_URL}/agent/api/sessions")
        return r.json()
    except:
        return []

def record_audio(filename, duration=5):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100 # Standard mic rate
    
    p = pyaudio.PyAudio()
    print(f"\n🎤 Agent Recording ({duration}s)... GO!")
    
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Mic Error: {e}")
        return False
    
    frames = []
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        
    print("✅ Finished.")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    return True

def main():
    print("=== AGENT REPLY TOOL ===")
    
    # 1. Select Session
    sessions = get_active_sessions()
    if not sessions:
        print("No active sessions found on server.")
        sid = input("Enter Session ID manually (or press Enter to exit): ").strip()
        if not sid: return
    else:
        print("\nActive Sessions:")
        for idx, s in enumerate(sessions):
            print(f"{idx+1}. {s['phone']} (Status: {s.get('status','Unknown')}) - ID: {s['id']}")
            
        choice = input("\nSelect Session # (or Enter ID): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(sessions):
            sid = sessions[int(choice)-1]['id']
        else:
            sid = choice
            
    print(f"\n💬 Chatting with Session: {sid}")
    print("Ctrl+C to Exit")
    
    while True:
        try:
            input("\n[Press Enter to Speak to User] ")
            filename = "temp_agent_msg.wav"
            if record_audio(filename, duration=5):
                print("📤 Sending...")
                with open(filename, 'rb') as f:
                    r = requests.post(f"{SERVER_URL}/agent/speak", 
                                      data={"session_id": sid},
                                      files={"file": f})
                    if r.status_code == 200:
                        print("✅ Sent to User.")
                    else:
                        print(f"❌ Error: {r.text}")
                
            if os.path.exists(filename):
                os.remove(filename)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    main()
