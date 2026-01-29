
def generate_report(risk_data):
    """
    Generates a human-readable report.
    Format specified by user:
    
    otp verified :
    personal data check:
    voice Analysis : (in percentage how much matching to ai )
    user intent : 
    total risk chances :
    
    Args:
        risk_data (dict): Output from risk_engine.calculate_risk
        
    Returns:
        str: Formatted report text.
    """
    signals = risk_data["signals"]
    final_risk = risk_data["final_risk"]
    
    # Recommendation Logic
    recommendation = "Low Risk"
    if final_risk == "HIGH":
        recommendation = "High Risk (Escalate)"
    elif final_risk == "MEDIUM":
        recommendation = "Medium Risk (Caution)"
        
    # Signal formatting
    # OTP
    otp_str = "YES" if signals["otp_success"] else "NO"
    
    # Personal Data
    if signals['identity_fails'] == 0:
        personal_data_str = "Verified"
    else:
        personal_data_str = f"Failed ({signals['identity_fails']} discrepancies)"
        
    # Voice Analysis % (Simulated based on risk label)
    # The user wants "percentage how much matching to ai"
    # In our mock/simulated "features.py", we returned high prob for AI.
    # We can retrieve the probability if we pass it through, but risk_engine only got "LOW/HIGH".
    # Let's map it for now or check if we can pass prob. 
    # To keep it simple without changing risk_engine signature too much, 
    # we can estimate: High Risk -> >90%, Low Risk -> <10%.
    # Better: Let's pass the probability in 'signals' if possible, otherwise mock it based on label.
    
    voice_prob = signals.get("voice_prob", 0.0) # We need to ensure this is passed
    voice_percent = f"{voice_prob * 100:.2f}%"
    
    # Risk Percentage
    risk_percentage = risk_data.get("risk_percentage", 0.0)
    
    report = f"""
__________________________________________________
           VOICESENTINEL FINAL REPORT             
__________________________________________________

otp verified        : {otp_str}
personal data check : {personal_data_str}
voice Analysis      : {voice_percent} matching to AI
user intent         : {signals['intent']}
total risk chances  : {risk_percentage:.1f}% ({final_risk})
__________________________________________________
"""
    return report.strip()
