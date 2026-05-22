from __future__ import annotations

import re
import time

from .models import IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import deny


class AdvancedGroupService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        if await self._finish_pending(msg, ctx):
            return True
        text = msg.effective_text or ""
        if await self._welcome_commands(msg, ctx, text):
            return True
        if await self._rules_commands(msg, ctx, text):
            return True
        if await self._subscription_commands(msg, ctx, text):
            return True
        if await self._info_commands(msg, ctx, text):
            return True
        if await self._alias_commands(msg, ctx, text):
            return True
        if await self._custom_rank_commands(msg, ctx, text):
            return True
        if await self._cleanup_commands(msg, ctx, text):
            return True
        if await self._warning_settings(msg, ctx, text):
            return True
        if await self._feature_switches(msg, ctx, text):
            return True
        if await self._timed_restrict(msg, ctx, text):
            return True
        return False

    async def _alias_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"اضف امر", "اضف اختصار"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:Alias", msg.user_id, ":", msg.chat_id), 300, "alias")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل الاختصار الجديد", msg.message_id)
            return True
        if text in {"اضف امر عام", "اضف اختصار عام"}:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:Alias:Global", msg.user_id), 300, "alias")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل الاختصار العام الجديد", msg.message_id)
            return True
        if text in {"مسح امر", "مسح اختصار"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:Alias", msg.user_id, ":", msg.chat_id), 300, "delete")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل الاختصار لمسحه", msg.message_id)
            return True
        if text in {"الاوامر المختصره", "الاختصارات"}:
            keys = await self.store.keys(self.store.key("Zelzal:Get:Reides:Commands:Group", msg.chat_id, ":*"))
            if not keys:
                await self.bot.send_message(msg.chat_id, "⇜ لا توجد اختصارات", msg.message_id)
                return True
            prefix = self.store.key("Zelzal:Get:Reides:Commands:Group", msg.chat_id, ":")
            lines = ["*⇜ الاختصارات*"]
            for key in sorted(keys):
                alias = key.removeprefix(prefix)
                target = await self.store.get(key) or ""
                lines.append(f"{alias} ← {target}")
            await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)
            return True
        return False

    async def _custom_rank_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"ضع رتبه", "ضع رتبة", "تعيين رتبه", "تعيين رتبة"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            if not msg.reply_to_user_id:
                await self.bot.send_message(msg.chat_id, "⇜ استخدم الامر بالرد على العضو", msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:CustomRank", msg.user_id, ":", msg.chat_id), 300, str(msg.reply_to_user_id))
            await self.bot.send_message(msg.chat_id, "⇜ ارسل الرتبة الجديدة", msg.message_id)
            return True
        if text in {"مسح رتبته", "مسح رتبه", "مسح رتبة"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            target = msg.reply_to_user_id
            if not target:
                await self.bot.send_message(msg.chat_id, "⇜ استخدم الامر بالرد على العضو", msg.message_id)
                return True
            await self.store.delete(self.store.key("Zelzal:SetRt", msg.chat_id, ":", target))
            await self.bot.send_message(msg.chat_id, "⇜ تم مسح رتبة العضو", msg.message_id)
            return True
        return False

    async def _warning_settings(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        match = re.fullmatch(r"(?:ضع|تعيين) التحذيرات (\d+)", text)
        if not match:
            return False
        if not ctx.manager:
            await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
            return True
        value = max(1, min(20, int(match.group(1))))
        await self.store.set(self.store.key("Zelzal:Warnings:Max", msg.chat_id), value)
        await self.bot.send_message(msg.chat_id, f"⇜ تم تعيين حد التحذيرات إلى {value}", msg.message_id)
        return True

    async def _welcome_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"ضع الترحيب", "تغيير الترحيب", "تعيين الترحيب"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:Welcome", msg.user_id, ":", msg.chat_id), 300, "text")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل كليشة الترحيب\n⇜ المتغيرات: {الاسم} {الايدي} {المعرف}", msg.message_id)
            return True
        if text in {"ضع صوره للترحيب", "ضع صورة للترحيب"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:Welcome", msg.user_id, ":", msg.chat_id), 300, "photo")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل صورة الترحيب الان", msg.message_id)
            return True
        if text in {"مسح الترحيب", "حذف الترحيب"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.delete(self.store.key("Zelzal:Welcome:Group", msg.chat_id), self.store.key("Zelzal:Welcome:Photo", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم مسح الترحيب", msg.message_id)
            return True
        if text in {"الترحيب", "جلب الترحيب"}:
            welcome = await self.store.get(self.store.key("Zelzal:Welcome:Group", msg.chat_id)) or "⇜ اهلاً وسهلاً بك"
            await self.bot.send_message(msg.chat_id, welcome, msg.message_id)
            return True
        return False

    async def _feature_switches(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        switches = {
            "الالعاب": "Zelzal:Status:Games",
            "الألعاب": "Zelzal:Status:Games",
            "البنك": "Zelzal:Status:Bank",
            "الردود": "Zelzal:Status:Reply",
            "الردود العامه": "Zelzal:Status:ReplySudo",
            "الردود العامة": "Zelzal:Status:ReplySudo",
            "الايدي": "Zelzal:Status:Id",
            "الايدي بالصوره": "Zelzal:Status:IdPhoto",
            "التاك": "tagallgroup",
        }
        for prefix, enabled in (("تفعيل ", True), ("تعطيل ", False)):
            if not text.startswith(prefix):
                continue
            subject = text.removeprefix(prefix).strip()
            key = switches.get(subject)
            if not key:
                return False
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            redis_key = self.store.key(key, msg.chat_id)
            disabled_key = self.store.key("Zelzal:Disabled:", subject, ":", msg.chat_id)
            if enabled:
                await self.store.set(redis_key, "true")
                await self.store.delete(disabled_key)
                await self.bot.send_message(msg.chat_id, f"⇜ تم تفعيل {subject}", msg.message_id)
            else:
                await self.store.delete(redis_key)
                await self.store.set(disabled_key, "true")
                await self.bot.send_message(msg.chat_id, f"⇜ تم تعطيل {subject}", msg.message_id)
            return True
        return False

    async def _rules_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"ضع القوانين", "تعيين القوانين"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:Rules", msg.user_id, ":", msg.chat_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل قوانين المجموعة الان", msg.message_id)
            return True
        if text in {"مسح القوانين", "حذف القوانين"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.delete(self.store.key("Zelzal:Rules:Group", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم مسح القوانين", msg.message_id)
            return True
        if text in {"القوانين", "قوانين"}:
            rules = await self.store.get(self.store.key("Zelzal:Rules:Group", msg.chat_id))
            await self.bot.send_message(msg.chat_id, rules or "⇜ لم يتم تعيين قوانين للمجموعة", msg.message_id)
            return True
        return False

    async def _subscription_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"تفعيل الاشتراك الاجباري", "تفعيل الاشتراك"}:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:ForceSub:Status"), "true")
            await self.bot.send_message(msg.chat_id, "⇜ تم تفعيل الاشتراك الاجباري", msg.message_id)
            return True
        if text in {"تعطيل الاشتراك الاجباري", "تعطيل الاشتراك"}:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.delete(self.store.key("Zelzal:ForceSub:Status"))
            await self.bot.send_message(msg.chat_id, "⇜ تم تعطيل الاشتراك الاجباري", msg.message_id)
            return True
        if text in {"الاشتراك الاجباري", "تغيير الاشتراك الاجباري", "اشتراك البوت"}:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:ForceSub", msg.user_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل معرف قناة الاشتراك بدون @ او معها", msg.message_id)
            return True
        if text == "ضع تاريخ الاشتراك":
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:ForceSubDate", msg.user_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل تاريخ انتهاء الاشتراك", msg.message_id)
            return True
        return False

    async def _info_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"معلومات المجموعه", "معلومات المجموعة", "معلومات القروب", "المجموعه", "القروب"}:
            members = await self.store.scard(self.store.key("Zelzal:Group:Users", msg.chat_id))
            messages = await self.store.keys(self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":*"))
            await self.bot.send_message(
                msg.chat_id,
                f"⇜ معلومات المجموعة\n⇜ الايدي: `{msg.chat_id}`\n⇜ الاعضاء المسجلين: {members}\n⇜ المتفاعلين: {len(messages)}",
                msg.message_id,
            )
            return True
        if text in {"رابط", "الرابط", "رابط المجموعة", "رابط المجموعه"}:
            link = await self.store.get(self.store.key("Zelzal:Group:Link", msg.chat_id))
            if not link:
                try:
                    chat = await self.bot.get_chat(msg.chat_id)
                    link = str(chat.get("invite_link") or "")
                except Exception:
                    link = ""
            await self.bot.send_message(msg.chat_id, link or "⇜ لا يوجد رابط محفوظ للمجموعة", msg.message_id)
            return True
        if text in {"ضع الرابط", "حفظ الرابط"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.setex(self.store.key("Zelzal:Set:Link", msg.user_id, ":", msg.chat_id), 300, "true")
            await self.bot.send_message(msg.chat_id, "⇜ ارسل رابط المجموعة", msg.message_id)
            return True
        return False

    async def _cleanup_commands(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if text in {"تفعيل الحذف التلقائي", "تفعيل التنظيف التلقائي"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.set(self.store.key("Zelzal:AutoClean", msg.chat_id), "true")
            await self.bot.send_message(msg.chat_id, "⇜ تم تفعيل الحذف التلقائي", msg.message_id)
            return True
        if text in {"تعطيل الحذف التلقائي", "تعطيل التنظيف التلقائي"}:
            if not ctx.manager:
                await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                return True
            await self.store.delete(self.store.key("Zelzal:AutoClean", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم تعطيل الحذف التلقائي", msg.message_id)
            return True
        if text in {"تنظيف المجموعات", "✦ تنظيف المجموعات ✦"}:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            groups = await self.store.smembers(self.store.key("Zelzal:ChekBotAdd"))
            await self.bot.send_message(msg.chat_id, f"⇜ تم فحص {len(groups)} مجموعة", msg.message_id)
            return True
        if text in {"تنظيف المشتركين", "✦ تنظيف المشتركين ✦"}:
            if not ctx.controller_bot:
                await self.bot.send_message(msg.chat_id, deny(controller_num(1)), msg.message_id)
                return True
            users = await self.store.smembers(self.store.key("Zelzal:Num:User:Pv"))
            await self.bot.send_message(msg.chat_id, f"⇜ تم فحص {len(users)} مشترك", msg.message_id)
            return True
        return False

    async def _timed_restrict(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        match = re.fullmatch(r"(?:تقييد|كتم) مؤقت\s+(\d+)\s*(د|س|ي)?", text)
        if not match:
            return False
        if not ctx.admin:
            await self.bot.send_message(msg.chat_id, deny(controller_num(7)), msg.message_id)
            return True
        if not msg.reply_to_user_id:
            await self.bot.send_message(msg.chat_id, "⇜ استخدم الامر بالرد على العضو", msg.message_id)
            return True
        amount = int(match.group(1))
        unit = match.group(2) or "د"
        seconds = amount * {"د": 60, "س": 3600, "ي": 86400}[unit]
        await self.bot.restrict_member(msg.chat_id, msg.reply_to_user_id, until_date=int(time.time()) + seconds)
        await self.bot.send_message(msg.chat_id, "⇜ تم تقييد العضو مؤقتاً", msg.message_id)
        return True

    async def _finish_pending(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        if not ctx.manager and not ctx.controller_bot:
            return False
        text = msg.effective_text or ""
        pending_map = {
            self.store.key("Zelzal:Set:Welcome", msg.user_id, ":", msg.chat_id): ("Zelzal:Welcome:Group", "⇜ تم حفظ الترحيب"),
            self.store.key("Zelzal:Set:Rules", msg.user_id, ":", msg.chat_id): ("Zelzal:Rules:Group", "⇜ تم حفظ القوانين"),
            self.store.key("Zelzal:Set:Link", msg.user_id, ":", msg.chat_id): ("Zelzal:Group:Link", "⇜ تم حفظ الرابط"),
        }
        for state_key, (target, done) in pending_map.items():
            mode = await self.store.get(state_key)
            if not mode:
                continue
            if target == "Zelzal:Welcome:Group" and mode == "photo":
                if msg.content_type != "photo" or not msg.file_id:
                    await self.bot.send_message(msg.chat_id, "⇜ ارسل صورة فقط", msg.message_id)
                    return True
                await self.store.set(self.store.key("Zelzal:Welcome:Photo", msg.chat_id), msg.file_id)
            else:
                await self.store.set(self.store.key(target, msg.chat_id), text)
            await self.store.delete(state_key)
            await self.bot.send_message(msg.chat_id, done, msg.message_id)
            return True
        alias_state = await self.store.get(self.store.key("Zelzal:Set:Alias", msg.user_id, ":", msg.chat_id))
        if alias_state:
            if alias_state == "alias":
                await self.store.set(self.store.key("Zelzal:Alias:Pending", msg.user_id, ":", msg.chat_id), text)
                await self.store.set(self.store.key("Zelzal:Set:Alias", msg.user_id, ":", msg.chat_id), "target")
                await self.bot.send_message(msg.chat_id, "⇜ ارسل الامر الاصلي", msg.message_id)
                return True
            if alias_state == "target":
                alias = await self.store.get(self.store.key("Zelzal:Alias:Pending", msg.user_id, ":", msg.chat_id))
                if alias:
                    await self.store.set(self.store.key("Zelzal:Get:Reides:Commands:Group", msg.chat_id, ":", alias), text)
                await self.store.delete(self.store.key("Zelzal:Set:Alias", msg.user_id, ":", msg.chat_id), self.store.key("Zelzal:Alias:Pending", msg.user_id, ":", msg.chat_id))
                await self.bot.send_message(msg.chat_id, "⇜ تم حفظ الاختصار", msg.message_id)
                return True
            await self.store.delete(self.store.key("Zelzal:Get:Reides:Commands:Group", msg.chat_id, ":", text), self.store.key("Zelzal:Set:Alias", msg.user_id, ":", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم مسح الاختصار", msg.message_id)
            return True
        global_alias_state = await self.store.get(self.store.key("Zelzal:Set:Alias:Global", msg.user_id))
        if global_alias_state:
            if global_alias_state == "alias":
                await self.store.set(self.store.key("Zelzal:Alias:Global:Pending", msg.user_id), text)
                await self.store.set(self.store.key("Zelzal:Set:Alias:Global", msg.user_id), "target")
                await self.bot.send_message(msg.chat_id, "⇜ ارسل الامر الاصلي", msg.message_id)
                return True
            alias = await self.store.get(self.store.key("Zelzal:Alias:Global:Pending", msg.user_id))
            if alias:
                await self.store.set(self.store.key("All:Get:Reides:Commands:Group", alias), text)
            await self.store.delete(self.store.key("Zelzal:Set:Alias:Global", msg.user_id), self.store.key("Zelzal:Alias:Global:Pending", msg.user_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم حفظ الاختصار العام", msg.message_id)
            return True
        custom_rank_target = await self.store.get(self.store.key("Zelzal:Set:CustomRank", msg.user_id, ":", msg.chat_id))
        if custom_rank_target:
            await self.store.set(self.store.key("Zelzal:SetRt", msg.chat_id, ":", custom_rank_target), text)
            await self.store.delete(self.store.key("Zelzal:Set:CustomRank", msg.user_id, ":", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم حفظ رتبة العضو", msg.message_id)
            return True
        if await self.store.get(self.store.key("Zelzal:Set:ForceSub", msg.user_id)):
            await self.store.set(self.store.key("Zelzal:ForceSub:Channel"), text.lstrip("@"))
            await self.store.delete(self.store.key("Zelzal:Set:ForceSub", msg.user_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم حفظ قناة الاشتراك الاجباري", msg.message_id)
            return True
        if await self.store.get(self.store.key("Zelzal:Set:ForceSubDate", msg.user_id)):
            await self.store.set(self.store.key("Zelzal:ForceSub:Date"), text)
            await self.store.delete(self.store.key("Zelzal:Set:ForceSubDate", msg.user_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم حفظ تاريخ الاشتراك", msg.message_id)
            return True
        return False
