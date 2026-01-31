# VoiceSentinel - AI Voice Fraud Detection System

VoiceSentinel is a real-time risk monitoring engine designed to detect AI-generated voice fraud (Deepfakes) and verify caller identity during support calls.

## Key Features
- **AI Voice Detection**: Analyzes audio features to distinguish between Human (Low Risk) and AI/Deepfake (High Risk) voices.
- **Weighted Risk Engine**: Calculates a precise Risk Percentage based on multiple signals:
    - **Voice Analysis** (Weight 2)
    - **Identity Verification** (Weight 2): Fuzzy matching for Name & DOB.
    - **OTP Verification** (Weight 1)
    - **Caller Intent** (Weight 1-4): Severity-based scoring for Intents like SIM Swap or Account Recovery.
- **Dual Operation Modes**:
    - **Live Interactive**: Real-time Q&A with audio accumulation.
    - **File Analysis**: Instant processing of pre-recorded audio files.

## Installation

### Prerequisites
- Python 3.10+
- System Audio Dependencies (Linux):
  ```bash
  sudo apt-get install portaudio19-dev ffmpeg
  ```
  *(FFmpeg is required for pydub/audio processing)*

### Setup
1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Live Interactive Mode (Default)
Run the simulation to start a mock support call. The system will listen to your microphone, accumulate your answers, and run the risk analysis automatically.

```bash
venv/bin/python main_simulation.py
```

### 2. File Analysis Mode (Deepfake Testing)
To test the system against specific audio files (e.g., an AI-generated sample) without speaking:

```bash
venv/bin/python main_simulation.py --audio-input path/to/audio.wav
```
*Example:*
```bash
venv/bin/python main_simulation.py --audio-input fraud_ai.wav
```

### 3. Simulation options
- `--fraud`: Hints the simulation to use specific mock behaviors if needed.

## Risk Scoring System
The system calculates a "Total Risk Chance" percentage based on weighted factors:
- **Max Score**: 9.0
- **Thresholds**:
    - **> 70%**: HIGH RISK (Escalate)
    - **> 40%**: MEDIUM RISK (Caution)
    - **< 40%**: LOW RISK

## Architecture
- `src/risk_engine.py`: Core logic for risk aggregation.
- `src/identity_processor.py`: NLP/Regex extraction of caller details.
- `src/features.py`: Audio feature extraction (Mock/Real hybrid for demo).
- `main_simulation.py`: Main entry point and orchestration.

## Troubleshooting
- **Microphone Errors**: If you see ALSA/Jack errors, they are usually harmless system warnings. The system suppresses most of them.
- **Parsing Issues**: Ensure you speak clearly. The system handles fuzzy matching for names like "Mukesh" (e.g., "Mokesh").
