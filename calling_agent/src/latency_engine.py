
import os
import librosa
import time

def get_audio_duration(file_path):
    """
    Returns duration of an audio file in seconds.
    """
    try:
        if not os.path.exists(file_path):
            return 0.0
        # librosa.get_duration is fast for header reading
        return librosa.get_duration(path=file_path)
    except Exception as e:
        print(f"[Latency] Error getting duration for {file_path}: {e}")
        return 0.0

def calculate_hesitation_risk(prompt_end_time, user_start_time):
    """
    Calculates risk based on response latency (hesitation).
    
    Args:
        prompt_end_time (float): Timestamp when bot finished speaking.
        user_start_time (float): Timestamp when user started speaking.
        
    Returns:
        tuple: (risk_level, risk_score, hesitation_seconds)
    """
    if prompt_end_time is None or user_start_time is None:
        return "UNKNOWN", 0.0, 0.0
        
    hesitation = user_start_time - prompt_end_time
    
    # Logic:
    # < 0.2s: Unnaturally fast (Bot/Scripted) -> Medium Risk
    # 0.2s - 2.0s: Normal -> Low Risk
    # 2.0s - 4.0s: Slow -> Low/Medium
    # > 5.0s: Suspiciously Slow (Coached) -> High Risk
    
    risk_level = "LOW"
    risk_score = 0.0
    
    if hesitation < 0.2:
        risk_level = "MEDIUM" # Potential Bot
        risk_score = 0.4
    elif hesitation > 5.0:
        risk_level = "HIGH" # Potential Coached / Distracted
        risk_score = 0.7
    elif hesitation > 3.0:
        risk_level = "MEDIUM"
        risk_score = 0.3
        
    return risk_level, risk_score, hesitation
