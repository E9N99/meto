from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import Settings
from .models import IncomingMessage
from .redis_store import RedisStore
from .telegram import TelegramBot


SOURCE_OWNER_IDS = {7291869416}


@dataclass(slots=True)
class PermissionContext:
    user_id: int
    chat_id: int
    rank: int
    role_name: str
    telegram_status: str = "member"
    controller_bot: bool = False
    developer_q: bool = False
    developer: bool = False
    owner_basic: bool = False
    owner: bool = False
    creator_basic: bool = False
    creator: bool = False
    manager: bool = False
    admin: bool = False
    distinguished: bool = False

    def at_least(self, rank: int) -> bool:
        return self.rank >= rank


class PermissionService:
    def __init__(self, settings: Settings, store: RedisStore, bot: TelegramBot) -> None:
        self.settings = settings
        self.store = store
        self.bot = bot

    async def context_for(self, msg: IncomingMessage) -> PermissionContext:
        user_id = msg.user_id
        chat_id = msg.chat_id
        telegram_status = await self._telegram_status(chat_id, user_id) if msg.chat_type != "private" else "member"
        p = self.store.key
        controller_all = await self.store.sismember(p("Zelzal:ControlAll:Groups"), user_id)
        developer_q = await self._member_any(user_id, "Zelzal:DevelopersQ:Groups", "Zelzal:MevelopersQ:Groups")
        developer = await self._member_any(user_id, "Zelzal:Developers:Groups", "Zelzal:Mevelopers:Groups")
        owner_basic = await self._member_any(user_id, f"Zelzal:MalekAsase:Group{chat_id}", f"Zelzal:MalemAsase:Group{chat_id}")
        owner = await self._member_any(user_id, f"Zelzal:TheBasicsQ:Group{chat_id}", f"Zelzal:TheMasicsQ:Group{chat_id}")
        creator_basic = await self._member_any(user_id, f"Zelzal:TheBasics:Group{chat_id}", f"Zelzal:TheMasics:Group{chat_id}")
        creator = await self._member_any(user_id, f"Zelzal:Originators:Group{chat_id}", f"Zelzal:Origimators:Group{chat_id}")
        manager = await self._member_any(user_id, f"Zelzal:Managers:Group{chat_id}", f"Zelzal:Mamagers:Group{chat_id}")
        admin = await self._member_any(user_id, f"Zelzal:Addictive:Group{chat_id}", f"Zelzal:Mddictive:Group{chat_id}")
        distinguished = await self._member_any(user_id, f"Zelzal:Distinguished:Group{chat_id}", f"Zelzal:Mistinguished:Group{chat_id}")

        rank = 0
        role_name = await self.role_reply("Mempar", chat_id, user_id, "عضو")
        if user_id in SOURCE_OWNER_IDS:
            rank, role_name = 100, "مبرمج السورس🎖️"
        elif user_id == self.settings.sudo_id:
            rank, role_name = 95, await self.store.get(p("Zelzal:Sudo:General:Reply")) or "مطور اساسي🎖️"
        elif controller_all:
            rank, role_name = 90, await self.store.get(p("Zelzal:Sudo2:General:Reply")) or "مطور اساسي²🎖"
        elif user_id == self.settings.bot_id:
            rank, role_name = 88, "البوت"
        elif developer_q:
            rank, role_name = 80, await self.store.get(p("Zelzal:DeveloperQ:General:Reply")) or "المطور الثانوي🎖️"
        elif developer:
            rank, role_name = 70, await self.role_reply("Developer", chat_id, user_id, "المطـــور ")
        elif owner_basic:
            rank, role_name = 65, await self.role_reply("PresidentQQ", chat_id, user_id, "المــــالك الاسـاسـي 🌟")
        elif owner or telegram_status == "creator":
            rank, role_name = 60, await self.role_reply("PresidentQ", chat_id, user_id, "المــــــالك 🌟")
        elif creator_basic:
            rank, role_name = 50, await self.role_reply("President", chat_id, user_id, "المنشئ الاساسي 🌟")
        elif creator:
            rank, role_name = 40, await self.role_reply("Constructor", chat_id, user_id, "المنشــىء 🌟")
        elif manager:
            rank, role_name = 30, await self.role_reply("Manager", chat_id, user_id, "المـــــدير 🌟")
        elif admin or telegram_status == "administrator":
            rank, role_name = 20, await self.role_reply("Admin", chat_id, user_id, "الادمـــــن 🌟")
        elif distinguished:
            rank, role_name = 10, await self.role_reply("Vip", chat_id, user_id, "المميــز ⭐️")

        return PermissionContext(
            user_id=user_id,
            chat_id=chat_id,
            rank=rank,
            role_name=role_name,
            telegram_status=telegram_status,
            controller_bot=rank >= 90,
            developer_q=rank >= 80,
            developer=rank >= 70,
            owner_basic=rank >= 65,
            owner=rank >= 60,
            creator_basic=rank >= 50,
            creator=rank >= 40,
            manager=rank >= 30,
            admin=rank >= 20,
            distinguished=rank >= 10,
        )

    async def role_reply(self, role: str, chat_id: int, user_id: int, fallback: str) -> str:
        p = self.store.key
        return (
            await self.store.get(p("Zelzal:SetRt", chat_id, ":", user_id))
            or await self.store.get(p(f"Zelzal:{role}:Group:Reply", chat_id))
            or await self.store.get(p(f"Zelzal:{role}:General:Reply"))
            or fallback
        )

    async def _member_any(self, user_id: int, *keys_without_prefix: str) -> bool:
        for key in keys_without_prefix:
            if await self.store.sismember(self.store.key(key), user_id):
                return True
        return False

    async def _telegram_status(self, chat_id: int, user_id: int) -> str:
        try:
            member: dict[str, Any] = await self.bot.get_chat_member(chat_id, user_id)
        except Exception:
            return "member"
        return str(member.get("status", "member"))


def controller_num(rank: int) -> str:
    labels = {
        1: "المطور الاساسي",
        2: "المطور الثانوي",
        3: "المطور",
        4: "المالك",
        5: "المنشئ الاساسي",
        6: "المدير",
        7: "الادمن",
        8: "المميز",
    }
    return labels.get(rank, "رتبة اعلى")

