from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .config import Settings
from .models import IncomingMessage
from .permissions import PermissionContext
from .redis_store import RedisStore
from .telegram import TelegramBot


class NSFWService:
    def __init__(self, settings: Settings, store: RedisStore, bot: TelegramBot) -> None:
        self.settings = settings
        self.store = store
        self.bot = bot

    async def handle_command(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if text not in {"تفعيل الاباحي", "تعطيل الاباحي", "تفعيل NSFW", "تعطيل NSFW"}:
            return False
        if not ctx.manager:
            return True
        key = self.store.key("NSFW:", msg.chat_id)
        if text.startswith("تفعيل"):
            await self.store.set(key, "true")
            await self.bot.send_message(msg.chat_id, "⇜ تم تفعيل كاشف المحتوى غير المناسب", msg.message_id)
        else:
            await self.store.delete(key)
            await self.bot.send_message(msg.chat_id, "⇜ تم تعطيل كاشف المحتوى غير المناسب", msg.message_id)
        return True

    async def scan(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        if ctx.distinguished or msg.content_type not in {"photo", "video", "animation"}:
            return False
        if not await self.store.get(self.store.key("NSFW:", msg.chat_id)):
            return False
        score = await self._score(msg)
        if score < self.settings.nsfw_threshold:
            return False
        try:
            await self.bot.delete_message(msg.chat_id, msg.message_id)
        except Exception:
            pass
        await self.bot.send_message(msg.chat_id, f"⇜ تم حذف محتوى غير مناسب\n⇜ نسبة الاشتباه : {score:.0%}", None)
        return True

    async def _score(self, msg: IncomingMessage) -> float:
        """Return NSFW probability score in [0..1].

        NOTE:
        - This project contains an original TF/Keras detector under lua-src/detect.py.
        - Telegram file download is required before running inference.
        """
        # Conservative fallback: if no media, don't score.
        if msg.content_type not in {"photo", "video", "animation"}:
            return 0.0

        # Wiring depends on how IncomingMessage stores remote file_id.
        # We try common attribute locations defensively.
        file_id: str | None = None
        if hasattr(msg, "photo") and msg.photo:
            file_id = msg.photo
        if file_id is None and hasattr(msg, "video") and msg.video:
            file_id = msg.video
        if file_id is None and hasattr(msg, "animation") and msg.animation:
            file_id = msg.animation
        if file_id is None and hasattr(msg, "effective_media"):
            file_id = getattr(msg.effective_media, "file_id", None)

        if not file_id:
            return 0.0

        # Download media from Telegram to a local temp file and run detector.
        # We rely on existing TelegramBot API via getFile/file_path.
        try:
            tg_file = await self.bot.request("getFile", file_id=file_id)
            file_path = tg_file.get("file_path")
            if not file_path:
                return 0.0

            # Telegram file download URL
            url = f"https://api.telegram.org/file/bot{self.settings.token}/{file_path}"
            import urllib.request
            from tempfile import NamedTemporaryFile

            with NamedTemporaryFile(delete=False, suffix=Path(file_path).suffix or "") as f:
                local_path = Path(f.name)
            urllib.request.urlretrieve(url, str(local_path))

            # Run the bundled detector. It returns "NONPORN" / "POORN" in stdout.
            # The detector expects a video file path.
            detect_script = Path(__file__).parent / "lua-src" / "detect.py"
            proc = await asyncio.to_thread(
                lambda: __import__("subprocess").run(
                    ["python", str(detect_script), str(local_path)],
                    capture_output=True,
                    text=True,
                )
            )
            out = (proc.stdout or "") + (proc.stderr or "")

            local_path.unlink(missing_ok=True)

            out_upper = out.upper()
            if "POORN" in out_upper:
                return 1.0
            if "NONPORN" in out_upper:
                return 0.0

            return 0.0
        except Exception:
            return 0.0


