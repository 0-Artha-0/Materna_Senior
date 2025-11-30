from datetime import datetime, date
from typing import Dict, Any, Optional, List
from sqlmodel import Session, select
from models import Patient, ModelFeatures, LabTest, Account
import json

# --- tiny helpers -------------------------------------------------


def _fmt_date(d: Optional[datetime | date]) -> str:
    if not d:
        return "N/A"
    if isinstance(d, date) and not isinstance(d, datetime):
        d = datetime.combine(d, datetime.min.time())
    return d.strftime("%b %d, %Y")


def _risk_badge_class(risk: Optional[str]) -> str:
    r = (risk or "").lower()
    if r.startswith("high"):
        return "risk-high"
    if r.startswith("medium"):
        return "risk-medium"
    return "risk-low"


def _bmi_value_class(bmi: Optional[float]) -> str:
    if bmi is None:
        return ""
    # flag underweight or overweight/obese
    return "bmi-warning" if (bmi < 18.5 or bmi >= 25.0) else ""


def _status_level_class(n: Optional[float | int]) -> str:
    """
    Map a numeric 'intensity' (1/2/3...) to status-1/2/3 for coloring.
    Falls back to '' if n isn't usable.
    """
    try:
        v = int(round(float(n)))
        if v >= 3:
            return "status-3"
        if v == 2:
            return "status-2"
        if v == 1:
            return "status-1"
    except Exception:
        pass
    return ""


def _lab_level_class(level: Optional[float]) -> str:
    """
    Simple visual thresholds for ng/g_lipid:
      <= 1.5 -> status-1 (greenish)
      <= 3.0 -> status-2 (amber)
      >  3.0 -> status-3 (coral)
    Adjust later if you adopt clinical cutoffs.
    """
    if level is None:
        return ""
    if level <= 1.5:
        return "status-1"
    if level <= 3.0:
        return "status-2"
    return "status-3"


def _latest_features(session: Session, patient_id: int) -> Optional[ModelFeatures]:
    mf = session.exec(
        select(ModelFeatures)
        .where(ModelFeatures.patient_id == patient_id)
        .order_by(ModelFeatures.date.desc())
        .limit(1)
    ).first()
    return mf


def _latest_released_lab(session: Session, patient_id: int) -> Optional[LabTest]:
    return session.exec(
        select(LabTest)
        .where(LabTest.patient_id == patient_id, LabTest.status.in_(["ready", "released"]))
        .order_by(LabTest.result_date.desc(), LabTest.collection_date.desc())
        .limit(1)
    ).first()

# --- main builder -------------------------------------------------


def get_physician_patient_profile(session: Session, patient_id: int) -> Dict[str, Any]:
    p: Patient | None = session.get(Patient, patient_id)
    if not p:
        return {
            "patient_name": "Not found",
            "patient_id": f"P-{patient_id}",
            "personal_info": [],
            "lifestyle_info": [],
            "diet_info": [],
            "environmental_info": [],
            "lab_results": [],
            "assessment_notes": "No notes available.",
        }

    mf = _latest_features(session, p.id)
    feats: Dict[str, Any] = (mf.input_features or {}) if mf else {}

    def _freq_label(code: Any) -> str:
        try:
            c = int(code)
        except (TypeError, ValueError):
            return "N/A"
        mapping = {
            1: "Less than once a month or never",
            2: "1–3 times a month",
            3: "Once a week",
            4: "2–4 times a week",
            5: "5–6 times a week",
            6: "Once a day",
            7: "2–3 times a day",
            8: "More than 4 times a day",
        }
        return mapping.get(c, f"Code {c}")

    # ---------- header ----------
    data: Dict[str, Any] = {
        "patient_name": p.name,
        "patient_id": f"P-{p.id}",
    }

    # ---------- basic info ----------
    bmi = None
    try:
        bmi = float(feats.get("BMI")) if feats.get("BMI") is not None else None
    except Exception:
        bmi = None

    edu_code = feats.get("Maternal Education")
    edu_map = {
        1: "No job-related training after school",
        2: "Technical / trade school",
        3: "College-level diploma",
        4: "Applied sciences university",
        5: "University degree",
        6: "Other education",
    }
    edu_label = edu_map.get(edu_code, "N/A")

    personal_info: List[Dict[str, Any]] = [
        {"label": "Age", "value": str(p.age or "-")},
        {
            "label": "Gestational Age",
            "value": f"{p.gestational_age} weeks" if p.gestational_age is not None else "N/A",
        },
        {"label": "Due Date", "value": _fmt_date(p.due_date)},
        {"label": "Educational Level", "value": edu_label},
        {
            "label": "BMI",
            "value": f"{bmi:.1f}" if bmi is not None else "N/A",
            "value_class": _bmi_value_class(bmi),
        },
        {
            "label": "Risk Level",
            "value": (p.risk or "").title(),
            "badge_class": _risk_badge_class(p.risk),
        },
        {
            "label": "Last Assessment",
            "value": _fmt_date(mf.date if mf else None),
        },
    ]
    data["personal_info"] = personal_info

    # ---------- lifestyle ----------
    lifestyle_info: List[Dict[str, Any]] = []

    smoking = feats.get("Smoking")
    smoking_map = {
        1: "Never smoked regularly",
        2: "Quit before pregnancy",
        3: "Quit when pregnancy was confirmed",
        4: "Quit later in pregnancy",
        5: "Smoked during pregnancy",
    }
    lifestyle_info.append({
        "label": "Smoking Status",
        "value": smoking_map.get(smoking, "N/A"),
        "value_class": _status_level_class(smoking),
    })

    alcohol = feats.get("Alcohol")
    alcohol_map = {
        1: "No alcohol at all",
        2: "A few times during pregnancy",
        3: "Monthly",
        4: "Weekly",
        5: "Several times a week",
    }
    lifestyle_info.append({
        "label": "Alcohol Use During Pregnancy",
        "value": alcohol_map.get(alcohol, "N/A"),
        "value_class": _status_level_class(alcohol),
    })

    vacc = feats.get("Q30 Have you received vaccines according to the vaccination program?") \
        or feats.get("Vaccination program")
    vacc_map = {
        1: "Yes, up to date",
        2: "No / not fully up to date",
    }
    lifestyle_info.append({
        "label": "Vaccinations",
        "value": vacc_map.get(vacc, "N/A"),
    })

    data["lifestyle_info"] = lifestyle_info

    # ---------- dietary ----------
    diet_info: List[Dict[str, Any]] = []

    daily_dairy = feats.get("Daily dairy doses")
    if daily_dairy is not None:
        diet_info.append({
            "label": "Dairy Portions Per Day",
            "value": f"{daily_dairy} portions/day",
        })

    cheese_slices = feats.get("Cheese slices")
    if cheese_slices is not None:
        diet_info.append({
            "label": "Cheese Slices Per Day",
            "value": f"{cheese_slices} slices/day",
        })

    sum_dairy = feats.get("Sum of dairy products")
    if sum_dairy is not None:
        try:
            sum_val = float(sum_dairy)
        except Exception:
            sum_val = None
        diet_info.append({
            "label": "Total Dairy Intake",
            "value": f"{sum_val:.1f} portions/day" if sum_val is not None else "N/A",
        })

    cups_coffee = feats.get("Cups of coffee")
    cups_tea = feats.get("Cups of tea")
    cups_green = feats.get("Cups of green tea")

    if cups_coffee is not None:
        diet_info.append({
            "label": "Coffee Per Day",
            "value": f"{cups_coffee} cups/day",
        })
    if cups_tea is not None:
        diet_info.append({
            "label": "Tea Per Day",
            "value": f"{cups_tea} cups/day",
        })
    if cups_green is not None:
        diet_info.append({
            "label": "Green Tea Per Day",
            "value": f"{cups_green} cups/day",
        })

    fish_dishes = feats.get("Fish dishes")
    if fish_dishes is not None:
        diet_info.append({
            "label": "Fish Dishes Frequency",
            "value": _freq_label(fish_dishes),
        })

    trout_salmon = feats.get("Trout/Salmon")
    if trout_salmon is not None:
        diet_info.append({
            "label": "Trout / Norwegian Salmon",
            "value": _freq_label(trout_salmon),
        })

    lake_fish = feats.get("Lake fish")
    if lake_fish is not None:
        diet_info.append({
            "label": "Lake Fish",
            "value": _freq_label(lake_fish),
        })

    apple = feats.get("Apple")
    if apple is not None:
        diet_info.append({
            "label": "Apple",
            "value": _freq_label(apple),
        })

    apple_juice = feats.get("Apple juice")
    if apple_juice is not None:
        diet_info.append({
            "label": "Apple Juice",
            "value": _freq_label(apple_juice),
        })

    grilled_food = feats.get("Grilled food")
    if grilled_food is not None:
        diet_info.append({
            "label": "Grilled Food",
            "value": _freq_label(grilled_food),
        })

    smoked_food = feats.get("Smoked food")
    if smoked_food is not None:
        diet_info.append({
            "label": "Smoked Food",
            "value": _freq_label(smoked_food),
        })

    breaded_food = feats.get("Breaded food")
    if breaded_food is not None:
        diet_info.append({
            "label": "Breaded Meat/Fish",
            "value": _freq_label(breaded_food),
        })

    data["diet_info"] = diet_info

    # ---------- environmental & supplements ----------
    environmental_info: List[Dict[str, Any]] = []

    chem = feats.get("Chemical exposure")
    chem_map = {
        1: "No exposure",
        2: "Yes, before pregnancy",
        3: "Yes, during pregnancy",
        4: "Yes, before and during pregnancy",
    }
    environmental_info.append({
        "label": "Chemical / Solvent Exposure at Work",
        "value": chem_map.get(chem, "N/A"),
        "value_class": _status_level_class(chem),
    })

    total_preps = feats.get("Q120.6 The total number of preparations")
    if total_preps is not None:
        environmental_info.append({
            "label": "Number of Different Preparations",
            "value": str(total_preps),
        })

    iron = feats.get("Q204 Iron -containing preparation during pregnancy")
    iron_map = {
        0: "No iron preparations",
        1: "Iron preparation",
        2: "In multivitamin / with calcium",
        3: "Several products at the same time",
        4: "Occasional use",
        5: "Multivitamin (type/timing unspecified)",
    }
    if iron is not None:
        environmental_info.append({
            "label": "Iron-containing Preparation",
            "value": iron_map.get(iron, f"Code {iron}"),
        })

    data["environmental_info"] = environmental_info

    # ---------- lab results (latest released/ready test) ----------
    lab_cards: List[Dict[str, Any]] = []
    lt = _latest_released_lab(session, p.id)
    if lt and lt.pcb_results:
        for row in lt.pcb_results:
            name = str(row.get("name", "")).replace("_", "-")
            level = row.get("level")
            lab_cards.append({
                "label": f"{name} Levels",
                "value": f"{level} ng/g_lipid" if level is not None else "N/A",
                "value_class": _lab_level_class(float(level) if level is not None else None),
            })
    data["lab_results"] = lab_cards

    # ---------- assessment notes ----------
    data["assessment_notes"] = (p.notes or "").strip() or "No notes available."

    return data


# --- helpers (tiny, safe) -------------------------------------------------

def _yn(v: Optional[int]) -> str:
    # 0/1 flag to "Yes (1)" / "No (0)"
    return "Yes (1)" if (v == 1) else "No (0)"


def _chem_text(v: Optional[int]) -> str:
    # simple categorical text seen in your mock
    if v == 3:
        return "Yes (During Pregnancy) (3)"
    if v == 2:
        return "Yes (Before Pregnancy) (2)"
    if v == 1:
        return "Yes (1)"
    return "No (0)"

# --- main builder ----------------------------------------------------------


def get_assessment_view_data(session: Session, patient_id: int) -> Dict[str, Any]:
    p: Patient | None = session.get(Patient, patient_id)
    if not p:
        return {
            "patient_name": "Not found",
            "patient_id": f"P-{patient_id}",
            "personal_info": [],
            "features": []
        }

    mf = _latest_features(session, p.id)
    feats: Dict[str, Any] = (mf.input_features or {}) if mf else {}
    lt = _latest_released_lab(session, p.id)

    def _freq_label(code: Any) -> str:
        """Map 1–8 frequency codes to human text."""
        try:
            c = int(code)
        except (TypeError, ValueError):
            return "N/A"
        mapping = {
            1: "Less than once a month or never",
            2: "1–3 times a month",
            3: "Once a week",
            4: "2–4 times a week",
            5: "5–6 times a week",
            6: "Once a day",
            7: "2–3 times a day",
            8: "More than 4 times a day",
        }
        return mapping.get(c, f"Code {c}")

    # ---------------- header ----------------
    data: Dict[str, Any] = {
        "id": p.id,
        "patient_name": p.name,
        "patient_id": f"P-{p.id}",
    }

    # ---------------- personal info ----------------
    bmi_val = None
    try:
        if feats.get("BMI") is not None:
            bmi_val = float(feats.get("BMI"))
    except Exception:
        bmi_val = None

    personal_info: List[Dict[str, str]] = [
        {"label": "Age", "value": str(p.age or "-")},
        {
            "label": "Gestational Age",
            "value": f"{p.gestational_age} weeks" if p.gestational_age is not None else "N/A"
        },
        {"label": "Due Date", "value": _fmt_date(p.due_date)},
        {
            "label": "Risk Level",
            "value": (p.risk or "").title() or "-"
        },
        {
            "label": "Last Assessment",
            "value": _fmt_date(mf.date if mf else None)
        },
        {
            "label": "BMI",
            "value": f"{bmi_val:.1f}" if bmi_val is not None else "N/A"
        },
    ]
    data["personal_info"] = personal_info

    # ---------------- features (model inputs) ----------------
    features: List[Dict[str, str]] = []

    # ---- Lifestyle / education ----
    edu_code = feats.get("Maternal Education")
    edu_map = {
        1: "No job-related training after school",
        2: "Technical / trade school",
        3: "College-level diploma",
        4: "Applied sciences university",
        5: "University degree",
        6: "Other education",
    }
    features.append({
        "label": "Maternal Education",
        "value": edu_map.get(edu_code, "N/A"),
    })

    smoking = feats.get("Smoking")
    smoking_map = {
        1: "Never smoked regularly",
        2: "Quit before pregnancy",
        3: "Quit when pregnancy was confirmed",
        4: "Quit later in pregnancy",
        5: "Smoked during pregnancy",
    }
    features.append({
        "label": "Smoking Status",
        "value": smoking_map.get(smoking, "N/A"),
    })

    alcohol = feats.get("Alcohol")
    alcohol_map = {
        1: "No alcohol at all",
        2: "A few times during pregnancy",
        3: "Monthly",
        4: "Weekly",
        5: "Several times a week",
    }
    features.append({
        "label": "Alcohol Consumption",
        "value": alcohol_map.get(alcohol, "N/A"),
    })

    vacc = feats.get("Q30 Have you received vaccines according to the vaccination program?") \
        or feats.get("Vaccination program")
    vacc_map = {
        1: "Yes",
        2: "No",
    }
    features.append({
        "label": "Vaccinations Up to Date",
        "value": vacc_map.get(vacc, "N/A"),
    })

    if bmi_val is not None:
        features.append({
            "label": "BMI",
            "value": f"{bmi_val:.1f}",
        })

    # ---- Dairy & drinks ----
    daily_dairy = feats.get("Daily dairy doses")
    if daily_dairy is not None:
        features.append({
            "label": "Dairy Portions Per Day",
            "value": f"{daily_dairy} portions/day",
        })

    cheese_slices = feats.get("Cheese slices")
    if cheese_slices is not None:
        features.append({
            "label": "Cheese Slices Per Day",
            "value": f"{cheese_slices} slices/day",
        })

    dairy_sum = feats.get("Sum of dairy products")
    if dairy_sum is not None:
        try:
            s_val = float(dairy_sum)
        except Exception:
            s_val = None
        features.append({
            "label": "Total Dairy Intake (All Products)",
            "value": f"{s_val:.1f} portions/day" if s_val is not None else "N/A",
        })

    cups_coffee = feats.get("Cups of coffee")
    cups_tea = feats.get("Cups of tea")
    cups_green = feats.get("Cups of green tea")

    if cups_coffee is not None:
        features.append({
            "label": "Cups of Coffee Per Day",
            "value": f"{cups_coffee} cups/day",
        })
    if cups_tea is not None:
        features.append({
            "label": "Cups of Tea Per Day",
            "value": f"{cups_tea} cups/day",
        })
    if cups_green is not None:
        features.append({
            "label": "Cups of Green Tea Per Day",
            "value": f"{cups_green} cups/day",
        })

    # ---- Bread & potatoes ----
    rye = feats.get("Rye bread")
    if rye is not None:
        features.append({
            "label": "Rye / Crispbread",
            "value": _freq_label(rye),
        })

    mixed = feats.get("Mixed bread")
    if mixed is not None:
        features.append({
            "label": "Yeast / Graham / Mixed Bread",
            "value": _freq_label(mixed),
        })

    boiled = feats.get("Boiled potatoes")
    if boiled is not None:
        features.append({
            "label": "Boiled Potatoes / Mash",
            "value": _freq_label(boiled),
        })

    fried = feats.get("Fried potatoes")
    if fried is not None:
        features.append({
            "label": "Fried Potatoes / Fries",
            "value": _freq_label(fried),
        })

    # ---- Meat, poultry & eggs ----
    beef = feats.get("Beef or pork")
    if beef is not None:
        features.append({
            "label": "Beef or Pork",
            "value": _freq_label(beef),
        })

    game = feats.get("Reindeer/game meat")
    if game is not None:
        features.append({
            "label": "Reindeer / Game Meat",
            "value": _freq_label(game),
        })

    light_meat = feats.get("Light meat")
    if light_meat is not None:
        features.append({
            "label": "Light Meat (e.g. Chicken)",
            "value": _freq_label(light_meat),
        })

    sausage = feats.get("Sausage dishes")
    if sausage is not None:
        features.append({
            "label": "Sausage Dishes",
            "value": _freq_label(sausage),
        })

    eggs = feats.get("Eggs")
    if eggs is not None:
        features.append({
            "label": "Eggs",
            "value": _freq_label(eggs),
        })

    # ---- Fish & seafood ----
    fish_dishes = feats.get("Fish dishes")
    if fish_dishes is not None:
        features.append({
            "label": "Fish Dishes (Total)",
            "value": _freq_label(fish_dishes),
        })

    trout_salmon = feats.get("Trout/Salmon")
    if trout_salmon is not None:
        features.append({
            "label": "Rainbow Trout / Norwegian Salmon",
            "value": _freq_label(trout_salmon),
        })

    native_salmon = feats.get("Q67 Native salmon")
    if native_salmon is not None:
        features.append({
            "label": "Domestic Sea Salmon",
            "value": _freq_label(native_salmon),
        })

    lake_fish = feats.get("Lake fish")
    if lake_fish is not None:
        features.append({
            "label": "Lake Fish",
            "value": _freq_label(lake_fish),
        })

    frozen_fish = feats.get("Frozen fish")
    if frozen_fish is not None:
        features.append({
            "label": "Frozen Fish Products",
            "value": _freq_label(frozen_fish),
        })

    shrimp = feats.get("Shrimp")
    if shrimp is not None:
        features.append({
            "label": "Shrimp",
            "value": _freq_label(shrimp),
        })

    # ---- Fruits, juices, cooking styles ----
    apple = feats.get("Apple")
    if apple is not None:
        features.append({
            "label": "Apple",
            "value": _freq_label(apple),
        })

    apple_juice = feats.get("Apple juice")
    if apple_juice is not None:
        features.append({
            "label": "Apple Juice",
            "value": _freq_label(apple_juice),
        })

    grilled_food = feats.get("Grilled food")
    if grilled_food is not None:
        features.append({
            "label": "Grilled Meat / Fish / Vegetables",
            "value": _freq_label(grilled_food),
        })

    smoked_food = feats.get("Smoked food")
    if smoked_food is not None:
        features.append({
            "label": "Smoked Meat or Fish",
            "value": _freq_label(smoked_food),
        })

    breaded_food = feats.get("Breaded food")
    if breaded_food is not None:
        features.append({
            "label": "Breaded Meat or Fish",
            "value": _freq_label(breaded_food),
        })

    # ---- Environment & supplements ----
    chem = feats.get("Chemical exposure")
    features.append({
        "label": "Workplace Chemical Exposure",
        "value": _chem_text(chem),
    })

    total_preps = feats.get("Q120.6 The total number of preparations")
    if total_preps is not None:
        features.append({
            "label": "Total Number of Preparations",
            "value": str(total_preps),
        })

    iron = feats.get("Q204 Iron -containing preparation during pregnancy")
    if iron is not None:
        iron_map = {
            0: "No iron preparations",
            1: "Iron preparation",
            2: "In multivitamin / with calcium",
            3: "Several products at the same time",
            4: "Occasional use",
            5: "Multivitamin (type/timing unspecified)",
        }
        features.append({
            "label": "Iron-containing Preparation",
            "value": iron_map.get(iron, f"Code {iron}"),
        })

    # ---------------- lab PCBs (also inputs) ----------------
    if lt and lt.pcb_results:
        for row in lt.pcb_results:
            name = str(row.get("name", "")).replace("_", " ")
            level = row.get("level")
            label = f"{name} Concentration".replace("PCB ", "PCB-")
            value = f"{level} ng/g_lipid" if level is not None else "N/A"
            features.append({"label": label, "value": value})

    data["features"] = features

    return data


def get_model_features(session: Session, patient_id: int, pcb_type: str, gender: str) -> Dict[str, Any]:
    mf = _latest_features(session, patient_id)
    lt = _latest_released_lab(session, patient_id)

    feats: Dict[str, Any] = (mf.input_features or {}) if mf else {}

    feats["Gender"] = gender
    feats["maternal_PCB"] = next(
        (p["level"] for p in lt.pcb_results if p["name"] == f"PCB_{pcb_type}"), None)

    return feats


def get_physicians(session: Session) -> Dict[str, Any]:
    physicians = session.exec(
        select(Account)
        .where(Account.role == 'physician').
        order_by(Account.id)).all()

    return [{"id": p.id, "name": f"{p.first_name} {p.last_name}"} for p in physicians]


def build_labtest_view_data(db: Session, labtest_id: int, mode: str = "result"):
    labtest = db.query(LabTest).filter(LabTest.id == labtest_id).first()
    if not labtest:
        return None

    patient = db.query(Patient).filter(
        Patient.id == labtest.patient_id
    ).first()
    physician = db.query(Account).filter(
        Account.id == labtest.physician_id
    ).first()

    # ---- FIXED PCB RESULTS HANDLING ----
    raw_pcb = labtest.pcb_results

    if isinstance(raw_pcb, str):
        try:
            pcb_results = json.loads(raw_pcb or "[]")
        except Exception:
            pcb_results = []
    elif isinstance(raw_pcb, list):
        pcb_results = raw_pcb
    else:
        pcb_results = []

    # total PCB
    total_pcb = round(
        sum(float(item.get("level", 0) or 0) for item in pcb_results),
        2
    ) if pcb_results else None

    data = {
        "mode": mode,                  # "result" or "request"
        "id": labtest.id,
        "test_type": labtest.test_type,
        "collection_date": labtest.collection_date,
        "result_date": labtest.result_date,
        "status": labtest.status,
        "severity": labtest.severity,
        "is_released": labtest.is_released,
        "risk": labtest.risk,
        "technician": labtest.technician,
        "notes": labtest.notes,

        # patient
        "patient_id": patient.id if patient else None,
        "patient_name": patient.name if patient else "Unknown",
        "patient_age": getattr(patient, "age", None),
        "gestational_age": getattr(patient, "gestational_age", None),
        "physician_contact": getattr(physician, "phone", None),

        # physician
        "physician_name": (
            f"{physician.first_name} {physician.last_name}"
            if physician else None
        ),

        # PCB data
        "pcb_results": pcb_results,
        "total_pcb": total_pcb,

        # simple summary
        "summary": labtest.notes,
        "recommendations": None,
    }

    return data


def get_labtest_result_view_data(db: Session, labtest_id: int):
    return build_labtest_view_data(db, labtest_id, mode="result")


def get_labtest_request_view_data(db: Session, labtest_id: int):
    return build_labtest_view_data(db, labtest_id, mode="request")
