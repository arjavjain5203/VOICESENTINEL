from pymongo import MongoClient
import os

# Config
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "voice_sentinel"
COLLECTION_NAME = "call_verification_records"

def clean_database():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    print(f"Connected to {DB_NAME}.{COLLECTION_NAME}")
    print(f"Initial Count: {collection.count_documents({})}")
    
    # 1. Identify the Manual Enrollment Record
    # Look for the one created by manual_enroll.py
    manual_query = {"call_id": {"$regex": "^MANUAL_ENROLL_"}}
    manual_record = collection.find_one(manual_query)
    
    if not manual_record:
        print("❌ No MANUAL_ENROLL record found! Aborting to prevent total data loss.")
        return
        
    manual_id = manual_record['_id']
    print(f"✅ Found Manual Record: {manual_record['call_id']} (ID: {manual_id})")
    
    # 2. Delete EVERYTHING ELSE
    result = collection.delete_many({"_id": {"$ne": manual_id}})
    print(f"🗑️ Deleted {result.deleted_count} other records.")
    
    # 3. Update the Manual Record (Remove +91)
    current_phone = manual_record.get('phone_number', '')
    new_phone = current_phone.replace("+91", "").replace(" ", "").strip()
    
    if current_phone != new_phone:
        collection.update_one(
            {"_id": manual_id},
            {"$set": {"phone_number": new_phone}}
        )
        print(f"✏️ Updated Phone: '{current_phone}' -> '{new_phone}'")
    else:
        print(f"Phone already clean: {new_phone}")
        
    print(f"Final Count: {collection.count_documents({})}")
    print("Database is now clean and ready for testing.")

if __name__ == "__main__":
    clean_database()
