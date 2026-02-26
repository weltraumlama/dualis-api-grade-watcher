from datetime import datetime
from pydantic import BaseModel
from typing import List


class Exam(BaseModel):
    name: str
    date: str
    grade: str
    externally_accepted: bool = False


class Unit(BaseModel):
    unit_nr: str
    title: str
    semester: str
    exams: List[Exam]


class Semester(BaseModel):
    id: str
    name: str


class GradeNotification(BaseModel):
    """Payload sent via webhook when a new grade is detected."""
    unit_nr: str
    title: str
    semester: str
    exam: Exam
    detected_at: datetime
