from __future__ import annotations

import asyncio
import time

from .advanced import AdvancedGroupService
from .admin import AdminService
from .bank import BankService
from .config import Settings
from .developer_commands import DeveloperCommandService
from .events import EventService
from .games import GamesService
from .models import CallbackQuery, IncomingMessage
from .menus import MenuService
from .nsfw import NSFWService
from .permissions import PermissionService
from .ported_service import PortedCommandService
from .protections import ProtectionService
from .redis_store import RedisStore
from .replies import ReplyService
from .smsm import SmsmService
from .tags import TagsService
from .telegram import TelegramBot
from .youtube import YoutubeService
from .zakhrafa import ZakhrafaService


class ZelzalApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = RedisStore(settings)
        self.bot = TelegramBot(settings.token)
        self.permissions = PermissionService(settings, self.store, self.bot)
        self.events = EventService(settings, self.store, self.bot)
        self.developer_commands = DeveloperCommandService(self.store, self.bot)
        self.menus = MenuService(settings, self.store, self.bot)
        self.admin = AdminService(self.store, self.bot)
        self.advanced = AdvancedGroupService(self.store, self.bot)
        self.protections = ProtectionService(self.store, self.bot)
        self.replies = ReplyService(self.store, self.bot)
        self.tags = TagsService(self.store, self.bot)
        self.bank = BankService(self.store, self.bot)
        self.games = GamesService(self.store, self.bot)
        self.youtube = YoutubeService(self.store, self.bot)
        self.zakhrafa = ZakhrafaService(self.store, self.bot)
        self.smsm = SmsmService(settings, self.store, self.bot)
        self.ported_commands = PortedCommandService(self.store, self.bot)
        self.nsfw = NSFWService(settings, self.store, self.bot)
        self.offset: int | None = None

    async def run(self) -> None:
        await self.store.connect()
        me = await self.bot.get_me()
        if me.get("username"):
            self.settings.bot_username = me["username"]
        print(f"Zelzal Python bot running as @{self.settings.bot_username or me.get('username', '')}")
        try:
            while True:
                updates = await self.bot.get_updates(self.offset, self.settings.poll_timeout)
                for update in updates:
                    self.offset = int(update["update_id"]) + 1
                    await self.process_update(update)
        finally:
            await self.store.close()

    async def process_update(self, update: dict) -> None:
        if await self.events.handle_update(update):
            return
        callback = CallbackQuery.from_update(update)
        if callback:
            await self._handle_callback(callback)
            return
        msg = IncomingMessage.from_update(update)
        if not msg or not msg.user_id:
            return
        if msg.user_id == self.settings.bot_id:
            return
        if msg.date and msg.date < int(time.time()) - 60:
            return
        msg = await self._normalize_text(msg)
        ctx = await self.permissions.context_for(msg)
        await self._track_message(msg)
        if await self._force_subscription(msg, ctx):
            return
        if await self.events.handle_message_event(msg):
            return
        if await self._blocked(msg, ctx):
            return
        if await self.nsfw.scan(msg, ctx):
            return
        if await self.protections.apply(msg, ctx):
            return
        for service in (self.nsfw, self.developer_commands, self.menus, self.admin, self.advanced, self.protections, self.replies, self.tags, self.games, self.bank, self.youtube, self.zakhrafa, self.smsm, self.ported_commands):
            handler = getattr(service, "handle", None) or getattr(service, "handle_command", None)
            if handler and await handler(msg, ctx):
                return

    async def _normalize_text(self, msg: IncomingMessage) -> IncomingMessage:
        text = msg.effective_text
        if not text:
            return msg
        bot_name = await self.store.get(self.store.key("Zelzal:Name:Bot")) or "بوت"
        if text.startswith(bot_name + " "):
            text = text[len(bot_name) + 1 :]
        mapped = await self.store.get(self.store.key("All:Get:Reides:Commands:Group", text))
        if not mapped:
            mapped = await self.store.get(self.store.key("Zelzal:Get:Reides:Commands:Group", msg.chat_id, ":", text))
        return msg.with_text(mapped or text)

    async def _track_message(self, msg: IncomingMessage) -> None:
        if msg.chat_type == "private":
            await self.store.sadd(self.store.key("Zelzal:Num:User:Pv"), msg.user_id)
            return
        await self.store.incrby(self.store.key("Zelzal:Num:Message:User", msg.chat_id, ":", msg.user_id), 1)
        await self.store.sadd(self.store.key("Zelzal:Group:Users", msg.chat_id), msg.user_id)
        await self.store.sadd(self.store.key("Zelzal:ChekBotAdd"), msg.chat_id)

    async def _blocked(self, msg: IncomingMessage, ctx) -> bool:
        if ctx.controller_bot:
            return False
        if await self.store.sismember(self.store.key("Zelzal:BanAll:Groups"), msg.user_id):
            try:
                await self.bot.ban_member(msg.chat_id, msg.user_id)
            except Exception:
                pass
            return True
        if await self.store.sismember(self.store.key("Zelzal:KtmAll:Groups"), msg.user_id):
            try:
                await self.bot.delete_message(msg.chat_id, msg.message_id)
            except Exception:
                pass
            return True
        if await self.store.sismember(self.store.key("Zelzal:BanGroup:Group", msg.chat_id), msg.user_id):
            try:
                await self.bot.ban_member(msg.chat_id, msg.user_id)
            except Exception:
                pass
            return True
        if await self.store.sismember(self.store.key("Zelzal:SilentGroup:Group", msg.chat_id), msg.user_id):
            try:
                await self.bot.delete_message(msg.chat_id, msg.message_id)
            except Exception:
                pass
            return True
        return False

    async def _force_subscription(self, msg: IncomingMessage, ctx) -> bool:
        if msg.chat_type != "private" or ctx.controller_bot:
            return False
        if not await self.store.get(self.store.key("Zelzal:ForceSub:Status")):
            return False
        channel = await self.store.get(self.store.key("Zelzal:ForceSub:Channel"))
        if not channel:
            return False
        try:
            member = await self.bot.get_chat_member("@" + channel.lstrip("@"), msg.user_id)
            if member.get("status") not in {"left", "kicked"}:
                return False
        except Exception:
            return False
        await self.bot.send_message(msg.chat_id, f"⇜ اشترك في قناة البوت أولاً:\n@{channel.lstrip('@')}", msg.message_id)
        return True

    async def _handle_callback(self, callback: CallbackQuery) -> None:
        if await self.menus.handle_callback(callback):
            return
        if await self.bank.handle_callback(callback):
            return
        if await self.youtube.handle_callback(callback):
            return
        if await self.ported_commands.handle_callback(callback):
            return
        await self.bot.answer_callback_query(callback.id, "⇜ تم استلام الامر", False)
