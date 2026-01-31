import pymongo
import datetime
import uuid
import random

# MongoDB Config
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "voice_sentinel"
COLLECTION_NAME = "call_verification_records"

def reset_and_seed():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # 1. DELETE EXISTING DATASET
    print(f"🗑️  Deleting collection '{COLLECTION_NAME}'...")
    collection.drop()
    
    # 2. CREATE INDEXES
    print("🏗️  Creating Indexes...")
    collection.create_index("call_id", unique=True)
    collection.create_index("user_id")
    collection.create_index("phone_number")
    collection.create_index("call_timestamp")
    
    # 3. SEED DATA
    print("🌱 Generating Seed Data...")
    
    # Base Relationships
    # user_id: 123456789 -> phone: 9310082225
    # user_id: 987654321 -> phone: 9310082225 (Shared Phone)
    # user_id: 123456789 -> phone: 9876500000 (Multi Phone)
    
    users = ["123456789", "987654321", "555555555"]
    phones = ["9310082225", "9876500000", "1122334455"]
    
    seed_records = []
    
    # Helper for sequence
    global_seq = 0
    
    def create_record(u_id, ph, seq_num, trust_ph, trust_usr, intent="ACCOUNT_RECOVERY", risk="LOW", match=1.0):
        # Determine duration randomly
        duration = random.randint(5, 120)
        
        # Audio ID logic
        audio_id = f"audio_{seq_num:04d}.wav"
        
        return {
            "call_id": str(uuid.uuid4()),
            "user_id": u_id,
            "phone_number": ph,
            "country_code": "IN",
            
            "total_calls": random.randint(1, 15),
            
            "is_first_time_caller": (random.choice([True, False])),
            "call_timestamp": datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(0, 10), minutes=random.randint(0, 60)),
            
            "otp_sent": True,
            "otp_verified": True,
            "otp_attempts": 1,
            
            "personal_details_provided": True,
            "personal_details_verified": True,
            
            "audio_file_id": audio_id,
            "audio_sequence_number": seq_num,
            "audio_hash": f"hash_{uuid.uuid4().hex[:8]}", # Mock hash
            "audio_duration_seconds": duration,
            
            "ai_audio_probability": random.uniform(0.0, 0.1) if risk == "LOW" else random.uniform(0.8, 1.0),
            "is_ai_generated_audio": (risk == "HIGH"),
            "voice_match_score": match,
            
            "audio_matched_with_existing_record": (match > 0.8),
            "matched_call_id": None, # Could link to prev, kept null for simplicity
            
            "voice_embedding": [], # Mock vector
            
            "fraud_risk_score": random.uniform(0.1, 0.3) if risk == "LOW" else random.uniform(0.8, 0.95),
            
            "phone_trust_score": trust_ph,
            "user_id_trust_score": trust_usr,
            
            "related_call_ids": [],
            "verification_status": "VERIFIED" if risk == "LOW" else "FLAGGED"
        }

    # Record 1: User A, Phone A (High Trust)
    global_seq += 1
    seed_records.append(create_record(users[0], phones[0], global_seq, 95, 90))
    
    # Record 2: User B, Phone A (Shared Phone - Diff User)
    global_seq += 1
    seed_records.append(create_record(users[1], phones[0], global_seq, 95, 20)) # Phone trusted, User B new/low trust
    
    # Record 3: User A, Phone B (Same User, Diff Phone)
    global_seq += 1
    seed_records.append(create_record(users[0], phones[1], global_seq, 50, 90)) 
    
    # Record 4: User C, Phone C (Random)
    global_seq += 1
    seed_records.append(create_record(users[2], phones[2], global_seq, 80, 80))
    
    # Record 5-12: Filler data to reach >10
    for _ in range(8):
        global_seq += 1
        u = random.choice(users)
        p = random.choice(phones)
        # Randomize trust slightly
        t_p = random.randint(40, 99)
        t_u = random.randint(40, 99)
        seed_records.append(create_record(u, p, global_seq, t_p, t_u))

    # Insert
    result = collection.insert_many(seed_records)
    print(f"✅ inserted {len(result.inserted_ids)} records.")
    
    # Verify Sequence
    last_doc = collection.find_one(sort=[("audio_sequence_number", -1)])
    print(f"🔊 Last Audio Sequence: {last_doc['audio_file_id']} ({last_doc['audio_sequence_number']})")
    
    print("\n✅ Antigraviti Delivery Complete: DB Reset & Seeded.")

if __name__ == "__main__":
    reset_and_seed()
