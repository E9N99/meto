from __future__ import annotations

from dataclasses import dataclass

from .models import IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import deny


@dataclass(slots=True)
class PendingState:
    key: str
    target_key: str
    prompt_done: str
    transform: str = "raw"


RANK_STATES = {
    "✦ رتبة المطور الاساسي ✦": ("Zelzal:Change:Rotba:Sudo1", "Zelzal:Sudo:General:Reply"),
    "✦ رتبة المطور الاساسي2 ✦": ("Zelzal:Change:Rotba:Sudo2", "Zelzal:Sudo2:General:Reply"),
    "✦ رتبة المطور الثانوي ✦": ("Zelzal:Change:Rotba:DevQ", "Zelzal:DeveloperQ:General:Reply"),
    "✦ رتبة المطوره الثانويه ✦": ("Zelzal:Change:Rotba:MevQ", "Zelzal:MeveloperQ:General:Reply"),
    "✦ رتبة المطور ✦": ("Zelzal:Change:Rotba:Dev", "Zelzal:Developer:General:Reply"),
    "✦ رتبة المطوره ✦": ("Zelzal:Change:Rotba:Mev", "Zelzal:Meveloper:General:Reply"),
    "✦ رتبة المالك الاساسي ✦": ("Zelzal:Change:Rotba:Pqq", "Zelzal:PresidentQQ:General:Reply"),
    "✦ رتبة المالكه الاساسيه ✦": ("Zelzal:Change:Rotba:Mqq", "Zelzal:MresidentQQ:General:Reply"),
    "✦ رتبة المالك ✦": ("Zelzal:Change:Rotba:Ppp", "Zelzal:PresidentQ:General:Reply"),
    "✦ رتبة المالكه ✦": ("Zelzal:Change:Rotba:Mpp", "Zelzal:MresidentQ:General:Reply"),
    "✦ رتبة المنشئ الاساسي ✦": ("Zelzal:Change:Rotba:Prr", "Zelzal:President:General:Reply"),
    "✦ رتبة المنشئه الاساسيه ✦": ("Zelzal:Change:Rotba:Mrr", "Zelzal:Mresident:General:Reply"),
    "✦ رتبة المنشئ ✦": ("Zelzal:Change:Rotba:Crr", "Zelzal:Constructor:General:Reply"),
    "✦ رتبة المنشئه ✦": ("Zelzal:Change:Rotba:Mir", "Zelzal:Monstructor:General:Reply"),
    "✦ رتبة المدير ✦": ("Zelzal:Change:Rotba:Mod", "Zelzal:Manager:General:Reply"),
    "✦ رتبة المديره ✦": ("Zelzal:Change:Rotba:Mom", "Zelzal:Mamager:General:Reply"),
    "✦ رتبة الادمن ✦": ("Zelzal:Change:Rotba:Adm", "Zelzal:Admin:General:Reply"),
    "✦ رتبة الادمونه ✦": ("Zelzal:Change:Rotba:Mdm", "Zelzal:Mdmin:General:Reply"),
    "✦ رتبة المميز ✦": ("Zelzal:Change:Rotba:Vip", "Zelzal:Vip:General:Reply"),
    "✦ رتبة المميزه ✦": ("Zelzal:Change:Rotba:Mip", "Zelzal:Mip:General:Reply"),
    "✦ رتبة العضو ✦": ("Zelzal:Change:Rotba:Mem", "Zelzal:Mempar:General:Reply"),
}


class DeveloperCommandService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if text in {"الغاء", "الغاء الامر", "✦ الغـاء الامــر ✦"}:
            if not ctx.controller_bot and not await self._has_pending(msg):
                return False
            await self._cancel(msg)
            return True
        if await self._finish_pending(msg, ctx):
            return True
        if not ctx.controller_bot:
            return False
        if text in {"✦ الاحصـائيـات ✦", "احصائيات"}:
            groups = await self.store.scard(self.store.key("Zelzal:ChekBotAdd"))
            users = await self.store.scard(self.store.key("Zelzal:Num:User:Pv"))
            await self.bot.send_message(msg.chat_id, f"*⇜ عدد احصائيات البوت *\nٴ*⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆*\n*⇜ عدد القروبات :* {groups}\n*⇜ عدد المشتركين :* {users}", msg.message_id)
            return True
        if text in {"✦ تفعيل البوت الخدمي ✦", "تفعيل البوت الخدمي"}:
            await self.store.set(self.store.key("Zelzal:BotFree"), "true")
            await self.bot.send_message(msg.chat_id, "*⇜ تم تفعيل البوت الخدمي*", msg.message_id)
            return True
        if text in {"✦ تعطيل البوت الخدمي ✦", "تعطيل البوت الخدمي"}:
            await self.store.delete(self.store.key("Zelzal:BotFree"))
            await self.bot.send_message(msg.chat_id, "*⇜ تم تعطيل البوت الخدمي*", msg.message_id)
            return True
        if text in {"تفعيل التواصل"}:
            await self.store.set(self.store.key("Zelzal:TwaslBot"), "true")
            await self.bot.send_message(msg.chat_id, "*⇜ تم تفعيل التواصل*", msg.message_id)
            return True
        if text in {"تعطيل التواصل"}:
            await self.store.delete(self.store.key("Zelzal:TwaslBot"))
            await self.bot.send_message(msg.chat_id, "*⇜ تم تعطيل التواصل*", msg.message_id)
            return True
        if text in {"اذاعه", "اذاعة", "✦ اذاعـه للمجموعـات ✦"}:
            await self.store.setex(self.store.key("Zelzal:Broadcast", msg.user_id), 300, "groups")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل نص الاذاعة للمجموعات*", msg.message_id)
            return True
        if text in {"اذاعه خاص", "اذاعة خاص", "✦ اذاعـه خـاص ✦"}:
            await self.store.setex(self.store.key("Zelzal:Broadcast", msg.user_id), 300, "users")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل نص الاذاعة للخاص*", msg.message_id)
            return True
        if text in {"اذاعه بالتثبيت", "اذاعة بالتثبيت", "✦ اذاعـه بالتثبيت ✦"}:
            await self.store.setex(self.store.key("Zelzal:Broadcast", msg.user_id), 300, "pin")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل نص الاذاعة بالتثبيت*", msg.message_id)
            return True
        if text in {"✦ تغيير اسم البوت ✦", "تغيير اسم البوت"}:
            await self.store.setex(self.store.key("Zelzal:Change:Name:Bot", msg.user_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل اسم البوت الجديد*", msg.message_id)
            return True
        if text in {"✦ حذف اسم البوت ✦", "مسح اسم البوت", "حذف اسم البوت"}:
            await self.store.delete(self.store.key("Zelzal:Name:Bot"))
            await self.bot.send_message(msg.chat_id, "*⇜ تم حذف اسم البوت*", msg.message_id)
            return True
        if text in {"تغيير كليشه ستارت", "✦ تغيير كليشه ستارت ✦"}:
            await self.store.setex(self.store.key("Zelzal:Change:Start:Bot", msg.user_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل كليشة ستارت الجديدة*", msg.message_id)
            return True
        if text in {"مسح كليشه ستارت", "✦ حذف كليشه ستارت ✦"}:
            await self.store.delete(self.store.key("Zelzal:Start:Bot"))
            await self.bot.send_message(msg.chat_id, "*⇜ تم مسح كليشة ستارت*", msg.message_id)
            return True
        if text == "تعيين قناة الحقوق":
            await self.store.set(self.store.key("set:chs", msg.user_id), "true")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل معرف قناة الحقوق مع @*", msg.message_id)
            return True
        if text in {"حذف قناة الحقوق", "مسح قناة الحقوق"}:
            await self.store.delete(self.store.key("chsource"))
            await self.bot.send_message(msg.chat_id, "*⇜ تم حذف قناة الحقوق*", msg.message_id)
            return True
        if text == "تعيين رمز السورس":
            await self.store.set(self.store.key("set:rmz", msg.user_id), "true")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل رمز السورس الجديد*", msg.message_id)
            return True
        if text in {"حذف رمز السورس", "مسح رمز السورس"}:
            await self.store.set(self.store.key("rmzsource"), "⇜")
            await self.bot.send_message(msg.chat_id, "*⇜ تم ارجاع رمز السورس الافتراضي*", msg.message_id)
            return True
        if text in RANK_STATES:
            state, _ = RANK_STATES[text]
            await self.store.setex(self.store.key(state, msg.user_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "*⇜ ارسل اسم الرتبة الجديد*", msg.message_id)
            return True
        if text in {"القروبات", "الجروبات", "الكروبات", "المجموعات", "✦ روابط المجموعات ✦"}:
            await self._list_groups(msg)
            return True
        if text in {"المحظورين عام", "قائمه العام"}:
            await self._list_set(msg, "Zelzal:BanAll:Groups", "قائمة المحظورين عام")
            return True
        if text in {"المكتومين عام", "قائمه المكتومين عام"}:
            await self._list_set(msg, "Zelzal:KtmAll:Groups", "قائمة المكتومين عام")
            return True
        if text in {"المطورين", "✦ المطـوريـن ✦"}:
            await self._list_set(msg, "Zelzal:Developers:Groups", "قائمة المطورين")
            return True
        if text in {"الثانويين", "✦ المطورين الثانويين ✦"}:
            await self._list_set(msg, "Zelzal:DevelopersQ:Groups", "قائمة المطورين الثانويين")
            return True
        return False

    async def _finish_pending(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        if not ctx.controller_bot:
            return False
        text = msg.effective_text or ""
        simple_states = [
            PendingState(self.store.key("Zelzal:Change:Name:Bot", msg.user_id), self.store.key("Zelzal:Name:Bot"), "*⇜ تم حفظ اسم البوت*"),
            PendingState(self.store.key("Zelzal:Change:Start:Bot", msg.user_id), self.store.key("Zelzal:Start:Bot"), "*⇜ تم حفظ كليشة ستارت*"),
            PendingState(self.store.key("set:chs", msg.user_id), self.store.key("chsource"), "*⇜ تم حفظ معرف قناة الحقوق*", "username"),
            PendingState(self.store.key("set:rmz", msg.user_id), self.store.key("rmzsource"), "*⇜ تم حفظ رمز السورس*"),
        ]
        broadcast = await self.store.get(self.store.key("Zelzal:Broadcast", msg.user_id))
        if broadcast:
            await self.store.delete(self.store.key("Zelzal:Broadcast", msg.user_id))
            targets = await self.store.smembers(self.store.key("Zelzal:ChekBotAdd" if broadcast in {"groups", "pin"} else "Zelzal:Num:User:Pv"))
            sent = 0
            for target in targets:
                try:
                    result = await self.bot.send_message(int(target), text)
                    if broadcast == "pin" and isinstance(result, dict):
                        message_id = int(result.get("message_id") or 0)
                        if message_id:
                            await self.bot.pin_message(int(target), message_id)
                    sent += 1
                except Exception:
                    continue
            await self.bot.send_message(msg.chat_id, f"*⇜ تمت الاذاعة إلى {sent} وجهة*", msg.message_id)
            return True
        for state in simple_states:
            if await self.store.get(state.key):
                value = text.lstrip("@") if state.transform == "username" else text
                await self.store.set(state.target_key, value)
                await self.store.delete(state.key)
                await self.bot.send_message(msg.chat_id, state.prompt_done, msg.message_id)
                return True
        for _, (state_name, target_name) in RANK_STATES.items():
            state_key = self.store.key(state_name, msg.user_id)
            if await self.store.get(state_key):
                await self.store.set(self.store.key(target_name), text)
                await self.store.delete(state_key)
                await self.bot.send_message(msg.chat_id, "*⇜ تم حفظ اسم الرتبة*", msg.message_id)
                return True
        return False

    async def _cancel(self, msg: IncomingMessage) -> None:
        patterns = [
            self.store.key("*", msg.user_id),
            self.store.key("Zelzal:Change:*", msg.user_id),
            self.store.key("set:chs", msg.user_id),
            self.store.key("set:rmz", msg.user_id),
        ]
        for pattern in patterns:
            keys = await self.store.keys(pattern)
            if keys:
                await self.store.delete(*keys)
        await self.bot.send_message(msg.chat_id, "*⇜ تم الغـاء الامـر .. بنجاح ✓*", msg.message_id)

    async def _has_pending(self, msg: IncomingMessage) -> bool:
        keys = [
            self.store.key("Zelzal:Change:Name:Bot", msg.user_id),
            self.store.key("Zelzal:Change:Start:Bot", msg.user_id),
            self.store.key("set:chs", msg.user_id),
            self.store.key("set:rmz", msg.user_id),
        ]
        keys.extend(self.store.key(state_name, msg.user_id) for _, (state_name, _) in RANK_STATES.items())
        for key in keys:
            if await self.store.get(key):
                return True
        return False

    async def _list_groups(self, msg: IncomingMessage) -> None:
        groups = sorted(await self.store.smembers(self.store.key("Zelzal:ChekBotAdd")))
        if not groups:
            await self.bot.send_message(msg.chat_id, "*⇜ لا توجد مجموعات مفعلة*", msg.message_id)
            return
        lines = ["*⇜ قائمة المجموعات*", "ٴ*⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆*"]
        lines.extend(f"{i} - `{group}`" for i, group in enumerate(groups[:50], 1))
        await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)

    async def _list_set(self, msg: IncomingMessage, key: str, title: str) -> None:
        values = sorted(await self.store.smembers(self.store.key(key)))
        if not values:
            await self.bot.send_message(msg.chat_id, f"*⇜ لا يوجد {title}*", msg.message_id)
            return
        lines = [f"*⇜ {title}*", "ٴ*⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆*"]
        lines.extend(f"{i} - `{value}`" for i, value in enumerate(values, 1))
        await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)
