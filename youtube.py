from __future__ import annotations

import asyncio
from pathlib import Path
import re
import tempfile

from .models import CallbackQuery, IncomingMessage
from .permissions import PermissionContext, controller_num
from .redis_store import RedisStore
from .telegram import TelegramBot
from .texts import get_by_name, mention


YOUTUBE_RE = re.compile(r"(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+)")
URL_RE = re.compile(r"(https?://\S+)")


class YoutubeService:
    def __init__(self, store: RedisStore, bot: TelegramBot) -> None:
        self.store = store
        self.bot = bot

    async def handle(self, msg: IncomingMessage, ctx: PermissionContext) -> bool:
        text = msg.effective_text or ""
        if text in {"تعطيل اليوتيوب", "تعطيل يوتيوب"}:
            if not ctx.admin:
                await self.bot.send_message(msg.chat_id, f"⇜ هذا الامر يخص ({controller_num(7)})", msg.message_id)
                return True
            key = self.store.key("youtubee", msg.chat_id)
            if await self.store.get(key):
                await self.bot.send_message(msg.chat_id, get_by_name(msg.user_id, msg.first_name) + " ⇜ تم تعطيل اليوتيوب مسبقاً", msg.message_id)
            else:
                await self.store.set(key, "true")
                await self.bot.send_message(msg.chat_id, get_by_name(msg.user_id, msg.first_name) + " ⇜ تم تعطيل اليوتيوب", msg.message_id)
            return True
        if text in {"تفعيل اليوتيوب", "تفعيل يوتيوب"}:
            if not ctx.admin:
                await self.bot.send_message(msg.chat_id, f"⇜ هذا الامر يخص ({controller_num(7)})", msg.message_id)
                return True
            key = self.store.key("youtubee", msg.chat_id)
            if await self.store.get(key):
                await self.store.delete(key)
                await self.bot.send_message(msg.chat_id, get_by_name(msg.user_id, msg.first_name) + " ⇜ تم تفعيل اليوتيوب", msg.message_id)
            else:
                await self.bot.send_message(msg.chat_id, get_by_name(msg.user_id, msg.first_name) + " ⇜ تم تفعيل اليوتيوب مسبقاً", msg.message_id)
            return True
        if text in {"تعطيل التحميل", "تعطيل سوشل"}:
            return await self._toggle_download(msg, ctx, disable=True, label=text)
        if text in {"تفعيل التحميل", "تفعيل سوشل"}:
            return await self._toggle_download(msg, ctx, disable=False, label=text)
        if text in {"اليوتيوب للمميزين", "سوشل للمميزين"}:
            if not ctx.owner:
                await self.bot.send_message(msg.chat_id, "⇜ هذا الامر يخص المالك", msg.message_id)
                return True
            await self.store.set(self.store.key("sochal", msg.chat_id), "true")
            await self.bot.send_message(msg.chat_id, f"⇜ تم تعيين {text} ومافوق", msg.message_id)
            return True
        if text in {"اليوتيوب للاعضاء", "سوشل للاعضاء"}:
            if not ctx.owner:
                await self.bot.send_message(msg.chat_id, "⇜ هذا الامر يخص المالك", msg.message_id)
                return True
            await self.store.delete(self.store.key("sochal", msg.chat_id))
            await self.bot.send_message(msg.chat_id, "⇜ تم تعيين السوشل لجميع الاعضاء", msg.message_id)
            return True
        if text in {"يوتيوب", "اليوتيوب"}:
            await self.bot.send_message(msg.chat_id, "⇜ ارسل `تحميل صوت` او `تحميل فيديو` ومعه رابط يوتيوب", msg.message_id)
            return True
        if await self._social_direct(msg, ctx, text):
            return True
        if text.startswith("بحث "):
            if await self._youtube_disabled(msg.chat_id):
                return False
            if await self._distinguished_only(msg, ctx, "⇜ عذراً اليوتيوب للمميزين ومافوق فقط"):
                return True
            search = text.removeprefix("بحث ").strip()
            await self._search(msg, search, "ytsearch5:", "yout")
            return True
        if text.startswith("ساوند ") or re.search(r" [Ss]$", text):
            if await self._download_disabled(msg.chat_id):
                return False
            if await self._distinguished_only(msg, ctx, "⇜ عذراً الساوند للمميزين ومافوق فقط"):
                return True
            search = text.removeprefix("ساوند ").removesuffix(" S").removesuffix(" s").strip()
            await self._search(msg, search, "scsearch5:", "socl")
            return True
        match = YOUTUBE_RE.search(text)
        if not match or not (text.startswith("تحميل") or text.startswith("يوتيوب")):
            return False
        if await self._youtube_disabled(msg.chat_id):
            return False
        if await self._distinguished_only(msg, ctx, "⇜ عذراً اليوتيوب للمميزين ومافوق فقط"):
            return True
        audio = "صوت" in text or "mp3" in text.lower()
        await self.bot.send_message(msg.chat_id, "⇜ جاري التحميل من يوتيوب ...", msg.message_id)
        try:
            path = await self._download(match.group(1), audio)
            await self.bot.send_media(msg.chat_id, "audio" if audio else "video", str(path), reply_to_message_id=msg.message_id)
        except Exception as exc:
            await self.bot.send_message(msg.chat_id, f"⇜ تعذر التحميل: {exc}", msg.message_id)
        return True

    async def handle_callback(self, callback: CallbackQuery) -> bool:
        user_id, action = self._split_callback(callback.data)
        if not user_id or callback.user_id != user_id:
            return False
        if ":yout:" not in action and ":socl:" not in action:
            return False
        _, kind, link = action.partition(":yout:")
        audio = False
        if not link:
            _, kind, link = action.partition(":socl:")
            audio = True
        url = ("https://youtu.be/" + link) if not audio else ("https://soundcloud.com/" + link)
        if callback.chat_id:
            await self.bot.answer_callback_query(callback.id, "⇜ جاري التحميل", False)
            try:
                path = await self._download(url, audio)
                await self.bot.send_media(callback.chat_id, "audio" if audio else "video", str(path), reply_to_message_id=callback.message_id)
            except Exception as exc:
                await self.bot.send_message(callback.chat_id, f"⇜ تعذر التحميل: {exc}", callback.message_id)
        return True

    async def _toggle_download(self, msg: IncomingMessage, ctx: PermissionContext, disable: bool, label: str) -> bool:
        if not ctx.admin:
            await self.bot.send_message(msg.chat_id, f"⇜ هذا الامر يخص ({controller_num(7)})", msg.message_id)
            return True
        key = self.store.key("soshle", msg.chat_id)
        if disable:
            await self.store.set(key, "true")
        else:
            await self.store.delete(key)
        await self.bot.send_message(msg.chat_id, get_by_name(msg.user_id, msg.first_name) + f" ⇜ تم {label}", msg.message_id)
        return True

    async def _social_direct(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        facebook = self._match_wrapped(text, "فيس")
        tiktok = self._match_wrapped(text, "تيك")
        sound = text.removeprefix("رابط ساوند ").strip() if text.startswith("رابط ساوند ") else ""
        if not (facebook or tiktok or sound):
            return False
        if await self._download_disabled(msg.chat_id):
            return False
        if facebook and await self._distinguished_only(msg, ctx, "⇜ عذراً الفيسبوك للمميزين ومافوق فقط"):
            return True
        if tiktok and await self._distinguished_only(msg, ctx, "⇜ عذراً التيك توك للمميزين ومافوق فقط"):
            return True
        if sound and await self._distinguished_only(msg, ctx, "⇜ عذراً الساوند للمميزين ومافوق فقط"):
            return True
        url = facebook or tiktok or sound
        audio = bool(sound)
        limit = 25 if audio else 50
        try:
            path = await self._download_generic(url, audio=audio, max_mb=limit)
            caption = f"- من قبل : {mention(msg.user_id, msg.first_name)}"
            await self.bot.send_media(msg.chat_id, "audio" if audio else "video", str(path), caption=caption, reply_to_message_id=msg.message_id)
        except Exception:
            await self.bot.send_message(msg.chat_id, f"⇜ لا استطيع تحميل اكثر من {limit} ميغا", msg.message_id)
        return True

    def _match_wrapped(self, text: str, word: str) -> str:
        if text.startswith(word + " "):
            return text.removeprefix(word + " ").strip()
        suffix = " " + word
        if text.endswith(suffix):
            return text[: -len(suffix)].strip()
        return ""

    async def _search(self, msg: IncomingMessage, search: str, prefix: str, kind: str) -> None:
        await self.bot.send_message(msg.chat_id, "⇜ جاري البحث ...", msg.message_id)
        try:
            results = await self._extract_search(prefix + search)
        except Exception as exc:
            await self.bot.send_message(msg.chat_id, f"⇜ تعذر البحث: {exc}", msg.message_id)
            return
        rows = []
        for title, url in results[:5]:
            if kind == "yout":
                link = url.rsplit("/", 1)[-1].replace("watch?v=", "")
                rows.append([{"text": title, "callback_data": f"{msg.user_id}/{search}:yout:{link}"}])
            else:
                link = url.replace("https://soundcloud.com/", "")
                rows.append([{"text": title, "callback_data": f"{msg.user_id}/{search}:socl:{link}"}])
        label = "اليوتيوب" if kind == "yout" else "الساوند"
        await self.bot.send_message(
            msg.chat_id,
            f"نتائج بحثك على {label} ل ( *{search}* )",
            msg.message_id,
            reply_markup={"inline_keyboard": rows},
        )

    async def _extract_search(self, query: str) -> list[tuple[str, str]]:
        def run() -> list[tuple[str, str]]:
            from yt_dlp import YoutubeDL

            with YoutubeDL({"quiet": True, "extract_flat": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(query, download=False)
            entries = info.get("entries") or []
            results = []
            for entry in entries:
                title = str(entry.get("title") or "بدون عنوان")
                url = str(entry.get("url") or entry.get("webpage_url") or "")
                if url and not url.startswith("http"):
                    url = "https://youtu.be/" + url
                results.append((title[:64], url))
            return results

        return await asyncio.to_thread(run)

    async def _youtube_disabled(self, chat_id: int) -> bool:
        return bool(await self.store.get(self.store.key("youtubee", chat_id)))

    async def _download_disabled(self, chat_id: int) -> bool:
        return bool(await self.store.get(self.store.key("soshle", chat_id)))

    async def _distinguished_only(self, msg: IncomingMessage, ctx: PermissionContext, text: str) -> bool:
        if await self.store.get(self.store.key("sochal", msg.chat_id)) and not ctx.distinguished:
            await self.bot.send_message(msg.chat_id, text, msg.message_id)
            return True
        return False

    async def _download(self, url: str, audio: bool) -> Path:
        def run() -> Path:
            from yt_dlp import YoutubeDL

            tmp = Path(tempfile.mkdtemp(prefix="zelzal_yt_"))
            outtmpl = str(tmp / "%(title).80s.%(ext)s")
            opts = {
                "outtmpl": outtmpl,
                "quiet": True,
                "noplaylist": True,
            }
            if audio:
                opts.update({"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]})
            else:
                opts.update({"format": "best[ext=mp4]/best"})
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = Path(ydl.prepare_filename(info))
            if audio:
                filename = filename.with_suffix(".mp3")
            return filename

        return await asyncio.to_thread(run)

    async def _download_generic(self, url: str, audio: bool, max_mb: int) -> Path:
        def run() -> Path:
            from yt_dlp import YoutubeDL

            tmp = Path(tempfile.mkdtemp(prefix="zelzal_social_"))
            outtmpl = str(tmp / "%(title).80s.%(ext)s")
            opts = {
                "outtmpl": outtmpl,
                "quiet": True,
                "noplaylist": True,
                "max_filesize": max_mb * 1024 * 1024,
            }
            if audio:
                opts.update({"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]})
            else:
                opts.update({"format": "best[ext=mp4]/best"})
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = Path(ydl.prepare_filename(info))
            if audio:
                filename = filename.with_suffix(".mp3")
            return filename

        return await asyncio.to_thread(run)

    def _split_callback(self, data: str) -> tuple[int | None, str]:
        if "/" not in data:
            return None, data
        user, action = data.split("/", 1)
        if user.isdigit():
            return int(user), action
        return None, action
