import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    telegram_token: str
    owner_id: int
    gemini_api_key: str
    gemini_model: str
    gemini_image_model: str
    gemini_tts_model: str
    database_path: str
    context_limit: int
    memory_limit: int

    @classmethod
    def from_env(cls):
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        key = os.getenv("GEMINI_API_KEY", "").strip()
        owner_raw = os.getenv("OWNER_ID", "").strip()

        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi.")
        if not key:
            raise RuntimeError("GEMINI_API_KEY belum diisi.")
        if not owner_raw:
            raise RuntimeError("OWNER_ID belum diisi. Isi dengan Telegram numeric user ID pemilik bot.")
        try:
            owner_id = int(owner_raw)
        except ValueError as exc:
            raise RuntimeError("OWNER_ID harus berupa angka Telegram numeric user ID.") from exc
        if owner_id <= 0:
            raise RuntimeError("OWNER_ID harus berupa angka positif.")

        raw_path = os.getenv("BOT_DB_PATH", "bot.db").strip() or "bot.db"
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            telegram_token=token,
            owner_id=owner_id,
            gemini_api_key=key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            gemini_image_model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
            gemini_tts_model=os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview"),
            database_path=str(path),
            context_limit=max(5, int(os.getenv("CONTEXT_LIMIT", "20"))),
            memory_limit=max(10, int(os.getenv("MEMORY_LIMIT", "50"))),
        )
