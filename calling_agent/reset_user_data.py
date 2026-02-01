import pymongo
import sys

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "voice_sentinel"
COLLECTION_NAME = "call_verification_records"
MEMORY_COLLECTION_NAME = "cross_call_memory"

def reset_user(phone_number):
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Delete Verification Records (where baseline audio lives)
        result1 = db[COLLECTION_NAME].delete_many({"phone_number": phone_number})
        print(f"[Reset] Deleted {result1.deleted_count} call records for {phone_number}")
        
        # 2. Delete Cross-Call Memory (Trust Score, Stability)
        result2 = db[MEMORY_COLLECTION_NAME].delete_many({"phone_number": phone_number})
        print(f"[Reset] Deleted {result2.deleted_count} memory records for {phone_number}")
        
        print("✅ User reset complete. Next call will be treated as First Time Caller.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Handle variations of the number
    # User said 931008225, but logs showed +9310082225 (different length?) 
    # Let's try to match what's in DB.
    
    target_phone = "+9310082225" # Based on previous logs
    # or input arg
    if len(sys.argv) > 1:
        target_phone = sys.argv[1]
        
    print(f"Resetting data for: {target_phone}")
    reset_user(target_phone)
