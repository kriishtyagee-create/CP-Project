# Smart Attendance System

A comprehensive College Mini Project that uses Face Recognition to automate attendance tracking. Built with Python, Flask, OpenCV, and a modern Web UI.

## Features

- **Role-Based Access Control**: Separate interfaces for Administrators and Students.
- **Student Authentication**: Secure sign-up and login with JWT token-based authentication.
- **Real-Time Face Recognition**: Marks attendance automatically by identifying students via a live webcam feed.
- **Face Registration Workflow**: Easy-to-use interface to capture and register student faces dynamically.
- **Attendance Management**: Includes an Admin dashboard to view, update, and delete attendance records.
- **Student Portal**: Allows students to view their historical attendance records, overall percentage, and independently mark their own attendance via face verification.

## Technology Stack

- **Backend**: Python 3, Flask, SQLAlchemy (SQLite database)
- **Face Recognition**: `opencv-python-headless`, `face_recognition`, `numpy` 
- **Security**: Werkzeug security (password hashing), PyJWT
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, dynamic rendering via Jinja2

## Setup & Installation

### Prerequisites
- Python 3.8+ installed on your system.
- A functional webcam for face capture and recognition.
- Note: The `face_recognition` and underlying `dlib` libraries may require C++ build tools or CMake to compile correctly on some systems.

### Installation Steps

1. **Navigate to the project directory**:
   ```bash
   cd "CP Lab Project"
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # OR
   venv\Scripts\activate     # On Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```
   The server will start on `http://127.0.0.1:5000`. The SQLite database and default users are automatically initialized on the first run.

## Usage Guide

1. Open your browser and navigate to `http://127.0.0.1:5000`.
2. **Default Accounts (for testing)**:
   - **Admin**: Username: `admin`, Password: `admin123`
   - **Student**: Username: `student`, Password: `student123` (Roll No: 101)
3. **Face Registration** (Admin):
   - Login as admin, go to "Register Face".
   - Enter student details and capture 5 different webcam angles.
   - Click "Train Model" to ensure the new faces are loaded contextually.
4. **Mark Attendance**:
   - Go to "Recognize" to open the live webcam feed. Registered students will be identified immediately, and their attendance added to the database.
   - Students can also use the "Mark Attendance" section in their portal to verify their own face using their laptop camera.

## Project Structure
- `app.py`: Main Flask application, background tasks, routing, and REST API definitions.
- `requirements.txt`: Python package dependencies.
- `static/`: Contains frontend assets (`js/`, `css/`) and the `known_faces/` directory where registered student face images are saved.
- `templates/`: Contains all the HTML views and Jinja2 templates.
- `instance/`: Created on runtime, where the SQLite database (`attendance.db`) is stored.
