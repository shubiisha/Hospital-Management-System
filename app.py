from flask import Flask, request, jsonify, render_template
from flask_mysqldb import MySQL
from flask_cors import CORS
from datetime import date, datetime
import os

try:
    import joblib
except ImportError:
    joblib = None

MODEL_FILE = os.path.join(os.path.dirname(__file__), 'consultation_model.pkl')
ml_model = None

def load_ml_model():
    global ml_model
    if joblib and os.path.exists(MODEL_FILE):
        try:
            ml_model = joblib.load(MODEL_FILE)
            print("[OK] Successfully loaded trained AI consultation prediction model.")
        except Exception as e:
            print("[WARN] Could not load ML model file:", e)

load_ml_model()

def calculate_predicted_time(doctor_id, priority, visit_type, visit_count, avg_time, age=30):
    if ml_model is not None:
        try:
            is_new = 1 if visit_type == "new" else 0
            pred = ml_model.predict([[int(doctor_id or 1), int(age or 30), is_new, int(priority or 0), int(visit_count or 0)]])[0]
            return max(5, int(round(pred)))
        except Exception as e:
            print("ML model prediction error, fallback:", e)

    # Calibrated rule-based fallback
    predicted = avg_time if avg_time else 15
    if visit_type == "new":
        predicted += 6
    if visit_count and int(visit_count) > 5:
        predicted -= 2
    if priority and int(priority) >= 3:
        predicted += 5
    if priority and int(priority) >= 10:
        predicted += 5
    return max(5, int(predicted))

app = Flask(__name__)
CORS(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '2006'   
app.config['MYSQL_DB'] = 'healthcare_db'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    name = data['name']
    age = data['age']
    password = data['password']

    cur = mysql.connection.cursor()

    cur.execute(
        "INSERT INTO patients (name, age,  password) VALUES (%s, %s, %s)",
        (name, age, password)
    )

    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Patient registered successfully!"})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    patient_id = data.get('patient_id')
    password = data.get('password')

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT id, name, age, email FROM patients WHERE id = %s AND password = %s",
        (patient_id, password)
    )
    user = cur.fetchone()
    cur.close()

    if user:
        return jsonify({
            "message": "Login successful!",
            "patient_id": user[0],
            "name": user[1],
            "age": user[2],
            "email": user[3]
        })

    return jsonify({
        "message": "Invalid patient ID or password"
    }), 401
    
@app.route('/doctors', methods=['GET'])
def get_doctors():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()
    cur.close()

    doctor_list = []
    for doc in doctors:
        doctor_list.append({
            "id": doc[0],
            "name": doc[1],
            "specialization": doc[2],
            "avg_consult_time": doc[3]
        })

    return jsonify(doctor_list)

@app.route('/available-slots/<int:doctor_id>/<appointment_date>')
def available_slots(doctor_id, appointment_date):

    all_slots = [
        "09:00:00","09:10:00","09:20:00","09:30:00",
        "09:40:00","09:50:00","10:00:00","10:10:00",
        "10:20:00","10:30:00","10:40:00","10:50:00",
        "11:00:00","11:10:00","11:20:00","11:30:00",
        "12:00:00","12:10:00","12:20:00","12:30:00"
    ]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT appointment_time
        FROM appointments
        WHERE doctor_id=%s
        AND appointment_date=%s
        AND status != 'Cancelled'
    """, (doctor_id, appointment_date))

    booked = cur.fetchall()

    cur.close()

    booked_slots = [str(row[0]) for row in booked]

    free_slots = [
        slot for slot in all_slots
        if slot not in booked_slots
    ]

    return jsonify(free_slots)

@app.route('/book', methods=['POST'])
def book_appointment():
    data = request.get_json() or {}

    patient_name = data.get('patient_name', '').strip()
    patient_age = data.get('patient_age', 30)
    patient_phone = data.get('phone') or data.get('patient_phone') or ''
    patient_phone = str(patient_phone).strip()

    doctor_id = data.get('doctor_id')
    appointment_date = data.get('appointment_date')
    appointment_time = data.get('appointment_time')

    priority = int(data.get('priority_level', 0))
    visit_type = data.get('visit_type', 'followup')

    if not patient_name or not doctor_id or not appointment_date or not appointment_time:
        return jsonify({"error": "Please provide patient name, doctor, date, and time."}), 400

    cur = mysql.connection.cursor()

    # Match patient by Phone Number (primary unique identifier) or Name + Age
    patient = None
    if patient_phone:
        cur.execute("SELECT id, visit_count, name FROM patients WHERE phone = %s", (patient_phone,))
        patient = cur.fetchone()

    if not patient:
        cur.execute("SELECT id, visit_count, name FROM patients WHERE name = %s AND age = %s", (patient_name, patient_age))
        patient = cur.fetchone()

    is_returning = False
    if patient:
        patient_id = patient[0]
        visit_count = (patient[1] or 0) + 1
        is_returning = True
        # Keep phone number up to date
        if patient_phone:
            cur.execute("UPDATE patients SET phone = %s, visit_count = %s WHERE id = %s", (patient_phone, visit_count, patient_id))
        else:
            cur.execute("UPDATE patients SET visit_count = %s WHERE id = %s", (visit_count, patient_id))
        mysql.connection.commit()
    else:
        cur.execute("""
            INSERT INTO patients (name, age, phone, visit_count)
            VALUES (%s, %s, %s, 1)
        """, (patient_name, patient_age, patient_phone or None))
        mysql.connection.commit()
        patient_id = cur.lastrowid
        visit_count = 1

    # Get doctor's details and average consultation time
    cur.execute("SELECT name, avg_consult_time FROM doctors WHERE id = %s", (doctor_id,))
    doc_row = cur.fetchone()
    if not doc_row:
        cur.close()
        return jsonify({"error": "Doctor not found"}), 404

    doctor_name, avg_time = doc_row

    # AI Consultation Duration Prediction (RandomForestRegressor with fallback)
    predicted_duration = calculate_predicted_time(
        doctor_id=doctor_id,
        priority=priority,
        visit_type=visit_type,
        visit_count=visit_count,
        avg_time=avg_time,
        age=patient_age
    )

    # Check for slot collision
    cur.execute("""
        SELECT id FROM appointments
        WHERE doctor_id = %s
        AND appointment_date = %s
        AND appointment_time = %s
        AND status != 'Cancelled'
    """, (doctor_id, appointment_date, appointment_time))

    existing = cur.fetchone()
    if existing:
        cur.close()
        return jsonify({"error": f"Slot {appointment_time} is already booked for Dr. {doctor_name}."}), 400

    # Insert appointment
    cur.execute("""
        INSERT INTO appointments
        (patient_id, patient_name, doctor_id, appointment_date, appointment_time, status, priority_level, visit_type, predicted_duration)
        VALUES (%s, %s, %s, %s, %s, 'Booked', %s, %s, %s)
    """, (
        patient_id,
        patient_name,
        doctor_id,
        appointment_date,
        appointment_time,
        priority,
        visit_type,
        predicted_duration
    ))
    appointment_id = cur.lastrowid
    mysql.connection.commit()

    # Dispatch rich SMS / System Notification
    sms_target = f" (SMS dispatched to {patient_phone})" if patient_phone else ""
    notification_msg = (
        f"Appointment #{appointment_id} successfully confirmed for {appointment_date} at {appointment_time} "
        f"with {doctor_name}. Patient ID: #{patient_id}.{sms_target}"
    )
    cur.execute("""
        INSERT INTO notifications (patient_id, message)
        VALUES (%s, %s)
    """, (patient_id, notification_msg))
    mysql.connection.commit()

    cur.close()

    return jsonify({
        "message": "Appointment booked successfully!",
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "phone": patient_phone,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "appointment_date": str(appointment_date),
        "appointment_time": str(appointment_time),
        "predicted_duration": predicted_duration,
        "is_returning": is_returning,
        "visit_count": visit_count,
        "notification": notification_msg
    })
    
@app.route('/appointments/today/<int:doctor_id>', methods=['GET'])
def todays_appointments(doctor_id):
    today = date.today().strftime('%Y-%m-%d') 
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.id, a.patient_id, COALESCE(a.patient_name, p.name, 'Patient'), a.appointment_time, a.status, a.priority_level
        FROM appointments a
        LEFT JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = %s
        AND a.appointment_date = %s
        AND a.status = 'Arrived'
        ORDER BY a.priority_level DESC, a.appointment_time ASC
        LIMIT 1
    """, (doctor_id, today))

    appointments = cur.fetchall()
    cur.close()

    result = []
    for appt in appointments:
        result.append({
            "appointment_id": appt[0],
            "patient_id": appt[1],
            "patient_name": appt[2],
            "time": str(appt[3]),
            "appointment_time": str(appt[3]),
            "status": appt[4],
            "priority_level": appt[5]
        })

    return jsonify(result)


@app.route('/appointments/next/<int:doctor_id>', methods=['GET'])
def next_patient(doctor_id):
    today = date.today().strftime('%Y-%m-%d')
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT a.id, a.patient_id, a.priority_level, a.appointment_time, COALESCE(a.patient_name, p.name, 'Patient')
        FROM appointments a
        LEFT JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = %s
        AND a.appointment_date = %s
        AND a.status = 'Arrived'
        ORDER BY a.priority_level DESC, a.appointment_time ASC
        LIMIT 1
    """, (doctor_id, today))

    patient = cur.fetchone()

    if patient:
        appointment_id = patient[0]
        patient_id = patient[1]
        priority_level = patient[2]
        appointment_time = str(patient[3])
        patient_name = patient[4]

        # Insert notification ONLY after we know patient_id
        cur.execute("""
            INSERT INTO notifications (patient_id, message)
            VALUES (%s, %s)
        """, (patient_id, f"You are next for consultation with Doctor #{doctor_id}. Please proceed to the room."))

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "appointment_id": appointment_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "priority_level": priority_level,
            "time": appointment_time
        })
    else:
        cur.close()
        return jsonify({"message": "No patients waiting"})
    
@app.route('/appointment/status', methods=['PUT'])
def update_status():
    data = request.get_json()
    print("Received:", data)
    appointment_id = data['appointment_id']
    new_status = data['status']

    cur = mysql.connection.cursor()

    cur.execute("UPDATE appointments SET status = %s WHERE id = %s", (new_status, appointment_id))
    
    mysql.connection.commit()

    if new_status == "In Consultation":
        cur.execute("UPDATE appointments SET start_time = NOW() WHERE id = %s", (appointment_id,))
        mysql.connection.commit()

    if new_status == "Completed":
        cur.execute("UPDATE appointments SET end_time = NOW() WHERE id = %s", (appointment_id,))
        cur.execute("""
UPDATE patients
SET visit_count = visit_count + 1
WHERE id = (
    SELECT patient_id FROM appointments WHERE id=%s
)
""",(appointment_id,))
        mysql.connection.commit()

        cur.execute("SELECT doctor_id, start_time, end_time FROM appointments WHERE id = %s", (appointment_id,))
        doctor_id, start_time, end_time = cur.fetchone()

        if start_time and end_time:
            cur.execute("SELECT TIMESTAMPDIFF(MINUTE, %s, %s)", (start_time, end_time))
            actual_duration = cur.fetchone()[0]
        else:
            actual_duration = 0

        cur.execute("SELECT avg_consult_time FROM doctors WHERE id = %s", (doctor_id,))
        old_avg = cur.fetchone()[0]

        new_avg = int((old_avg + actual_duration) / 2)
        cur.execute("UPDATE doctors SET avg_consult_time = %s WHERE id = %s", (new_avg, doctor_id))
        mysql.connection.commit()

    cur.close()
    return jsonify({"message": "Appointment status updated"})

@app.route('/appointments/wait-time/<int:doctor_id>', methods=['GET'])
def wait_time(doctor_id):

    today = date.today().strftime('%Y-%m-%d')
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT a.id, a.priority_level, a.visit_type, d.avg_consult_time
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.doctor_id = %s
        AND DATE(a.appointment_date) = %s
        AND a.status = 'Arrived'
        ORDER BY a.priority_level DESC, a.appointment_time ASC
    """, (doctor_id, today))

    patients = cur.fetchall()

    total_wait = 0

    for patient in patients:

        priority = patient[1]
        visit_type = patient[2]
        avg_time = patient[3]

        predicted_time = avg_time

        if visit_type == "new":
            predicted_time += 5

        if priority >= 3:
            predicted_time += 5

        total_wait += predicted_time

    if total_wait > 30:

        cur.execute("""
        INSERT INTO notifications (patient_id, message)
        SELECT patient_id,
        CONCAT('Doctor running late. Updated wait time: ', %s, ' minutes')
        FROM appointments
        WHERE doctor_id=%s
        AND status='Arrived'
        """, (total_wait, doctor_id))

        mysql.connection.commit()

    cur.close()

    return jsonify({
        "patients_waiting": len(patients),
        "estimated_wait_time_minutes": total_wait
    })
    
@app.route('/dashboard/doctor/<int:doctor_id>', methods=['GET'])
def doctor_dashboard(doctor_id):
    today = date.today().strftime('%Y-%m-%d')
    cur = mysql.connection.cursor()

    # Get doctor average consultation time
    cur.execute("SELECT name, avg_consult_time FROM doctors WHERE id = %s", (doctor_id,))
    doctor = cur.fetchone()

    if not doctor:
        cur.close()
        return jsonify({"error": "Doctor not found"})

    doctor_name, avg_time = doctor

    # Total appointments today
    cur.execute("""
        SELECT COUNT(*) FROM appointments
        WHERE doctor_id = %s AND appointment_date = %s
    """, (doctor_id, today))
    total_appointments = cur.fetchone()[0]

    # Completed appointments today
    cur.execute("""
        SELECT COUNT(*) FROM appointments
        WHERE doctor_id = %s AND appointment_date = %s AND status = 'Completed'
    """, (doctor_id, today))
    completed = cur.fetchone()[0]

    # Patients still waiting
    cur.execute("""
        SELECT COUNT(*) FROM appointments
        WHERE doctor_id = %s AND appointment_date = %s AND status = 'Arrived'
    """, (doctor_id, today))
    waiting = cur.fetchone()[0]

    # Calculate doctor daily clinical utilization (8-hour shift = 480 mins)
    cur.execute("""
        SELECT SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time))
        FROM appointments
        WHERE doctor_id = %s AND status = 'Completed' AND appointment_date = %s
    """, (doctor_id, today))
    sum_row = cur.fetchone()
    total_mins = sum_row[0] if (sum_row and sum_row[0]) else 0
    utilization = round((total_mins / 480.0) * 100, 1)

    cur.close()

    return jsonify({
        "doctor_name": doctor_name,
        "avg_consultation_time_minutes": avg_time,
        "total_appointments_today": total_appointments,
        "completed_today": completed,
        "patients_waiting": waiting,
        "utilization_percent": utilization
    })
@app.route('/notifications/<int:patient_id>', methods=['GET'])
def get_notifications(patient_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT message, created_at
        FROM notifications
        WHERE patient_id = %s
        ORDER BY created_at DESC
    """, (patient_id,))

    notifications = cur.fetchall()
    cur.close()
    return jsonify([
        {"message": n[0], "time": str(n[1])}
        for n in notifications
    ])

@app.route('/appointments/complete/<int:appointment_id>', methods=['POST'])
def complete_appointment(appointment_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE appointments
        SET status = 'Completed'
        WHERE id = %s
    """, (appointment_id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": "Appointment completed"})

@app.route('/ai/predict-time/<int:appointment_id>', methods=['GET'])
def predict_consultation_time(appointment_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT a.priority_level, a.visit_type, p.visit_count, d.avg_consult_time, a.doctor_id, p.age,
               a.patient_id, COALESCE(a.patient_name, p.name, 'Patient') AS patient_name,
               d.name AS doctor_name
        FROM appointments a
        LEFT JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN patients p ON a.patient_id = p.id
        WHERE a.id = %s
    """, (appointment_id,))

    data = cur.fetchone()

    if not data:
        cur.close()
        return jsonify({"error": "Appointment not found"}), 404

    priority, visit_type, visit_count, avg_time, doc_id, age, pat_id, pat_name, doc_name = data

    predicted_time = calculate_predicted_time(
        doctor_id=doc_id,
        priority=priority,
        visit_type=visit_type,
        visit_count=visit_count,
        avg_time=avg_time,
        age=age or 30
    )
    cur.close()

    return jsonify({
        "appointment_id": appointment_id,
        "patient_id": pat_id,
        "patient_name": pat_name,
        "doctor_id": doc_id,
        "doctor_name": doc_name or f"Doctor #{doc_id}",
        "predicted_consult_time_minutes": predicted_time,
        "model_used": "RandomForestRegressor" if ml_model is not None else "Calibrated Heuristic Formula"
    })

@app.route('/appointments/check-no-show', methods=['POST'])
def detect_no_show():
    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE appointments
        SET status = 'No Show'
        WHERE status = 'Booked'
          AND appointment_date = CURDATE()
          AND appointment_time < CURTIME()
    """)

    mysql.connection.commit()
    updated_count = cur.rowcount
    cur.close()

    return jsonify({
        "message": f"No-show detection completed. {updated_count} elapsed appointment(s) updated to 'No Show'."
    })

@app.route('/appointments/emergency', methods=['POST'])
def emergency_case():
    data = request.get_json() or {}
    cur = mysql.connection.cursor()

    patient_id = data.get('patient_id')
    patient_name = data.get('patient_name', 'Emergency Patient').strip()
    patient_age = data.get('patient_age', 30)
    patient_phone = str(data.get('phone') or data.get('patient_phone') or '').strip()
    doctor_id = data.get('doctor_id', 1)

    # Get doctor name
    cur.execute("SELECT name FROM doctors WHERE id = %s", (doctor_id,))
    doc_row = cur.fetchone()
    doctor_name = doc_row[0] if doc_row else f"Doctor #{doctor_id}"

    if not patient_id:
        patient = None
        if patient_phone:
            cur.execute("SELECT id, name FROM patients WHERE phone = %s", (patient_phone,))
            patient = cur.fetchone()
        if not patient:
            cur.execute("SELECT id, name FROM patients WHERE name = %s AND age = %s", (patient_name, patient_age))
            patient = cur.fetchone()

        if patient:
            patient_id = patient[0]
            patient_name = patient[1]
        else:
            cur.execute("""
                INSERT INTO patients (name, age, phone, visit_count)
                VALUES (%s, %s, %s, 1)
            """, (patient_name, patient_age, patient_phone or None))
            mysql.connection.commit()
            patient_id = cur.lastrowid
    else:
        cur.execute("SELECT name FROM patients WHERE id = %s", (patient_id,))
        p_row = cur.fetchone()
        if p_row:
            patient_name = p_row[0]

    # Insert urgent appointment with priority 10 & status 'Arrived'
    cur.execute("""
        INSERT INTO appointments
        (patient_id, patient_name, doctor_id, appointment_date, appointment_time, status, priority_level, visit_type, predicted_duration)
        VALUES (%s, %s, %s, CURDATE(), CURTIME(), 'Arrived', 10, 'new', 25)
    """, (patient_id, patient_name, doctor_id))

    mysql.connection.commit()
    appointment_id = cur.lastrowid

    # Urgent notification
    notification_msg = (
        f"🚨 EMERGENCY ADMISSION: Appointment #{appointment_id} for {patient_name} (Patient ID: #{patient_id}) "
        f"assigned to {doctor_name} with Priority 10."
    )
    cur.execute("""
        INSERT INTO notifications (patient_id, message)
        VALUES (%s, %s)
    """, (patient_id, notification_msg))
    mysql.connection.commit()

    cur.close()

    return jsonify({
        "message": "Emergency patient successfully admitted to queue!",
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "doctor_name": doctor_name,
        "priority_level": 10,
        "status": "Arrived",
        "notification": notification_msg
    })

@app.route('/doctor/utilization/<int:doctor_id>')
def doctor_utilization(doctor_id):
    today = date.today().strftime('%Y-%m-%d')
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            COUNT(*),
            SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time))
        FROM appointments
        WHERE doctor_id = %s AND status = 'Completed' AND appointment_date = %s
    """, (doctor_id, today))

    total_consults, total_time = cur.fetchone()
    total_time = total_time or 0

    # Based on standard 8-hour shift (480 minutes)
    utilization = round((total_time / 480.0) * 100, 1)

    cur.close()

    return jsonify({
        "consultations": total_consults,
        "total_time_minutes": total_time,
        "utilization_percent": utilization
    })

@app.route('/doctor/patients/<int:doctor_id>', methods=['GET'])
def doctor_patients(doctor_id):
    today = date.today().strftime('%Y-%m-%d')
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            a.id,
            a.patient_id,
            COALESCE(a.patient_name, p.name, 'Patient') AS patient_name,
            a.appointment_time,
            a.priority_level,
            a.status
        FROM appointments a
        LEFT JOIN patients p
            ON a.patient_id = p.id
        WHERE a.doctor_id = %s
        AND a.appointment_date = %s
        ORDER BY a.priority_level DESC,
                a.appointment_time ASC
    """, (doctor_id, today))

    rows = cur.fetchall()
    cur.close()

    result = []
    for row in rows:
        result.append({
            "appointment_id": row[0],
            "patient_id": row[1],
            "patient_name": row[2],
            "appointment_time": str(row[3]),
            "time": str(row[3]),
            "priority": row[4],
            "priority_level": row[4],
            "status": row[5]
        })

    return jsonify(result)

@app.route('/doctor-dashboard/<int:doctor_id>')
def doctor_dashboard_page(doctor_id):
    return render_template(
        "doctor_dashboard.html",
        doctor_id=doctor_id
    )
    
if __name__ == '__main__':
    app.run(debug=True)