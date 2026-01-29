
import os
import tempfile
import time
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

def speak(text, slow=False):
    """
    Generates audio from text using Google TTS and plays it.
    
    Args:
        text (str): Text to speak.
        slow (bool): Whether to speak slowly.
    """
    print(f"\n[System Voice]: {text}\n")
    
    try:
        # Generate TTS
        tts = gTTS(text=text, lang='en', slow=slow)
        
        # Save to temp mp3
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
            temp_path = fp.name
            
        tts.save(temp_path)
        
        # Check if ffmpeg/ffplay is available for pydub
        # If running headless, this might fail or just not play sound.
        try:
            # os.system(f"ffplay -nodisp -autoexit -hide_banner {temp_path} > /dev/null 2>&1")
            # Using os.system is easier for simple playback than pydub sometimes in restricted envs
            exit_code = os.system(f"ffplay -nodisp -autoexit -hide_banner -loglevel quiet '{temp_path}'")
            
            if exit_code != 0:
                # Fallback to just logging if player fails
                pass 
                
        except Exception as e:
            print(f"[Audio Error] Could not play audio: {e}")
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"[TTS Error] Failed to generate speech: {e}")

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
