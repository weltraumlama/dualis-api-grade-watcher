# dualis-api-service

FastAPI service that authenticates against the DHBW Dualis portal and scrapes
grade data.

**Port:** `8000`
**Image:** `ghcr.io/weltraumlama/dualis-api-service:latest`

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/semesters` | List available semesters |
| `POST` | `/grades` | Grades from all semesters |
| `POST` | `/grades/{semester_id}` | Grades for one semester |

All grade endpoints require a JSON body with `user` (e-mail) and `password`.

See the [root README](../README.md) for full request/response schemas.
