from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
from sqlalchemy import Column, JSON

# ------------------------------------------------------------
# Base Account and Research entities
# ------------------------------------------------------------


class RoleEnum(str, Enum):
    administrator = "administrator"
    physician = "physician"
    lab_admin = "lab administrator"
    data_receptionist = "data receptionist"
    researcher = "researcher"


class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    username: str
    password: str
    role: RoleEnum = Field(default=RoleEnum.physician)
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = Field(default=True)

    # Relationships
    appointments: List["Appointment"] = Relationship(
        back_populates="physician")
    patients: List["Patient"] = Relationship(back_populates="physician")
    lab_tests_conducted: List["LabTest"] = Relationship(
        back_populates="physician")
    reports: List["Report"] = Relationship(back_populates="user")
    studies_added: List["Study"] = Relationship(back_populates="researcher")


# ------------------------------------------------------------
# Core Patient & Appointment entities
# ------------------------------------------------------------

class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    bdate: date
    age: Optional[int] = None
    gestational_age: Optional[int] = None
    due_date: Optional[date] = None
    risk: Optional[str] = None  # e.g. 'low', 'medium', 'high'
    data_consent: bool = Field(default=False)
    is_complete: bool = Field(default=False)
    notes: Optional[str] = None
    docs: Optional[str] = None  # Could be file path or JSON metadata

    # Foreign Keys
    physician_id: Optional[int] = Field(default=None, foreign_key="account.id")

    # Relationships
    physician: Optional[Account] = Relationship(back_populates="patients")
    appointments: List["Appointment"] = Relationship(back_populates="patient")
    lab_tests: List["LabTest"] = Relationship(back_populates="patient")
    model_features: List["ModelFeatures"] = Relationship(
        back_populates="patient")


class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    purpose: str
    datetime: datetime
    status: str  # e.g. 'scheduled', 'completed', 'cancelled'

    # Foreign Keys
    patient_id: int = Field(foreign_key="patient.id")
    physician_id: int = Field(foreign_key="account.id")

    # Relationships
    patient: "Patient" = Relationship(back_populates="appointments")
    physician: "Account" = Relationship(back_populates="appointments")


# ------------------------------------------------------------
# Laboratory & Results
# ------------------------------------------------------------

class LabTest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)  # now int
    test_type: str = "Maternal Cord Blood"
    collection_date: date
    result_date: Optional[date] = None
    technician: Optional[str] = None
    notes: Optional[str] = None

    # 'pending', 'ready', 'released'
    status: Optional[str] = Field(default="pending")
    severity: Optional[str] = None
    is_released: bool = Field(default=False)
    risk: Optional[str] = None

    # Results as JSON (list of {"name": "PCB_74", "level": 1.23})
    pcb_results: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Foreign keys (now ints, consistent with Patient/Account)
    patient_id: int = Field(foreign_key="patient.id")
    physician_id: Optional[int] = Field(default=None, foreign_key="account.id")

    # Relationships
    patient: "Patient" = Relationship(back_populates="lab_tests")
    physician: Optional["Account"] = Relationship(
        back_populates="lab_tests_conducted")


# ------------------------------------------------------------
# Model Features (includes model inputs + outputs)
# ------------------------------------------------------------

class ModelFeatures(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    date: datetime = Field(default_factory=datetime.utcnow)

    # JSON blobs
    input_features: dict = Field(sa_column=Column(JSON))
    output_predictions: Optional[dict] = Field(
        default=None, sa_column=Column(JSON))

    # Relationships
    patient: "Patient" = Relationship(back_populates="model_features")


# ------------------------------------------------------------
# Reports & Studies (research-related)
# ------------------------------------------------------------

class Report(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str
    subject: str
    description: Optional[str] = None
    attachment: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    date: datetime = Field(default_factory=datetime.utcnow)
    response: Optional[str] = None
    resolved_at: Optional[datetime] = None

    # Who created it
    user_id: Optional[int] = Field(default=None, foreign_key="account.id")

    # Relationships
    user: Optional["Account"] = Relationship(back_populates="reports")


class Study(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    link: Optional[str] = None
    summary: Optional[str] = None

    # Foreign Keys
    researcher_id: Optional[int] = Field(
        default=None, foreign_key="account.id")

    # Relationships
    researcher: Optional[Account] = Relationship(
        back_populates="studies_added")
