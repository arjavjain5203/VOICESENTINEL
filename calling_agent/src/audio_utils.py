import librosa
import numpy as np

def load_audio(path, sr=16000):
    """
    Loads audio file using librosa.
    Returns numpy array.
    """
    try:
        y, _ = librosa.load(path, sr=sr)
        return y
    except Exception as e:
        print(f"[Error] Failed to load audio {path}: {e}")
        return np.zeros(16000) # Return 1s silence on error

