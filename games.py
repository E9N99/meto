from __future__ import annotations

import random

from .models import IncomingMessage
from .permissions import PermissionContext
from .redis_store import RedisStore
from .telegram import TelegramBot


SMILES = ["😀", "😂", "😍", "😎", "😭", "😡", "🤔", "😴", "🥶", "🤯"]
RIDDLES = [
    ("شيء كلما أخذت منه كبر؟", "الحفرة"),
    ("يمشي بلا رجلين ولا يدخل إلا بالأذنين؟", "الصوت"),
    ("له أوراق وليس نباتاً؟", "الكتاب"),
]
WORDS = ["زلزال", "بايثون", "حماية", "مجموعة", "بوت", "العاب"]
QUESTIONS = [
    ("عاصمة العراق؟", "بغداد"),
    ("ناتج 5 + 7؟", "12"),
    ("اكمل: خير الكلام ما قل و...", "دل"),
]
WOULD_YOU = [
    "لو خيروك بين السفر للماضي أو المستقبل؟",
    "لو خيروك بين المال أو راحة البال؟",
    "لو خيروك بين الصداقة أو الحب؟",
]
CONFESSIONS = [
    "صارحنا: أكثر شيء تخاف منه؟",
    "صارحنا: شخص تفتقده؟",
    "صارحنا: قرار ندمت عليه؟",
]
FLAGS = [("🇮🇶", "العراق"), ("🇸🇦", "السعودية"), ("🇪🇬", "مصر"), ("🇯🇴", "الاردن")]


class GamesService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        if await self.store.get(self.store.key("Zelzal:Disabled:الالعاب:", msg.chat_id)) and not ctx.manager:
            return False
        if await self._answer_active_game(msg):
            return True
        text = msg.effective_text or ""
        if text in {"العاب", "الالعاب"}:
            await self.bot.send_message(msg.chat_id, "⇜ الالعاب:\n`سمايلات` - `لغز` - `نقاطي` - `مسح نقاطي` - `توب الالعاب`", msg.message_id)
            return True
        if text in {"سمايلات", "لعبة السمايلات"}:
            answer = random.choice(SMILES)
            await self.store.setex(self.store.key("Zelzal:Game:Smile", msg.chat_id), 300, answer)
            await self.bot.send_message(msg.chat_id, f"⇜ ارسل نفس السمايل:\n\n{answer}", msg.message_id)
            return True
        if text in {"لغز", "الغاز"}:
            question, answer = random.choice(RIDDLES)
            await self.store.setex(self.store.key("Zelzal:Game:Riddles", msg.chat_id), 300, answer)
            await self.bot.send_message(msg.chat_id, f"⇜ {question}", msg.message_id)
            return True
        if text in {"اسئلة", "سؤال", "كت"}:
            question, answer = random.choice(QUESTIONS)
            await self.store.setex(self.store.key("Zelzal:Game:Question", msg.chat_id), 300, answer)
            await self.bot.send_message(msg.chat_id, f"⇜ {question}", msg.message_id)
            return True
        if text in {"ترتيب", "رتب", "رتب الحروف"}:
            word = random.choice(WORDS)
            shuffled = " ".join(random.sample(list(word), len(word)))
            await self.store.setex(self.store.key("Zelzal:Game:Arrange", msg.chat_id), 300, word)
            await self.bot.send_message(msg.chat_id, f"⇜ رتب الحروف:\n{shuffled}", msg.message_id)
            return True
        if text in {"اسرع", "سرعة", "تحدي السرعة"}:
            word = random.choice(WORDS)
            await self.store.setex(self.store.key("Zelzal:Game:Speed", msg.chat_id), 120, word)
            await self.bot.send_message(msg.chat_id, f"⇜ اسرع واحد يكتب:\n`{word}`", msg.message_id)
            return True
        if text in {"لو خيروك", "لوخيروك"}:
            await self.bot.send_message(msg.chat_id, random.choice(WOULD_YOU), msg.message_id)
            return True
        if text in {"صراحه", "صراحة"}:
            await self.bot.send_message(msg.chat_id, random.choice(CONFESSIONS), msg.message_id)
            return True
        if text in {"اعلام", "علم"}:
            flag, country = random.choice(FLAGS)
            await self.store.setex(self.store.key("Zelzal:Game:Flags", msg.chat_id), 300, country)
            await self.bot.send_message(msg.chat_id, f"⇜ ما اسم هذه الدولة؟\n{flag}", msg.message_id)
            return True
        if text == "نقاطي":
            points = await self.store.get(self.store.key("Zelzal:Num:Add:Games", msg.chat_id, msg.user_id)) or 0
            await self.bot.send_message(msg.chat_id, f"⇜ نقاطك : {points}", msg.message_id)
            return True
        if text == "مسح نقاطي":
            await self.store.delete(self.store.key("Zelzal:Num:Add:Games", msg.chat_id, msg.user_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم مسح نقاطك", msg.message_id)
            return True
        if text in {"توب الالعاب", "توب العاب"}:
            await self._top(msg)
            return True
        return False

    async def _answer_active_game(self, msg: IncomingMessage) -> bool:
        text = msg.effective_text
        if not text:
            return False
        for key in ("Zelzal:Game:Smile", "Zelzal:Game:Monotonous", "Zelzal:Game:alam", "Zelzal:Game:ausm", "Zelzal:Game:Riddles", "Zelzal:Game:Question", "Zelzal:Game:Arrange", "Zelzal:Game:Speed", "Zelzal:Game:Flags", "Zelzal:Game:Meaningof", "Zelzal:Game:Reflection"):
            answer = await self.store.get(self.store.key(key, msg.chat_id))
            if answer and text.strip() == answer.strip():
                await self.store.delete(self.store.key(key, msg.chat_id))
                points = await self.store.incrby(self.store.key("Zelzal:Num:Add:Games", msg.chat_id, msg.user_id), 1)
                await self.store.sadd(self.store.key("Zelzal:Games:Players", msg.chat_id), msg.user_id)
                await self.bot.send_message(msg.chat_id, f"\n⇜ كفو اجابتك صح \n⇜ تم اضافة لك نقطة\n⇜ نقاطك الان : {points} \n✓", msg.message_id)
                return True
        return False

    async def _top(self, msg: IncomingMessage) -> None:
        players = await self.store.smembers(self.store.key("Zelzal:Games:Players", msg.chat_id))
        rows = []
        for player in players:
            points = int(await self.store.get(self.store.key("Zelzal:Num:Add:Games", msg.chat_id, player)) or 0)
            rows.append((points, player))
        rows.sort(reverse=True)
        if not rows:
            await self.bot.send_message(msg.chat_id, "⇜ لا توجد نقاط العاب", msg.message_id)
            return
        text = "⇜ ترتيب نقاط الالعاب\n" + "\n".join(f"{i} - `{user}` : {points}" for i, (points, user) in enumerate(rows[:10], 1))
        await self.bot.send_message(msg.chat_id, text, msg.message_id)
