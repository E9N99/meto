from __future__ import annotations

import asyncio
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


class TelegramError(RuntimeError):
    pass


class TelegramBot:
    def __init__(self, token: str) -> None:
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    async def request(self, method: str, **params: Any) -> dict[str, Any]:
        return await asyncio.to_thread(self._request_sync, method, params)

    async def request_multipart(self, method: str, file_field: str, file_path: Path, **params: Any) -> dict[str, Any]:
        return await asyncio.to_thread(self._request_multipart_sync, method, file_field, file_path, params)

    def _request_sync(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (dict, list, tuple)):
                clean[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                clean[key] = "true" if value else "false"
            else:
                clean[key] = value
        body = urlencode(clean).encode("utf-8")
        req = Request(f"{self.base_url}/{method}", data=body)
        with urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok"):
            raise TelegramError(f"{method}: {payload}")
        return payload["result"]

    def _request_multipart_sync(self, method: str, file_field: str, file_path: Path, params: dict[str, Any]) -> dict[str, Any]:
        boundary = "----ZelzalPython" + uuid4().hex
        chunks: list[bytes] = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, bool):
                value = "true" if value else "false"
            chunks.append(f"--{boundary}\r\n".encode())
            chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
            chunks.append(str(value).encode("utf-8"))
            chunks.append(b"\r\n")
        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n".encode()
        )
        chunks.append(file_path.read_bytes())
        chunks.append(b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        req = Request(
            f"{self.base_url}/{method}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urlopen(req, timeout=600) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok"):
            raise TelegramError(f"{method}: {payload}")
        return payload["result"]

    async def get_me(self) -> dict[str, Any]:
        return await self.request("getMe")

    async def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        return await self.request(
            "getUpdates",
            offset=offset,
            timeout=timeout,
            allowed_updates=[
                "message",
                "edited_message",
                "callback_query",
                "inline_query",
                "my_chat_member",
                "chat_member",
            ],
        )

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = "Markdown",
        reply_markup: dict[str, Any] | None = None,
        disable_web_page_preview: bool = True,
    ) -> dict[str, Any]:
        return await self.request(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup,
        )

    async def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        parse_mode: str | None = "Markdown",
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    async def delete_message(self, chat_id: int | str, message_id: int) -> bool:
        return bool(await self.request("deleteMessage", chat_id=chat_id, message_id=message_id))

    async def restrict_member(
        self,
        chat_id: int | str,
        user_id: int,
        until_date: int | None = None,
        can_send_messages: bool = False,
    ) -> bool:
        permissions = {
            "can_send_messages": can_send_messages,
            "can_send_audios": can_send_messages,
            "can_send_documents": can_send_messages,
            "can_send_photos": can_send_messages,
            "can_send_videos": can_send_messages,
            "can_send_video_notes": can_send_messages,
            "can_send_voice_notes": can_send_messages,
            "can_send_polls": can_send_messages,
            "can_send_other_messages": can_send_messages,
            "can_add_web_page_previews": can_send_messages,
        }
        return bool(await self.request("restrictChatMember", chat_id=chat_id, user_id=user_id, permissions=permissions, until_date=until_date))

    async def ban_member(self, chat_id: int | str, user_id: int) -> bool:
        return bool(await self.request("banChatMember", chat_id=chat_id, user_id=user_id))

    async def unban_member(self, chat_id: int | str, user_id: int) -> bool:
        return bool(await self.request("unbanChatMember", chat_id=chat_id, user_id=user_id, only_if_banned=True))

    async def get_chat_member(self, chat_id: int | str, user_id: int) -> dict[str, Any]:
        return await self.request("getChatMember", chat_id=chat_id, user_id=user_id)

    async def get_chat(self, chat_id: int | str) -> dict[str, Any]:
        return await self.request("getChat", chat_id=chat_id)

    async def answer_callback_query(self, callback_query_id: str, text: str, show_alert: bool = True) -> bool:
        return bool(await self.request("answerCallbackQuery", callback_query_id=callback_query_id, text=text, show_alert=show_alert))

    async def pin_message(self, chat_id: int | str, message_id: int, disable_notification: bool = False) -> bool:
        return bool(await self.request("pinChatMessage", chat_id=chat_id, message_id=message_id, disable_notification=disable_notification))

    async def unpin_message(self, chat_id: int | str, message_id: int) -> bool:
        return bool(await self.request("unpinChatMessage", chat_id=chat_id, message_id=message_id))

    async def leave_chat(self, chat_id: int | str) -> bool:
        return bool(await self.request("leaveChat", chat_id=chat_id))

    async def send_media(
        self,
        chat_id: int | str,
        kind: str,
        file_id: str,
        caption: str = "",
        reply_to_message_id: int | None = None,
        parse_mode: str | None = "Markdown",
    ) -> dict[str, Any]:
        method_by_kind = {
            "photo": ("sendPhoto", "photo"),
            "video": ("sendVideo", "video"),
            "animation": ("sendAnimation", "animation"),
            "document": ("sendDocument", "document"),
            "audio": ("sendAudio", "audio"),
            "voice": ("sendVoice", "voice"),
            "video_note": ("sendVideoNote", "video_note"),
            "sticker": ("sendSticker", "sticker"),
        }
        method, field = method_by_kind[kind]
        params: dict[str, Any] = {field: file_id, "chat_id": chat_id, "reply_to_message_id": reply_to_message_id}
        if kind not in {"sticker", "video_note"}:
            params["caption"] = caption
            params["parse_mode"] = parse_mode
        local_path = Path(file_id)
        if local_path.exists():
            params.pop(field, None)
            return await self.request_multipart(method, field, local_path, **params)
        return await self.request(method, **params)
