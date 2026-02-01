def calculate_risk(otp_success, identity_fails, voice_risk, intent, voice_prob=0.0, voice_match_score=1.0, history_modifier=0, country_mismatch=False,
                   name_stability=1.0, dob_stability=1.0, trust_trend="stable", latency_score=0.0):
    """
    Aggregates risk signals into a final percentage score based on user-defined weights.
    
    Weights:
    - OTP Verification: 1 (Add if Failed)
    - Personal Data: 2 (Add if Failed)
    - Voice Analysis: 35 (Add * prob_ai) [CRITICAL]
    - Voice Match: 15 (Add * (1-match)) [HIGH]
    - Intent: Weight 1-4
    - Country Mismatch: 2 (Add if True)
    - History Modifier: -1 (Safe), 0 (Neutral), +1 (Risky)
      -> Adjusts final level, NOT just raw score.
    
    Total Max Score = 67.0
    """
    
    # Intialize Score
    current_score = 0.0
    details = {}
    
    # --- CORE SIGNALS ---
    
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
        
    # 3. Voice Analysis (Weight 35 - CRITICAL)
    # Scale proportional to AI probability
    # If 100% AI, adds 35 points.
    voice_contribution = voice_prob * 35.0
    current_score += voice_contribution
    details["voice_score"] = voice_contribution

    # 3b. Voice Match (Weight 15 - HIGH IMPORTANCE) - EQUAL TO AI
    # Match 1.0 -> Risk 0
    # Match 0.0 -> Risk 15
    voice_match_risk = (1.0 - voice_match_score) * 15.0
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

    # --- MEMORY SIGNALS (Priority 1) ---
    
    # 6. Name Stability (Weight 2)
    # 1.0 = Stable (0 risk), 0.0 = Changed (2 risk)
    name_risk = (1.0 - name_stability) * 2.0
    current_score += name_risk
    details["name_stability_risk"] = name_risk
    
    # 7. DOB Stability (Weight 3 - Critical)
    # 1.0 = Stable, 0.0 = Mismatch
    dob_risk = (1.0 - dob_stability) * 3.0
    current_score += dob_risk
    details["dob_stability_risk"] = dob_risk
    
    # 8. Trust Trend (Weight 1)
    # decreasing -> +1 risk
    if trust_trend == "decreasing":
        current_score += 1.0
        details["trust_trend_risk"] = 1.0
    else:
        details["trust_trend_risk"] = 0.0
        
    # --- LATENCY SIGNALS (Priority 2) ---
    # 9. Response Latency (Weight 2)
    # Score 0.0 to 1.0 input (where 0.7 is high risk)
    # Scaled by 2
    l_risk = latency_score * 2.0
    current_score += l_risk
    details["latency_risk"] = l_risk
    
    # Calculate Percentage
    # Calculate Percentage
    # Max Score Calculation:
    # Base (17) + VoiceAI (35) + VoiceMatch (15) = 67.0
    max_score = 67.0
    risk_percentage = (current_score / max_score) * 100.0
    
    # Determine Initial Risk Label
    if risk_percentage >= 60:
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
            "intent": intent,
            "country_mismatch": country_mismatch,
            "name_stability": name_stability,
            "dob_stability": dob_stability,
            "trust_trend": trust_trend,
            "latency_score": latency_score
        }
    }
