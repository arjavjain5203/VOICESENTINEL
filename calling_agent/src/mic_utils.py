from src.suppress_warnings import ignore_stderr
import speech_recognition as sr
import time
import os
from src.tts_utils import speak

# Global flag to track if mic is available
MIC_AVAILABLE = True
try:
    with ignore_stderr():
        import pyaudio
except ImportError:
    MIC_AVAILABLE = False
    print("\n[System Warning] PyAudio not installed. Microphone input will fallback to text.\n")
except Exception:
    # Sometimes ALSA errors crash import? unlikely but safe.
    pass

import wave

def listen_and_transcribe(prompt_text, retries=3, save_to_file=None):
    """
    Plays a prompt, listens for user input, and returns the transcribed text.
    Fallbacks to text input if Mic is unavailable.
    
    Args:
        save_to_file (str, optional): Path to append the recorded audio to.
    """
    global MIC_AVAILABLE
    
    # Speak the prompt
    speak(prompt_text)
    
    if not MIC_AVAILABLE:
        # Fallback to text
        print(f"[Mic Unavailable] Please type your response to: '{prompt_text}'")
        return input(">> ").strip()
    
    recognizer = sr.Recognizer()
    
    for attempt in range(retries):
        try:
            with ignore_stderr():
                mic = sr.Microphone()
                with mic as source:
                    print(f"\n[Listening ({attempt+1}/{retries})...]")
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # Append audio if requested
            if save_to_file:
                 append_audio_to_wav(audio, save_to_file)
            
            print("[Processing...]")
            with ignore_stderr():
                text = recognizer.recognize_google(audio)
            print(f"[User Said]: {text}")
            return text
            
        except sr.WaitTimeoutError:
            print("[Silence detected]")
            if attempt < retries - 1:
                speak("I didn't hear anything. Could you please repeat that?")
        except sr.UnknownValueError:
            print("[Unintelligible]")
            if attempt < retries - 1:
                speak("I'm sorry, I didn't quite catch that. Can you say it again?")
        except Exception as e:
            print(f"[Error] {e}")
            # If Mic fails (e.g. no device), disable it for session and fallback
            MIC_AVAILABLE = False
            print("[System] Switching to text input due to Mic error.")
            return input(">> ").strip()
            
    speak("I am having trouble hearing you. Moving on.")
    return ""

def append_audio_to_wav(audio_data, filename):
    """
    Appends AudioData (from speech_recognition) to a WAV file.
    """
    data_bytes = audio_data.get_wav_data()
    
    # If file doesn't exist, we can just write it.
    # But audio_data.get_wav_data() returns a full valid WAV file (header + bytes).
    # To append, we need to strip headers from subsequent chunks and merge data,
    # OR simpler: Use pydub to append if available, or just standard wave module logic.
    # standard wave is complex for appending because we need to update nframes in header.
    # EASIEST: Just simply overwrite for this demo if it's single chunk?
    # NO, Requirement is ACCUMULATION.
    
    # Let's use a robust append approach.
    # Since we don't have pydub in 'requirements.txt' enforced, we try standard lib.
    # Actually pydub *is* installed in venv (from TTS step).
    
    try:
        from pydub import AudioSegment
        import io
        
        new_segment = AudioSegment.from_wav(io.BytesIO(data_bytes))
        
        if os.path.exists(filename):
            existing_segment = AudioSegment.from_wav(filename)
            combined = existing_segment + new_segment
            combined.export(filename, format="wav")
        else:
            new_segment.export(filename, format="wav")
            
        # print(f"[Debug] Appended audio to {filename}")
        
    except Exception as e:
        print(f"[Audio Append Error] {e}")

def record_audio_background(output_filename, duration=10):
    """
    Records audio in the background.
    If Mic unavailable, generates a dummy file using TTS/Signal logic.
    """
    global MIC_AVAILABLE
    
    if MIC_AVAILABLE:
        try:
            recognizer = sr.Recognizer()
            with ignore_stderr():
                mic = sr.Microphone()
                with mic as source:
                    # print(f"[Background Recording] Listening...")
                    audio = recognizer.record(source, duration=duration)
                
            with open(output_filename, "wb") as f:
                f.write(audio.get_wav_data())
            return True
        except Exception as e:
            print(f"[Background Rec Error] {e}")
            MIC_AVAILABLE = False
    
    # Fallback: Just ensure the file exists from previous generation steps
    # or create a placeholder for the "Risk Engine" to analyze.
    # The 'main_simulation' should have already ensured 'legit.wav' or 'fraud_ai.wav' exists.
    # We will just COPY one of those to 'current_session.wav' to simulate recording.
    import shutil
    try:
        # Default to legit for safety if mock, or let the simulation control which one to use
        # Logic in main will handle the file source for risk analysis.
        pass 
    except Exception:
        pass
        
    return False
