from flask import Flask, request, jsonify, send_from_directory
import json
import os
import uuid
import threading
import sys
import wave
import contextlib
import contextlib
import numpy as np
from datetime import datetime

# Ensure src in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.risk_engine import calculate_risk
from src.ivr_flow import IVR_STEPS, get_next_question, ensure_ivr_audio_files
from src.database import init_db, get_recent_calls, save_verification_record, is_first_time_caller, get_baseline_audio, get_user_embedding, get_cross_call_memory, update_cross_call_memory
from src.tts_utils import generate_wav
from src.history import analyze_history
from src.memory_engine import calculate_name_stability, calculate_dob_stability, calculate_trust_trend
from src.voice_auth import VoiceAuthenticator
from src.audio_utils import load_audio
from src.asr_utils import transcribe_audio
from src.identity_processor import extract_details_from_transcript, validate_identity
from src.risk_engine import calculate_risk
from src.ai_detector import detect_ai_audio
from src.latency_engine import get_audio_duration, calculate_hesitation_risk
import time

app = Flask(__name__)

# Global Sessions Store
sessions = {}

# Ensure IVR questions exist & Cache Durations
ensure_ivr_audio_files(generate_wav)
PROMPT_DURATIONS = {}
for step in IVR_STEPS:
    try:
        PROMPT_DURATIONS[step['id']] = get_audio_duration(step['audio_file'])
        print(f"[Init] Cached duration for {step['id']}: {PROMPT_DURATIONS[step['id']]:.2f}s")
    except Exception as e:
        print(f"[Init] Failed to cache duration for {step['id']}: {e}")
        PROMPT_DURATIONS[step['id']] = 0.0

    # Helper: Merge Audio Files
def merge_audio_files(outfile, file_list):
    """
    Concatenates multiple wav files into one. Skips invalid files.
    """
    data = []
    params = None
    for fpath in file_list:
        if os.path.exists(fpath):
            try:
                with wave.open(fpath, 'rb') as w:
                    if not params:
                        params = w.getparams()
                    data.append(w.readframes(w.getnframes()))
            except Exception as e:
                print(f"[Warning] Skipping invalid chunk {fpath}: {e}")
                
    if not params or not data:
        return
        
    try:
        with wave.open(outfile, 'wb') as w:
            w.setparams(params)
            for d in data:
                w.writeframes(d)
    except Exception as e:
        print(f"[Error] Failed to write merged audio: {e}")

# ... (omitted) ...

        # --- Cleanup Temporary Files ---
        try:
            if os.path.exists(session['accumulated_audio']):
                os.remove(session['accumulated_audio'])
            for chunk_file in session['chunks']:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
            print(f"[Cleanup] Removed temp files for session {session_id}")
        except Exception as e:
            print(f"[Cleanup Warning] {e}")
            
        # Report is now printed inside submit_response before cleaning up
        
        return jsonify({
            "status": "completed",
            "report": risk_data
        })

def analysis_thread(session_id):
    """
    Background Analysis:
    - Transcribe accumulated audio
    - Extract details (OTP, Name, etc.)
    - Run Risk Engine
    - Run Voice Auth
    """
    session = sessions.get(session_id)
    if not session:
        return

    print(f"[Analysis] Starting background analysis for session {session_id}")
    
    accumulated_path = session['accumulated_audio']
    
    if not os.path.exists(accumulated_path):
        print(f"[Analysis] Skipped (File cleaned up/missing): {accumulated_path}")
        return
    
    # 1. Transcribe
    try:
        if os.path.exists(accumulated_path):
            transcript = transcribe_audio(accumulated_path, "UNKNOWN")
            session['transcript'] = transcript
            print(f"[Analysis] Transcript: {transcript}")

            # PLAYBACK ON SERVER (So Agent hears the User)
            # Use latest chunk to avoid replaying history
            if session['chunks']:
                try:
                    subprocess.run(["aplay", "-q", session['chunks'][-1]], check=False)
                except Exception as e:
                    print(f"[Playback Error] Could not play audio: {e}")
        
            # 2. Extract Details
            # We update the session's details incrementally
            new_details = extract_details_from_transcript(transcript)
            session['extracted_details'].update(new_details)
        else:
            return
    except Exception as e:
        print(f"[Analysis] Transcription Error: {e}")
    
    # 3. AI Detection (HuggingFace Transformers)
    try:
        if not os.path.exists(accumulated_path): return
        
        # New Deepfake detection
        ai_prob = detect_ai_audio(accumulated_path)
        session['voice_prob'] = ai_prob
        print(f"[Analysis] AI Prob: {ai_prob:.4f}")
        
    except Exception as e:
        print(f"[Analysis] AI Detection Error: {e}")
        session['voice_prob'] = 0.0

    # 4. Voice Auth (Resemblyzer)
    try:
        if not os.path.exists(accumulated_path): return
            
        # Lazy load authenticator
        auth = VoiceAuthenticator()
        emb = auth.extract_embedding_from_file(accumulated_path)
        
        if emb is not None:
             # Connect DB
            from src.database import get_baseline_audio
            baseline_emb = get_baseline_audio(session['phone'])
            
            if baseline_emb is not None:
                score = auth.compare_embeddings(emb, baseline_emb)
                session['voice_match_score'] = score
            else:
                # First time caller (or no verified baseline yet)
                # We will save this embedding implicitly when saving the full record
                session['voice_match_score'] = 1.0 # Consider 1.0 for self (first time)
                session['enrolled_now'] = True
    except Exception as e:
         if "No such file" not in str(e):
             print(f"[Analysis] Voice Auth Error: {e}")

    session['analyzed'] = True
    session['analyzing'] = False
    print(f"[Analysis] Finished for {session_id}")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "ivr_backend"})

@app.route('/start-call', methods=['POST'])
def start_call():
    """
    Init call.
    Check Country.
    """
    data = request.json
    phone = data.get('phone')
    country = data.get('country', 'IN') # Default IN
    account_id = data.get('account_id', 'UNKNOWN')
    
    if not phone:
        return jsonify({"error": "Phone required"}), 400
        
    session_id = str(uuid.uuid4())
    
    # Country Check Logic
    # Mock: Assume registered country is 'IN' for everyone
    registered_country = "IN" 
    country_mismatch = (country != registered_country)
    
    sessions[session_id] = {
        "id": session_id,
        "phone": phone,
        "account_id": account_id,
        "country_mismatch": country_mismatch,
        "step_index": 0,
        "chunks": [],
        "accumulated_audio": f"temp_{session_id}_full.wav",
        "extracted_details": {"otp": None, "name": None, "dob": None, "intent": None},
        "voice_prob": 0.0,
        "voice_match_score": 0.0,
        "analyzed": False,
        "transcript": "",
        "step_start_time": time.time(),
        "latency_risks": []  # List of {step, hesitation, score}
    }
    
    # Return first question
    first_q = get_next_question(0)
    
    return jsonify({
        "session_id": session_id,
        "message": "Call Started",
        "audio_url": f"/audio/{os.path.basename(first_q['audio_file'])}",
        "next_step": first_q['id']
    })

@app.route('/submit-response', methods=['POST'])
def submit_response():
    """
    Accepts audio chunk.
    Appends to session.
    Checks duration -> Background Analysis.
    Returns next question or Final Report.
    """
    if 'file' not in request.files:
         return jsonify({"error": "No file part"}), 400
         
    file = request.files['file']
    session_id = request.form.get('session_id')
    
    session = sessions.get(session_id)
    if not session:
        return jsonify({"error": "Invalid Session"}), 404
        
    # Save Chunk
    chunk_name = f"temp_{session_id}_{len(session['chunks'])}.wav"
    file.save(chunk_name)
    
    # --- Latency Check (First Chunk Only) ---
    if len(session['chunks']) == 0:
        current_step_id = get_next_question(session['step_index'])['id']
        arrival_time = time.time()
        start_time = session.get('step_start_time', arrival_time)
        prompt_dur = PROMPT_DURATIONS.get(current_step_id, 0.0)
        
        # Determine when prompt ENDED (approx) = Start + Duration
        prompt_end_time = start_time + prompt_dur
        
        r_level, r_score, hesitation = calculate_hesitation_risk(prompt_end_time, arrival_time)
        
        print(f"[Latency] Step: {current_step_id}, Hesitation: {hesitation:.2f}s, Risk: {r_level}", flush=True)
        
        session['latency_risks'].append({
            "step": current_step_id,
            "hesitation": hesitation,
            "score": r_score,
            "level": r_level
        })
        
    session['chunks'].append(chunk_name)
    
    # Merge
    merge_audio_files(session['accumulated_audio'], session['chunks'])
    
    # Check Duration > 10s (Simulated here by number of chunks or actual check)
    # Let's assume frontend sends ~3-4s chunks. Use file size or wave gen
    # Running analysis iteratively is fine too.
    # Trigger analysis in background if not already running heavily?
    # For now, trigger every time to keep state updated.
    
    # Prevent Duplicate Analysis
    if session.get('analyzing'):
        print(f"[Analysis] Skipped: Session {session_id} is busy.")
    else:
        session['analyzing'] = True
        threading.Thread(target=analysis_thread, args=(session_id,)).start()
    
    # Move to next step
    current_index = session['step_index']
    next_index = current_index + 1
    session['step_index'] = next_index
    
    next_q = get_next_question(next_index)
    
    if next_q:
        session['step_start_time'] = time.time() # Reset timer for next step
        return jsonify({
            "status": "continued",
            "audio_url": f"/audio/{os.path.basename(next_q['audio_file'])}",
            "next_step": next_q['id']
        })
    else:
        # End of Flow -> Generate Final Report
        # Wait for analysis thread to finish? Or return what we have?
        # Ideally we wait a bit or the frontend polls. 
        # But user asked to "return report in json format" at last.
        # We will do a synchronous final check here.
        
        # Ensure latest analysis
        analysis_thread(session_id) 
        
        # History
        # History
        # History & Memory Engine
        history = get_recent_calls(session['account_id']) # Legacy history (list of calls)
        mod, explanations = analyze_history(history)
        
        # New Cross-Call Memory (Priority 1)
        phone = session['phone']
        memory_record = get_cross_call_memory(phone)
        
        details = session['extracted_details']
        
        # Compute Stability Scores
        name_score, name_changed = calculate_name_stability(details.get("name"), memory_record)
        dob_score, dob_mismatch = calculate_dob_stability(details.get("dob"), memory_record)
        trust_trend = calculate_trust_trend(50, memory_record) # Current trust passed as placeholder/default for now until updated
        
        otp_success, identity_fails, _ = validate_identity(details["otp"], details["name"], details["dob"])
        
        # Calculate average latency score
        latencies = session.get('latency_risks', [])
        if latencies:
            avg_latency_score = sum(l['score'] for l in latencies) / len(latencies)
        else:
            avg_latency_score = 0.0
            
        risk_data = calculate_risk(
            otp_success=otp_success,
            identity_fails=identity_fails,
            voice_risk="HIGH" if session['voice_prob'] > 0.5 else "LOW",
            intent=details['intent'],
            voice_prob=session['voice_prob'],
            history_modifier=mod,
            country_mismatch=session['country_mismatch'],
            name_stability=name_score,
            dob_stability=dob_score,
            trust_trend=trust_trend,
            latency_score=avg_latency_score
        )
        
        risk_data["voice_match_score"] = session['voice_match_score']
        
        # Prepare Consolidated Record Logic
        from src.database import save_verification_record, is_first_time_caller
        
        # 1. Prepare Data
        verification_data = {
            "call_id": session_id,
            "phone_number": session['phone'],
            "country_code": session.get('country', 'IN'),
            "is_first_time_caller": None, # Let DB determine, or calculate here
            
            # OTP
            "otp_sent": True, # We always send OTP in this flow
            "otp_verified": otp_success,
            "otp_attempts": 1, # Simplified for demo
            
            # Personal Details
            "personal_details": {
                "name": details.get("name"),
                "dob": details.get("dob"),
                "intent": details.get("intent")
            },
            "personal_details_verified": False, # Mock logic: Need real check
            
            # Audio Analysis
            "audio_duration": 0, # Could calc from file size
            "ai_audio_probability": float(session.get('voice_prob', 0.0)),
            
            # Voice Match
            "voice_match_score": float(session.get('voice_match_score', 0.0)),
            "matched_call_id": None, # Would come from Auth logic if implemented fully
            
            # Risk
            "fraud_risk_score": risk_data["risk_percentage"],
            "verification_status": "VERIFIED" if risk_data["final_risk"] == "LOW" else "FAILED"
        }

        # 2. Get Audio Bytes
        audio_bytes = None
        if os.path.exists(session['accumulated_audio']):
            try:
                with open(session['accumulated_audio'], "rb") as f:
                    audio_bytes = f.read()
            except Exception as e:
                print(f"[Audio Read Error] {e}")
        verification_data['audio_bytes'] = audio_bytes
        
        # 3. Save to MongoDB
        saved_record = save_verification_record(verification_data)
        if saved_record:
            verification_data.update(saved_record)
            
            # 4. Update Cross-Call Memory
            # We trust the provided details if verification status is VERIFIED or at least PARTIAL
            # For strictness, let's update if risk is not HIGH. or just track what was claimed.
            # Requirement: "Track name claims across calls"
            
            # Calculate new trust score snapshot (using the calculated score)
            # Default trust is 50, modify by risk? 
            # Simplified: 100 - risk_percentage
            current_trust = 100.0 - risk_data["risk_percentage"]
            
            mem_update = {
                "last_verified_name": details.get("name"),
                "last_verified_dob": details.get("dob"),
                "trust_score": current_trust,
                "call_timestamp": datetime.utcnow()
            }
            update_cross_call_memory(session['phone'], mem_update)

        # 4. Print Terminal Report
        try:
            print("\n" + "="*80, flush=True)
            print("                       🔒 CALL VERIFICATION REPORT", flush=True)
            print("="*80, flush=True)
            print(f"Call ID           : {session_id}", flush=True)
            print(f"Caller            : {session['phone']} (IN)", flush=True)
            print(f"Timestamp         : {datetime.utcnow()}", flush=True)
            print("-"*80, flush=True)
            print("VERIFICATION CHECKS", flush=True)
            print("-"*80, flush=True)
            
            otp_mark = "✅" if otp_success else "❌"
            print(f"[{otp_mark}] OTP Verified           (Attempts: 1)", flush=True)
            
            # Personal Details Check (Mock)
            det_mark = "✅" if details.get("name") else "⚠️"
            print(f"[{det_mark}] Personal Details       (Name: {details.get('name')}, DOB: {details.get('dob')})", flush=True)
            
            # AI Check
            ai_prob = session.get('voice_prob', 0.0)
            ai_percent = ai_prob * 100
            human_percent = 100 - ai_percent
            ai_mark = "✅" if ai_prob < 0.5 else "❌"
            print(f"[{ai_mark}] Live Human Audio       ({human_percent:.1f}% Human / {ai_percent:.1f}% AI)", flush=True)
            
            # Voice Match
            vm_score = session.get('voice_match_score', 0.0)
            vm_percent = vm_score * 100
            vm_mark = "✅" if vm_score > 0.75 else "⚠️"
            msg = "MATCHED" if vm_score > 0.75 else ("FIRST TIME" if vm_score == 1.0 else "NO MATCH")
            print(f"[{vm_mark}] Voice Match            ({vm_percent:.1f}% Match - {msg})", flush=True)
            
            print("-"*80, flush=True)
            print("RISK ASSESSMENT", flush=True)
            print("-"*80, flush=True)
            
            r_score = risk_data["risk_percentage"]
            print(f"Fraud Risk Score  : {r_score} / 100", flush=True)
            print(f"Risk Level        : {risk_data['final_risk']}", flush=True)
            print(f"Risk Level        : {risk_data['final_risk']}", flush=True)
            
            # Print Memory Signals
            print("-"*80, flush=True)
            print("MEMORY SIGNALS", flush=True)
            print("-"*80, flush=True)
            print(f"Name Stability    : {name_score*100:.0f}% {'(Changed)' if name_changed else '(Stable)'}", flush=True)
            print(f"DOB Stability     : {dob_score*100:.0f}% {'(Mismatch)' if dob_mismatch > 0 else '(Stable)'}", flush=True)
            print(f"Trust Trend       : {trust_trend.upper()}", flush=True)
            print(f"Avg Latency Score : {avg_latency_score:.2f} (Hesitation Risk)", flush=True)
            
            print(f"\nSTATUS            : {verification_data['verification_status']}", flush=True)
            print("="*80 + "\n", flush=True)

            # --- LAUNCH GUI POPUP (DETACHED) ---
            import subprocess
            import sys
            
            # Pass relevant data needed for the popup
            # Be careful with quoting for command line
            
            # Sanitise data for JSON (remove bytes)
            gui_safe_data = verification_data.copy()
            if 'audio_bytes' in gui_safe_data: del gui_safe_data['audio_bytes']
            if 'voice_embedding' in gui_safe_data: del gui_safe_data['voice_embedding']
            if 'voice_embedding_bytes' in gui_safe_data: del gui_safe_data['voice_embedding_bytes'] # if present
            
            gui_data = json.dumps(gui_safe_data)
            
            # Launch async
            print(f"[GUI] Launching popup report...", flush=True)
            # Pass current environment (important for DISPLAY)
            env = os.environ.copy()
            subprocess.Popen([sys.executable, "src/show_report.py", gui_data], env=env)

        except Exception as e:
            print(f"[Report Error] {e}", flush=True)
        
        # --- Cleanup Temporary Files ---
        try:
            if os.path.exists(session['accumulated_audio']):
                os.remove(session['accumulated_audio'])
            for chunk_file in session['chunks']:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
            print(f"[Cleanup] Removed temp files for session {session_id}")
        except Exception as e:
            print(f"[Cleanup Warning] {e}")
        
        # Sanitize risk_data for JSON
        for k, v in risk_data.items():
            if hasattr(v, 'item'):
                 risk_data[k] = v.item()
            elif isinstance(v, (np.float32, np.float64)):
                 risk_data[k] = float(v)

        return jsonify({
            "status": "completed",
            "report": risk_data
        })

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory('ivr_audio', filename)

# --- Real-Time Agent Communication ---

AGENT_OUTBOX = {} # Stores pending audio URL for session: {ssid: url}
AGENT_AUDIO_DIR = os.path.join(os.getcwd(), 'agent_audio')
os.makedirs(AGENT_AUDIO_DIR, exist_ok=True)

@app.route('/agent/audio/<path:filename>')
def serve_agent_audio(filename):
    return send_from_directory('agent_audio', filename)

import subprocess

# --- Agent Dashboard Routes ---

@app.route('/dashboard')
def dashboard():
    return send_from_directory('templates', 'dashboard.html')

@app.route('/agent/speak', methods=['POST'])
def agent_speak():
    """
    Agent uploads audio to talk to client.
    """
    try:
        session_id = request.form.get('session_id')
        if not session_id:
            return jsonify({"error": "No session_id"}), 400
            
        if 'file' not in request.files:
            return jsonify({"error": "No file"}), 400
            
        file = request.files['file']
        filename = f"agent_{uuid.uuid4().hex}.wav"
        save_path = os.path.join(AGENT_AUDIO_DIR, filename)
        file.save(save_path)
        
        # Queue it (Store filename only)
        AGENT_OUTBOX[session_id] = filename
        print(f"[{session_id}] Agent Message Queued: {filename}")
        
        # Return URL for the sender (Agent) just for confirmation
        return jsonify({"status": "sent", "url": f"/agent/audio/{filename}"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/client/poll_agent/<session_id>', methods=['GET'])
def poll_agent(session_id):
    """
    Client polls this to see if Agent is speaking.
    """
    if session_id in AGENT_OUTBOX:
        filename = AGENT_OUTBOX.pop(session_id) 
        # Construct URL relative to the Client's view (request.host_url)
        full_url = f"{request.host_url}agent/audio/{filename}"
        return jsonify({"has_audio": True, "audio_url": full_url})
    else:
        return jsonify({"has_audio": False})

@app.route('/agent/api/sessions')
def get_sessions():
    """
    Returns list of active/completed sessions for dashboard.
    """
    session_list = []
    # Sort by time? Dictionary is unordered, but we can just list them.
    for sid, sess in sessions.items():
        # Determine current risk snapshot
        risk_level = "PENDING"
        if sess.get('analyzed'):
            prob = sess.get('voice_prob', 0)
            if prob > 0.5: risk_level = "HIGH"
            elif prob > 0.2: risk_level = "MEDIUM"
            else: risk_level = "LOW"
            
        # Or if final report exists
        status = "IN_PROGRESS"
        
        session_list.append({
            "id": sid,
            "phone": sess.get('phone'),
            "account_id": sess.get('account_id'),
            "risk_level": risk_level,
            "voice_match": int(sess.get('voice_match_score', 0) * 100),
            "status": "ACTIVE", # can refine
            "report_json": None # placeholder
        })
    return jsonify(session_list)

if __name__ == '__main__':
    # Init DB
    try:
        init_db()
    except:
        pass
    # To allow access over Wi-Fi, we must bind to 0.0.0.0
    
    # Suppress heavy polling logs
    import logging
    log = logging.getLogger('werkzeug')
    # Custom filter to mute polling logs
    class PollFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            if "/client/poll_agent/" in msg and " 200 " in msg: return False
            if "/client/wait_for_agent/" in msg and " 404 " in msg: return False
            return True
            
    log.addFilter(PollFilter())
    
    app.run(host='0.0.0.0', port=5001, debug=True)
