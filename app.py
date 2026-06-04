from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from datetime import date
from flask import render_template


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

    data = request.get_json()

    patient_id = data['patient_id']

    cur = mysql.connection.cursor()

    cur.execute(
    "INSERT INTO patients (name, age, password) VALUES (%s, %s, %s)",
    (name, age, password)
)

    user = cur.fetchone()

    cur.close()

    if user:
        return jsonify({
            "message": "Login successful!",
            "patient_id": user[0]
        })

    return jsonify({
        "message": "Patient not found"
    }), 404
    
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

@app.route('/book', methods=['POST'])
def book_appointment():

    data = request.get_json()

    patient_name = data['patient_name']
    patient_age = data['patient_age']

    doctor_id = data['doctor_id']
    appointment_date = data['appointment_date']
    appointment_time = data['appointment_time']

    priority = int(data.get('priority_level', 0))
    visit_type = data.get('visit_type', 'followup')

    cur = mysql.connection.cursor()

    # Check if patient already exists
    cur.execute(
    "SELECT id, visit_count FROM patients WHERE name=%s AND age=%s",
    (patient_name, patient_age)
)

    patient = cur.fetchone()

    if patient:
        patient_id = patient[0]
        visit_count = patient[1] or 0

    else:
        cur.execute("""
            INSERT INTO patients (name, age)
            VALUES (%s, %s)
        """, (
            patient_name,
            patient_age
        ))

        mysql.connection.commit()

        patient_id = cur.lastrowid
        visit_count = 0

    # Get doctor's average consultation time
    cur.execute(
        "SELECT avg_consult_time FROM doctors WHERE id=%s",
        (doctor_id,)
    )

    doctor = cur.fetchone()

    if not doctor:
        cur.close()
        return jsonify({"error": "Doctor not found"}), 404

    avg_time = doctor[0]

    # AI prediction
    predicted_duration = avg_time

    if visit_type == "new":
        predicted_duration += 6

    if visit_count > 5:
        predicted_duration -= 2

    if priority >= 3:
        predicted_duration += 5

    if predicted_duration < 5:
        predicted_duration = 5

    # Insert appointment
    cur.execute("""
        INSERT INTO appointments
        (
            patient_id,
            doctor_id,
            appointment_date,
            appointment_time,
            status,
            priority_level,
            visit_type,
            predicted_duration
        )
        VALUES
        (%s,%s,%s,%s,'Booked',%s,%s,%s)
    """,
    (
        patient_id,
        doctor_id,
        appointment_date,
        appointment_time,
        priority,
        visit_type,
        predicted_duration
    ))

    appointment_id = cur.lastrowid

    mysql.connection.commit()

    # Notification
    cur.execute("""
        INSERT INTO notifications
        (patient_id, message)
        VALUES (%s,%s)
    """,
    (
        patient_id,
        f"Appointment #{appointment_id} booked successfully."
    ))

    mysql.connection.commit()

    cur.close()

    return jsonify({
        "message": "Appointment booked successfully!",
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "predicted_duration": predicted_duration
    })
    
@app.route('/appointments/today/<int:doctor_id>', methods=['GET'])
def todays_appointments(doctor_id):
    today = date.today().strftime('%Y-%m-%d') 


    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT a.id, p.name, a.appointment_time, a.status
    FROM appointments a
    JOIN patients p ON a.patient_id = p.id
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
    "patient_name": appt[1],
    "time": str(appt[2]),
    "status": appt[3]
})

    return jsonify(result)


@app.route('/appointments/next/<int:doctor_id>', methods=['GET'])
def next_patient(doctor_id):
    today = date.today().strftime('%Y-%m-%d')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, patient_id, priority_level, appointment_time
        FROM appointments
        WHERE doctor_id = %s
        AND appointment_date = %s
        AND status = 'Arrived'
        ORDER BY priority_level DESC, appointment_time ASC
        LIMIT 1
    """, (doctor_id, today))

    patient = cur.fetchone()

    if patient:
        appointment_id = patient[0]
        patient_id = patient[1]

        # Insert notification ONLY after we know patient_id
        cur.execute("""
            INSERT INTO notifications (patient_id, message)
            VALUES (%s, %s)
        """, (patient_id, "You are next. Please proceed to the doctor's room."))

        mysql.connection.commit()
        cur.close()

        return jsonify({
            "appointment_id": appointment_id,
            "patient_id": patient_id,
            "priority_level": patient[2],
            "time": str(patient[3])
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

    cur.close()

    return jsonify({
        "doctor_name": doctor_name,
        "avg_consultation_time_minutes": avg_time,
        "total_appointments_today": total_appointments,
        "completed_today": completed,
        "patients_waiting": waiting
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

    # Get appointment details
    cur.execute("""
SELECT a.priority_level, a.visit_type, p.visit_count, d.avg_consult_time
FROM appointments a
LEFT JOIN doctors d ON a.doctor_id = d.id
LEFT JOIN patients p ON a.patient_id = p.id
WHERE a.id = %s
""", (appointment_id,))

    data = cur.fetchone()

    if not data:
        cur.close()
        return jsonify({"error": "Appointment not found"})

    priority, visit_type, visit_count, avg_time = data

    predicted_time = calculate_predicted_time(
    priority,
    visit_type,
    visit_count,
    avg_time
)
    cur.close()

    return jsonify({
    "appointment_id": appointment_id,
    "predicted_consult_time_minutes": predicted_time
    })
    
def calculate_predicted_time(priority, visit_type, visit_count, avg_time):

    predicted = avg_time

    if visit_type == "new":
        predicted += 6

    if visit_count > 5:
        predicted -= 2

    if priority >= 3:
        predicted += 5

    return predicted

@app.route('/appointments/check-no-show', methods=['POST'])
def detect_no_show():

    from datetime import datetime

    now = datetime.now()

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, appointment_time
        FROM appointments
        WHERE status = 'Booked'
    """)

    appointments = cur.fetchall()

    for appt in appointments:

        appt_id = appt[0]
        appt_time = appt[1]

        if now.time() > appt_time:

            cur.execute("""
                UPDATE appointments
                SET status = 'No Show'
                WHERE id = %s
            """, (appt_id,))

    mysql.connection.commit()
    cur.close()

    return jsonify({"message":"No-show detection completed"})

@app.route('/appointments/emergency', methods=['POST'])
def emergency_case():

    data = request.get_json()

    patient_id = data['patient_id']
    doctor_id = data['doctor_id']

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO appointments
        (patient_id,doctor_id,appointment_date,appointment_time,status,priority_level)
        VALUES (%s,%s,CURDATE(),NOW(),'Arrived',10)
    """,(patient_id,doctor_id))

    mysql.connection.commit()
    cur.close()

    return jsonify({"message":"Emergency case inserted"})

@app.route('/doctor/utilization/<int:doctor_id>')
def doctor_utilization(doctor_id):

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT
    COUNT(*),
    SUM(TIMESTAMPDIFF(MINUTE,start_time,end_time))
    FROM appointments
    WHERE doctor_id=%s AND status='Completed'
    """,(doctor_id,))

    total_consults, total_time = cur.fetchone()

    total_time = total_time or 0

    utilization = round((total_time/(8*60))*100, 2)

    cur.close()

    return jsonify({
        "consultations": total_consults,
        "utilization_percent": utilization
    })

@app.route('/doctor/patients/<int:doctor_id>', methods=['GET'])
def doctor_patients(doctor_id):

    today = date.today().strftime('%Y-%m-%d')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            a.id,
            p.name,
            a.appointment_time,
            a.priority_level,
            a.status
        FROM appointments a
        JOIN patients p
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
            "patient_name": row[1],
            "appointment_time": str(row[2]),
            "priority": row[3],
            "status": row[4]
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