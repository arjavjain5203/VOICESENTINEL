import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

# Default to SQLite for local testing if env var not set
# Ensure we trust the certificate for Aiven (mysql+pymysql usually handles it if system certs are okay, 
# otherwise we might need confirm ssl_ca or check_hostname=False for hackathon/dev).
DB_URL = os.getenv("DATABASE_URL", "sqlite:///voice_sentinel.db")

Base = declarative_base()

class CallRecord(Base):
    __tablename__ = 'call_records'
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String(50), index=True) # MySQL needs length for Varchar index usually
    call_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Risk Signals
    otp_success = Column(Boolean)
    identity_fails = Column(Integer)
    voice_risk_level = Column(String(10)) 
    intent = Column(String(50))
    
    # Final Outcome
    final_risk_level = Column(String(10)) 
    risk_percentage = Column(Float)
    agent_decision = Column(String(20), nullable=True) 

# Setup Engine
# Aiven requires SSL. passing connect_args={'ssl': {'ssl_mode': 'REQUIRED'}} might be needed if not in URL.
# Pymysql uses 'ssl_ca' usually, but 'ssl_disabled=False' default.
# Let's trust Aiven.
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def save_call_record(db, record_data):
    """
    Saves a new call record.
    record_data: dict containing required fields.
    """
    db_record = CallRecord(**record_data)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

def get_account_history(db, account_id, limit=5):
    """
    Fetches the last N records for an account.
    """
    return db.query(CallRecord).filter(CallRecord.account_id == account_id).order_by(CallRecord.call_timestamp.desc()).limit(limit).all()
