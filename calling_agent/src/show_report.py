import tkinter as tk
from tkinter import messagebox
import argparse
import json
import sys
import os

# Ensure DISPLAY for Linux
if os.environ.get('DISPLAY','') == '':
    print('no display found. Using :0.0')
    os.environ.__setitem__('DISPLAY', ':0.0')

def show_popup(report_json):
    # Debug Log
    try:
        with open("gui_debug.log", "a") as f:
            f.write(f"Popup Start...\n")
    except:
        pass
        
    try:
        data = json.loads(report_json)
    except:
        print("Invalid JSON")
        return

    # Debug Log
    with open("gui_debug.log", "a") as f:
        f.write(f"Popup Triggered: {data.get('call_id')}\n")

    root = tk.Tk()
    root.title(f"Voice Sentinel - {data.get('phone_number', 'Unknown')}")
    
    # Dimensions & Center
    w, h = 500, 480
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
    header_text = f"{status}"
    
    lbl_header = tk.Label(root, text=header_text, font=("Helvetica", 24, "bold"), bg=header_color, fg="white", pady=20)
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
    if call_id and len(call_id) > 8: call_id = call_id[:8] + "..."
    
    add_row("Phone Number:", data.get('phone_number', 'Unknown'))
    add_row("Call ID:", call_id)
    
    # Metrics
    tk.Label(frame, text="", bg="#f0f0f0").pack() # Spacer
    
    # AI Score
    ai_prob = data.get('ai_audio_probability', 0.0)
    ai_pct = ai_prob * 100
    human_pct = 100 - ai_pct
    add_row("Audio Source:", f"{human_pct:.1f}% Human", color="#2e7d32" if ai_prob < 0.5 else "#d32f2f")
    
    # Voice Match
    vm_score = data.get('voice_match_score', 0.0)
    vm_is_first = data.get('is_first_time_caller', False)
    
    if vm_is_first and vm_score == 1.0:
         vm_text = "First Time Caller (Enrolled)"
         vm_color = "#1976d2"
    else:
         vm_text = f"{vm_score*100:.1f}% Match"
         vm_color = "#2e7d32" if vm_score > 0.75 else "#d32f2f"
         
    add_row("Voice Match:", vm_text, color=vm_color)
    
    # Risk
    tk.Label(frame, text="", bg="#f0f0f0").pack() # Spacer
    add_row("Risk Score:", f"{risk_score} / 100", color="#d32f2f" if risk_score > 50 else "#2e7d32")

    # Close Button
    btn = tk.Button(root, text="Close Report", command=root.destroy, bg="#555", fg="white", font=("Helvetica", 10))
    btn.pack(pady=10)

    # Bring to front
    root.lift()
    root.attributes('-topmost',True)
    root.after_idle(root.attributes,'-topmost',False)
    
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Join all args as JSON might contain spaces
        json_str = " ".join(sys.argv[1:])
        show_popup(json_str)
    else:
        print("No data provided")
