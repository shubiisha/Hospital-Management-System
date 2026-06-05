function bookAppointment() {
  let patient_name = document.getElementById("patient_name").value;
  let patient_age = document.getElementById("patient_age").value;
  let doctor = document.getElementById("doctor_id").value;
  let date = document.getElementById("date").value;
  let time = document.getElementById("time").value;
  let priority = document.getElementById("priority").value;
  let visitType = document.getElementById("visit_type").value;

  fetch("/book", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      patient_name: patient_name,
      patient_age: patient_age,
      doctor_id: doctor,
      appointment_date: date,
      appointment_time: time,
      priority_level: priority,
      visit_type: visitType,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      document.getElementById("result").innerHTML = `
    <div class="success-box">
        <h3>✅ Appointment Booked</h3>

        <p><strong>Appointment ID:</strong> ${data.appointment_id}</p>

        <p><strong>Patient:</strong> ${data.patient_name}</p>

        <p><strong>Doctor ID:</strong> ${data.doctor_id}</p>

        <p><strong>Time:</strong> ${data.appointment_time}</p>

        <p><strong>Predicted Duration:</strong> ${data.predicted_duration} min</p>
    </div>
`;
    })
    .catch((err) => console.error(err));
}

function getNextPatient() {
  let doctor = document.getElementById("doctor_queue").value;

  fetch("/appointments/next/" + doctor)
    .then((res) => res.json())
    .then((data) => {
      if (data.message) {
        document.getElementById("queue").innerText = data.message;
      } else {
        document.getElementById("queue").innerText =
          "Next Patient ID: " +
          data.patient_id +
          " | Priority: " +
          data.priority_level +
          " | Time: " +
          data.time;
      }
    });
}

function predictTime() {
  let id = document.getElementById("appointment_id").value;

  fetch("/ai/predict-time/" + id)
    .then((res) => res.json())
    .then((data) => {
      if (data.error) {
        document.getElementById("prediction").innerText = data.error;
      } else {
        document.getElementById("prediction").innerText =
          "Predicted Consultation Time: " +
          data.predicted_consult_time_minutes +
          " minutes";
      }
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

function loadSlots() {
  let doctor = document.getElementById("doctor_id").value;
  let date = document.getElementById("date").value;

  if (!doctor || !date) return;

  fetch(`/available-slots/${doctor}/${date}`)
    .then((res) => res.json())
    .then((slots) => {
      let dropdown = document.getElementById("time");

      dropdown.innerHTML = "";

      slots.forEach((slot) => {
        dropdown.innerHTML += `
          <option value="${slot}">
            ${slot}
          </option>
        `;
      });
    });
}
