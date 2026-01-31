import pymongo
import gridfs
import os

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "voice_sentinel"

def check():
    print("🔍 Checking MongoDB Connection...")
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info()
        print("✅ MongoDB is Running and Reachable.")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("   -> Please install MongoDB manually (sudo apt install mongodb).")
        return

    db = client[DB_NAME]
    fs = gridfs.GridFS(db)
    
    print("Writing verification file to GridFS...")
    try:
        file_id = fs.put(b"test_audio_data", filename="test.txt")
        print(f"✅ Write Success: {file_id}")
        
        out = fs.get(file_id).read()
        print(f"✅ Read Success: {out}")
        
        fs.delete(file_id)
        print("✅ Delete Success")
        
    except Exception as e:
        print(f"❌ GridFS Error: {e}")

if __name__ == "__main__":
    check()
