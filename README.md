# dualis-api-grade-watcher

Automatically watches your DHBW Dualis grades and sends a Telegram notification
the moment a new grade appears.

Three microservices work together:

```
                     poll grades
  refresh-service  ------------->  dualis-api-service
    (port 8001)                       (port 8000)
        |
        | webhook on new grade
        v
  notification-service  ------->  Telegram
     (port 8002)
```

---

## Services

| Service | Image | Port | Description |
|---|---|---|---|
| `dualis-api-service` | `ghcr.io/weltraumlama/dualis-api-service:latest` | 8000 | Scrapes Dualis and exposes a REST API for grades |
| `refresh-service` | `ghcr.io/weltraumlama/dualis-refresh-service:latest` | 8001 | Polls the API on an interval, fires a webhook on new grades |
| `notification-service` | `ghcr.io/weltraumlama/dualis-notification-service:latest` | 8002 | Receives the webhook and sends a Telegram message |

---

## Quick Setup

**1. Download `docker-compose.yaml` and fill in your values**

```yaml
# refresh-service
- DUALIS_USER=your@email.de
- DUALIS_PASSWORD=yourpassword

# notification-service
- TELEGRAM_BOT_TOKEN=123456:ABC-...
- TELEGRAM_CHAT_ID=123456789
```

**2. Pull images and start**

```bash
docker compose pull
docker compose up -d
```

**3. Verify**

```bash
docker compose ps
```

---

## Environment Variables

### `refresh-service`

| Variable | Required | Default | Description |
|---|---|---|---|
| `DUALIS_USER` | yes | — | Dualis login e-mail |
| `DUALIS_PASSWORD` | yes | — | Dualis password (min 8 chars) |
| `SEMESTER_ID` | no | *(auto-detect latest)* | Semester ID to watch. Leave empty to use the most recent semester automatically. Retrieve valid IDs via `POST /semesters`. |
| `REFRESH_INTERVAL_SECONDS` | no | `300` | Polling interval in seconds |
| `DUALIS_API_URL` | no | `http://dualis-api-service:8000` | Internal URL of the dualis-api-service |
| `WEBHOOK_URL` | no | `http://notification-service:8002/new-grade` | Internal URL of the notification webhook |
| `STATE_FILE` | no | `grades_state.json` | Path to the grade state file (persisted via Docker volume) |
| `PORT` | no | `8001` | Listening port |

### `notification-service`

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | yes | — | Target chat/user ID for grade notifications |
| `PORT` | no | `8002` | Listening port |

### `dualis-api-service`

No environment variables needed. The service is stateless — credentials are passed per request.

---

## API Reference

### dualis-api-service — `http://localhost:8000`

> Interactive Swagger UI available at `/docs`.

#### `GET /health`
Liveness check. Returns `{"status": "ok"}`.

---

#### `POST /semesters`
Returns all semesters available for the authenticated user.
Use this to look up a valid `semester_id`.

**Request body**
```json
{
  "user": "your@email.de",
  "password": "yourpassword"
}
```

**Response `200`**
```json
[
  { "id": "000000015178000", "name": "Wintersemester 2024/2025" },
  { "id": "000000014901000", "name": "Sommersemester 2024" }
]
```

---

#### `POST /grades`
Returns grades from **all** semesters.

**Request body** — same as `/semesters`

**Response `200`** — array of `Unit` objects (see schema below)

---

#### `POST /grades/{semester_id}`
Returns grades for a **specific** semester.

| Path param | Description |
|---|---|
| `semester_id` | Numeric ID from `POST /semesters` (e.g. `000000015178000`) |

**Request body** — same as `/semesters`

**Response `200`**
```json
[
  {
    "unit_nr": "T3INF3001",
    "title": "Software Engineering II",
    "semester": "SoSe 2026",
    "exams": [
      {
        "name": "Klausur",
        "date": "2026-02-10",
        "grade": "1,7",
        "externally_accepted": false
      }
    ]
  }
]
```

**Error responses**

| Code | Reason |
|---|---|
| `404` | `semester_id` not found for this user |
| `502` | Dualis login failed or Dualis unreachable |

---

### refresh-service — `http://localhost:8001`

#### `GET /health`
Liveness check. Returns `{"status": "ok"}`.

The grade polling loop starts automatically on startup. There are no other endpoints.

---

### notification-service — `http://localhost:8002`

#### `GET /health`
Liveness check. Returns `{"status": "ok"}`.

---

#### `POST /new-grade`
Webhook called by the refresh-service when a new or changed grade is detected.

**Request body**
```json
{
  "unit_nr": "T3INF3001",
  "title": "Software Engineering II",
  "semester": "SoSe 2026",
  "exam": {
    "name": "Klausur",
    "date": "2026-02-10",
    "grade": "1,7",
    "externally_accepted": false
  },
  "detected_at": "2026-02-27T14:00:00Z"
}
```

**Response `200`** — `{"status": "sent"}`

**Response `502`** — Telegram API error or unreachable.

---

## Grade State Persistence

The refresh-service writes known grades to a JSON file inside the `refresh-state`
Docker volume. A notification fires only once per grade — on first detection or
when a grade value changes. Restarting the container does **not** re-send known grades.

---

## Getting your Telegram Chat ID

Talk to [@userinfobot](https://t.me/userinfobot) on Telegram — it replies with
your numeric user ID. Set that as `TELEGRAM_CHAT_ID`.
