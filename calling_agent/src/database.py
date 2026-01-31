import pymongo
import gridfs
import json
import numpy as np
import os
import datetime
import hashlib

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "voice_sentinel"
COLLECTION_NAME = "call_verification_records"

def get_db_connection():
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client[DB_NAME]
    return db

def init_db():
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info()
        print(f"[Database] Connected to MongoDB (Local): {DB_NAME}")
    except Exception as e:
        print(f"❌ [Database Error] Could not connect to MongoDB: {e}")

def get_baseline_audio(phone_number):
    """
    Retrieves the baseline audio embedding (or raw bytes) for a repeat caller.
    We look for the FIRST successfully verified record.
    """
    db = get_db_connection()
    # Find the oldest verified record for this number
    record = db[COLLECTION_NAME].find_one(
        {"phone_number": phone_number, "verification_status": "VERIFIED"},
        sort=[("call_timestamp", 1)] # Oldest first
    )
    
    if record and record.get('voice_embedding'):
        return np.frombuffer(record['voice_embedding'], dtype=np.float32)
    return None

def is_first_time_caller(phone_number):
    db = get_db_connection()
    count = db[COLLECTION_NAME].count_documents({"phone_number": phone_number})
    return count == 0

def save_verification_record(data):
    """
    Saves the consolidated Verification Record.
    """
    db = get_db_connection()
    fs = gridfs.GridFS(db)
    
    # 1. Handle Audio Upload
    audio_id = None
    audio_hash = None
    audio_bytes = data.get('audio_bytes')
    
    if audio_bytes:
        try:
            filename = f"{data['call_id']}.wav"
            audio_id = fs.put(audio_bytes, filename=filename, content_type="audio/wav")
            audio_hash = hashlib.sha256(audio_bytes).hexdigest()
        except Exception as e:
            print(f"[GridFS Error] {e}")

    # 2. Determine "First Time" Status (if not explicitly passed)
    is_first = data.get('is_first_time_caller')
    if is_first is None:
        is_first = is_first_time_caller(data['phone_number'])

    # 3. Construct Document
    doc = {
        "call_id": data['call_id'],
        "phone_number": data['phone_number'],
        "country_code": data.get('country_code', 'IN'),
        "is_first_time_caller": is_first,
        "call_timestamp": datetime.datetime.utcnow().timestamp(),

        # OTP
        "otp_sent": data.get('otp_sent', False),
        "otp_verified": data.get('otp_verified', False),
        "otp_attempts": data.get('otp_attempts', 0),

        # Personal Details
        "personal_details_provided": data.get('personal_details', {}),
        "personal_details_verified": data.get('personal_details_verified', False),

        # Audio
        "audio_file_id": audio_id,
        "audio_hash": audio_hash,
        "audio_duration_seconds": data.get('audio_duration', 0),

        # AI Detection
        "ai_audio_probability": data.get('ai_audio_probability', 0.0),
        "is_ai_generated_audio": data.get('ai_audio_probability', 0.0) > 0.8,

        # Voice Matching
        "voice_match_score": data.get('voice_match_score', 0.0),
        "audio_matched_with_existing_record": not is_first,
        "matched_call_id": data.get('matched_call_id'),
        
        # Store embedding for future comparisons (Crucial for Baseline)
        "voice_embedding": data.get('voice_embedding_bytes'), 

        # Final Risk
        "fraud_risk_score": data.get('fraud_risk_score', 0),
        "verification_status": data.get('verification_status', "FAILED")
    }
    
    try:
        result = db[COLLECTION_NAME].insert_one(doc)
        print(f"[Database] Saved Verification Record: {result.inserted_id}")
        return doc
    except Exception as e:
        print(f"[Database Error] Save failed: {e}")
        return None

# Deprecated / Wrapper functions for compatibility if needed
def get_user_embedding(account_id):
    # This might need to look up by phone_number instead of account_id now?
    # For now, let's assume account_id is phone_number or needed for migration.
    # We'll map account_id -> phone_number lookup if possible, or just return None
    # to force a fresh baseline if strict new schema is used.
    return None 

def get_recent_calls(account_id, limit=5):
    # Map account_id to phone_number query logic if needed
    # returning empty list to avoid breaking legacy calls
    return []
