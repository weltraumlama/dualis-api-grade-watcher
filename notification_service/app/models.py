from datetime import datetime
from pydantic import BaseModel


class Exam(BaseModel):
    name: str
    date: str
    grade: str
    externally_accepted: bool = False


class GradeNotification(BaseModel):
    """Incoming webhook payload from the refresh service."""
    unit_nr: str
    title: str
    semester: str
    exam: Exam
    detected_at: datetime
