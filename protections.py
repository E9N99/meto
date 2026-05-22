from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Awaitable, Callable

from .models import IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import deny


Detector = Callable[[IncomingMessage], bool]


@dataclass(slots=True)
class LockSpec:
    label: str
    key: str
    aliases: tuple[str, ...]
    content_types: tuple[str, ...] = ()
    detector: Detector | None = None
    boolean: bool = False


LINK_RE = re.compile(r"(?:https?://|t\.me/|telegram\.(?:me|dog)/|www\.|\.com|\.org|\.net|\.tk|\.ml)", re.I)


def text_has(pattern: re.Pattern[str]) -> Detector:
    return lambda msg: bool(msg.effective_text and pattern.search(msg.effective_text))


LOCKS: list[LockSpec] = [
    LockSpec("الروابط", "Zelzal:Lock:Link", ("الروابط", "الرابط", "لينك"), detector=text_has(LINK_RE)),
    LockSpec("المعرف", "Zelzal:Lock:User:Name", ("المعرف", "المعرفات", "اليوزر"), detector=text_has(re.compile(r"@[\w_]+"))),
    LockSpec("الهاشتاق", "Zelzal:Lock:hashtak", ("الهاشتاق", "الهاشتاك", "الهاشتاغ", "التاك"), detector=text_has(re.compile(r"#[\w_]+"))),
    LockSpec("الاوامر", "Zelzal:Lock:Cmd", ("الاوامر", "الشارحه", "السلاش"), detector=text_has(re.compile(r"^/[\w_]+"))),
    LockSpec("الصور", "Zelzal:Lock:Photo", ("الصور", "الصوره"), content_types=("photo",)),
    LockSpec("الفيديو", "Zelzal:Lock:Video", ("الفيديو", "الفيديوهات"), content_types=("video",)),
    LockSpec("المتحركات", "Zelzal:Lock:Animation", ("المتحركات", "المتحركه", "الجيف"), content_types=("animation",)),
    LockSpec("الملصقات", "Zelzal:Lock:Sticker", ("الملصقات", "الملصق", "الاستكر"), content_types=("sticker",)),
    LockSpec("البصمات", "Zelzal:Lock:vico", ("البصمات", "البصمه", "الصوتيات"), content_types=("voice", "video_note")),
    LockSpec("الصوت", "Zelzal:Lock:Audio", ("الصوت", "الاغاني", "الاغاني"), content_types=("audio",)),
    LockSpec("الملفات", "Zelzal:Lock:Document", ("الملفات", "الملف"), content_types=("document",)),
    LockSpec("الجهات", "Zelzal:Lock:Contact", ("الجهات", "جهات الاتصال"), content_types=("contact",)),
    LockSpec("التوجيه", "Zelzal:Lock:forward", ("التوجيه", "الفوروارد"), detector=lambda msg: bool(msg.raw.get("forward_origin") or msg.raw.get("forward_from"))),
    LockSpec("الكيبورد", "Zelzal:Lock:Keyboard", ("الكيبورد", "الازرار"), detector=lambda msg: bool(msg.raw.get("reply_markup"))),
    LockSpec("الماركداون", "Zelzal:Lock:Markdaun", ("الماركداون", "الماركدون"), detector=lambda msg: bool(msg.raw.get("entities") or msg.raw.get("caption_entities"))),
    LockSpec("السبام", "Zelzal:Lock:Spam", ("السبام", "التكرار"), detector=lambda msg: bool(msg.effective_text and len(msg.effective_text) > 500)),
    LockSpec("الانلاين", "Zelzal:Lock:Inlen", ("الانلاين", "الاينلاين"), detector=lambda msg: bool(msg.raw.get("via_bot"))),
    LockSpec("القنوات", "Zelzal:Lock:SenderChat", ("القنوات", "الحسابات الوهمية"), detector=lambda msg: bool(msg.raw.get("sender_chat")), boolean=True),
    LockSpec("الخدمات", "Zelzal:Lock:tagservr", ("الخدمات", "الاشعارات"), content_types=("new_chat_members", "left_chat_member", "pinned_message"), boolean=True),
    LockSpec("الدردشه", "Zelzal:Lock:text", ("الدردشه", "الشات", "الكتابه"), detector=lambda msg: bool(msg.effective_text), boolean=True),
    LockSpec("الانكليزي", "Zelzal:Lock:english", ("الانكليزي", "الانجليزي"), detector=text_has(re.compile(r"[A-Za-z]")), boolean=True),
    LockSpec("العربيه", "Zelzal:Lock:arabic", ("العربيه", "العربية", "العربي"), detector=text_has(re.compile(r"[\u0600-\u06ff]")), boolean=True),
    LockSpec("البوتات", "Zelzal:Lock:Bot:kick", ("البوتات", "البوت"), detector=lambda msg: any(user.get("is_bot") for user in msg.new_chat_members), boolean=False),
    LockSpec("الدخول بالرابط", "Zelzal:Lock:Join", ("الدخول بالرابط", "الدخول", "الاضافه"), content_types=("new_chat_members",), boolean=False),
    LockSpec("التعديل", "Zelzal:Lock:Edit", ("التعديل", "تعديل الرسائل"), detector=lambda msg: bool(msg.raw.get("edit_date")), boolean=False),
    LockSpec("المسح", "Zelzal:Lock:Delete", ("المسح", "حذف الرسائل"), boolean=True),
]

MODE_ALIASES = {
    "": "del",
    "بالحذف": "del",
    "حذف": "del",
    "بالتقييد": "ked",
    "تقييد": "ked",
    "بالكتم": "ktm",
    "كتم": "ktm",
    "بالطرد": "kick",
    "طرد": "kick",
}


class ProtectionService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle_command(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if await self._bad_words_command(msg, ctx, text):
            return True
        if await self._spam_settings(msg, ctx, text):
            return True
        if not (text.startswith("قفل ") or text.startswith("فتح ")):
            return False
        if not ctx.manager:
            await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
            return True
        action = "lock" if text.startswith("قفل ") else "unlock"
        rest = text.split(" ", 1)[1].strip()
        mode = ""
        for alias in sorted(MODE_ALIASES, key=len, reverse=True):
            if alias and rest.endswith(" " + alias):
                rest = rest[: -len(alias)].strip()
                mode = alias
                break
        spec = self._find_spec(rest)
        if not spec:
            return False
        key = self.store.key(spec.key, msg.chat_id)
        if action == "unlock":
            await self.store.delete(key)
            await self.bot.send_message(msg.chat_id, f"⇜ تم فتح {spec.label}", msg.message_id)
            return True
        value = "true" if spec.boolean else MODE_ALIASES.get(mode, "del")
        await self.store.set(key, value)
        await self.bot.send_message(msg.chat_id, f"⇜ تم قفل {spec.label}", msg.message_id)
        return True

    async def apply(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        if ctx.distinguished or msg.chat_type == "private":
            return False
        if await self._bad_words_apply(msg):
            return True
        if await self._flood_apply(msg):
            return True
        for spec in LOCKS:
            if spec.content_types and msg.content_type not in spec.content_types:
                continue
            if spec.detector and not spec.detector(msg):
                continue
            action = await self.store.get(self.store.key(spec.key, msg.chat_id))
            if not action:
                continue
            await self._punish(msg, action, spec.label)
            return True
        return False

    async def _bad_words_command(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"اضف كلمه ممنوعه", "اضف كلمة ممنوعة", "منع كلمه", "منع كلمة"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:FilterWord", msg.user_id, ":", msg.chat_id), 300, "add")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل الكلمة الممنوعة", msg.message_id)
            return True
        if text in {"مسح كلمه ممنوعه", "مسح كلمة ممنوعة"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:FilterWord", msg.user_id, ":", msg.chat_id), 300, "del")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل الكلمة لحذفها", msg.message_id)
            return True
        state_key = self.store.key("Zelzal:Set:FilterWord", msg.user_id, ":", msg.chat_id)
        state = await self.store.get(state_key)
        if state and text:
            if state == "add":
                await self.store.sadd(self.store.key("Zelzal:Filter:Words", msg.chat_id), text)
                done = "⇜ تم اضافة الكلمة الممنوعة"
            else:
                await self.store.srem(self.store.key("Zelzal:Filter:Words", msg.chat_id), text)
                done = "⇜ تم حذف الكلمة الممنوعة"
            await self.store.delete(state_key)
            await self.bot.send_message(msg.chat_id, done, msg.message_id)
            return True
        if text in {"الكلمات الممنوعه", "الكلمات الممنوعة"}:
            words = sorted(await self.store.smembers(self.store.key("Zelzal:Filter:Words", msg.chat_id)))
            await self.bot.send_message(msg.chat_id, "\n".join(["⇜ الكلمات الممنوعة:"] + words) if words else "⇜ لا توجد كلمات ممنوعة", msg.message_id)
            return True
        if text in {"مسح الكلمات الممنوعه", "مسح الكلمات الممنوعة"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.delete(self.store.key("Zelzal:Filter:Words", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم مسح الكلمات الممنوعة", msg.message_id)
            return True
        return False

    async def _spam_settings(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        match = re.fullmatch(r"(?:ضع|تعيين) التكرار (\d+)", text)
        if not match:
            return False
        if not ctx.manager:
            await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
            return True
        limit = max(3, min(30, int(match.group(1))))
        await self.store.set(self.store.key("Zelzal:Spam:Limit", msg.chat_id), limit)
        await self.bot.send_message(msg.chat_id, f"⇜ تم تعيين حد التكرار إلى {limit}", msg.message_id)
        return True

    async def _bad_words_apply(self, msg: IncomingMessage) -> bool:
        text = msg.effective_text or ""
        if not text:
            return False
        words = await self.store.smembers(self.store.key("Zelzal:Filter:Words", msg.chat_id))
        if not words:
            return False
        lowered = text.casefold()
        if any(word.casefold() in lowered for word in words):
            await self._punish(msg, await self.store.get(self.store.key("Zelzal:Lock:FilterWords", msg.chat_id)) or "del", "الكلمات الممنوعة")
            return True
        return False

    async def _flood_apply(self, msg: IncomingMessage) -> bool:
        text = msg.effective_text
        if not text:
            return False
        limit = int(await self.store.get(self.store.key("Zelzal:Spam:Limit", msg.chat_id)) or 6)
        key = self.store.key("Zelzal:Spam:User", msg.chat_id, ":", msg.user_id, ":", text[:40])
        count = await self.store.incrby(key, 1)
        if count == 1:
            await self.store.setex(key, 10, count)
        if count >= limit and await self.store.get(self.store.key("Zelzal:Lock:Spam", msg.chat_id)):
            await self._punish(msg, await self.store.get(self.store.key("Zelzal:Lock:Spam", msg.chat_id)) or "del", "التكرار")
            return True
        return False

    async def _punish(self, msg: IncomingMessage, action: str, label: str) -> None:
        await self.store.sadd(self.store.key("Zelzal:Protection:Logs", msg.chat_id), f"{int(time.time())}:{msg.user_id}:{label}:{action}")
        try:
            await self.bot.delete_message(msg.chat_id, msg.message_id)
        except Exception:
            pass
        if action == "ked":
            await self.bot.restrict_member(msg.chat_id, msg.user_id, until_date=int(time.time()) + 86400)
        elif action == "ktm":
            await self.store.sadd(self.store.key("Zelzal:SilentGroup:Group", msg.chat_id), msg.user_id)
            await self.bot.restrict_member(msg.chat_id, msg.user_id)
        elif action == "kick":
            await self.bot.ban_member(msg.chat_id, msg.user_id)
            await self.bot.unban_member(msg.chat_id, msg.user_id)

    def _find_spec(self, name: str) -> LockSpec | None:
        normalized = name.strip()
        for spec in LOCKS:
            if normalized == spec.label or normalized in spec.aliases:
                return spec
        return None
