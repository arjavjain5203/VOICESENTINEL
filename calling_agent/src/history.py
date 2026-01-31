from datetime import datetime, timedelta

def analyze_history(history_records):
    """
    Analyzes past call records to determine a risk modifier.
    
    Args:
        history_records (list): List of CallRecord objects (ordered by desc time).
        
    Returns:
        tuple: (modifier_score, explanation_list)
        modifier_score: -1 (Lower Risk), 0 (Neutral), +1 (Raise Risk)
    """
    if not history_records:
        return 0, ["No prior history."]
    
    modifier = 0
    explanations = []
    
    # Helper to safely get data
    def get_intent(record):
        return record.get('details', {}).get('intent')
    
    def get_risk(record):
        return record.get('details', {}).get('final_risk_level', 'LOW')
        
    def get_timestamp(record):
        return record.get('timestamp')
    
    # 1. Repeated Intent (e.g., 3x Refund/SimSwap in recent history)
    intents = [get_intent(r) for r in history_records]
    if len(intents) >= 3:
        # Check if last 3 are same (and not None)
        if intents[0] is not None and intents[0] == intents[1] == intents[2]:
            modifier += 1
            explanations.append(f"Repeated Intent Detected: {intents[0]} (3x)")
            
    # 2. Previous Escalations / High Risk
    # If the VERY LAST call was High Risk, be cautious.
    if get_risk(history_records[0]) == "HIGH":
        modifier += 1
        explanations.append("Last call was HIGH Risk.")
        
    # 3. Frequency / Velocity (Simple check: 3 calls in 1 hour)
    # Using timestamp
    if len(history_records) >= 3:
        t1 = get_timestamp(history_records[0])
        t3 = get_timestamp(history_records[2])
        
        # t1, t3 are floats (timestamp). 
        if t1 and t3:
             if (t1 - t3) < 3600: # 1 hour in seconds
                 modifier += 1
                 explanations.append("High call velocity (3 calls in <1 hour).")

    # 4. Good Behavior (Redemption)
    # If last 5 calls were LOW risk and OTP passed (Risk from DB usually factors OTP)
    if len(history_records) >= 5:
        recent_risks = [get_risk(r) for r in history_records[:5]]
        if all(risk == "LOW" for risk in recent_risks):
            modifier -= 1
            explanations.append("Consistent Low Risk history (Trusted).")

    # Clamp modifier to range [-1, 1] per requirements
    # "History may increase or decrease the current risk by one level at most"
    modifier = max(-1, min(1, modifier))
    
    if modifier == 0 and not explanations:
        explanations.append("Normal history.")
        
    return modifier, explanations
