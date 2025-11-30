from typing import List, Dict, Any, Optional, Union
from datetime import datetime, time, timedelta
from sqlmodel import Session, select, func
from models import RoleEnum, Report, Patient, Appointment, LabTest


def fetch_recent_activities(
    session: Session,
    role: Union[str, RoleEnum],
    # physician / lab_admin can be filtered by their account id
    user_id: Optional[int] = None,
    limit: int = 5
) -> List[Dict[str, str]]:
    """
    Returns a simple, ready-to-render list of recent activities tailored to the user's role.
    Each item: {"time": "Today, 9:05 AM", "message": "Text..."}.
    """

    # --- helpers ---
    now = datetime.utcnow()

    def _fmt(dt: datetime) -> str:
        if dt.date() == now.date():
            return dt.strftime("Today, %I:%M %p").replace(" 0", " ")
        elif dt.date() == (now.date() - timedelta(days=1)):
            return dt.strftime("Yesterday, %I:%M %p").replace(" 0", " ")
        return dt.strftime("%b %d, %I:%M %p").replace(" 0", " ")

    def _as_item(when: datetime, msg: str) -> Dict[str, str]:
        return {"time": _fmt(when), "message": msg}

    def _norm_role(r: Union[str, RoleEnum]) -> str:
        return r.value if isinstance(r, RoleEnum) else str(r)

    role_str = _norm_role(role).lower()
    items: List[Dict[str, Any]] = []

    # ------------------------------
    # ADMINISTRATOR: accounts + reports
    # ------------------------------
    if role_str == "administrator":
        # Recent reports (new)
        new_reports = session.exec(
            select(Report).order_by(Report.date.desc()).limit(8)
        ).all()
        for r in new_reports:
            rid = f"R-{(r.id or 0):04d}"
            if (r.priority or "").lower() == "high":
                items.append(
                    {"when": r.date, "msg": f"New critical report: {r.subject} ({rid})"})
            else:
                items.append(
                    {"when": r.date, "msg": f"New report: {r.subject} ({rid})"})

        # Recently resolved
        resolved = session.exec(
            select(Report)
            .where(Report.resolved_at.is_not(None))
            .order_by(Report.resolved_at.desc())
            .limit(6)
        ).all()
        for r in resolved:
            rid = f"R-{(r.id or 0):04d}"
            items.append(
                {"when": r.resolved_at, "msg": f"Resolved report: {r.subject} ({rid})"})

    # ------------------------------
    # PHYSICIAN: patients + lab tests (received) + appointments
    # ------------------------------
    elif role_str == "physician":
        # Upcoming appointments for this physician (next 24h)
        if user_id:
            upcoming = session.exec(
                select(Appointment)
                .where(Appointment.physician_id == user_id)
                .where(Appointment.datetime >= now)
                .where(Appointment.datetime <= now + timedelta(days=1))
                .order_by(Appointment.datetime.asc())
                .limit(6)
            ).all()
            for a in upcoming:
                items.append(
                    {"when": a.datetime, "msg": f"Upcoming appointment (Patient #{a.patient_id})"})

            # Recently released lab tests for this physician
            released = session.exec(
                select(LabTest)
                .where(LabTest.physician_id == user_id)
                .where(LabTest.status == "released")
                .order_by(LabTest.result_date.desc())
                .limit(6)
            ).all()
            for t in released:
                when = t.result_date or t.collection_date
                items.append({"when": datetime.combine(
                    when, datetime.min.time()), "msg": f"Lab test released (#{t.id})"})

            # Latest patients assigned to this physician (proxy by ID)
            latest_pts = session.exec(
                select(Patient)
                .where(Patient.physician_id == user_id)
                .order_by(Patient.id.desc())
                .limit(5)
            ).all()
            for i, p in enumerate(latest_pts):
                pseudo_when = now - timedelta(minutes=5 + i)
                items.append(
                    {"when": pseudo_when, "msg": f"Patient record updated: {p.name} (#{p.id})"})

    # ------------------------------
    # DATA RECEPTIONIST: patients (new/updated) + appointments
    # ------------------------------
    elif role_str == "data receptionist":
        # Latest patients (proxy by ID desc)
        latest_pts = session.exec(
            select(Patient).order_by(Patient.id.desc()).limit(8)
        ).all()
        for i, p in enumerate(latest_pts):
            pseudo_when = now - timedelta(minutes=i+1)
            items.append(
                {"when": pseudo_when, "msg": f"New/updated patient record: {p.name} (#{p.id})"})

        # Appointments coming in next day (for scheduling overview)
        upcoming = session.exec(
            select(Appointment)
            .where(Appointment.datetime >= now)
            .where(Appointment.datetime <= now + timedelta(days=1))
            .order_by(Appointment.datetime.asc())
            .limit(8)
        ).all()
        for a in upcoming:
            items.append(
                {"when": a.datetime, "msg": f"Upcoming appointment (Patient #{a.patient_id})"})

    # ------------------------------
    # LAB ADMINISTRATOR: lab test requests + reviews/results
    # ------------------------------
    elif role_str == "lab administrator":
        # Pending / ready / released (most recent first)
        pending = session.exec(
            select(LabTest)
            .where(LabTest.status == "pending")
            .order_by(LabTest.collection_date.desc())
            .limit(5)
        ).all()
        for t in pending:
            items.append({"when": datetime.combine(t.collection_date, datetime.min.time(
            )), "msg": f"New lab request pending (#{t.id})"})

        ready = session.exec(
            select(LabTest)
            .where(LabTest.status == "ready")
            .order_by(LabTest.collection_date.desc())
            .limit(5)
        ).all()
        for t in ready:
            items.append({"when": datetime.combine(t.collection_date, datetime.min.time(
            )), "msg": f"Lab result ready for review (#{t.id})"})

        released = session.exec(
            select(LabTest)
            .where(LabTest.status == "released")
            .order_by(LabTest.result_date.desc())
            .limit(6)
        ).all()
        for t in released:
            when = t.result_date or t.collection_date
            items.append({"when": datetime.combine(
                when, datetime.min.time()), "msg": f"Lab result released (#{t.id})"})

    # Fallback (unknown role): show nothing
    # ------------------------------

    # Final sort (newest first) & format
    items.sort(key=lambda x: x["when"], reverse=True)
    simple = [_as_item(x["when"], x["msg"]) for x in items[:limit]]
    return simple


def get_notifications(session: Session, role: Union[str, RoleEnum], user_id: Optional[int] = None, limit: int = 4) -> Dict[str, Any]:
    """
    Returns role-specific notification data for the home page.

    - physician -> {"type":"physician","items":[{"patient_name","info","time"}...]}
    - lab_admin -> {"type":"lab_admin","items":[{"patient_name","info","priority_text","priority_class"}...]}
    - data_receptionist -> {"type":"data_receptionist","summary":[{"count","title","subtitle"}...]}

    Keep it simple and template-friendly.
    """
    role_str = role.value if isinstance(role, RoleEnum) else str(role)
    role_str = role_str.lower()
    now = datetime.now()
    start_today = datetime.combine(now.date(), time.min)
    end_today = datetime.combine(now.date(), time.max)

    def fmt_time(dt: datetime) -> str:
        return dt.strftime("%I:%M %p").lstrip("0")

    summary: List[Dict[str, str]] = []

    if role_str == "physician":
        # Today's appointments for this physician

        appts: List[Appointment] = session.exec(
            select(Appointment)
            .where(Appointment.physician_id == user_id)
            .where(Appointment.datetime >= start_today)
            .where(Appointment.datetime <= end_today)
            .order_by(Appointment.datetime.asc())
            .limit(limit)
        ).all()

        for a in appts:
            p = session.get(Patient, a.patient_id)
            patient_name = p.name if p else f"Patient #{a.patient_id}"
            patient_code = f"P-{(p.id if p else a.patient_id):05d}"
            summary.append({
                "patient_name": patient_name,                            # e.g., "Amina Jameel"
                # e.g., "P-24502 • Follow-up"
                "info": f"{patient_code} • {a.purpose}",
                # e.g., "10:30 AM"
                "time": fmt_time(a.datetime),
            })

    if role_str == "lab administrator":
        # Recent lab tests to act on: pending/ready (review) + recently released
        tests: List[LabTest] = session.exec(
            select(LabTest)
            .where(LabTest.status.in_(["pending", "ready", "released"]))
            .order_by(LabTest.result_date.desc().nulls_last(), LabTest.collection_date.desc())
            .limit(limit)
        ).all()

        def priority_map(severity: Optional[str]) -> Dict[str, str]:
            sev = (severity or "").lower()
            if sev == "high":
                return {"text": "High Priority", "cls": "priority-high"}
            if sev == "medium":
                return {"text": "Medium Priority", "cls": "priority-medium"}
            return {"text": "Normal", "cls": "priority-low"}

        for t in tests:
            p = session.get(Patient, t.patient_id)
            patient_name = p.name if p else f"Patient #{t.patient_id}"
            patient_code = f"P-{(p.id if p else t.patient_id):05d}"
            pr = priority_map(t.severity)
            test_type = t.test_type or "Lab Test"
            summary.append({
                "patient_name": patient_name,                        # e.g., "Tayba Saeed"
                # e.g., "P-24505 • Blood Serum"
                "info": f"{patient_code} • {test_type}",
                # e.g., "High Priority"
                "priority_text": pr["text"],
                # e.g., "priority-high"
                "priority_class": pr["cls"],
            })

    if role_str == "data receptionist":
        # Summary boxes
        incomplete_records = session.exec(
            select(func.count()).select_from(Patient).where(Patient.is_complete == False)  # noqa: E712
        ).one()

        todays_appointments = session.exec(
            select(func.count()).select_from(Appointment)
            .where(Appointment.datetime >= start_today)
            .where(Appointment.datetime <= end_today)
        ).one()

        # Define "updates needed" simply as data_consent == False (adjust as you like)
        updates_needed = session.exec(
            select(func.count()).select_from(Patient).where(Patient.data_consent == False)  # noqa: E712
        ).one()

        summary = [
            {"count": incomplete_records, "title": "Incomplete Records",
                "subtitle": "Need additional information"},
            {"count": todays_appointments, "title": "Today's Appointments",
                "subtitle": "Patients scheduled for today"},
            {"count": updates_needed, "title": "Updates Needed",
                "subtitle": "Records requiring updates"},
        ]

    return {"summary": summary}
