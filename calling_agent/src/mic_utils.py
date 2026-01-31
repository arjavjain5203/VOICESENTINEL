from src.suppress_warnings import ignore_stderr
import time
import os
from src.tts_utils import speak

# Stub for cloud deployment - No Mic Access
MIC_AVAILABLE = False

def listen_and_transcribe(prompt_text, retries=3, save_to_file=None):
    """
    Stub implementation for cloud.
    Always falls back to text input or returns empty string if headless.
    """
    speak(prompt_text)
    print(f"[Mic Unavailable - Cloud Mode] Please type your response to: '{prompt_text}'")
    try:
        return input(">> ").strip()
    except EOFError:
        return ""

def append_audio_to_wav(audio_data, filename):
    pass

def record_audio_background(output_filename, duration=10):
    """
    Stub implementation. 
    Just ensures the file exists (touches it) to prevent errors in risk engine.
    """
    print(f"[Cloud Mode] Mocking background recording to {output_filename}")
    # touch file
    with open(output_filename, 'wb') as f:
        pass
    return True
