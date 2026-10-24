class Appointment:
    TYPES = ["Regular", "Follow-up", "Emergency"]

    def __init__(self, appointment_id, patient, doctor, date, time, appointment_type):
        if not doctor.is_available:
            raise ValueError(f"{doctor.name} abhi available nahi hain.")

        if appointment_type not in Appointment.TYPES:
            raise ValueError("Appointment type galat hai.")

        self.appointment_id = appointment_id
        self.patient = patient
        self.doctor = doctor
        self.date = date
        self.time = time
        self.appointment_type = appointment_type

        if appointment_type == "Emergency":
            self.status = "Emergency"
        else:
            self.status = "Scheduled"

    def cancel(self):
        if self.status == "Completed":
            raise ValueError("Completed appointment cancel nahi ho sakti.")
        self.status = "Cancelled"

    def complete(self):
        if self.status == "Cancelled":
            raise ValueError("Cancelled appointment complete nahi ho sakti.")
        self.status = "Completed"

    def __str__(self):
        return (f"{self.appointment_id}: {self.patient.name} -> {self.doctor.name} "
                f"({self.date} {self.time}, {self.appointment_type}, {self.status})")