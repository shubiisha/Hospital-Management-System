function bookAppointment() {
  console.log("Book button clicked");
  let patient_name = document.getElementById("patient_name").value;
  let patient_age = document.getElementById("patient_age").value;
  let patient_phone = document.getElementById("patient_phone") ? document.getElementById("patient_phone").value : "";
  let doctor = document.getElementById("doctor_id").value;
  let date = document.getElementById("date").value;
  let time = document.getElementById("time").value;
  let priority = document.getElementById("priority").value;
  let visitType = document.getElementById("visit_type").value;

  if (!patient_name || !doctor || !date || !time) {
    document.getElementById("result").innerHTML = `<div style="color:red;">❌ Please fill in Patient Name, Doctor, Date, and Time.</div>`;
    return;
  }

  fetch("/book", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      patient_name: patient_name,
      patient_age: patient_age || 30,
      phone: patient_phone,
      doctor_id: doctor,
      appointment_date: date,
      appointment_time: time,
      priority_level: priority || 0,
      visit_type: visitType,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        document.getElementById("result").innerHTML = `<div style="color:red;">❌ ${data.error}</div>`;
        return;
      }

      const statusBadge = data.is_returning 
        ? `<span style="background:#e8f4fd; color:#0d6efd; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:bold;">🔁 Returning Patient (Visit #${data.visit_count})</span>` 
        : `<span style="background:#e8f8ee; color:#28a745; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:bold;">🆕 New Patient Registered</span>`;

      document.getElementById("result").innerHTML = `
        <div class="success-box">
          <h3>✅ Appointment Booked Successfully!</h3>
          <p><b>Appointment ID:</b> #${data.appointment_id}</p>
          <p><b>Patient ID:</b> <span style="font-size:16px; font-weight:bold; color:#2980b9;">#${data.patient_id}</span> &nbsp; ${statusBadge}</p>
          <p><b>Patient Name:</b> ${data.patient_name}</p>
          <p><b>Contact Phone:</b> ${data.phone || 'None provided'}</p>
          <p><b>Doctor:</b> ${data.doctor_name || 'Doctor #' + data.doctor_id}</p>
          <p><b>Scheduled For:</b> ${data.appointment_date} at <b>${data.appointment_time}</b></p>
          <p><b>Predicted Duration:</b> ${data.predicted_duration} minutes</p>
          <div style="margin-top:10px; padding:8px 12px; background:#fff; border-radius:6px; border-left:4px solid #28a745; font-size:12px; color:#333;">
            <b>📲 SMS / System Notification Sent:</b><br>${data.notification}
          </div>
        </div>
      `;
    })
    .catch((err) => {
      console.error(err);
      document.getElementById("result").innerHTML = `<div style="color:red;">Error connecting to booking service.</div>`;
    });
}

function getNextPatient() {
  let doctor = document.getElementById("doctor_queue").value;
  let qDiv = document.getElementById("queue");

  if (!doctor) {
    qDiv.innerHTML = `<span style="color:red;">Please select a doctor first.</span>`;
    return;
  }

  fetch("/appointments/next/" + doctor)
    .then((res) => res.json())
    .then((data) => {
      if (data.message) {
        qDiv.innerText = data.message;
      } else {
        const isEmerg = data.priority_level >= 10;
        qDiv.innerHTML = `
          <div style="background:#ffffff; border-left: 4px solid ${isEmerg ? '#e74c3c' : '#3498db'}; padding:12px; border-radius:6px;">
            <p style="margin:4px 0;"><b>Appointment ID:</b> #${data.appointment_id}</p>
            <p style="margin:4px 0;"><b>Patient ID:</b> <span style="color:#2980b9; font-weight:bold; font-size:15px;">#${data.patient_id}</span></p>
            <p style="margin:4px 0;"><b>Patient Name:</b> <b>${data.patient_name || 'Patient'}</b></p>
            <p style="margin:4px 0;"><b>Queue Priority:</b> <span style="font-weight:bold; color:${isEmerg ? '#c0392b' : '#2c3e50'};">${isEmerg ? '🚨 Emergency (' + data.priority_level + ')' : data.priority_level}</span></p>
            <p style="margin:4px 0;"><b>Scheduled Time:</b> ${data.time}</p>
            <p style="margin:6px 0 0 0; font-size:12px; color:#27ae60; font-weight:bold;">🔔 Notification logged: Patient alerted to enter doctor's room.</p>
          </div>
        `;
      }
    })
    .catch((err) => {
      console.error(err);
      qDiv.innerText = "Error fetching next patient.";
    });
}

function predictTime() {
  let id = document.getElementById("appointment_id").value;
  let pDiv = document.getElementById("prediction");

  if (!id) {
    pDiv.innerHTML = `<span style="color:red;">Please enter an Appointment ID.</span>`;
    return;
  }

  fetch("/ai/predict-time/" + id)
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        pDiv.innerText = data.error;
      } else {
        pDiv.innerHTML = `
          <div style="background:#ffffff; padding:12px; border-radius:6px; border-left:4px solid #8e44ad;">
            <p style="margin:4px 0;"><b>Appointment ID:</b> #${data.appointment_id}</p>
            <p style="margin:4px 0;"><b>Patient ID:</b> #${data.patient_id || 'N/A'}</p>
            <p style="margin:4px 0;"><b>Patient Name:</b> <b>${data.patient_name || 'Patient'}</b></p>
            <p style="margin:4px 0;"><b>Doctor:</b> ${data.doctor_name || 'Doctor #' + data.doctor_id}</p>
            <p style="margin:6px 0; font-size:15px;"><b>Predicted Consultation Time:</b> <span style="font-weight:bold; color:#8e44ad;">${data.predicted_consult_time_minutes} minutes</span></p>
            <p style="margin:2px 0 0 0; font-size:11px; color:#888;">AI Engine: ${data.model_used || 'RandomForestRegressor'}</p>
          </div>
        `;
      }
    })
    .catch((err) => {
      console.error(err);
      pDiv.innerText = "Error predicting consultation time.";
    });
}
function updateStatus() {
  let id = document.getElementById("status_id").value;
  let status = document.getElementById("status_value").value;

  console.log("Appointment:", id);
  console.log("Status:", status);

  fetch("/appointment/status", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      appointment_id: id,
      status: status,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      console.log(data);
      document.getElementById("status_result").innerText = data.message;
    })
    .catch((err) => {
      console.error(err);
    });
}

function loadDoctorPatients() {
  let doctorId = document.getElementById("doctor_dashboard_id").value;

  fetch("/doctor/patients/" + doctorId)
    .then((res) => res.json())
    .then((data) => {
      let html = `
        <table border="1" width="100%">
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Time</th>
            <th>Priority</th>
            <th>Status</th>
          </tr>
      `;

      data.forEach((p) => {
        html += `
          <tr>
            <td>${p.appointment_id}</td>
            <td>${p.patient_name}</td>
            <td>${p.appointment_time}</td>
            <td>${p.priority}</td>
            <td>${p.status}</td>
          </tr>
        `;
      });

      html += "</table>";

      document.getElementById("doctor_patients").innerHTML = html;
    });
}
function openDoctorDashboard(doctorId) {
  window.location.href = "/doctor-dashboard/" + doctorId;
}

function loadAvailableSlots() {
  let doctor = document.getElementById("doctor_id").value;
  let date = document.getElementById("date").value;

  if (!doctor || !date) return;

  fetch(`/available-slots/${doctor}/${date}`)
    .then((res) => res.json())
    .then((slots) => {
      let dropdown = document.getElementById("time");

      dropdown.innerHTML = "";

      if (slots.length === 0) {
        dropdown.innerHTML = "<option>No Slots Available</option>";
        return;
      }

      slots.forEach((slot) => {
        let option = document.createElement("option");
        option.value = slot;
        option.textContent = slot;
        dropdown.appendChild(option);
      });
    });
}

// 🚨 Emergency Appointment Booking
function bookEmergencyAppointment() {
  let name = document.getElementById("emerg_patient_name").value;
  let age = document.getElementById("emerg_patient_age").value;
  let phone = document.getElementById("emerg_patient_phone") ? document.getElementById("emerg_patient_phone").value : "";
  let doctorId = document.getElementById("emerg_doctor_id").value;
  let resultDiv = document.getElementById("emerg_result");

  if (!name || !doctorId) {
    resultDiv.innerHTML = `<span style="color:red;">Please enter patient name and select doctor.</span>`;
    return;
  }

  fetch("/appointments/emergency", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      patient_name: name,
      patient_age: age || 30,
      phone: phone,
      doctor_id: doctorId,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      resultDiv.innerHTML = `
        <div style="color: #c0392b; background: #fde8e8; padding: 12px; border-radius: 6px; border-left: 4px solid #c0392b;">
          <b>🚨 ${data.message}</b><br>
          <p style="margin:4px 0;"><b>Appointment ID:</b> #${data.appointment_id || 'N/A'}</p>
          <p style="margin:4px 0;"><b>Patient ID:</b> <span style="font-weight:bold; color:#2980b9;">#${data.patient_id}</span></p>
          <p style="margin:4px 0;"><b>Patient Name:</b> ${data.patient_name}</p>
          <p style="margin:4px 0;"><b>Assigned Doctor:</b> ${data.doctor_name || 'Doctor #' + doctorId}</p>
          <p style="margin:4px 0;"><b>Queue Priority:</b> 10 (Max Priority)</p>
          <p style="margin:4px 0;"><b>Status:</b> Arrived (Front of Queue)</p>
          <p style="margin:6px 0 0 0; font-size:12px; color:#555;"><b>Notification:</b> ${data.notification || 'Alert logged.'}</p>
        </div>
      `;
    })
    .catch((err) => {
      console.error(err);
      resultDiv.innerText = "Error booking emergency appointment.";
    });
}

// ⏱️ Check Doctor Current Wait Time
function checkWaitTime() {
  let doctorId = document.getElementById("wait_doctor_id").value;
  let outDiv = document.getElementById("wait_output");

  if (!doctorId) return;

  fetch(`/appointments/wait-time/${doctorId}`)
    .then((res) => res.json())
    .then((data) => {
      outDiv.innerHTML = `
        <div style="background: #eef7fc; padding: 10px; border-radius: 6px;">
          <b>Patients Waiting:</b> ${data.patients_waiting}<br>
          <b>Estimated Wait Time:</b> <span style="font-size: 16px; font-weight: bold; color: ${data.estimated_wait_time_minutes > 30 ? '#e74c3c' : '#27ae60'};">${data.estimated_wait_time_minutes} minutes</span>
          ${data.estimated_wait_time_minutes > 30 ? '<br><small style="color: #e74c3c;">⚠️ Doctor is running late. Notifications dispatched to waiting patients.</small>' : ''}
        </div>
      `;
    })
    .catch((err) => {
      console.error(err);
      outDiv.innerText = "Error loading wait time.";
    });
}

// 🔔 View Live Notifications for Patient
function viewNotifications() {
  let patientId = document.getElementById("notif_patient_id").value;
  let listDiv = document.getElementById("notif_list");

  if (!patientId) {
    listDiv.innerHTML = `<span style="color:red;">Please enter a Patient ID.</span>`;
    return;
  }

  fetch(`/notifications/${patientId}`)
    .then((res) => res.json())
    .then((notifs) => {
      if (notifs.length === 0) {
        listDiv.innerHTML = `<p style="color:#777;">No notifications for Patient #${patientId}.</p>`;
        return;
      }

      let html = "";
      notifs.forEach((n) => {
        html += `
          <div class="notif-item">
            <strong>${n.message}</strong>
            <span class="notif-time">${n.time}</span>
          </div>
        `;
      });
      listDiv.innerHTML = html;
    })
    .catch((err) => {
      console.error(err);
      listDiv.innerText = "Error loading notifications.";
    });
}

// ⚡ Trigger No-Show Detection
function triggerNoShowDetection() {
  let outDiv = document.getElementById("noshow_output");
  outDiv.innerText = "Scanning today's appointments...";

  fetch("/appointments/check-no-show", { method: "POST" })
    .then((res) => res.json())
    .then((data) => {
      outDiv.innerHTML = `<span style="color: green; font-weight: bold;">✅ ${data.message}</span>`;
    })
    .catch((err) => {
      console.error(err);
      outDiv.innerText = "Error running no-show detection.";
    });
}

// Dynamically populate doctors dropdowns from database
function loadDoctorsDropdown() {
  fetch("/doctors")
    .then((res) => res.json())
    .then((doctors) => {
      if (!doctors || doctors.length === 0) return;

      const dropdownIds = ["doctor_id", "doctor_queue", "wait_doctor_id", "emerg_doctor_id"];
      dropdownIds.forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = "";
        if (id === "doctor_id" || id === "emerg_doctor_id" || id === "doctor_queue") {
          const defaultOpt = document.createElement("option");
          defaultOpt.value = "";
          defaultOpt.textContent = "Select Doctor";
          el.appendChild(defaultOpt);
        }
        doctors.forEach((doc) => {
          const opt = document.createElement("option");
          opt.value = doc.id;
          opt.textContent = `${doc.name} — ${doc.specialization}`;
          el.appendChild(opt);
        });
      });
    })
    .catch((err) => console.log("Doctors loaded from HTML defaults:", err));
}

window.addEventListener("DOMContentLoaded", () => {
  loadDoctorsDropdown();
});
