from datetime import datetime, timedelta, date
from models import Report, Patient, ModelFeatures, Appointment, LabTest
from sqlmodel import Session
import random


def insert_new_report(subject: str, type: str, priority: str, description: str, status: str, user_id: str, session: Session):

    report = Report(
        type=type,
        subject=subject.strip(),
        description=description.strip() or None,
        attachment=None,
        priority=priority,
        status=status,
        date=datetime.utcnow(),
        response=None,
        resolved_at=None,
        user_id=user_id,
    )

    session.add(report)
    session.commit()


def insert_new_patient(name: str, bdate: date, age: int, gestational_age: int, due_date: date, physician_id: int, data_consent: bool,
                       is_complete: bool, appointment_datetime: str, appointment_purpose: str, features: dict, session: Session):
    patient = Patient(
        name=name,
        bdate=datetime.strptime(bdate, "%Y-%m-%d").date(),
        age=age,
        gestational_age=gestational_age,
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date(),
        data_consent=True if data_consent == "on" else False,
        is_complete=True if is_complete == "on" else False,
        physician_id=physician_id,
    )

    session.add(patient)
    session.flush()
    patient_id = patient.id

    model_features = ModelFeatures(
        patient_id=patient_id,
        # JSON blobs
        input_features=features,
    )

    session.add(model_features)

    appointment = Appointment(
        purpose=appointment_purpose,
        datetime=datetime.strptime(appointment_datetime, "%Y-%m-%dT%H:%M"),
        status="scheduled",
        patient_id=patient_id,
        physician_id=physician_id,
    )
    session.add(appointment)
    session.commit()


def update_patient_notes(notes: str, patient_id: int, session: Session):
    patient = session.get(Patient, patient_id)
    if not patient:
        return 404

    # simple field update (assumes Patient has assessment_notes column)
    patient.notes = notes
    session.add(patient)
    session.commit()
    return 200


def insert_new_labtest_request(patient_id: int, physician_id: int, test_type: str, severity: str, session: Session):
    patient = session.get(Patient, patient_id)
    if not patient:
        return 404

    lab = LabTest(
        test_type=test_type,
        collection_date=datetime.utcnow().date(),  # simple string date
        result_date=None,
        technician="",
        notes=None,
        status="pending",
        severity=severity,
        is_released=False,
        risk="medium",
        pcb_result=[],   # assumes column accepts JSON/array
        patient_id=patient_id,
        physician_id=physician_id,
    )

    session.add(lab)
    session.commit()
    return 200


def dispatch_lab_test(db: Session, labtest_id: int) -> bool:
    """
    Simulate sending the test to the machine:
    - generate random PCB levels
    - compute total & risk
    - mark as released
    - save to DB

    Returns:
        True if successfully processed (or already released),
        False if lab test not found.
    """
    labtest = db.query(LabTest).filter(LabTest.id == labtest_id).first()
    if not labtest:
        return False

    # If already processed, do nothing – caller can still redirect to result.
    if labtest.is_released:
        return True

    # ---- Simulate PCB machine output ----
    pcb_names = [
        "PCB_74", "PCB_99", "PCB_118", "PCB_138",
        "PCB_153", "PCB_156", "PCB_170", "PCB_180",
        "PCB_183", "PCB_187",
    ]

    pcb_results = []
    for name in pcb_names:
        level = round(random.uniform(0.5, 4.0), 2)
        pcb_results.append({"name": name, "level": level})

    # If your column is TEXT (string) – like your CSV example:
    labtest.pcb_results = pcb_results
    # If it's JSON type instead, use:
    # labtest.pcb_results = pcb_results

    total_pcb = sum(item["level"] for item in pcb_results)

    if total_pcb < 15:
        risk = severity = "low"
    elif total_pcb < 25:
        risk = severity = "medium"
    else:
        risk = severity = "high"

    # ---- Update labtest fields ----
    labtest.status = "released"
    labtest.is_released = False
    labtest.severity = severity
    labtest.risk = risk
    labtest.result_date = date.today()
    labtest.technician = labtest.technician or "AutoMachine"

    if not labtest.notes:
        labtest.notes = "Automatically processed by machine simulation."

    db.commit()
    db.refresh(labtest)

    return True


def release_lab_test(db: Session, labtest_id: int) -> bool:
    """
    Mark a lab test as released to the physician.
    Returns True if found (even if already released), False if not found.
    """
    labtest = db.query(LabTest).filter(LabTest.id == labtest_id).first()
    if not labtest:
        return False

    # If you want to ignore repeated calls, just set and commit anyway
    labtest.is_released = True

    db.commit()
    db.refresh(labtest)
    return True
