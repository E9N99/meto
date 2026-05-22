from __future__ import annotations

import re


def mention(user_id: int, first_name: str | None) -> str:
    name = (first_name or str(user_id)).replace("[", "").replace("]", "")
    return f"[{name}](tg://user?id={user_id})"


def get_by_name(user_id: int, first_name: str | None) -> str:
    return f"*⇜ من*  {mention(user_id, first_name)}\n"


def deny(role: str) -> str:
    return f"\n*⇜ هـذا الامـر يخـص* ( {role} ) "


def format_money(value: int | float | str) -> str:
    try:
        number = int(float(value))
    except Exception:
        number = 0
    return f"{number:,}".replace(",", ".")


def coin(text: str | None) -> int:
    if not text:
        return 0
    value = text.strip().lower()
    multipliers = {
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
        "الف": 1_000,
        "ألف": 1_000,
        "مليون": 1_000_000,
        "مليار": 1_000_000_000,
    }
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([a-z]+|الف|ألف|مليون|مليار)?$", value)
    if not match:
        digits = re.sub(r"[^\d]", "", value)
        return int(digits or 0)
    amount = float(match.group(1))
    suffix = match.group(2)
    return int(amount * multipliers.get(suffix or "", 1))


def ctime(seconds: int) -> str:
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts: list[str] = []
    if days:
        parts.append(f"{days} يوم")
    if hours:
        parts.append(f"{hours} ساعة")
    if minutes:
        parts.append(f"{minutes} دقيقة")
    if sec or not parts:
        parts.append(f"{sec} ثانية")
    return " و ".join(parts)

