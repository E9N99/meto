from __future__ import annotations

from functools import lru_cache
from typing import Any

from .ported_commands import LUA_COMMANDS as PORTED_COMMANDS
from .ported_texts import LUA_TEXTS as PORTED_TEXTS


@lru_cache(maxsize=1)
def commands_by_name() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for command in PORTED_COMMANDS:
        index.setdefault(str(command["name"]), []).append(dict(command))
    return index


@lru_cache(maxsize=1)
def commands_by_system() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for command in PORTED_COMMANDS:
        index.setdefault(str(command["system"]), []).append(dict(command))
    return index


@lru_cache(maxsize=1)
def texts_by_value() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for text in PORTED_TEXTS:
        index.setdefault(str(text["value"]), []).append(dict(text))
    return index


def ported_command_names() -> set[str]:
    return set(commands_by_name())


def has_ported_command(name: str) -> bool:
    return name in commands_by_name()


def has_ported_text(value: str) -> bool:
    return value in texts_by_value()
