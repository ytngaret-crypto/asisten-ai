# Telegram AI Group Bot — Railway + SQLite

Telegram group AI bot using Gemini and a local SQLite file database.

## Required Railway variables

- `TELEGRAM_BOT_TOKEN`
- `OWNER_ID`
- `GEMINI_API_KEY`

No `DATABASE_URL` is required.

## Optional database path

`BOT_DB_PATH` defaults to `bot.db`.
For a persistent Railway Volume mounted at `/data`, set:

`BOT_DB_PATH=/data/bot.db`

Without a persistent volume, the SQLite file can be lost when Railway replaces the service/container. The bot will recreate the database tables on startup.

## Optional model/settings variables

- `GEMINI_MODEL=gemini-3.1-flash-lite`
- `GEMINI_IMAGE_MODEL=gemini-3.1-flash-image`
- `GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview`
- `CONTEXT_LIMIT=20`
- `MEMORY_LIMIT=50`
