import joblib
import sys

try:
    scaler = joblib.load("scaler.pkl")
    print(f"Scaler type: {type(scaler)}")
    if hasattr(scaler, "n_features_in_"):
        print(f"n_features_in_: {scaler.n_features_in_}")
    else:
        print("n_features_in_ attribute not found.")
        print(dir(scaler))
    
    model = joblib.load("audio_classifier.pkl")
    print(f"Model type: {type(model)}")
except Exception as e:
    print(f"Error: {e}")
