from __future__ import annotations

import re
import time

from .models import IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import deny, get_by_name


class AdminService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if text in {"تفعيل", "تفعيل البوت"} and msg.chat_type != "private":
            if not ctx.owner:
                await self.bot.send_message(msg.chat_id, deny(controller_num(4)), msg.message_id)
                return True
            await self.store.sadd(self.store.key("Zelzal:ChekBotAdd"), msg.chat_id)
            await self.bot.send_message(msg.chat_id, get_by_name(msg.user_id, msg.first_name) + "*⇜ تم تفعيل البوت في المجموعة*", msg.message_id)
            return True
        if text in {"تعطيل", "تعطيل البوت"} and msg.chat_type != "private":
            if not ctx.owner:
                await self.bot.send_message(msg.chat_id, deny(controller_num(4)), msg.message_id)
                return True
            await self.store.srem(self.store.key("Zelzal:ChekBotAdd"), msg.chat_id)
            await self.bot.send_message(msg.chat_id, get_by_name(msg.user_id, msg.first_name) + "*⇜ تم تعطيل البوت في المجموعة*", msg.message_id)
            return True
        if text in {"ايدي", "ايديي", "id"}:
            target_id = msg.reply_to_user_id or msg.user_id
            name = msg.first_name if target_id == msg.user_id else "العضو"
            await self.bot.send_message(msg.chat_id, f"⇜ الاسم : {name}\n⇜ الايدي : `{target_id}`\n⇜ رتبتك : {ctx.role_name}", msg.message_id)
            return True
        if text in {"كشف", "كشف العضو"}:
            target_id = msg.reply_to_user_id
            if not target_id:
                await self.bot.send_message(msg.chat_id, "⇜ استخدم الامر بالرد على العضو", msg.message_id)
                return True
            messages = await self.store.get(self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":", target_id)) or "0"
            warnings = await self.store.get(self.store.key("Zelzal:Warnings", msg.chat_id, ":", target_id)) or "0"
            await self.bot.send_message(msg.chat_id, f"⇜ كشف العضو\n⇜ الايدي : `{target_id}`\n⇜ الرسائل : {messages}\n⇜ التحذيرات : {warnings}", msg.message_id)
            return True
        if text in {"رسائلي", "تفاعلي"}:
            count = await self.store.get(self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":", msg.user_id)) or "0"
            await self.bot.send_message(msg.chat_id, f"⇜ رسائلك : {count}", msg.message_id)
            return True
        if text in {"مسح رسائلي", "مسح تفاعلي"}:
            await self.store.delete(self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":", msg.user_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم مسح رسائلك", msg.message_id)
            return True
        if text in {"توب التفاعل", "توب الرسائل", "توب المتفاعلين"}:
            await self._top_messages(msg)
            return True
        if text in {"رتبتي", "من انا"}:
            await self.bot.send_message(msg.chat_id, f"⇜ رتبتك : {ctx.role_name}", msg.message_id)
            return True
        if text in {"الاعدادات", "الاعدادت"}:
            await self._settings(msg)
            return True
        if await self._rank_lists_and_clear(msg, ctx, text):
            return True
        if await self._moderation_command(msg, ctx, text):
            return True
        if text.startswith("رفع ") or text.startswith("تنزيل "):
            return await self._rank_command(msg, ctx, text)
        return False

    async def _top_messages(self, msg: IncomingMessage) -> None:
        keys = await self.store.keys(self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":*"))
        rows = []
        prefix = self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":")
        for key in keys:
            user_id = key.removeprefix(prefix)
            count = int(await self.store.get(key) or 0)
            rows.append((count, user_id))
        rows.sort(reverse=True)
        if not rows:
            await self.bot.send_message(msg.chat_id, "⇜ لا يوجد تفاعل مسجل", msg.message_id)
            return
        lines = ["*⇜ توب التفاعل*"]
        lines.extend(f"{i} - `{user}` : {count}" for i, (count, user) in enumerate(rows[:10], 1))
        await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)

    async def _settings(self, msg: IncomingMessage) -> None:
        lock_names = {
            "الروابط": "Zelzal:Lock:Link",
            "المعرف": "Zelzal:Lock:User:Name",
            "الصور": "Zelzal:Lock:Photo",
            "الفيديو": "Zelzal:Lock:Video",
            "الملصقات": "Zelzal:Lock:Sticker",
            "التوجيه": "Zelzal:Lock:forward",
            "السبام": "Zelzal:Lock:Spam",
        }
        lines = ["*⇜ اعدادات المجموعة*", "ٴ*⋆┄─┄─┄─┄┄─┄─┄─┄─┄┄⋆*"]
        for label, key in lock_names.items():
            value = await self.store.get(self.store.key(key, msg.chat_id))
            lines.append(f"⇜ قفل {label} : {'نعم' if value else 'لا'}")
        await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)

    async def _rank_lists_and_clear(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        rank_sets = {
            "المالكين الاساسيين": ("Zelzal:MalekAsase:Group", 60, "قائمة المالكين الاساسيين"),
            "المالكين": ("Zelzal:TheBasicsQ:Group", 50, "قائمة المالكين"),
            "المنشئين الاساسيين": ("Zelzal:TheBasics:Group", 50, "قائمة المنشئين الاساسيين"),
            "المنشئين": ("Zelzal:Originators:Group", 40, "قائمة المنشئين"),
            "المدراء": ("Zelzal:Managers:Group", 30, "قائمة المدراء"),
            "الادمنيه": ("Zelzal:Addictive:Group", 20, "قائمة الادمنية"),
            "الادمنية": ("Zelzal:Addictive:Group", 20, "قائمة الادمنية"),
            "المميزين": ("Zelzal:Distinguished:Group", 10, "قائمة المميزين"),
        }
        if text == "تنزيل جميع الرتب":
            if not ctx.owner:
                await self.bot.send_message(msg.chat_id, deny(controller_num(4)), msg.message_id)
                return True
            keys = [self.store.key(prefix, msg.chat_id) for prefix, _, _ in rank_sets.values()]
            await self.store.delete(*keys)
            await self.bot.send_message(msg.chat_id, "⇜ تم تنزيل جميع رتب المجموعة", msg.message_id)
            return True
        if text.startswith("مسح "):
            target = text.removeprefix("مسح ").strip()
            if target in rank_sets:
                prefix, required, label = rank_sets[target]
                if ctx.rank < required:
                    await self.bot.send_message(msg.chat_id, deny(controller_num(6)), msg.message_id)
                    return True
                await self.store.delete(self.store.key(prefix, msg.chat_id))
                await self.bot.send_message(msg.chat_id, f"⇜ تم مسح {label}", msg.message_id)
                return True
        if text in rank_sets:
            prefix, required, label = rank_sets[text]
            if ctx.rank < min(required, 30):
                await self.bot.send_message(msg.chat_id, deny(controller_num(7)), msg.message_id)
                return True
            values = sorted(await self.store.smembers(self.store.key(prefix, msg.chat_id)))
            if not values:
                await self.bot.send_message(msg.chat_id, f"⇜ لا يوجد {label}", msg.message_id)
                return True
            lines = [f"*⇜ {label}*"]
            lines.extend(f"{i} - `{user_id}`" for i, user_id in enumerate(values, 1))
            await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)
            return True
        return False

    async def _moderation_command(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        moderation = {
            "حظر": ("ban", 20),
            "طرد": ("kick", 20),
            "كتم": ("mute", 20),
            "تقييد": ("restrict", 20),
            "الغاء حظر": ("unban", 20),
            "الغاء الحظر": ("unban", 20),
            "الغاء كتم": ("unmute", 20),
            "الغاء الكتم": ("unmute", 20),
            "الغاء تقييد": ("unrestrict", 20),
            "رفع القيود": ("unrestrict", 20),
            "حظر عام": ("global_ban", 70),
            "كتم عام": ("global_mute", 70),
            "الغاء العام": ("global_clear", 70),
            "الغاء حظر عام": ("global_unban", 70),
            "الغاء كتم عام": ("global_unmute", 70),
            "تحذير": ("warn", 20),
            "انذار": ("warn", 20),
            "مسح التحذيرات": ("clear_warns", 20),
            "مسح الانذارات": ("clear_warns", 20),
        }
        if text in {"تثبيت", "تثبيت الرساله", "تثبيت الرسالة"}:
            if not ctx.admin:
                await self.bot.send_message(msg.chat_id, deny(controller_num(7)), msg.message_id)
                return True
            if not msg.reply_to_message_id:
                await self.bot.send_message(msg.chat_id, "⇜ قم بالرد على الرسالة لتثبيتها", msg.message_id)
                return True
            await self.bot.pin_message(msg.chat_id, msg.reply_to_message_id)
            await self.bot.send_message(msg.chat_id, "⇜ تم تثبيت الرسالة", msg.message_id)
            return True
        if text in {"الغاء تثبيت", "الغاء التثبيت"}:
            if not ctx.admin:
                await self.bot.send_message(msg.chat_id, deny(controller_num(7)), msg.message_id)
                return True
            target_message = msg.reply_to_message_id or msg.message_id
            await self.bot.unpin_message(msg.chat_id, target_message)
            await self.bot.send_message(msg.chat_id, "⇜ تم الغاء التثبيت", msg.message_id)
            return True
        if text in {"مغادره", "غادر", "اخرج"}:
            if not ctx.owner:
                await self.bot.send_message(msg.chat_id, deny(controller_num(4)), msg.message_id)
                return True
            await self.bot.send_message(msg.chat_id, "⇜ تم تعطيل البوت ومغادرة المجموعة", msg.message_id)
            await self.store.srem(self.store.key("Zelzal:ChekBotAdd"), msg.chat_id)
            await self.bot.leave_chat(msg.chat_id)
            return True

        command, target_id = self._targeted_action(text, moderation)
        if not command:
            return False
        action, required_rank = command
        if ctx.rank < required_rank:
            await self.bot.send_message(msg.chat_id, deny(controller_num(7 if required_rank <= 20 else 3)), msg.message_id)
            return True
        target_id = target_id or msg.reply_to_user_id
        if not target_id:
            await self.bot.send_message(msg.chat_id, "⇜ استخدم الامر بالرد على العضو او مع الايدي", msg.message_id)
            return True
        if target_id == msg.user_id:
            await self.bot.send_message(msg.chat_id, "⇜ لا تستطيع تنفيذ الامر على نفسك", msg.message_id)
            return True
        await self._apply_moderation(msg, action, target_id)
        return True

    def _targeted_action(self, text: str, commands: dict[str, tuple[str, int]]) -> tuple[tuple[str, int] | None, int | None]:
        for command in sorted(commands, key=len, reverse=True):
            if text == command:
                return commands[command], None
            if text.startswith(command + " "):
                match = re.search(r"(-?\d+)$", text)
                return commands[command], int(match.group(1)) if match else None
        return None, None

    async def _apply_moderation(self, msg: IncomingMessage, action: str, target_id: int) -> None:
        if action == "ban":
            await self.store.sadd(self.store.key("Zelzal:BanGroup:Group", msg.chat_id), target_id)
            await self.bot.ban_member(msg.chat_id, target_id)
            text = "⇜ تم حظر العضو"
        elif action == "kick":
            await self.bot.ban_member(msg.chat_id, target_id)
            await self.bot.unban_member(msg.chat_id, target_id)
            text = "⇜ تم طرد العضو"
        elif action == "mute":
            await self.store.sadd(self.store.key("Zelzal:SilentGroup:Group", msg.chat_id), target_id)
            await self.bot.restrict_member(msg.chat_id, target_id)
            text = "⇜ تم كتم العضو"
        elif action == "restrict":
            await self.bot.restrict_member(msg.chat_id, target_id, until_date=int(time.time()) + 86400)
            text = "⇜ تم تقييد العضو"
        elif action == "unban":
            await self.store.srem(self.store.key("Zelzal:BanGroup:Group", msg.chat_id), target_id)
            await self.bot.unban_member(msg.chat_id, target_id)
            text = "⇜ تم الغاء حظر العضو"
        elif action == "unmute":
            await self.store.srem(self.store.key("Zelzal:SilentGroup:Group", msg.chat_id), target_id)
            await self.bot.restrict_member(msg.chat_id, target_id, can_send_messages=True)
            text = "⇜ تم الغاء كتم العضو"
        elif action == "unrestrict":
            await self.bot.restrict_member(msg.chat_id, target_id, can_send_messages=True)
            text = "⇜ تم رفع القيود عن العضو"
        elif action == "global_ban":
            await self.store.sadd(self.store.key("Zelzal:BanAll:Groups"), target_id)
            text = "⇜ تم حظر العضو عام"
        elif action == "global_mute":
            await self.store.sadd(self.store.key("Zelzal:KtmAll:Groups"), target_id)
            text = "⇜ تم كتم العضو عام"
        elif action == "global_unban":
            await self.store.srem(self.store.key("Zelzal:BanAll:Groups"), target_id)
            text = "⇜ تم الغاء حظر العضو عام"
        elif action == "global_unmute":
            await self.store.srem(self.store.key("Zelzal:KtmAll:Groups"), target_id)
            text = "⇜ تم الغاء كتم العضو عام"
        elif action == "warn":
            count = await self.store.incrby(self.store.key("Zelzal:Warnings", msg.chat_id, ":", target_id), 1)
            max_warns = int(await self.store.get(self.store.key("Zelzal:Warnings:Max", msg.chat_id)) or 3)
            if count >= max_warns:
                await self.bot.ban_member(msg.chat_id, target_id)
                await self.store.delete(self.store.key("Zelzal:Warnings", msg.chat_id, ":", target_id))
                text = "⇜ وصل العضو للحد وتم حظره"
            else:
                text = f"⇜ تم تحذير العضو\n⇜ تحذيراته: {count}/{max_warns}"
        elif action == "clear_warns":
            await self.store.delete(self.store.key("Zelzal:Warnings", msg.chat_id, ":", target_id))
            text = "⇜ تم مسح تحذيرات العضو"
        else:
            await self.store.srem(self.store.key("Zelzal:BanAll:Groups"), target_id)
            await self.store.srem(self.store.key("Zelzal:KtmAll:Groups"), target_id)
            text = "⇜ تم الغاء العام عن العضو"
        await self.bot.send_message(msg.chat_id, text, msg.message_id)

    async def _rank_command(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if not msg.reply_to_user_id:
            return False
        verb, role = text.split(" ", 1)
        role_map = {
            "مطور": ("Zelzal:Developers:Groups", 80),
            "مالك اساسي": (f"Zelzal:MalekAsase:Group{msg.chat_id}", 65),
            "مالك": (f"Zelzal:TheBasicsQ:Group{msg.chat_id}", 60),
            "منشئ اساسي": (f"Zelzal:TheBasics:Group{msg.chat_id}", 50),
            "منشئ": (f"Zelzal:Originators:Group{msg.chat_id}", 40),
            "مدير": (f"Zelzal:Managers:Group{msg.chat_id}", 30),
            "ادمن": (f"Zelzal:Addictive:Group{msg.chat_id}", 20),
            "مميز": (f"Zelzal:Distinguished:Group{msg.chat_id}", 10),
        }
        if role not in role_map:
            return False
        key, required_rank = role_map[role]
        if ctx.rank < required_rank:
            await self.bot.send_message(msg.chat_id, deny(controller_num(4)), msg.message_id)
            return True
        redis_key = self.store.key(key) if key.startswith("Zelzal:Developers") else self.store.key(key)
        if verb == "رفع":
            await self.store.sadd(redis_key, msg.reply_to_user_id)
            await self.bot.send_message(msg.chat_id, f"⇜ ابشر رفعته {role}", msg.message_id)
        else:
            await self.store.srem(redis_key, msg.reply_to_user_id)
            await self.bot.send_message(msg.chat_id, f"⇜ ابشر نزلته من {role}", msg.message_id)
        return True
