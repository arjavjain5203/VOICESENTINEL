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
MEMORY_COLLECTION_NAME = "cross_call_memory"

def get_db_connection():
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client[DB_NAME]
    return db

def init_db():
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info()
        print(f"[Database] Connected to MongoDB (Local): {DB_NAME}")
        
        # Ensure indexes for memory collection
        db = client[DB_NAME]
        db[MEMORY_COLLECTION_NAME].create_index("phone_number", unique=True)
        print(f"[Database] specific indexes created for {MEMORY_COLLECTION_NAME}")
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

    # 2. Determine Sequence Number (GLOBAL)
    last_record = db[COLLECTION_NAME].find_one(sort=[("audio_sequence_number", -1)])
    if last_record and "audio_sequence_number" in last_record:
        next_seq = last_record["audio_sequence_number"] + 1
    else:
        next_seq = 1
        
    formatted_audio_id = f"audio_{next_seq:04d}.wav"
    
    # GridFS Storage (Still useful, or store on disk and link?)
    # Requirement says "audio_file_id should reference storage using sequence".
    # We will use GridFS but name it correctly.
    if audio_bytes:
        try:
            # We override gridfs filename to match the standard
            audio_id = fs.put(audio_bytes, filename=formatted_audio_id, content_type="audio/wav")
            audio_hash = hashlib.sha256(audio_bytes).hexdigest()
        except Exception as e:
            print(f"[GridFS Error] {e}")

    # 3. Determine "First Time" Status and Total Calls
    phone = data['phone_number']
    prev_calls = db[COLLECTION_NAME].count_documents({"phone_number": phone})
    is_first = (prev_calls == 0)
    total_calls = prev_calls + 1


    # 3b. Velocity Check (Trust Decay)
    # Check calls in last 24 hours
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    daily_count = db[COLLECTION_NAME].count_documents({
        "phone_number": phone, 
        "call_timestamp": {"$gte": cutoff}
    })
    
    # Trust Logic
    phone_trust = data.get('phone_trust_score', 50)
    user_trust = data.get('user_id_trust_score', 50)
    
    # Penalty: If > 4 calls in 24h (Velocity Rule)
    # Applied primarily for "BATTERY_SWAP" but good as general rule for now
    if daily_count >= 4:
        print(f"[Trust Risk] High Velocity Detected ({daily_count} calls/24h). Applying Penalty.")
        phone_trust = max(0, phone_trust - 20)
        user_trust = max(0, user_trust - 20)
        
    # 4. Construct Document (STRICT SCHEMA)
    doc = {
        "call_id": data['call_id'], # Expected UUID string
        "user_id": data.get('user_id', f"unknown_{phone}"), # Fallback
        
        "phone_number": phone,
        "country_code": data.get('country_code', 'IN'),
        
        "total_calls": total_calls,
        
        "is_first_time_caller": is_first,
        "call_timestamp": datetime.datetime.utcnow(),
        
        "otp_sent": data.get('otp_sent', False),
        "otp_verified": data.get('otp_verified', False),
        "otp_attempts": data.get('otp_attempts', 0),
        
        "personal_details_provided": bool(data.get('personal_details')),
        "personal_details_verified": data.get('personal_details_verified', False),
        
        "audio_file_id": formatted_audio_id, # Strict Format
        "audio_sequence_number": next_seq,
        "audio_hash": audio_hash,
        "audio_duration_seconds": data.get('audio_duration', 0),
        
        "ai_audio_probability": data.get('ai_audio_probability', 0.0),
        "is_ai_generated_audio": data.get('ai_audio_probability', 0.0) > 0.8,
        "voice_match_score": data.get('voice_match_score', 0.0),
        
        "audio_matched_with_existing_record": not is_first, # Simple logic
        "matched_call_id": data.get('matched_call_id'),
        
        "voice_embedding": data.get('voice_embedding_bytes'), # Vector/Blob
        
        "fraud_risk_score": data.get('fraud_risk_score', 0),
        
        "phone_trust_score": phone_trust,
        "user_id_trust_score": user_trust,
        
        "related_call_ids": [],
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

def get_cross_call_memory(phone_number):
    """
    Retrieves the cross-call memory for a specific phone number.
    Returns dict or None.
    """
    db = get_db_connection()
    return db[MEMORY_COLLECTION_NAME].find_one({"phone_number": phone_number})

def update_cross_call_memory(phone_number, data_update):
    """
    Updates the cross-call memory for a phone number.
    data_update: dict containing fields to update (e.g., last_verified_name, trust_score_history)
    """
    db = get_db_connection()
    
    # We use upsert=True to create if not exists
    # We want to push to arrays and set scalar values
    
    set_fields = {}
    push_fields = {}
    
    # Fields that overwrite
    if 'last_verified_name' in data_update:
        set_fields['last_verified_name'] = data_update['last_verified_name']
    if 'last_verified_dob' in data_update:
        set_fields['last_verified_dob'] = data_update['last_verified_dob']
    if 'last_verified_embedding_hash' in data_update:
        set_fields['last_verified_embedding_hash'] = data_update['last_verified_embedding_hash']
        
    # Fields that append
    if 'trust_score' in data_update:
        push_fields['trust_score_history'] = data_update['trust_score']
    if 'call_timestamp' in data_update:
        push_fields['call_timestamps'] = data_update['call_timestamp']
        
    update_query = {}
    if set_fields:
        update_query["$set"] = set_fields
    if push_fields:
        update_query["$push"] = push_fields
        
    if update_query:
        db[MEMORY_COLLECTION_NAME].update_one(
            {"phone_number": phone_number},
            update_query,
            upsert=True
        )

def get_linked_accounts(phone_number):
    """
    Returns list of linked 'account_id' strings for a phone number.
    Returns empty list if none found.
    """
    mem = get_cross_call_memory(phone_number)
    if mem and 'linked_accounts' in mem:
        return mem['linked_accounts']
    return []

def add_linked_account(phone_number, account_id):
    """
    Adds an account_id to the authorized graph for this phone number.
    """
    db = get_db_connection()
    db[MEMORY_COLLECTION_NAME].update_one(
        {"phone_number": phone_number},
        {"$addToSet": {"linked_accounts": account_id}},
        upsert=True
    )
