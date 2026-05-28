from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import re
import cv2
from flask import Response
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))
from posture_detector import PostureDetector
import datetime
import json
from collections import Counter
import time

app = Flask(__name__)
app.secret_key = '1122'

# ---------------------------
# Posture Detection Setup
# ---------------------------
detector = PostureDetector()
camera = cv2.VideoCapture(1)  # 1 = DroidCam usually

if not camera.isOpened():
    print("Camera NOT opened")
else:
    print("Camera opened successfully")

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# ---------------------------
# Database Connection
# ---------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",          # add password if required
        database="alignmatrix",    # change to your GEONEX database name
        port=3307             # change if needed
    )

# ---------------------------
# HOME PAGE
# ---------------------------
@app.route('/')
def index():
    return render_template('index.html')

# ---------------------------
# ABOUT PAGE
# ---------------------------
@app.route('/about')
def about():
    return render_template('about.html')

# ---------------------------
# METHODOLOGY PAGE
# ---------------------------
@app.route('/methodology')
def methodology():
    return render_template('methodology.html')

# ---------------------------
# SIGN UP
# ---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['uname']
        email = request.form['email']
        password = request.form['password']

        # Basic validation
        if not uname.strip():
            flash("Username is required", "danger")
            return redirect(url_for('register'))

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email address", "danger")
            return redirect(url_for('register'))

        if len(password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check existing email
        cursor.execute("SELECT u_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("Email already registered", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('register'))

        # Insert user
        cursor.execute(
            "INSERT INTO users (uname, email, password) VALUES (%s, %s, %s)",
            (uname, email, hashed_password)
        )
        conn.commit()

        cursor.close()
        conn.close()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# ---------------------------
# LOGIN
# ---------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email address", "danger")
            return redirect(url_for('login'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['u_id']
            session['username'] = user['uname']
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

# ---------------------------
# LOGOUT 
# ---------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------
# DETECT PAGE
# ---------------------------
@app.route('/detect')
def detect():
    return render_template('detect.html')

@app.route('/report', methods=['GET', 'POST'])
def report():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    logs = []
    searched = False
    most_frequent_issue = None
    average_risk = 0  # Still defined but set to 0 to prevent UnboundLocalError
    repetition_percentage = 0  # new percentage metric
    recommendation = None

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        searched = True

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT * FROM posture_logs
            WHERE user_id = %s
            AND DATE(recorded_at) BETWEEN %s AND %s
            ORDER BY recorded_at DESC
        """

        cursor.execute(query, (session['user_id'], start_date, end_date))
        logs = cursor.fetchall()

        cursor.close()
        conn.close()

        if logs:

            # -------- Parse DB Issue Arrays --------
            # Every valid log has a comma-separated string format: "Issue A, Issue B, Issue C"
            all_valid_issues = []
            for log in logs:
                raw_issues = log['issue_type']
                if raw_issues not in ["GOOD POSTURE", "No Person Detected", "Not Enough Landmarks Visible"]:
                    # Split string by commas into individual issues and clean whitespace
                    individual_issues = [iss.strip() for iss in raw_issues.split(',') if iss.strip()]
                    all_valid_issues.extend(individual_issues)

            # -------- Calculate Top Frequency & Percentage --------
            if all_valid_issues:
                issue_count = Counter(all_valid_issues)
                most_frequent_issue = issue_count.most_common(1)[0][0]
                most_frequent_count = issue_count.most_common(1)[0][1]
                total_issue_count = len(all_valid_issues)
                
                repetition_percentage = round((most_frequent_count / total_issue_count) * 100, 1)
            else:
                most_frequent_issue = "GOOD POSTURE" if logs else None
                repetition_percentage = 0

            # -------- Average Risk (Deprecated) --------
            # Disabled calculation since it's removed from database. Keep it 0.
            average_risk = 0

            # -------- Load Recommendation JSON --------
            recommendation = None
            with open('data/posture_recommendations.json', 'r') as f:
                recommendations_data = json.load(f)

            if most_frequent_issue in recommendations_data:
                recommendation = recommendations_data[most_frequent_issue]
            else:
                try:
                    with open('data/posture_recommendations2.json', 'r') as f2:
                        rec2 = json.load(f2)
                    if most_frequent_issue in rec2:
                        recommendation = rec2[most_frequent_issue]
                except Exception:
                    pass

    return render_template(
        'report.html',
        logs=logs,
        searched=searched,
        most_frequent_issue=most_frequent_issue,
        repetition_percentage=repetition_percentage,
        recommendation=recommendation
    )

@app.route('/video_feed')
def video_feed():
    global camera_active, last_saved_time

    if 'user_id' not in session:
        return redirect(url_for('login'))

    camera_active = True
    last_saved_time = datetime.datetime.now()

    user_id = session['user_id']   # GET USER ID HERE

    return Response(generate_frames(user_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
@app.route('/live_detection')
def live_detection():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('live_detection.html')

@app.route('/stop_camera')
def stop_camera():
    global camera_active
    camera_active = False
    return redirect(url_for('detect'))

camera_active = False
last_saved_time = None

def save_posture_log(user_id, issue, posture):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO posture_logs (user_id, issue_type, posture_type)
            VALUES (%s, %s, %s)
        """, (user_id, issue, posture))

        conn.commit()
        cursor.close()
        conn.close()

        print("Posture saved to DB")

    except Exception as e:
        print("DB Insert Error:", e)

def generate_frames(user_id):
    global camera_active, last_saved_time

    while camera_active:
        success, frame = camera.read()
        if not success:
            break

        # REMOVE flip if you don't want mirror
        # frame = cv2.flip(frame, 1)

        frame, issues = detector.process_frame(frame)

        # -------- SAVE EVERY 20 SECONDS ----------
        current_time = datetime.datetime.now()

        if (current_time - last_saved_time).total_seconds() >= 20:
            if not issues:
                save_posture_log(user_id, "GOOD POSTURE", detector.current_position)
            else:
                # Clean all issues inside this 20-sec frame and stringify them
                cleaned_issues = [re.sub(r'\s*\(\d+\s*degrees\)', '', re.sub(r'\s*\(\d+°\)', '', iss)).strip() for iss in issues]
                joined_issues_string = ", ".join(cleaned_issues)
                save_posture_log(user_id, joined_issues_string, detector.current_position)
            last_saved_time = current_time

        # -------- DISPLAY PANEL ----------
        # Calculate FPS
        current_time_fps = time.time()
        fps = 1 / (current_time_fps - detector.pTime) if detector.pTime > 0 else 0
        detector.pTime = current_time_fps
        
        cv2.rectangle(frame, (0, 0), (500, 160), (0, 0, 0), -1)

        cv2.putText(frame, f"Mode: {detector.current_mode}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"View: {detector.current_view}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Pos:  {detector.current_position}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"FPS:  {int(fps)}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        y_offset = 150
        if not issues:
            cv2.putText(frame, "GOOD POSTURE", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "ISSUES DETECTED:", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.rectangle(frame, (0, 160), (500, 170 + 30 * len(issues)), (0, 0, 0), -1)
            for issue in list(issues):
                y_offset += 30
                cv2.putText(frame, f"- {issue}", (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ---------------------------
# RUN APP
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)
