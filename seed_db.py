import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.getcwd())

from src.database import init_db, get_db, save_call_record

def seed():
    print("Initializing Database...")
    init_db()
    db = next(get_db())
    
    # 1. Account 12345: High Risk History (Repeated SIM Swap)
    print("Seeding Account 12345 (High Risk History)...")
    base_time = datetime.utcnow() - timedelta(days=1)
    
    records = [
        {
            "account_id": "12345",
            "call_timestamp": base_time + timedelta(hours=1),
            "otp_success": False,
            "identity_fails": 1,
            "voice_risk_level": "LOW",
            "intent": "SIM_SWAP",
            "final_risk_level": "MEDIUM",
            "risk_percentage": 60.0,
            "agent_decision": "BLOCK"
        },
        {
            "account_id": "12345",
            "call_timestamp": base_time + timedelta(hours=2),
            "otp_success": True,
            "identity_fails": 0,
            "voice_risk_level": "LOW",
            "intent": "SIM_SWAP",
            "final_risk_level": "LOW",
            "risk_percentage": 30.0,
            "agent_decision": "ALLOW"
        },
         {
            "account_id": "12345",
            "call_timestamp": base_time + timedelta(hours=3),
            "otp_success": True,
            "identity_fails": 0,
            "voice_risk_level": "LOW",
            "intent": "SIM_SWAP",
            "final_risk_level": "LOW",
            "risk_percentage": 30.0,
            "agent_decision": "ALLOW"
        }
    ]
    
    for r in records:
        save_call_record(db, r)
        
    # 2. Account 99999: Clean History
    print("Seeding Account 99999 (Clean History)...")
    for i in range(5):
        save_call_record(db, {
            "account_id": "99999",
            "call_timestamp": base_time + timedelta(days=i),
            "otp_success": True,
            "identity_fails": 0,
            "voice_risk_level": "LOW",
            "intent": "REFUND",
            "final_risk_level": "LOW",
            "risk_percentage": 10.0,
            "agent_decision": "ALLOW"
        })

    print("Database Seeded Successfully.")

if __name__ == "__main__":
    seed()
