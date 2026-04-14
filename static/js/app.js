const API_URL = '/api';

// Toast Notification System
function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.className = "show";
    setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
}

// Authentication Handlers
async function login(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('username', data.username);
            localStorage.setItem('role', data.role || 'admin');
            
            showToast('Login successful!');
            setTimeout(() => { 
                if (data.role === 'student') {
                    window.location.href = '/student_dashboard'; 
                } else {
                    window.location.href = '/dashboard'; 
                }
            }, 1000);
        } else {
            showToast(data.message || 'Login failed');
        }
    } catch (error) {
        showToast('Error connecting to server');
        console.error(error);
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    window.location.href = '/';
}

function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
    }
}

function getAuthHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
    };
}

// Attendance Logic
async function fetchAttendance() {
    try {
        const response = await fetch(`${API_URL}/attendance`, {
            headers: getAuthHeaders()
        });
        
        if (response.status === 401) { logout(); return; }
        
        const data = await response.json();
        return data.attendance;
    } catch (error) {
        console.error('Failed to fetch attendance:', error);
        return [];
    }
}

async function markAttendance(event) {
    event.preventDefault();
    const student_name = document.getElementById('student_name').value;
    const roll_number = document.getElementById('roll_number').value;
    const status = document.getElementById('status').value;
    const date = document.getElementById('date').value;

    try {
        const response = await fetch(`${API_URL}/attendance`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({student_name, roll_number, status, date})
        });
        const data = await response.json();
        
        if (response.ok) {
            showToast('Attendance marked!');
            event.target.reset(); // clear form
        } else {
            showToast(data.message || 'Failed to mark attendance');
        }
    } catch (error) {
        showToast('Error connecting to server');
    }
}

async function deleteRecord(id) {
    if(!confirm("Are you sure you want to delete this record?")) return;
    
    try {
        const response = await fetch(`${API_URL}/attendance/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (response.ok) {
            showToast('Record deleted!');
            // Refresh table if on reports page
            if (typeof loadReports === 'function') loadReports();
        } else {
            showToast('Failed to delete');
        }
    } catch (error) {
        showToast('Error');
    }
}

// --- Student Logic ---
async function fetchStudentStats() {
    try {
        const response = await fetch(`${API_URL}/student/stats`, { headers: getAuthHeaders() });
        if (response.status === 401) { logout(); return; }
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch stats:', error);
        return null;
    }
}

async function fetchStudentHistory() {
    try {
        const response = await fetch(`${API_URL}/student/history`, { headers: getAuthHeaders() });
        if (response.status === 401) { logout(); return; }
        const data = await response.json();
        return data.history;
    } catch (error) {
        console.error('Failed to fetch history:', error);
        return [];
    }
}

async function startWebcam() {
    const video = document.getElementById('webcam');
    if (!video) return;
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (err) {
        console.error("Error accessing webcam: ", err);
        showToast("Cannot access webcam. Please allow permissions.");
    }
}

async function captureAndVerifyFace() {
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('canvas');
    if (!video || !canvas) return;

    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const imageData = canvas.toDataURL('image/jpeg');
    const scanBtn = document.getElementById('scan-btn');
    if(scanBtn) {
        scanBtn.disabled = true;
        scanBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning...';
    }

    try {
        const response = await fetch(`${API_URL}/student/verify_face`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ image: imageData })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✅ ' + data.message);
        } else {
            showToast('⚠️ ' + data.message);
        }
    } catch (error) {
        console.error(error);
        showToast('❌ Server Error during verification');
    } finally {
        if(scanBtn) {
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<i class="fa-solid fa-expand"></i> Scan Face & Mark Attendance';
        }
    }
}

// Ensure elements exist before adding listeners
document.addEventListener('DOMContentLoaded', () => {
    // Inject toast UI if not exists
    if (!document.getElementById('toast')) {
        const toastDiv = document.createElement('div');
        toastDiv.id = 'toast';
        document.body.appendChild(toastDiv);
    }

    const loginForm = document.getElementById('login-form');
    if (loginForm) loginForm.addEventListener('submit', login);

    const markForm = document.getElementById('mark-form');
    if (markForm) markForm.addEventListener('submit', markAttendance);

    const scanBtn = document.getElementById('scan-btn');
    if (scanBtn) scanBtn.addEventListener('click', captureAndVerifyFace);

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);
    
    // Auto start webcam if element exists
    if (document.getElementById('webcam')) {
        startWebcam();
    }
});
