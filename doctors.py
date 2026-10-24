
class Doctor:
    def __init__(
        self,
        doctor_id,
        name,
        specialization,
        experience,
        is_available=True
    ):
        self.doctor_id = doctor_id
        self.name = name
        self.specialization = specialization
        self.experience = experience
        self.is_available = is_available

    def calculate_consultation_fee(self):
        return 0


class GeneralPhysician(Doctor):
    def calculate_consultation_fee(self):
        return 500


class Cardiologist(Doctor):
    def calculate_consultation_fee(self):
        return 1500


class Neurologist(Doctor):
    def calculate_consultation_fee(self):
        return 1800


class Surgeon(Doctor):
    def calculate_consultation_fee(self):
        return 2500
