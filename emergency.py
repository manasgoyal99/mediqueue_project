class EmergencyPatient:
    LEVELS = {1: "Critical", 2: "Serious", 3: "Moderate", 4: "Minor"}

    def __init__(self, patient, level):
        if level not in EmergencyPatient.LEVELS:
            raise ValueError("Level 1 se 4 ke beech hona chahiye.")
        self.patient = patient
        self.level = level

    @property
    def label(self):
        return EmergencyPatient.LEVELS[self.level]

    def __lt__(self, other):
        return self.level < other.level

    def __str__(self):
        return f"{self.patient.patient_id} -> Level {self.level} ({self.label})"


class EmergencyQueue:
    def __init__(self):
        self.__patients = []

    def add(self, emergency_patient):
        self.__patients.append(emergency_patient)
        self.__patients.sort()

    def next_patient(self):
        if not self.__patients:
            return None
        return self.__patients.pop(0)

    def get_all(self):
        return list(self.__patients)

    def __len__(self):
        return len(self.__patients)