class Patient:
    def __init__(
        self,
        patient_id,
        name,
        age,
        phone,
        email,
        disease,
        blood_group
    ):
        self.patient_id = patient_id
        self.name = name
        self.age = age
        self.phone = phone
        self.email = email
        self.disease = disease
        self.blood_group = blood_group
        self.__medical_history = []

    def add_medical_record(self, record):
        if not record or not record.strip():
            raise ValueError("Medical record cannot be empty.")

        self.__medical_history.append(record.strip())

    def view_medical_history(self):
        return self.__medical_history.copy()
