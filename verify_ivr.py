import subprocess
import time
import requests
import os
import signal
import sys

SERVER_URL = "http://localhost:5001"

def wait_for_server():
    for i in range(30):
        try:
            resp = requests.get(f"{SERVER_URL}/health")
            if resp.status_code == 200:
                print(f"Server is up! (Attempt {i+1})")
                return True
        except:
            time.sleep(1)
            print(f"Waiting for server... ({i+1}/30)")
    return False

def run_test():
    # Start Server
    print("Starting Server...")
    # Use unbuffered output to see logs
    process = subprocess.Popen([sys.executable, "calling_agent/server.py"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
    
    try:
        if not wait_for_server():
            print("Server failed to start.")
            process.kill()
            stdout, stderr = process.communicate()
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return

        # 1. Start Call
        print("\n[Test] Starting Call...")
        payload = {"phone": "+919876543210", "country": "IN", "account_id": "TEST_USER_IVR"}
        resp = requests.post(f"{SERVER_URL}/start-call", json=payload)
        print("Start Response:", resp.json())
        assert resp.status_code == 200
        session_id = resp.json()['session_id']
        
        # 2. Submit Response (Mock Audio)
        print(f"\n[Test] Submitting Response for Session {session_id}...")
        
        # Use existing legit.wav as a "chunk"
        # Ensure it exists
        if not os.path.exists("calling_agent/legit.wav"):
             # dummy create if missing (though verify steps before created it)
             with open("calling_agent/legit.wav", "wb") as f:
                 f.write(b"RIFF....WAVEfmt ....data....") 
        
        with open("calling_agent/legit.wav", "rb") as f:
            files = {'file': f}
            data = {'session_id': session_id}
            resp = requests.post(f"{SERVER_URL}/submit-response", files=files, data=data)
            
        print("Submit Response:", resp.json())
        assert resp.status_code == 200
        
        # 3. Submit Final Response (Simulate end)
        # To trigger 'completed', we need to loop through steps.
        # Flow has 4 steps. Step 0 (Start) -> Resp 1 (After OTP) -> Resp 2 (Name) -> Resp 3 (DOB) -> Resp 4 (Intent) -> Done
        # Current index in server starts at 0.
        # start-call -> returns step 0 (welcome_otp)
        # submit-resp -> increments to 1 (ask_name), returns next_step=ask_name
        
        # Loop until done
        step = 0
        while step < 4:
            print(f"\n[Test] Sending Answer for Step {step}...")
            with open("calling_agent/legit.wav", "rb") as f:
                files = {'file': f}
                data = {'session_id': session_id}
                resp = requests.post(f"{SERVER_URL}/submit-response", files=files, data=data)
                
            json_resp = resp.json()
            print(f"Step {step} Response: {json_resp}")
            
            if json_resp.get("status") == "completed":
                print("IVR Flow Completed!")
                report = json_resp.get("report")
                print("Final Report Risk:", report["final_risk"])
                break
            step += 1
            time.sleep(1) # simulate user delay

    finally:
        print("\nStopping Server...")
        process.terminate()
        try:
            outs, errs = process.communicate(timeout=5)
            print("Server Output:\n", outs)
            print("Server Errors:\n", errs)
        except:
             process.kill()

if __name__ == "__main__":
    run_test()
