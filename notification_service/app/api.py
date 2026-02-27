import logging

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.models import GradeNotification
from app.telegram import send_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("notification-service")

app = FastAPI(
    title="Dualis Grade notification Service",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/new-grade")
async def receive_grade(notification: GradeNotification):
    """
    Webhook endpoint called by the refresh service
    when a new grade is detected.
    """
    logger.info(
        "Received new grade: %s / %s -> %s",
        notification.unit_nr,
        notification.exam.name,
        notification.exam.grade,
    )

    success = await send_notification(
        unit_nr=notification.unit_nr,
        title=notification.title,
        semester=notification.semester,
        exam_name=notification.exam.name,
        grade=notification.exam.grade,
        date=notification.exam.date,
        externally_accepted=notification.exam.externally_accepted,
    )

    if success:
        return {"status": "sent"}
    else:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"status": "telegram_error"},
        )
