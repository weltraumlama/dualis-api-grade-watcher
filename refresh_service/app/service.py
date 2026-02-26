import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import httpx

from app.config import settings
from app.models import GradeNotification, Semester, Unit

logger = logging.getLogger("refresh-service")


# ---- Webhook -----------------------------------------------------------

async def _send_webhook(notification: GradeNotification) -> None:
    """POST a grade notification to the configured webhook URL."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.webhook_url,
                content=notification.model_dump_json(),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            logger.info("Webhook -> %s [%d]", settings.webhook_url, resp.status_code)
    except Exception:
        logger.exception("Webhook POST failed")


# ---- State persistence -------------------------------------------------

def _state_path() -> Path:
    return Path(settings.state_file)


def _load_state() -> Dict[str, str]:
    path = _state_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Could not read state file, starting fresh.")
    return {}


def _save_state(state: Dict[str, str]) -> None:
    try:
        _state_path().write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        logger.exception("Could not write state file")


def _grade_key(unit_nr: str, exam_name: str) -> str:
    return f"{unit_nr}::{exam_name}"


# ---- Dualis API communication ------------------------------------------

async def _fetch_semesters(client: httpx.AsyncClient) -> List[Semester]:
    resp = await client.post(
        f"{settings.dualis_api_url}/semesters",
        json={"user": settings.dualis_user, "password": settings.dualis_password},
        timeout=30,
    )
    resp.raise_for_status()
    return [Semester(**s) for s in resp.json()]


async def _fetch_grades(client: httpx.AsyncClient, semester_id: str) -> List[Unit]:
    resp = await client.post(
        f"{settings.dualis_api_url}/grades/{semester_id}",
        json={"user": settings.dualis_user, "password": settings.dualis_password},
        timeout=60,
    )
    resp.raise_for_status()
    return [Unit(**u) for u in resp.json()]


async def _resolve_semester_id(client: httpx.AsyncClient) -> str:
    if settings.semester_id:
        return settings.semester_id
    semesters = await _fetch_semesters(client)
    if not semesters:
        raise RuntimeError("No semesters found on Dualis")
    logger.info("Auto-detected semester: %s (%s)", semesters[0].name, semesters[0].id)
    return semesters[0].id


# ---- Main refresh loop -------------------------------------------------

async def refresh_loop() -> None:
    logger.info(
        "Starting refresh loop (interval: %ds, webhook: %s)",
        settings.refresh_interval_seconds,
        settings.webhook_url,
    )
    known = _load_state()

    while True:
        try:
            async with httpx.AsyncClient() as client:
                semester_id = await _resolve_semester_id(client)
                units = await _fetch_grades(client, semester_id)

            now = datetime.now(timezone.utc)
            new_count = 0

            for unit in units:
                for exam in unit.exams:
                    key = _grade_key(unit.unit_nr, exam.name)
                    old_grade = known.get(key)

                    is_new = (
                        exam.grade
                        and exam.grade != "noch nicht gesetzt"
                        and old_grade != exam.grade
                    )

                    if is_new:
                        new_count += 1
                        logger.info(
                            "NEW GRADE: %s / %s -> %s (was: %s)",
                            unit.unit_nr,
                            exam.name,
                            exam.grade,
                            old_grade or "unknown",
                        )
                        await _send_webhook(
                            GradeNotification(
                                unit_nr=unit.unit_nr,
                                title=unit.title,
                                semester=unit.semester,
                                exam=exam,
                                detected_at=now,
                            )
                        )

                    if exam.grade:
                        known[key] = exam.grade

            _save_state(known)

            if new_count == 0:
                logger.info("No new grades detected.")
            else:
                logger.info("Detected %d new grade(s).", new_count)

        except Exception:
            logger.exception("Error during refresh cycle")

        await asyncio.sleep(settings.refresh_interval_seconds)
