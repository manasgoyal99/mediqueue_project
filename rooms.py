class Room:
    room_type = "Room"
    price_per_day = 0

    def __init__(self, room_number):
        self.room_number = room_number
        self.is_available = True
        self.patient = None

    def check_availability(self):
        return self.is_available

    def assign_room(self, patient):
        if not self.is_available:
            raise ValueError(f"Room {self.room_number} already occupied hai.")
        self.patient = patient
        self.is_available = False

    def release_room(self):
        self.patient = None
        self.is_available = True

    def calculate_room_charge(self, days):
        if days <= 0:
            raise ValueError("Days 1 ya usse zyada hone chahiye.")
        return self.price_per_day * days


class GeneralWard(Room):
    room_type = "General Ward"
    price_per_day = 1000


class PrivateRoom(Room):
    room_type = "Private Room"
    price_per_day = 3000


class ICU(Room):
    room_type = "ICU"
    price_per_day = 7000


class EmergencyRoom(Room):
    room_type = "Emergency Room"
    price_per_day = 5000