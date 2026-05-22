from __future__ import annotations

from typing import Any

from .config import Settings
from .models import IncomingMessage
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import mention


class EventService:
    def __init__(self, settings: Settings, store: RedisStore, bot: TelegramBot) -> None:
        self.settings = settings
        self.store = store
        self.bot = bot

    async def handle_update(self, update: dict[str, Any]) -> bool:
        if "my_chat_member" in update:
            return await self._my_chat_member(update["my_chat_member"])
        return False

    async def handle_message_event(self, msg: IncomingMessage) -> bool:
        if msg.content_type == "new_chat_members":
            await self._welcome(msg)
            return True
        if msg.content_type == "left_chat_member":
            await self._left(msg)
            return True
        return False

    async def _my_chat_member(self, data: dict[str, Any]) -> bool:
        chat = data.get("chat") or {}
        chat_id = int(chat.get("id", 0))
        new_status = (data.get("new_chat_member") or {}).get("status")
        old_status = (data.get("old_chat_member") or {}).get("status")
        actor = data.get("from") or {}
        if new_status in {"administrator", "member"} and old_status in {"left", "kicked"}:
            await self.activate_group(chat_id, int(actor.get("id", 0)))
            return True
        if new_status in {"left", "kicked"}:
            await self.store.srem(self.store.key("Zelzal:ChekBotAdd"), chat_id)
            return True
        return False

    async def activate_group(self, chat_id: int, actor_id: int) -> None:
        defaults = {
            "Zelzal:Alzwag:Chat": "true",
            "Zelzal:Aldel:Chat": "true",
            "NSFW:": "true",
            "tagallgroup": "open",
            "Zelzal:Status:Link": "true",
            "Zelzal:Status:Games": "true",
            "replayallbot": "true",
            "rebomsg": "true",
            "Zelzal:AlThther:Chat": "true",
            "Zelzal:Status:Welcome": "true",
            "tagall@all": "open",
            "Zelzal:Status:IdPhoto": "true",
            "Zelzal:Status:Id": "true",
            "Zelzal:Status:Reply": "true",
            "Zelzal:Status:ReplySudo": "true",
            "Zelzal:Status:BanId": "true",
            "Zelzal:Status:SetId": "true",
            "Zelzal:Lock:phshar": "true",
        }
        for name, value in defaults.items():
            await self.store.set(self.store.key(name, chat_id), value)
        await self.store.sadd(self.store.key("Zelzal:ChekBotAdd"), chat_id)
        if actor_id:
            await self.store.sadd(self.store.key("Zelzal:TheBasicsQ:Group", chat_id), actor_id)
            await self.store.sadd(self.store.key("Zelzal:MalekAsase:Group", chat_id), actor_id)
        try:
            await self.bot.send_message(chat_id, "*⇜ تم تفعيل المجموعة تلقائيـاً*\n*⇜ اضغـط* /Commands *لعـرض اوامـر البـوت*")
        except Exception:
            pass

    async def _welcome(self, msg: IncomingMessage) -> None:
        if await self.store.get(self.store.key("Zelzal:Lock:tagservr", msg.chat_id)):
            try:
                await self.bot.delete_message(msg.chat_id, msg.message_id)
            except Exception:
                pass
            return
        if not await self.store.get(self.store.key("Zelzal:Status:Welcome", msg.chat_id)):
            return
        welcome = await self.store.get(self.store.key("Zelzal:Welcome:Group", msg.chat_id)) or "⇜ اهلاً وسهلاً بك"
        for user in msg.new_chat_members:
            await self.bot.send_message(msg.chat_id, welcome.replace("{الاسم}", mention(int(user["id"]), user.get("first_name"))), msg.message_id)

    async def _left(self, msg: IncomingMessage) -> None:
        if await self.store.get(self.store.key("Zelzal:Lock:tagservr", msg.chat_id)):
            try:
                await self.bot.delete_message(msg.chat_id, msg.message_id)
            except Exception:
                pass

