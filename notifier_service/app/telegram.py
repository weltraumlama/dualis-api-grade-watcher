import logging

import httpx

from app.config import settings

logger = logging.getLogger("notifier-service")

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


def _format_message(unit_nr: str, title: str, semester: str,
                    exam_name: str, grade: str, date: str,
                    externally_accepted: bool) -> str:
    """Build a Telegram message with MarkdownV2 formatting."""
    # Escape special MarkdownV2 characters
    def esc(text: str) -> str:
        special = r"_*[]()~`>#+-=|{}.!"
        for ch in special:
            text = text.replace(ch, f"\\{ch}")
        return text

    lines = [
        "🎓 *Neue Note eingetragen\\!*",
        "",
        f"*Modul:* {esc(unit_nr)} \\- {esc(title)}",
        f"*Semester:* {esc(semester)}",
        f"*Prüfung:* {esc(exam_name)}",
        f"*Note:* {esc(grade)}",
    ]

    if date:
        lines.append(f"🗓 *Datum:* {esc(date)}")

    if externally_accepted:
        lines.append("🔄 _Extern anerkannt_")

    return "\n".join(lines)


async def send_notification(
    unit_nr: str,
    title: str,
    semester: str,
    exam_name: str,
    grade: str,
    date: str = "",
    externally_accepted: bool = False,
) -> bool:
    """Send a grade notification to the configured Telegram chat."""
    text = _format_message(
        unit_nr, title, semester, exam_name, grade, date, externally_accepted
    )

    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "MarkdownV2",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json=payload,
                timeout=10,
            )

            if resp.status_code == 200:
                logger.info("Telegram message sent successfully.")
                return True
            else:
                logger.error(
                    "Telegram API error [%d]: %s", resp.status_code, resp.text
                )
                return False
    except Exception:
        logger.exception("Failed to send Telegram message")
        return False
