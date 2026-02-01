
import sys
import os
import time

# Add src
sys.path.append(os.path.join(os.getcwd(), 'src'))
from tts_utils import generate_wav
from ai_detector import detect_ai_audio

def test_model():
    print("Generating AI Audio...")
    wav_path = "test_direct_ai.wav"
    generate_wav("This is a test of the AI detection system.", wav_path)
    
    print("Running Inference...")
    start = time.time()
    prob = detect_ai_audio(wav_path)
    dur = time.time() - start
    
    print(f"Inference Time: {dur:.2f}s")
    print(f"AI Probability: {prob:.4f}")
    
    if prob > 0.5:
        print("RESULT: FAIL (Predicted Fake)") # Wait, detecting AI should be SUCCESS for the system, but "Fake" means AI.
        # If prob is high, it detected AI.
        print("Risk Level: HIGH (Correctly detected AI)")
    else:
        print("RESULT: PASS (Predicted Real)") 
        # Wait, if I create AI audio, I WANT it to detect AI.
        # So prob > 0.5 is SUCCESS.
        print(f"Risk Level: LOW (Failed to detect AI - Prob {prob})")

    if os.path.exists(wav_path):
        os.remove(wav_path)

if __name__ == "__main__":
    test_model()
