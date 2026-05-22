from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


def _file_id(message: dict[str, Any], kind: str) -> str | None:
    if kind == "photo" and message.get("photo"):
        return message["photo"][-1]["file_id"]
    if kind in message:
        value = message[kind]
        if isinstance(value, dict):
            return value.get("file_id")
    return None


@dataclass(slots=True)
class IncomingMessage:
    update_id: int
    message_id: int
    chat_id: int
    user_id: int
    text: str | None
    caption: str | None
    content_type: str
    file_id: str | None
    date: int
    chat_type: str
    first_name: str = ""
    username: str = ""
    reply_to_message_id: int | None = None
    reply_to_user_id: int | None = None
    reply_to_text: str | None = None
    new_chat_members: list[dict[str, Any]] = field(default_factory=list)
    left_chat_member: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_text(self) -> str | None:
        return self.text or self.caption

    def with_text(self, text: str | None) -> "IncomingMessage":
        return replace(self, text=text)

    @classmethod
    def from_update(cls, update: dict[str, Any]) -> "IncomingMessage | None":
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return None
        sender = msg.get("from") or {}
        chat = msg.get("chat") or {}
        reply = msg.get("reply_to_message") or {}
        reply_sender = reply.get("from") or {}
        text = msg.get("text")
        caption = msg.get("caption")
        content_type = "text" if text is not None else "unknown"
        file_id = None
        for kind in ("photo", "video", "animation", "document", "audio", "voice", "video_note", "sticker", "contact"):
            found = _file_id(msg, kind)
            if found or kind in msg:
                content_type = kind
                file_id = found
                break
        if msg.get("new_chat_members"):
            content_type = "new_chat_members"
        elif msg.get("left_chat_member"):
            content_type = "left_chat_member"
        elif msg.get("pinned_message"):
            content_type = "pinned_message"
        return cls(
            update_id=int(update["update_id"]),
            message_id=int(msg["message_id"]),
            chat_id=int(chat["id"]),
            user_id=int(sender.get("id", 0)),
            text=text,
            caption=caption,
            content_type=content_type,
            file_id=file_id,
            date=int(msg.get("date", 0)),
            chat_type=str(chat.get("type", "")),
            first_name=str(sender.get("first_name", "")),
            username=str(sender.get("username", "")),
            reply_to_message_id=reply.get("message_id"),
            reply_to_user_id=reply_sender.get("id"),
            reply_to_text=reply.get("text") or reply.get("caption"),
            new_chat_members=msg.get("new_chat_members") or [],
            left_chat_member=msg.get("left_chat_member"),
            raw=msg,
        )


@dataclass(slots=True)
class CallbackQuery:
    update_id: int
    id: str
    user_id: int
    data: str
    chat_id: int | None
    message_id: int | None
    raw: dict[str, Any]

    @classmethod
    def from_update(cls, update: dict[str, Any]) -> "CallbackQuery | None":
        data = update.get("callback_query")
        if not data:
            return None
        message = data.get("message") or {}
        chat = message.get("chat") or {}
        return cls(
            update_id=int(update["update_id"]),
            id=str(data["id"]),
            user_id=int(data.get("from", {}).get("id", 0)),
            data=str(data.get("data", "")),
            chat_id=chat.get("id"),
            message_id=message.get("message_id"),
            raw=data,
        )

