def calculate_risk(otp_success, identity_fails, voice_risk, intent, voice_prob=0.0):
    """
    Aggregates risk signals into a final percentage score based on user-defined weights.
    
    Weights:
    - OTP Verification: 1 (Add if Failed)
    - Personal Data: 2 (Add if Failed)
    - Voice Analysis: 2 (Add * prob_ai)
    - Intent:
        - REFUND: 1
        - SIM_SWAP: 2
        - KYC_UPDATE: 3
        - ACCOUNT_RECOVERY: 4
    
    Total Max Score = 1 + 2 + 2 + 4 = 9.
    """
    
    # Intialize Score
    current_score = 0.0
    details = {}
    
    # 1. OTP (Weight 1)
    if not otp_success:
        current_score += 1.0
        details["otp_score"] = 1.0
    else:
        details["otp_score"] = 0.0
        
    # 2. Personal Data (Weight 2)
    if identity_fails > 0:
        current_score += 2.0
        details["data_score"] = 2.0
    else:
        details["data_score"] = 0.0
        
    # 3. Voice Analysis (Weight 2)
    # Scale proportional to AI probability
    voice_contribution = voice_prob * 2.0
    current_score += voice_contribution
    details["voice_score"] = voice_contribution
    
    # 4. Intent Scoring (Weight 1-4)
    intent_scores = {
        "REFUND": 1.0,
        "SIM_SWAP": 2.0,
        "KYC_UPDATE": 3.0,
        "ACCOUNT_RECOVERY": 4.0
    }
    # Default to 2.0 (Medium) if unknown
    intent_val = intent_scores.get(intent, 2.0)
    current_score += intent_val
    details["intent_score"] = intent_val
    
    # Calculate Percentage
    max_score = 9.0
    risk_percentage = (current_score / max_score) * 100.0
    
    # Determine Risk Label
    if risk_percentage >= 70:
        final_risk = "HIGH"
    elif risk_percentage >= 40:
        final_risk = "MEDIUM"
    else:
        final_risk = "LOW"
        
    return {
        "base_risk": f"{risk_percentage:.1f}%",
        "final_risk": final_risk,
        "risk_percentage": risk_percentage,
        "breakdown": details,
        "signals": {
            "otp_success": otp_success,
            "identity_fails": identity_fails,
            "voice_risk": voice_risk,
            "voice_prob": voice_prob,
            "intent": intent
        }
    }
