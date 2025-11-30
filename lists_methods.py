from models import Account
from typing import Dict, Any, List, Set
from datetime import datetime, timedelta
from models import Patient, ModelFeatures, Appointment, Account, LabTest, Report
from sqlmodel import Session, select


def get_physician_patients_page(session: Session, physician_id: int) -> Dict[str, Any]:
    # --- patients for this physician ---
    patients = session.exec(
        select(Patient).where(Patient.physician_id == physician_id)
    ).all()

    # --- summary counts (risk + assessment from ModelFeatures) ---
    total_patients = len(patients)
    high_risk = sum(1 for p in patients if (p.risk or "").lower() == "high")
    medium_risk = sum(1 for p in patients if (
        p.risk or "").lower() == "medium")
    low_risk = sum(1 for p in patients if (p.risk or "").lower() == "low")

    assessed = 0  # has a ModelFeatures row with output_predictions
    # --- table records ---
    records: List[Dict[str, Any]] = []
    for p in patients:
        pid = f"P-{p.id:05d}"
        gest_age = f"{p.gestational_age} weeks" if p.gestational_age else "-"
        due = p.due_date.strftime("%b %d, %Y") if p.due_date else "-"

        # latest model assessment (prediction) for this patient
        mf = session.exec(
            select(ModelFeatures)
            .where(ModelFeatures.patient_id == p.id)
            .where(ModelFeatures.output_predictions.is_not(None))
            .order_by(ModelFeatures.date.desc())
        ).first()

        if mf:
            last_assessment = mf.date.strftime("%b %d, %Y")
            assessed += 1
        else:
            last_assessment = "-"

        # risk badge
        risk = (p.risk or "").lower()
        if risk == "high":
            status_class, status_text = "risk-high", "High"
        elif risk == "medium":
            status_class, status_text = "risk-medium", "Medium"
        elif risk == "low":
            status_class, status_text = "risk-low", "Low"
        else:
            status_class, status_text = "status-neutral", "-"

        records.append({
            "id": p.id,
            "fields": [pid, p.name, p.age, gest_age, due, last_assessment],
            "status": status_text,          # used by your badge cell
            "status_class": status_class,
            "action": "View",
        })

    pending = total_patients - assessed

    data = {
        "title": "Patients",
        "subtitle": "Manage and monitor patient records and model-based risk assessments",
        # controls button optional in your template -> omit to hide
        "summary": [
            {"number": total_patients, "label": "Total Patients"},
            {"number": high_risk, "label": "High Risk"},
            {"number": medium_risk, "label": "Medium Risk"},
            {"number": low_risk, "label": "Low Risk"},
            {"number": assessed, "label": "Assessed"},
            {"number": pending, "label": "Pending Assessment"},
        ],
        "search_placeholder": "Search patients by name or ID...",
        "filters": [
            {"options": ["All Risk Levels", "High Risk",
                         "Medium Risk", "Low Risk"]},
            {"options": ["All Gestational Ages",
                         "First Trimester (< 13 weeks)", "Second Trimester (13-26 weeks)", "Third Trimester (> 26 weeks)"]},
            {"options": ["All Assessment Status", "Assessed", "Pending"]},
        ],
        "attributes": [
            "Patient ID", "Name", "Age", "Gestational Age",
            "Due Date", "Last Assessment", "Risk Level", "Action"
        ],
        "records": records,
    }
    return data

# ------------------------------------------------------------------------------------------------


def get_data_clerk_patients_page(session: Session) -> Dict[str, Any]:
    now = datetime.utcnow()
    patients = session.exec(select(Patient).order_by(Patient.id.desc())).all()

    def data_status(p: Patient):
        # Incomplete > Needs Update > Complete
        if (not p.is_complete) or (p.gestational_age is None) or (p.due_date is None):
            return "Incomplete", "status-incomplete"
        notes = (p.notes or "").lower()
        if ("update" in notes) or ("review" in notes) or (p.risk is None):
            return "Needs Update", "status-update"
        return "Complete", "status-complete"

    def last_next_appointment(pid: int):
        appts = session.exec(
            select(Appointment).where(Appointment.patient_id == pid)
        ).all()
        if not appts:
            return None, None
        past = [a for a in appts if a.datetime <= now]
        future = [a for a in appts if a.datetime > now]
        last_dt = max((a.datetime for a in past), default=None)
        next_dt = min((a.datetime for a in future), default=None)
        def fmt(d): return d.strftime("%b %d, %Y") if d else "N/A"
        return fmt(last_dt), fmt(next_dt)

    records: List[Dict[str, Any]] = []
    for p in patients:
        pid_str = f"P-{p.id:05d}"
        # simple deterministic proxy so filters work (replace with created_at later)
        entry_dt = (now - timedelta(days=(p.id or 0) %
                    30)).strftime("%b %d, %Y")
        last_appt, next_appt = last_next_appointment(p.id)
        status_text, status_class = data_status(p)

        records.append({
            "id": p.id,
            "fields": [pid_str, p.name, entry_dt, last_appt, next_appt],
            "status": status_text,         # badge text
            "status_class": status_class,  # badge class
            "action": "Edit",
        })

    data = {
        "title": "Patient Records",
        "subtitle": "Enter and update patient data for PCB risk assessment",
        "primary_button": "Register New Patient",
        "primary_href": "patients/new",
        "summary": [
            {"number": len(patients), "label": "Total Patients"},
            {"number": sum(1 for p in patients if (not p.is_complete) or (
                p.gestational_age is None) or (p.due_date is None)), "label": "Incomplete Records"},
            {"number": sum(1 for p in patients if p.is_complete and (("update" in (p.notes or "").lower()) or (
                "review" in (p.notes or "").lower()) or (p.risk is None))), "label": "Requires Update"},
            {"number": sum(1 for p in patients if p.is_complete and p.gestational_age is not None and p.due_date is not None and ("update" not in (
                p.notes or "").lower()) and ("review" not in (p.notes or "").lower()) and (p.risk is not None)), "label": "Complete Records"},
        ],
        "search_placeholder": "Search patients by name, ID, or status...",
        "filters": [
            {"options": ["All Data Status", "Incomplete",
                         "Needs Update", "Complete"]},
            {"options": ["All Entry Dates", "Today", "Last 7 Days",
                         "Last 30 Days", "Older than 30 Days"]},
            {"options": ["All Appointment Status",
                         "With Upcoming Appointment", "No Upcoming Appointment"]},
        ],
        "attributes": [
            "Patient ID", "Name", "Data Entry Date", "Last Appointment",
            "Next Appointment", "Data Status", "Action"
        ],
        "records": records,
    }
    return data

# ---------------------------------------------------------------------------------------------------


def get_data_clerk_appointments_page(session: Session) -> Dict[str, Any]:
    now = datetime.utcnow()
    appts = session.exec(select(Appointment).order_by(
        Appointment.datetime.desc())).all()

    # Simple caches to avoid repeated DB hits
    patient_cache: Dict[int, Patient] = {}
    phys_cache: Dict[int, Account] = {}

    def patient_name(pid: int) -> str:
        if pid not in patient_cache:
            patient_cache[pid] = session.get(Patient, pid)
        return patient_cache[pid].name if patient_cache[pid] else f"Patient #{pid}"

    def physician_name(aid: int) -> str:
        if aid not in phys_cache:
            phys_cache[aid] = session.get(Account, aid)
        a = phys_cache[aid]
        return f"Dr. {a.first_name} {a.last_name}" if a else f"Physician #{aid}"

    # Summary counts
    total = len(appts)
    today_cnt = sum(1 for a in appts if a.datetime.date() == now.date())
    next7_cnt = sum(1 for a in appts if now <=
                    a.datetime <= now + timedelta(days=7))
    completed_cnt = sum(1 for a in appts if (
        a.status or "").lower() == "completed")

    # Records list
    records: List[Dict[str, Any]] = []
    physicians_seen: Set[str] = set()

    for a in appts:
        aid_str = f"AP-{a.id:03d}"
        p_name = patient_name(a.patient_id)
        doc = physician_name(a.physician_id)
        physicians_seen.add(doc)
        dt_text = a.datetime.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")

        # Map to your defined CSS classes
        st = (a.status or "").lower()
        if st == "completed":
            badge_class, status_text = "status-complete", "Completed"
        elif st == "cancelled":
            badge_class, status_text = "status-incomplete", "Cancelled"
        else:
            badge_class, status_text = "status-pending", "Scheduled"

        records.append({
            "id": a.id,
            "fields": [aid_str, p_name, a.purpose, dt_text, doc],
            "status": status_text,
            "status_class": badge_class,
            "action": "Edit",
        })

    data = {
        "title": "Appointments",
        "subtitle": "Manage and schedule patient appointments",

        "summary": [
            {"number": total, "label": "Total Appointments"},
            {"number": today_cnt, "label": "Today"},
            {"number": next7_cnt, "label": "Next 7 Days"},
            {"number": completed_cnt, "label": "Completed"},
        ],

        "search_placeholder": "Search by patient or appointment ID...",
        "filters": [
            {"options": ["All Status", "Scheduled", "Completed", "Cancelled"]},
            {"options": ["All Dates", "Today", "Next 7 Days",
                         "Next 30 Days", "Past Dates"]},
            {"options": ["All Physicians", *sorted(physicians_seen)]},
        ],

        "attributes": [
            "Appointment ID", "Patient", "Purpose", "Date/Time",
            "Physician", "Status", "Action"
        ],
        "records": records,
    }

    return data

# ----------------------------------------------------------------------------------------------


def get_physician_schedule_page(session: Session, physician_id: int) -> Dict[str, Any]:
    now = datetime.utcnow()

    appts = session.exec(
        select(Appointment).where(Appointment.physician_id == physician_id)
    ).all()

    # ----- sorting: scheduled future first (soonest), then others, completed at bottom -----
    def sort_key(a: Appointment):
        st = (a.status or "").lower()
        is_completed = (st == "completed")
        is_scheduled = (st == "scheduled")
        is_future = a.datetime >= now
        # We want: (0=scheduled future) -> (1=others) -> (2=completed)
        tier = 0 if (is_scheduled and is_future) else (
            2 if is_completed else 1)
        return (tier, a.datetime)

    appts.sort(key=sort_key)

    # ----- summary counts (scheduled-only logic for upcoming windows) -----
    upcoming_cnt = sum(1 for a in appts if (
        a.status or "").lower() == "scheduled" and a.datetime > now)
    today_cnt = sum(1 for a in appts if (a.status or "").lower()
                    == "scheduled" and a.datetime.date() == now.date())
    next7_cnt = sum(1 for a in appts if (a.status or "").lower(
    ) == "scheduled" and now <= a.datetime <= now + timedelta(days=7))
    completed_cnt = sum(1 for a in appts if (
        a.status or "").lower() == "completed")
    total_cnt = len(appts)

    # ----- build rows -----
    records: List[Dict[str, Any]] = []
    for a in appts:
        patient = session.get(Patient, a.patient_id)
        p_name = patient.name if patient else f"Patient #{a.patient_id}"

        aid_str = f"AP-{a.id:03d}"
        dt_txt = a.datetime.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")

        st = (a.status or "").lower()
        if st == "completed":
            badge, text = "status-complete", "Completed"
        elif st == "cancelled":
            badge, text = "status-incomplete", "Cancelled"
        else:
            badge, text = "status-pending", "Scheduled"

        records.append({
            "id": a.id,
            "fields": [aid_str, p_name, a.purpose, dt_txt],
            "status": text,
            "status_class": badge,   # matches your CSS map
            "action": "View",
        })

    data = {
        "title": "Schedule",
        "subtitle": "All appointments, closest first. Completed appear last.",
        "primary_button": "Schedule New Appointment",
        "primary_href": "/appointments/new",

        "summary": [
            {"number": total_cnt,    "label": "All Appointments"},
            {"number": upcoming_cnt, "label": "Upcoming"},
            {"number": today_cnt,    "label": "Today"},
            {"number": next7_cnt,    "label": "Next 7 Days"},
            {"number": completed_cnt, "label": "Completed"},
        ],

        "search_placeholder": "Search by patient or appointment ID...",
        "filters": [
            {"options": ["All Status", "Scheduled", "Completed", "Cancelled"]},
            # you already added the two date inputs; keep using those on the client side
        ],

        "attributes": ["Appointment ID", "Patient", "Purpose", "Date/Time", "Status", "Action"],
        "records": records,
    }
    return data


# -----------------------------------------------------------------------------


def get_admin_accounts_page(session: Session) -> Dict[str, Any]:
    accounts = session.exec(select(Account).order_by(Account.id.asc())).all()

    # unique sets
    roles: Set[str] = set()
    depts: Set[str] = set()

    total = len(accounts)
    active_cnt = sum(1 for a in accounts if a.is_active)
    inactive_cnt = total - active_cnt

    for a in accounts:
        roles.add(a.role)
        if a.department:
            depts.add(a.department)

    # table records
    records: List[Dict[str, Any]] = []
    for a in accounts:
        aid = f"A-{a.id:03d}" if isinstance(a.id, int) else str(a.id)
        name = f"{a.first_name} {a.last_name}".strip()
        status_txt = "Active" if a.is_active else "Inactive"
        status_class = "status-complete" if a.is_active else "status-incomplete"

        records.append({
            "id": a.id,
            "fields": [
                aid, name, a.username, a.role.title(),
                a.department or "-", a.email or "-", a.phone or "-"
            ],
            "status": status_txt,
            "status_class": status_class,
            "action": "Edit",
        })

    role_opts = ["All Roles"] + sorted(r.title() for r in roles)
    dept_opts = ["All Departments"] + sorted(depts)

    data: Dict[str, Any] = {
        "title": "Accounts Manager",
        "subtitle": "Create, update, and manage user accounts and roles",
        "primary_button": "Create Account",
        "primary_href": "/accounts/new",

        "summary": [
            {"number": total, "label": "Total Accounts"},
            {"number": active_cnt, "label": "Active"},
            {"number": inactive_cnt, "label": "Inactive"},
        ],

        "search_placeholder": "Search by name, username, or ID...",
        "filters": [
            {"options": role_opts},
            {"options": ["All Status", "Active", "Inactive"]},
            {"options": dept_opts},
        ],

        "attributes": [
            "Account ID", "Name", "Username", "Role",
            "Department", "Email", "Phone", "Active", "Action"
        ],
        "records": records,
    }
    return data
# -----------------------------------------------------------------------------------------


def get_admin_reports_page(session: Session) -> Dict[str, Any]:
    reports = session.exec(
        select(Report).order_by(Report.date.desc())
    ).all()

    now = datetime.utcnow()

    # --- helpers ---
    def fmt_id(i: int | None, prefix: str) -> str:
        if i is None:
            return "-"
        return f"{prefix}-{i:04d}"

    def human_date(dt: datetime | None) -> str:
        if not dt:
            return "-"
        return dt.strftime("%b %d, %Y")

    # summary counts
    total = len(reports)
    critical_issues = sum(1 for r in reports if (
        r.priority or "").lower() == "high")
    pending_review = sum(1 for r in reports if (r.status or "").lower() in {
                         "open", "in_progress", "pending"})
    resolved_cnt = sum(1 for r in reports if (
        r.status or "").lower() in {"resolved", "closed"})

    # dropdown sources
    types: Set[str] = set()
    statuses: Set[str] = set()

    # rows
    records: List[Dict[str, Any]] = []
    for r in reports:
        types.add(r.type or "Other")
        statuses.add((r.status or "open").title())

        # sender (Account)
        sender_display = "-"
        if r.user_id:
            acc = session.get(Account, r.user_id)
            if acc:
                sender_display = f"User ID: {fmt_id(acc.id, 'A')}"
            else:
                sender_display = f"User ID: {fmt_id(r.user_id, 'A')}"

        rid = fmt_id(r.id, "R")
        priority_txt = (r.priority or "-").title()
        status_txt = (r.status or "open").title()

        # map status to your CSS badge classes
        st_lower = status_txt.lower()
        if st_lower in {"resolved", "closed"}:
            badge = "status-resolved"
        elif st_lower in {"in_progress", "pending", "open"}:
            badge = "status-pending"
        else:
            badge = "status-pending"

        records.append({
            "id": r.id,
            "fields": [
                rid,                     # Report ID
                r.type or "-",           # Type
                r.subject or "-",        # Subject
                sender_display,          # Sender
                human_date(r.date),      # Date Reported
                priority_txt,            # Priority
            ],
            "status": status_txt,        # shows in the badge column
            "status_class": badge,
            "action": "Review",
        })

    data: Dict[str, Any] = {
        "title": "Issue Reports & Feedback",
        "subtitle": "Track and resolve system issues and user feedback.",
        "primary_button": "Export Reports",
        "primary_href": "/reports/export",

        "summary": [
            {"number": total,           "label": "Total Reports"},
            {"number": critical_issues, "label": "Critical Issues"},
            {"number": pending_review,  "label": "Pending Review"},
            {"number": resolved_cnt,    "label": "Resolved"},
        ],

        "search_placeholder": "Search by report ID, subject, or sender...",
        "filters": [
            {"options": ["All Types", *sorted(t for t in types if t)]},
            {"options": ["All Status", *sorted(s for s in statuses if s)]},
            {"options": ["All Dates", "Today", "Last 7 Days", "Last 30 Days"]},
        ],

        "attributes": [
            "Report ID", "Type", "Subject", "Sender",
            "Date Reported", "Priority", "Status", "Action"
        ],
        "records": records,
    }
    return data
# ---------------------------------------------------------------------------------


def get_lab_results_page(session: Session) -> Dict[str, Any]:
    tests = session.exec(
        select(LabTest).where(LabTest.status.in_(["ready", "released"]))
    ).all()
    now = datetime.utcnow()

    def tier(t: LabTest):
        s = (t.status or "").lower()
        return 0 if s == "released" else 1  # Released first, then Ready

    def dt_when(t: LabTest):
        return (t.result_date or t.collection_date or now)

    tests.sort(key=lambda t: (tier(t), dt_when(t)), reverse=True)

    total = len(tests)
    ready_cnt = sum(1 for t in tests if (t.status or "").lower() == "ready")
    released_cnt = sum(1 for t in tests if (
        t.status or "").lower() == "released")
    critical = sum(1 for t in tests if (t.severity or "").lower() == "high")

    test_types: Set[str] = set()
    records: List[Dict[str, Any]] = []

    for t in tests:
        test_types.add(t.test_type or "Unknown")
        pat = session.get(Patient, t.patient_id)
        pname = pat.name if pat else f"Patient #{t.patient_id}"
        tid = f"T-{t.id:05d}" if isinstance(t.id, int) else str(t.id)
        pid = f"P-{t.patient_id:05d}" if isinstance(
            t.patient_id, int) else str(t.patient_id)
        when = dt_when(t)
        when_txt = when.strftime("%b %d, %Y")

        s = (t.status or "").lower()
        if s == "released":
            badge, text = "status-complete", "Released"
        else:
            badge, text = "status-pending", "Ready"

        records.append({
            "id": t.id,
            "fields": [tid, pid, pname, (t.test_type or "-"), when_txt],
            "status": text,
            "status_class": badge,
            "action": "View",
        })

    data: Dict[str, Any] = {
        "title": "Lab Results",
        "subtitle": "Review and manage finalized and ready-to-release results",
        # "primary_button": "Enter New Result",
        # "primary_href": "/lab/results/new",

        "summary": [
            {"number": total,        "label": "Visible Results"},
            {"number": released_cnt, "label": "Released"},
            {"number": ready_cnt,    "label": "Ready"},
            {"number": critical,     "label": "Critical Severity"},
        ],

        "search_placeholder": "Search by patient name, ID, or test ID...",
        "filters": [
            {"options": ["All Status", "Ready", "Released"]},
            {"options": ["All Test Types", *
                         sorted(tt for tt in test_types if tt)]},
        ],

        "attributes": [
            "Test ID", "Patient ID", "Patient Name",
            "Test Type", "Collection Date", "Status", "Action"
        ],
        "records": records,
    }
    return data
# --------------------------------------------------------------------------------------


def get_lab_test_queue_page(session: Session) -> Dict[str, Any]:
    tests = session.exec(
        select(LabTest).where(LabTest.status == "pending")
    ).all()
    now = datetime.utcnow()

    # Oldest first to process in order
    tests.sort(key=lambda t: (t.collection_date or now))

    total = len(tests)
    test_types: Set[str] = set()
    records: List[Dict[str, Any]] = []

    for t in tests:
        test_types.add(t.test_type or "Unknown")
        pat = session.get(Patient, t.patient_id)
        pname = pat.name if pat else f"Patient #{t.patient_id}"
        tid = f"T-{t.id:05d}" if isinstance(t.id, int) else str(t.id)
        pid = f"P-{t.patient_id:05d}" if isinstance(
            t.patient_id, int) else str(t.patient_id)
        when_txt = (t.collection_date.strftime(
            "%b %d, %Y") if t.collection_date else "-")

        records.append({
            "id": t.id,
            "fields": [tid, pid, pname, (t.test_type or "-"), when_txt],
            "status": "Pending",
            "status_class": "status-incomplete",
            "action": "Process",
        })

    data: Dict[str, Any] = {
        "title": "Test Requests",
        "subtitle": "Process incoming requests awaiting results",
        # "primary_button": "Enter New Result",
        # "primary_href": "/lab/results/new",

        "summary": [
            {"number": total, "label": "Pending Requests"},
        ],

        "search_placeholder": "Search by patient name, ID, or test ID...",
        "filters": [
            {"options": ["All Test Types", *
                         sorted(tt for tt in test_types if tt)]},
        ],

        "attributes": [
            "Request ID", "Patient ID", "Patient Name",
            "Test Type", "Collected On", "Status", "Action"
        ],
        "records": records,
    }
    return data

# ----------------------------------------------------------------------------------------
