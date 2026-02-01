import os
import sys
import uuid
import datetime
import subprocess
import numpy as np

# Adjust path to find src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.voice_auth import VoiceAuthenticator
from src.database import save_verification_record, add_linked_account

def enroll_user(phone_number, user_id):
    print(f"\n🎙️  Starting Manual Voice Enrollment for {phone_number} (ID: {user_id})")
    print("---------------------------------------------------------------")
    
    # 1. Record Audio
    filename = "enrollment_temp.wav"
    try:
        if os.path.exists(filename):
            os.remove(filename)
            
        print("🔴 RECORDING for 8 seconds... SPEAK NOW! (Say: 'My voice is my password')")
        # Use arecord (16kHz, Mono, Signed 16bit)
        subprocess.run(
            ["arecord", "-d", "8", "-f", "S16_LE", "-r", "16000", "-c", "1", filename], 
            check=True
        )
        print("✅ Recording Complete.")
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return

    # 2. Generate Embedding
    try:
        print("⚙️  Generating Voice Embedding...")
        auth = VoiceAuthenticator()
        embedding = auth.extract_embedding_from_file(filename)
        
        if embedding is None:
            print("❌ Failed to extract embedding. Audio might be silent.")
            return
            
        print("✅ Embedding generated successfully.")
    except Exception as e:
        print(f"❌ Voice Auth Error: {e}")
        return

    # 3. Save to Database
    try:
        print("💾 Saving to Database...")
        with open(filename, "rb") as f:
            audio_bytes = f.read()
            
        call_id = str(uuid.uuid4())
        
        data = {
            "call_id": call_id,
            "user_id": user_id,
            "phone_number": phone_number,
            "country_code": "IN",
            "otp_sent": True,
            "otp_verified": True,
            "otp_attempts": 1,
            "personal_details": {"name": "Manual Enroll", "intent": "ENROLLMENT"},
            "personal_details_verified": True,
            "audio_bytes": audio_bytes,
            "audio_duration": 8.0,
            "ai_audio_probability": 0.0,
            "voice_match_score": 1.0, # Baseline
            "matched_call_id": None,
            "voice_embedding_bytes": embedding.tobytes(),
            "fraud_risk_score": 0,
            "phone_trust_score": 50, # Reset to neutral
            "user_id_trust_score": 50,
            "verification_status": "VERIFIED"
        }
        
        doc = save_verification_record(data)
        
        # Link account
        add_linked_account(phone_number, user_id)
        
        print(f"✅ Enrollment Successful! Record ID: {doc.get('audio_file_id')}")
        print("---------------------------------------------------------------")
        
        # Cleanup
        os.remove(filename)
        
    except Exception as e:
        print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    target_phone = "+9310082225"
    target_uid = "123456789"
    
    if len(sys.argv) > 2:
        target_phone = sys.argv[1]
        target_uid = sys.argv[2]
        
    enroll_user(target_phone, target_uid)
