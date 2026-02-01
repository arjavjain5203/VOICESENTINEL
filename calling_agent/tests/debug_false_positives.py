
import os
import sys

# Add parent directory to path to find 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai_detector import detect_ai_audio

# Test Files
HUMAN_FILES = [
    "/home/arjav-jain/Coding/Hackathon/client_handover_response.wav",
    "/home/arjav-jain/Coding/Hackathon/client_response.wav"
]

print("="*60)
print("DEBUGGING AI FALSE POSITIVES")
print("="*60)

# Generate AI Sample
from gtts import gTTS
ai_file = "debug_ai_gen.wav"
tts = gTTS("This is a synthesized AI voice for debugging purposes.", lang='en')
tts.save(ai_file)

FILES = [
    # Full Files (Known Working)
    ("AI Sample 1 (Full)", "/home/arjav-jain/Coding/Hackathon/calling_agent/temp_d4f32cdf-ffbe-4c31-9aea-41182d632771_full.wav"),
    
    # Partial Chunks
    ("AI Sample 1 (Chunk 0)", "/home/arjav-jain/Coding/Hackathon/calling_agent/temp_d4f32cdf-ffbe-4c31-9aea-41182d632771_0.wav"),
    ("AI Sample 2 (Chunk 0)", "/home/arjav-jain/Coding/Hackathon/calling_agent/temp_9e112e46-22d0-42d3-a757-bcfebc18b2f7_0.wav"),
    ("AI Sample 2 (Chunk 1)", "/home/arjav-jain/Coding/Hackathon/calling_agent/temp_9e112e46-22d0-42d3-a757-bcfebc18b2f7_1.wav")
]

for label, fpath in FILES:
    if os.path.exists(fpath):
        print(f"\n--- Testing {label} ({os.path.basename(fpath)}) ---")
        try:
            # We need raw probs, but the function returns single value.
            # Let's just trust the function's consistency for now, or assume it returns P(Index 0).
            # Current implementation: returns P(Index 0).
            
            prob_idx_0 = detect_ai_audio(fpath) # This returns probs[0][0] based on my code
            
            print(f"-> Model Output (P(Index 0)): {prob_idx_0:.4f}")
            print(f"-> Current Logic Interpretation: {prob_idx_0*100:.1f}% FAKE")
            
        except Exception as e:
            print(f"-> Error: {e}")
    else:
        print(f"Skipping {fpath}")

print("\n" + "="*60)
