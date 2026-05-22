from __future__ import annotations

import random
import re
from typing import Any

from .models import CallbackQuery, IncomingMessage
from .permissions import PermissionContext
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import coin, ctime, format_money, mention


def inline_keyboard(rows: list[list[tuple[str, str]]]) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": callback_data} for text, callback_data in row]
            for row in rows
        ]
    }


def channel_keyboard(channel: str) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "˹𓌗 قنـاة البـوت 𓌗.", "url": f"https://t.me/{channel.lstrip('@')}"}]]}


COUNTRIES = {
    "syria": "🇸🇾",
    "sudia": "🇸🇦",
    "iraqq": "🇮🇶",
    "yemen": "🇾🇪",
    "tunsia": "🇹🇳",
    "qatar": "🇶🇦",
    "sudan": "🇸🇩",
    "plastin": "🇵🇸",
    "moroco": "🇲🇦",
    "oman": "🇴🇲",
    "libya": "🇱🇾",
    "kuwit": "🇰🇼",
    "lebanon": "🇱🇧",
    "jordan": "🇯🇴",
    "bahren": "🇧🇭",
    "egypt": "🇪🇬",
    "algeria": "🇩🇿",
    "emarite": "🇦🇪",
}


class BankService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if await self._admin_bank_commands(msg, ctx, text):
            return True
        if await self.store.get(self.store.key("Zelzal:Disabled:البنك:", msg.chat_id)) and not ctx.manager:
            return False
        if await self._finish_transfer(msg):
            return True
        if text in {"بنك", "البنك"}:
            await self.bot.send_message(msg.chat_id, self._help_text(), msg.message_id)
            return True
        if text in {"انشاء حساب بنكي", "انشاء حساب البنكي", "انشاء الحساب بنكي", "انشاء الحساب البنكي", "انشاء حساب", "فتح حساب بنكي"}:
            await self._create_account(msg)
            return True
        if text in {"مسح حساب بنكي", "مسح حساب البنكي", "مسح الحساب بنكي", "مسح الحساب البنكي", "مسح حسابي البنكي", "مسح حسابي بنكي", "مسح حسابي"}:
            await self._delete_account(msg)
            return True
        if text in {"فلوسي", "فلوس", "كم فلوسي"} and not msg.reply_to_message_id:
            await self._balance(msg)
            return True
        if text in {"حسابي", "حسابي البنكي", "رقم حسابي"}:
            await self._account(msg)
            return True
        if text in {"راتب", "راتبي"}:
            await self._salary(msg)
            return True
        if text in {"هدية يومية", "المكافأة اليومية", "مكافأة يومية"}:
            await self._daily_reward(msg)
            return True
        if text in {"بخشيش", "بقشيش"}:
            await self._tip(msg)
            return True
        if text.startswith("سرقه ") or text.startswith("سرقة "):
            await self._steal(msg, coin(text.split(" ", 1)[1]))
            return True
        if text.startswith("رهان "):
            await self._gamble(msg, coin(text.removeprefix("رهان ")))
            return True
        if text.startswith("حظ "):
            await self._luck(msg, coin(text.removeprefix("حظ ")))
            return True
        if text in {"مستواي", "مستوى البنك", "مستوى حسابي"}:
            await self._level(msg)
            return True
        if text in {"متجر", "المتجر"}:
            await self._shop(msg)
            return True
        if text.startswith("شراء "):
            await self._buy(msg, text.removeprefix("شراء ").strip())
            return True
        if text in {"ممتلكاتي", "مقتنياتي"}:
            await self._inventory(msg)
            return True
        if text == "تحويل":
            await self.bot.send_message(msg.chat_id, "⇜ استعمل الامر كذا :\n\n⇜ `تحويل` المبلغ", msg.message_id)
            return True
        if text.startswith("تحويل "):
            await self._start_transfer(msg, coin(text.removeprefix("تحويل ")))
            return True
        if text == "استثمار":
            await self.bot.send_message(msg.chat_id, "⇜ استعمل الامر كذا :\n\n⇜ `استثمار` المبلغ", msg.message_id)
            return True
        if text == "استثمار فلوسي":
            balance = await self._money(msg.user_id)
            await self._invest(msg, balance)
            return True
        if text.startswith("استثمار "):
            await self._invest(msg, coin(text.removeprefix("استثمار ")))
            return True
        if text in {"اغنياء", "الاغنياء", "ترتيب الاغنياء", "توب الفلوس"}:
            await self._rich_list(msg)
            return True
        return False

    async def _admin_bank_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        target_id = msg.reply_to_user_id
        if text.startswith(("حظر بنك", "منع بنك")):
            if not ctx.manager:
                return False
            target_id = target_id or self._id_from_tail(text)
            if not target_id:
                await self.bot.send_message(msg.chat_id, "⇜ استخدم الامر بالرد او مع الايدي", msg.message_id)
                return True
            await self.store.set(self.store.key("bandid", target_id), target_id)
            await self.bot.send_message(msg.chat_id, "⇜ تم منع العضو من البنك", msg.message_id)
            return True
        if text.startswith(("الغاء حظر بنك", "الغاء منع بنك")):
            if not ctx.manager:
                return False
            target_id = target_id or self._id_from_tail(text)
            if not target_id:
                await self.bot.send_message(msg.chat_id, "⇜ استخدم الامر بالرد او مع الايدي", msg.message_id)
                return True
            await self.store.delete(self.store.key("bandid", target_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم الغاء منع العضو من البنك", msg.message_id)
            return True
        if text.startswith("اضف فلوس "):
            if not ctx.controller_bot:
                return False
            amount = coin(text.removeprefix("اضف فلوس "))
            target_id = target_id or msg.user_id
            await self._set_money(target_id, await self._money(target_id) + amount)
            await self.store.sadd(self.store.key("booob"), target_id)
            await self.bot.send_message(msg.chat_id, f"⇜ تم اضافة {format_money(amount)} ﷼", msg.message_id)
            return True
        if text.startswith("خصم فلوس "):
            if not ctx.controller_bot:
                return False
            amount = coin(text.removeprefix("خصم فلوس "))
            target_id = target_id or msg.user_id
            await self._set_money(target_id, max(0, await self._money(target_id) - amount))
            await self.bot.send_message(msg.chat_id, f"⇜ تم خصم {format_money(amount)} ﷼", msg.message_id)
            return True
        return False

    def _id_from_tail(self, text: str) -> int | None:
        match = re.search(r"(-?\d+)$", text)
        return int(match.group(1)) if match else None

    async def handle_callback(self, callback: CallbackQuery) -> bool:
        user_id, action = self._split_callback(callback.data)
        if not user_id or callback.user_id != user_id:
            return False
        if action in {"master", "visaa", "express"}:
            card_data = {
                "master": ("ماستر", 5_000_000_000_000_000, 5_999_999_999_999_999),
                "visaa": ("فيزا", 4_000_000_000_000_000, 4_999_999_999_999_999),
                "express": ("اكسبرس", 6_000_000_000_000_000, 6_999_999_999_999_999),
            }[action]
            await self._create_card_account(callback, *card_data)
            return True
        if action in {"msalm", "shrer"}:
            await self._choose_personality(callback, action)
            return True
        if action in COUNTRIES:
            await self._choose_country(callback, COUNTRIES[action])
            return True
        return False

    async def account_exists(self, user_id: int) -> bool:
        return await self.store.sismember(self.store.key("booob"), user_id)

    async def _money(self, user_id: int) -> int:
        return int(float(await self.store.get(self.store.key("boob", user_id)) or 0))

    async def _set_money(self, user_id: int, value: int) -> None:
        await self.store.set(self.store.key("boob", user_id), int(value))

    async def _create_account(self, msg: IncomingMessage) -> None:
        if await self.store.get(self.store.key("bandid", msg.user_id)) == str(msg.user_id):
            await self.bot.send_message(msg.chat_id, "⇜ حسابك محظور من لعبة البنك", msg.message_id)
            return
        if await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "⇜ لديك حساب بنكي مسبقاً\n\n⇜ لعرض معلومات حسابك اكتب\n⇠ `حسابي`", msg.message_id)
            return
        await self.bot.send_message(
            msg.chat_id,
            "⇜ عشان تسوي حساب اختار نوع بطاقتك",
            msg.message_id,
            reply_markup=inline_keyboard(
                [[("ماستر", f"{msg.user_id}/master"), ("فيزا", f"{msg.user_id}/visaa"), ("اكسبرس", f"{msg.user_id}/express")]]
            ),
        )

    async def _create_card_account(self, callback: CallbackQuery, card: str, start: int, end: int) -> None:
        if callback.chat_id is None or callback.message_id is None:
            return
        if await self.account_exists(callback.user_id):
            await self.bot.answer_callback_query(callback.id, "⇜ لديك حساب بنكي مسبقاً", True)
            return
        account_no = str(random.randint(start, end))
        while await self.store.get(self.store.key("boballcc", account_no)):
            account_no = str(random.randint(start, end))
        first_name = str((callback.raw.get("from") or {}).get("first_name") or " لا يوجد")
        await self.store.sadd(self.store.key("booob"), callback.user_id)
        await self.store.set(self.store.key("bobna", callback.user_id), first_name)
        await self.store.set(self.store.key("boob", callback.user_id), 50)
        await self.store.set(self.store.key("boobb", callback.user_id), account_no)
        await self.store.set(self.store.key("bbobb", callback.user_id), card)
        await self.store.set(self.store.key("boballname", account_no), first_name)
        await self.store.set(self.store.key("boballbalc", account_no), 50)
        await self.store.set(self.store.key("boballcc", account_no), account_no)
        await self.store.set(self.store.key("boballban", account_no), card)
        await self.store.set(self.store.key("boballid", account_no), callback.user_id)
        channel = await self.store.get(self.store.key("chsource")) or "Zelzal"
        await self.bot.edit_message_text(
            callback.chat_id,
            callback.message_id,
            "⇜ اختر شخصيتك في اللعبة",
            reply_markup={
                "inline_keyboard": [
                    [
                        {"text": "شخصية طيبة 😇", "callback_data": f"{callback.user_id}/msalm"},
                        {"text": "شخصية شريرة 😈", "callback_data": f"{callback.user_id}/shrer"},
                    ],
                    [{"text": "˹𓌗 قنـاة البـوت 𓌗.", "url": f"https://t.me/{channel.lstrip('@')}"}],
                ]
            },
        )
        await self.bot.answer_callback_query(callback.id, "⇜ تم استلام الامر", False)

    async def _choose_personality(self, callback: CallbackQuery, action: str) -> None:
        if callback.chat_id is None or callback.message_id is None:
            return
        personality = "طيبة" if action == "msalm" else "شريرة"
        await self.store.set(self.store.key("shkse", callback.user_id), personality)
        channel = await self.store.get(self.store.key("chsource")) or "Zelzal"
        rows: list[list[dict[str, str]]] = [
            [{"text": "🇸🇾", "callback_data": f"{callback.user_id}/syria"}, {"text": "🇸🇦", "callback_data": f"{callback.user_id}/sudia"}, {"text": "🇮🇶", "callback_data": f"{callback.user_id}/iraqq"}],
            [{"text": "🇾🇪", "callback_data": f"{callback.user_id}/yemen"}, {"text": "🇹🇳", "callback_data": f"{callback.user_id}/tunsia"}, {"text": "🇶🇦", "callback_data": f"{callback.user_id}/qatar"}],
            [{"text": "🇸🇩", "callback_data": f"{callback.user_id}/sudan"}, {"text": "🇵🇸", "callback_data": f"{callback.user_id}/plastin"}, {"text": "🇲🇦", "callback_data": f"{callback.user_id}/moroco"}],
            [{"text": "🇴🇲", "callback_data": f"{callback.user_id}/oman"}, {"text": "🇱🇾", "callback_data": f"{callback.user_id}/libya"}, {"text": "🇰🇼", "callback_data": f"{callback.user_id}/kuwit"}],
            [{"text": "🇱🇧", "callback_data": f"{callback.user_id}/lebanon"}, {"text": "🇯🇴", "callback_data": f"{callback.user_id}/jordan"}, {"text": "🇧🇭", "callback_data": f"{callback.user_id}/bahren"}],
            [{"text": "🇪🇬", "callback_data": f"{callback.user_id}/egypt"}, {"text": "🇩🇿", "callback_data": f"{callback.user_id}/algeria"}, {"text": "🇦🇪", "callback_data": f"{callback.user_id}/emarite"}],
        ]
        if action == "msalm":
            rows.append([{"text": "˹𓌗 قنـاة البـوت 𓌗.", "url": f"https://t.me/{channel.lstrip('@')}"}])
            text = "⇜ اختر دولتك"
        else:
            text = "⇜ اختر دولتك "
        await self.bot.edit_message_text(callback.chat_id, callback.message_id, text, reply_markup={"inline_keyboard": rows})
        await self.bot.answer_callback_query(callback.id, "⇜ تم استلام الامر", False)

    async def _choose_country(self, callback: CallbackQuery, flag: str) -> None:
        if callback.chat_id is None or callback.message_id is None:
            return
        await self.store.set(self.store.key("doltebank", callback.user_id), flag)
        account_no = await self.store.get(self.store.key("boobb", callback.user_id)) or "لا يوجد"
        card = await self.store.get(self.store.key("bbobb", callback.user_id)) or "لا يوجد"
        personality = await self.store.get(self.store.key("shkse", callback.user_id))
        personality_text = "طيبة 😇" if personality == "طيبة" else "شريرة 😈"
        text = (
            "⇜ وسوينا لك حساب في بنك الاهلي\n"
            "⇜ وشحنالك ٥٠ ﷼ 💸 هديه\n\n"
            f"⇜ رقم حسابك ↤ ❲ `{account_no}` ❳\n"
            f"⇜ نوع البطاقة ↤ ❲ {card} ❳\n"
            "⇜ فلوسك ↤ ❲ 50 ﷼ 💸 ❳\n"
            f"⇜ شخصيتك ↤ {personality_text}\n"
            f"⇜ دولتك ↤ ❲ {flag} ❳"
        )
        channel = await self.store.get(self.store.key("chsource")) or "Zelzal"
        await self.bot.edit_message_text(callback.chat_id, callback.message_id, text, reply_markup=channel_keyboard(channel))
        await self.bot.answer_callback_query(callback.id, "⇜ تم استلام الامر", False)

    async def _delete_account(self, msg: IncomingMessage) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        account_no = await self.store.get(self.store.key("boobb", msg.user_id))
        delete_keys = [
            "boob", "boobb", "bbobb", "rrfff", "roog1", "rooga1", "rahr1", "rahrr1",
            "tabbroat", "shkse", "doltebank", "ratbinc", "ratbtrans",
        ]
        await self.store.srem(self.store.key("booob"), msg.user_id)
        await self.store.srem(self.store.key("taza"), msg.user_id)
        await self.store.srem(self.store.key("rrfffid"), msg.user_id)
        await self.store.delete(*(self.store.key(k, msg.user_id) for k in delete_keys))
        if account_no:
            await self.store.delete(self.store.key("boballcc", account_no), self.store.key("boballid", account_no), self.store.key("boballban", account_no))
        await self.bot.send_message(msg.chat_id, "⇜ مسحت حسابك البنكي 🏦", msg.message_id)

    async def _balance(self, msg: IncomingMessage) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        await self.bot.send_message(msg.chat_id, f"⇜ فلوسك ↤ ❲ {format_money(await self._money(msg.user_id))} ﷼ 💵 ❳", msg.message_id)

    async def _account(self, msg: IncomingMessage) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        account_no = await self.store.get(self.store.key("boobb", msg.user_id)) or "لا يوجد"
        card = await self.store.get(self.store.key("bbobb", msg.user_id)) or "لا يوجد"
        country = await self.store.get(self.store.key("doltebank", msg.user_id)) or "غير محدد"
        balance = format_money(await self._money(msg.user_id))
        await self.bot.send_message(
            msg.chat_id,
            f"⇜ الاسم ↤ {mention(msg.user_id, msg.first_name)}\n⇜ الحساب ↤ `{account_no}`\n⇜ بنك ↤ ❲ الاهلي ❳\n⇜ نوع ↤ ❲ {card} ❳\n⇜ الرصيد ↤ ❲ {balance} ﷼ 💵 ❳\n⇜ دولتك ↤ ❲ {country} ❳",
            msg.message_id,
        )

    async def _salary(self, msg: IncomingMessage) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        ttl = await self.store.ttl(self.store.key("iiioo", msg.user_id))
        if ttl >= 60:
            await self.bot.send_message(msg.chat_id, f"⇜ راتبك بينزل بعد {ctime(ttl)} ", msg.message_id)
            return
        amount = 5000
        await self._set_money(msg.user_id, await self._money(msg.user_id) + amount)
        await self.store.setex(self.store.key("iiioo", msg.user_id), 600, "true")
        await self.store.incrby(self.store.key("ratbinc", msg.user_id), 1)
        await self.bot.send_message(msg.chat_id, f"⌯ اشعار ايداع {mention(msg.user_id, msg.first_name)}\n\n⇜ المبلغ : {amount} ﷼ 💵\n⇜ نوع العملية : اضافة راتب\n⇜ رصيدك الان : `{format_money(await self._money(msg.user_id))}` ﷼ 💵\n✓", msg.message_id)

    async def _tip(self, msg: IncomingMessage) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        ttl = await self.store.ttl(self.store.key("bakhshesh", msg.user_id))
        if ttl >= 60:
            await self.bot.send_message(msg.chat_id, f"*⇜ من شوي اخذت بخشيش استنى *{ctime(ttl)} ", msg.message_id)
            return
        amount = random.randint(50, 500)
        await self._set_money(msg.user_id, await self._money(msg.user_id) + amount)
        await self.store.setex(self.store.key("bakhshesh", msg.user_id), 600, "true")
        await self.bot.send_message(msg.chat_id, f"*⇜ تكرم وهي بخشيش *{amount} ﷼ 💵", msg.message_id)

    async def _daily_reward(self, msg: IncomingMessage) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        ttl = await self.store.ttl(self.store.key("Zelzal:Bank:Daily", msg.user_id))
        if ttl >= 60:
            await self.bot.send_message(msg.chat_id, f"⇜ اخذت مكافأتك اليومية، تعال بعد {ctime(ttl)}", msg.message_id)
            return
        amount = random.randint(1000, 10000)
        await self._set_money(msg.user_id, await self._money(msg.user_id) + amount)
        await self.store.setex(self.store.key("Zelzal:Bank:Daily", msg.user_id), 86400, "true")
        await self.bot.send_message(msg.chat_id, f"⇜ مكافأتك اليومية: {format_money(amount)} ﷼ 💵", msg.message_id)

    async def _steal(self, msg: IncomingMessage, amount: int) -> None:
        if not msg.reply_to_user_id:
            await self.bot.send_message(msg.chat_id, "⇜ استخدم السرقة بالرد على العضو", msg.message_id)
            return
        if amount < 100:
            await self.bot.send_message(msg.chat_id, "⇜ اقل مبلغ للسرقة 100", msg.message_id)
            return
        ttl = await self.store.ttl(self.store.key("Zelzal:Bank:Steal", msg.user_id))
        if ttl >= 60:
            await self.bot.send_message(msg.chat_id, f"⇜ لا تستطيع السرقة الآن، انتظر {ctime(ttl)}", msg.message_id)
            return
        victim_money = await self._money(msg.reply_to_user_id)
        if victim_money < amount:
            await self.bot.send_message(msg.chat_id, "⇜ الضحية ماعنده المبلغ", msg.message_id)
            return
        await self.store.setex(self.store.key("Zelzal:Bank:Steal", msg.user_id), 900, "true")
        if random.randint(1, 100) <= 45:
            await self._set_money(msg.reply_to_user_id, victim_money - amount)
            await self._set_money(msg.user_id, await self._money(msg.user_id) + amount)
            await self.bot.send_message(msg.chat_id, f"⇜ نجحت السرقة وربحت {format_money(amount)} ﷼", msg.message_id)
        else:
            fine = min(await self._money(msg.user_id), amount // 2)
            await self._set_money(msg.user_id, await self._money(msg.user_id) - fine)
            await self.bot.send_message(msg.chat_id, f"⇜ فشلت السرقة وانخصم منك {format_money(fine)} ﷼", msg.message_id)

    async def _shop(self, msg: IncomingMessage) -> None:
        await self.bot.send_message(msg.chat_id, "⇜ المتجر:\nسيارة - 50000\nبيت - 250000\nمزرعة - 750000\n\n⇜ للشراء: `شراء سيارة`", msg.message_id)

    async def _buy(self, msg: IncomingMessage, item: str) -> None:
        prices = {"سيارة": 50000, "بيت": 250000, "مزرعة": 750000}
        if item not in prices:
            await self.bot.send_message(msg.chat_id, "⇜ هذا الشيء غير موجود في المتجر", msg.message_id)
            return
        balance = await self._money(msg.user_id)
        if balance < prices[item]:
            await self.bot.send_message(msg.chat_id, "⇜ فلوسك ماتكفي", msg.message_id)
            return
        await self._set_money(msg.user_id, balance - prices[item])
        await self.store.sadd(self.store.key("Zelzal:Bank:Inventory", msg.user_id), item)
        await self.bot.send_message(msg.chat_id, f"⇜ تم شراء {item}", msg.message_id)

    async def _inventory(self, msg: IncomingMessage) -> None:
        items = sorted(await self.store.smembers(self.store.key("Zelzal:Bank:Inventory", msg.user_id)))
        await self.bot.send_message(msg.chat_id, "⇜ ممتلكاتك:\n" + ("\n".join(items) if items else "لا يوجد"), msg.message_id)

    async def _gamble(self, msg: IncomingMessage, amount: int) -> None:
        if amount < 100:
            await self.bot.send_message(msg.chat_id, "⇜ اقل رهان 100 ﷼", msg.message_id)
            return
        balance = await self._money(msg.user_id)
        if balance < amount:
            await self.bot.send_message(msg.chat_id, "⇜ فلوسك ماتكفي", msg.message_id)
            return
        if random.choice([True, False]):
            prize = amount
            await self._set_money(msg.user_id, balance + prize)
            await self.bot.send_message(msg.chat_id, f"⇜ فزت بالرهان وربحت {format_money(prize)} ﷼", msg.message_id)
        else:
            await self._set_money(msg.user_id, balance - amount)
            await self.bot.send_message(msg.chat_id, f"⇜ خسرت الرهان وانخصم {format_money(amount)} ﷼", msg.message_id)

    async def _luck(self, msg: IncomingMessage, amount: int) -> None:
        if amount < 100:
            await self.bot.send_message(msg.chat_id, "⇜ اقل مبلغ للحظ 100 ﷼", msg.message_id)
            return
        balance = await self._money(msg.user_id)
        if balance < amount:
            await self.bot.send_message(msg.chat_id, "⇜ فلوسك ماتكفي", msg.message_id)
            return
        multiplier = random.choice([0, 0, 1, 2, 3])
        await self._set_money(msg.user_id, balance - amount + amount * multiplier)
        if multiplier == 0:
            await self.bot.send_message(msg.chat_id, f"⇜ حظك سيء وخسرت {format_money(amount)} ﷼", msg.message_id)
        else:
            await self.bot.send_message(msg.chat_id, f"⇜ حظك ضرب وربحت x{multiplier}: {format_money(amount * multiplier)} ﷼", msg.message_id)

    async def _level(self, msg: IncomingMessage) -> None:
        balance = await self._money(msg.user_id)
        level = 1 + min(99, balance // 100_000)
        next_level = level * 100_000
        await self.store.set(self.store.key("Zelzal:Bank:Level", msg.user_id), level)
        await self.bot.send_message(msg.chat_id, f"⇜ مستوى حسابك البنكي: {level}\n⇜ رصيدك: {format_money(balance)} ﷼\n⇜ المستوى القادم عند: {format_money(next_level)} ﷼", msg.message_id)

    async def _start_transfer(self, msg: IncomingMessage, amount: int) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        ttl = await self.store.ttl(self.store.key("tanstime", msg.user_id))
        if ttl >= 60:
            await self.bot.send_message(msg.chat_id, f"⇜ مايمديك تحول فلوس الحين\n⇜ تعال بعد {ctime(ttl)} ", msg.message_id)
            return
        if amount < 100:
            await self.bot.send_message(msg.chat_id, "⇜ الحد الادنى المسموح به هو 100 ﷼ \n✓", msg.message_id)
            return
        if amount > await self._money(msg.user_id):
            await self.bot.send_message(msg.chat_id, "⇜ فلوسك ماتكفي\n✓", msg.message_id)
            return
        await self.store.set(self.store.key("transn", msg.user_id), amount)
        await self.store.setex(self.store.key("trans", msg.chat_id, ":", msg.user_id), 60, "true")
        await self.bot.send_message(msg.chat_id, "⇜ ارسل الحين رقم الحساب البنكي الي تبي تحول له\n\n– معاك دقيقة وحدة والغي طلب التحويل .\n✓", msg.message_id)

    async def _finish_transfer(self, msg: IncomingMessage) -> bool:
        if not await self.store.get(self.store.key("trans", msg.chat_id, ":", msg.user_id)):
            return False
        text = msg.effective_text or ""
        if not text.isdigit():
            await self._cancel_transfer(msg)
            await self.bot.send_message(msg.chat_id, "⇜ ارسل رقم حساب بنكي ", msg.message_id)
            return True
        own_account = await self.store.get(self.store.key("boobb", msg.user_id))
        if text == own_account:
            await self._cancel_transfer(msg)
            await self.bot.send_message(msg.chat_id, "⇜ مايمديك تحول لنفسك ", msg.message_id)
            return True
        target_id = await self.store.get(self.store.key("boballid", text))
        if not target_id:
            await self._cancel_transfer(msg)
            await self.bot.send_message(msg.chat_id, "⇜ مافيه حساب بنكي كذا", msg.message_id)
            return True
        amount = int(float(await self.store.get(self.store.key("transn", msg.user_id)) or 0))
        net = amount - (amount // 10)
        await self._set_money(msg.user_id, await self._money(msg.user_id) - amount)
        await self._set_money(int(target_id), await self._money(int(target_id)) + net)
        await self.store.setex(self.store.key("tanstime", msg.user_id), 1800, "true")
        await self._cancel_transfer(msg)
        await self.bot.send_message(msg.chat_id, f"⇜ حوالة صادرة من بنك الاهلي\n\n⇜ الحساب رقم ↤ `{own_account}`\n⇜ المستلم ↤ `{text}`\n⇜ خصمت 10% رسوم تحويل\n⇜ المبلغ ↤ {format_money(net)} ﷼ 💵", msg.message_id)
        try:
            await self.bot.send_message(int(target_id), f"⌯ حوالة واردة من بنك الاهلي\n\n⇜ المرسل ↤ `{own_account}`\n⇜ المبلغ ↤ {format_money(net)} ﷼ 💵")
        except Exception:
            pass
        return True

    async def _cancel_transfer(self, msg: IncomingMessage) -> None:
        await self.store.delete(self.store.key("trans", msg.chat_id, ":", msg.user_id), self.store.key("transn", msg.user_id))

    async def _invest(self, msg: IncomingMessage, amount: int) -> None:
        if not await self.account_exists(msg.user_id):
            await self.bot.send_message(msg.chat_id, "*⇜ ماعندك حساب بنكي ارسـل ↢* ( `انشاء حساب بنكي` )", msg.message_id)
            return
        if amount <= 0 or amount > await self._money(msg.user_id):
            await self.bot.send_message(msg.chat_id, "⇜ فلوسك ماتكفي\n✓", msg.message_id)
            return
        percent = random.randint(1, 15)
        profit = amount * percent // 100
        await self._set_money(msg.user_id, await self._money(msg.user_id) + profit)
        await self.bot.send_message(msg.chat_id, f"⇜ استثمار ناجح 💰\n⇜ نسبة الربح ↤ {percent}%\n⇜ مبلغ الربح ↤ ❲ {format_money(profit)} ﷼ 💵 ❳\n⇜ فلوسك صارت ↤ ❲ {format_money(await self._money(msg.user_id))} ﷼ 💵 ❳\n✓", msg.message_id)

    async def _rich_list(self, msg: IncomingMessage) -> None:
        users = await self.store.smembers(self.store.key("booob"))
        if not users:
            await self.bot.send_message(msg.chat_id, "⇜ لا يوجد حسابات في البنك", msg.message_id)
            return
        rows = []
        for user in users:
            rows.append((await self._money(int(user)), user))
        rows.sort(reverse=True)
        lines = ["⇜ ترتيب الاغنياء", "ٴ⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆"]
        for index, (money, user) in enumerate(rows[:10], 1):
            lines.append(f"{index} - `{user}` ↤ {format_money(money)} ﷼ 💵")
        await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)

    def _help_text(self) -> str:
        return (
            "*⌯ اوامر البنك 🏦*\n\n"
            "⌯ `انشاء حساب بنكي`  *↢  تسوي حساب وتقدر تحول فلوس*\n"
            "⌯ `مسح حساب بنكي`  *↢  تلغي حسابك البنكي*\n"
            "⌯ `تحويل`  *↢  تحول فلوس*\n"
            "⌯ `فلوسي`  *↢  يعلمك كم فلوسك*\n"
            "⌯ `راتب`  *↢  يعطيك راتب كل ١٠ دقائق*\n"
            "⌯ `بخشيش`  *↢  يعطيك بخشيش كل ١٠ دقايق*\n"
            "⌯ `استثمار`  *↢  تستثمر بالمبلغ اللي تبيه*"
            "\n⌯ `رهان` / `حظ` / `متجر` / `مستواي`"
        )

    def _split_callback(self, data: str) -> tuple[int | None, str]:
        if "/" not in data:
            return None, data
        user, action = data.split("/", 1)
        if user.isdigit():
            return int(user), action
        return None, action
