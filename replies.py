from __future__ import annotations

from dataclasses import dataclass
import random

from .models import IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import deny, mention


@dataclass(slots=True)
class StoredReply:
    kind: str
    value: str
    caption: str = ""


MEDIA_ORDER = [
    ("Text", "text"),
    ("Photo", "photo"),
    ("Video", "video"),
    ("Gif", "animation"),
    ("File", "document"),
    ("Audio", "audio"),
    ("Vico", "voice"),
    ("Stekrs", "sticker"),
    ("video_note", "video_note"),
]


class ReplyService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        if await self.store.get(self.store.key("Zelzal:Disabled:الردود:", msg.chat_id)) and not ctx.manager:
            return False
        if await self._finish_add(msg, ctx, global_reply=False):
            return True
        if await self._finish_add(msg, ctx, global_reply=True):
            return True
        text = msg.effective_text or ""
        if text in {"اضف رد", "اضف رد خاص"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:Set:Manager:rd", msg.user_id, ":", msg.chat_id), "true")
            await self.bot.send_message(msg.chat_id, "*⇜ حسناً ارسل كلمة الرد*", msg.message_id)
            return True
        if text in {"اضف رد متعدد", "اضف رد متعدد خاص"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:Set:MultiRd", msg.user_id, ":", msg.chat_id), "trigger")
            await self.bot.send_message(msg.chat_id, "*⇜ حسناً ارسل كلمة الرد المتعدد*", msg.message_id)
            return True
        if text == "اضف رد متعدد عام":
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:Set:MultiRd:Sudo", msg.user_id, ":", msg.chat_id), "trigger")
            await self.bot.send_message(msg.chat_id, "*⇜ حسناً ارسل كلمة الرد المتعدد العام*", msg.message_id)
            return True
        if text == "مسح رد متعدد عام":
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:Set:MultiRd:Sudo", msg.user_id, ":", msg.chat_id), "delete")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل اسم الرد المتعدد العام لمسحه*", msg.message_id)
            return True
        if text in {"مسح رد متعدد", "حذف رد متعدد"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:Set:MultiRd", msg.user_id, ":", msg.chat_id), "delete")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل اسم الرد المتعدد لمسحه*", msg.message_id)
            return True
        if text in {"الردود المتعدده", "الردود المتعددة"}:
            values = sorted(await self.store.smembers(self.store.key("Zelzal:List:MultiRd", msg.chat_id)))
            await self.bot.send_message(msg.chat_id, "\n".join(["*⇜ قائمة الردود المتعددة*"] + [f"{i} - {v}" for i, v in enumerate(values, 1)]) if values else "*⇜ لا توجد ردود متعددة*", msg.message_id)
            return True
        if text in {"الردود المتعدده عام", "الردود المتعددة عام"}:
            values = sorted(await self.store.smembers(self.store.key("Zelzal:List:MultiRd:Sudo")))
            await self.bot.send_message(msg.chat_id, "\n".join(["*⇜ قائمة الردود المتعددة العامة*"] + [f"{i} - {v}" for i, v in enumerate(values, 1)]) if values else "*⇜ لا توجد ردود متعددة عامة*", msg.message_id)
            return True
        if text in {"مسح رد", "حذف رد"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:Set:Manager:rd", msg.user_id, ":", msg.chat_id), "true2")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل الرد الذي تريد مسحه*", msg.message_id)
            return True
        if text in {"الردود", "الردود المضافه"}:
            await self._list_replies(msg, global_reply=False)
            return True
        if text in {"مسح الردود", "مسح الردود المضافه"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self._clear_replies(msg, global_reply=False)
            return True
        if text == "اضف رد عام":
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:Set:Rd", msg.user_id, ":", msg.chat_id), "true")
            await self.bot.send_message(msg.chat_id, "*⇜ حسناً ارسل كلمة الرد العام*", msg.message_id)
            return True
        if text in {"الردود العامه", "الردود العامة"}:
            await self._list_replies(msg, global_reply=True)
            return True
        if text in {"مسح الردود العامه", "مسح الردود العامة"}:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self._clear_replies(msg, global_reply=True)
            return True
        return await self.send_matching(msg, ctx)

    async def send_matching(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text
        if not text:
            return False
        for global_reply in (True, False):
            reply = await self._get_reply(text, msg.chat_id, global_reply)
            if reply:
                await self._send_reply(msg, ctx, reply)
                return True
        multi = await self.store.smembers(self.store.key("Zelzal:Add:MultiRd:Sudo:", text))
        if multi:
            await self.bot.send_message(msg.chat_id, random.choice(sorted(multi)), msg.message_id)
            return True
        multi = await self.store.smembers(self.store.key("Zelzal:Add:MultiRd", msg.chat_id, ":", text))
        if multi:
            await self.bot.send_message(msg.chat_id, random.choice(sorted(multi)), msg.message_id)
            return True
        return False

    async def _finish_add(self, msg: IncomingMessage, ctx: PermissionContext, global_reply: bool) -> bool:
        if await self._finish_multi(msg, ctx, global_reply):
            return True
        state_key = self.store.key("Zelzal:Set:Rd" if global_reply else "Zelzal:Set:Manager:rd", msg.user_id, ":", msg.chat_id)
        state = await self.store.get(state_key)
        if not state:
            return False
        list_key = self.store.key("Zelzal:List:Rd:Sudo") if global_reply else self.store.key("Zelzal:List:Manager", msg.chat_id)
        if state == "true2":
            trigger = msg.effective_text or ""
            await self._delete_reply_keys(trigger, msg.chat_id, global_reply)
            await self.store.srem(list_key, trigger)
            await self.store.delete(state_key)
            await self.bot.send_message(msg.chat_id, "*⇜ ابشر .. مسحت الـرد مـن الـردود ✅*", msg.message_id)
            return True
        if state == "true":
            trigger = msg.effective_text
            if not trigger:
                return True
            await self.store.set(state_key, "true1")
            await self.store.set(self.store.key("Zelzal:Text:Sudo:Bot" if global_reply else "Zelzal:Text:Manager", msg.user_id, ":", msg.chat_id), trigger)
            await self.store.sadd(list_key, trigger)
            await self._delete_reply_keys(trigger, msg.chat_id, global_reply)
            await self.bot.send_message(
                msg.chat_id,
                "*⇜ حلو , الحين ارسل جواب الرد*\n*⇜ ( نص,صوره,فيديو,متحركه,بصمه,اغنيه )*",
                msg.message_id,
            )
            return True
        if state == "true1":
            trigger = await self.store.get(self.store.key("Zelzal:Text:Sudo:Bot" if global_reply else "Zelzal:Text:Manager", msg.user_id, ":", msg.chat_id))
            if not trigger:
                await self.store.delete(state_key)
                return True
            await self._store_payload(trigger, msg, global_reply)
            await self.store.delete(state_key)
            await self.bot.send_message(msg.chat_id, f"*「  *{trigger}*  」\nواضفنا الرد ياحلو 🌚\n✓*", msg.message_id)
            return True
        return False

    async def _finish_multi(self, msg: IncomingMessage, ctx: PermissionContext, global_reply: bool) -> bool:
        state_key = self.store.key("Zelzal:Set:MultiRd:Sudo" if global_reply else "Zelzal:Set:MultiRd", msg.user_id, ":", msg.chat_id)
        state = await self.store.get(state_key)
        if not state:
            return False
        if global_reply and not ctx.controller_bot:
            return False
        text = msg.effective_text or ""
        list_key = self.store.key("Zelzal:List:MultiRd:Sudo") if global_reply else self.store.key("Zelzal:List:MultiRd", msg.chat_id)
        if state == "delete":
            add_key = self.store.key("Zelzal:Add:MultiRd:Sudo:", text) if global_reply else self.store.key("Zelzal:Add:MultiRd", msg.chat_id, ":", text)
            await self.store.delete(add_key)
            await self.store.srem(list_key, text)
            await self.store.delete(state_key)
            await self.bot.send_message(msg.chat_id, "*⇜ تم مسح الرد المتعدد*", msg.message_id)
            return True
        if state == "trigger":
            await self.store.set(self.store.key("Zelzal:MultiRd:Trigger", msg.user_id, ":", msg.chat_id), text)
            await self.store.sadd(list_key, text)
            await self.store.set(state_key, "answers")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل الردود واحداً واحداً، وارسل `تم` للحفظ*", msg.message_id)
            return True
        if state == "answers":
            trigger = await self.store.get(self.store.key("Zelzal:MultiRd:Trigger", msg.user_id, ":", msg.chat_id))
            if not trigger:
                await self.store.delete(state_key)
                return True
            if text == "تم":
                await self.store.delete(state_key, self.store.key("Zelzal:MultiRd:Trigger", msg.user_id, ":", msg.chat_id))
                await self.bot.send_message(msg.chat_id, "*⇜ تم حفظ الرد المتعدد*", msg.message_id)
                return True
            add_key = self.store.key("Zelzal:Add:MultiRd:Sudo:", trigger) if global_reply else self.store.key("Zelzal:Add:MultiRd", msg.chat_id, ":", trigger)
            await self.store.sadd(add_key, text)
            await self.bot.send_message(msg.chat_id, "*⇜ تم اضافة جواب، ارسل جواب آخر او `تم`*", msg.message_id)
            return True
        return False

    async def _store_payload(self, trigger: str, msg: IncomingMessage, global_reply: bool) -> None:
        clean_text = (msg.effective_text or "").replace('"', "").replace("`", "").replace("*", "")
        base = "Zelzal:Add:Rd:Sudo:" if global_reply else "Zelzal:Add:Rd:Manager:"
        suffix = "" if global_reply else str(msg.chat_id)
        if msg.content_type == "text":
            await self.store.set(self.store.key(base, "Text", trigger, suffix), clean_text)
            return
        kind_map = {
            "photo": "Photo",
            "video": "Video",
            "animation": "Gif",
            "document": "File",
            "audio": "Audio",
            "voice": "Vico",
            "sticker": "Stekrs",
            "video_note": "video_note",
        }
        redis_kind = kind_map.get(msg.content_type)
        if redis_kind and msg.file_id:
            await self.store.set(self.store.key(base, redis_kind, trigger, suffix), msg.file_id)
            if msg.caption:
                await self.store.set(self.store.key("Zelzal:Add:Rd:caption:", redis_kind.lower(), msg.file_id, suffix), msg.caption)

    async def _get_reply(self, trigger: str, chat_id: int, global_reply: bool) -> StoredReply | None:
        base = "Zelzal:Add:Rd:Sudo:" if global_reply else "Zelzal:Add:Rd:Manager:"
        suffix = "" if global_reply else str(chat_id)
        for redis_kind, send_kind in MEDIA_ORDER:
            value = await self.store.get(self.store.key(base, redis_kind, trigger, suffix))
            if value:
                caption = await self.store.get(self.store.key("Zelzal:Add:Rd:caption:", redis_kind.lower(), value, suffix)) or ""
                return StoredReply(send_kind, value, caption)
        return None

    async def _send_reply(self, msg: IncomingMessage, ctx: PermissionContext, reply: StoredReply) -> None:
        if reply.kind == "text":
            text = reply.value
            text = text.replace("{اليوزر}", msg.username or "لا يوجد")
            text = text.replace("{الاسم}", msg.first_name or str(msg.user_id))
            text = text.replace("{الايدي}", str(msg.user_id))
            text = text.replace("{الرتبه}", ctx.role_name)
            text = text.replace("{الرسائل}", await self.store.get(self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":", msg.user_id)) or "0")
            await self.bot.send_message(msg.chat_id, text if "]" in text else f"[{text}]", msg.message_id)
        else:
            await self.bot.send_media(msg.chat_id, reply.kind, reply.value, reply.caption, msg.message_id)

    async def _list_replies(self, msg: IncomingMessage, global_reply: bool) -> None:
        list_key = self.store.key("Zelzal:List:Rd:Sudo") if global_reply else self.store.key("Zelzal:List:Manager", msg.chat_id)
        values = sorted(await self.store.smembers(list_key))
        title = "قائمة الردود العامة" if global_reply else "قائمة الردود"
        if not values:
            await self.bot.send_message(msg.chat_id, "*⇜ مافي ردود مضافة !*", msg.message_id)
            return
        lines = [f"*⇜ {title} *", "ٴ*⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆*"]
        lines.extend(f"{i} - ( {value} )" for i, value in enumerate(values, 1))
        await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)

    async def _clear_replies(self, msg: IncomingMessage, global_reply: bool) -> None:
        list_key = self.store.key("Zelzal:List:Rd:Sudo") if global_reply else self.store.key("Zelzal:List:Manager", msg.chat_id)
        values = await self.store.smembers(list_key)
        for trigger in values:
            await self._delete_reply_keys(trigger, msg.chat_id, global_reply)
        await self.store.delete(list_key)
        await self.bot.send_message(msg.chat_id, "*⇜ ابشر مسحت الردود*", msg.message_id)

    async def _delete_reply_keys(self, trigger: str, chat_id: int, global_reply: bool) -> None:
        base = "Zelzal:Add:Rd:Sudo:" if global_reply else "Zelzal:Add:Rd:Manager:"
        suffix = "" if global_reply else str(chat_id)
        keys = [self.store.key(base, redis_kind, trigger, suffix) for redis_kind, _ in MEDIA_ORDER]
        await self.store.delete(*keys)
