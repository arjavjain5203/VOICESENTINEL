import pymongo

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "voice_sentinel"

def reset():
    print("⚠️  RESETTING MONGODB DATABASE...")
    
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.drop_database(DB_NAME)
        print(f"✅ Dropped Database: {DB_NAME}")
    except Exception as e:
        print(f"❌ Error dropping database: {e}")
        print("   Ensure MongoDB is running.")
        return

    print("\n✅ Database Reset Complete.")
    print("   The next call will enroll the user as a new entry.")

if __name__ == "__main__":
    reset()
