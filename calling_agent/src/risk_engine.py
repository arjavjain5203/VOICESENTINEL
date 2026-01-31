def calculate_risk(otp_success, identity_fails, voice_risk, intent, voice_prob=0.0, voice_match_score=1.0, history_modifier=0, country_mismatch=False):
    """
    Aggregates risk signals into a final percentage score based on user-defined weights.
    
    Weights:
    - OTP Verification: 1 (Add if Failed)
    - Personal Data: 2 (Add if Failed)
    - Voice Analysis: 2 (Add * prob_ai)
    - Intent: Weight 1-4
    - Country Mismatch: 2 (Add if True)
    - History Modifier: -1 (Safe), 0 (Neutral), +1 (Risky)
      -> Adjusts final level, NOT just raw score.
    
    Total Max Score = 11.
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

    # 3b. Voice Match (Weight 2) - EQUAL TO AI
    # Match 1.0 -> Risk 0
    # Match 0.0 -> Risk 2
    voice_match_risk = (1.0 - voice_match_score) * 2.0
    current_score += voice_match_risk
    details["match_score"] = voice_match_risk
    
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

    # 3b. Voice Match Score (Weight 2)
    # Inverse logic: High match (1.0) -> Low Risk (0.0 added)
    # Low match (0.0) -> High Risk (2.0 added)
    # We assume 'voice_match_score' is passed in arguments or kwargs? 
    # Current signature doesn't have it explicitly, let's look at kwargs or add it.
    # Wait, the tool call below changes the signature too.
    
    # 5. Country Mismatch (Weight 2)
    if country_mismatch:
        current_score += 2.0
        details["country_score"] = 2.0
    else:
        details["country_score"] = 0.0
    
    # Calculate Percentage
    max_score = 13.0 # Updated from 11 (Added 2 for Voice Match)
    risk_percentage = (current_score / max_score) * 100.0
    
    # Determine Initial Risk Label
    if risk_percentage >= 70:
        base_label = "HIGH"
    elif risk_percentage >= 40:
        base_label = "MEDIUM"
    else:
        base_label = "LOW"
        
    # 6. Apply History Modifier
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
            "intent": intent,
            "country_mismatch": country_mismatch
        }
    }
