# VoiceSentinel API Documentation

Base URL: `https://voicesentinel-1.onrender.com`

## 1. Analyze Audio
Upload an audio file (10s recommended) to detect if it's AI-generated.

- **Endpoint**: `/analyze`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

### Request Body
| Key | Type | Description |
|-----|------|-------------|
| `file` | File | Audio file (`.wav`, `.mp3`, `.ogg`, `.flac`) |

### Response (Success - 200 OK)
```json
{
  "label": "AI",          // "AI" or "HUMAN"
  "confidence": 0.9926,   // Probability (0.0 to 1.0)
  "is_ai": true           // Boolean flag
}
```

### Example (JavaScript/Fetch)
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('https://voicesentinel-1.onrender.com/analyze', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log(data);
    if (data.is_ai) {
        alert(`Warning: AI Voice Detected! (${(data.confidence * 100).toFixed(1)}%)`);
    } else {
        alert("Voice seems Human.");
    }
})
.catch(error => console.error('Error:', error));
```

## 2. Health Check
Check if the the API is running and models are loaded.

- **Endpoint**: `/health`
- **Method**: `GET`

### Response
```json
{
  "status": "ok",
  "models_loaded": true
}
```
