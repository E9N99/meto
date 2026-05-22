from __future__ import annotations

from functools import lru_cache
from typing import Any

from .models import IncomingMessage
from .models import CallbackQuery
from .permissions import PermissionContext, controller_num
from .ported_registry import PORTED_COMMANDS, PORTED_TEXTS, commands_by_name
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import deny


SYSTEM_LABELS = {
    "core_admin": "الإدارة",
    "ranks_admin": "الرتب",
    "protections": "الحماية",
    "replies": "الردود",
    "bank_economy": "البنك",
    "games": "الألعاب",
    "callbacks_buttons": "الأزرار",
    "youtube": "اليوتيوب",
    "smsm": "الخدمات",
    "library": "النظام",
    "other": "عام",
}


class PortedCommandService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = (msg.effective_text or "").strip()
        if not text:
            return False
        matches = commands_by_name().get(text)
        if not matches:
            return False
        command = self._best_match(matches)
        if not await self._allowed(msg, ctx, command):
            return True
        if await self._state_command(msg, text, command):
            return True
        if await self._list_command(msg, text, command):
            return True
        await self._generic_command(msg, text, command)
        return True

    async def handle_callback(self, callback: CallbackQuery) -> bool:
        data = callback.data or ""
        user_id, action = self._split_callback(data)
        if user_id and user_id != callback.user_id:
            await self.bot.answer_callback_query(callback.id, "• الامر لا يخصك", True)
            return True
        if action.startswith("Status_") and callback.chat_id:
            label = action.removeprefix("Status_")
            key = self.store.key("Zelzal:Ported:Callback:Status:", callback.chat_id, ":", label)
            if await self.store.get(key):
                await self.store.delete(key)
                state = "تعطيل"
            else:
                await self.store.set(key, "true")
                state = "تفعيل"
            await self.bot.answer_callback_query(callback.id, f"⇜ تم {state} {label}", True)
            return True
        if action.startswith(("mute_", "unmute_")) and callback.chat_id:
            enabled = action.startswith("mute_")
            label = action.split("_", 1)[1]
            key = self.store.key("Zelzal:Ported:Callback:Mute:", callback.chat_id, ":", label)
            if enabled:
                await self.store.set(key, "true")
            else:
                await self.store.delete(key)
            await self.bot.answer_callback_query(callback.id, f"⇜ تم {'تفعيل' if enabled else 'تعطيل'} {label}", True)
            return True
        if action in {"back", "helpall", "NextSeting", "BackSeting"}:
            await self.bot.answer_callback_query(callback.id, "⇜ تم تنفيذ الزر", False)
            return True
        if action:
            await self.bot.answer_callback_query(callback.id, "⇜ تم تنفيذ الامر", False)
            return True
        return False

    async def _allowed(self, msg: IncomingMessage, ctx: PermissionContext, command: dict[str, Any]) -> bool:
        system = str(command.get("system") or "")
        name = str(command.get("name") or "")
        if msg.chat_type == "private" and system in {"core_admin", "ranks_admin", "protections"}:
            return True
        required = 0
        if system in {"core_admin", "ranks_admin"}:
            required = 20
        if system == "protections" or name.startswith(("قفل ", "فتح ", "تفعيل ", "تعطيل ", "مسح ")):
            required = max(required, 30)
        if any(token in name for token in ("مطور", "عام", "اذاعه", "اذاعة", "الاحصائيات", "المطورين")):
            required = max(required, 70)
        if ctx.rank >= required:
            return True
        label = controller_num(6 if required == 30 else 7 if required == 20 else 3)
        await self.bot.send_message(msg.chat_id, deny(label), msg.message_id)
        return False

    async def _state_command(self, msg: IncomingMessage, text: str, command: dict[str, Any]) -> bool:
        if text.startswith("تفعيل "):
            subject = text.removeprefix("تفعيل ").strip()
            await self.store.set(self._state_key(msg.chat_id, "Status", subject), "true")
            await self._record(msg, text, command)
            await self.bot.send_message(msg.chat_id, f"⇜ تم تفعيل {subject}", msg.message_id)
            return True
        if text.startswith("تعطيل "):
            subject = text.removeprefix("تعطيل ").strip()
            await self.store.delete(self._state_key(msg.chat_id, "Status", subject))
            await self._record(msg, text, command)
            await self.bot.send_message(msg.chat_id, f"⇜ تم تعطيل {subject}", msg.message_id)
            return True
        if text.startswith("قفل "):
            subject = text.removeprefix("قفل ").strip()
            await self.store.set(self._state_key(msg.chat_id, "Lock", subject), "del")
            await self._record(msg, text, command)
            await self.bot.send_message(msg.chat_id, f"⇜ تم قفل {subject}", msg.message_id)
            return True
        if text.startswith("فتح "):
            subject = text.removeprefix("فتح ").strip()
            await self.store.delete(self._state_key(msg.chat_id, "Lock", subject))
            await self._record(msg, text, command)
            await self.bot.send_message(msg.chat_id, f"⇜ تم فتح {subject}", msg.message_id)
            return True
        if text.startswith(("مسح ", "حذف ")):
            subject = text.split(" ", 1)[1].strip()
            await self.store.delete(self._state_key(msg.chat_id, "Data", subject))
            await self._record(msg, text, command)
            await self.bot.send_message(msg.chat_id, f"⇜ تم مسح {subject}", msg.message_id)
            return True
        return False

    async def _list_command(self, msg: IncomingMessage, text: str, command: dict[str, Any]) -> bool:
        if text in {"اوامر", "الاوامر", "الاوامر المنقوله", "الاوامر المنقولة"}:
            by_system = _commands_grouped()
            lines = ["*⇜ فهرس الاوامر المنقولة إلى Python*"]
            for system, names in by_system.items():
                label = SYSTEM_LABELS.get(system, system)
                lines.append(f"⇜ {label}: {len(names)} امر")
            await self._record(msg, text, command)
            await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)
            return True
        if "قائمه" in text or "قائمة" in text or text.endswith("ين"):
            key = self._state_key(msg.chat_id, "List", text)
            values = sorted(await self.store.smembers(key))
            if not values:
                label = SYSTEM_LABELS.get(str(command.get("system")), "القائمة")
                await self.bot.send_message(msg.chat_id, f"⇜ لا توجد عناصر في {label}", msg.message_id)
                return True
            lines = [f"*⇜ {text}*"]
            lines.extend(f"{index} - `{value}`" for index, value in enumerate(values, 1))
            await self._record(msg, text, command)
            await self.bot.send_message(msg.chat_id, "\n".join(lines), msg.message_id)
            return True
        return False

    async def _generic_command(self, msg: IncomingMessage, text: str, command: dict[str, Any]) -> None:
        await self._record(msg, text, command)
        response = self._nearby_text(command)
        if not response:
            label = SYSTEM_LABELS.get(str(command.get("system")), "النظام")
            response = f"⇜ تم تنفيذ امر {label}: {text}"
        await self.bot.send_message(msg.chat_id, self._clean_response(response), msg.message_id)

    async def _record(self, msg: IncomingMessage, text: str, command: dict[str, Any]) -> None:
        await self.store.sadd(self.store.key("Zelzal:Ported:Commands:Executed", msg.chat_id), text)
        await self.store.hset(self.store.key("Zelzal:Ported:Last", msg.chat_id), "command", text)
        await self.store.hset(self.store.key("Zelzal:Ported:Last", msg.chat_id), "system", command.get("system", ""))
        await self.store.hset(self.store.key("Zelzal:Ported:Last", msg.chat_id), "user", msg.user_id)

    def _best_match(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        return sorted(matches, key=lambda item: (str(item.get("match_type")) != "exact", str(item.get("system"))))[0]

    def _nearby_text(self, command: dict[str, Any]) -> str:
        file_name = str(command.get("file") or "")
        line = int(command.get("line") or 0)
        candidates = [
            row for row in PORTED_TEXTS
            if str(row.get("file") or "") == file_name and abs(int(row.get("line") or 0) - line) <= 40
        ]
        if not candidates:
            return ""
        candidates.sort(key=lambda row: (abs(int(row.get("line") or 0) - line), len(str(row.get("value") or ""))))
        value = str(candidates[0].get("value") or "")
        return value if 1 < len(value) <= 3500 else ""

    def _clean_response(self, response: str) -> str:
        return response.replace("{الاسم}", "عزيزي").replace("{الايدي}", "").strip()

    def _state_key(self, chat_id: int, namespace: str, subject: str) -> str:
        return self.store.key("Zelzal:Ported:", namespace, ":", chat_id, ":", subject)

    def _split_callback(self, data: str) -> tuple[int | None, str]:
        if "/" not in data:
            return None, data
        user, action = data.split("/", 1)
        if user.isdigit():
            return int(user), action
        return None, action


@lru_cache(maxsize=1)
def _commands_grouped() -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for command in PORTED_COMMANDS:
        if command.get("match_type") != "exact":
            continue
        grouped.setdefault(str(command.get("system")), set()).add(str(command.get("name")))
    return grouped
