class Bill:
    def __init__(self, bill_id, patient, consultation=0, treatment=0,
                 medicine=0, room=0, emergency=0, insurance=0):
        self.bill_id = bill_id
        self.patient = patient
        self.consultation = consultation
        self.treatment = treatment
        self.medicine = medicine
        self.room = room
        self.emergency = emergency
        self.insurance = insurance
        self.paid = 0

    def final_amount(self):
        total = (self.consultation + self.treatment + self.medicine
                 + self.room + self.emergency)
        return max(total - self.insurance, 0)

    def balance(self):
        return self.final_amount() - self.paid

    @property
    def payment_status(self):
        if self.paid >= self.final_amount():
            return "PAID"
        if self.paid > 0:
            return "PARTIALLY PAID"
        return "PENDING"

    def make_payment(self, amount):
        if amount <= 0:
            raise ValueError("Amount 0 se zyada hona chahiye.")
        if amount > self.balance():
            raise ValueError("Amount baaki balance se zyada hai.")
        self.paid += amount

    def generate_bill(self):
        lines = [
            f"Consultation Fee : Rs{self.consultation}",
            f"Treatment        : Rs{self.treatment}",
            f"Medicines        : Rs{self.medicine}",
            f"Room Charges     : Rs{self.room}",
            f"Emergency        : Rs{self.emergency}",
            f"Insurance        : -Rs{self.insurance}",
            f"Final Amount     : Rs{self.final_amount()}",
            f"Payment Status   : {self.payment_status}",
        ]
        return "\n".join(lines)