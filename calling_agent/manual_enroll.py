import pyaudio
import wave
import sys
import os
import datetime
import hashlib
from src.database import save_verification_record
from src.voice_auth import VoiceAuthenticator

def record_audio(filename, duration=5):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000 # Resemblyzer prefers 16k
    
    p = pyaudio.PyAudio()
    
    print(f"\n🎤 Recording for {duration} seconds... Speak naturally!")
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
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

def main():
    print("=== MANUAL USER ENROLLMENT ===")
    
    # 1. Gather Details
    phone = input("Phone (+Code Number) [Default: +91 9310082225]: ").strip() or "+91 9310082225"
    account_id = input("Account ID [Default: 123456789]: ").strip() or "123456789"
    name = input("Name [Default: mukesh]: ").strip() or "mukesh"
    dob = input("DOB [Default: 15-07-2005]: ").strip() or "15-07-2005"
    
    # 2. Record Voice
    audio_file = "temp_enrollment.wav"
    input("\nPress Enter to start recording voice sample... ")
    record_audio(audio_file, duration=5)
    
    # 3. Process Audio (Extract Embedding)
    try:
        print("⚙️ Processing Voice Embedding...")
        auth = VoiceAuthenticator()
        emb = auth.extract_embedding_from_file(audio_file)
        
        if emb is None:
            print("❌ Failed to extract vocal features. Try again.")
            return
            
        # Read bytes for storage
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
            
    except Exception as e:
        print(f"❌ Audio Processing Error: {e}")
        return

    # 4. Save to DB (Verified Status)
    verification_data = {
        "call_id": f"MANUAL_ENROLL_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "phone_number": phone,
        "country_code": "IN", # Approx
        "is_first_time_caller": True, # This creates the baseline
        "otp_sent": False,
        "otp_verified": True, # MANUALLY VERIFIED
        "otp_attempts": 0,
        "personal_details": {
            "name": name,
            "dob": dob,
            "intent": "Manual Enrollment"
        },
        "personal_details_verified": True,
        "audio_bytes": audio_bytes,
        "audio_duration": 5.0,
        "ai_audio_probability": 0.0,
        "is_ai_generated_audio": False,
        "voice_match_score": 1.0, # Self match
        "voice_embedding_bytes": emb.tobytes(), # Save explicit embedding for faster lookup
        "fraud_risk_score": 0,
        "verification_status": "VERIFIED"
    }
    
    print("\n💾 Saving to MongoDB...", end=" ")
    save_verification_record(verification_data)
    print("DONE!")
    
    # Cleanup
    os.remove(audio_file)
    print(f"\n✅ User {name} ({phone}) enrolled successfully.")
    print("Next call from this number should show 'MATCHED'.")

if __name__ == "__main__":
    main()
