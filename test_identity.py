
from src.identity_processor import validate_identity, extract_details_from_transcript

def test():
    print("Testing Identity Processor Fuzzy Matching & Extraction...")
    
    # 1. Test failing case from user logs
    # Transcript: "The OTP is 5,646. My name is Mokesh, my date of birth is July 15th. 2005, I want to recover my account."
    print("\n--- Test Case: User Provided Transcript (AI Audio) ---")
    transcript = "The OTP is 5,646. My name is Mokesh, my date of birth is July 15th. 2005, I want to recover my account."
    
    details = extract_details_from_transcript(transcript)
    print(f"Extracted: {details}")
    
    # Assertions
    if details["otp"] == "5646":
        print("PASS: OTP Extracted (5646)")
    else:
        print(f"FAIL: OTP Extracted ({details['otp']}) - Expected 5646")
        
    if details["name"] == "Mukesh":
        print("PASS: Name Extracted (Mukesh from Mokesh)")
    else:
        print(f"FAIL: Name Extracted ({details['name']}) - Expected Mukesh")
        
    if "15" in details["dob"] and "July" in details["dob"]:
        print("PASS: DOB Extracted")
    else:
         print(f"FAIL: DOB Extracted ({details['dob']})")

    # 2. Test Year Confusion (OTP vs 2005)
    # "My otp is 2024" -> Should be 2024? Or ignored?
    # Logic says: skip years unless forced.
    # "OTP is 5646 and year is 2005"
    print("\n--- Test Case: Year vs OTP ---")
    t2 = "My year is 2005 and OTP is 5646"
    d2 = extract_details_from_transcript(t2)
    print(f"Transcript: '{t2}' -> OTP: {d2['otp']}")
    if d2['otp'] == "5646": print("PASS: Correctly picked non-year OTP")
    else: print("FAIL: Picked year?")
    
    # 3. Test Text with Comma
    print("\n--- Test Case: Comma separation ---")
    t3 = "code 5,646"
    d3 = extract_details_from_transcript(t3)
    if d3['otp'] == "5646": print("PASS: Comma removed")
    else: print("FAIL: Comma issue")

if __name__ == "__main__":
    test()
