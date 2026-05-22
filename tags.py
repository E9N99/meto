from __future__ import annotations

import json
import random

from .models import IncomingMessage
from .permissions import PermissionContext
from .redis_store import RedisStore
from .telegram import TelegramBot


TAG_REPLIES = [
    "ياعيوني تعال 🌹",
    "وينك حبي 😭",
    "تعال شوف الموضوع 😅",
    "هلا نورت 😍",
    "الگروب منور بيك ✨",
    "لك وينك اختفيت؟ 😂",
    "ناديته الك حيل 🥺",
]


class TagsService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if not text or msg.chat_type == "private":
            return False
        if await self._finish_add(msg):
            return True
        if text == "اضف تاك":
            if not self._allowed(ctx):
                return False
            await self.store.set(self._state_key(msg), json.dumps({"step": "name"}, ensure_ascii=False))
            await self.bot.send_message(msg.chat_id, "↜ ارسل الان اسم التاك 🌹", msg.message_id)
            return True
        if text.startswith("مسح تاك "):
            if not self._allowed(ctx):
                return False
            name = text.removeprefix("مسح تاك ").strip()
            tags = await self._load_tags(msg.chat_id)
            if name in tags:
                tags.pop(name, None)
                await self._save_tags(msg.chat_id, tags)
                await self.bot.send_message(msg.chat_id, f"↜ تم مسح التاك ({name}) ✅", msg.message_id)
            else:
                await self.bot.send_message(msg.chat_id, "↜ هذا التاك مو موجود ❌", msg.message_id)
            return True
        if text == "قائمة التاكات":
            tags = await self._load_tags(msg.chat_id)
            lines = ["↜ قائمة التاكات المضافة 📋:"]
            for name, user in tags.items():
                lines.append(f"\n{name} → {user}")
            await self.bot.send_message(msg.chat_id, "".join(lines), msg.message_id)
            return True
        if text == "مسح قائمة التاكات":
            if not self._allowed(ctx):
                return False
            await self._save_tags(msg.chat_id, {})
            await self.bot.send_message(msg.chat_id, "↜ تم مسح جميع التاكات ✅", msg.message_id)
            return True
        tags = await self._load_tags(msg.chat_id)
        for name, user in tags.items():
            if name and name in text:
                await self.bot.send_message(msg.chat_id, f"{random.choice(TAG_REPLIES)} : {user}", msg.message_id)
                return True
        return False

    async def _finish_add(self, msg: IncomingMessage) -> bool:
        state_raw = await self.store.get(self._state_key(msg))
        if not state_raw:
            return False
        state = json.loads(state_raw)
        text = msg.effective_text or ""
        if state.get("step") == "name":
            state = {"step": "user", "name": text}
            await self.store.set(self._state_key(msg), json.dumps(state, ensure_ascii=False))
            await self.bot.send_message(msg.chat_id, f"↜ تم حفظ الاسم ({text}) ✅\n↜ الان ارسل اليوزر 🌹", msg.message_id)
            return True
        if state.get("step") == "user":
            name = str(state.get("name", ""))
            tags = await self._load_tags(msg.chat_id)
            tags[name] = text
            await self._save_tags(msg.chat_id, tags)
            await self.store.delete(self._state_key(msg))
            await self.bot.send_message(msg.chat_id, f"↜ تم حفظ التاك بنجاح ✅\n{name} → {text}", msg.message_id)
            return True
        await self.store.delete(self._state_key(msg))
        return True

    def _allowed(self, ctx: PermissionContext) -> bool:
        return ctx.manager or ctx.creator or ctx.creator_basic or ctx.owner or ctx.controller_bot

    def _state_key(self, msg: IncomingMessage) -> str:
        return self.store.key("tags:add:", msg.chat_id, ":", msg.user_id)

    def _tags_key(self, chat_id: int) -> str:
        return f"tags:{chat_id}"

    async def _load_tags(self, chat_id: int) -> dict[str, str]:
        raw = await self.store.get(self._tags_key(chat_id))
        if not raw:
            await self.store.set(self._tags_key(chat_id), "{}")
            return {}
        try:
            data = json.loads(raw)
        except Exception:
            return {}
        return {str(key): str(value) for key, value in data.items()}

    async def _save_tags(self, chat_id: int, values: dict[str, str]) -> None:
        await self.store.set(self._tags_key(chat_id), json.dumps(values, ensure_ascii=False))
