# # main.py (FastAPI application)
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI, Request, Depends, Query, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import pickle
from pydantic import BaseModel  # TO BE REMOVED

from contextlib import asynccontextmanager

from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session, select
from database import init_db
from models import Account
from deps import get_session

# User defined functions
import home_methods as home
import lists_methods as lis
import fetch_db_methods as dbf
import insert_db_methods as dbi
import dashboard_methods as dash

logging.basicConfig(
    level=logging.DEBUG,
    format="DEBUGGGG: %(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # OPTIONALLY YOU CAN LOAD THE MODELS HERE ON STARTUP

    # Initialize Database
    init_db()

    # Clean up and release the resources
    yield

# Initialize FASTAPI app, configure the static files directory, and create a templates object
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configure CORS to allow our HTML page to fetch data from the app
origins = [
    # Or whatever port your HTML is served from (e.g., Live Server in VS Code)
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    # Allows requests from files opened directly in the browser (file://)
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_ME"
)

# TO BE REMOVED


# class Features(BaseModel):
#     Gender: int
#     Age: int
#     Chemical_exposure: int
#     Q30_vaccines_received: int
#     Daily_dairy_doses: float
#     Cheese_slices: int
#     Sum_of_dairy_products: float
#     Cups_of_coffee: float
#     Cups_of_tea: float
#     Cups_of_green_tea: float
#     Rye_bread: int
#     Mixed_bread: int
#     Boiled_potatoes: int
#     Fried_potatoes: int
#     Beef_or_pork: int
#     Reindeer_game_meat: int
#     Light_meat: int
#     Sausage_dishes: int
#     Eggs: int
#     Fish_dishes: int
#     Trout_Salmon: int
#     Domestic_sea_salmon: int
#     Lake_fish: int
#     Frozen_fish: int
#     Shrimp: int
#     Apple: int
#     Apple_juice: int
#     Grilled_food: int
#     Smoked_food: int
#     Breaded_food: int
#     BMI: float
#     Maternal_Education: int
#     Smoking: int
#     Alcohol: int
#     mPCB: float

# Additional Precuationary route to handle "favicon template not found" exception


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("static/logo.png")

# Function to handle GET requests to /predict_cPCB


@app.post("/predict_cPCB", response_class=HTMLResponse)
async def predict_cPCB(request: Request, session: Session = Depends(get_session)):
    features: Dict[str, Any] = await request.json()

    gender = int(features["gender"])
    pcb_type = str(features["pcb_type"])
    patient_id = int(features["patient_id"])

    features = dbf.get_model_features(
        session=session, patient_id=patient_id, pcb_type=pcb_type, gender=gender)

    # load model from file
    model = pickle.load(open(f'models/PCB_{pcb_type}_final_model.pkl', 'rb'))

    # Convert features dictionary to a dataframe
    features_df = pd.DataFrame([features])

    # make a prediction
    cPCB_pred = model.predict(features_df)

    # return prediction alongside user data
    # user_data = request.session.get("user")

    # data = user_data.copy()

    data = {"prediction": {"value": round(float(
        cPCB_pred[0]), 3), "date": datetime.utcnow().strftime("%B %d, %Y at %H:%M")}}

    # role = data["role"]

    # return templates.TemplateResponse(f"{role}/assessment.html", {"request": request, "data": data})

    return JSONResponse(data, status_code=200)


@app.get("/", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login_verify(request: Request, username: str = Form(...), password: str = Form(...), role: str = Form(...), session_db: Session = Depends(get_session)):

    # query database to verify credentials
    user = session_db.exec(select(Account).where(Account.username == username).where(
        Account.password == password).where(Account.role == role)).first()

    if not user:
        # invalid credentials -> return with an error
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password."}, status_code=401,)
    elif not user.is_active:
        # valid credentials but account deactivated
        return templates.TemplateResponse("login.html", {"request": request, "error": "Account deactivated."}, status_code=401,)
    else:
        if user.role == "administrator":
            directory = "admin"
        elif user.role == "physician":
            directory = "physician"
        elif user.role == "lab administrator":
            directory = "lab_admin"
        elif user.role == "data receptionist":
            directory = "data_clerk"
        else:
            directory = "researcher"

        # valid credentials
        request.session["user"] = {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "job": user.role.title(),
            "role": directory,
        }

        return RedirectResponse(url="/home", status_code=303)


# def get_role(request: Request):
#     user_data = request.session.get("user")

#     return user_data.get("role")


@app.get("/home", response_class=HTMLResponse)
def login_get(request: Request, session: Session = Depends(get_session)):
    # logger.debug("We're about to see the home page!")

    user_data = request.session.get("user")

    role = user_data.get("role")

    data = user_data.copy()

    if role == "researcher":
        return templates.TemplateResponse(f"{role}/home.html", {"request": request, "data": data})

    current_time = datetime.now().strftime("%A, %B %d, %Y")
    activities = home.fetch_recent_activities(
        session=session,
        role=user_data["job"],        # string or RoleEnum ok
        user_id=user_data["id"],       # used for physician/lab_admin filtering
        limit=5)

    data |= {"current_time": current_time, "activities": activities}

    if role != "admin":
        notif = home.get_notifications(
            session, role=user_data["job"], user_id=user_data["id"], limit=4)

        data |= {"notifications": notif}

    return templates.TemplateResponse(f"{role}/home.html", {"request": request, "data": data})


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.post("/support", response_class=HTMLResponse)
def send_support_request(request: Request, subject: str = Form(...), type: str = Form(...), priority: str = Form(...), description: str = Form(...), status: str = Form(...), session_db: Session = Depends(get_session)):

    # logger.debug("Support Request will be recorded shortly..")

    template_context = {"request": request}

    if request.session.get("user"):
        user_id = request.session.get("user").get("id")
        template_context |= {"data": request.session.get("user")}
    else:
        user_id = None

    dbi.insert_new_report(subject=subject, type=type, priority=priority,
                          description=description, status=status, user_id=user_id, session=session_db)

    return templates.TemplateResponse("/layouts/support_sent.html", template_context)


@app.get("/dashboard_analytics", response_class=HTMLResponse)
def get_page(request: Request):

    return templates.TemplateResponse("researcher/analytics_dashboard.html", {"request": request})


@app.get("/dashboard_data")
def get_dashboard_data(range: str = Query("all"), session: Session = Depends(get_session)):
    start, end = dash.get_range_bounds(range)

    return {
        "summary": dash.fetch_summary(session, start, end),

        "avg_pcb_levels": dash.fetch_avg_pcb_levels(session, start, end),
        "risk_distribution": dash.fetch_risk_distribution_by_pcb(session, start, end),
        "concentration_series": dash.fetch_concentration_series(session, start, end),

        "demographics": {
            "pcb_by_age": dash.fetch_age_groups_avg(session, start, end),
            "scatter_total_vs_age": dash.fetch_scatter_total_vs_age(session, start, end),
            "pcb_by_bmi": dash.fetch_pcb_by_bmi(session, start, end),
            "smoking_comparison": dash.fetch_smoking_comparison(session, start, end),
            "correlation_heatmap": dash.fetch_correlation_heatmap(session, start, end),
        },

        "environment": {
            "exposure_contribution": dash.fetch_exposure_contribution(session, start, end),
            "dietary_patterns": dash.fetch_dietary_patterns(session, start, end),
            "lifestyle_clusters": dash.fetch_lifestyle_clusters(session, start, end),
        },

        "research": dash.fetch_related_research(session, limit=8),
    }


@app.get("/patients/patient_profile/{patient_id}")
def physician_patient_profile(request: Request, patient_id: int, session: Session = Depends(get_session)):

    user_data = request.session.get("user")
    data = user_data.copy()

    role = data.get("role")

    if role == "physician":
        data |= dbf.get_physician_patient_profile(session, patient_id)
        return templates.TemplateResponse(f"{role}/patient_profile.html", {"request": request, "data": data})


@app.post("/patients/{patient_id}/notes")
async def update_patient_notes(patient_id: int, request: Request, session: Session = Depends(get_session)):
    payload = await request.json()
    notes = payload.get("notes", "") if isinstance(payload, dict) else ""

    status = dbi.update_patient_notes(notes, patient_id, session)

    if status != 200:
        return JSONResponse({"success": False, "error": "patient not found"}, status_code=404)
    else:
        return JSONResponse({"success": True})


@app.post("/patients/{patient_id}/lab_request")
async def request_lab_test(patient_id: int, request: Request, session: Session = Depends(get_session)):

    payload = await request.json()
    test_type = payload.get("test_type", "Maternal Cord Blood")
    severity = payload.get("severity", "medium")

    # get physician id from session
    user = request.session.get("user") or {}
    physician_id = user.get("id")

    status = dbi.insert_new_labtest_request(
        patient_id, physician_id, test_type, severity, session)

    if status != 200:
        return JSONResponse({"success": False, "error": "patient not found"}, status_code=404)
    else:
        return JSONResponse({"success": True})


@app.get("/patients/patient_profile/{patient_id}/assessment")
def physician_patient_assesment(request: Request, patient_id: int, session: Session = Depends(get_session)):
    user_data = request.session.get("user")
    data = user_data.copy()

    role = data.get("role")

    if role == "physician":
        data |= dbf.get_assessment_view_data(
            session=session, patient_id=patient_id)
        return templates.TemplateResponse(f"{role}/assessment.html", {"request": request, "data": data})

    # Dynamic route to serve different pages based on the URL


@app.get("/patients/new", response_class=HTMLResponse)
def data_clerk_new_patient(request: Request, session: Session = Depends(get_session)):

    user_data = request.session.get("user")
    data = user_data.copy()

    role = data.get("role")

    if role == "data_clerk":
        data["physicians"] = dbf.get_physicians(session=session)

        return templates.TemplateResponse(f"{role}/patient_form.html", {"request": request, "data": data})


@app.get("/lab-tests/{test_id}/result")
async def lab_test_result_view(test_id: int, request: Request, db: Session = Depends(get_session)):

    user_data = request.session.get("user")
    data = user_data.copy()

    role = data.get("role")

    if role == "lab_admin":
        data |= dbf.get_labtest_result_view_data(db, test_id)
        if not data:
            raise HTTPException(status_code=404, detail="Test not found")
        return templates.TemplateResponse(f"{role}/lab_test_view.html", {"request": request, "data": data},)


@app.get("/lab-tests/{test_id}/request")
async def lab_test_request_view(test_id: int, request: Request, db: Session = Depends(get_session)):

    user_data = request.session.get("user")
    data = user_data.copy()

    role = data.get("role")

    if role == "lab_admin":
        data |= dbf.get_labtest_request_view_data(db, test_id)
        if not data:
            raise HTTPException(status_code=404, detail="Test not found")
        return templates.TemplateResponse(f"{role}/lab_test_view.html", {"request": request, "data": data},)


@app.post("/lab-tests/{test_id}/dispatch")
async def dispatch_lab_test_endpoint(test_id: int, request: Request, db: Session = Depends(get_session)):
    user_data = request.session.get("user") or {}
    role = user_data.get("role")

    if role != "lab_admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    processed = dbi.dispatch_lab_test(db, test_id)

    if not processed:
        raise HTTPException(status_code=404, detail="Test not found")

    # Always go to the result page after processing
    return RedirectResponse(
        url=f"/lab-tests/{test_id}/result",
        status_code=303,
    )


@app.post("/lab-tests/{test_id}/release")
async def release_lab_test_endpoint(
    test_id: int,
    request: Request,
    db: Session = Depends(get_session),
):
    user_data = request.session.get("user") or {}
    role = user_data.get("role")

    if role != "lab_admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    ok = dbi.release_lab_test(db, test_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Test not found")

    # Redirect back to the result page with a flag (?sent=1)
    return RedirectResponse(
        url=f"/lab-tests/{test_id}/result?sent=1",
        status_code=303,
    )


@app.get("/{page_name}", response_class=HTMLResponse)
def get_page(request: Request, page_name: str, session: Session = Depends(get_session)):
    user_data = request.session.get("user")

    if user_data:
        data = user_data.copy()
    else:
        data = None

    # logger.debug("Entered the general pages route function..")

    if page_name == "support.html":
        # logger.debug("User requested support page!")
        if not data:  # not logged in
            # logger.debug("User is not logged in yet though")
            # logger.debug(f"current data: {data}")
            return templates.TemplateResponse("/layouts/support.html", {"request": request})
        else:
            # logger.debug("User already logged! yay!")
            # logger.debug(f"current data: {data}")
            return templates.TemplateResponse("/layouts/support.html", {"request": request, "data": data})

    # -----------------------------------------------------
    if page_name == "home.html":
        # logger.debug("User requested home page! redirecting to its route!")
        return RedirectResponse(url="/home", status_code=303)

    # ------------------------------------------------
    role = data.get("role")

    if role == "physician":
        if page_name == "patients.html":
            # logger.debug("We're going to fetch the physician patient page!")
            data |= lis.get_physician_patients_page(
                session=session, physician_id=request.session.get("user").get("id"))

        elif page_name == "schedule.html":
            data |= lis.get_physician_schedule_page(
                session=session, physician_id=request.session.get("user").get("id"))

    elif role == "data_clerk":
        if page_name == "patients.html":
            data |= lis.get_data_clerk_patients_page(session=session)

        elif page_name == "appointments.html":
            data |= lis.get_data_clerk_appointments_page(session=session)

    elif role == "admin":
        if page_name == "accounts.html":
            data |= lis.get_admin_accounts_page(session=session)
        elif page_name == "reports.html":
            data |= lis.get_admin_reports_page(session=session)

    elif role == "lab_admin":
        if page_name == "results.html":
            data |= lis.get_lab_results_page(session=session)

        elif page_name == "requests.html":
            data |= lis.get_lab_test_queue_page(session=session)

    return templates.TemplateResponse(f"{role}/{page_name}", {"request": request, "data": data})


@app.post("/patient/save")
async def register_new_patient(request: Request, session: Session = Depends(get_session)):

    logger.debug("We're in /patient/save!")

    form = await request.form()
    data = dict(form)

    features = {"Gender": None,
                "Age": int(data["age"]),
                "Chemical exposure": int(data["chemical_exposure"]),
                "Q30 Have you received vaccines according to the vaccination program?": int(data["vaccination_program"]),
                "Daily dairy doses": int(data["daily_dairy_doses"]),
                "Cheese slices": int(data["cheese_slices"]),
                "Sum of dairy products": int(data["sum_dairy_products"]),
                "Cups of coffee": int(data["cups_coffee"]),
                "Cups of tea": int(data["cups_tea"]),
                "Cups of green tea": int(data["cups_green_tea"]),
                "Rye bread": int(data["rye_bread"]),
                "Mixed bread": int(data["mixed_bread"]),
                "Boiled potatoes": int(data["boiled_potatoes"]),
                "Fried potatoes": int(data["fried_potatoes"]),
                "Beef or pork": int(data["beef"]),
                "Reindeer/game meat": int(data["game_meat"]),
                "Light meat": int(data["light_meat"]),
                "Sausage dishes": int(data["sausage_dishes"]),
                "Eggs": int(data["eggs"]),
                "Fish dishes": int(data["fish_dishes_total"]),
                "Trout/Salmon": int(data["trout_salmon"]),
                "Q67 Native salmon": int(data["native_salmon"]),
                "Lake fish": int(data["lake_fish"]),
                "Frozen fish": int(data["frozen_fish"]),
                "Shrimp": int(data["shrimp"]),
                "Apple": int(data["apple"]),
                "Apple juice": int(data["apple_juice"]),
                "Grilled food": int(data["grilled_food"]),
                "Smoked food": int(data["smoked_food"]),
                "Breaded food": int(data["breaded_food"]),
                "Q120.6 The total number of preparations": int(data["total_preparations"]),
                "Q204 Iron -containing preparation during pregnancy": int(data["iron_preparation"]),
                "BMI": float(data["bmi"]),
                "Maternal Education": int(data["maternal_education"]),
                "Smoking": int(data["smoking"]),
                "Alcohol": int(data["alcohol"]),
                "maternal_PCB": None}

    dbi.insert_new_patient(data["name"], data["bdate"], data["age"], data["gestational_age"], data["due_date"], data["physician_id"],
                           data["consent"], data["is_complete"], data["appointment_datetime"], data["appointment_purpose"], features, session)

    logger.debug("New Patient Inserted!!")
    return RedirectResponse(url="/patients.html", status_code=303)

# @app.get("/{role}/{page_name}", response_class=HTMLResponse)
# def get_page(request: Request, role: str, page_name: str):
#     return templates.TemplateResponse(f"{role}/{page_name}", {"request": request})
