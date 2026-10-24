
from flask import Flask, render_template, request, redirect
from doctors import GeneralPhysician, Cardiologist, Neurologist, Surgeon
from patients import Patient
from appointment import Appointment
from emergency import EmergencyPatient, EmergencyQueue
from rooms import GeneralWard, PrivateRoom, ICU, EmergencyRoom
from billing import Bill
from discharge import discharge_patient
from database import get_connection, init_db


app = Flask(__name__)

DOCTOR_TYPES = {
    "General Physician": GeneralPhysician,
    "Cardiologist": Cardiologist,
    "Neurologist": Neurologist,
    "Surgeon": Surgeon,
}

DOCTOR_FEES = {
    "General Physician": 500,
    "Cardiologist": 1500,
    "Neurologist": 1800,
    "Surgeon": 2500,
}
EMERGENCY_CHARGE = 1000

ROOM_TYPES = {
    "General Ward": GeneralWard,
    "Private Room": PrivateRoom,
    "ICU": ICU,
    "Emergency Room": EmergencyRoom,
}

BLOOD_GROUPS = [
    "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"
]


# ---------- DATABASE INITIALIZATION ----------

def initialize_hospital():
    init_db()

    with get_connection() as conn:
        doctor_count = conn.execute(
            "SELECT COUNT(*) FROM doctors"
        ).fetchone()[0]

        if doctor_count == 0:
            default_doctors = [
                ("D1", "Dr. Sharma", "General Physician", 12, 1),
                ("D2", "Dr. Mehta", "Cardiologist", 18, 1),
                ("D3", "Dr. Singh", "Neurologist", 10, 0),
                ("D4", "Dr. Verma", "Surgeon", 25, 1),
            ]

            for doctor_id, name, specialization, experience, available in default_doctors:
                conn.execute(
                    """
                    INSERT INTO doctors
                    (doctor_id, name, specialization, experience,
                     is_available, consultation_fee)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doctor_id,
                        name,
                        specialization,
                        experience,
                        available,
                        DOCTOR_FEES[specialization],
                    ),
                )

        room_count = conn.execute(
            "SELECT COUNT(*) FROM rooms"
        ).fetchone()[0]

        if room_count == 0:
            default_rooms = [
                GeneralWard(101),
                PrivateRoom(201),
                ICU(301),
                EmergencyRoom(401),
            ]

            for room in default_rooms:
                conn.execute(
                    """
                    INSERT INTO rooms
                    (room_number, room_type, price_per_day, is_available)
                    VALUES (?, ?, ?, 1)
                    """,
                    (
                        room.room_number,
                        room.room_type,
                        room.price_per_day,
                    ),
                )


# ---------- DATA HELPERS ----------

def load_patients():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM patients ORDER BY rowid"
        ).fetchall()

        records = conn.execute(
            """
            SELECT patient_id, record
            FROM medical_records
            ORDER BY id
            """
        ).fetchall()

    history = {}
    for row in records:
        history.setdefault(row["patient_id"], []).append(row["record"])

    patients = []

    for row in rows:
        patient = Patient(
            row["patient_id"],
            row["name"],
            row["age"],
            row["phone"],
            row["email"] or "",
            row["disease"] or "",
            row["blood_group"] or "",
        )

        for record in history.get(patient.patient_id, []):
            patient.add_medical_record(record)

        patients.append(patient)

    return patients


def load_doctors():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM doctors ORDER BY rowid"
        ).fetchall()

    doctors = []

    for row in rows:
        doctor_class = DOCTOR_TYPES.get(
            row["specialization"], GeneralPhysician
        )

        doctor = doctor_class(
            row["doctor_id"],
            row["name"],
            row["specialization"],
            row["experience"],
            bool(row["is_available"]),
        )

        doctors.append(doctor)

    return doctors


def load_appointments(patients, doctors):
    patient_map = {p.patient_id: p for p in patients}
    doctor_map = {d.doctor_id: d for d in doctors}

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM appointments ORDER BY rowid"
        ).fetchall()

    appointments = []

    for row in rows:
        patient = patient_map.get(row["patient_id"])
        doctor = doctor_map.get(row["doctor_id"])

        if patient is None or doctor is None:
            continue

        # Purani appointment ko doctor ki current availability
        # se block nahi hona chahiye.
        doctor_class = DOCTOR_TYPES.get(
            doctor.specialization, GeneralPhysician
        )

        available_copy = doctor_class(
            doctor.doctor_id,
            doctor.name,
            doctor.specialization,
            doctor.experience,
            True,
        )

        appointment = Appointment(
            row["appointment_id"],
            patient,
            available_copy,
            row["appointment_date"],
            row["appointment_time"],
            row["appointment_type"],
        )

        # Original doctor object retain karo.
        appointment.doctor = doctor
        appointment.status = row["status"]
        appointments.append(appointment)

    return appointments


def load_rooms(patients):
    patient_map = {p.patient_id: p for p in patients}

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM rooms ORDER BY room_number"
        ).fetchall()

        releases = conn.execute(
            """
            SELECT rr.*, r.room_type
            FROM room_releases rr
            JOIN rooms r ON r.room_number = rr.room_number
            ORDER BY rr.id
            """
        ).fetchall()

    rooms = []

    for row in rows:
        room_class = ROOM_TYPES.get(row["room_type"])

        if room_class is None:
            continue

        room = room_class(row["room_number"])
        patient_id = row["patient_id"]
        patient = patient_map.get(patient_id) if patient_id else None

        if patient is not None:
            room.assign_room(patient)
        else:
            # Database ki saved availability bhi retain karo.
            room.is_available = bool(row["is_available"])

        rooms.append(room)

    release_log = []

    for row in releases:
        patient = patient_map.get(row["patient_id"])

        release_log.append({
            "room": row["room_number"],
            "type": row["room_type"],
            "patient": patient.name if patient else "Unknown",
            "patient_id": row["patient_id"],
            "days": row["days"],
            "charge": row["charge"],
        })

    return rooms, release_log


def load_bills(patients):
    patient_map = {p.patient_id: p for p in patients}

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM bills ORDER BY rowid"
        ).fetchall()

    bills = []

    for row in rows:
        patient = patient_map.get(row["patient_id"])

        if patient is None:
            continue

        bill = Bill(
            row["bill_id"],
            patient,
            row["consultation"],
            row["treatment"],
            row["medicine"],
            row["room"],
            row["emergency"],
            row["insurance"],
        )

        bill.paid = row["paid"]
        bills.append(bill)

    return bills


def load_emergency_queue(patients):
    patient_map = {p.patient_id: p for p in patients}
    queue = EmergencyQueue()
    treated = []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, patient_id, priority_level, status
            FROM emergency_records
            ORDER BY id
            """
        ).fetchall()

    for row in rows:
        patient = patient_map.get(row["patient_id"])

        if patient is None:
            continue

        emergency_patient = EmergencyPatient(
            patient,
            row["priority_level"],
        )

        # Record ID is attached to this loaded object so the
        # exact queue entry can be updated when treated.
        emergency_patient.record_id = row["id"]

        if row["status"] == "Waiting":
            queue.add(emergency_patient)
        elif row["status"] == "Treated":
            treated.append(emergency_patient)

    return queue, treated


def load_discharged(patients):
    patient_map = {p.patient_id: p for p in patients}

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT patient_id FROM discharges ORDER BY id"
        ).fetchall()

    return [
        patient_map[row["patient_id"]]
        for row in rows
        if row["patient_id"] in patient_map
    ]


def next_id(table, prefix, column):
    # Table aur column names yahan fixed internal values hain.
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {column} FROM {table}"
        ).fetchall()

    highest = 0

    for row in rows:
        value = row[column]

        if value and value.startswith(prefix):
            suffix = value[len(prefix):]

            if suffix.isdigit():
                highest = max(highest, int(suffix))

    return f"{prefix}{highest + 1}"


def save_appointment_status(appointment):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE appointments
            SET status = ?
            WHERE appointment_id = ?
            """,
            (appointment.status, appointment.appointment_id),
        )


# ---------- HOME ----------

@app.route("/")
def home():
    patients = load_patients()
    doctors = load_doctors()
    appointments = load_appointments(patients, doctors)
    rooms, _ = load_rooms(patients)
    bills = load_bills(patients)
    emergency_queue, _ = load_emergency_queue(patients)
    discharged = load_discharged(patients)

    stats = {
        "patients": len(patients),
        "doctors": len(doctors),
        "available_doctors": sum(
            1 for d in doctors if d.is_available
        ),
        "active_appointments": sum(
            1 for a in appointments
            if a.status in ("Scheduled", "Emergency")
        ),
        "emergency": len(emergency_queue),
        "occupied": sum(1 for r in rooms if not r.is_available),
        "free": sum(1 for r in rooms if r.is_available),
        "pending_bills": sum(
            1 for b in bills if b.payment_status != "PAID"
        ),
        "discharged": len(discharged),
    }

    return render_template(
        "home.html",
        stats=stats,
        queue=emergency_queue.get_all(),
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ---------- DOCTORS ----------

@app.route("/doctors")
def show_doctors():
    return render_template(
        "doctors.html",
        doctors=load_doctors(),
    )


@app.route("/add_doctor", methods=["GET", "POST"])
def add_doctor():
    if request.method == "POST":
        name = request.form["name"].strip()
        specialization = request.form["specialization"]

        try:
            experience = int(request.form["experience"])
        except ValueError:
            return "Experience must be a valid number.", 400

        is_available = request.form.get("available") == "on"

        if not name:
            return "Doctor name is required.", 400

        if experience < 0:
            return "Experience cannot be negative.", 400

        if specialization not in DOCTOR_TYPES:
            return "Invalid specialization.", 400

        doctor_id = next_id("doctors", "D", "doctor_id")

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO doctors
                (doctor_id, name, specialization, experience,
                 is_available, consultation_fee)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    doctor_id,
                    name,
                    specialization,
                    experience,
                    int(is_available),
                    DOCTOR_FEES[specialization],
                ),
            )

        return redirect("/doctors")

    return render_template(
        "doctor_form.html",
        doctor=None,
        types=DOCTOR_TYPES.keys(),
        title="Add New Doctor",
    )


@app.route("/edit/<doctor_id>", methods=["GET", "POST"])
def edit_doctor(doctor_id):
    doctors = load_doctors()
    doctor = next(
        (d for d in doctors if d.doctor_id == doctor_id),
        None,
    )

    if doctor is None:
        return "Doctor not found.", 404

    if request.method == "POST":
        name = request.form["name"].strip()
        specialization = request.form["specialization"]

        try:
            experience = int(request.form["experience"])
        except ValueError:
            return "Experience must be a valid number.", 400

        is_available = request.form.get("available") == "on"

        if not name:
            return "Doctor name is required.", 400

        if experience < 0:
            return "Experience cannot be negative.", 400

        if specialization not in DOCTOR_TYPES:
            return "Invalid specialization.", 400

        with get_connection() as conn:
            conn.execute(
                """
                UPDATE doctors
                SET name = ?, specialization = ?, experience = ?,
                    is_available = ?, consultation_fee = ?
                WHERE doctor_id = ?
                """,
                (
                    name,
                    specialization,
                    experience,
                    int(is_available),
                    DOCTOR_FEES[specialization],
                    doctor_id,
                ),
            )

        return redirect("/doctors")

    return render_template(
        "doctor_form.html",
        doctor=doctor,
        types=DOCTOR_TYPES.keys(),
        title="Edit Doctor",
    )


# ---------- PATIENTS ----------

@app.route("/patients")
def show_patients():
    return render_template(
        "patients.html",
        patients=load_patients(),
    )


@app.route("/register_patient", methods=["GET", "POST"])
def register_patient():
    if request.method == "POST":
        name = request.form["name"].strip()

        try:
            age = int(request.form["age"])
        except ValueError:
            return "Age must be a valid number.", 400

        phone = request.form["phone"].strip()
        email = request.form["email"].strip()
        disease = request.form["disease"].strip()
        blood_group = request.form["blood_group"]

        if not name or not phone or not disease:
            return "Name, phone and disease are required.", 400

        if age < 0 or age > 120:
            return "Age must be between 0 and 120.", 400

        if blood_group not in BLOOD_GROUPS:
            return "Invalid blood group.", 400

        patient_id = next_id("patients", "P", "patient_id")

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO patients
                (patient_id, name, age, phone, email, disease, blood_group)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    name,
                    age,
                    phone,
                    email,
                    disease,
                    blood_group,
                ),
            )

        return redirect("/patients")

    return render_template(
        "patient_form.html",
        blood_groups=BLOOD_GROUPS,
    )


# ---------- APPOINTMENTS ----------

@app.route("/book", methods=["GET", "POST"])
def book_appointment():
    patients = load_patients()
    doctors = load_doctors()
    error = None

    if request.method == "POST":
        patient = next(
            (
                p for p in patients
                if p.patient_id == request.form["patient_id"]
            ),
            None,
        )

        doctor = next(
            (
                d for d in doctors
                if d.doctor_id == request.form["doctor_id"]
            ),
            None,
        )

        try:
            if patient is None or doctor is None:
                raise ValueError("Please select a valid patient and doctor.")

            if not doctor.is_available:
                raise ValueError(
                    f"{doctor.name} is currently unavailable."
                )

            appointment_id = next_id(
                "appointments", "A", "appointment_id"
            )

            appointment = Appointment(
                appointment_id,
                patient,
                doctor,
                request.form["date"],
                request.form["time"],
                request.form["appointment_type"],
            )

            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO appointments
                    (appointment_id, patient_id, doctor_id,
                     appointment_date, appointment_time,
                     appointment_type, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        appointment.appointment_id,
                        patient.patient_id,
                        doctor.doctor_id,
                        appointment.date,
                        appointment.time,
                        appointment.appointment_type,
                        appointment.status,
                    ),
                )

            return redirect("/appointments")

        except ValueError as e:
            error = str(e)

    return render_template(
        "book.html",
        patients=patients,
        doctors=doctors,
        types=Appointment.TYPES,
        error=error,
    )


@app.route("/appointments")
def show_appointments():
    patients = load_patients()
    doctors = load_doctors()
    appointments = load_appointments(patients, doctors)

    return render_template(
        "appointments.html",
        appointments=appointments,
        error=None,
    )


@app.route(
    "/appointments/<appointment_id>/<action>",
    methods=["POST"],
)
def update_appointment(appointment_id, action):
    if action not in ("cancel", "complete"):
        return "Invalid action.", 400

    patients = load_patients()
    doctors = load_doctors()
    appointments = load_appointments(patients, doctors)

    appointment = next(
        (
            a for a in appointments
            if a.appointment_id == appointment_id
        ),
        None,
    )

    if appointment is None:
        return "Appointment not found.", 404

    try:
        if action == "cancel":
            appointment.cancel()
        else:
            appointment.complete()

        save_appointment_status(appointment)

    except ValueError as e:
        return render_template(
            "appointments.html",
            appointments=appointments,
            error=str(e),
        )

    return redirect("/appointments")


# ---------- EMERGENCY ----------

@app.route("/emergency", methods=["GET", "POST"])
def emergency():
    patients = load_patients()
    queue, treated = load_emergency_queue(patients)
    error = None

    if request.method == "POST":
        patient_id = request.form["patient_id"]

        try:
            level = int(request.form["level"])
        except ValueError:
            level = 0

        patient = next(
            (p for p in patients if p.patient_id == patient_id),
            None,
        )

        if patient is None:
            error = "Patient not found."

        elif level not in EmergencyPatient.LEVELS:
            error = "Priority level must be between 1 and 4."

        else:
            with get_connection() as conn:
                existing = conn.execute(
                    """
                    SELECT id
                    FROM emergency_records
                    WHERE patient_id = ? AND status = 'Waiting'
                    """,
                    (patient_id,),
                ).fetchone()

                if existing:
                    error = (
                        f"{patient.name} is already in the emergency queue."
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO emergency_records
                        (patient_id, priority_level, status)
                        VALUES (?, ?, 'Waiting')
                        """,
                        (patient_id, level),
                    )

                    return redirect("/emergency")

    return render_template(
        "emergency.html",
        queue=queue.get_all(),
        treated=treated,
        patients=patients,
        levels=EmergencyPatient.LEVELS,
        error=error,
    )


@app.route("/emergency/treat", methods=["POST"])
def treat_next():
    patients = load_patients()
    queue, _ = load_emergency_queue(patients)
    next_patient = queue.next_patient()

    if next_patient is not None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE emergency_records
                SET status = 'Treated'
                WHERE id = ? AND status = 'Waiting'
                """,
                (next_patient.record_id,),
            )

    return redirect("/emergency")


# ---------- ROOMS ----------

def render_rooms(error=None):
    patients = load_patients()
    rooms, release_log = load_rooms(patients)

    return render_template(
        "rooms.html",
        rooms=rooms,
        patients=patients,
        release_log=release_log,
        error=error,
    )


@app.route("/rooms", methods=["GET", "POST"])
def show_rooms():
    if request.method == "POST":
        try:
            room_number = int(request.form["room_number"])
        except ValueError:
            return render_rooms("Invalid room number.")

        patient_id = request.form["patient_id"]
        patients = load_patients()
        rooms, _ = load_rooms(patients)

        room = next(
            (r for r in rooms if r.room_number == room_number),
            None,
        )

        patient = next(
            (p for p in patients if p.patient_id == patient_id),
            None,
        )

        try:
            if room is None or patient is None:
                raise ValueError("Room or patient not found.")

            if not room.is_available:
                raise ValueError("This room is already occupied.")

            if any(
                r.patient and r.patient.patient_id == patient_id
                for r in rooms
            ):
                raise ValueError("This patient already has a room.")

            room.assign_room(patient)

            with get_connection() as conn:
                conn.execute(
                    """
                    UPDATE rooms
                    SET is_available = 0, patient_id = ?
                    WHERE room_number = ?
                    """,
                    (patient_id, room_number),
                )

            return redirect("/rooms")

        except ValueError as e:
            return render_rooms(str(e))

    return render_rooms()


@app.route("/rooms/<int:room_number>/release", methods=["POST"])
def release_room(room_number):
    patients = load_patients()
    rooms, _ = load_rooms(patients)

    room = next(
        (r for r in rooms if r.room_number == room_number),
        None,
    )

    if room is None or room.check_availability():
        return "Room not found or already available.", 404

    try:
        days = int(request.form["days"])
        charge = room.calculate_room_charge(days)
    except ValueError as e:
        return render_rooms(str(e))

    patient = room.patient

    if patient is None:
        return render_rooms(
            "This room has no linked patient. Please check the room record."
        )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO room_releases
            (room_number, patient_id, days, charge)
            VALUES (?, ?, ?, ?)
            """,
            (
                room.room_number,
                patient.patient_id,
                days,
                charge,
            ),
        )

        conn.execute(
            """
            UPDATE rooms
            SET is_available = 1, patient_id = NULL
            WHERE room_number = ?
            """,
            (room_number,),
        )

    return redirect("/rooms")

# ---------- MEDICINES ----------

@app.route("/medicines", methods=["GET", "POST"])
def medicines():
    patients = load_patients()
    error = None

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        medicine_name = request.form.get("medicine_name", "").strip()

        try:
            quantity = int(request.form.get("quantity", "0"))
            price = float(request.form.get("price", "0"))

            patient = next(
                (p for p in patients if p.patient_id == patient_id),
                None,
            )

            if patient is None:
                raise ValueError("Please select a valid patient.")

            if not medicine_name:
                raise ValueError("Medicine name is required.")

            if quantity <= 0 or price < 0:
                raise ValueError(
                    "Quantity must be positive and price cannot be negative."
                )

            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO medicine_records
                    (patient_id, medicine_name, quantity, price_per_unit)
                    VALUES (?, ?, ?, ?)
                    """,
                    (patient_id, medicine_name, quantity, price),
                )

            return redirect("/medicines")

        except ValueError as e:
            error = str(e)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT mr.*, p.name AS patient_name
            FROM medicine_records mr
            JOIN patients p ON p.patient_id = mr.patient_id
            ORDER BY mr.id DESC
            """
        ).fetchall()

    medicine_records = [
        {
            "patient_id": row["patient_id"],
            "patient_name": row["patient_name"],
            "medicine_name": row["medicine_name"],
            "quantity": row["quantity"],
            "price": row["price_per_unit"],
            "total": row["quantity"] * row["price_per_unit"],
        }
        for row in rows
    ]

    return render_template(
        "medicines.html",
        patients=patients,
        medicine_records=medicine_records,
        error=error,
    )
# ---------- BILLS ----------

def render_bills(error=None):
    patients = load_patients()
    bills = load_bills(patients)

    return render_template(
        "bills.html",
        bills=bills,
        patients=patients,
        error=error,
    )


@app.route("/bills", methods=["GET", "POST"])
def show_bills():
    if request.method == "POST":
        patients = load_patients()
        doctors = load_doctors()
        appointments = load_appointments(patients, doctors)
        _, release_log = load_rooms(patients)
        bills = load_bills(patients)

        patient_id = request.form.get("patient_id")

        patient = next(
            (p for p in patients if p.patient_id == patient_id),
            None,
        )

        try:
            if patient is None:
                raise ValueError("Please select a valid patient.")

            if any(
                b.patient.patient_id == patient.patient_id
                for b in bills
            ):
                raise ValueError("A bill already exists for this patient.")

            # 1. Consultation charges from appointments
            consultation = sum(
                a.doctor.calculate_consultation_fee()
                for a in appointments
                if a.patient.patient_id == patient.patient_id
                and a.status != "Cancelled"
            )

            # 2. Room charges from released rooms
            room_charge = sum(
                item["charge"]
                for item in release_log
                if item["patient_id"] == patient.patient_id
            )

            # 3. Emergency charges: demo rate per emergency record
            with get_connection() as conn:
                emergency_count = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM emergency_records
                    WHERE patient_id = ?
                    """,
                    (patient.patient_id,),
                ).fetchone()[0]

            emergency_amount = emergency_count * EMERGENCY_CHARGE

            # 4. Demo treatment charge: ₹500 per medical record
            with get_connection() as conn:
                treatment_count = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM medical_records
                    WHERE patient_id = ?
                    """,
                (patient.patient_id,),
                ).fetchone()[0]

                treatment = treatment_count * 500

            # 5. Medicine charges from saved medicine records
            with get_connection() as conn:
                medicine_total = conn.execute(
                    """
                    SELECT COALESCE(SUM(quantity * price_per_unit), 0)
                    FROM medicine_records
                    WHERE patient_id = ?
                    """,
                (patient.patient_id,),
                ).fetchone()[0]

                medicine = float(medicine_total)

            # 6. Insurance stays zero until actual policy/coverage data exists
            insurance = 0.0
            bill_id = next_id("bills", "B", "bill_id")

            bill = Bill(
                bill_id=bill_id,
                patient=patient,
                consultation=consultation,
                treatment=treatment,
                medicine=medicine,
                room=room_charge,
                emergency=emergency_amount,
                insurance=insurance,
            )

            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO bills (
                        bill_id, patient_id, consultation,
                        treatment, medicine, room, emergency,
                        insurance, paid
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        bill.bill_id,
                        patient.patient_id,
                        bill.consultation,
                        bill.treatment,
                        bill.medicine,
                        bill.room,
                        bill.emergency,
                        bill.insurance,
                    ),
                )

            return redirect("/bills")

        except ValueError as e:
            return render_bills(str(e))

    return render_bills()


@app.route("/bills/<bill_id>/pay", methods=["POST"])
def pay_bill(bill_id):
    patients = load_patients()
    bills = load_bills(patients)

    bill = next(
        (b for b in bills if b.bill_id == bill_id),
        None,
    )

    if bill is None:
        return "Bill not found.", 404

    try:
        amount = float(request.form["amount"])
        bill.make_payment(amount)

        with get_connection() as conn:
            conn.execute(
                "UPDATE bills SET paid = ? WHERE bill_id = ?",
                (bill.paid, bill.bill_id),
            )

            conn.execute(
                "INSERT INTO payments (bill_id, amount) VALUES (?, ?)",
                (bill.bill_id, amount),
            )

    except ValueError as e:
        return render_bills(str(e))

    return redirect("/bills")


# ---------- DISCHARGE ----------

@app.route("/discharge", methods=["GET", "POST"])
def discharge():
    patients = load_patients()
    bills = load_bills(patients)
    discharged = load_discharged(patients)
    result = None

    if request.method == "POST":
        patient = next(
            (
                p for p in patients
                if p.patient_id == request.form["patient_id"]
            ),
            None,
        )

        if patient is None:
            result = {
                "ok": False,
                "reasons": ["Patient not found."],
            }

        elif any(
            p.patient_id == patient.patient_id
            for p in discharged
        ):
            result = {
                "ok": False,
                "reasons": ["This patient has already been discharged."],
            }

        else:
            bill = next(
                (
                    b for b in bills
                    if b.patient.patient_id == patient.patient_id
                ),
                None,
            )

            treatment_completed = request.form.get("treatment") == "on"
            doctor_approval = request.form.get("approval") == "on"

            ok, reasons = discharge_patient(
                treatment_completed,
                doctor_approval,
                bill,
            )

            if ok:
                with get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO discharges
                        (patient_id, treatment_completed, doctor_approval)
                        VALUES (?, ?, ?)
                        """,
                        (
                            patient.patient_id,
                            int(treatment_completed),
                            int(doctor_approval),
                        ),
                    )

                discharged.append(patient)

            result = {
                "ok": ok,
                "reasons": reasons,
                "name": patient.name,
            }

    return render_template(
        "discharge.html",
        patients=patients,
        bills=bills,
        discharged=discharged,
        result=result,
    )


# ---------- START APPLICATION ----------

initialize_hospital()

if __name__ == "__main__":
    app.run(debug=True)
