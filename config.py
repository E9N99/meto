from __future__ import annotations

from dataclasses import dataclass
import os
import sys
from pathlib import Path


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass(slots=True)
class Settings:
    token: str
    sudo_id: int
    sudo_username: str = ""
    bot_username: str = ""
    redis_url: str = "redis://127.0.0.1:6379/0"
    nsfw_threshold: float = 0.75
    poll_timeout: int = 25
    in_memory_redis: bool = False

    @property
    def bot_id(self) -> int:
        return int(self.token.split(":", 1)[0])

    @property
    def redis_prefix(self) -> str:
        return str(self.bot_id)

    @classmethod
    def from_env(cls) -> "Settings":
        dotenv = _load_dotenv(Path(".env"))
        token = os.getenv("BOT_TOKEN") or dotenv.get("BOT_TOKEN") or ""
        sudo_id = os.getenv("SUDO_ID") or dotenv.get("SUDO_ID") or "0"
        sudo_username = os.getenv("SUDO_USERNAME") or dotenv.get("SUDO_USERNAME") or ""
        bot_username = os.getenv("BOT_USERNAME") or dotenv.get("BOT_USERNAME") or ""
        if not token and sys.stdin.isatty():
            token = input("ارسل لي توكن البوت الان: ").strip()
        if (not sudo_id or sudo_id == "0") and sys.stdin.isatty():
            sudo_id = input("ارسل ايدي المطور الاساسي الان: ").strip() or "0"
        if not sudo_username and sys.stdin.isatty():
            sudo_username = input("ارسل معرف المطور الاساسي بدون @ الان: ").strip().lstrip("@")
        if not token:
            raise RuntimeError("BOT_TOKEN is required. Put it in .env or set $env:BOT_TOKEN.")
        if not sudo_id or sudo_id == "0":
            raise RuntimeError("SUDO_ID is required. Put it in .env or set $env:SUDO_ID.")
        return cls(
            token=token,
            sudo_id=int(float(sudo_id)),
            sudo_username=sudo_username,
            bot_username=bot_username,
            redis_url=os.getenv("REDIS_URL") or dotenv.get("REDIS_URL") or "redis://127.0.0.1:6379/0",
            nsfw_threshold=float(os.getenv("NSFW_THRESHOLD") or dotenv.get("NSFW_THRESHOLD") or "0.75"),
            poll_timeout=int(os.getenv("POLL_TIMEOUT") or dotenv.get("POLL_TIMEOUT") or "25"),
            in_memory_redis=(os.getenv("ZELZAL_IN_MEMORY") or dotenv.get("ZELZAL_IN_MEMORY") or "0") == "1",
        )
