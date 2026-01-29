def calculate_risk(otp_success, identity_fails, voice_risk, intent, voice_prob=0.0, history_modifier=0):
    """
    Aggregates risk signals into a final percentage score based on user-defined weights.
    
    Weights:
    - OTP Verification: 1 (Add if Failed)
    - Personal Data: 2 (Add if Failed)
    - Voice Analysis: 2 (Add * prob_ai)
    - Intent: Weight 1-4
    - History Modifier: -1 (Safe), 0 (Neutral), +1 (Risky)
      -> Adjusts final level, NOT just raw score.
    
    Total Max Score = 9.
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
    
    # Determine Initial Risk Label
    if risk_percentage >= 70:
        base_label = "HIGH"
    elif risk_percentage >= 40:
        base_label = "MEDIUM"
    else:
        base_label = "LOW"
        
    # 5. Apply History Modifier
    # Rules: History moves risk by at most 1 level.
    # History [-1, 0, 1]
    levels = ["LOW", "MEDIUM", "HIGH"]
    current_idx = levels.index(base_label)
    new_idx = current_idx + history_modifier
    
    # Clamp
    new_idx = max(0, min(2, new_idx))
    final_risk = levels[new_idx]
    
    # If modifier forced a change, explain it?
    history_impact = "None"
    if new_idx > current_idx:
        history_impact = "Increased Risk Level"
    elif new_idx < current_idx:
        history_impact = "Decreased Risk Level"
        
    return {
        "base_risk": f"{risk_percentage:.1f}%",
        "final_risk": final_risk,
        "risk_percentage": risk_percentage,
        "breakdown": details,
        "history_modifier": history_modifier,
        "history_impact": history_impact,
        "signals": {
            "otp_success": otp_success,
            "identity_fails": identity_fails,
            "voice_risk": voice_risk,
            "voice_prob": voice_prob,
            "intent": intent
        }
    }
