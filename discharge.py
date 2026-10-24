def discharge_patient(treatment_completed, doctor_approval, bill):
    reasons = []

    if not treatment_completed:
        reasons.append("Treatment is not completed.")
    if not doctor_approval:
        reasons.append("Doctor ki approval baaki hai.")
    if bill is None:
        reasons.append("Bill is not generated.")
    elif bill.payment_status != "PAID":
        reasons.append("Payment is still pending.")

    return (len(reasons) == 0, reasons)