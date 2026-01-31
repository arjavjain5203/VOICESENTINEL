// --- Configuration ---
let SERVER_URL = "http://localhost:5001";
let SESSION_ID = null;

// --- State ---
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let pollingInterval;

// --- Elements ---
const views = {
    setup: document.getElementById('view-setup'),
    call: document.getElementById('view-call'),
    handover: document.getElementById('view-handover')
};

const inputs = {
    phone: document.getElementById('input-phone'),
    account: document.getElementById('input-account'),
    server: document.getElementById('input-server')
};

const callUI = {
    status: document.getElementById('call-status'),
    subtext: document.getElementById('call-subtext'),
    timer: document.getElementById('call-timer'),
    btn: document.getElementById('btn-record-toggle'),
    btnText: document.getElementById('btn-text'),
    dot: document.getElementById('rec-dot'),
    dotPing: document.getElementById('rec-dot-ping'),
    visualizer: document.getElementById('visualizer'),
    avatarRing: document.getElementById('avatar-ring')
};

// --- Setup ---
document.getElementById('setup-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Config
    SERVER_URL = inputs.server.value.replace(/\/$/, ""); // trim slash
    const phone = inputs.phone.value.trim();
    const account = inputs.account.value.trim();

    // Switch View
    switchView('call');
    updateStatus("Connecting...", "Establishing secure handshake");

    try {
        // Start Call
        const res = await fetch(`${SERVER_URL}/start-call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone: phone,
                account_id: account,
                country: 'IN' // Defaulting
            })
        });

        const data = await res.json();

        if (data.session_id) {
            SESSION_ID = data.session_id;
            console.log("Session Started:", SESSION_ID);
            updateStatus("Connected", "Listening for instructions...");

            // Auto-play first audio
            if (data.audio_url) {
                await playAudio(data.audio_url);
            }
        } else {
            throw new Error(data.error || "Failed to start");
        }

    } catch (err) {
        console.error(err);
        alert(`Connection Failed: ${err.message}`);
        switchView('setup');
    }
});

document.getElementById('btn-end').addEventListener('click', () => {
    if (confirm("End current session?")) {
        location.reload();
    }
});

// --- Recording Logic ---
callUI.btn.addEventListener('click', toggleRecording);

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = submitResponse;

        mediaRecorder.start();
        isRecording = true;

        // UI Updates
        updateRecordingUI(true);

    } catch (err) {
        console.error("Mic Access Error:", err);
        alert("Microphone access is required.");
    }
}

async function stopRecording() {
    if (!mediaRecorder) return;
    mediaRecorder.stop();
    isRecording = false;
    updateRecordingUI(false);
}

function updateRecordingUI(recording) {
    if (recording) {
        callUI.btnText.innerText = "Stop & Send";
        callUI.btn.classList.replace('bg-indigo-600', 'bg-red-500');
        callUI.btn.classList.replace('hover:bg-indigo-700', 'hover:bg-red-600');
        callUI.dot.classList.replace('bg-white/50', 'bg-red-500');
        callUI.dotPing.classList.remove('hidden');
        callUI.avatarRing.style.opacity = "1";
        callUI.avatarRing.style.animation = "pulse-soft 1.5s infinite";

        animateVisualizer(true);
    } else {
        callUI.btnText.innerText = "Start Speaking";
        callUI.btn.classList.replace('bg-red-500', 'bg-indigo-600');
        callUI.btn.classList.replace('hover:bg-red-600', 'hover:bg-indigo-700');
        callUI.dot.classList.replace('bg-red-500', 'bg-white/50');
        callUI.dotPing.classList.add('hidden');
        callUI.avatarRing.style.opacity = "0";
        callUI.avatarRing.style.animation = "none";

        animateVisualizer(false);
    }
}

async function submitResponse() {
    updateStatus("Processing...", "Analyzing voice patterns");
    callUI.btn.disabled = true;

    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append('file', audioBlob, 'response.wav');
    formData.append('session_id', SESSION_ID);

    try {
        const res = await fetch(`${SERVER_URL}/submit-response`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (data.status === 'continued') {
            updateStatus("Listening...", "Waiting for input");
            if (data.audio_url) {
                await playAudio(data.audio_url);
            }
        } else if (data.status === 'completed') {
            enterHandoverMode();
        }

    } catch (err) {
        console.error("Submission Error", err);
        alert("Failed to send response");
    } finally {
        callUI.btn.disabled = false;
    }
}

// --- Audio Playback ---
function playAudio(url) {
    return new Promise((resolve) => {
        updateStatus("Sentinel Speaking", "Secure Voice Output");
        animateVisualizer(true, 'blue'); // Different color/style for playback?

        const fullUrl = url.startsWith("http") ? url : `${SERVER_URL}${url}`;
        const audio = new Audio(fullUrl);

        audio.onended = () => {
            animateVisualizer(false);
            updateStatus("Your Turn", "Press button to speak");
            resolve();
        };

        audio.onerror = (e) => {
            console.error("Playback Error", e);
            animateVisualizer(false);
            resolve();
        }

        audio.play().catch(e => {
            console.warn("Autoplay blocked?", e);
            resolve();
        });
    });
}

// --- Handover Mode ---
function enterHandoverMode() {
    switchView('handover');

    // Start polling for agent audio
    pollingInterval = setInterval(pollAgent, 2000);
}

async function pollAgent() {
    try {
        const res = await fetch(`${SERVER_URL}/client/poll_agent/${SESSION_ID}`);
        if (res.status === 200) {
            const data = await res.json();
            if (data.has_audio && data.audio_url) {
                // Determine URL (Handle Localhost relative vs absolute)
                // If the backend returns a full URL using its internal knowledge, we might need to adjust if proxied.
                // But server logic uses request.host_url so it should be fine.

                const agentMsgBox = document.getElementById('agent-msg-box');
                agentMsgBox.innerHTML = `<button onclick="playAudio('${data.audio_url}')" class="px-4 py-2 bg-indigo-100 text-indigo-700 rounded-lg flex items-center gap-2"><i data-lucide="play"></i> Play Message from Agent</button>`;

                // Optional: Auto Play
                playAudio(data.audio_url);
            }
        }
    } catch (e) {
        // Silent fail
    }
}


// --- Utilities ---
function switchView(viewName) {
    Object.values(views).forEach(el => el.classList.add('hidden'));
    views[viewName].classList.remove('hidden');

    // Reset timer on call start
    if (viewName === 'call') startTimer();
}

function updateStatus(title, subtitle) {
    callUI.status.innerText = title;
    callUI.subtext.innerText = subtitle;
}

let timerInt;
function startTimer() {
    clearInterval(timerInt);
    let sec = 0;
    timerInt = setInterval(() => {
        sec++;
        const m = Math.floor(sec / 60).toString().padStart(2, '0');
        const s = (sec % 60).toString().padStart(2, '0');
        callUI.timer.innerText = `${m}:${s}`;
    }, 1000);
}

let vizInt;
function animateVisualizer(active, color = 'default') {
    clearInterval(vizInt);
    const bars = document.querySelectorAll('.visualizer-bar');

    if (!active) {
        bars.forEach(b => b.style.height = '10px');
        return;
    }

    vizInt = setInterval(() => {
        bars.forEach(b => {
            const h = Math.floor(Math.random() * 30) + 10;
            b.style.height = `${h}px`;
        });
    }, 100);
}