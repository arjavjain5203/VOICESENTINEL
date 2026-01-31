import requests
import pyaudio
import wave
import threading
import time
import os
import sys
import json
import tkinter as tk
from tkinter import messagebox

# Ensure DISPLAY for Linux
if os.environ.get('DISPLAY','') == '':
    # Only if truly missing, but user usually has it if launching server locally
    # print('no display found. Using :0.0')
    # os.environ.__setitem__('DISPLAY', ':0.0')
    pass

SERVER_URL = "http://localhost:5001" 

def record_audio(filename, duration=5, status_label=None):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100 
    
    p = pyaudio.PyAudio()
    if status_label: status_label.config(text=f"Recording {duration}s... Speak Now!", fg="red")
    root_update()
    
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        if status_label: status_label.config(text=f"Mic Error: {e}", fg="red")
        return False
    
    frames = []
    # Non-blocking loop not possible easily without threading, but 5s is short
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        if i % 10 == 0: root_update() # Keep UI alive
        
    if status_label: status_label.config(text="Sending...", fg="#111")
    root_update()
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    return True

root_tk = None
def root_update():
    if root_tk: root_tk.update()

def send_reply(session_id, status_label):
    def _run():
        filename = "temp_agent_reply.wav"
        if record_audio(filename, duration=5, status_label=status_label):
            try:
                with open(filename, 'rb') as f:
                    r = requests.post(f"{SERVER_URL}/agent/speak", 
                                      data={"session_id": session_id},
                                      files={"file": f}) # server expects 'file' not 'audio' per Step 1326
                    
                if r.status_code == 200:
                    status_label.config(text="✅ Reply Sent!", fg="green")
                else:
                    status_label.config(text=f"❌ Send Failed: {r.status_code}", fg="red")
            except Exception as e:
                status_label.config(text=f"Error: {e}", fg="red")
                
            if os.path.exists(filename):
                os.remove(filename)
        else:
             if status_label: status_label.config(text="Recording Failed", fg="red")
             
    threading.Thread(target=_run).start()

def show_popup(report_json):
    global root_tk
    # ... (omitted logs) ...
    try:
        data = json.loads(report_json)
    except:
        return

    root = tk.Tk()
    root_tk = root
    root.title(f"Voice Sentinel - {data.get('phone_number', 'Unknown')}")
    
    # Dimensions
    w, h = 500, 600 # Increased Height for Reply Button
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    root.configure(bg="#f0f0f0")

    # Header
    status = data.get('verification_status', 'UNKNOWN')
    risk_score = data.get('fraud_risk_score', 0)
    
    header_color = "#2e7d32" if status == "VERIFIED" else ("#d32f2f" if status == "High Risk" else "#f57c00")
    lbl_header = tk.Label(root, text=status, font=("Helvetica", 24, "bold"), bg=header_color, fg="white", pady=20)
    lbl_header.pack(fill=tk.X)

    # Content Frame
    frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    def add_row(label, value, color="black"):
        row = tk.Frame(frame, bg="#f0f0f0", pady=5)
        row.pack(fill=tk.X)
        tk.Label(row, text=label, font=("Helvetica", 12, "bold"), bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        tk.Label(row, text=str(value), font=("Helvetica", 12), bg="#f0f0f0", fg=color, anchor="w").pack(side=tk.LEFT)

    # Details
    call_id = data.get('call_id', 'N/A')
    add_row("Phone Number:", data.get('phone_number', 'Unknown'))
    add_row("Call ID:", call_id[:8] + "...")
    
    # Metrics
    tk.Label(frame, text="", bg="#f0f0f0").pack() 
    
    ai_prob = data.get('ai_audio_probability', 0.0)
    human_pct = 100 - (ai_prob * 100)
    add_row("Audio Source:", f"{human_pct:.1f}% Human", color="#2e7d32" if ai_prob < 0.5 else "#d32f2f")
    
    vm_score = data.get('voice_match_score', 0.0)
    add_row("Voice Match:", f"{vm_score*100:.1f}% Match", color="#2e7d32" if vm_score > 0.75 else "#d32f2f")
    
    tk.Label(frame, text="", bg="#f0f0f0").pack() 
    add_row("Risk Score:", f"{risk_score} / 100", color="#d32f2f" if risk_score > 50 else "#2e7d32")

    # --- Talk Back Feature ---
    tk.Label(frame, text="Two-Way Communication", font=("Helvetica", 10, "bold"), bg="#f0f0f0", pady=10).pack()
    
    status_lbl = tk.Label(frame, text="Ready to Reply", font=("Helvetica", 10), bg="#f0f0f0", fg="gray")
    status_lbl.pack()
    
    # Use full Call ID for reply
    btn_reply = tk.Button(frame, text="🎙️ Reply to Caller (5s)", 
                          command=lambda: send_reply(call_id, status_lbl), 
                          bg="#1976d2", fg="white", font=("Helvetica", 12, "bold"), padx=10, pady=5)
    btn_reply.pack(pady=5)

    # Close Button
    tk.Button(root, text="Close Report", command=root.destroy, bg="#555", fg="white", font=("Helvetica", 10)).pack(side=tk.BOTTOM, pady=20)

    root.lift()
    root.attributes('-topmost',True)
    root.after_idle(root.attributes,'-topmost',False)
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Join all args as JSON might contain spaces
        json_str = " ".join(sys.argv[1:])
        show_popup(json_str)
