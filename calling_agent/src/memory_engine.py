
import numpy as np
import datetime
from difflib import SequenceMatcher

def calculate_name_stability(current_name, history):
    """
    Computes name stability score.
    Returns: (score [0.0-1.0], flag [bool])
    """
    if not history or not history.get('last_verified_name'):
        return 1.0, False # First time or no history defaults to stable/neutral
        
    last_name = history['last_verified_name']
    
    if not current_name:
        return 0.5, False # Missing current name is suspicious but not a mismatch
        
    # Normalized Comparison
    s1 = current_name.lower().strip()
    s2 = last_name.lower().strip()
    
    ratio = SequenceMatcher(None, s1, s2).ratio()
    
    # Thresholds
    # > 0.8 : High match (Stable)
    # < 0.4 : Mismatch (Unstable)
    
    is_changed = ratio < 0.8
    return ratio, is_changed

def calculate_dob_stability(current_dob, history):
    """
    Computes DOB stability.
    Returns: (score [0.0-1.0], mismatch_count [int])
    """
    if not history or not history.get('last_verified_dob'):
        return 1.0, 0
        
    last_dob = history['last_verified_dob']
    
    if not current_dob:
         return 0.5, 0
         
    # Simple string match for date
    # Format expected: YYYY-MM-DD or similar
    if current_dob == last_dob:
        return 1.0, 0
    else:
        return 0.0, 1

def calculate_trust_trend(current_score, history):
    """
    Determines trust trend direction.
    Returns: "increasing" | "stable" | "decreasing"
    """
    if not history or not history.get('trust_score_history'):
        return "stable"
        
    past_scores = history['trust_score_history']
    if not past_scores:
        return "stable"
        
    # Average of last 3
    recent_avg = sum(past_scores[-3:]) / len(past_scores[-3:])
    
    if current_score > recent_avg + 5:
        return "increasing"
    elif current_score < recent_avg - 5:
        return "decreasing"
    else:
        return "stable"

def calculate_voice_similarity_trend(current_similarity_to_last, history):
    """
    Tracks if voice similarity is improving or degrading.
    This requires storing past similarity scores? 
    For now, we just return the raw similarity as the trend logic needs more data points than usually available in v1.
    """
    return "stable" # Placeholder for complex trend logic
