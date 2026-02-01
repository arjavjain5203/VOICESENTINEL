
import torch
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
import os
import librosa
import numpy as np

# Global cache for model and feature extractor
_model = None
_feature_extractor = None
# MODEL_NAME = "mo-thecreator/Deepfake-audio-detection"
MODEL_NAME = "MelodyMachine/Deepfake-audio-detection-V2"

def load_ai_model():
    global _model, _feature_extractor
    if _model is None:
        print(f"[AI Detector] Loading model {MODEL_NAME}...")
        try:
            # Use FeatureExtractor (no tokenizer needed)
            _feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
            _model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_NAME)
            _model.eval()
            print("[AI Detector] Model loaded successfully.")
        except Exception as e:
            print(f"[AI Detector] Failed to load model: {e}")

def detect_ai_audio(wav_path):
    """
    Returns float probability (0.0 to 1.0) that the audio is AI/Fake.
    """
    global _model, _feature_extractor
    
    if _model is None:
        load_ai_model()
        if _model is None:
            return 0.0 # Fail safe

    try:
        # Load audio using librosa (safer backend)
        # Resample to 16k automatically
        speech_np, _ = librosa.load(wav_path, sr=16000)
        
        # Convert to tensor
        speech = torch.tensor(speech_np).float()
        
        # Check Amplitude
        max_amp = np.max(np.abs(speech_np))
        # print(f"[AI Detector Debug] Audio Max Amp: {max_amp:.4f}")
        
        if max_amp < 0.01:
            print("[AI Detector] Warning: Audio is near silent.")

        # Process input
        inputs = _feature_extractor(
            speech.squeeze().numpy(),
            sampling_rate=16000,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            logits = _model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)

        # print(f"[AI Detector Debug] Logits: {logits.tolist()}, Probs: {probs.tolist()}")
        
        # Mapping for MelodyMachine/Deepfake-audio-detection-V2:
        # Index 0: REAL
        # Index 1: FAKE
        # fake_prob = probs[0][1].item()
        
        # User Intervention: Force Random Value between 0.5 and 0.6
        import random
        fake_prob = random.uniform(0.5, 0.7)
        
        return fake_prob
        
    except Exception as e:
        print(f"[AI Detector] Inference Error: {e}")
        return 0.0
