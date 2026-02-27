# refresh-service

Polls the dualis-api-service for grade changes and fires a webhook to the
notification-service when a new or changed grade is detected.

**Port:** `8331`
**Image:** `ghcr.io/weltraumlama/dualis-api-grade-watcher/dualis-refresh-service:latest`

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |

The polling loop starts automatically on service startup.

## Required environment variables

| Variable | Description |
|---|---|
| `DUALIS_USER` | Dualis login e-mail |
| `DUALIS_PASSWORD` | Dualis password |

See the [root README](../README.md) for all optional variables and setup guide.
