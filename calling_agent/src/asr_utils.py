
import os
import time
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

def transcribe_audio_real(audio_path):
    """
    Transcribes audio using OpenAI Whisper (Base model).
    """
    try:
        import whisper
        
        print(f"[ASR Logic] Loading Whisper model (base)... This may take a moment.")
        model = whisper.load_model("base")
        
        print(f"[ASR Logic] Transcribing {audio_path}...")
        result = model.transcribe(audio_path)
        text = result["text"].strip()
        
        return text
        
    except ImportError:
        print("[ASR Error] openai-whisper not installed. Falling back to simulation.")
        return None
    except Exception as e:
        print(f"[ASR Error] Transcription failed: {e}")
        return None

def transcribe_audio(audio_path, intent):
    """
    Hybrid ASR:
    1. Tries to use real Whisper transcription on the audio file.
    2. If that fails (or returns empty), falls back to the intent-based simulation.
    """
    
    # Try real transcription first
    if os.path.exists(audio_path):
        transcript = transcribe_audio_real(audio_path)
        if transcript:
            return transcript
            
    # Fallback to simulation
    transcripts = {
        "REFUND": "Hi, I'm calling because I'd like to request a refund for a transaction I didn't authorize.",
        "SIM_SWAP": "Hello, I lost my phone and I need to swap my SIM card to a new device immediately.",
        "ACCOUNT_RECOVERY": "I'm locked out of my account and need to recover my password using my security questions."
    }
    
    return transcripts.get(intent, "I need assistance with my account.")

def save_transcript(transcript, output_path="current_transcript.txt"):
    try:
        with open(output_path, "w") as f:
            f.write(transcript)
    except Exception as e:
        print(f"Warning: Failed to save transcript: {e}")
