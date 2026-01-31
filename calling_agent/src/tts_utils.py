import os
import tempfile
import time
from gtts import gTTS
from pydub import AudioSegment

def speak(text, slow=False):
    """
    Generates audio from text using Google TTS and plays it.
    
    ON CLOUD: Playback is disabled. Just logs the text.
    """
    print(f"\n[System Voice]: {text}\n")
    # Cloud Optimization: No playback

def generate_wav(text, output_path):
    """
    Generates a WAV file from text (useful for creating dummy input files).
    """
    try:
        tts = gTTS(text=text, lang='en')
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            mp3_path = fp.name
        
        tts.save(mp3_path)
        
        # Convert to wav using pydub
        sound = AudioSegment.from_mp3(mp3_path)
        sound.export(output_path, format="wav")
        
        os.remove(mp3_path)
        print(f"Generated audio file: {output_path}")
        
    except Exception as e:
        print(f"Failed to generate wav: {e}")
