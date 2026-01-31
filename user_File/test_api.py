import requests
import sys

def test_api(filepath):
    url = 'http://localhost:5001/analyze'
    
    print(f"Testing {url} with {filepath}...")
    
    try:
        with open(filepath, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
            
        print(f"Status: {response.status_code}")
        print("Response:", response.json())
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <audio_file>")
        sys.exit(1)
        
    test_api(sys.argv[1])
