import pymongo
import datetime

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "voice_sentinel"

def inspect():
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        db = client[DB_NAME]
        client.server_info()
    except Exception as e:
        print(f"❌ Could not connect to MongoDB: {e}")
        return

    print("\n" + "="*50)
    print("📂 MONGODB INSPECTION")
    print("="*50)

    # 1. Verification Records
    print("\n[Collection: call_verification_records]")
    try:
        records = list(db.call_verification_records.find().sort("call_timestamp", -1).limit(5))
        if not records:
            print("  (No records found)")
        for r in records:
            print(f"  Call ID  : {r.get('call_id')}")
            print(f"  Phone    : {r.get('phone_number')} (First Time: {r.get('is_first_time_caller')})")
            print(f"  Status   : {r.get('verification_status')} (Risk: {r.get('fraud_risk_score')})")
            print(f"  Voice    : Match={r.get('voice_match_score')} | AI Prob={r.get('ai_audio_probability')}")
            print(f"  OTP      : {r.get('otp_verified')} | Details: {r.get('personal_details_verified')}")
            print(f"  Audio ID : {r.get('audio_file_id')}")
            print("-" * 40)
    except Exception as e:
        print(f"  Error reading records: {e}")

    print("="*50 + "\n")

if __name__ == "__main__":
    inspect()
