from __future__ import annotations

from .models import IncomingMessage
from .permissions import PermissionContext
from .redis_store import RedisStore
from .telegram import TelegramBot


ARABIC_BASE = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
ARABIC_STYLES = [
    {ord(ch): ch + "ہ" for ch in ARABIC_BASE},
    {ord(ch): ch + "͠" for ch in ARABIC_BASE},
]

ENGLISH_FANCY = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅",
)


class ZakhrafaService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if text in {"زخرفه", "زخرفة", "زخرفه اونلاين", "زخرفة اونلاين"}:
            await self.store.setex(self.store.key("Zelzal:Zakhrafa:Wait", msg.user_id, ":", msg.chat_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل الاسم او النص لزخرفته", msg.message_id)
            return True
        if text.startswith(("زخرفه ", "زخرفة ")):
            raw = text.split(" ", 1)[1].strip()
            await self._send_styles(msg, raw)
            return True
        if await self.store.get(self.store.key("Zelzal:Zakhrafa:Wait", msg.user_id, ":", msg.chat_id)):
            await self.store.delete(self.store.key("Zelzal:Zakhrafa:Wait", msg.user_id, ":", msg.chat_id))
            await self._send_styles(msg, text)
            return True
        return False

    async def _send_styles(self, msg: IncomingMessage, text: str) -> None:
        if not text:
            await self.bot.send_message(msg.chat_id, "⇜ ارسل نص صالح", msg.message_id)
            return
        styles = [
            text.translate(ARABIC_STYLES[0]),
            text.translate(ARABIC_STYLES[1]),
            text.translate(ENGLISH_FANCY),
            f"『 {text} 』",
            f"𓆩 {text} 𓆪",
            f"•.¸¸.• {text} •.¸¸.•",
        ]
        unique = []
        for style in styles:
            if style not in unique:
                unique.append(style)
        await self.bot.send_message(msg.chat_id, "⇜ زخارف جاهزة:\n\n" + "\n".join(f"{i} - `{value}`" for i, value in enumerate(unique, 1)), msg.message_id)
