import pymongo
import gridfs
import pyaudio
import wave
import os
import subprocess
import hashlib
import sys
from src.voice_auth import VoiceAuthenticator

# MongoDB Config
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "voice_sentinel"
COLLECTION_NAME = "call_verification_records"

def record_audio(filename, duration=5):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    p = pyaudio.PyAudio()
    
    print(f"🎤 Recording {duration}s... GO!")
    
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    
    for _ in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def main():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    fs = gridfs.GridFS(db)
    auth = VoiceAuthenticator()

    # Fetch Sorted Records
    records = list(collection.find().sort("audio_sequence_number", 1))
    total = len(records)
    
    print(f"📋 Found {total} records to populate.")
    
    for i, r in enumerate(records):
        print(f"\n[{i+1}/{total}] Processing Record: {r['audio_file_id']}")
        print(f"  User: {r['user_id']} | Phone: {r['phone_number']}")
        print(f"  Context: {r.get('personal_details_provided', {})}")
        
        while True:
            choice = input("  Press [Enter] to Record, 's' to Skip, 'q' to Quit: ").strip().lower()
            if choice == 'q': return
            if choice == 's': break
            
            # Record
            temp_file = "temp_fill.wav"
            record_audio(temp_file)
            
            # Playback
            print("  🔊 Playing back...")
            subprocess.run(["aplay", "-q", temp_file])
            
            confirm = input("  Keep this? (y/n): ").strip().lower()
            if confirm == 'y':
                with open(temp_file, "rb") as f:
                    data = f.read()
                    
                # 1. Update GridFS
                # Delete old if exists (unlikely for seed but good practice) or just put new
                # Since ID is string in doc but GridFS uses ObjectID usually, or we use filename.
                # Our schema uses 'audio_file_id' as filename "audio_XXXX.wav".
                filename = r['audio_file_id']
                
                # Check if exists in GridFS
                existing_file = fs.find_one({"filename": filename})
                if existing_file:
                    fs.delete(existing_file._id)
                
                # Upload
                fs.put(data, filename=filename, content_type="audio/wav")
                
                # 2. Extract Embedding
                emb = auth.extract_embedding_from_file(temp_file)
                emb_bytes = emb.tobytes() if emb is not None else None
                
                # 3. Update Document
                collection.update_one(
                    {"_id": r["_id"]},
                    {"$set": {
                        "voice_embedding": emb_bytes,
                        "audio_hash": hashlib.sha256(data).hexdigest()
                    }}
                )
                print("  ✅ Saved!")
                os.remove(temp_file)
                break
            else:
                print("  ♻️ Retrying...")

if __name__ == "__main__":
    main()
