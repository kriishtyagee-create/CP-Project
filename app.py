from flask import Flask, request, jsonify, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
import os
import cv2
import face_recognition
import numpy as np
from flask import Response

app = Flask(__name__)
# Enable CORS for potential separate frontend deployment
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'your_secret_key_here_for_project' # Change in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Face Recognition Properties ---
KNOWN_FACES_DIR = os.path.join(app.root_path, 'static', 'known_faces')
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

known_face_encodings = []
known_face_names = []

def load_known_faces():
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    
    if os.path.exists(KNOWN_FACES_DIR):
        for filename in os.listdir(KNOWN_FACES_DIR):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                filepath = os.path.join(KNOWN_FACES_DIR, filename)
                parts = filename.split('_')
                name_part = parts[0]
                roll_part = parts[1] if len(parts) > 1 else 'Unknown'
                identifier = f"{name_part} ({roll_part})"
                
                try:
                    img = face_recognition.load_image_file(filepath)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        known_face_encodings.append(encodings[0])
                        known_face_names.append(identifier)
                except Exception as e:
                    print(f"Error loading {filepath}: {e}")
    print(f"Loaded {len(known_face_encodings)} face encodings.")

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)
    roll_number = db.Column(db.String(50), nullable=True)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False) # 'Present', 'Absent', 'Late'
    date = db.Column(db.String(20), nullable=False) # Storing as string YYYY-MM-DD for simplicity

# --- Auth Decorator ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check headers for token
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# --- Frontend Routes (HTML Views) ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/mark')
def mark_page():
    return render_template('mark.html')

@app.route('/reports')
def reports_page():
    return render_template('reports.html')

@app.route('/register_face_page')
def register_face_page():
    return render_template('register_face.html')

@app.route('/recognize_page')
def recognize_page():
    return render_template('recognize.html')

@app.route('/student_dashboard')
def student_dashboard_page():
    return render_template('student_dashboard.html')

@app.route('/student_mark')
def student_mark_page():
    return render_template('student_mark.html')

@app.route('/student_history')
def student_history_page():
    return render_template('student_history.html')




# --- REST API Endpoints ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Could not verify'}), 401

    user = User.query.filter_by(username=data.get('username')).first()

    if not user:
        return jsonify({'message': 'User not found'}), 401

    if check_password_hash(user.password_hash, data.get('password')):
        # Generate JWT Token
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            'token': token, 
            'username': user.username,
            'role': user.role,
            'roll_number': user.roll_number
        })

    return jsonify({'message': 'Wrong password'}), 401

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('roll_number'):
        return jsonify({'message': 'Missing data fields'}), 400

    username = data.get('username')
    
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists'}), 400
        
    roll_number = data.get('roll_number')

    hashed_pw = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
    new_user = User(
        username=username,
        password_hash=hashed_pw,
        role='student',
        roll_number=roll_number
    )
    
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Student created successfully!'}), 201

@app.route('/api/attendance', methods=['GET'])
@token_required
def get_attendance(current_user):
    records = Attendance.query.all()
    output = []
    for record in records:
        record_data = {
            'id': record.id,
            'student_name': record.student_name,
            'roll_number': record.roll_number,
            'status': record.status,
            'date': record.date
        }
        output.append(record_data)
    
    return jsonify({'attendance': output})

@app.route('/api/attendance', methods=['POST'])
@token_required
def mark_attendance(current_user):
    data = request.get_json()
    
    # Simple validation
    if not all(key in data for key in ('student_name', 'roll_number', 'status', 'date')):
        return jsonify({'message': 'Missing data fields!'}), 400

    new_record = Attendance(
        student_name=data['student_name'],
        roll_number=data['roll_number'],
        status=data['status'],
        date=data['date']
    )
    
    db.session.add(new_record)
    db.session.commit()
    
    return jsonify({'message': 'Attendance marked successfully!'}), 201

@app.route('/api/attendance/<int:id>', methods=['PUT'])
@token_required
def update_attendance(current_user, id):
    record = Attendance.query.get(id)
    if not record:
        return jsonify({'message': 'Record not found!'}), 404

    data = request.get_json()
    
    if 'student_name' in data: record.student_name = data['student_name']
    if 'roll_number' in data: record.roll_number = data['roll_number']
    if 'status' in data: record.status = data['status']
    if 'date' in data: record.date = data['date']
    
    db.session.commit()
    return jsonify({'message': 'Record updated successfully!'})

@app.route('/api/attendance/<int:id>', methods=['DELETE'])
@token_required
def delete_attendance(current_user, id):
    record = Attendance.query.get(id)
    if not record:
        return jsonify({'message': 'Record not found!'}), 404
        
    db.session.delete(record)
    db.session.commit()
    
    return jsonify({'message': 'Record deleted successfully!'})

# --- Student Specific API Endpoints ---
@app.route('/api/student/stats', methods=['GET'])
@token_required
def student_stats(current_user):
    if current_user.role != 'student':
        return jsonify({'message': 'Unauthorized'}), 403
    
    roll = current_user.roll_number
    records = Attendance.query.filter_by(roll_number=roll).all()
    # Mocking total classes held to be a bit random for demonstration, or static
    # e.g., Assume 40 classes held in total
    total_classes = 40
    attended = len([r for r in records if r.status == 'Present'])
    percentage = (attended / total_classes * 100) if total_classes > 0 else 0

    return jsonify({
        'totalClasses': total_classes,
        'classesAttended': attended,
        'attendancePercentage': round(percentage, 1)
    })

@app.route('/api/student/history', methods=['GET'])
@token_required
def student_history(current_user):
    if current_user.role != 'student':
        return jsonify({'message': 'Unauthorized'}), 403
    
    roll = current_user.roll_number
    records = Attendance.query.filter_by(roll_number=roll).order_by(Attendance.id.desc()).all()
    output = []
    for record in records:
        output.append({
            'id': record.id,
            'status': record.status,
            'date': record.date
        })
    return jsonify({'history': output})

import base64

@app.route('/api/student/verify_face', methods=['POST'])
@token_required
def student_verify_face(current_user):
    if current_user.role != 'student':
        return jsonify({'message': 'Unauthorized access'}), 403
    
    data = request.get_json()
    image_data = data.get('image')
    if not image_data:
        return jsonify({'success': False, 'message': 'No image data provided'}), 400

    try:
        # Extract base64 part
        encoded_data = image_data.split(',')[1] if ',' in image_data else image_data
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to RGB for face_recognition
        rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if not face_locations:
            return jsonify({'success': False, 'message': 'Face Not Recognized (No face found in frame)'}), 400

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            
            if True in matches:
                first_match_index = matches.index(True)
                name = known_face_names[first_match_index]
                
                if '(' in name:
                    roll_number = name.split(' (')[1].replace(')', '')
                    student_name = name.split(' (')[0]
                    
                    if roll_number != current_user.roll_number:
                        return jsonify({'success': False, 'message': 'Face does not match logged-in student.'}), 403
                    
                    today_str = str(datetime.date.today())
                    existing = Attendance.query.filter_by(roll_number=roll_number, date=today_str).first()
                    
                    if existing:
                        return jsonify({'success': False, 'message': 'Already Marked Today'}), 200
                        
                    new_record = Attendance(
                        student_name=student_name,
                        roll_number=roll_number,
                        status="Present",
                        date=today_str
                    )
                    db.session.add(new_record)
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Attendance Marked Successfully'})

        return jsonify({'success': False, 'message': 'Face Not Recognized (Not registered)'}), 400
        
    except Exception as e:
        print(f"Error scanning face: {e}")
        return jsonify({'success': False, 'message': 'Server error while processing image'}), 500


@app.route('/api/register_face', methods=['POST'])
@token_required
def api_register_face(current_user):
    data = request.get_json()
    student_name = data.get('student_name')
    roll_number = data.get('roll_number')

    if not student_name or not roll_number:
        return jsonify({'message': 'Missing data'}), 400

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return jsonify({'message': 'Could not open webcam'}), 500

    count = 0
    max_images = 5
    
    while count < max_images:
        ret, frame = cap.read()
        if not ret:
            break
        
        rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if face_locations:
            filename = f"{student_name}_{roll_number}_{count}.jpg"
            filepath = os.path.join(KNOWN_FACES_DIR, filename)
            cv2.imwrite(filepath, frame)
            count += 1
            cv2.waitKey(200)

    cap.release()
    
    if count == 0:
        return jsonify({'message': 'No faces detected. Please try again.'}), 400
        
    return jsonify({'message': f'Successfully captured {count} images. Please Train Model next.'})

@app.route('/api/train_model', methods=['POST'])
@token_required
def api_train_model(current_user):
    load_known_faces()
    return jsonify({'message': 'Model trained successfully'})

def gen_frames():
    cap = cv2.VideoCapture(0)
    with app.app_context():
        while True:
            success, frame = cap.read()
            if not success:
                break
                
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            face_names = []
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"
                
                if True in matches:
                    first_match_index = matches.index(True)
                    name = known_face_names[first_match_index]
                    
                    if '(' in name:
                        student_name = name.split(' (')[0]
                        roll_number = name.split(' (')[1].replace(')', '')
                        
                        today_str = str(datetime.date.today())
                        existing = Attendance.query.filter_by(roll_number=roll_number, date=today_str).first()
                        if not existing:
                            new_record = Attendance(
                                student_name=student_name,
                                roll_number=roll_number,
                                status="Present",
                                date=today_str
                            )
                            db.session.add(new_record)
                            db.session.commit()

                face_names.append(name)
                
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                   
    if cap.isOpened():
        cap.release()

@app.route('/api/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Database Initialization ---
def init_db():
    with app.app_context():
        # Drop all to easily migrate our test schema
        db.drop_all()
        db.create_all()
        
        hashed_pw_admin = generate_password_hash('admin123', method='pbkdf2:sha256')
        admin = User(username='admin', password_hash=hashed_pw_admin, role='admin')
        db.session.add(admin)
        
        # Add a student user for dummy testing. Password: student123
        hashed_pw_student = generate_password_hash('student123', method='pbkdf2:sha256')
        student1 = User(username='student', password_hash=hashed_pw_student, role='student', roll_number="101")
        student2 = User(username='bob', password_hash=hashed_pw_student, role='student', roll_number="102")
        db.session.add_all([student1, student2])
        
        # Add some dummy attendance data for demonstration
        dummy_records = [
            Attendance(student_name="Student User", roll_number="101", status="Present", date=str(datetime.date.today())),
            Attendance(student_name="Bob Jones", roll_number="102", status="Absent", date=str(datetime.date.today() - datetime.timedelta(days=1))),
            Attendance(student_name="Charlie Brown", roll_number="103", status="Present", date=str(datetime.date.today()))
        ]
        db.session.bulk_save_objects(dummy_records)
        db.session.commit()
        print("Database initialized with admin and dummy student users.")

if __name__ == '__main__':
    # Initialize DB on start
    init_db()
    
    # Load known faces from filesystem on startup
    print("Loading known faces...")
    load_known_faces()
    
    app.run()
