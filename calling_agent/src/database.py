import os
import datetime
import pymongo
from pymongo import MongoClient
import ssl
from dotenv import load_dotenv
import bson.binary

# Load env variables from .env file
load_dotenv()

# MongoDB Configuration
# Default to the provided Cloud Atlas URL
DEFAULT_DB_URL = "mongodb+srv://kushagrapandey0333_db_user:9310022664d@client.0hwe3gz.mongodb.net/?retryWrites=true&w=majority"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
DB_NAME = "voice_sentinel"

client = None
db = None

def init_db():
    """
    Initializes the MongoDB connection.
    """
    global client, db
    try:
        # Create a new client and connect to the server
        # 'ssl_cert_reqs=ssl.CERT_NONE' might be needed for some environments/dev certificates, 
        # but try standard connection first or use certifi if needed.
        import certifi
        client = MongoClient(DB_URL, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
        
        # Send a ping to confirm a successful connection
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        
        db = client[DB_NAME]
        
        # Create indexes
        db.users.create_index("account_id", unique=True)
        db.call_records.create_index("account_id")
        db.call_records.create_index([("call_timestamp", pymongo.DESCENDING)])
        
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise e

def get_db():
    """
    Returns the database instance. Initialize if not already done.
    """
    global db
    if db is None:
        init_db()
    return db

def save_call_record(db_conn, record_data):
    """
    Saves a new call record to 'call_records' collection.
    """
    # Ensure timestamp is datetime object
    if "call_timestamp" not in record_data:
        record_data["call_timestamp"] = datetime.datetime.utcnow()
        
    result = db_conn.call_records.insert_one(record_data)
    record_data["_id"] = result.inserted_id
    return record_data

def get_account_history(db_conn, account_id, limit=5):
    """
    Fetches the last N records for an account.
    """
    cursor = db_conn.call_records.find({"account_id": account_id}).sort("call_timestamp", -1).limit(limit)
    return list(cursor)

def get_user_embedding(db_conn, account_id):
    """
    Retrieves the voice embedding for a user.
    Returns: binary/bytes embedding or None if user not found.
    """
    user = db_conn.users.find_one({"account_id": account_id}, {"voice_embedding": 1})
    if user and "voice_embedding" in user:
        return user["voice_embedding"]
    return None

def save_user_embedding(db_conn, account_id, embedding_bytes):
    """
    Saves or updates a user's voice embedding.
    embedding_bytes: The embedding as bytes (from numpy array or resemblyzer).
    """
    user_data = {
        "account_id": account_id,
        "voice_embedding": bson.binary.Binary(embedding_bytes),
        "updated_at": datetime.datetime.utcnow()
    }
    
    # Upsert: Update if exists, Insert if new
    db_conn.users.update_one(
        {"account_id": account_id},
        {"$set": user_data},
        upsert=True
    )
    print(f"User {account_id} enrolled/updated in Voice Auth DB.")
