import pyaudio
import wave
import sys
import os
import numpy as np
from src.database import get_baseline_audio, init_db
from src.voice_auth import VoiceAuthenticator

def record_audio(filename, duration=5):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000 
    
    p = pyaudio.PyAudio()
    print(f"\n🎤 Recording Test Sample ({duration}s)...")
    
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Error opening mic: {e}")
        return False
    
    frames = []
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        
    print("✅ Recording Finished.")
    
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
    print("=== VOICE MATCH ACCURACY TEST ===")
    
    # 1. Get Baseline
    phone = input("Enter Phone Number to Test [Default: +91 9310082225]: ").strip() or "+91 9310082225"
    
    print(f"🔍 Fetching Baseline for {phone}...")
    try:
        baseline_emb = get_baseline_audio(phone)
    except Exception as e:
        print(f"Database Error: {e}")
        return

    if baseline_emb is None:
        print("❌ No verified baseline found for this number.")
        print("   Run 'manual_enroll.py' first.")
        return
        
    print("✅ Baseline Found.")
    
    # 2. Record New Sample
    test_file = "temp_test_match.wav"
    input("Press Enter to start recording NEW sample (Speak same/different phrase)... ")
    if not record_audio(test_file):
        return
        
    # 3. Compare
    print("⚙️ Comparing Voice Features...")
    try:
        auth = VoiceAuthenticator()
        new_emb = auth.extract_embedding_from_file(test_file)
        
        if new_emb is None:
            print("❌ Could not extract voice features from recording (Too quiet?).")
        else:
            score = auth.compare_embeddings(new_emb, baseline_emb)
            percent = score * 100
            
            print("\n" + "="*30)
            print(f"MATCH SCORE: {score:.4f}")
            print(f"ACCURACY   : {percent:.2f}%")
            print("="*30)
            
            if score > 0.75:
                print("✅ RESULT: MATCH (Same Person)")
            else:
                print("❌ RESULT: NO MATCH (Different Person)")
                
    except Exception as e:
        print(f"Error: {e}")
        
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    init_db() # Print DB connection status
    main()
