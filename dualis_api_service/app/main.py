import logging
import re
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, constr
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple

app = FastAPI(title="Dualis Grades API", version="1.1.0")

BASE_URL = "https://dualis.dhbw.de"
SCRIPT_PATH = f"{BASE_URL}/scripts/mgrqispi.dll"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dualis-api")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class Credentials(BaseModel):
    user: EmailStr
    password: constr(min_length=8)


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


# ---------------------------------------------------------------------------
# Session & Login Helpers
# ---------------------------------------------------------------------------

def _create_session() -> requests.Session:
    """Create a fresh requests session with browser-like headers."""
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })
    return s


def _login(credentials: Credentials) -> Tuple[requests.Session, str, BeautifulSoup]:
    """
    Login to Dualis and return the authenticated session, the base
    COURSERESULTS URL (without semester suffix), and the semester overview soup.

    Raises HTTPException on failure.
    """
    s = _create_session()

    # 1. Get initial cookies
    url = (
        f"{SCRIPT_PATH}?APPNAME=CampusNet&PRGNAME=EXTERNALPAGES"
        f"&ARGUMENTS=-N000000000000001,-N000324,-Awelcome"
    )
    cookie_response = s.get(url, timeout=10)
    if not cookie_response.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to Dualis.",
        )

    # 2. Login
    data = {
        "usrname": credentials.user,
        "pass": credentials.password,
        "APPNAME": "CampusNet",
        "PRGNAME": "LOGINCHECK",
        "ARGUMENTS": "clino,usrname,pass,menuno,menu_type,browser,platform",
        "clino": "000000000000001",
        "menuno": "000324",
        "menu_type": "classic",
        "browser": "",
        "platform": "",
    }
    login_response = s.post(url, data=data, timeout=10, allow_redirects=False)

    refresh = login_response.headers.get("REFRESH")
    if not refresh:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Dualis login failed.",
        )

    # 3. Follow REFRESH URL to initialise server-side session
    refresh_parts = refresh.split("URL=", 1)
    if len(refresh_parts) > 1:
        s.get(f"{BASE_URL}{refresh_parts[1]}", timeout=10)

    # 4. Extract ARGUMENTS for course results
    args_marker = "ARGUMENTS="
    args_index = refresh.find(args_marker)
    if args_index == -1:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Dualis login failed.",
        )
    extracted_args = refresh[args_index + len(args_marker) :]

    # 5. Get semester overview
    url_content = (
        f"{SCRIPT_PATH}?APPNAME=CampusNet&PRGNAME=COURSERESULTS"
        f"&ARGUMENTS={extracted_args}"
    )
    semester_response = s.get(url_content, timeout=10)
    if not semester_response.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve semesters.",
        )

    soup = BeautifulSoup(
        semester_response.content, "html.parser", from_encoding="utf-8"
    )

    return s, url_content, soup


def _logout(s: requests.Session, soup: BeautifulSoup) -> None:
    """Attempt to logout from Dualis."""
    try:
        tag = soup.find("a", {"id": "logoutButton"})
        if tag and tag.get("href"):
            s.get(f"{BASE_URL}{tag['href']}", timeout=10)
    except Exception:
        logger.warning("Logout failed.")


def _get_semesters(soup: BeautifulSoup) -> List[Semester]:
    """Extract available semesters from the semester overview page."""
    semesters = []
    for opt in soup.find_all("option"):
        value = opt.get("value")
        name = opt.text.strip()
        if value and name:
            semesters.append(Semester(id=value, name=name))
    return semesters


# ---------------------------------------------------------------------------
# Parsing Helpers
# ---------------------------------------------------------------------------

def _parse_unit_heading(raw: str) -> Tuple[str, str, str]:
    """
    Parse the h1 heading into (unit_nr, title, semester).

    Expected formats:
        'T3INF3001  Software Engineering II (SoSe 2026)'
        'T3_3101  Studienarbeit (SoSe 2026)'
    """
    raw = raw.replace("\n", " ").replace("\r", "").strip()

    match = re.match(r"^(\S+)\s{1,}(.+?)\s*\(([^)]+)\)\s*$", raw)
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()

    parts = re.split(r"\s{2,}", raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip(), ""

    return raw, raw, ""


def _parse_semester_page(url: str, s: requests.Session) -> List[str]:
    """Extract all unit detail URLs from a semester page."""
    try:
        response = s.get(url, timeout=10)
        if not response.ok:
            return []
        soup = BeautifulSoup(
            response.content, "html.parser", from_encoding="utf-8"
        )
        table = soup.find("table", {"class": "list"})
        if not table:
            return []
        unit_urls = []
        for script in table.find_all("script"):
            match = re.search(r'dl_popUp\("(/scripts/[^"]+)"', script.text)
            if match:
                unit_urls.append(match.group(1))
        return unit_urls
    except Exception:
        logger.exception("Error parsing semester.")
        return []


def _parse_unit_page(url: str, s: requests.Session) -> Unit | None:
    """Parse a unit detail page and extract exams."""
    try:
        response = s.get(f"{BASE_URL}{url}", timeout=10)
        if not response.ok:
            return None
        soup = BeautifulSoup(
            response.content, "html.parser", from_encoding="utf-8"
        )

        h1_tag = soup.find("h1")
        if not h1_tag:
            return None
        unit_nr, title, semester = _parse_unit_heading(h1_tag.text)

        table = soup.find("table", {"class": "tb"})
        if not table:
            return None

        exams: List[Exam] = []
        for row in table.find_all("tr"):
            cells = row.find_all("td", class_="tbdata")
            if not cells:
                continue
            values = [c.text.strip() for c in cells]

            meaningful = [v for v in values if v and v != "noch nicht gesetzt"]
            if not meaningful:
                continue

            exam_name = values[1] if len(values) > 1 else ""
            exam_date = values[2] if len(values) > 2 else ""
            exam_grade = values[3] if len(values) > 3 else ""
            externally_accepted = bool(values[4].strip()) if len(values) > 4 else False

            if exam_name or exam_grade:
                exams.append(
                    Exam(
                        name=exam_name,
                        date=exam_date,
                        grade=exam_grade,
                        externally_accepted=externally_accepted,
                    )
                )

        if not exams:
            return None

        return Unit(unit_nr=unit_nr, title=title, semester=semester, exams=exams)
    except Exception:
        logger.exception("Error parsing unit.")
        return None


def _collect_units(
    semester_urls: List[str], s: requests.Session
) -> List[Unit]:
    """Parse all units across the given semester URLs."""
    units: List[Unit] = []
    for semester_url in semester_urls:
        for unit_url in _parse_semester_page(semester_url, s):
            unit = _parse_unit_page(unit_url, s)
            if unit:
                units.append(unit)
    return units


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/semesters", response_model=List[Semester])
def get_semesters(credentials: Credentials):
    """List all available semesters with their IDs."""
    try:
        s, _, soup = _login(credentials)
        semesters = _get_semesters(soup)
        _logout(s, soup)
        return semesters
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error occurred.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        )


@app.post("/grades", response_model=List[Unit])
def get_grades(credentials: Credentials):
    """Query grades from all semesters."""
    try:
        s, url_content, soup = _login(credentials)

        semesters = _get_semesters(soup)
        semester_urls = [url_content[:-15] + sem.id for sem in semesters]

        units = _collect_units(semester_urls, s)
        _logout(s, soup)
        return units

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error occurred.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        )


@app.post("/grades/{semester_id}", response_model=List[Unit])
def get_grades_by_semester(semester_id: str, credentials: Credentials):
    """
    Query grades for a specific semester.

    Use GET /semesters first to retrieve available semester IDs.
    Example: POST /grades/000000015178330
    """
    try:
        s, url_content, soup = _login(credentials)

        # Validate that the semester ID exists
        semesters = _get_semesters(soup)
        valid_ids = {sem.id for sem in semesters}
        if semester_id not in valid_ids:
            _logout(s, soup)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Semester '{semester_id}' not found. "
                       f"Available: {[sem.id for sem in semesters]}",
            )

        semester_url = url_content[:-15] + semester_id
        units = _collect_units([semester_url], s)
        _logout(s, soup)
        return units

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error occurred.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        )