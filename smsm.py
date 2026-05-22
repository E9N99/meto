from __future__ import annotations

import json
from urllib.parse import quote
from urllib.request import urlopen

from .config import Settings
from .models import IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot


class SmsmService:
    def __init__(self, settings: Settings, store: RedisStore, bot: TelegramBot) -> None:
        self.settings = settings
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if text == "تفعيل سمسمي":
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, f"\n*• هذا الامر يخص {controller_num(6)} *", msg.message_id)
                return True
            await self.store.delete(self.store.key("smsme", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "• تم تفعيل سمسمي", msg.message_id, parse_mode=None)
            return True
        if text == "تعطيل سمسمي":
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, f"\n*• هذا الامر يخص {controller_num(6)} *", msg.message_id)
                return True
            await self.store.set(self.store.key("smsme", msg.chat_id), "true")
            return True
        if not text or msg.reply_to_user_id != self.settings.bot_id:
            return False
        disabled = await self.store.get(self.store.key("smsme")) or await self.store.get(self.store.key("smsme", msg.chat_id))
        if disabled:
            return False
        try:
            ai_text = await self._ask(text)
        except Exception:
            return False
        if "سناب" in ai_text or " تيك " in ai_text:
            ai_text = "لا افهمك"
        await self.bot.send_message(msg.chat_id, ai_text, msg.message_id, parse_mode=None)
        return True

    async def _ask(self, text: str) -> str:
        import asyncio

        def run() -> str:
            url = "https://dev-almortageltech.pantheonsite.io/api/smsm.php?almortagel=ه" + quote(text) + "&lc=ar&cf=false"
            with urlopen(url, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return str(payload.get("success", ""))

        return await asyncio.to_thread(run)
