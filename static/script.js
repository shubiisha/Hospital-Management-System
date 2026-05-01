function bookAppointment() {
  let patient = document.getElementById("patient_id").value;
  let doctor = document.getElementById("doctor_id").value;
  let date = document.getElementById("date").value;
  let time = document.getElementById("time").value;
  let priority = document.getElementById("priority").value;

  fetch("/book", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      patient_id: patient,
      doctor_id: doctor,
      appointment_date: date,
      appointment_time: time,
      priority_level: priority,
    }),
  })
    .then((res) => res.json())
    .then((data) => {
      document.getElementById("result").innerText = data.message;
    });
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
      document.getElementById("status_result").innerText = data.message;
    });
}
