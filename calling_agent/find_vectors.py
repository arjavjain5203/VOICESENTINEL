import joblib
import numpy as np
import sys

# Load artifacts
try:
    scaler = joblib.load("scaler.pkl")
    model = joblib.load("audio_classifier.pkl")
except Exception as e:
    print(f"Failed to load artifacts: {e}")
    sys.exit(1)

print("Modules loaded.")

def find_vector(target_label):
    # target_label: 0 for Human, 1 for AI (assuming, verify assumption)
    # The prompt says: label = "AI" if prob_ai > 0.5 else "Human"
    # Usually model.classes_ is [0, 1] or ["Human", "AI"].
    # Checking classes_
    print(f"Classes: {model.classes_}")
    
    # Generate random vectors
    for i in range(100000):
        # Generate raw features (gaussian)
        raw_features = np.random.randn(1, 32) * 5 # Scale up to cover more space
        
        # Scale
        features_scaled = scaler.transform(raw_features)
        
        # Predict
        probs = model.predict_proba(features_scaled)[0]
        prob_ai = probs[1] # Assuming index 1 is the positive class, logic says "prob_ai > 0.5"
        
        if target_label == "AI" and prob_ai > 0.9:
            return raw_features, prob_ai
        if target_label == "Human" and prob_ai < 0.1:
            return raw_features, prob_ai

    return None, None

print("Finding Human vector...")
human_vec, human_prob = find_vector("Human")
if human_vec is not None:
    print(f"FOUND HUMAN: Prob={human_prob}")
    print(f"Vector={list(human_vec[0])}")
else:
    print("Could not find Human vector")

print("Finding AI vector...")
ai_vec, ai_prob = find_vector("AI")
if ai_vec is not None:
    print(f"FOUND AI: Prob={ai_prob}")
    print(f"Vector={list(ai_vec[0])}")
else:
    print("Could not find AI vector")
