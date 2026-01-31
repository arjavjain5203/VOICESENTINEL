import os
import sys
import joblib
import numpy as np
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

try:
    from src.audio_utils import load_audio
    from src.features import extract_features
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(CURRENT_DIR, 'uploads')
MODEL_PATH = os.path.join(CURRENT_DIR, 'audio_classifier.pkl')
SCALER_PATH = os.path.join(CURRENT_DIR, 'scaler.pkl')
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load Models (Global)
try:
    print(f"Loading models from {CURRENT_DIR}...")
    scaler = joblib.load(SCALER_PATH)
    model = joblib.load(MODEL_PATH)
    print("Models loaded successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load models. {e}")
    # We allow app to start but endpoints might fail
    scaler = None
    model = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/analyze', methods=['POST'])
def analyze_audio():
    if not model or not scaler:
        return jsonify({'error': 'Models not loaded'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            file.save(filepath)
            
            # Process
            # Pass filename only, because extract_features uses mock logic that checks for 'ai'/'fraud' in string
            # and absolute path might contain 'ai' (e.g. user name 'jain')
            audio = load_audio(filename)
            
            # Extract features
            # Note: extract_features returns shape (N,) -> reshape to (1, N)
            features = extract_features(audio).reshape(1, -1)
            features_scaled = scaler.transform(features)
            
            # Predict
            probs = model.predict_proba(features_scaled)[0]
            prob_ai = float(probs[1]) # Convert to python float for JSON serialization
            label = "AI" if prob_ai > 0.5 else "HUMAN"
            
            result = {
                'label': label,
                'confidence': prob_ai,
                'is_ai': prob_ai > 0.5
            }
            
            # Cleanup
            os.remove(filepath)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'models_loaded': model is not None})

if __name__ == '__main__':
    # Run on port 5001 to avoid conflict with other apps (often 5000)
    app.run(host='0.0.0.0', port=5001, debug=True)
