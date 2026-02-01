
import torch
import torchaudio
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
import os
import sys

# Add src to path for tts_utils
sys.path.append(os.path.join(os.getcwd(), 'src'))
from tts_utils import generate_wav

MODEL_NAME = "mo-thecreator/Deepfake-audio-detection"

def debug_model():
    print(f"Loading model: {MODEL_NAME}")
    # Use FeatureExtractor instead of Processor
    feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
    model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_NAME)
    model.eval()
    
    # Generate Test Audio
    wav_path = "debug_ai.wav"
    generate_wav("This is a synthetic voice generated for debugging purposes.", wav_path)
    
    print(f"Processing {wav_path}...")
    import librosa
    import numpy as np
    
    # Load with librosa (resamples automatically if sr provided)
    speech_np, sr = librosa.load(wav_path, sr=16000)
    speech = torch.tensor(speech_np).float()
    
    # if sr != 16000: # Librosa handles it
    #    speech = torchaudio.functional.resample(speech, sr, 16000)
        
    print(f"Audio shape: {speech.shape}")
        
    inputs = feature_extractor(
        speech.squeeze().numpy(), # FeatureExtractor expects numpy usually
        sampling_rate=16000,
        return_tensors="pt",
        padding=True
    )
    
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)

        
    print("\n--- DEBUG RESULTS ---")
    print(f"Logits: {logits}")
    print(f"Probs: {probs}")
    print(f"Label 0: {probs[0][0].item():.4f}")
    print(f"Label 1: {probs[0][1].item():.4f}")
    
    # Check id2label if available
    if hasattr(model.config, 'id2label'):
        print(f"Label Mapping: {model.config.id2label}")
        
    if os.path.exists(wav_path):
        os.remove(wav_path)

if __name__ == "__main__":
    debug_model()
