# --------------- Dashboard functions --------------------# analytics_service.py
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, date
from sqlmodel import Session, select
from models import LabTest, ModelFeatures, Study, Patient
import math
from collections import defaultdict

# -------------------------------
# Helpers
# -------------------------------

PCB_KEYS = ["PCB_118", "PCB_138", "PCB_153", "PCB_180", "PCB_74",
            "PCB_99", "PCB_156", "PCB_170", "PCB_183", "PCB_187"]


def get_range_bounds(range_str: str) -> Tuple[datetime, datetime]:
    now = datetime.utcnow()
    if range_str == "week":
        return now - timedelta(days=7), now
    if range_str == "month":
        return now - timedelta(days=30), now
    if range_str == "threemonths":
        return now - timedelta(days=90), now
    # all-time (practically very early start)
    return datetime(2000, 1, 1), now


def _test_date(t: LabTest) -> datetime:
    d = t.result_date or t.collection_date
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime.combine(d, datetime.min.time())
    return datetime(2000, 1, 1)


def _risk_label(val: float) -> str:
    # simple bins—adjust thresholds later
    if val < 1.0:
        return "low"
    if val < 2.0:
        return "medium"
    return "high"


def _bmi_bucket(bmi: Optional[float]) -> str:
    if bmi is None:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def _corr(xs: List[float], ys: List[float]) -> float:
    # tiny Pearson helper without numpy
    n = len(xs)
    if n == 0 or n != len(ys):
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x)*(y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x)**2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y)**2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def _latest_by_patient(features: List[ModelFeatures]) -> Dict[int, ModelFeatures]:
    # keep last ModelFeatures per patient_id
    by_patient: Dict[int, ModelFeatures] = {}
    for mf in features:
        if mf.patient_id not in by_patient or by_patient[mf.patient_id].date < mf.date:
            by_patient[mf.patient_id] = mf
    return by_patient


# ---------- helpers (add near your helpers) ----------
PCB_KEYS = ["PCB_118", "PCB_138", "PCB_153", "PCB_180", "PCB_74",
            "PCB_99", "PCB_156", "PCB_170", "PCB_183", "PCB_187"]


def _latest_by_patient(features: List[ModelFeatures]) -> Dict[int, ModelFeatures]:
    by = {}
    for mf in features:
        if mf.patient_id not in by or by[mf.patient_id].date < mf.date:
            by[mf.patient_id] = mf
    return by


def _bmi3(bmi: Optional[float]) -> Optional[str]:
    if bmi is None:
        return None
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    return "Overweight"


def _risk_from_value(v: float) -> str:
    # simple, explicit thresholds for PCB predictions
    if v < 2.0:
        return "low"
    if v < 4.0:
        return "medium"
    return "high"


# -------------------------------
# Summary metrics
# -------------------------------

def fetch_summary(session: Session, start: datetime, end: datetime) -> Dict:
    # patients assessed = with any ModelFeatures in range (latest per patient)
    mfs = session.exec(
        select(ModelFeatures).where(ModelFeatures.date >=
                                    start, ModelFeatures.date <= end)
    ).all()
    latest = _latest_by_patient(mfs)
    pids = list(latest.keys())

    # high risk from Patient.risk
    patients = {}
    if pids:
        rows = session.exec(select(Patient).where(Patient.id.in_(pids))).all()
        patients = {p.id: p for p in rows}
    high_risk = sum(1 for pid in pids if patients.get(
        pid) and str(patients[pid].risk).lower() == "high")

    # fetal per-PCB avgs & overall avg fetal concentration
    pcb_sum = {k: 0.0 for k in PCB_KEYS}
    pcb_cnt = {k: 0 for k in PCB_KEYS}
    fetal_totals = []

    for mf in latest.values():
        preds = mf.output_predictions or {}
        total = 0.0
        for k in PCB_KEYS:
            v = preds.get(k)
            if v is not None:
                fv = float(v)
                pcb_sum[k] += fv
                pcb_cnt[k] += 1
                total += fv
        fetal_totals.append(total)

    avgs = {k: (pcb_sum[k]/pcb_cnt[k] if pcb_cnt[k] else 0.0)
            for k in PCB_KEYS}
    top_pcb = max(avgs.items(), key=lambda x: x[1])[0] if avgs else "-"
    top_pcb_avg = avgs.get(top_pcb, 0.0)
    avg_fetal = (sum(fetal_totals)/len(fetal_totals)) if fetal_totals else 0.0

    # maternal–fetal correlation using maternal_PCB from input_features vs fetal totals
    xs, ys = [], []
    for mf in latest.values():
        feats = mf.input_features or {}
        mpcb = feats.get("maternal_PCB")
        if mpcb is None:
            continue
        ft = sum(float((mf.output_predictions or {}).get(k, 0.0))
                 for k in PCB_KEYS)
        xs.append(float(mpcb))
        ys.append(ft)
    corr = 0.0
    if xs and ys:
        mx = sum(xs)/len(xs)
        my = sum(ys)/len(ys)
        num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
        denx = (sum((x-mx)**2 for x in xs))**0.5
        deny = (sum((y-my)**2 for y in ys))**0.5
        corr = round((num/(denx*deny)) if denx and deny else 0.0, 3)

    return {
        "total_patients": len(latest),
        "high_risk": high_risk,
        "top_pcb": top_pcb,
        "top_pcb_avg": round(top_pcb_avg, 3),
        "avg_fetal_pcb": round(avg_fetal, 3),
        "correlation": corr,
    }


# -------------------------------
# 1) Exposure and Risk Patterns
# -------------------------------

def fetch_avg_pcb_levels(session: Session, start: datetime, end: datetime) -> Dict:
    # maternal from LabTest (released/ready) in range
    ms, mc = {k: 0.0 for k in PCB_KEYS}, {k: 0 for k in PCB_KEYS}
    tests = session.exec(select(LabTest).where(
        LabTest.status.in_(["ready", "released"]))).all()
    for t in tests:
        dt = t.result_date or t.collection_date
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        if not (start <= (dt or start) <= end):
            continue
        for row in (t.pcb_results or []):
            name = str(row.get("name", "")).upper()
            if name in ms and row.get("level") is not None:
                ms[name] += float(row["level"])
                mc[name] += 1
    maternal = [(ms[k]/mc[k] if mc[k] else 0.0) for k in PCB_KEYS]

    # fetal from ModelFeatures in range
    fs, fc = {k: 0.0 for k in PCB_KEYS}, {k: 0 for k in PCB_KEYS}
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        preds = mf.output_predictions or {}
        for k in PCB_KEYS:
            v = preds.get(k)
            if v is not None:
                fs[k] += float(v)
                fc[k] += 1
    fetal = [(fs[k]/fc[k] if fc[k] else 0.0) for k in PCB_KEYS]

    return {"labels": PCB_KEYS, "maternal": maternal, "fetal": fetal}


def fetch_risk_distribution_by_pcb(session: Session, start: datetime, end: datetime) -> Dict:
    # fixed thresholds on predicted PCB values
    lows = [0]*len(PCB_KEYS)
    meds = [0]*len(PCB_KEYS)
    highs = [0]*len(PCB_KEYS)
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        preds = mf.output_predictions or {}
        for i, k in enumerate(PCB_KEYS):
            v = float(preds.get(k, 0.0))
            r = _risk_from_value(v)
            if r == "low":
                lows[i] += 1
            elif r == "medium":
                meds[i] += 1
            else:
                highs[i] += 1
    return {"labels": PCB_KEYS, "risk_low": lows, "risk_med": meds, "risk_high": highs}


def fetch_concentration_series(session: Session, start: datetime, end: datetime) -> Dict:
    """
    Return a line-friendly dataset comparing maternal vs fetal PCB averages per patient.
    """
    # 1) maternal average per patient
    mat_avgs = {}
    tests = session.exec(
        select(LabTest).where(LabTest.status.in_(["ready", "released"]))
    ).all()
    for t in tests:
        ts = _test_date(t)
        if not (start <= ts <= end) or not t.patient_id:
            continue
        levels = [float(r.get("level") or 0.0) for r in (
            t.pcb_results or []) if r.get("level") is not None]
        if levels:
            mat_avgs[t.patient_id] = sum(levels) / len(levels)

    # 2) fetal average per patient
    mfs = session.exec(
        select(ModelFeatures).where(ModelFeatures.date >=
                                    start, ModelFeatures.date <= end)
    ).all()
    latest = _latest_by_patient(mfs)
    fet_avgs = {}
    for pid, mf in latest.items():
        preds = mf.output_predictions or {}
        vals = [float(preds.get(k, 0) or 0.0) for k in PCB_KEYS]
        nonzero = [v for v in vals if v > 0]
        if nonzero:
            fet_avgs[pid] = sum(nonzero) / len(nonzero)

    # 3) align patients having both
    common_ids = sorted(set(mat_avgs) & set(fet_avgs))
    labels = [f"P{i+1}" for i in range(len(common_ids))]
    maternal_series = [mat_avgs[pid] for pid in common_ids]
    fetal_series = [fet_avgs[pid] for pid in common_ids]

    return {"labels": labels, "maternal_series": maternal_series, "fetal_series": fetal_series}


# -------------------------------
# 2) Demographic Correlations
# -------------------------------


def fetch_age_groups_avg(session: Session, start: datetime, end: datetime) -> Dict:
    # use Patient.age paired with latest ModelFeatures total
    mfs = _latest_by_patient(session.exec(
        select(ModelFeatures).where(ModelFeatures.date >=
                                    start, ModelFeatures.date <= end)
    ).all())
    if not mfs:
        return {"labels": ["<25", "25-30", "31-35", "36-40", "41+"], "values": [0, 0, 0, 0, 0]}

    rows = session.exec(select(Patient).where(
        Patient.id.in_(list(mfs.keys())))).all()
    patients = {p.id: p for p in rows}

    buckets = {"<25": [], "25-30": [], "31-35": [], "36-40": [], "41+": []}
    for pid, mf in mfs.items():
        p = patients.get(pid)
        if not p or p.age is None:
            continue
        total = sum(float((mf.output_predictions or {}).get(k, 0.0))
                    for k in PCB_KEYS)
        a = p.age
        if a < 25:
            buckets["<25"].append(total)
        elif a <= 30:
            buckets["25-30"].append(total)
        elif a <= 35:
            buckets["31-35"].append(total)
        elif a <= 40:
            buckets["36-40"].append(total)
        else:
            buckets["41+"].append(total)

    labels = list(buckets.keys())
    vals = [(sum(v)/len(v) if v else 0.0) for v in buckets.values()]
    return {"labels": labels, "values": vals}


def fetch_scatter_total_vs_age(session: Session, start: datetime, end: datetime) -> List[Dict]:
    mfs = _latest_by_patient(session.exec(
        select(ModelFeatures).where(ModelFeatures.date >=
                                    start, ModelFeatures.date <= end)
    ).all())
    if not mfs:
        return []
    rows = session.exec(select(Patient).where(
        Patient.id.in_(list(mfs.keys())))).all()
    patients = {p.id: p for p in rows}

    pts = []
    for pid, mf in mfs.items():
        p = patients.get(pid)
        if not p or p.age is None:
            continue
        total = sum(float((mf.output_predictions or {}).get(k, 0.0))
                    for k in PCB_KEYS)
        pts.append({"x": float(p.age), "y": round(total, 3)})
    return pts


def fetch_pcb_by_bmi(session: Session, start: datetime, end: datetime) -> Dict:
    buckets: Dict[str, List[float]] = defaultdict(list)
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        feats = mf.input_features or {}
        label = _bmi3(float(feats.get("BMI")) if feats.get(
            "BMI") is not None else None)
        if not label:
            continue
        total = sum(float((mf.output_predictions or {}).get(k, 0.0))
                    for k in PCB_KEYS)
        buckets[label].append(total)
    labels = ["Underweight", "Normal", "Overweight"]
    vals = [(sum(buckets[l])/len(buckets[l]) if buckets[l] else 0.0)
            for l in labels]
    return {"labels": labels, "values": vals}


def fetch_smoking_comparison(session: Session, start: datetime, end: datetime) -> Dict:
    smokers, nons = [], []
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        feats = mf.input_features or {}
        total = sum(float((mf.output_predictions or {}).get(k, 0.0))
                    for k in PCB_KEYS)
        if int(feats.get("Smoking", 0)) == 1:
            smokers.append(total)
        else:
            nons.append(total)
    avg_s = (sum(smokers)/len(smokers)) if smokers else 0.0
    avg_n = (sum(nons)/len(nons)) if nons else 0.0
    return {"labels": ["Non-smokers", "Smokers"], "values": [avg_n, avg_s]}


def fetch_correlation_heatmap(session: Session, start: datetime, end: datetime) -> Dict:
    # Diet, Smoking, BMI, Age, maternal_PCB (from input_features)
    vars_ = ["Diet", "Smoking", "BMI", "Age", "mPCB"]
    series = {k: [] for k in vars_}
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        feats = mf.input_features or {}
        series["Diet"].append(float(feats.get(
            "Daily dairy doses", feats.get("Sum of dairy products", 0.0)) or 0.0))
        series["Smoking"].append(float(feats.get("Smoking", 0) or 0.0))
        series["BMI"].append(float(feats.get("BMI", 0.0) or 0.0))
        series["Age"].append(float(feats.get("Age", 0.0) or 0.0))
        series["mPCB"].append(float(feats.get("maternal_PCB", 0.0) or 0.0))

    def corr(a, b):
        n = len(a)
        if n == 0 or n != len(b):
            return 0.0
        mx = sum(a)/n
        my = sum(b)/n
        num = sum((x-mx)*(y-my) for x, y in zip(a, b))
        denx = (sum((x-mx)**2 for x in a))**0.5
        deny = (sum((y-my)**2 for y in b))**0.5
        return (num/(denx*deny)) if denx and deny else 0.0

    mat = []
    for r in vars_:
        row = []
        for c in vars_:
            row.append(round(corr(series[r], series[c]), 3))
        mat.append(row)
    return {"labels": vars_, "matrix": mat}


# -------------------------------
# 3) Environment & Lifestyle
# -------------------------------


def fetch_exposure_contribution(session: Session, start: datetime, end: datetime) -> Dict:
    # absolute correlations vs total fetal PCB
    cats = ["Chemical exposure", "Coffee", "Tea",
            "BMI", "Smoking", "Maternal Education"]
    X = {k: [] for k in cats}
    totals = []
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        feats = mf.input_features or {}
        totals.append(sum(float((mf.output_predictions or {}).get(k, 0.0))
                      for k in PCB_KEYS))
        X["Chemical exposure"].append(
            float(feats.get("Chemical exposure", 0.0) or 0.0))
        X["Coffee"].append(float(feats.get("Cups of coffee", 0.0) or 0.0))
        X["Tea"].append(float(feats.get("Cups of tea", 0.0) or 0.0))
        X["BMI"].append(float(feats.get("BMI", 0.0) or 0.0))
        X["Smoking"].append(float(feats.get("Smoking", 0) or 0.0))
        X["Maternal Education"].append(
            float(feats.get("Maternal Education", 0) or 0.0))

    def corr(a, b):
        n = len(a)
        if n == 0 or n != len(b):
            return 0.0
        mx = sum(a)/n
        my = sum(b)/n
        num = sum((x-mx)*(y-my) for x, y in zip(a, b))
        denx = (sum((x-mx)**2 for x in a))**0.5
        deny = (sum((y-my)**2 for y in b))**0.5
        return (num/(denx*deny)) if denx and deny else 0.0

    vals = [round(abs(corr(X[k], totals)), 3) for k in cats]
    return {"labels": cats, "values": vals}


def fetch_dietary_patterns(session: Session, start: datetime, end: datetime) -> Dict:
    bins = {"Low dairy": [], "Medium dairy": [], "High dairy": []}
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        feats = mf.input_features or {}
        dairy = float(feats.get("Daily dairy doses", feats.get(
            "Sum of dairy products", 0.0)) or 0.0)
        total = sum(float((mf.output_predictions or {}).get(k, 0.0))
                    for k in PCB_KEYS)
        if dairy < 1.0:
            bins["Low dairy"].append(total)
        elif dairy < 2.0:
            bins["Medium dairy"].append(total)
        else:
            bins["High dairy"].append(total)
    labels = list(bins.keys())
    vals = [(sum(v)/len(v) if v else 0.0) for v in bins.values()]
    return {"labels": labels, "values": [round(v, 3) for v in vals]}


def fetch_lifestyle_clusters(session: Session, start: datetime, end: datetime) -> List[Dict]:
    pts = []
    for mf in session.exec(select(ModelFeatures).where(ModelFeatures.date >= start, ModelFeatures.date <= end)).all():
        feats = mf.input_features or {}
        age = feats.get("Age")
        if age is None:
            continue
        total = sum(float((mf.output_predictions or {}).get(k, 0.0))
                    for k in PCB_KEYS)
        pts.append({"x": float(age), "y": round(total, 3)})
    return pts


# -------------------------------
# 4) Related research
# -------------------------------


def fetch_related_research(session: Session, limit: int = 6) -> List[Dict]:
    rows = session.exec(select(Study).order_by(
        Study.year.desc()).limit(limit)).all()
    return [
        {"title": s.title, "link": s.link, "year": s.year, "authors": s.authors}
        for s in rows
    ]
