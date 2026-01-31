import os

# Define the flow steps
IVR_STEPS = [
    {
        "id": "welcome_otp",
        "question_text": "Welcome to Voice Sentinel. For verification, please provide the One Time Password sent to your registered mobile.",
        "audio_file": "ivr_audio/welcome_otp.wav",
        "expected_field": "otp"
    },
    {
        "id": "ask_name",
        "question_text": "Thank you. Please say your full name.",
        "audio_file": "ivr_audio/ask_name.wav",
        "expected_field": "name"
    },
    {
        "id": "ask_dob",
        "question_text": "Please state your date of birth.",
        "audio_file": "ivr_audio/ask_dob.wav",
        "expected_field": "dob"
    },
    {
        "id": "ask_intent",
        "question_text": "How can I help you today?",
        "audio_file": "ivr_audio/ask_intent.wav",
        "expected_field": "intent"
    }
]

def get_next_question(current_step_index):
    """
    Returns the next question object based on current index.
    Returns None if passed the last step.
    """
    if current_step_index < len(IVR_STEPS):
        return IVR_STEPS[current_step_index]
    return None

def ensure_ivr_audio_files(tts_engine_func):
    """
    Ensures that the static IVR audio files exist.
    tts_engine_func: Function to generate wav from text (e.g., speak/generate_wav)
    """
    if not os.path.exists("ivr_audio"):
        os.makedirs("ivr_audio")
        
    for step in IVR_STEPS:
        path = step["audio_file"]
        if not os.path.exists(path):
            print(f"Generating IVR Audio: {path}")
            tts_engine_func(step["question_text"], path)
