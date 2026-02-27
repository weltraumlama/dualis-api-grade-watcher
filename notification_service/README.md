# notification-service

FastAPI service that receives a grade webhook and forwards it as a
Telegram message.

**Port:** `8332`
**Image:** `ghcr.io/weltraumlama/dualis-api-grade-watcher/dualis-notification-service:latest`

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/new-grade` | Receive grade notification and send Telegram message |

## Required environment variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Chat or user ID to send messages to |

See the [root README](../README.md) for full webhook payload schema and setup guide.
